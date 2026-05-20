import logging
import asyncio
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


async def monitor_pnl_job(engine=None) -> None:
    """
    TASK-415: Monitora P&L live e broadcast su WS.
    Calcola P&L totale per ogni strategia ACTIVE e invia aggiornamenti.
    """
    if engine is None:
        return
    try:
        from app.db.supabase_client import get_supabase
        db = get_supabase()
        # Recupera tutte le strategie ACTIVE
        res = db.table("strategies").select("*").eq("status", "ACTIVE").execute()
        active_strategies = res.data or []
        if not active_strategies:
            return

        # Calcola P&L per ogni strategia
        for strategy in active_strategies:
            strategy_id = strategy["id"]
            # Recupera trade OPEN per questa strategia
            trades_res = db.table("trades").select("*").eq("strategy_id", strategy_id).eq("status", "OPEN").execute()
            open_trades = trades_res.data or []

            if not open_trades:
                continue

            # Calcola P&L totale
            total_pnl_pct = 0.0
            total_pnl_eur = 0.0
            initial_capital = float(strategy.get("initial_capital_usdt") or strategy.get("budget_eur") or 100.0)

            for trade in open_trades:
                entry_price = float(trade.get("price", 0))
                qty = float(trade.get("quantity", 0))
                current_price = get_current_price(trade["pair"])
                if trade["action"] == "BUY":
                    pnl_pct = ((current_price - entry_price) / entry_price) * 100
                else:
                    pnl_pct = ((entry_price - current_price) / entry_price) * 100
                pnl_eur = (pnl_pct / 100) * initial_capital
                total_pnl_pct += pnl_pct
                total_pnl_eur += pnl_eur

            avg_pnl_pct = total_pnl_pct / len(open_trades) if open_trades else 0.0
            current_value = initial_capital + total_pnl_eur

            # Broadcast su WS (TASK-414/416)
            await manager.broadcast_strategy_pnl_updated(
                strategy_id=strategy_id,
                current_pnl_pct=total_pnl_pct,
                current_pnl_eur=total_pnl_eur,
                current_value_usdt=current_value
            )

            # Aggiorna DB con current_value
            db.table("strategies").update({
                "current_value_usdt": round(current_value, 2),
            }).eq("id", strategy_id).execute()

        logger.info("Monitor P&L job completed")
    except Exception as e:
        logger.error(f"Monitor P&L job error: {e}")


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
    TASK-429: Gestisce errori exchange e broadcast via WebSocket.
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

        # TASK-429: asyncio.gather con return_exceptions=True
        results = await asyncio.gather(
            *[runner.run_tick(s) for s in active_strategies],
            return_exceptions=True
        )

        # TASK-429: Gestione errori e broadcast per strategie fallite
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                strategy = active_strategies[i]
                strategy_id = strategy["id"]
                error_type = type(result).__name__
                error_message = str(result)

                logger.error(
                    f"[{strategy_id}] Strategy tick failed: {error_type}: {error_message}",
                    exc_info=result
                )

                # Broadcast errore via WebSocket
                try:
                    await manager.broadcast_exchange_error(
                        strategy_id=strategy_id,
                        error_message=error_message or "Unknown error",
                        error_type=error_type
                    )
                except Exception as broadcast_err:
                    logger.warning(f"Failed to broadcast error for {strategy_id}: {broadcast_err}")

        success_count = sum(1 for r in results if not isinstance(r, Exception))
        error_count = sum(1 for r in results if isinstance(r, Exception))
        logger.info(
            f"Active strategies job: {success_count} success, {error_count} errors "
            f"out of {len(active_strategies)} total"
        )
    except Exception as e:
        logger.error(f"Active strategies job error: {e}")


def setup_scheduler(engine=None) -> AsyncIOScheduler:
    scheduler.add_job(run_pipeline_job, "interval",
                      minutes=settings.SCHEDULER_PIPELINE_INTERVAL_MIN,
                      id="pipeline")
    scheduler.add_job(monitor_wrapper, "interval", args=[engine],
                      seconds=settings.SCHEDULER_MONITOR_POSITIONS_INTERVAL_SECONDS, id="monitor")
    scheduler.add_job(heartbeat_job, "interval", 
                      seconds=settings.SCHEDULER_HEARTBEAT_INTERVAL_SECONDS, id="heartbeat")
    scheduler.add_job(run_active_strategies_job, "interval", args=[engine],
                      minutes=settings.SCHEDULER_SIGNAL_INTERVAL_MIN,
                      id="active_strategies")
    scheduler.add_job(monitor_pnl_job, "interval", args=[engine],
                      seconds=settings.SCHEDULER_MONITOR_PNL_INTERVAL_SECONDS, id="monitor_pnl")
    return scheduler
