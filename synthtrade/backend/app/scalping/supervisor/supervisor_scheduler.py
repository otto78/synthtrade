"""Supervisor Scheduler - orchestrazione periodica ogni 10 minuti."""

import asyncio
import json
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
from app.config import settings
STRATEGY_CHANGE_COOLDOWN = settings.scalping.SCALPING_STRATEGY_COOLDOWN_SEC
PARAM_UPDATE_COOLDOWN = settings.scalping.SCALPING_PARAM_UPDATE_COOLDOWN_SEC
THRESHOLD_CHANGE_COOLDOWN = 1800  # 30 minuti — modifiche soglia meno frequenti di strategia


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
        self._last_threshold_change: float = 0.0
        # Strategia corrente (rilevata dal loop)
        self._current_strategy: Optional[str] = None

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

    async def _save_decision_to_memory(
        self,
        decision: SupervisorDecision,
        was_applied: bool = False,
        blocked_reason: Optional[str] = None,
    ):
        """Salva la decisione del supervisor nella tabella supervisor_memory.

        TASK-847: Persistenza memoria supervisor. Chiamata dopo ogni tick
        con flag was_applied=True/False e blocked_reason se non applicata.
        """
        try:
            from app.db.supabase_client import get_supabase

            session_id = getattr(self._loop, "session_id", None) if self._loop else None
            if not session_id:
                logger.debug("_save_decision_to_memory: no session_id, skipping")
                return

            # Market context snapshot
            regime_name = self._loop.regime.regime if self._loop and self._loop.regime else "unknown"
            market_context = {"regime": regime_name}

            # Session performance snapshot
            session_perf = {}
            try:
                trades = getattr(self._loop, "_execution_state", {}).get("trade_history", []) if hasattr(self._loop, "_execution_state") else []
                if trades:
                    closed = [t for t in trades if t.get("exit_price")]
                    total = len(closed)
                    wins = len([t for t in closed if (t.get("pnl") or 0) > 0])
                    total_pnl = sum((t.get("pnl") or 0) for t in closed)
                    session_perf = {
                        "total_trades": total,
                        "winning_trades": wins,
                        "total_pnl": round(total_pnl, 2),
                    }
            except Exception:
                pass

            def _db_op():
                supabase = get_supabase()
                supabase.table("supervisor_memory").insert({
                    "session_id": session_id,
                    "symbol": self._symbol,
                    "decided_at": decision.decided_at.isoformat() if decision.decided_at else None,
                    "action": decision.action,
                    "reason": decision.reason,
                    "confidence": decision.confidence,
                    "market_bias": decision.market_bias,
                    "primary_signal": decision.primary_signal,
                    "new_strategy": decision.new_strategy,
                    "new_params": json.dumps(decision.new_params) if decision.new_params else None,
                    "was_applied": was_applied,
                    "blocked_reason": blocked_reason,
                    "market_context": json.dumps(market_context),
                    "session_perf": json.dumps(session_perf) if session_perf else None,
                }).execute()

            await asyncio.to_thread(_db_op)
        except Exception as e:
            logger.warning(f"Failed to save supervisor memory: {e}")

    async def _tick(self) -> Optional[SupervisorDecision]:
        # SAFETY: Check if stopped before starting expensive AI call
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

        # Leggi strategia corrente dal loop
        self._current_strategy = self._loop.strategy.name if self._loop and self._loop.strategy else None

        # Recupera session_id dal loop
        session_id = getattr(self._loop, "session_id", None) if self._loop else None

        decision = await self._client.decide(
            symbol=self._symbol,
            snapshot=snapshot,
            regime=regime,
            score=score,
            session_id=session_id,
        )

        # Final safety check
        if not self._running:
            logger.debug("Supervisor tick aborted after AI call: scheduler stopped")
            return None

        logger.debug(
            f"Supervisor decision: action={decision.action} | "
            f"reason={decision.reason} | "
            f"confidence={decision.confidence} | "
            f"bias={decision.market_bias or 'N/A'} | "
            f"signal={decision.primary_signal or 'N/A'} | "
            f"new_strategy={decision.new_strategy} | "
            f"new_params={decision.new_params}"
        )

        # ── Cooldown check ──
        now = time.time()
        blocked_reason = None
        was_applied = True

        if decision.action == "change_strategy":
            elapsed = now - self._last_strategy_change
            if elapsed < STRATEGY_CHANGE_COOLDOWN:
                remaining_min = int((STRATEGY_CHANGE_COOLDOWN - elapsed) / 60)
                logger.info(
                    f"⏳ Strategy change cooldown attivo — {remaining_min} min rimanenti. "
                    f"Decisione ignorata (action={decision.action}, new_strategy={decision.new_strategy})"
                )
                blocked_reason = f"cooldown: {remaining_min} min rimanenti"
                was_applied = False

        if decision.action == "update_params":
            elapsed = now - self._last_param_update
            if elapsed < PARAM_UPDATE_COOLDOWN:
                remaining_min = int((PARAM_UPDATE_COOLDOWN - elapsed) / 60)
                logger.info(
                    f"⏳ Param update cooldown attivo — {remaining_min} min rimanenti. "
                    f"Aggiornamento ignorato"
                )
                blocked_reason = f"cooldown: {remaining_min} min rimanenti"
                was_applied = False

        if decision.action == "update_threshold":
            elapsed = now - self._last_threshold_change
            if elapsed < THRESHOLD_CHANGE_COOLDOWN:
                remaining_min = int((THRESHOLD_CHANGE_COOLDOWN - elapsed) / 60)
                logger.info(
                    f"⏳ Threshold change cooldown attivo — {remaining_min} min rimanenti. "
                    f"Modifica soglia ignorata"
                )
                blocked_reason = f"cooldown: {remaining_min} min rimanenti"
                was_applied = False

        # ── Regime validation ──
        if decision.action == "change_strategy" and decision.new_strategy:
            current_regime = self._loop.regime.regime if self._loop and self._loop.regime else "unknown"
            allowed = REGIME_ALLOWED_STRATEGIES.get(current_regime, ["momentum_base"])
            if decision.new_strategy not in allowed:
                logger.warning(
                    f"⛔ Supervisor ha proposto '{decision.new_strategy}' "
                    f"ma regime={current_regime} (allowed={allowed}) — "
                    f"strategia invariata"
                )
                self._last_strategy_change = 0.0
                blocked_reason = f"regime mismatch: {decision.new_strategy} not in {allowed}"
                was_applied = False

        # Applica la decisione se non bloccata
        if was_applied:
            await self._updater.apply(decision)
        else:
            # Salva in memoria anche se non applicata
            await self._save_decision_to_memory(decision, was_applied=False, blocked_reason=blocked_reason)
            return decision

        # Aggiorna cooldown solo se effettivamente applicato
        if decision.action == "change_strategy":
            self._last_strategy_change = now
            self._current_strategy = decision.new_strategy
        elif decision.action == "update_params":
            self._last_param_update = now
        elif decision.action == "update_threshold":
            self._last_threshold_change = now

        # Salva in memoria come applicata
        await self._save_decision_to_memory(decision, was_applied=True)

        # Broadcast via WebSocket to frontend
        try:
            from app.scalping.router import broadcast_scalping_event
            now_iso = decision.decided_at.isoformat() if decision.decided_at else None

            action_map = {
                "update_params": "update_params",
                "change_strategy": "change_strategy",
                "update_threshold": "update_threshold",
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
                "timestamp": now_iso,
            })
            logger.info(f"Supervisor decision broadcasted: action={standard_action}")
        except Exception as broadcast_err:
            logger.warning(f"Could not broadcast supervisor decision to frontend: {broadcast_err}")

        return decision