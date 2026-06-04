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
        """Aggiorna parametri di esecuzione e salva su DB."""
        if not new_params:
            return
        logger.info(f"Updating params: {new_params}")
        # Applica i parametri all'ExecutionLoop
        if self._loop:
            self._loop.set_params(new_params)
        
        # Salva i nuovi parametri su DB
        try:
            from app.scalping.router import _execution_state
            db_sid = _execution_state["session"].get("db_session_id")
            if db_sid:
                from app.db.supabase_client import get_supabase
                supabase = get_supabase()
                supabase.table("scalping_sessions") \
                    .update({"strategy_params": new_params}) \
                    .eq("id", db_sid) \
                    .execute()
                logger.info(f"Strategy params saved to DB session {db_sid}")
        except Exception as e:
            logger.warning(f"Failed to save strategy params to DB: {e}")

    async def _change_strategy(self, new_strategy: Optional[str]) -> None:
        """Cambia strategia corrente e salva su DB."""
        if not new_strategy:
            return
        logger.info(f"Changing strategy to: {new_strategy}")
        if self._loop:
            self._loop.set_strategy(new_strategy)
            logger.info(f"Strategy changed successfully in execution loop")
            
            # Salva la nuova strategia nella sessione di memoria
            try:
                from app.scalping.router import _execution_state
                _execution_state["session"]["strategy"] = new_strategy
                logger.info(f"Session strategy updated in memory: {new_strategy}")
                
                # Salva la nuova strategia su DB (colonna strategy + active_strategy)
                db_sid = _execution_state["session"].get("db_session_id")
                if db_sid:
                    from app.db.supabase_client import get_supabase
                    supabase = get_supabase()
                    supabase.table("scalping_sessions") \
                        .update({
                            "strategy": new_strategy,
                            "active_strategy": new_strategy,
                        }) \
                        .eq("id", db_sid) \
                        .execute()
                    logger.info(f"Strategy saved to DB session {db_sid}: {new_strategy}")
            except Exception as e:
                logger.warning(f"Failed to persist strategy change to session: {e}")
        else:
            logger.warning(f"Cannot change strategy: loop not set or missing set_strategy method")

    async def _pause(self) -> None:
        """Metti in pausa il trading."""
        logger.warning("Pausing trading per supervisor decision")
        try:
            from app.scalping.router import _execution_state
            _execution_state["session"]["status"] = "paused"
            logger.info("Trading paused - session status set to 'paused'")
        except Exception as e:
            logger.error(f"Failed to pause trading: {e}")

    async def _resume(self) -> None:
        """Riavvia il trading."""
        logger.info("Resuming trading per supervisor decision")
        try:
            from app.scalping.router import _execution_state
            _execution_state["session"]["status"] = "running"
            logger.info("Trading resumed - session status set to 'running'")
        except Exception as e:
            logger.error(f"Failed to resume trading: {e}")