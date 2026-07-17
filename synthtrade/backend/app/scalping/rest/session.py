import asyncio
import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.scalping._state import _execution_state
from app.scalping.broadcast import _now, broadcast_scalping_event
from app.scalping.pricing import (
    _get_fee_rate,
    _is_valid_uuid,
    _net_to_gross_pct,
    _sl_price_from_entry,
)
from app.scalping.trade_executor import (
    _close_position_and_record,
    _handle_bracket_failed,
)
from app.scalping.session_lifecycle import (
    _refresh_session_balance,
    _sync_session_load_guard,
)
from app.scalping.db_ops import _save_open_position_to_db, _update_closed_position_in_db
from app.scalping.pipeline import _start_ws_broadcast, _stop_ws_broadcast
from app.scalping.config_loader import get_scalping_config
from app.db.supabase_client import get_supabase
from app.config import settings
from app.scalping.engine.position_manager import PositionManager
from app.scalping.intelligence.signal_score_engine import SignalScoreEngine
from app.core.logging import SessionContextFilter
from app.core.session_log_handler import SessionLogHandler

logger = logging.getLogger(__name__)

router = APIRouter()


def _calc_session_entry_and_hold(
    trade_history: List[Dict[str, Any]],
    current_price: Optional[float],
):
    """Calcola l'entry price del primo trade storico e il PnL % del buy-and-hold.

    Args:
        trade_history: Lista dei trade della sessione
        current_price: Prezzo corrente (ultima candela) per calcolare hold PnL
    
    Returns:
        tuple: (first_trade_entry, hold_pnl_pct) — None se non ci sono trade chiusi
    """
    closed = [t for t in trade_history if t.get("exit_price") is not None]
    if not closed:
        return None, None
    # Primo trade storico (più vecchio)
    oldest = sorted(closed, key=lambda t: t.get("timestamp", ""))[0]
    entry = oldest.get("entry_price")
    if entry is None or entry <= 0:
        return None, None
    if current_price is not None and current_price > 0:
        hold_pnl = ((current_price - entry) / entry) * 100
    else:
        hold_pnl = None
    return float(entry), round(hold_pnl, 2) if hold_pnl is not None else None


@router.get("/health")
async def scalping_health() -> Dict:
    """Health check per tutti i componenti del modulo scalping (TASK-865)."""
    session = _execution_state["session"]
    ws_client = _execution_state.get("ws_client")
    uds = _execution_state.get("user_data_stream")
    supervisor = _execution_state.get("supervisor_scheduler")
    loop = _execution_state.get("loop")
    signal_engine = _execution_state.get("signal_engine")
    guard = _execution_state.get("session_load_guard")

    return {
        "session_status": session.get("status"),
        "ws_client": {
            "connected": ws_client is not None and not ws_client._stop_event.is_set(),
            "symbol": session.get("symbol"),
        },
        "uds": {
            "active": uds is not None,
            "running": uds._running if uds else False,
        },
        "supervisor": {
            "active": supervisor._running if supervisor else False,
            "interval_sec": supervisor._interval if supervisor else None,
            "daily_calls": supervisor._daily_ai_calls if supervisor else 0,
        },
        "candle_buffer": {
            "size": len(loop._candle_buffer) if loop and loop._candle_buffer else 0,
            "ready": loop._candle_buffer.is_ready() if loop and loop._candle_buffer else False,
        },
        "signal_engine": {
            "symbol": signal_engine.symbol if signal_engine else None,
            "active": signal_engine is not None,
        },
        "session_guard": guard.monitor_data if guard else {},
    }


@router.get("/session")
async def get_session() -> Dict:
    """Get current session status.
    
    For live sessions, automatically refreshes the balance from the exchange
    so the frontend always shows the real balance, not a stale one.
    """
    session = _execution_state["session"]
    # Refresh live balance if mode is live and exchange is initialized
    if session.get("status") == "running" and session.get("mode") == "live":
        await _refresh_session_balance()
    result = session.copy()
    guard = _execution_state.get("session_load_guard")
    if guard:
        result["load_guard"] = guard.monitor_data
    
    # Aggiungi entry price e hold PnL (calcolati dai trade history)
    loop = _execution_state.get("loop")
    current_price = None
    if loop and hasattr(loop, "_candle_buffer") and loop._candle_buffer and loop._candle_buffer.latest:
        current_price = float(loop._candle_buffer.latest.close)
    first_entry, hold_pnl = _calc_session_entry_and_hold(
        _execution_state.get("trade_history", []),
        current_price,
    )
    result["first_trade_entry"] = first_entry
    result["hold_pnl_pct"] = hold_pnl
    result["fee_tier_certified"] = _execution_state.get("fee_tier_certified", None)
    # Add current signal threshold so frontend can show score/threshold
    try:
        result["signal_strength_threshold"] = get_scalping_config().signal_strength_threshold
    except Exception:
        result["signal_strength_threshold"] = None
    
    return result


