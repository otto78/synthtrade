import asyncio
import uuid
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import auth, strategies, dashboard, logs, ws, trades, eval as eval_api, pipeline, exchange, monitor, config_api
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
    # Step 1 — query DB
    try:
        result = db.table("scalping_sessions").select("*").eq("status", "running").limit(1).execute()
    except Exception as e:
        logger.error("Failed to query scalping_sessions from DB: %s", e, exc_info=True)
        return

    if not result.data:
        logger.info("No active scalping session found in DB")
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
            db.table("scalping_sessions").update({
                "status": "stopped",
                "stopped_at": datetime.utcnow().isoformat()
            }).eq("id", session_id).execute()
            logger.info("Stale session %s marked as stopped", session_id)
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
    except Exception as e:
        logger.error(
            "Failed to populate _execution_state from DB session: %s", e, exc_info=True
        )

    # Step 5 — Carica trade history dal DB per popolare la lista trade e performance
    try:
        db_trades = db.table("scalping_trades") \
            .select("*") \
            .eq("session_id", session_id) \
            .order("exit_time", desc=True) \
            .limit(200) \
            .execute()
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

    # Step 6 — Inizializza balance live se la modalità è live
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
                from app.scalping.router import _normalize_binance_total_balance, _select_preferred_quote_balance

                ccxt_balance = await adapter.client.fetch_balance()
                all_balances = ccxt_balance.get("total", {})
                normalized = _normalize_binance_total_balance(all_balances)

                filters = await adapter.get_symbol_filters(symbol)
                quote = filters.get("quoteAsset", "USDT")
                live_bal = _select_preferred_quote_balance(normalized, quote)

                if live_bal is not None and live_bal > 0:
                    _execution_state["session"]["live_balance"] = live_bal
                    _execution_state["session"]["paper_balance"] = live_bal
                    logger.info("Live balance restored: %s %s", live_bal, quote)
                else:
                    logger.warning("No live balance found — keeping previous value")
            else:
                logger.warning("No API keys for live mode — balance not refreshed during restore")
        except Exception as e:
            logger.error("Failed to initialize exchange adapter during restore: %s", e, exc_info=True)

    # Step 7 — Restore open position from DB (if any trade with status='open' exists)
    try:
        open_trades = db.table("scalping_trades") \
            .select("*") \
            .eq("session_id", session_id) \
            .eq("status", "open") \
            .limit(1) \
            .execute()
        if open_trades.data:
            ot = open_trades.data[0]
            side = ot.get("side", "BUY")
            entry_price = ot.get("entry_price", 0)
            quantity = ot.get("quantity", 0)
            symbol = ot.get("symbol", _execution_state["session"]["symbol"])
            if entry_price and quantity and entry_price > 0 and quantity > 0:
                from decimal import Decimal
                pm = _execution_state["position_manager"]
                pos_obj = pm.open_position(
                    symbol=symbol,
                    side=side,
                    entry_price=Decimal(str(entry_price)),
                    quantity=Decimal(str(quantity)),
                )
                logger.info(
                    "Open position restored from DB: %s %s @ %s qty=%s",
                    side, symbol, entry_price, quantity,
                )
    except Exception as e:
        logger.error("Failed to restore open position from DB: %s", e, exc_info=True)

    # Step 8 — avvia il pipeline (WS, ExecutionLoop, candle processing)
    # Questo è il passo che mancava: senza, la sessione appare "running" ma non
    # ha alcun flusso dati attivo, nessun trade parte, nessun log del pipeline.
    try:
        restored_symbol = _execution_state["session"]["symbol"].lower()
        _execution_state["session"]["status"] = "running"  # ensure before async task reads it

        from app.scalping.router import _start_ws_broadcast
        asyncio.create_task(
            _start_ws_broadcast(restored_symbol, restore_mode=True),
            name=f"scalping-restore-{restored_symbol}",
        )
        logger.info(
            "Scalping pipeline ASYNC START scheduled for %s (restore_mode=True)",
            restored_symbol,
        )
    except Exception as e:
        logger.error(
            "Failed to schedule _start_ws_broadcast for restored session: %s", e, exc_info=True
        )


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