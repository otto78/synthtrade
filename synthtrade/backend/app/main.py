import asyncio
import uuid
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Request
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
    synthtrade_exception_handler
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

        logger.info(
            "Scalping session restored: id=%s symbol=%s mode=%s trade_value=%s",
            session_id,
            _execution_state["session"]["symbol"],
            session_mode,
            _execution_state["session"].get("trade_value"),
        )
        guard.complete_phase("db_phase")
    except Exception as e:
        logger.error(
            "Failed to populate _execution_state from DB session: %s", e, exc_info=True
        )
        guard.fail(f"restore_state_failed: {type(e).__name__}: {e}")

    # Step 6 — Check for open positions FIRST (before balance check)
    # Balance check can fail if we already hold the base asset from a previous BUY
    has_open_position = False
    if session_mode == "live":
        try:
            from app.execution.exchange import BinanceExchangeAdapter
            from app.config import settings as app_settings

            api_key = app_settings.BINANCE_API_KEY_LIVE or app_settings.BINANCE_API_KEY
            api_secret = app_settings.BINANCE_SECRET_KEY_LIVE or app_settings.BINANCE_SECRET_KEY
            if api_key and api_secret:
                adapter = BinanceExchangeAdapter(api_key, api_secret, testnet=False)
                _execution_state["exchange"] = adapter

                symbol = _execution_state["session"]["symbol"]
                from app.scalping.router import _get_spot_balances_from_info

                ccxt_balance = await adapter.client.fetch_balance()
                spot_balances = _get_spot_balances_from_info(ccxt_balance)

                filters = await adapter.get_symbol_filters(symbol)
                base_asset = filters.get("baseAsset", "")
                min_qty = float(filters.get("minQty", 0.001))

                total_bal = float(ccxt_balance.get("total", {}).get(base_asset, 0))

                # Check if we have an open trade in DB for this symbol
                def _db_op_open():
                    return db.table("scalping_trades") \
                        .select("*") \
                        .eq("session_id", session_id) \
                        .eq("status", "open") \
                        .limit(1) \
                        .execute()
                open_trades = await asyncio.to_thread(_db_op_open)
                if open_trades.data:
                    ot = open_trades.data[0]
                    symbol_ot = ot.get("symbol", symbol)
                    side = ot.get("side", "BUY")
                    entry_price = ot.get("entry_price", 0)
                    quantity = ot.get("quantity", 0)
                    if entry_price and quantity and entry_price > 0 and quantity > 0:
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
                        has_open_position = True
                        logger.info(
                            "Open position restored from DB during startup: %s %s @ %s qty=%s",
                            side, symbol_ot, entry_price, quantity,
                        )
        except Exception as e:
            logger.warning(f"Could not check open positions during restore: {e}")

    # Step 6b — Inizializza balance live se la modalità è live
    if session_mode == "live":
        try:
            adapter = _execution_state.get("exchange") or BinanceExchangeAdapter(
                app_settings.BINANCE_API_KEY_LIVE or app_settings.BINANCE_API_KEY,
                app_settings.BINANCE_SECRET_KEY_LIVE or app_settings.BINANCE_SECRET_KEY,
                testnet=False,
            )
            if not _execution_state.get("exchange"):
                _execution_state["exchange"] = adapter

            symbol = _execution_state["session"]["symbol"]
            from app.scalping.router import _normalize_binance_total_balance, _select_preferred_quote_balance

            ccxt_balance = await adapter.client.fetch_balance()
            spot_balances = _get_spot_balances_from_info(ccxt_balance)
            normalized = _normalize_binance_total_balance(spot_balances)

            filters = await adapter.get_symbol_filters(symbol)
            quote = filters.get("quoteAsset", "USDT")
            live_bal = _select_preferred_quote_balance(normalized, quote)

            if has_open_position:
                # Skip balance check - we have an open position
                _execution_state["session"]["status"] = "running"
                _execution_state["session"]["live_balance"] = live_bal or 0
                _execution_state["session"]["paper_balance"] = live_bal or 0
                logger.info("Live balance noted (position already open): %s %s", live_bal, quote)
                guard.complete_phase("exchange_phase")
            else:
                # No open position - balance check applies
                trade_val = float(_execution_state["session"].get("trade_value", 10.0))
                if live_bal is not None and live_bal > 0 and live_bal >= trade_val:
                    _execution_state["session"]["live_balance"] = live_bal
                    _execution_state["session"]["paper_balance"] = live_bal
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

