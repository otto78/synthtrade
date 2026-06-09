"""Supervisor Scheduler - orchestrazione periodica ogni 10 minuti."""

import asyncio
import logging
import time
from typing import Optional, Dict, List

from app.scalping.supervisor.supervisor_client import SupervisorClient
from app.scalping.supervisor.parameter_updater import ParameterUpdater
from app.scalping.engine.execution_loop import ExecutionLoop
from app.scalping.intelligence.signal_score_engine import SignalScoreEngine
from app.scalping.models.supervisor import SupervisorDecision

logger = logging.getLogger(__name__)

# ── Regime → Strategie permesse ─────────────────────────────────────────────
# Impedisce al supervisor AI di assegnare strategie sbagliate per il regime
# corrente. Ad esempio: ema_cross su mercato ranging non produce segnali
# perché lo slope filter blocca tutto (le EMA sono piatte in ranging).
REGIME_ALLOWED_STRATEGIES: Dict[str, List[str]] = {
    "ranging":        ["rsi_bollinger", "momentum_base", "stoch_rsi_bb_squeeze"],
    "volatile":       ["stoch_rsi_bb_squeeze", "momentum_base"],
    "trending_up":    ["ema_cross"],
    "trending_down":  ["ema_cross"],
    "unknown":        ["momentum_base"],
}

# Cooldown tra decisioni drastiche per stabilizzare il sistema (TASK-815)
# Cambiare strategia ogni 1-2 minuti produce instabilità — nessuna strategia ha
# tempo di generare segnali validi. I log mostrano loop rsi_bollinger→ema_cross→rsi_bollinger.
STRATEGY_CHANGE_COOLDOWN = 20 * 60  # 20 minuti in secondi
PARAM_UPDATE_COOLDOWN = 10 * 60     # 10 minuti in secondi


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
        # Cooldown timestamps
        self._last_strategy_change: float = 0.0
        self._last_param_update: float = 0.0

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
        # SAFETY: Check if stopped before starting expensive AI call
        # (prevents race condition where old tick completes after new session starts)
        if not self._running:
            logger.debug("Supervisor tick skipped: scheduler not running")
            return None
            
        snapshot = await self._score_engine.get_snapshot()
        score = await self._score_engine.compute()
        
        # Check again after data collection
        if not self._running:
            logger.debug("Supervisor tick aborted after data collection: scheduler stopped")
            return None
            
        regime = self._loop.regime if self._loop else None

        decision = await self._client.decide(
            symbol=self._symbol,
            snapshot=snapshot,
            regime=regime,
            score=score,
        )
        
        # Final safety check — may have been stopped during the AI call
        if not self._running:
            logger.debug("Supervisor tick aborted after AI call: scheduler stopped")
            return None

        logger.info(
            f"Supervisor decision: action={decision.action} | "
            f"reason={decision.reason} | "
            f"confidence={decision.confidence} | "
            f"bias={decision.market_bias or 'N/A'} | "
            f"signal={decision.primary_signal or 'N/A'} | "
            f"new_strategy={decision.new_strategy} | "
            f"new_params={decision.new_params}"
        )

        # ── Cooldown check: evita cambi strategia/parametri troppo frequenti ──
        # Il supervisor tende a rimbalzare tra strategie (rsi_bollinger↔ema_cross)
        # se ticka ogni minuto su dati che cambiano poco (Fear&Greed fisso a 8).
        # Con cooldown 20min: massimo 3 cambi/ora invece di 20-30.
        now = time.time()
        if decision.action == "change_strategy":
            elapsed = now - self._last_strategy_change
            if elapsed < STRATEGY_CHANGE_COOLDOWN:
                remaining_min = int((STRATEGY_CHANGE_COOLDOWN - elapsed) / 60)
                logger.info(
                    f"⏳ Strategy change cooldown attivo — {remaining_min} min rimanenti. "
                    f"Decisione ignorata (action={decision.action}, new_strategy={decision.new_strategy})"
                )
                return decision  # Ritorna la decisione ma non applica il cambio
            self._last_strategy_change = now

        if decision.action == "update_params":
            elapsed = now - self._last_param_update
            if elapsed < PARAM_UPDATE_COOLDOWN:
                remaining_min = int((PARAM_UPDATE_COOLDOWN - elapsed) / 60)
                logger.info(
                    f"⏳ Param update cooldown attivo — {remaining_min} min rimanenti. "
                    f"Aggiornamento ignorato"
                )
                return decision
            self._last_param_update = now

        # ── Regime validation: impedisce strategie sbagliate per il regime ──
        # Il supervisor AI può alucinare e scegliere ema_cross in ranging.
        # Questa validazione agisce come barriera di sicurezza: se la strategia
        # proposta non è compatibile con il regime corrente, viene ignorata.
        if decision.action == "change_strategy" and decision.new_strategy:
            current_regime = self._loop.regime.regime if self._loop and self._loop.regime else "unknown"
            allowed = REGIME_ALLOWED_STRATEGIES.get(current_regime, ["momentum_base"])
            if decision.new_strategy not in allowed:
                logger.warning(
                    f"⛔ Supervisor ha proposto '{decision.new_strategy}' "
                    f"ma regime={current_regime} (allowed={allowed}) — "
                    f"strategia invariata"
                )
                # Reset del cooldown così il prossimo tick valido non è bloccato
                self._last_strategy_change = 0.0
                return decision  # Non applica il cambio, esce presto

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