@router.post("/session")
async def control_session(control: Dict) -> Dict:
    """Control session: start, stop, pause, resume."""
    session = _execution_state["session"]
    action = control.get("action")
    logger.info(f"[control_session] action={action} control={control}")

    if action == "start":
        guard = _execution_state.get("session_load_guard")
        if guard:
            guard.reset()
            guard.start_loading()

        active_symbol = control.get("symbol", session.get("symbol", "BTCUSDT"))

        # ── LIVE/DEMO MODE: verify balance BEFORE setting session state ────────────
        # TASK-1107: provider-neutral — build adapter via factory (OKX or Binance).
        # Prevent stale state when balance check fails (HTTPException would leave
        # a dirty session in memory, confusing the frontend on reconnect).
        session_mode = control.get("mode", session.get("mode", "paper"))
        if session_mode in ("live", "test"):
            if not settings.exchange_api_key or not settings.exchange_secret_key:
                raise HTTPException(status_code=400, detail="Mancano le API Key nel file .env per la modalità Live/Demo.")

            # TASK-1107: use factory — returns OkxExchangeAdapter or BinanceExchangeAdapter
            from app.execution.exchange_factory import build_exchange_adapter
            adapter = build_exchange_adapter()

            try:
                # Get quote asset from symbol (e.g. BTC-EUR -> EUR, BTCUSDT -> USDT)
                from app.execution.exchange_models import SymbolRef, UnsupportedInstrumentError
                try:
                    sym_ref = SymbolRef.from_okx(active_symbol) if "-" in active_symbol else SymbolRef.from_compact(active_symbol)
                    quote_asset = sym_ref.quote
                except Exception:
                    quote_asset = "EUR"  # fallback for OKX default

                # TASK-1116.G.3: Validate symbol exists in current environment BEFORE balance check
                try:
                    await adapter.get_symbol_rules(sym_ref)
                except UnsupportedInstrumentError:
                    mode_label = "Demo Trading" if session_mode == "test" else "Live Trading"
                    error_msg = (
                        f"Il simbolo {active_symbol} non e' disponibile in {mode_label} su {settings.EXCHANGE_PROVIDER.upper()}. "
                        f"Prova con un altro simbolo."
                    )
                    logger.error(f"✗ SYMBOL NOT AVAILABLE: {active_symbol} in {mode_label}")
                    session["status"] = "idle"
                    session["error_message"] = error_msg
                    session["error_code"] = "SYMBOL_NOT_AVAILABLE"
                    if guard:
                        guard.fail(f"symbol_not_available: {active_symbol} in {mode_label}")
                        _sync_session_load_guard()
                    try:
                        await adapter.close()
                    except Exception:
                        pass
                    return session.copy()

                available_balance = await adapter.get_balance(quote_asset)
                trade_val = float(control.get("trade_value", session.get("trade_value", 10.0)))

                if available_balance is not None and available_balance > 0 and available_balance >= trade_val:
                    _execution_state["exchange"] = adapter
                    session["live_balance"] = available_balance
                    session["paper_balance"] = available_balance
                    mode_label = "DEMO" if session_mode == "test" else "LIVE"
                    logger.info(f"✓ \033[96m\033[1mStarting balance: {available_balance} {quote_asset} [{settings.EXCHANGE_PROVIDER.upper()} {mode_label}]\033[0m")

                    # TASK-877/1114: Recupera fee tier account all'avvio sessione
                    # OKX returns negative fees (rebates): maker=-0.002 means -0.2% rebate.
                    try:
                        sym_ref_for_fee = SymbolRef.from_okx(active_symbol) if "-" in active_symbol else SymbolRef.from_compact(active_symbol)
                        fee_tier_obj = await adapter.get_trade_fee(sym_ref_for_fee)
                        fee_tier = {"maker": fee_tier_obj.maker, "taker": fee_tier_obj.taker}
                        _execution_state["fee_tier"] = fee_tier
                        _execution_state["fee_tier_certified"] = fee_tier_obj.certified
                        logger.info(f"✓ Fee tier [{settings.EXCHANGE_PROVIDER}]: maker={fee_tier_obj.maker}, taker={fee_tier_obj.taker} certified={fee_tier_obj.certified}")
                    except Exception as e:
                        logger.error(f"Impossibile recuperare fee tier reale: {e} — uso default 0.001 NON CERTIFICATO")
                        _execution_state["fee_tier"] = {"maker": 0.001, "taker": 0.001}
                        _execution_state["fee_tier_certified"] = False
                else:
                    error_msg = (
                        f"Nessun saldo Spot disponibile per {quote_asset} (trovato: {available_balance}). "
                        f"I fondi potrebbero essere in Simple Earn. Spostali su Spot e riprova."
                    )
                    mode_label = "DEMO" if session_mode == "test" else "LIVE"
                    logger.error(f"\033[91m✗ {mode_label} START BLOCKED: {error_msg}\033[0m")
                    session["live_balance"] = None
                    session["paper_balance"] = None
                    session["status"] = "idle"
                    session["error_message"] = error_msg
                    session["error_code"] = f"{mode_label}_START_BLOCKED"
                    if guard:
                        guard.fail(f"{session_mode}_start_blocked: insufficient_spot_balance")
                        _sync_session_load_guard()
                    # Close the exchange adapter to prevent resource leak
                    try:
                        await adapter.close()
                    except Exception:
                        pass
                    # Return idle session with error details (frontend will show error toast via sessionRestored$)
                    return session.copy()
            except HTTPException:
                raise
            except Exception as e:
                error_msg = f"Impossibile verificare il saldo Spot: {type(e).__name__}. Riprova."
                logger.error(f"✗ Balance fetch failed: {e}", exc_info=True)
                await broadcast_scalping_event("error", {"code": f"{session_mode.upper()}_START_BALANCE_FETCH_FAILED", "message": error_msg})
                raise HTTPException(status_code=400, detail=error_msg)

        # ── Set session state (balance is verified) ───────────────────────────
        _sync_session_load_guard()
        session["status"] = "running"
        session["session_id"] = f"sess_{uuid.uuid4().hex[:8]}"
        session["mode"] = control.get("mode", session.get("mode", "paper"))
        session["strategy"] = control.get("strategy", "scalping_v2")
        session["symbol"] = active_symbol
        session["trade_value"] = float(control.get("trade_value", session.get("trade_value", 10.0)))
        session["started_at"] = _now()
        session["stopped_at"] = None
        # Clear any previous error state from failed start attempts
        session["error_code"] = None
        session["error_message"] = None
        _execution_state["trade_history"] = []
        _execution_state["position_manager"] = PositionManager()
        
        # TASK-877: Inizializza fee tier (default per paper trading, sovrascritto per live/demo)
        if session["mode"] != "live" and not settings.exchange_demo:
            _execution_state["fee_tier"] = {"maker": 0.001, "taker": 0.001}  # default paper
        
        # Reset strategy override if there's an existing execution loop
        existing_loop = _execution_state.get("loop")
        if existing_loop:
            existing_loop.reset_strategy_override()
        
        if guard:
            guard.complete_phase("exchange_phase")
            guard.complete_phase("position_phase")

        # Store trade_value from UI (USD amount per trade)
        if "trade_value" in control:
            try:
                session["trade_value"] = max(1.0, float(control["trade_value"]))
            except (TypeError, ValueError):
                pass  # keep existing value

        # Initialize SignalScoreEngine for the symbol (usando singleton)
        try:
            _execution_state["signal_engine"] = SignalScoreEngine.get_or_create(symbol=active_symbol)
        except Exception as e:
            logger.warning(f"Could not initialize SignalScoreEngine: {e}")

        # NOTE (TASK-827): UDS non viene avviato qui.
        # Viene avviato da _start_uds_if_needed() DOPO che l'OCO è confermato.
        # Questo evita che UDS sia attivo senza ordini e rispetta il pattern singleton.

        # Start WS client + ExecutionLoop pipeline
        async def _start_with_error_logging():
            """Wrapper that logs any exception from _start_ws_broadcast."""
            logger.info(">>> START_WITH_ERROR_LOGGING: entering _start_with_error_logging")
            try:
                await _start_ws_broadcast(active_symbol.lower())
                
                # Guard: check if session is still running BEFORE saving to DB
                # Prevents race condition where user clicked stop while this task was starting
                if session.get("status") != "running":
                    logger.warning("Session status changed during broadcast startup — skipping DB insert (session already stopped by user)")
                    return
                
                # Save to Supabase after successful start
                try:
                    supabase = get_supabase()
                    db_resp = supabase.table("scalping_sessions").insert({
                        "symbol": session["symbol"],
                        "mode": session["mode"].upper(),
                        "timeframe": "1m",
                        "status": "running",
                        "started_at": session["started_at"],
                        "strategy": session.get("strategy", "scalping_v2"),
                        "trade_value": session.get("trade_value", 100.0),
                        # TASK-1108: provider-neutral fields
                        "exchange_provider": settings.EXCHANGE_PROVIDER.lower(),
                        "exchange_account_mode": settings.TRADING_MODE,
                        "exchange_demo": settings.exchange_demo,
                        "fee_tier_certified": _execution_state.get("fee_tier_certified"),
                        "fee_tier_maker": _get_fee_rate(_execution_state.get("fee_tier") or {}, "maker", None),
                        "fee_tier_taker": _get_fee_rate(_execution_state.get("fee_tier") or {}, "taker", None),
                    }).execute()
                    if db_resp.data:
                        session["db_session_id"] = db_resp.data[0]["id"]
                        logger.info(f"Session saved to DB with id={session['db_session_id']} mode={session['mode']} trade_value={session.get('trade_value')}")
                        if guard:
                            guard.complete_phase("db_phase")
                    elif guard:
                        guard.fail("db_insert_failed: empty response")
                except Exception as db_e:
                    logger.warning(f"Failed to insert session in DB: {db_e}")
                    if guard:
                        guard.fail(f"db_insert_failed: {type(db_e).__name__}: {db_e}")
                    
                # Start SupervisorScheduler
                from app.scalping.supervisor.supervisor_scheduler import SupervisorScheduler
                supervisor = SupervisorScheduler(symbol=active_symbol, interval_seconds=settings.scalping.SCALPING_SUPERVISOR_INTERVAL_SEC, score_engine=_execution_state.get("signal_engine"))
                # Attach db_session_id (UUID) so the supervisor can log it to DB
                _execution_state["loop"].session_id = session.get("db_session_id")
                supervisor.set_execution_loop(_execution_state["loop"])
                supervisor.start()
                _execution_state["supervisor_scheduler"] = supervisor
                    
            except Exception as e:
                if guard:
                    guard.fail(f"broadcast_start_failed: {type(e).__name__}: {e}")
                logger.error(f"Scalping broadcast start FAILED for {active_symbol}: {e}", exc_info=True)
                # Reset session if broadcast failed to start
                session["status"] = "idle"
                session["session_id"] = None
                session["started_at"] = None

        task = asyncio.create_task(
            _start_with_error_logging(),
            name=f"scalping-ws-{active_symbol}",
        )
        logger.info(f"[control_session] task created: name=scalping-ws-{active_symbol} done={task.done()} cancelled={task.cancelled()}")
        # Log exception if task fails silently
        def _on_task_done(t):
            if t.exception():
                logger.error(f"Scalping broadcast task CRASHED: {t.exception()}", exc_info=True)
            elif t.cancelled():
                logger.warning("Scalping broadcast task was CANCELLED")
            else:
                logger.info("Scalping broadcast task completed normally")
        task.add_done_callback(_on_task_done)
        
        # ── SESSION LOGGING: attach session_id to all logs + start capture ──
        SessionContextFilter.set_session_id(session["session_id"])
        db_sid = session.get("db_session_id", "")
        session_log_handler = SessionLogHandler(
            session_id=session["session_id"],
            db_session_id=db_sid,
        )
        session_log_handler.symbol = active_symbol
        session_log_handler.attach()  # aggancia root + forced logger
        
        # Soluzione 1: Configura callback per persistenza live su DB
        _handler_logger = logger  # capture reference for closure
        def _make_persist_callback(h: SessionLogHandler) -> Callable[[str], None]:
            """Crea un callback sincrono che salva il contenuto su DB via asyncio thread."""
            import functools
            _db_sid = h.db_session_id
            def _save_to_db(content: str) -> None:
                if not _db_sid:
                    return
                try:
                    from app.db.supabase_client import get_supabase
                    supabase = get_supabase()
                    supabase.table("scalping_sessions").update({
                        "log_content": content,
                    }).eq("id", _db_sid).execute()
                except Exception as e:
                    _handler_logger.warning(f"[LIVE_LOG] Failed to persist logs to DB: {e}")
            return _save_to_db
        
        if db_sid:
            session_log_handler.set_persist_callback(_make_persist_callback(session_log_handler))
            logger.info(f"[LIVE_LOG] Persist callback configured for session {db_sid}")
        
        _execution_state["session_log_handler"] = session_log_handler
        logger.info(f"Session log capture started for {session['session_id']}")
        
        # Soluzione 1: Avvia il task periodico di persistenza log (ogni 5 min)
        _LOG_PERSIST_INTERVAL_SEC = 300  # 5 minuti
        async def _periodic_log_persist():
            """Task asincrono che salva i log su DB ogni 5 minuti.
            
            Se il backend crasha/riavvia, i log salvati fino all'ultimo persist
            sono comunque recuperabili dal DB (non più persi completamente).
            """
            while session.get("status") == "running":
                await asyncio.sleep(_LOG_PERSIST_INTERVAL_SEC)
                handler = _execution_state.get("session_log_handler")
                if handler and handler.log_count > 0:
                    ok = handler.persist_now()
                    if ok:
                        _handler_logger.info(f"[LIVE_LOG] Periodic persist OK ({handler.log_count} entries)")
                    else:
                        _handler_logger.debug("[LIVE_LOG] Periodic persist skipped (no callback or empty)")
        
        _persist_task = asyncio.create_task(_periodic_log_persist(), name="log-persist-periodic")
        _execution_state["log_persist_task"] = _persist_task

        logger.info(f"Session started: {session['session_id']} mode={session['mode']} symbol={active_symbol}")

    elif action == "stop":
        # Set session status to idle IMMEDIATELY to prevent race conditions
        # (the _start_with_error_logging task checks this flag before saving to DB)
        session["status"] = "idle"
        
        # Force close any open position at market price
        pm = _execution_state["position_manager"]
        pos = pm.get_open()
        
        # TASK-1128 FIX: In live mode, also liquidate any untracked base asset balance.
        # Race condition: if the session is stopped between the market BUY and the bracket
        # registration, pm.get_open() returns None but we still hold the base asset.
        _stop_mode = _execution_state.get("session", {}).get("mode", "paper")
        _stop_exchange = _execution_state.get("exchange")
        if not pos and _stop_mode == "live" and _stop_exchange:
            active_sym = _execution_state.get("session", {}).get("symbol", "")
            if active_sym:
                try:
                    logger.info(f"[STOP] No tracked position but live mode — checking exchange balance for {active_sym} before stop")
                    await _handle_bracket_failed(_stop_exchange, active_sym.upper())
                except Exception as _stop_emergency_e:
                    logger.warning(f"[STOP] Emergency liquidation check failed (non-blocking): {_stop_emergency_e}")
        
        if pos:
            close_price: float = float(pos.entry_price)
            _mode_stop = _execution_state["session"].get("mode", "paper")
            exchange_stop = _execution_state.get("exchange")

            # Use latest candle price if available for more accurate close.
            # PAPER MODE: only use candle price if it's from the mock generator
            # (to avoid using real OKX prices for mock positions opened at ~100€).
            # LIVE MODE: always use latest candle.
            loop = _execution_state.get("loop")
            if loop and hasattr(loop, "_candle_buffer") and getattr(loop, "_candle_buffer", None):
                latest = loop._candle_buffer.latest
                if latest:
                    latest_price = float(latest.close)
                    if _mode_stop == "live":
                        close_price = latest_price
                    else:
                        # Paper: only use candle price if it's close to entry (within 10x)
                        # This avoids mixing real market prices with mock positions
                        if latest_price > 0 and abs(latest_price - float(pos.entry_price)) / float(pos.entry_price) < 9.0:
                            close_price = latest_price

            if _mode_stop == "live" and exchange_stop:
                # TASK-829: cancella OCO e attendi conferma prima di market sell
                try:
                    open_orders_before = await exchange_stop.get_open_orders(pos.symbol)
                    if open_orders_before:
                        ccxt_sym = exchange_stop._get_ccxt_symbol(pos.symbol)
                        for o in open_orders_before:
                            try:
                                await exchange_stop.client.cancel_order(o["id"], ccxt_sym)
                            except Exception:
                                pass
                        logger.info(f"Cancellati {len(open_orders_before)} ordini OCO per stop sessione")

                        # Attendi conferma cancellazione (race condition protection)
                        await asyncio.sleep(0.5)
                        for _retry in range(3):
                            remaining = await exchange_stop.get_open_orders(pos.symbol)
                            if not remaining:
                                break
                            await asyncio.sleep(0.3)
                        else:
                            logger.warning(f"OCO orders still active after 3 retries for {pos.symbol}")
                except Exception as cancel_e:
                    logger.warning(f"OCO cancel on stop failed (non-blocking): {cancel_e}")

            # Close position at market
            try:
                await _close_position_and_record(pm, close_price, pos, reason="session_stop")
                logger.info(f"Position force-closed at market @ {close_price} due to session stop")
            except Exception as e:
                logger.error(f"Error force closing position during session stop: {e}", exc_info=True)
                if pos.status == "open" and _mode_stop != "live":
                    pm.close_position(Decimal(str(close_price)))
        
        # Stop WS client and pipeline
        asyncio.create_task(
            _stop_ws_broadcast(),
            name="scalping-ws-stop",
        )

        # Stop User Data Stream if active (TASK-827)
        uds = _execution_state.pop("user_data_stream", None)
        if uds:
            asyncio.create_task(uds.stop(), name="uds-stop")
        
        # Stop SupervisorScheduler if running
        if "supervisor_scheduler" in _execution_state and _execution_state["supervisor_scheduler"]:
            _execution_state["supervisor_scheduler"].stop()
            _execution_state["supervisor_scheduler"] = None
        
    # ── SESSION LOGGING: save log content to DB (deploy-safe) ──
        session_log_handler = _execution_state.pop("session_log_handler", None)
        mem_session_id = session.get("session_id")
        db_sid_for_log = session.get("db_session_id")
        log_symbol = session.get("symbol", "UNKNOWN")
        if session_log_handler and mem_session_id:
            try:
                log_content = session_log_handler.get_formatted_content(
                    session_id=mem_session_id,
                    symbol=log_symbol,
                )
                if log_content and db_sid_for_log:
                    supabase_log = get_supabase()
                    supabase_log.table("scalping_sessions").update({
                        "log_content": log_content,
                    }).eq("id", db_sid_for_log).execute()
                    logger.info(f"Session log content saved to DB for session {db_sid_for_log}")
            except Exception as log_e:
                logger.warning(f"Failed to save log content to DB: {log_e}")
        # Remove session log handler from root + forced loggers
        if session_log_handler:
            session_log_handler.detach()
        # Clear session_id from log context
        SessionContextFilter.set_session_id(None)

        # Clear session state
        session["session_id"] = None
        session["started_at"] = None
        session["stopped_at"] = _now()
        
        if _execution_state.get("exchange"):
            asyncio.create_task(_execution_state["exchange"].close(), name="close_exchange")
            _execution_state["exchange"] = None
        
        # Update DB: set status to "stopped"
        try:
            db_sid = session.get("db_session_id")
            if db_sid:
                supabase = get_supabase()
                # Calcola statistiche dalla trade history in memoria
                closed = [t for t in _execution_state.get("trade_history", []) if t.get("exit_price") is not None]
                total_pnl_val = round(sum((t.get("pnl") or 0) for t in closed), 4)
                win_count_val = len([t for t in closed if (t.get("pnl") or 0) > 0])
                supabase.table("scalping_sessions").update({
                    "status": "stopped",
                    "stopped_at": session["stopped_at"],
                    "trade_count": len(closed),
                    "win_count": win_count_val,
                    "total_pnl": total_pnl_val,
                }).eq("id", db_sid).execute()
                logger.info(f"Session {db_sid} stopped — trades={len(closed)} wins={win_count_val} pnl={total_pnl_val}")
        except Exception as e:
            logger.warning(f"Failed to update session in DB: {e}")
        
        logger.info(f"Session stopped — open positions closed at market")

    elif action == "pause":
        if session["status"] == "running":
            session["status"] = "paused"
            try:
                db_sid = session.get("db_session_id")
                if db_sid:
                    supabase = get_supabase()
                    supabase.table("scalping_sessions").update({
                        "status": "paused"
                    }).eq("id", db_sid).execute()
            except Exception as e:
                logger.warning(f"Failed to update session in DB: {e}")

    elif action == "resume":
        if session["status"] == "paused":
            # Se live mode, verifica prima che lo spot balance sia sufficiente
            if session.get("mode") == "live":
                try:
                    await _refresh_session_balance()
                    bal = session.get("live_balance", 0)
                    trade_val = float(session.get("trade_value", 10.0))
                    if bal is None or bal <= 0 or bal < trade_val:
                        logger.warning(
                            f"\033[91m⚠️ RESUME BLOCKED: Spot balance={bal} < trade_value={trade_val}. "
                            f"Still in Earn. Remain paused.\033[0m"
                        )
                        session["status"] = "paused"
                        return {"status": "paused", "reason": "spot_empty",
                                "message": "Ancora nessun fondo in Spot. Sposta fondi da Earn a Spot e riprova."}
                    logger.info(f"Resume: Spot balance OK ({bal}), resuming session.")
                except Exception as e:
                    logger.warning(f"Resume balance refresh failed (non-fatal): {e}")
                    # Se fallisce, resuma comunque — meglio di restare bloccati
            session["status"] = "running"
            try:
                db_sid = session.get("db_session_id")
                if db_sid:
                    supabase = get_supabase()
                    supabase.table("scalping_sessions").update({
                        "status": "running"
                    }).eq("id", db_sid).execute()
            except Exception as e:
                logger.warning(f"Failed to update session in DB: {e}")

    result = session.copy()
    try:
        result["signal_strength_threshold"] = get_scalping_config().signal_strength_threshold
    except Exception:
        result["signal_strength_threshold"] = None
    return result