# Step 7 — Restore open position from DB (if any trade with status='open' exists)
    # Skip if we already restored in Step 6 (has_open_position is True)
    if not has_open_position:
        try:
            def _db_op4():
                return db.table("scalping_trades") \
                    .select("*") \
                    .eq("session_id", session_id) \
                    .eq("status", "open") \
                    .limit(1) \
                    .execute()
            open_trades = await asyncio.to_thread(_db_op4)
            if open_trades.data:
                ot = open_trades.data[0]
                side = ot.get("side", "BUY")
                entry_price = ot.get("entry_price", 0)
                quantity = ot.get("quantity", 0)
                symbol = ot.get("symbol", _execution_state["session"]["symbol"])
                if entry_price and quantity and entry_price > 0 and quantity > 0:
                    # Verify the position actually exists on the exchange
                    verified = True
                    if session_mode == "live" and _execution_state.get("exchange"):
                        try:
                            adapter = _execution_state["exchange"]
                            filters = await adapter.get_symbol_filters(symbol)
                            base_asset = filters.get("baseAsset", "")
                            ccxt_bal = await adapter.client.fetch_balance()
                            free_bal = float(ccxt_bal.get("free", {}).get(base_asset, 0))
                            total_bal = float(ccxt_bal.get("total", {}).get(base_asset, 0))
                            min_qty = float(filters.get("minQty", 0.001))

                            if total_bal < min_qty:
                                # Position already closed externally
                                logger.warning(
                                    "Open position %s %s found in DB but exchange balance below minQty. "
                                    "Marking as closed.",
                                    side, symbol,
                                )
                                trade_id = ot.get("id")
                                if trade_id:
                                    def _db_close():
                                        db.table("scalping_trades").update({
                                            "status": "closed",
                                            "exit_price": float(entry_price),
                                            "pnl": 0.0,
                                            "pnl_pct": 0.0,
                                            "exit_time": datetime.now(timezone.utc).isoformat(),
                                            "signal_reason": "stop_loss",
                                        }).eq("id", trade_id).execute()
                                    await asyncio.to_thread(_db_close)
                                verified = False
                            else:
                                logger.info(
                                    "Open position verified on exchange: total_balance=%.6f, free=%.6f %s",
                                    total_bal, free_bal, base_asset,
                                )
                        except Exception as ord_e:
                            logger.warning("Could not verify open orders during restore (non-blocking): %s", ord_e)

                    if verified:
                        from decimal import Decimal
                        pm = _execution_state["position_manager"]
                        pos_obj = pm.open_position(
                            symbol=symbol,
                            side=side,
                            entry_price=Decimal(str(entry_price)),
                            quantity=Decimal(str(quantity)),
                        )
                        pos_obj.oco_order_list_id = ot.get("oco_order_list_id")
                        pos_obj.sl_order_id = ot.get("sl_order_id")
                        pos_obj.tp_order_id = ot.get("tp_order_id")
                        logger.info(
                            "Open position restored from DB: %s %s @ %s qty=%s",
                            side, symbol, entry_price, quantity,
                        )
        except Exception as e:
            logger.error("Failed to restore open position from DB: %s", e, exc_info=True)
            guard.fail(f"restore_position_failed: {type(e).__name__}: {e}")

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
    from app.execution.exchange import BinanceExchangeAdapter
    from app.execution.risk_manager import RiskManager, RiskConfig
    from app.execution.order_tracker import OrderTracker
    from app.execution.execution_engine import ExecutionEngine
    from app.execution.signal_resolver import DefaultSignalResolver
    from app.services.stop_loss_service import StopLossService
    from app.db.repositories.trade_repository import TradeRepository
    from app.db.supabase_client import get_supabase

    db = get_supabase()
    trade_repo = TradeRepository(db)

    exchange = BinanceExchangeAdapter(
        api_key=settings.binance_api_key,
        secret=settings.binance_secret_key,
        testnet=settings.TRADING_MODE == 'test',
    )
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
    sched.start()
    logger.info("ExecutionEngine singleton ready (testnet=%s)", settings.BINANCE_TESTNET)

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
    print("  Mode      : %s" % ("TESTNET" if settings.BINANCE_TESTNET else "LIVENET"))
    print("  Host      : 0.0.0.0:8000")
    print("  API Docs  : http://0.0.0.0:8000/docs")
    print("  Scheduler : Active")
    print("")
    print("====================================================================")
    print("")

    # --- Restore active scalping session from DB ---
    await _restore_scalping_session(db)

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

    response = await call_next(request)

    process_time = (time.time() - start_time) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{process_time:.2f}ms"

    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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