import asyncio
import uuid
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Callable
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import auth, strategies, dashboard, logs, ws, trades, eval as eval_api, pipeline, exchange, monitor, config_api
# WatchFiles reload uccide la connessione WS Binance in corso, causando
# "unknown" regime e blocchi di pipeline. Disabilitiamo il watch su file
# di moduli runtime per evitare restart forzati durante sessioni live.
# Il flag --reload è gestito da uvicorn args in start.ps1.
from app.scalping.router import router as scalping_router, ws_scalping_router
from app.api import llm_models_api
from app.scheduler.jobs import setup_scheduler
from app.core.logging import setup_logging, reconfigure_uvicorn_loggers
from app.core.exceptions import (
    SynthTradeError,
    global_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    synthtrade_exception_handler,
    _QUIET_ERRORS,
)
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

logger = logging.getLogger(__name__)


async def _restore_scalping_session(db) -> None:
    """
    Tenta di ripristinare una sessione di scalping attiva dal DB all'avvio.
    Ogni step ha il proprio try/except con exc_info=True per rendere visibile
    esattamente dove fallisce, senza inghiottire silenziosamente gli errori.
    """
    try:
        from app.scalping.router import _execution_state
        guard = _execution_state["session_load_guard"]
        guard.reset()
        guard.start_loading()
        _execution_state["session"]["load_guard"] = {
            "blocked_attempts": 0,
            "last_blocked_at": None,
        }
    except Exception as e:
        logger.error("Failed to initialize session load guard during restore: %s", e, exc_info=True)
        return

    # Step 1 — query DB
    try:
        def _db_op1():
            return db.table("scalping_sessions").select("*").eq("status", "running").limit(1).execute()
        result = await asyncio.to_thread(_db_op1)
    except Exception as e:
        logger.error("Failed to query scalping_sessions from DB: %s", e, exc_info=True)
        guard.fail(f"restore_db_query_failed: {type(e).__name__}: {e}")
        return

    if not result.data:
        logger.info("No active scalping session found in DB")
        guard.reset()
        return

    sess = result.data[0]
    session_id   = sess.get("id")
    session_mode = sess.get("mode", "paper").lower()
    global_mode  = getattr(settings, 'TRADING_MODE', 'test')

    logger.info(
        "Found active scalping session in DB: id=%s symbol=%s mode=%s",
        session_id, sess.get("symbol"), session_mode,
    )

    # Step 2 — mode consistency check
    if session_mode != global_mode:
        logger.warning(
            "Skipping session restore: session mode=%s ≠ global mode=%s. "
            "Marking session as stopped to avoid stale state.",
            session_mode, global_mode,
        )
        try:
            def _db_op2():
                db.table("scalping_sessions").update({
                    "status": "stopped",
                    "stopped_at": datetime.utcnow().isoformat()
                }).eq("id", session_id).execute()
            await asyncio.to_thread(_db_op2)
            logger.info("Stale session %s marked as stopped", session_id)
            guard.fail("restore_skipped: session mode does not match global mode")
        except Exception as e:
            logger.error("Failed to mark stale session as stopped: %s", e, exc_info=True)
        return

    # Step 3 — import _execution_state
    try:
        from app.scalping.router import _execution_state
    except Exception as e:
        logger.error(
            "Failed to import _execution_state from app.scalping.router: %s", e, exc_info=True
        )
        return

    # Step 4 — populate state
    try:
        db_trade_value = sess.get("trade_value")

        _execution_state["session"]["session_id"]    = session_id
        _execution_state["session"]["status"]        = "running"
        _execution_state["session"]["mode"]          = session_mode
        _execution_state["session"]["strategy"]      = sess.get("strategy", "scalping_v2")
        _execution_state["session"]["symbol"]        = sess.get("symbol", "BTCUSDT")
        _execution_state["session"]["db_session_id"] = session_id
        _execution_state["session"]["started_at"]    = sess.get("started_at")

        if db_trade_value is not None:
            _execution_state["session"]["trade_value"] = float(db_trade_value)

        # TASK-877: Inizializza fee tier (default per paper trading)
        if session_mode != "live":
            _execution_state["fee_tier"] = {"maker": 0.001, "taker": 0.001}

        logger.info(
            "Scalping session restored: id=%s symbol=%s mode=%s trade_value=%s",
            session_id,
            _execution_state["session"]["symbol"],
            session_mode,
            _execution_state["session"].get("trade_value"),
        )
        guard.complete_phase("db_phase")

        # ── SESSION LOGGING: attach session_id to all logs + start capture ──
        from app.core.logging import SessionContextFilter
        from app.core.session_log_handler import SessionLogHandler
        short_session_id = f"sess_{uuid.uuid4().hex[:8]}"
        SessionContextFilter.set_session_id(short_session_id)
        session_log_handler = SessionLogHandler(
            session_id=short_session_id,
            db_session_id=session_id,
        )
        session_log_handler.symbol = _execution_state["session"]["symbol"]
        session_log_handler.attach()

        def _make_restore_persist_callback(h: SessionLogHandler) -> Callable[[str], None]:
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
                    logger.warning("[LIVE_LOG] Failed to persist logs to DB during restore: %s", e)
            return _save_to_db

        session_log_handler.set_persist_callback(_make_restore_persist_callback(session_log_handler))
        _execution_state["session_log_handler"] = session_log_handler
        logger.info("[LIVE_LOG] Session log capture started for restore %s (db=%s)", short_session_id, session_id)

        _LOG_PERSIST_INTERVAL_SEC = 300
        async def _periodic_log_persist_restore():
            while _execution_state["session"].get("status") == "running":
                await asyncio.sleep(_LOG_PERSIST_INTERVAL_SEC)
                handler = _execution_state.get("session_log_handler")
                if handler and handler.log_count > 0:
                    ok = handler.persist_now()
                    if ok:
                        logger.info("[LIVE_LOG] Periodic persist OK (%d entries)", handler.log_count)
                    else:
                        logger.debug("[LIVE_LOG] Periodic persist skipped (no callback or empty)")

        _persist_task = asyncio.create_task(_periodic_log_persist_restore(), name="log-persist-restore")
        _execution_state["log_persist_task"] = _persist_task

    except Exception as e:
        logger.error(
            "Failed to populate _execution_state from DB session: %s", e, exc_info=True
        )
        guard.fail(f"restore_state_failed: {type(e).__name__}: {e}")

    # Step 6 — Check for open positions FIRST (before balance check)
    # Balance check can fail if we already hold the base asset from a previous BUY
    has_open_position = False
    adapter = None
    base_asset = None
    sym_ref = None
    if session_mode == "live":
        try:
            from app.execution.exchange_factory import build_exchange_adapter
            from app.execution.exchange_models import SymbolRef
            adapter = build_exchange_adapter()
            _execution_state["exchange"] = adapter

            symbol = _execution_state["session"]["symbol"]
            try:
                sym_ref = SymbolRef.from_okx(symbol) if "-" in symbol else SymbolRef.from_compact(symbol)
                rules = await adapter.get_symbol_rules(sym_ref)
                base_asset = rules.symbol.base
                min_qty = float(rules.min_sz)
            except Exception as e:
                logger.warning("Could not get symbol rules during restore: %s", e)
                # Continue with DB check - we still need to reconcile
                sym_ref = SymbolRef.from_compact(symbol)
                base_asset = sym_ref.base
                min_qty = 0.00001  # fallback minimum
        except Exception as e:
            # TASK-1176: live session — adapter failure is critical, log at error level
            logger.error("Could not initialize adapter during restore: %s", e, exc_info=True)

        # Check if we have an open trade in DB for this symbol (BEFORE balance check)
        try:
            def _db_op_open():
                return db.table("scalping_trades") \
                    .select("*") \
                    .eq("session_id", session_id) \
                    .eq("status", "open") \
                    .limit(1) \
                    .execute()
            open_trades = await asyncio.to_thread(_db_op_open)
            if open_trades.data and sym_ref:
                ot = open_trades.data[0]
                symbol_ot = ot.get("symbol", symbol)
                side = ot.get("side", "BUY")
                entry_price = ot.get("entry_price", 0)
                quantity = ot.get("quantity", 0)
                if entry_price and quantity and entry_price > 0 and quantity > 0:
                    # ── Reconcile with exchange BEFORE restoring in memory ──
                    from app.scalping.router import (
                        _reconcile_position_with_exchange,
                        broadcast_scalping_event,
                        _get_fee_rate,
                    )
                    bracket_id = ot.get("exchange_bracket_id") or ot.get("oco_order_list_id")
                    reconcile = await _reconcile_position_with_exchange(
                        symbol=symbol_ot,
                        pos_side=side,
                        entry_price=float(entry_price),
                        quantity=float(quantity),
                        exchange=adapter,
                        bracket_id=bracket_id,
                    )
                    if reconcile is not None:
                        # Position was closed externally on exchange — update DB, skip restore
                        trade_id = ot.get("id")
                        if trade_id:
                            fp = reconcile["fill_price"]
                            gross_pnl = (
                                (fp - float(entry_price)) * float(quantity)
                                if side == "BUY"
                                else (float(entry_price) - fp) * float(quantity)
                            )
                            fee_tier = _execution_state.get("fee_tier", {"maker": 0.001, "taker": 0.001})
                            entry_fee_r = _get_fee_rate(fee_tier, "taker", 0.001)
                            exit_fee_r = _get_fee_rate(fee_tier, "maker", 0.001)
                            total_fees = (
                                (float(entry_price) * float(quantity) * entry_fee_r)
                                + (fp * float(quantity) * exit_fee_r)
                            )
                            pnl = gross_pnl - total_fees
                            pnl_pct = (
                                (pnl / (float(entry_price) * float(quantity))) * 100
                                if float(entry_price) > 0
                                else 0
                            )
                            reason = reconcile["reason"]

                            def _db_close_reconciled():
                                db.table("scalping_trades").update({
                                    "status": "closed",
                                    "exit_price": fp,
                                    "pnl": round(pnl, 2),
                                    "pnl_pct": round(pnl_pct, 2),
                                    "exit_time": datetime.now(timezone.utc).isoformat(),
                                    "signal_reason": reason,
                                }).eq("id", trade_id).execute()
                            await asyncio.to_thread(_db_close_reconciled)

                            await broadcast_scalping_event("position_reconciled_externally", {
                                "symbol": symbol_ot,
                                "side": side,
                                "entry_price": float(entry_price),
                                "exit_price": fp,
                                "quantity": float(quantity),
                                "pnl": round(pnl, 2),
                                "pnl_pct": round(pnl_pct, 2),
                                "source": reconcile["source"],
                                "reason": reason,
                            })
                            logger.info(
                                "[POSITION_RECONCILE] Startup: %s %s closed externally | "
                                "fill=%.4f source=%s reason=%s pnl=%.2f",
                                side, symbol_ot, fp, reconcile["source"], reason, pnl,
                            )
                        # has_open_position stays False — balance check will proceed normally
                    else:
                        # Position confirmed open on exchange — restore in memory
                        from decimal import Decimal
                        pm = _execution_state["position_manager"]
                        pos_obj = pm.open_position(
                            symbol=symbol_ot,
                            side=side,
                            entry_price=Decimal(str(entry_price)),
                            quantity=Decimal(str(quantity)),
                        )
                        pos_obj.oco_order_list_id = ot.get("oco_order_list_id")
                        pos_obj.sl_order_id = ot.get("sl_order_id")
                        pos_obj.tp_order_id = ot.get("tp_order_id")
                        if ot.get("tp_price"):
                            pos_obj.tp_price = Decimal(str(ot["tp_price"]))
                        if ot.get("sl_price"):
                            pos_obj.sl_price = Decimal(str(ot["sl_price"]))
                        # TASK-1187: ripristina entry_order_id (ordId market) e
                        # exchange_bracket_id (algoId OCO) dal DB per tracciabilità
                        # completa e disponibilità nei path di reconcile.
                        if ot.get("exchange_order_id"):
                            pos_obj.entry_order_id = ot["exchange_order_id"]
                        # exchange_bracket_id è la fonte primaria di verità per il reconcile;
                        # oco_order_list_id è il legacy field — usiamo exchange_bracket_id
                        # come override se diverso (record più recenti usano solo exchange_bracket_id).
                        if ot.get("exchange_bracket_id") and not pos_obj.oco_order_list_id:
                            pos_obj.oco_order_list_id = ot["exchange_bracket_id"]
                        has_open_position = True
                        logger.info(
                            "Open position restored from DB during startup: %s %s @ %s qty=%s "
                            "ordId=%s algoId=%s",
                            side, symbol_ot, entry_price, quantity,
                            pos_obj.entry_order_id, pos_obj.oco_order_list_id,
                        )
        except Exception as e:
            logger.warning(f"Could not check open positions during restore: {e}")

    # Step 6b — Inizializza balance live se la modalità è live
    if session_mode == "live":
        try:
            from app.execution.exchange_factory import build_exchange_adapter
            from app.execution.exchange_models import SymbolRef
            adapter = _execution_state.get("exchange") or build_exchange_adapter()
            if not _execution_state.get("exchange"):
                _execution_state["exchange"] = adapter

            symbol = _execution_state["session"]["symbol"]
            sym_ref = SymbolRef.from_okx(symbol) if "-" in symbol else SymbolRef.from_compact(symbol)
            quote = sym_ref.quote
            live_bal = await adapter.get_balance(quote)

            if has_open_position:
                # Skip balance check - we have an open position
                _execution_state["session"]["status"] = "running"
                _execution_state["session"]["live_balance"] = live_bal or 0
                _execution_state["session"]["paper_balance"] = live_bal or 0
                logger.info("Live balance noted (position already open): %s %s", live_bal, quote)
                
                # TASK-877: Recupera fee tier durante restore sessione
                try:
                    fee_tier = await adapter.get_trade_fee(sym_ref)
                    _execution_state["fee_tier"] = fee_tier
                    logger.info(f"✓ Fee tier salvato durante restore: maker={fee_tier.maker}, taker={fee_tier.taker}")
                except Exception as e:
                    logger.warning(f"Impossibile recuperare fee tier durante restore: {e} — uso default 0.001")
                    _execution_state["fee_tier"] = {"maker": 0.001, "taker": 0.001}
                
                guard.complete_phase("exchange_phase")
            else:
                # No open position - balance check applies
                trade_val = float(_execution_state["session"].get("trade_value", 10.0))
                if live_bal is not None and live_bal > 0 and live_bal >= trade_val:
                    _execution_state["session"]["live_balance"] = live_bal
                    _execution_state["session"]["paper_balance"] = live_bal
                    
                    # TASK-877: Recupera fee tier durante restore sessione (no open position)
                    try:
                        fee_tier = await adapter.get_trade_fee(sym_ref)
                        _execution_state["fee_tier"] = fee_tier
                        logger.info(f"✓ Fee tier salvato durante restore: maker={fee_tier.maker}, taker={fee_tier.taker}")
                    except Exception as e:
                        logger.warning(f"Impossibile recuperare fee tier durante restore: {e} — uso default 0.001")
                        _execution_state["fee_tier"] = {"maker": 0.001, "taker": 0.001}
                    logger.info("Live balance restored: %s %s", live_bal, quote)
                else:
                    logger.warning(
                        f"\033[91m⚠️ RESTORE: Spot balance={live_bal} < trade_value={trade_val}. "
                        f"All funds may be in Earn. Stopping session.\033[0m"
                    )
                    _execution_state["session"]["status"] = "stopped"
                    _execution_state["session"]["live_balance"] = None
                    _execution_state["session"]["paper_balance"] = None
                    try:
                        def _db_stop():
                            db.table("scalping_sessions").update({
                                "status": "stopped",
                                "stopped_at": datetime.now(timezone.utc).isoformat()
                            }).eq("id", session_id).execute()
                        await asyncio.to_thread(_db_stop)
                        logger.info("Session %s marked as stopped in DB", session_id)
                    except Exception:
                        pass
                    guard.fail("restore_skipped: insufficient spot balance")
                    return
        except Exception as e:
            logger.error("Failed to initialize exchange adapter during restore: %s", e, exc_info=True)
            guard.fail(f"restore_exchange_failed: {type(e).__name__}: {e}")
            return

    else:
        guard.complete_phase("exchange_phase")

    if session_mode == "live":
        guard.complete_phase("exchange_phase")

    guard.complete_phase("position_phase")

    # Step 7.5 — Carica trade history dal DB
    # Always load trade history, even if session was stopped (for display)
    try:
        def _db_op3():
            return db.table("scalping_trades") \
                .select("*") \
                .eq("session_id", session_id) \
                .order("exit_time", desc=True) \
                .limit(200) \
                .execute()
        db_trades = await asyncio.to_thread(_db_op3)
        if db_trades.data:
            trade_list = []
            for t in db_trades.data:
                # TASK-1180: escludi trade fantasma chiusi al restart precedente
                # (reconciliazione fallita senza fill), appartengono a run passati
                if t.get("signal_reason") == "external_close_unknown_price":
                    continue
                trade_list.append({
                    "symbol": t.get("symbol"),
                    "side": t.get("side"),
                    "entry_price": t.get("entry_price", 0),
                    "exit_price": t.get("exit_price", 0),
                    "quantity": t.get("quantity", 0),
                    "pnl": t.get("pnl", 0),
                    "pnl_pct": t.get("pnl_pct", 0),
                    "timestamp": t.get("exit_time") or t.get("entry_time"),
                    "signal_reason": t.get("signal_reason", ""),
                })
            _execution_state["trade_history"] = trade_list
            logger.info("Restored %d historical trades for session %s", len(trade_list), session_id)
    except Exception as e:
        logger.error("Failed to restore trade history from DB: %s", e, exc_info=True)

    # Step 8 — avvia il pipeline (WS, ExecutionLoop, candle processing)
    # Solo se la sessione non è fermata
    if _execution_state["session"]["status"] != "stopped":
        try:
            restored_symbol = _execution_state["session"]["symbol"].lower()
            _execution_state["session"]["status"] = "running"  # ensure before async task reads it

            from app.scalping.router import _start_ws_broadcast
            task = asyncio.create_task(
                _start_ws_broadcast(restored_symbol, restore_mode=True),
                name=f"scalping-restore-{restored_symbol}",
            )
            task.add_done_callback(lambda t: guard.fail(f"restore_broadcast_failed: {type(t.exception()).__name__}: {t.exception()}") if t.exception() else None)
            logger.info(
                "Scalping pipeline ASYNC START scheduled for %s (restore_mode=True)",
                restored_symbol,
            )
        except Exception as e:
            logger.error(
                "Failed to schedule _start_ws_broadcast for restored session: %s", e, exc_info=True
            )
            guard.fail(f"restore_pipeline_schedule_failed: {type(e).__name__}: {e}")
    else:
        logger.info("Session restore skipped pipeline start: status=stopped (spot balance insufficient)")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    reconfigure_uvicorn_loggers()
    logger.info("SynthTrade API starting...")

    # TASK-409: Singleton ExecutionEngine — istanziato una sola volta, condiviso da scheduler e API
    from app.execution.risk_manager import RiskManager, RiskConfig
    from app.execution.order_tracker import OrderTracker
    from app.execution.execution_engine import ExecutionEngine
    from app.execution.signal_resolver import DefaultSignalResolver
    from app.services.stop_loss_service import StopLossService
    from app.db.repositories.trade_repository import TradeRepository
    from app.db.supabase_client import get_supabase

    db = get_supabase()
    trade_repo = TradeRepository(db)

    from app.execution.exchange_factory import build_exchange_adapter

    exchange = build_exchange_adapter()
    risk_config = RiskConfig.from_settings(settings)
    sl_service  = StopLossService()

    # TASK-217: Iniezione del resolver configurato
    resolver = DefaultSignalResolver(strength_threshold=settings.SIGNAL_STRENGTH_THRESHOLD)

    engine = ExecutionEngine(
        risk_manager=RiskManager(config=risk_config),
        order_tracker=OrderTracker(repo=trade_repo),
        exchange=exchange,
        sl_service=sl_service,
        signal_resolver=resolver,
    )

    app.state.engine   = engine
    app.state.exchange = exchange

    sched = setup_scheduler(engine=engine)
    is_demo = getattr(settings, 'exchange_demo', settings.TRADING_MODE == 'test')
    logger.info("ExecutionEngine singleton ready (demo=%s)", is_demo)

    print("")
    print("====================================================================")
    print("")
    print("   ____             _   _     _____              _      ")
    print("  / ___| _   _ _ __ | |_| |__ |_   _| __ __ _  __| | ___ ")
    print("  \\___ \\| | | | '_ \\| __| '_ \\  | || '__/ _` |/ _` |/ _ \\")
    print("   ___) | |_| | | | | |_| | | | | || | | (_| | (_| |  __/")
    print("  |____/ \\__, |_| |_|\\__|_| |_| |_||_|  \\__,_|\\__,_|\\___|")
    print("         |___/                                            ")
    print("")
    print("  SynthTrade IS RUNNING!!!")
    print("")
    print("  Version   : 0.1.0")
    print("  Mode      : %s" % ("TESTNET" if settings.TRADING_MODE == 'test' else "LIVE"))
    print("  Host      : 0.0.0.0:8000")
    print("  API Docs  : http://0.0.0.0:8000/docs")
    print("")
    print("====================================================================")
    print("")

    # --- Restore active scalping session from DB ---
    await _restore_scalping_session(db)

    # Avvia scheduler solo dopo restore (e warmup pipeline se attivo)
    try:
        from app.scalping.router import _execution_state
        guard = _execution_state.get("session_load_guard")
        if guard and guard.monitor_data.get("state") == "loading":
            logger.info("Waiting for scalping session load guard before starting scheduler...")
            try:
                await asyncio.wait_for(guard._ready_event.wait(), timeout=30.0)
            except asyncio.TimeoutError:
                logger.warning(
                    "Session load guard not ready after 30s — starting scheduler anyway"
                )
    except Exception as e:
        logger.debug("Session load guard wait skipped: %s", e)

    sched.start()
    logger.info("Scheduler started")
    logger.info("Scheduler : Active")

    yield

    sched.shutdown(wait=False)
    await exchange.close()
    logger.info("🛑 SynthTrade API stopped")