@router.get("/session/{session_id}/logs")
async def download_session_logs(session_id: str) -> Response:
    """Download the log file for a given session.

    Genera il file .txt al volo dal contenuto salvato nel DB (log_content).
    I log vengono salvati nel DB allo stop della sessione.
    """
    try:
        supabase = get_supabase()
        resp = supabase.table("scalping_sessions") \
            .select("log_content, symbol") \
            .eq("id", session_id) \
            .limit(1) \
            .execute()

        if not resp.data:
            raise HTTPException(status_code=404, detail="Session not found.")

        row = resp.data[0]
        log_content = row.get("log_content")
        if not log_content:
            raise HTTPException(
                status_code=404,
                detail="Log non disponibili per questa sessione. "
                       "I log vengono salvati nel DB allo stop della sessione. "
                       "Sessioni precedenti alla migration potrebbero non averli."
            )

        symbol = row.get("symbol", "UNKNOWN")
        filename = f"session_{symbol}_{session_id}_logs.txt"
        return Response(
            content=log_content,
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Failed to download session logs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download logs: {e}")


@router.get("/session/{session_id}/logs/analysis")
async def get_session_log_analysis(session_id: str) -> Dict:
    """Restituisce l'analisi strutturata dei log di una sessione in formato JSON.

    Utile per analisi programmatiche e report automatici.
    Contiene conteggi e metriche estratte dai log raw.
    """
    try:
        supabase = get_supabase()
        resp = supabase.table("scalping_sessions") \
            .select("log_content, symbol") \
            .eq("id", session_id) \
            .limit(1) \
            .execute()

        if not resp.data:
            raise HTTPException(status_code=404, detail="Session not found.")

        row = resp.data[0]
        log_content = row.get("log_content")
        if not log_content:
            raise HTTPException(status_code=404, detail="Log non disponibili per questa sessione.")

        # Parse log lines back into a temporary handler for analysis
        from app.core.session_log_handler import SessionLogHandler

        # Create a temp handler and replay the log content through it
        temp_handler = SessionLogHandler()
        for line in log_content.split("\n"):
            if line.strip():
                # Skip header/footer lines
                if line.startswith("=") or line.startswith(" SESSION LOG DUMP") or \
                   line.startswith(" Session ID") or line.startswith(" Symbol") or \
                   line.startswith(" Entries") or line.startswith(" Generated") or \
                   line.startswith(" SESSION ANALYSIS SUMMARY"):
                    continue
                temp_handler._buffer.append(line)

        analysis = temp_handler.get_structured_analysis()

        # Convert Counter objects to dicts for JSON serialization
        def _clean(obj):
            if isinstance(obj, dict):
                return {k: _clean(v) for k, v in obj.items()}
            elif hasattr(obj, 'most_common'):
                return dict(obj)
            elif isinstance(obj, list):
                return [_clean(i) for i in obj]
            return obj

        return {
            "session_id": session_id,
            "symbol": row.get("symbol", "UNKNOWN"),
            "analysis": _clean(analysis),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Failed to analyze session logs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze logs: {e}")


@router.patch("/session/trade-value")
async def update_trade_value(body: Dict) -> Dict:
    """Update trade_value for the active session.
    
    This takes effect from the NEXT trade execution.
    Accepts: {"trade_value": <number>}
    """
    session = _execution_state["session"]
    try:
        new_value = max(1.0, float(body["trade_value"]))
        session["trade_value"] = new_value
        logger.info(f"Trade value updated to {new_value} USD (effective from next trade)")
        return {"trade_value": new_value, "status": session["status"]}
    except (KeyError, TypeError, ValueError) as e:
        raise HTTPException(status_code=422, detail=f"Invalid trade_value: {e}")


@router.get("/position")
async def get_position() -> Optional[Dict]:
    """Get current open position from PositionManager."""
    pm = _execution_state["position_manager"]
    pos = pm.get_open()
    if not pos:
        return None
    
    # Calculate current PnL estimate
    entry = float(pos.entry_price)
    loop = _execution_state.get("loop")
    if loop and hasattr(loop, "_candle_buffer") and len(loop._candle_buffer) > 0:
        candles = loop._candle_buffer.get()
        current_price = float(candles[-1].close)
        qty = float(pos.quantity)
        entry_val = entry * qty
        current_val = current_price * qty
        gross_pnl = (current_price - entry) * qty if pos.side == "BUY" else (entry - current_price) * qty
        
        # TASK-884: Usa fee tier per PnL non realizzato (Caso B)
        # Entry: commissione reale se disponibile da WebSocket, altrimenti fee tier
        if pos.entry_commission is not None and pos.entry_commission > 0:
            entry_commission = float(pos.entry_commission)
            # Converti BNB to USDC se necessario
            if pos.entry_commission_asset == "BNB":
                # Non possiamo chiamare exchange qui (endpoint sincrono), assumiamo conversione manuale o valore salvato
                # Per ora usiamo il valore come è (dovrebbe essere già convertito o in USDC)
                entry_commission = entry_commission
        else:
            # Fallback: usa fee tier per entrata (costo atteso)
            fee_tier = _execution_state.get("fee_tier", {"maker": 0.001, "taker": 0.001})
            entry_fee_rate = _get_fee_rate(fee_tier, "taker", 0.001)  # market order = taker
            entry_commission = entry_val * entry_fee_rate
        
        # Exit: usa fee tier (costo di chiusura atteso al tier corrente)
        fee_tier = _execution_state.get("fee_tier", {"maker": 0.001, "taker": 0.001})
        exit_fee_rate = _get_fee_rate(fee_tier, "taker", 0.001)  # OKX OCO = market order (taker)
        exit_commission = current_val * exit_fee_rate
        
        total_fees = entry_commission + exit_commission
        pnl = gross_pnl - total_fees
        pnl_pct = (pnl / entry_val) * 100
    else:
        current_price = float(pos.entry_price)
        pnl = 0.0
        pnl_pct = 0.0
    
    # TASK-885: Calcola target netti TP/SL per endpoint REST
    risk_cfg = _execution_state.get("risk_config", {})
    sl_pct = float(risk_cfg.get("stop_loss_pct", 0.3))
    tp_pct = float(risk_cfg.get("take_profit_pct", 0.5))
    fee_tier = _execution_state.get("fee_tier", {"maker": 0.001, "taker": 0.001})
    entry_fee_rate = _get_fee_rate(fee_tier, "taker", 0.001)  # market order = taker
    exit_fee_rate = _get_fee_rate(fee_tier, "taker", 0.001)  # OKX OCO = market order (taker)
    fee_round_trip = (entry_fee_rate + exit_fee_rate) * 100  # converti in percentuale
    
    # Calcola percentuali nette (sottrai fee round-trip dai target lordi)
    sl_pct_net = sl_pct - fee_round_trip  # perdita netta è peggiore
    tp_pct_net = tp_pct - fee_round_trip  # guadagno netto è minore

    # TASK-1129: veri prezzi TP/SL piazzati su OKX (fallback a ricalcolo da pct
    # per posizioni pre-fix / restore senza questi campi).
    _ef_p = _get_fee_rate(fee_tier, "taker", 0.001)
    _xf_p = _get_fee_rate(fee_tier, "taker", 0.001)  # OKX OCO = market (taker)
    # TASK-1127: Fees are now positive for base level accounts
    sl_price_calc = _sl_price_from_entry(entry, pos.side, sl_pct, _ef_p, _xf_p)[0]
    tp_price_calc = entry * (1 + _net_to_gross_pct(tp_pct, _ef_p, _xf_p) / 100) if pos.side == "BUY" else entry * (1 - _net_to_gross_pct(tp_pct, _ef_p, _xf_p) / 100)
    stop_loss_price = float(pos.sl_price) if pos.sl_price is not None else sl_price_calc
    take_profit_price = float(pos.tp_price) if pos.tp_price is not None else tp_price_calc

    return {
        "symbol": pos.symbol,
        "side": pos.side,
        "entry_price": float(pos.entry_price),
        "current_price": current_price,
        "quantity": float(pos.quantity),
        "pnl": round(pnl, 2),
        "pnl_pct": round(pnl_pct, 2),
        "status": pos.status.value,
        "entry_time": pos.entry_time.isoformat(),
        "stop_loss_pct": sl_pct,
        "take_profit_pct": tp_pct,
        "stop_loss_pct_net": round(sl_pct_net, 2),  # TASK-885
        "take_profit_pct_net": round(tp_pct_net, 2),  # TASK-885
        "stop_loss_price": round(stop_loss_price, 2),  # TASK-1129
        "take_profit_price": round(take_profit_price, 2),  # TASK-1129
        "breakeven_pct": round(fee_round_trip, 2),
    }


@router.get("/position/list")
async def list_positions() -> List[Dict]:
    """List all positions from PositionManager."""
    pm = _execution_state["position_manager"]
    positions = pm.get_all()
    return [
        {
            "symbol": p.symbol,
            "side": p.side,
            "entry_price": float(p.entry_price),
            "quantity": float(p.quantity),
            "status": p.status.value,
            "entry_time": p.entry_time.isoformat(),
        }
        for p in positions
    ]


@router.get("/config")
async def get_scalping_config_endpoint():
    cfg = get_scalping_config()
    return {"config": cfg._config, "source": "env+db_override"}

@router.post("/config/reload")
async def reload_scalping_config():
    get_scalping_config().reload()
    return {"status": "reloaded"}

@router.post("/config/{key}")
async def update_scalping_config(key: str, value: str):
    db = get_supabase()
    db.table("scalping_runtime_config").update({
        "value": value,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("key", key).execute()
    get_scalping_config().reload()
    return {"key": key, "value": value, "status": "updated"}


@router.get("/risk/config")
async def get_risk_config() -> Dict:
    try:
        supabase = get_supabase()
        response = supabase.table("scalping_risk_config").select("*").eq("id", 1).execute()
        if response.data and len(response.data) > 0:
            db_config = response.data[0]
            # Exclude id, updated_at from the active memory representation
            clean_config = {k: v for k, v in db_config.items() if k not in ["id", "updated_at"]}
            _execution_state["risk_config"] = clean_config
            return clean_config
    except Exception as e:
        logger.error(f"Error fetching risk config from DB: {e}")
    # Fallback to memory
    return _execution_state.get("risk_config", {})

@router.post("/risk/config")
async def update_risk_config(config: Dict) -> Dict:
    # Exclude position_size if present (managed via trade_value instead)
    clean_cfg = {k: v for k, v in config.items() if k != "position_size"}
    _execution_state["risk_config"] = clean_cfg
    
    # Persist to Supabase
    try:
        supabase = get_supabase()
        db_payload = {
            "id": 1,
            "max_daily_loss": clean_cfg.get("max_daily_loss", 50),
            "max_drawdown": clean_cfg.get("max_drawdown", 10),
            "leverage": clean_cfg.get("leverage", 10),
            "stop_loss_pct": clean_cfg.get("stop_loss_pct", 1.05),
            "take_profit_pct": clean_cfg.get("take_profit_pct", 1.55),
        }
        supabase.table("scalping_risk_config").upsert(db_payload).execute()
        logger.info("Persisted risk config to Supabase")
    except Exception as e:
        logger.error(f"Error persisting risk config to DB: {e}")
        
    return clean_cfg


@router.get("/performance")
async def get_performance() -> Dict:
    """Get performance metrics from trade history."""
    # Only count completed (closed) trades — exclude open positions still in history
    trades = [t for t in _execution_state["trade_history"] if t.get("exit_price") is not None]

    if not trades:
        return {
            "total_pnl": 0,
            "total_pnl_pct": 0,
            "win_rate": 0,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "avg_win": 0,
            "avg_loss": 0,
            "profit_factor": 0,
            "max_drawdown": 0,
            "consecutive_losses": 0,
        }
    
    winning = [t for t in trades if (t.get("pnl") or 0) > 0]
    losing = [t for t in trades if (t.get("pnl") or 0) < 0]
    
    total_pnl = sum((t.get("pnl") or 0) for t in trades)
    win_count = len(winning)
    lose_count = len(losing)
    total = len(trades)
    
    avg_win = sum((t.get("pnl") or 0) for t in winning) / win_count if win_count else 0
    avg_loss = abs(sum((t.get("pnl") or 0) for t in losing) / lose_count) if lose_count else 0
    
    gross_profit = sum((t.get("pnl") or 0) for t in winning)
    gross_loss = abs(sum((t.get("pnl") or 0) for t in losing))
    profit_factor = round(gross_profit / gross_loss, 4) if gross_loss > 0 else 0
    
    # Calculate max drawdown from running equity
    running_pnl = 0.0
    base_balance = float(_execution_state["session"].get("paper_balance", 10000.0) or 10000.0)
    equity = base_balance
    peak_equity = base_balance
    max_dd_pct = 0.0
    for t in trades:
        running_pnl += (t.get("pnl") or 0)
        equity = base_balance + running_pnl
        if equity > peak_equity:
            peak_equity = equity
        if peak_equity > 0:
            dd_pct = (peak_equity - equity) / peak_equity
            if dd_pct > max_dd_pct:
                max_dd_pct = dd_pct
    
    # Consecutive losses
    cons_losses = 0
    max_cons_losses = 0
    for t in reversed(trades):
        if (t.get("pnl") or 0) < 0:
            cons_losses += 1
        else:
            break
    # Also calculate historical max consecutive losses
    current_run = 0
    for t in trades:
        if (t.get("pnl") or 0) < 0:
            current_run += 1
            max_cons_losses = max(max_cons_losses, current_run)
        else:
            current_run = 0
    
    session = _execution_state["session"]
    allocated_capital = float(session.get("trade_value") or 0)
    if allocated_capital <= 0:
        allocated_capital = float(session.get("paper_balance") or 10000.0)
    
    total_pnl_pct = (total_pnl / allocated_capital) * 100 if allocated_capital > 0 else 0

    # Hold PnL: how much we'd have made holding from first trade entry price
    loop = _execution_state.get("loop")
    current_price = None
    if loop and hasattr(loop, "_candle_buffer") and loop._candle_buffer and loop._candle_buffer.latest:
        current_price = float(loop._candle_buffer.latest.close)
    first_entry, hold_pnl_pct = _calc_session_entry_and_hold(
        _execution_state.get("trade_history", []),
        current_price,
    )

    # Signal strength threshold (variable, set by supervisor)
    try:
        signal_threshold = get_scalping_config().signal_strength_threshold
    except Exception:
        signal_threshold = None

    trading_beats_hold = None
    if hold_pnl_pct is not None:
        trading_beats_hold = total_pnl_pct >= hold_pnl_pct

    return {
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl_pct, 2),
        "win_rate": round(win_count / total * 100, 2) if total else 0,
        "total_trades": total,
        "winning_trades": win_count,
        "losing_trades": lose_count,
        "avg_win": round(avg_win, 4),
        "avg_loss": round(avg_loss, 4),
        "profit_factor": profit_factor,
        "max_drawdown": max_dd_pct,
        "consecutive_losses": max_cons_losses,
        # Trading vs Hold comparison
        "hold_pnl_pct": round(hold_pnl_pct, 2) if hold_pnl_pct is not None else None,
        "trading_beats_hold": trading_beats_hold,
        # Signal threshold (for proximity indicator in Market Intel panel)
        "signal_strength_threshold": signal_threshold,
    }
