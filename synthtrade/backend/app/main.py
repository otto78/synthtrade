import uuid
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import auth, strategies, dashboard, logs, ws, trades, eval as eval_api, pipeline, exchange, monitor
from app.scheduler.jobs import setup_scheduler
from app.core.logging import setup_logging
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("🚀 SynthTrade API starting...")

    # TASK-409: Singleton ExecutionEngine — istanziato una sola volta, condiviso da scheduler e API
    from app.execution.exchange import BinanceExchangeAdapter
    from app.execution.risk_manager import RiskManager, RiskConfig
    from app.execution.order_tracker import OrderTracker
    from app.execution.execution_engine import ExecutionEngine

    exchange = BinanceExchangeAdapter(
        api_key=settings.BINANCE_API_KEY,
        secret=settings.BINANCE_SECRET_KEY,
        testnet=settings.BINANCE_TESTNET,
    )
    risk_config = RiskConfig(
        max_concurrent_positions=settings.MAX_CONCURRENT_POSITIONS,
        max_exposure_per_symbol_pct=settings.MAX_EXPOSURE_PER_SYMBOL_PCT,
        max_drawdown_pct=settings.MAX_DRAWDOWN_PCT,
        default_position_size_pct=settings.DEFAULT_POSITION_SIZE_PCT,
        default_stop_loss_pct=settings.DEFAULT_STOP_LOSS_PCT,
        default_take_profit_pct=settings.DEFAULT_TAKE_PROFIT_PCT,
    )
    engine = ExecutionEngine(
        risk_manager=RiskManager(config=risk_config),
        order_tracker=OrderTracker(),
        exchange=exchange,
    )

    # Rende l'engine disponibile via request.app.state.engine
    app.state.engine = engine
    app.state.exchange = exchange

    sched = setup_scheduler(engine=engine)
    sched.start()
    logger.info("✅ ExecutionEngine singleton pronto (testnet=%s)", settings.BINANCE_TESTNET)
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
    # Inject request_id into context for logging
    # Note: simple approach using a filter or contextvars would be better for complex apps
    # but for now we'll just log it here and in the response header
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

app.include_router(auth.router, prefix="/api")
app.include_router(strategies.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(logs.router, prefix="/api")
app.include_router(ws.router, prefix="/api")
app.include_router(trades.router, prefix="/api")
app.include_router(eval_api.router, prefix="/api")
app.include_router(pipeline.router, prefix="/api")
app.include_router(exchange.router, prefix="/api")
app.include_router(monitor.router, prefix="/api")

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