app = FastAPI(title="SynthTrade API", version="0.1.0", lifespan=lifespan)

# Exception Handlers (TASK-301, 302, 303)
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SynthTradeError, synthtrade_exception_handler)

# TASK-299: Request ID Middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = time.time()

    try:
        response = await call_next(request)
    except _QUIET_ERRORS as exc:
        logger.warning(f"Transient connection error: {exc} [request_id={request_id}]")
        return JSONResponse(
            status_code=502,
            content={
                "error": "upstream_disconnected",
                "message": "Servizio temporaneamente non disponibile, riprova.",
                "request_id": request_id,
            },
        )

    process_time = (time.time() - start_time) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{process_time:.2f}ms"

    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,        prefix="/api")
app.include_router(strategies.router,  prefix="/api")
app.include_router(dashboard.router,   prefix="/api")
app.include_router(logs.router,        prefix="/api")
app.include_router(ws.router,          prefix="/api")
app.include_router(trades.router,      prefix="/api")
app.include_router(eval_api.router,    prefix="/api")
app.include_router(pipeline.router,    prefix="/api")
app.include_router(exchange.router,    prefix="/api")
app.include_router(monitor.router,     prefix="/api")
app.include_router(config_api.router,  prefix="/api")
app.include_router(llm_models_api.router, prefix="/api")
app.include_router(scalping_router,    prefix="/api")
# Scalping WebSocket — mounted at /ws to match the proxy rule /ws (ws: true)
# which properly handles WS upgrade. Full path: /ws/scalping
app.include_router(ws_scalping_router, prefix="/ws")


@app.get("/")
def read_root():
    return {"message": "SynthTrade API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/scheduler/status")
def scheduler_status():
    from app.scheduler.jobs import scheduler
    jobs = [{"id": j.id, "next_run": str(j.next_run_time)} for j in scheduler.get_jobs()]
    return {"running": scheduler.running, "jobs": jobs}