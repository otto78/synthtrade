"""Candle processor: consume candle_queue, broadcast to frontend, feed execution loop.

Extracted from market_processors.py (TASK-1166.D).
"""
import asyncio
import logging
import math
from datetime import datetime, timezone
from decimal import Decimal

from app.config import settings
from app.db.supabase_client import get_supabase
from app.scalping._state import _execution_state
from app.scalping.pricing import (
    _get_fee_rate,
    _sl_price_from_entry,
    _net_to_gross_pct,
    _convert_bnb_commission_to_usdc,
    _sl_gross_fraction,
    _expected_net_pct_at_exit,
)
from app.scalping.db_ops import _save_open_position_to_db
from app.scalping.break_even import (
    _check_and_apply_break_even,
    _check_and_apply_trailing,
    _compute_trailing_step_levels,
)
from app.scalping.trade_executor import (
    _start_uds_if_needed,
    _handle_bracket_failed,
    _close_position_and_record,
    _check_session_loss,
    _check_drawdown,
)
from app.scalping.session_lifecycle import _sync_session_load_guard, _refresh_session_balance
from app.scalping.broadcast import broadcast_scalping_event
from app.scalping.models.market import Candle
from app.execution.exchange_models import MarketOrderRequest, ExitBracketRequest, SymbolRef
from app.core.signal_log_writer import log_signal_decision, log_mean_reversion_decision, log_execution_error, log_hold_decision

logger = logging.getLogger(__name__)

# ANSI color codes for decision cycle visibility
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


async def _wait_for_fill(
    exchange,
    sym_ref,
    order_id: str,
    fallback_price: float,
    fallback_qty: float,
    max_attempts: int = 20,
    sleep_sec: float = 0.25,
) -> tuple[float, float]:
    """Attendere il fill reale di un market order prima di piazzare il bracket.

    OKX riempie i market order in modo asincrono: la POST restituisce subito
    l'ordId ma avgPx/accFillSz possono essere ancora vuoti e il saldo BTC non
    accreditato sul ledger. Piazzare il bracket SELL in quel momento produce
    sCode 51008 ("available BTC balance is insufficient, and your available
    margin ... too low for borrowing"). Questo helper fa polling su
    GET /trade/order finché state=filled e ritorna (avgPx, accFillSz) reali.

    Provider-neutral: se l'adapter non espone get_order_by_id (es. Binance
    legacy) salta il polling e ritorna subito i fallback.
    """
    if not order_id or not hasattr(exchange, "get_order_by_id"):
        return fallback_price, fallback_qty

    price = fallback_price
    qty = fallback_qty
    for _attempt in range(max_attempts):
        try:
            polled = await exchange.get_order_by_id(sym_ref, order_id)
            state = (polled.get("state") or "").lower()
            acc_fill = float(polled.get("accFillSz") or 0)
            avg_px = float(polled.get("avgPx") or 0)
            if state == "filled" and acc_fill > 0:
                price = avg_px if avg_px > 0 else price
                qty = acc_fill
                logger.info(
                    "ASYNC FILL: ordId=%s state=filled accFillSz=%.8f avgPx=%.2f",
                    order_id, acc_fill, avg_px,
                )
                return price, qty
        except Exception as poll_e:
            logger.warning(f"ASYNC FILL: poll failed for ordId={order_id}: {poll_e}")
        await asyncio.sleep(sleep_sec)

    logger.warning(
        "ASYNC FILL: ordId=%s non confermato filled dopo %.1fs — uso fallback calcolato",
        order_id, max_attempts * sleep_sec,
    )
    return price, qty


