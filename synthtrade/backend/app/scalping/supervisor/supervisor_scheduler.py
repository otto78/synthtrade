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
        interval_seconds: int = 600,  # 10 minuti
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
        """Imposta il reference all'ExecutionLoop."""
        self._loop = loop
        self._updater.set_execution_loop(loop)

    def start(self) -> None:
        """Avvia lo scheduler."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info(f"Supervisor scheduler started for {self._symbol}")

    def stop(self) -> None:
        """Ferma lo scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("Supervisor scheduler stopped")

    async def _run(self) -> None:
        """Loop principale dello scheduler."""
        while self._running:
            try:
                await self._tick()
            except Exception as e:
                logger.error(f"Supervisor tick error: {e}")
            await asyncio.sleep(self._interval)

    async def run_once(self) -> Optional[SupervisorDecision]:
        """Esegui un singolo ciclo di supervisione (usato dai job scheduler)."""
        return await self._tick()

    async def _tick(self) -> Optional[SupervisorDecision]:
        """Esegui un ciclo di supervisione."""
        # Get market intelligence
        snapshot = await self._score_engine.get_snapshot()
        score = await self._score_engine.compute()

        # Get regime from execution loop if available
        regime = self._loop.regime if self._loop else None

        # Get decision
        decision = await self._client.decide(
            symbol=self._symbol,
            snapshot=snapshot,
            regime=regime,
            score=score,
        )

        logger.info(f"Supervisor decision: {decision.action} ({decision.reason})")

        # Apply decision
        await self._updater.apply(decision)

        # TODO: Save to Supabase supervisor_decisions table
        # await self._save_decision(decision, snapshot, score)