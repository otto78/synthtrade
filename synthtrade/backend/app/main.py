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
                from app.scalping.router import _normalize_binance_total_balance, _select_preferred_quote_balance, _get_spot_balances_from_info

                ccxt_balance = await adapter.client.fetch_balance()
                spot_balances = _get_spot_balances_from_info(ccxt_balance)
                normalized = _normalize_binance_total_balance(spot_balances)

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
                guard.fail("restore_exchange_failed: missing Binance API keys")
        except Exception as e:
            logger.error("Failed to initialize exchange adapter during restore: %s", e, exc_info=True)
            guard.fail(f"restore_exchange_failed: {type(e).__name__}: {e}")

    else:
        guard.complete_phase("exchange_phase")

    if session_mode == "live":
        guard.complete_phase("exchange_phase")

    # Step 7 — Restore open position from DB (if any trade with status='open' exists)
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
                # (it may have been closed externally, e.g. by SL/TP or manually)
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
                            # Balance totale (free + locked) sotto minQty → OCO già eseguito (asset venduto)
                            logger.warning(
                                "Open position %s %s found in DB but exchange has total %.8f %s "
                                "(below minQty=%.4f). Marking DB trade as closed (position closed externally).",
                                side, symbol, total_bal, base_asset, min_qty,
                            )
                            # Mark the DB trade as closed since the position was closed externally
                            trade_id = ot.get("id")
                            if trade_id:
                                real_exit_price = float(entry_price)
                                pnl = 0.0
                                pnl_pct = 0.0
                                exit_time_str = datetime.now(timezone.utc).isoformat()

                                # TASK-831: usa sl_order_id / tp_order_id specifici salvati in DB
                                # per trovare il fill price preciso (evita di leggere ordini di altre sessioni)
                                sl_order_id_db = ot.get("sl_order_id")
                                tp_order_id_db = ot.get("tp_order_id")
                                try:
                                    fill_price_found = None
                                    for oid in [tp_order_id_db, sl_order_id_db]:
                                        if oid:
                                            fp = await adapter._fetch_fill_price_by_order_id(symbol, oid)
                                            if fp and fp > 0:
                                                fill_price_found = fp
                                                break

                                    if fill_price_found and fill_price_found > 0:
                                        real_exit_price = fill_price_found
                                    else:
                                        # Fallback: cerca negli ordini chiusi recenti
                                        ccxt_symbol = await adapter._get_ccxt_symbol(symbol)
                                        closed_orders = await adapter.client.fetch_closed_orders(ccxt_symbol, limit=20)
                                        close_side = "sell" if side.lower() == "buy" else "buy"
                                        for o in sorted(closed_orders, key=lambda x: x.get("timestamp", 0), reverse=True):
                                            if o.get("status") == "closed" and o.get("side", "").lower() == close_side:
                                                fp = float(o.get("price") or o.get("average") or 0)
                                                if fp > 0:
                                                    real_exit_price = fp
                                                    break

                                    if real_exit_price > 0 and entry_price > 0:
                                        if side.lower() == "buy":
                                            pnl_pct = ((real_exit_price - entry_price) / entry_price) * 100
                                        else:
                                            pnl_pct = ((entry_price - real_exit_price) / entry_price) * 100
                                        trade_val = float(_execution_state["session"].get("trade_value", 10.0) or 10.0)
                                        pnl = (pnl_pct / 100.0) * trade_val

                                except Exception as my_trade_e:
                                    logger.warning(f"Could not fetch fill price during restore: {my_trade_e}")

                                def _db_op5():
                                    db.table("scalping_trades").update({
                                        "status": "closed",
                                        "exit_price": real_exit_price,
                                        "pnl": pnl,
                                        "pnl_pct": pnl_pct,
                                        "exit_time": exit_time_str,
                                        "signal_reason": "take_profit" if pnl > 0 else "stop_loss",
                                    }).eq("id", trade_id).execute()
                                await asyncio.to_thread(_db_op5)
                            verified = False
                        else:
                            # Balance OK → asset ancora in mano.
                            # Verifica ulteriore: se non ci sono open orders su Binance,
                            # l'OCO potrebbe essere eseguito DURANTE il restart
                            # (race: balance non ancora aggiornato ma ordini già eseguiti).
                            try:
                                open_orders = await adapter.get_open_orders(symbol)
                                oco_list_id = ot.get("oco_order_list_id")
                                if not open_orders and oco_list_id:
                                    # Nessun ordine aperto ma balance presente →
                                    # OCO eseguito durante la finestra di restart.
                                    # NON ripristinare la posizione: risolviamo via fill price.
                                    logger.warning(
                                        "Balance OK (total=%.6f, free=%.6f %s) but NO open orders on Binance "
                                        "for OCO %s — OCO eseguito durante restart. "
                                        "Marking as closed.",
                                        total_bal, free_bal, base_asset, oco_list_id,
                                    )
                                    trade_id = ot.get("id")
                                    if trade_id:
                                        real_exit_price = float(entry_price)
                                        pnl = 0.0
                                        pnl_pct = 0.0
                                        exit_time_str = datetime.now(timezone.utc).isoformat()
                                        # Recupera fill price via orderId specifici
                                        for oid in [ot.get("tp_order_id"), ot.get("sl_order_id")]:
                                            if oid:
                                                fp = await adapter._fetch_fill_price_by_order_id(symbol, oid)
                                                if fp and fp > 0:
                                                    real_exit_price = fp
                                                    break
                                        if real_exit_price > 0 and float(entry_price) > 0:
                                            ep = float(entry_price)
                                            pnl_pct = ((real_exit_price - ep) / ep * 100) if side.lower() == "buy" else ((ep - real_exit_price) / ep * 100)
                                            trade_val = float(_execution_state["session"].get("trade_value", 10.0) or 10.0)
                                            pnl = (pnl_pct / 100.0) * trade_val
                                        def _db_op6():
                                            db.table("scalping_trades").update({
                                                "status": "closed",
                                                "exit_price": real_exit_price,
                                                "pnl": pnl,
                                                "pnl_pct": pnl_pct,
                                                "exit_time": exit_time_str,
                                                "signal_reason": "take_profit" if pnl > 0 else "stop_loss",
                                            }).eq("id", trade_id).execute()
                                        await asyncio.to_thread(_db_op6)
                                    verified = False
                                else:
                                    logger.info(
                                        "Open position verified on exchange: total_balance=%.6f, free=%.6f %s, "
                                        "open_orders=%d",
                                        total_bal, free_bal, base_asset, len(open_orders),
                                    )
                            except Exception as ord_e:
                                logger.warning("Could not verify open orders during restore (non-blocking): %s", ord_e)
                    except Exception as bal_e:
                        logger.warning(f"Could not verify position on exchange: {bal_e}")

                if verified:
                    from decimal import Decimal
                    pm = _execution_state["position_manager"]
                    pos_obj = pm.open_position(
                        symbol=symbol,
                        side=side,
                        entry_price=Decimal(str(entry_price)),
                        quantity=Decimal(str(quantity)),
                    )
                    # Ripristina OCO IDs dal DB sul position object (TASK-831)
                    pos_obj.oco_order_list_id = ot.get("oco_order_list_id")
                    pos_obj.sl_order_id = ot.get("sl_order_id")
                    pos_obj.tp_order_id = ot.get("tp_order_id")
                    logger.info(
                        "Open position restored from DB: %s %s @ %s qty=%s oco_list=%s",
                        side, symbol, entry_price, quantity, pos_obj.oco_order_list_id,
                    )
                    # TASK-827: riavvia UDS singleton post-restore se la sessione è live
                    if session_mode == "live":
                        try:
                            from app.scalping.router import _start_uds_if_needed
                            await _start_uds_if_needed()
                        except Exception as uds_e:
                            logger.warning("Could not start UDS after session restore: %s", uds_e)
    except Exception as e:
        logger.error("Failed to restore open position from DB: %s", e, exc_info=True)
        guard.fail(f"restore_position_failed: {type(e).__name__}: {e}")

    guard.complete_phase("position_phase")

    # Step 7.5 — Carica trade history dal DB per popolare la lista trade e performance (DOPO aver chiuso i trade esterni)
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
    # Questo è il passo che mancava: senza, la sessione appare "running" ma non
    # ha alcun flusso dati attivo, nessun trade parte, nessun log del pipeline.
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