async def _broadcast_position_update(session: dict, event) -> None:
    """Broadcast position_update su ogni candela chiusa (post ciclo decisione).

    Aggiorna la position card in tempo reale: PnL, prezzo corrente, SL/TP reali
    piazzati su OKX, break-even e trailing. Estratto dal ciclo candela così gira
    anche quando la sessione è in pausa (il vecchio `continue` saltava sia il
    broadcast sia il log CYCLE END, rendendo i log confusi).
    """
    try:
        pm = _execution_state["position_manager"]
        pos = pm.get_open()
        if pos:
            current_price_f = float(event.close)
            entry_f = float(pos.entry_price)
            qty_f = float(pos.quantity)
            entry_val = entry_f * qty_f
            current_val = current_price_f * qty_f
            gross_pnl = (current_price_f - entry_f) * qty_f if pos.side == "BUY" else (entry_f - current_price_f) * qty_f

            # TASK-882: Usa fee tier per PnL non realizzato (Caso B)
            # Entry: commissione reale se disponibile da WebSocket, altrimenti fee tier
            if pos.entry_commission is not None and pos.entry_commission > 0:
                entry_commission = float(pos.entry_commission)
                # Converti BNB to USDC se necessario
                exchange = _execution_state.get("exchange")
                if pos.entry_commission_asset == "BNB" and exchange:
                    entry_commission = await _convert_bnb_commission_to_usdc(
                        exchange, entry_commission, context="Position update (loop): "
                    )
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

            risk_cfg = _execution_state.get("risk_config", {})
            _sl_cfg = float(risk_cfg.get("stop_loss_pct", 0.3))
            _tp_cfg = float(risk_cfg.get("take_profit_pct", 0.5))
            _ft3 = _execution_state.get("fee_tier", {"maker": 0.001, "taker": 0.001})
            _ef3, _xf3 = _get_fee_rate(_ft3, "taker", 0.001), _get_fee_rate(_ft3, "taker", 0.001)
            # TASK-1127: Fees are now positive for base level accounts
            sl_price = _sl_price_from_entry(entry_f, pos.side, _sl_cfg, _ef3, _xf3)[0]
            tp_price = entry_f * (1 + _net_to_gross_pct(_tp_cfg, _ef3, _xf3) / 100) if pos.side == "BUY" else entry_f * (1 - _net_to_gross_pct(_tp_cfg, _ef3, _xf3) / 100)
            # TASK-1129: usa i veri prezzi TP/SL piazzati su OKX se disponibili
            # (fallback al ricalcolo da percentuali per posizioni pre-fix / restore).
            if pos.sl_price is not None and float(pos.sl_price) > 0:
                sl_price = float(pos.sl_price)
            if pos.tp_price is not None and float(pos.tp_price) > 0:
                tp_price = float(pos.tp_price)

            # TASK-885: Target netti TP/SL = netto effettivo ai prezzi reali piazzati.
            # take_profit_pct/stop_loss_pct nel config sono GIÀ target netti (il prezzo
            # deriva da _net_to_gross_pct/_sl_price_from_entry), quindi NON si sottraggono
            # di nuovo le fee (doppio conto). Si ricalcola dal prezzo reale TP/SL.
            fee_tier = _execution_state.get("fee_tier", {"maker": 0.001, "taker": 0.001})
            entry_fee_rate = _get_fee_rate(fee_tier, "taker", 0.001)  # market order = taker
            exit_fee_rate = _get_fee_rate(fee_tier, "taker", 0.001)  # OKX OCO = market order (taker)

            sl_pct_net = round(_expected_net_pct_at_exit(entry_f, sl_price, pos.side, entry_fee_rate, exit_fee_rate), 2)
            tp_pct_net = round(_expected_net_pct_at_exit(entry_f, tp_price, pos.side, entry_fee_rate, exit_fee_rate), 2)

            # Calculate progress percentage:
            # -100% = at SL, 0% = at entry, +100% = at TP
            if pos.side == "BUY":
                total_range = tp_price - sl_price
                current_offset = current_price_f - entry_f  # positive if above entry
            else:
                total_range = sl_price - tp_price
                current_offset = entry_f - current_price_f  # positive if below entry

            progress_pct = 0.0
            if total_range > 0:
                if pos.side == "BUY":
                    # How far from entry towards TP or SL
                    if current_price_f >= entry_f:
                        progress_pct = ((current_price_f - entry_f) / (tp_price - entry_f)) * 100
                    else:
                        progress_pct = -((entry_f - current_price_f) / (entry_f - sl_price)) * 100
                else:
                    if current_price_f <= entry_f:
                        progress_pct = ((entry_f - current_price_f) / (entry_f - tp_price)) * 100
                    else:
                        progress_pct = -((current_price_f - entry_f) / (sl_price - entry_f)) * 100

            # Clamp to [-100, 100]
            progress_pct = max(-100.0, min(100.0, progress_pct))

            # TASK-1243: Break-even profit lock — valuta il trigger su candela chiusa.
            # Eseguito PRIMA del broadcast così position_update porta già il nuovo SL.
            # No-op se feature flag off, posizione paper, o già attivato.
            await _check_and_apply_break_even(pos, current_price_f, session)

            # TASK-1246: Trailing stop progressivo — eseguito dopo il break-even.
            # No-op se break_even_triggered=False o trailing_enabled=False.
            await _check_and_apply_trailing(pos, current_price_f, session)

            # Rilegge sl_price dopo eventuale amend (potrebbe essere cambiato)
            if pos.sl_price is not None and float(pos.sl_price) > 0:
                sl_price = float(pos.sl_price)

            await broadcast_scalping_event("position_update", {
                "symbol": pos.symbol,
                "side": pos.side,
                "entry_price": entry_f,
                "current_price": round(current_price_f, 2),
                "quantity": qty_f,
                "trade_value_usd": round(qty_f * entry_f, 2),
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl_pct, 2),
                "stop_loss_price": round(sl_price, 2),
                "take_profit_price": round(tp_price, 2),
                "stop_loss_pct": float(risk_cfg.get("stop_loss_pct", 0.3)),
                "take_profit_pct": float(risk_cfg.get("take_profit_pct", 0.5)),
                "stop_loss_pct_net": round(sl_pct_net, 2),  # TASK-885
                "take_profit_pct_net": round(tp_pct_net, 2),  # TASK-885
                "progress_pct": round(progress_pct, 1),         # -100 to +100
                "sl_distance_pct": round(max(0, (entry_f - current_price_f) / (entry_f - sl_price) * 100) if pos.side == "BUY" and (entry_f - sl_price) > 0 else 0, 1),
                "tp_distance_pct": round(min(100, (current_price_f - entry_f) / (tp_price - entry_f) * 100) if pos.side == "BUY" and (tp_price - entry_f) > 0 else 0, 1),
                "breakeven_pct": round((_get_fee_rate(fee_tier, "taker", 0.001) + _get_fee_rate(fee_tier, "taker", 0.001)) * 100, 2),
                # TASK-1243: profit lock state per frontend
                "profit_lock_active": pos.break_even_triggered,
                "profit_lock_sl_price": round(float(pos.break_even_sl_price), 4) if pos.break_even_sl_price else None,
                # TASK-1247: trailing step + SL net % effettivo (dopo eventuale amend)
                "trailing_step": pos.trailing_step,
                "sl_net_pct": round(_expected_net_pct_at_exit(entry_f, sl_price, pos.side, _ef3, _xf3), 2),
                # TASK-1249: step di trailing rimanenti per le barrette UI
                "trailing_steps": _compute_trailing_step_levels(pos, risk_cfg, fee_tier),
            })
            logger.debug(f"Position update broadcast @ {current_price_f}: PnL={pnl:.2f} ({pnl_pct:.2f}%) progress={progress_pct:.1f}%")
    except Exception as e:
        logger.error(f"Error in position broadcast: {e}")
    else:
        logger.debug(f"[Candle] LIVE update (not closed): {event.symbol} close={event.close}")


async def _stop_session_on_risk_limit(code: str, total_pnl: float, limit_pct: float):
    """Stop the session immediately when a risk limit is breached."""
    session = _execution_state["session"]
    session["status"] = "idle"
    session["stopped_at"] = datetime.now(timezone.utc).isoformat()

    # Close exchange connection
    exchange = _execution_state.get("exchange")
    if exchange:
        try:
            asyncio.create_task(exchange.close(), name="close_exchange_risk")
        except Exception as e:
            logger.warning(f"Failed to close exchange on risk stop: {e}")
        _execution_state["exchange"] = None

    # Update DB
    try:
        db_sid = session.get("db_session_id")
        if db_sid:
            closed = [t for t in _execution_state.get("trade_history", []) if t.get("exit_price") is not None]
            total_pnl_val = round(sum((t.get("pnl") or 0) for t in closed), 4)
            win_count_val = len([t for t in closed if (t.get("pnl") or 0) > 0])
            get_supabase().table("scalping_sessions").update({
                "status": "stopped",
                "stopped_at": session["stopped_at"],
                "trade_count": len(closed),
                "win_count": win_count_val,
                "total_pnl": total_pnl_val,
            }).eq("id", db_sid).execute()
    except Exception as e:
        logger.warning(f"Failed to update DB on risk stop: {e}")

    await broadcast_scalping_event("session_restored", {
        **session.copy(),
        "status": "idle",
        "pause_reason": code,
        "pause_message": f"Sessione fermata: {code}. PnL: {total_pnl:.2f}€. Limite: {limit_pct}%.",
    })


