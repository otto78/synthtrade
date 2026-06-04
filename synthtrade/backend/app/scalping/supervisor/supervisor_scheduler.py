"""Supervisor Scheduler - orchestrazione periodica ogni 10 minuti."""

import asyncio
import logging
from typing import Optional

from app.scalping.supervisor.supervisor_client import SupervisorClient
from app.scalping.supervisor.parameter_updater import ParameterUpdater
from app.scalping.engine.execution_loop import ExecutionLoop
from app.scalping.intelligence.signal_score_engine import SignalScoreEngine
from app.scalping.models.supervisor import SupervisorDecision

logger = logging.getLogger(__name__)


class SupervisorScheduler:
    """Scheduler per esecuzione periodica del supervisor AI."""

    def __init__(
        self,
        symbol: str = "BTCUSDT",
        interval_seconds: int = 600,
        client: Optional[SupervisorClient] = None,
        updater: Optional[ParameterUpdater] = None,
        score_engine: Optional[SignalScoreEngine] = None,
    ):
        self._symbol = symbol
        self._interval = interval_seconds
        self._client = client or SupervisorClient()
        self._updater = updater or ParameterUpdater()
        self._score_engine = score_engine or SignalScoreEngine()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._loop: Optional[ExecutionLoop] = None

    def set_execution_loop(self, loop: ExecutionLoop) -> None:
        self._loop = loop
        self._updater.set_execution_loop(loop)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info(f"Supervisor scheduler started for {self._symbol}")

    def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("Supervisor scheduler stopped")

    async def _run(self) -> None:
        while self._running:
            try:
                await self._tick()
            except Exception as e:
                logger.error(f"Supervisor tick error: {e}")
            await asyncio.sleep(self._interval)

    async def run_once(self) -> Optional[SupervisorDecision]:
        return await self._tick()

    async def _tick(self) -> Optional[SupervisorDecision]:
        snapshot = await self._score_engine.get_snapshot()
        score = await self._score_engine.compute()
        regime = self._loop.regime if self._loop else None

        decision = await self._client.decide(
            symbol=self._symbol,
            snapshot=snapshot,
            regime=regime,
            score=score,
        )

        logger.info(
            f"Supervisor decision: action={decision.action} | "
            f"reason={decision.reason} | "
            f"confidence={decision.confidence} | "
            f"bias={decision.market_bias or 'N/A'} | "
            f"signal={decision.primary_signal or 'N/A'} | "
            f"new_strategy={decision.new_strategy} | "
            f"new_params={decision.new_params}"
        )

        await self._updater.apply(decision)

        # Broadcast via WebSocket to frontend
        try:
            from app.scalping.router import broadcast_scalping_event
            now_iso = decision.decided_at.isoformat() if decision.decided_at else None
            
            # Map internal action to standardized string for frontend CSS mapping
            action_map = {
                "update_params": "update_params",
                "change_strategy": "change_strategy",
                "pause_trading": "pause_trading",
                "resume_trading": "resume_trading",
                "no_action": "no_action"
            }
            standard_action = action_map.get(decision.action, decision.action)

            await broadcast_scalping_event("supervisor", {
                "action": standard_action,
                "reason": decision.reason,
                "confidence": decision.confidence,
                "market_bias": decision.market_bias or "neutral",
                "primary_signal": decision.primary_signal or "",
                "new_strategy": decision.new_strategy,
                "new_params": decision.new_params,
                "decided_at": now_iso,
                "timestamp": now_iso,  # Frontend expects this field
            })
            logger.info(f"Supervisor decision broadcasted: action={standard_action}")
        except Exception as broadcast_err:
            logger.warning(f"Could not broadcast supervisor decision to frontend: {broadcast_err}")

        # Save to DB
        try:
            from app.db.supabase_client import get_supabase
            supabase = get_supabase()
            session_id = getattr(self._loop, "session_id", None) if self._loop else None
            supabase.table("supervisor_decisions").insert({
                "session_id": session_id,
                "action": decision.action,
                "reason": decision.reason,
                "confidence": decision.confidence,
                "new_params": decision.new_params,
                "new_strategy": decision.new_strategy,
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to save supervisor decision to DB: {e}")

        return decision