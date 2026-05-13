import logging
from datetime import datetime, UTC
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.core.run_pipeline import run_pipeline
from app.core.market_data import get_current_price
from app.api.ws import manager
from app.config import settings

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def run_pipeline_job() -> None:
    try:
        await run_pipeline()
        logger.info("Pipeline job completed")
    except Exception as e:
        logger.error(f"Pipeline job error: {e}")


async def monitor_positions_job(engine=None) -> None:
    if engine is None:
        return
    try:
        positions = engine.order_tracker.get_open_positions()
        for pos in positions:
            price = get_current_price(pos.symbol)
            await engine.close_position_if_needed(pos, price)
    except Exception as e:
        logger.error(f"Monitor positions job error: {e}")


async def monitor_wrapper(engine=None):
    await monitor_positions_job(engine)


async def heartbeat_job() -> None:
    try:
        await manager.broadcast({
            "type": "heartbeat",
            "timestamp": datetime.now(UTC).isoformat(),
            "status": "ok",
        })
    except Exception as e:
        logger.error(f"Heartbeat job error: {e}")


async def run_active_strategies_job(engine=None) -> None:
    """
    TASK-408: Esegue run_tick() su tutte le strategie ACTIVE.
    """
    if engine is None:
        return
    try:
        from app.db.supabase_client import get_supabase
        from app.execution.strategy_runner import StrategyRunner
        db = get_supabase()
        res = db.table("strategies").select("*").eq("status", "ACTIVE").execute()
        active_strategies = res.data or []
        if not active_strategies:
            return
        runner = StrategyRunner(engine)
        import asyncio
        await asyncio.gather(*[runner.run_tick(s) for s in active_strategies], return_exceptions=True)
        logger.info(f"Active strategies job: {len(active_strategies)} strategie processate")
    except Exception as e:
        logger.error(f"Active strategies job error: {e}")


def setup_scheduler(engine=None) -> AsyncIOScheduler:
    scheduler.add_job(run_pipeline_job, "interval",
                      minutes=settings.SCHEDULER_PIPELINE_INTERVAL_MIN,
                      id="pipeline")
    scheduler.add_job(monitor_wrapper, "interval", args=[engine],
                      seconds=30, id="monitor")
    scheduler.add_job(heartbeat_job, "interval", seconds=10, id="heartbeat")
    scheduler.add_job(run_active_strategies_job, "interval", args=[engine],
                      minutes=settings.SCHEDULER_SIGNAL_INTERVAL_MIN,
                      id="active_strategies")
    return scheduler