async def _candle_processor(symbol: str, restore_mode: bool = False):
    """Consume candle_queue and broadcast + feed execution loop.
    
    SAFETY: On first execution, verify the buffer has warmup data.
    If warmup failed (e.g. REST timeout), force-reload candles here
    so the buffer is ready for signal generation.
    """
    _first_candle = True
    _last_event_time = datetime.now(timezone.utc)
    _ws_client_ref = None  # init before loop: assigned inside the body each iteration
    
    session = _execution_state["session"]
    while _execution_state["session"]["status"] != "idle" and (_ws_client_ref is None or not _ws_client_ref._stop_event.is_set()):
        # Refresh client reference from state every iteration in case watchdog restarted it
        _ws_client_ref = _execution_state.get("ws_client")
        if _ws_client_ref is None:
            await asyncio.sleep(0.1)
            continue
        try:
            event = await asyncio.wait_for(_ws_client_ref.candle_queue.get(), timeout=1.0)
            _last_event_time = datetime.now(timezone.utc)
        except asyncio.TimeoutError:
            if _execution_state["session"]["status"] == "idle":
                break
            
            # ── FIX-2026-06-05: Watchdog — check if data is stale ──
            # If no candle received for > 3 minutes, the WS may be stuck.
            # Force-reload historical candles via REST to keep the pipeline alive,
            # and restart the WS client connection.
            stale_seconds = (datetime.now(timezone.utc) - _last_event_time).total_seconds()

            # LOG every 30s when no data received (reduced level: candles arrive via REST poller
            # every ~55s, so this is expected and not an error)
            if 30 <= stale_seconds < 35:
                logger.debug(
                    f"No WS candle data for {stale_seconds:.0f}s for {symbol} — "
                    f"candles arriving via REST poller every ~55s"
                )
            
            if stale_seconds > 180:  # 3 minutes
                logger.warning(
                    f"[Candle] WATCHDOG: No data for {stale_seconds:.0f}s. "
                    f"Force-reloading candles via REST API..."
                )
                _last_event_time = datetime.now(timezone.utc)  # reset to avoid spamming
                
                # Load fresh candles via REST API directly into the buffer
                fresh_candles = []
                try:
                    from app.scalping.backtest.historical_loader import HistoricalLoader
                    loader = HistoricalLoader()
                    fresh_candles = await loader.load_ohlcv(symbol.upper(), interval="1m", limit=100)
                    if fresh_candles:
                        loaded = 0
                        for c in fresh_candles:
                            if hasattr(c, "timestamp") and hasattr(c, "open"):
                                _execution_state.get('loop')._candle_buffer.add(c)
                                loaded += 1
                            await broadcast_scalping_event("candle", {
                                "symbol": symbol,
                                "open": float(c.open),
                                "high": float(c.high),
                                "low": float(c.low),
                                "close": float(c.close),
                                "volume": float(c.volume),
                                "timestamp": c.timestamp.isoformat() if hasattr(c.timestamp, 'isoformat') else str(c.timestamp),
                            })
                        logger.info(f"[Candle] WATCHDOG: Loaded {loaded} fresh candles via REST")
                except Exception as rest_e:
                    logger.error(f"[Candle] WATCHDOG: REST reload failed: {rest_e}")
                
                # TASK-907: Full WS and tasks restart
                try:
                    if not _ws_client_ref._stop_event.is_set():
                        logger.info("[Candle] WATCHDOG: Triggering full WS restart...")
                        
                        async def _full_restart():
                            try:
                                # Stop Vecchio Client (chiude le code)
                                logger.info("[Candle] RESTART: Stopping old client...")
                                await _ws_client_ref.stop()
                                
                                # Ferma Supervisor se presente
                                old_supervisor = _execution_state.get("supervisor_scheduler")
                                if old_supervisor:
                                    old_supervisor.stop()
                                
                                # Cancella vecchi task (incluso me stesso alla fine)
                                logger.info("[Candle] RESTART: Cancelling old tasks...")
                                for t in _execution_state.get("ws_tasks", []):
                                    if t != asyncio.current_task():
                                        t.cancel()
                                
                                await asyncio.sleep(2)

                                if _execution_state["session"]["status"] in ("running", "paused"):
                                    logger.info("[Candle] RESTART: Calling _start_ws_broadcast(restore_mode=True)...")
                                    from app.scalping.pipeline import _start_ws_broadcast
                                    await _start_ws_broadcast(symbol, restore_mode=True)
                                    logger.info("[Candle] RESTART: Full restart completed!")
                                    
                            except Exception as inner_e:
                                logger.error(f"[Candle] RESTART: Failed: {inner_e}")
                        
                        asyncio.create_task(_full_restart(), name="ws-full-restart-watchdog")
                        
                        # Esci da questo `_candle_processor` così muore pulito, il nuovo prenderà il suo posto.
                        break
                except Exception as ws_e:
                    logger.error(f"[Candle] WATCHDOG: WS restart failed: {ws_e}")

                # ── WAKEUP BALANCE CHECK ────────────────────────────────────
                # When the PC resumes from standby, the WS watchdog fires after
                # 3 minutes of stale data. This is the ideal moment to refresh
                # the live balance and detect if Spot funds moved to Earn during
                # the inactive period. If spot balance is zero, auto-pause session.
                if _execution_state["session"].get("mode") == "live":
                    try:
                        logger.info("[Candle] WAKEUP: Refreshing balance after standby...")
                        await _refresh_session_balance()
                        bal = _execution_state["session"].get("live_balance", 0)
                        trade_val = float(_execution_state["session"].get("trade_value", 10.0))
                        if bal is None or bal <= 0 or bal < trade_val:
                            logger.warning(
                                f"\033[91m⚠️ WAKEUP: Spot balance={bal} < trade_value={trade_val}. "
                                f"All funds may be in Earn. Pausing session.\033[0m"
                            )
                            _execution_state["session"]["status"] = "paused"
                            await broadcast_scalping_event("session_restored", {
                                **_execution_state["session"].copy(),
                                "status": "paused",
                                "pause_reason": "SPOT_BALANCE_ZERO",
                                "pause_message": "I tuoi fondi sono in Simple Earn. Spostali su Spot e fai Resume.",
                            })
                        else:
                            logger.info(f"[Candle] WAKEUP: Spot balance OK: {bal}")
                    except Exception as bal_e:
                        logger.warning(f"[Candle] WAKEUP: Balance refresh failed (non-fatal): {bal_e}")
            
            continue

        # SAFETY: On first candle event, check if buffer was properly warmed up.
        # If not (warmup may have failed or buffer instances diverged), 
        # force-load candles directly into the ExecutionLoop's buffer.
        if _first_candle:
            _first_candle = False
            if len(_execution_state.get('loop')._candle_buffer) < 50:
                logger.warning(
                    f"[Candle] SAFETY: buffer has only {len(_execution_state.get('loop')._candle_buffer)} candles. "
                    f"Force-loading warmup data into ExecutionLoop buffer (id={id(_execution_state.get('loop')._candle_buffer)})..."
                )
                try:
                    from app.scalping.backtest.historical_loader import HistoricalLoader
                    loader = HistoricalLoader()
                    past_candles = await loader.load_ohlcv(symbol.upper(), interval="1m", limit=100)
                    if past_candles:
                        for c in past_candles:
                            if hasattr(c, "timestamp") and hasattr(c, "open"):
                                _execution_state.get('loop')._candle_buffer.add(c)
                        logger.info(f"[Candle] SAFETY: Force-loaded {len(past_candles)} candles. Buffer now: {len(_execution_state.get('loop')._candle_buffer)}")
                except Exception as reload_err:
                    logger.error(f"[Candle] SAFETY: Force-load failed: {reload_err}")

        # Broadcast to frontend WS clients
        await broadcast_scalping_event("candle", {
            "symbol": event.symbol,
            "open": event.open,
            "high": event.high,
            "low": event.low,
            "close": event.close,
            "volume": event.volume,
            "timestamp": datetime.fromtimestamp(event.open_time / 1000, tz=timezone.utc).isoformat(),
        })

        # TRACE: log every event to understand flow (debug-only, too noisy for info)
        buf_size = len(_execution_state.get('loop')._candle_buffer) if _execution_state.get('loop')._candle_buffer else -1
        logger.debug(f"[Candle] EVENT: {event.symbol} is_closed={event.is_closed} close={event.close} buffer={buf_size} session_status={_execution_state['session']['status']}")

        # Feed into execution loop for signal generation (only closed candles)
        if event.is_closed:
            guard = _execution_state.get("session_load_guard")
            if guard and not guard.is_ready():
                guard.record_trade_attempt(event.symbol, "candle_processor")
                _sync_session_load_guard()
                continue
            if _execution_state["session"]["status"] != "running":
                # Still process the candle for regime/strategy/signal updates
                # so the supervisor can evaluate and re-activate later.
                # Only skip trade execution and signal DB logging below.
                pass
            
            candle = Candle(
                symbol=event.symbol.upper(),
                open=Decimal(str(event.open)),
                high=Decimal(str(event.high)),
                low=Decimal(str(event.low)),
                close=Decimal(str(event.close)),
                volume=Decimal(str(event.volume)),
                timestamp=datetime.fromtimestamp(event.open_time / 1000, tz=timezone.utc),
                closed=True,
            )
            logger.info(f"{BOLD}{CYAN}[Candle] CYCLE START: {event.symbol} @ {candle.close}{RESET}")
            try:
                decision = await _execution_state.get('loop').process_candle(candle)
                
                # ── COALESCING: track repeated identical decisions ──
                _coalescing = _execution_state.setdefault("_coalescing", {
                    "last_key": None, "count": 0, "db_logged": False
                })
                _dec_key = None
                if decision and not decision.execute:
                    _dec_key = f"{decision.signal_type}:{decision.reason}"
                if _dec_key and _dec_key == _coalescing["last_key"]:
                    _coalescing["count"] += 1
                    # Skip log for repeated decisions (log summary every 10)
                    if _coalescing["count"] % 10 != 0:
                        logger.debug(f"[Candle] REJECTED (x{_coalescing['count']}): {decision.reason}")
                    else:
                        logger.info(f"[Candle] BLOCK x{_coalescing['count']}: {decision.reason}")
                else:
                    # New decision — log summary if there were repetitions
                    if _coalescing["count"] > 1:
                        logger.info(f"[Candle] BLOCK x{_coalescing['count']}: {_coalescing['last_key']}")
                    _coalescing["last_key"] = _dec_key
                    _coalescing["count"] = 1 if _dec_key else 0
                    _coalescing["db_logged"] = False
                    if decision and not decision.execute:
                        logger.debug(f"[Candle] REJECTED: {decision.reason}")
                # Sync actual running strategy to session for frontend display
                if _execution_state.get('loop')._strategy and _execution_state.get('loop')._strategy.name:
                    actual_strategy = _execution_state.get('loop')._strategy.name
                    if session.get("strategy") != actual_strategy:
                        session["strategy"] = actual_strategy
                        logger.info(f"[Candle] SYNC: strategy={actual_strategy}")
                        await broadcast_scalping_event("session_restored", session.copy())
                if decision and decision.execute:
                    pm = _execution_state["position_manager"]
                    
                    # TASK-894/895: initialize signal_log_id before conditional branching
                    # to ensure it's always bound when used for DB persistence below
                    _signal_log_id = None
                    
                    # ── FIX: If already in position, only allow CLOSE signals ──
                    # This prevents BUY/SELL spam while still allowing supervisor
                    # to update parameters and strategies in background.
                    # Non trade signals are kept for supervisor analysis.
                    if pm.has_open() and decision.signal_type != "CLOSE":
                        logger.debug(
                            f"[Candle] SKIP broadcast: {event.symbol} "
                            f"has_open=True, signal_type={decision.signal_type} "
                            f"(keeping for supervisor background analysis)"
                        )
                    else:
                        logger.info(f"{BOLD}{GREEN}[Candle] DECISION APPROVED -> {decision.reason} | confidence={decision.confidence}{RESET}")
                        # TASK-894/895: log decisione execute su session_signal_log, cattura ID per collegamento
                        # TASK-912: usa il flag is_mean_reversion_override per decidere quale logging function chiamare
                        _ms = _execution_state.get('loop')._last_market_score
                        if getattr(decision, 'is_mean_reversion_override', False):
                            # TASK-912: Log mean-reversion override correttamente
                            _signal_log_id = await asyncio.to_thread(
                                log_mean_reversion_decision,
                                session_id=session.get("db_session_id") or session.get("session_id") or "",
                                symbol=event.symbol.upper(),
                                override_reason=decision.reason or "",
                                regime=_execution_state.get('loop')._current_regime.regime if _execution_state.get('loop')._current_regime else "unknown",
                                strategy_type=_execution_state.get('loop')._strategy.name if _execution_state.get('loop')._strategy else "unknown",
                                tech_signal=decision.signal_type,
                                tech_confidence=round(abs(decision.confidence), 3),
                                intel_score=float(_ms.total) if _ms else None,
                                intel_bias=_ms.bias if _ms else None,
                                trend_direction=_ms.trend_direction if _ms else None,
                                trend_value=float(_ms.trend_5m) if _ms and _ms.trend_5m is not None else None,
                            )
                        else:
                            # Logging normale per execute
                            _signal_log_id = await asyncio.to_thread(
                                log_signal_decision,
                                session_id=session.get("db_session_id") or session.get("session_id") or "",
                                symbol=event.symbol.upper(),
                                decision_type="execute",
                                decision_reason=decision.reason,
                                regime=_execution_state.get('loop')._current_regime.regime if _execution_state.get('loop')._current_regime else "unknown",
                                strategy_type=_execution_state.get('loop')._strategy.name if _execution_state.get('loop')._strategy else "unknown",
                                tech_signal=decision.signal_type,
                                tech_confidence=round(abs(decision.confidence), 3),
                                intel_score=float(_ms.total) if _ms else None,
                                intel_bias=_ms.bias if _ms else None,
                                trend_direction=_ms.trend_direction if _ms else None,
                                trend_value=float(_ms.trend_5m) if _ms and _ms.trend_5m is not None else None,
                            )
                        # A signal was generated — broadcast it
                        await broadcast_scalping_event("signal", {
                            "symbol": event.symbol.upper(),
                            "type": decision.signal_type,
                            "price": float(candle.close),
                            "confidence": abs(decision.confidence),
                            "reason": decision.reason,
                        })

                    # ── Risk limit check on every candle (not just on trade entry) ──
                    if _execution_state["trade_history"] and (
                        _check_session_loss() or _check_drawdown()
                    ):
                        risk_cfg = _execution_state.get("risk_config", {})
                        if _check_session_loss():
                            max_pct = risk_cfg.get("session_max_loss_pct", 10)
                            base = float(session.get("trade_value") or session.get("starting_balance") or 0)
                            total_pnl = sum(t.get("pnl") or 0.0 for t in _execution_state["trade_history"])
                            logger.warning(
                                f"SESSION LOSS LIMIT: {total_pnl:.2f}€ "
                                f"(max {max_pct}% of {base:.2f}€). Stopping session."
                            )
                            await _stop_session_on_risk_limit("SESSION_MAX_LOSS", total_pnl, max_pct)
                        else:
                            dd_pct = risk_cfg.get("max_drawdown", 10)
                            logger.warning(f"Max drawdown {dd_pct}% exceeded. Stopping session.")
                            await _stop_session_on_risk_limit("MAX_DRAWDOWN", 0, dd_pct)
                        continue

                    # Simulate trade execution
                    if session["status"] != "running":
                        logger.warning(f"{YELLOW}[Candle] PAUSED: skipping trade execution (status={session['status']}){RESET}")
                        # TASK-1250: anche in pausa aggiorna la position card (PnL, SL/TP
                        # reali, BE/trailing) — il vecchio `continue` saltava tutto.
                        await _broadcast_position_update(session, event)
                        continue
                    side = decision.signal_type
                    logger.info(f"{CYAN}[Candle] TRADE: side={side} has_open={pm.has_open()} session_loss={_check_session_loss()}{RESET}")
                    
                    guard = _execution_state.get("session_load_guard")
                    if guard and not guard.is_ready():
                        guard.record_trade_attempt(event.symbol.upper(), "live_trade_gate")
                        _sync_session_load_guard()
                        await broadcast_scalping_event("warn", {
                            "code": "SESSION_NOT_READY",
                            "reason": guard.monitor_data.get("error", "loading"),
                        })
                        continue

                    if not pm.has_open():


                        # Only BUY signals reach this point (CLOSE/NONE already filtered)
                        if side != "BUY":
                            logger.debug(f"Skipping non-BUY signal: {side}")
                            continue

                        macro = {}
                        try:
                            exchange = _execution_state.get("exchange")
                            if exchange:
                                macro = await exchange.get_btc_macro_context()
                        except Exception as e_mac:
                            logger.warning(f"Failed to fetch macro context for filter: {e_mac}")

                        # TASK-1242: Macro Trend Filter (Fase 2)
                        # Blocca BUY se BTC < EMA20 4h o in forte dump orario
                        if side == "BUY":
                            btc_price = macro.get("btc_price_at_entry", 0.0)
                            ema20_4h = macro.get("btc_ema20_4h", 0.0)
                            change_1h = macro.get("btc_change_1h_pct", 0.0)
                            
                            if ema20_4h > 0 and btc_price < ema20_4h:
                                logger.warning(f"MACRO TREND FILTER: BTC price {btc_price} < EMA20 4h {ema20_4h}. Blocking BUY.")
                                await broadcast_scalping_event("warn", {"code": "MACRO_TREND", "reason": f"BTC ({btc_price}) sotto EMA20 4h ({ema20_4h})"})
                                continue
                                
                            if change_1h < -0.5:
                                logger.warning(f"MACRO TREND FILTER: BTC 1h change {change_1h}% < -0.5%. Blocking BUY.")
                                await broadcast_scalping_event("warn", {"code": "MACRO_TREND", "reason": f"Forte discesa oraria BTC ({change_1h}%)"})
                                continue

                        # --- COMPILE SUPERVISOR CONTEXT ---
                        supervisor_context = {}
                        try:
                            supervisor_context.update(macro)

                            supervisor_context["candlestick_pattern"] = getattr(decision, "ta_patterns", None)
                            supervisor_context["volume_anomaly"] = getattr(decision, "vol_anomaly", False)

                            # TASK-1241: fix regime_classified — ExecutionDecision non ha .regime,
                            # la fonte corretta è _execution_state["loop"]._current_regime.regime
                            _loop = _execution_state.get("loop")
                            _current_regime = getattr(_loop, "_current_regime", None) if _loop else None
                            supervisor_context["regime_classified"] = (
                                _current_regime.regime if _current_regime and hasattr(_current_regime, "regime") else None
                            )

                            supervisor_context["strategy_rejection_reason"] = getattr(decision, "reason", None)
                            supervisor_context["signal_price"] = float(candle.close)

                            # TASK-1241: persist signal_score — _ms è già disponibile in questo scope
                            # (assegnato a L.277 prima del branch is_mean_reversion_override).
                            # _ms è un SignalScore con .total (float -100..+100) e .breakdown (dict per collector).
                            supervisor_context["signal_score"] = float(_ms.total) if _ms else None

                        except Exception as ctx_e:
                            logger.warning(f"Failed to compile supervisor context: {ctx_e}")
                        # ----------------------------------


                        # Mode and trade values
                        _mode = _execution_state["session"].get("mode", "paper")
                        _trade_val = float(_execution_state["session"].get("trade_value", 10.0))
                        
                        if _mode == "live" or settings.exchange_demo:
                            exchange = _execution_state.get("exchange")
                            if not exchange:
                                logger.error("Live mode requested but exchange is not initialized!")
                                continue
                                
                            try:
                                # 1. Get exact symbol filters for precision
                                filters = await exchange.get_symbol_filters(event.symbol.upper())
                                
                                # 2. Compute exact quantity
                                min_notional = float(filters.get("minNotional", 5.0))
                                if _trade_val < min_notional:
                                    logger.warning(f"Trade value {_trade_val} below minNotional {min_notional}, adjusting")
                                    _trade_val = min_notional
                                _qty_raw = _trade_val / float(event.close)
                                step_size = float(filters["stepSize"])
                                _qty_precise = round(math.floor(_qty_raw / step_size) * step_size, 8)
                                
                                # 3. Check real free balance in quote asset BEFORE placing order (TASK-1160)
                                _current_price = float(event.close)
                                _min_qty = float(filters["minQty"])
                                try:
                                    holdings = await exchange.get_holdings()
                                    quote_asset = filters.get("quoteAsset", "EUR")
                                    free_quote = holdings.get(quote_asset, 0.0)

                                    max_qty_by_balance = (free_quote * 0.98) / _current_price
                                    max_qty_floor = max_qty_by_balance - (max_qty_by_balance % step_size)
                                    if _qty_precise > max_qty_floor:
                                        logger.warning(
                                            f"Safety cap: qty_precise={_qty_precise} exceeds available balance "
                                            f"(free={free_quote} * 0.98 / price={_current_price} = {max_qty_floor}). "
                                            f"Capping to {max_qty_floor}"
                                        )
                                        _qty_precise = max_qty_floor

                                    if _qty_precise < _min_qty:
                                        logger.error(
                                            f"Quantity too small after safety cap: {_qty_precise} < {_min_qty}. "
                                            f"Insufficient balance to meet minQty. free_balance={free_quote:.2f}"
                                        )
                                        await broadcast_scalping_event("error", {
                                            "code": "QTY_TOO_SMALL",
                                            "message": f"Trade quantity {_qty_precise} below minimum {_min_qty} even after balance cap. Insufficient balance.",
                                        })
                                        continue

                                    logger.info(
                                        f"LIVE BALANCE: {quote_asset} free={free_quote} "
                                        f"trade_cost={_qty_precise * _current_price:.2f}"
                                    )
                                except Exception as bal_e:
                                    logger.warning(f"Balance check failed (non-blocking): {bal_e}")

                                logger.info(f"LIVE TRADE CALC: symbol={event.symbol}, trade_value={_trade_val}, price={event.close}, qty_raw={_qty_raw}, step_size={step_size}, qty_precise={_qty_precise}, min_qty={filters['minQty']}")
                                
                                if _qty_precise < float(filters["minQty"]):
                                    logger.error(f"Quantity too small: {_qty_precise} < {filters['minQty']} - TRADE BLOCKED")
                                    await broadcast_scalping_event("error", {
                                        "code": "QTY_TOO_SMALL",
                                        "message": f"Trade quantity {_qty_precise} below minimum {filters['minQty']}",
                                    })
                                    continue
                                    
                                # 3. Execute Market Buy
                                from app.execution.exchange_models import MarketOrderRequest, SymbolRef

                                sym_str = event.symbol.upper()
                                sym_ref = SymbolRef.from_okx(sym_str) if "-" in sym_str else SymbolRef.from_compact(sym_str)

                                # side is "BUY" (validated above)
                                # FIX-2026-07-10: Use quote_amount (EUR) instead of quantity (OKB)
                                # for BUY market orders so OKX uses tgtCcy=quote_ccy and calculates
                                # the base quantity respecting its own minSz constraints.
                                # This fixes sCode=51020 "Your order should meet or exceed the minimum order amount."
                                market_request = MarketOrderRequest(
                                    symbol=sym_ref,
                                    side="buy",  # 'buy' o 'sell'
                                    quote_amount=_trade_val,  # OKX calcola la quantità base da sola
                                )
                                market_res = await exchange.place_market_order(market_request)

                                exec_price = float(market_res.average_price or event.close)
                                # TASK-1128 FIX: The market order uses quote_amount (EUR) so the REST
                                # fallback returns sz=20 (EUR input) and accFillSz=0 (not filled yet).
                                # Using market_res.quantity here gives 20 EUR misread as OKB.
                                # Correct fallback: use _qty_precise (pre-calculated base qty).
                                exec_qty = float(market_res.filled) if market_res.filled and float(market_res.filled) > 0 else _qty_precise

                                # Attendi il fill reale prima di piazzare il bracket.
                                # OKX riempie in modo asincrono: senza questo polling il
                                # bracket SELL partirebbe con availBal BTC=0 -> sCode 51008.
                                # Aggiorna exec_price/exec_qty con avgPx/accFillSz reali.
                                exec_price, exec_qty = await _wait_for_fill(
                                    exchange,
                                    sym_ref,
                                    market_res.order_id,
                                    exec_price,
                                    exec_qty,
                                )

                                # TASK-886: commissione reale dell'entry, dalla risposta dell'ordine market
                                entry_commission_real = float(market_res.commission or 0.0)
                                entry_commission_asset_real = market_res.commission_asset

                                # 4. Calculate Risk SL/TP with proper price precision
                                # I valori configurati (stop_loss_pct, take_profit_pct) rappresentano
                                # il risultato NETTO atteso dopo fee. Convertiamo nel movimento di
                                # prezzo LORDO necessario tramite _net_to_gross_pct.
                                risk_cfg = _execution_state.get("risk_config", {})
                                sl_pct_net_cfg = float(risk_cfg.get("stop_loss_pct", 0.3))
                                tp_pct_net_cfg = float(risk_cfg.get("take_profit_pct", 0.5))
                                price_prec = int(filters.get("pricePrecision", 2))

                                fee_tier_pricing = _execution_state.get("fee_tier", {"maker": 0.001, "taker": 0.001})
                                # TASK-1127: Fees are now positive for base level accounts (converted in adapter)
                                entry_fee_pricing = _get_fee_rate(fee_tier_pricing, "taker", 0.001)
                                exit_fee_pricing = _get_fee_rate(fee_tier_pricing, "taker", 0.001)  # OKX OCO = market order (taker)

                                # TASK-1127: SL/TP gross price calculation.
                                # SL: _sl_gross_fraction always returns positive move magnitude
                                # (with high OKX fees _net_to_gross_pct(-sl) can be positive — must use abs).
                                sl_gross_frac = _sl_gross_fraction(sl_pct_net_cfg, entry_fee_pricing, exit_fee_pricing)
                                tp_gross_pct = _net_to_gross_pct(tp_pct_net_cfg, entry_fee_pricing, exit_fee_pricing) / 100

                                # BUY: SL below entry, TP above — SELL: reversed
                                sl_price = _sl_price_from_entry(
                                    exec_price, side, sl_pct_net_cfg,
                                    entry_fee_pricing, exit_fee_pricing, price_prec=price_prec,
                                )[0]
                                tp_price = round(exec_price * (1 + tp_gross_pct), price_prec) if side == "BUY" else round(exec_price * (1 - tp_gross_pct), price_prec)

                                _certified = _execution_state.get('fee_tier_certified', False)
                                logger.info(
                                     f"[NET_PRICING] provider={settings.EXCHANGE_PROVIDER} symbol={event.symbol} entry_taker={entry_fee_pricing} exit_taker={exit_fee_pricing} certified={_certified} | "
                                    f"Target netti: TP={tp_pct_net_cfg}% SL={sl_pct_net_cfg}% | "
                                    f"Lordi al prezzo: TP=+{tp_gross_pct*100:.4f}% SL=-{sl_gross_frac*100:.4f}% | "
                                    f"sl_price={sl_price} tp_price={tp_price} | "
                                    f"fee entry={entry_fee_pricing} exit={exit_fee_pricing}"
                                )
                                if not _certified:
                                    logger.warning(
                                        f"[NET_PRICING] fee_tier_certified=False — fee fallback 0.001/0.001 "
                                        f"(OKX get_trade_fee non raggiunto durante session restore in main.py, "
                                        f"TASK-1235: controlla log startup per conferma fetch)"
                                    )

                                # 5. Place exit bracket (TASK-1107: provider-neutral)
                                bracket_res = None
                                bracket_failed = False
                                try:
                                    from app.execution.exchange_models import ExitBracketRequest, SymbolRef, FeeTier
                                    
                                    # Parse symbol to SymbolRef
                                    sym_str = event.symbol.upper()
                                    sym_ref = SymbolRef.from_okx(sym_str) if "-" in sym_str else SymbolRef.from_compact(sym_str)
                                    
                                    # Build fee tier object for bracket request
                                    fee_tier_obj = FeeTier(
                                        maker=exit_fee_pricing,
                                        taker=entry_fee_pricing,
                                        certified=_execution_state.get("fee_tier_certified", False),
                                        source="execution_state",
                                    )
                                    
                                    # FIX: Use exec_qty from the market order fill (the actual BTC received).
                                    # DO NOT read _balance_from_rest() — that returns the FULL spot balance.
                                    # DO NOT subtract estimated fees — the fee is in EUR (quote ccy) on OKX spot,
                                    # so the full filled BTC amount is available for the bracket.
                                    bracket_qty = round(exec_qty, 8)

                                    bracket_req = ExitBracketRequest(
                                        symbol=sym_ref,
                                        side="sell" if side == "BUY" else "buy",
                                        quantity=bracket_qty,
                                        tp_price=tp_price,
                                        sl_price=sl_price,
                                        entry_order_id=market_res.order_id,
                                        fee_tier=fee_tier_obj,
                                    )
                                    bracket_res = await exchange.place_exit_bracket(bracket_req)
                                except Exception as bracket_e:
                                    logger.error(f"Exit bracket placement FAILED for {event.symbol}: {bracket_e}")
                                    bracket_failed = True

                                if bracket_failed or not bracket_res:
                                    # ── CASO B: BRACKET FALLITO ──
                                    # Market sell di emergenza con qty reale post-fee
                                    logger.error(f"BRACKET_FLOW CASO B: bracket fallito per {event.symbol} — eseguo market sell emergenza")
                                    await _handle_bracket_failed(exchange, event.symbol.upper())
                                    continue  # Nessun salvataggio DB, nessuna apertura posizione

                                # ── CASO A: BRACKET RIUSCITO ──
                                # 3b. Register position AFTER bracket confermato (TASK-827 / TASK-1107)
                                # TASK-886: propaga la commissione reale dell'entry sulla Position
                                pos_obj = pm.open_position(
                                    symbol=event.symbol.upper(),
                                    side=side,
                                    entry_price=Decimal(str(exec_price)),
                                    quantity=Decimal(str(exec_qty)),
                                    entry_commission=entry_commission_real if entry_commission_real > 0 else None,
                                    entry_commission_asset=entry_commission_asset_real,
                                )

                                # Salva bracket IDs sul position object (provider-neutral)
                                pos_obj.oco_order_list_id = str(bracket_res.bracket_id or "")
                                pos_obj.sl_order_id = str(bracket_res.sl_order_id or "")
                                pos_obj.tp_order_id = str(bracket_res.tp_order_id or "")
                                # Legacy fields for backward compat
                                pos_obj.oco_id = bracket_res.bracket_id
                                pos_obj.sl_id = bracket_res.sl_order_id
                                pos_obj.tp_id = bracket_res.tp_order_id

                                # TASK-1129: porta i veri prezzi TP/SL (piazzati sull'exchange
                                # via bracket) anche sull'oggetto in memoria. Altrimenti il
                                # sistema li ricalcola da percentuali e mostra valori sballati.
                                pos_obj.tp_price = Decimal(str(tp_price))
                                pos_obj.sl_price = Decimal(str(sl_price))

                                # Persist open position to DB con tp/sl price e OCO IDs (TASK-825)
                                if supervisor_context:
                                    # Calculate slippage
                                    sig_p = supervisor_context.get("signal_price")
                                    if sig_p and float(sig_p) > 0:
                                        supervisor_context["slippage_pct"] = round(abs(float(exec_price) - sig_p) / sig_p * 100, 4)
                                await _save_open_position_to_db(
                                    pos_obj, session.get("db_session_id"),
                                    tp_price=tp_price, sl_price=sl_price,
                                    supervisor_context=supervisor_context,
                                    signal_log_id=_signal_log_id,
                                )

                                # Avvia UDS singleton post-OCO (TASK-827)
                                await _start_uds_if_needed()

                                # Refresh live balance
                                await _refresh_session_balance()

                                logger.info(
                                    f"\033[92m🎯 EXIT BRACKET ATTIVO: {side} {event.symbol.upper()} @ {exec_price} | TP={tp_price:.2f} | SL={sl_price:.2f} | provider={settings.EXCHANGE_PROVIDER.upper()}\033[0m"
                                )

                                await broadcast_scalping_event("position", {
                                    "symbol": pos_obj.symbol,
                                    "side": pos_obj.side,
                                    "entry_price": float(pos_obj.entry_price),
                                    "current_price": float(candle.close),
                                    "entry_time": pos_obj.entry_time.isoformat(),
                                    "quantity": float(pos_obj.quantity),
                                    "trade_value_usd": round(float(pos_obj.quantity) * float(pos_obj.entry_price), 2),
                                    "pnl": 0.0,
                                    "pnl_pct": 0.0,
                                    "stop_loss_price": round(sl_price, 2),
                                    "take_profit_price": round(tp_price, 2),
                                    "stop_loss_pct": float(risk_cfg.get("stop_loss_pct", 0.3)),
                                    "take_profit_pct": float(risk_cfg.get("take_profit_pct", 0.5)),
                                    "breakeven_pct": round((entry_fee_pricing + exit_fee_pricing) * 100, 2),
                                    # TASK-1247: trailing step (0 all'apertura) + SL net % effettivo
                                    "trailing_step": pos_obj.trailing_step,
                                    "sl_net_pct": round(_expected_net_pct_at_exit(float(pos_obj.entry_price), sl_price, pos_obj.side, entry_fee_pricing, exit_fee_pricing), 2),
                                    # TASK-1249: step di trailing rimanenti per le barrette UI
                                    "trailing_steps": _compute_trailing_step_levels(pos_obj, risk_cfg, fee_tier_pricing),
                                })

                                # Signal to session stop that we need a close on Binance
                                _execution_state["pending_live_close"] = True

                                
                            except Exception as live_e:
                                # TASK-908: log body completo eccezione Binance
                                from app.execution.exchange import ExchangeOrderError
                                if isinstance(live_e, ExchangeOrderError):
                                    # TASK-908: extract preserved original details
                                    error_detail = str(live_e)
                                    if live_e.original_details:
                                        error_detail = f"{error_detail} | Original: {live_e.original_details}"
                                    if live_e.original_exception:
                                        error_detail += f" | Exception: {type(live_e.original_exception).__name__}"
                                else:
                                    error_detail = f"{type(live_e).__name__}: {live_e}"
                                logger.error(f"Live trade failed: {error_detail}")
                                # TASK-894: log execution_error su session_signal_log (non-blocking)
                                asyncio.create_task(asyncio.to_thread(
                                    log_execution_error,
                                    session_id=session.get("db_session_id") or session.get("session_id") or "",
                                    symbol=event.symbol.upper(),
                                    error_message=error_detail,
                                    regime=_execution_state.get('loop')._current_regime.regime if _execution_state.get('loop')._current_regime else "unknown",
                                    strategy_type=_execution_state.get('loop')._strategy.name if _execution_state.get('loop')._strategy else "unknown",
                                    tech_signal=side,
                                ))
                                await broadcast_scalping_event("error", {
                                    "code": "LIVE_TRADE_ERROR",
                                    "message": f"Live trade failed: {error_detail}",
                                })
                                continue
                        
                        else:
                            # Paper mode
                            _qty = Decimal(str(round(_trade_val / float(event.close), 6)))
                            pos_obj = pm.open_position(
                                symbol=event.symbol.upper(),
                                side=side,
                                entry_price=Decimal(str(event.close)),
                                quantity=_qty,
                            )
                            # Persist open position to DB immediately
                            if supervisor_context:
                                sig_p = supervisor_context.get("signal_price")
                                if sig_p and float(sig_p) > 0:
                                    supervisor_context["slippage_pct"] = round(abs(float(event.close) - sig_p) / sig_p * 100, 4)
                            await _save_open_position_to_db(pos_obj, session.get("db_session_id"), supervisor_context=supervisor_context, signal_log_id=_signal_log_id)
                            
                            # Update paper balance to reflect Free Balance
                            session["paper_balance"] -= float(_trade_val)
                            await broadcast_scalping_event("session_restored", session.copy())
                            await broadcast_scalping_event("position", {
                                "symbol": pos_obj.symbol,
                                "side": pos_obj.side,
                                "entry_price": float(pos_obj.entry_price),
                                "current_price": float(candle.close),
                                "entry_time": pos_obj.entry_time.isoformat(),
                                "quantity": float(pos_obj.quantity),
                                "trade_value_usd": round(float(pos_obj.quantity) * float(pos_obj.entry_price), 2),
                                "pnl": 0.0,
                                "pnl_pct": 0.0,
                                "breakeven_pct": round((_get_fee_rate(_execution_state.get("fee_tier", {}), "taker", 0.001) + _get_fee_rate(_execution_state.get("fee_tier", {}), "maker", 0.001)) * 100, 2),
                            })
                            logger.info(f"{GREEN}[Candle] TRADE EXECUTED: {side} {event.symbol.upper()} @ {candle.close}{RESET}")
                    else:
                        # If opposite signal, close position
                        pos = pm.get_open()
                        if pos.side.lower() != side.lower():
                            logger.info(f"{YELLOW}[Candle] CLOSING: {pos.side} position opposite to {side} signal{RESET}")
                            await _close_position_and_record(pm, float(candle.close), pos, reason=decision.reason or "signal")
                        else:
                            logger.info(f"{DIM}[Candle] HOLD: existing {pos.side} position matches {side} signal{RESET}")
                            # TASK-894: log hold su session_signal_log (non-blocking)
                            _ms = _execution_state.get('loop')._last_market_score
                            asyncio.create_task(asyncio.to_thread(
                                log_hold_decision,
                                session_id=session.get("db_session_id") or session.get("session_id") or "",
                                symbol=event.symbol.upper(),
                                hold_reason=f"existing {pos.side} position matches {side} signal",
                                regime=_execution_state.get('loop')._current_regime.regime if _execution_state.get('loop')._current_regime else "unknown",
                                strategy_type=_execution_state.get('loop')._strategy.name if _execution_state.get('loop')._strategy else "unknown",
                                tech_signal=side,
                                intel_score=float(_ms.total) if _ms else None,
                                intel_bias=_ms.bias if _ms else None,
                                trend_direction=_ms.trend_direction if _ms else None,
                                trend_value=float(_ms.trend_5m) if _ms and _ms.trend_5m is not None else None,
                            ))

                else:
                    reason_str = decision.reason if decision else "decision=None"
                    # ── COALESCING: skip DB log for repeated identical decisions ──
                    _is_repeat = (
                        _coalescing.get("last_key")
                        and _coalescing["count"] > 1
                        and decision
                        and not decision.execute
                        and f"{decision.signal_type}:{decision.reason}" == _coalescing["last_key"]
                    )
                    if not _is_repeat:
                        logger.info(f"{RED}[Candle] DECISION REJECTED: {reason_str}{RESET}")
                        # TASK-894: log rejected su session_signal_log (non-blocking)
                        if decision and session.get("db_session_id") and not _coalescing.get("db_logged"):
                            _ms = _execution_state.get('loop')._last_market_score
                            # Determina decision_type più specifico dal reason
                            _dtype = "rejected_other"
                            if decision.signal_type == "HOLD":
                                _dtype = "hold_existing_position"
                            elif decision.reason and "conflitto intelligence-tecnico" in decision.reason:
                                _dtype = "block_conflict"
                            elif decision.reason and "MEAN-REVERSION" in decision.reason:
                                _dtype = "mean_reversion_override"
                            asyncio.create_task(asyncio.to_thread(
                                log_signal_decision,
                                session_id=session.get("db_session_id") or "",
                                symbol=event.symbol.upper(),
                                decision_type=_dtype,
                                decision_reason=decision.reason,
                                regime=_execution_state.get('loop')._current_regime.regime if _execution_state.get('loop')._current_regime else "unknown",
                                strategy_type=_execution_state.get('loop')._strategy.name if _execution_state.get('loop')._strategy else "unknown",
                                tech_signal=decision.signal_type or None,
                                intel_score=float(_ms.total) if _ms else None,
                                intel_bias=_ms.bias if _ms else None,
                                trend_direction=_ms.trend_direction if _ms else None,
                                trend_value=float(_ms.trend_5m) if _ms and _ms.trend_5m is not None else None,
                            ))
                            _coalescing["db_logged"] = True
            except Exception as e:
                logger.warning(f"Execution loop processing error: {e}")
                import traceback
                logger.error(traceback.format_exc())
            finally:
                # TASK-1250: log sempre il CYCLE END, anche sui `continue`
                # (pausa, guard non pronto, session loss, drawdown, errore live).
                logger.info(f"{BOLD}{CYAN}[Candle] CYCLE END: {event.symbol}{RESET}")
            
            await _broadcast_position_update(session, event)
