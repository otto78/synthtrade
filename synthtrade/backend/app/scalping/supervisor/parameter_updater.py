"""Parameter Updater - applica decisioni del supervisor all'ExecutionLoop."""

import logging
from typing import Optional, Callable

from app.scalping.models.supervisor import SupervisorDecision
from app.scalping.engine.execution_loop import ExecutionLoop

logger = logging.getLogger(__name__)


class ParameterUpdater:
    """Applica decisioni del supervisor al loop di esecuzione."""

    def __init__(self, execution_loop: Optional[ExecutionLoop] = None):
        self._loop = execution_loop

    def set_execution_loop(self, loop: ExecutionLoop) -> None:
        """Imposta il reference all'ExecutionLoop."""
        self._loop = loop

    async def apply(self, decision: SupervisorDecision) -> None:
        """Applica una decisione del supervisor."""
        if decision.action == "update_params":
            await self._apply_params(decision.new_params)
        elif decision.action == "change_strategy":
            await self._change_strategy(decision.new_strategy)
        elif decision.action == "pause_trading":
            await self._pause()
        elif decision.action == "resume_trading":
            await self._resume()
        # no_action does nothing

    async def _apply_params(self, new_params: Optional[dict]) -> None:
        """Aggiorna parametri di esecuzione."""
        if not new_params:
            return
        logger.info(f"Updating params: {new_params}")
        # Qui applicheremo ai parametri dell'ExecutionLoop

    async def _change_strategy(self, new_strategy: Optional[str]) -> None:
        """Cambia strategia corrente."""
        if not new_strategy:
            return
        logger.info(f"Changing strategy to: {new_strategy}")
        # Qui cambieremo la strategia nell'ExecutionLoop

    async def _pause(self) -> None:
        """Metti in pausa il trading."""
        logger.warning("Pausing trading per supervisor decision")
        # Implementeremo la logica di pausa

    async def _resume(self) -> None:
        """Riavvia il trading."""
        logger.info("Resuming trading per supervisor decision")
        # Implementeremo la logica di resume