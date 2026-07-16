"""Supervisor Scheduler - orchestrazione periodica ogni 10 minuti."""

import asyncio
import json
import logging
import time
from datetime import date
from typing import Optional, Dict, List

from app.scalping.supervisor.supervisor_client import SupervisorClient
from app.scalping.supervisor.parameter_updater import ParameterUpdater
from app.scalping.engine.execution_loop import ExecutionLoop
from app.scalping.intelligence.signal_score_engine import SignalScoreEngine
from app.scalping.models.supervisor import SupervisorDecision

logger = logging.getLogger(__name__)

# TASK-904: fallback hardcoded — il mapping reale viene da ScalpingConfigLoader
_FALLBACK_REGIME_ALLOWED_STRATEGIES: Dict[str, List[str]] = {
    "ranging":        ["rsi_bollinger", "momentum_base", "stoch_rsi_bb_squeeze"],
    "volatile":       ["stoch_rsi_bb_squeeze", "momentum_base"],
    "trending_up":    ["ema_cross"],
    "trending_down":  ["ema_cross"],
    "unknown":        ["momentum_base"],
}

from app.config import settings
STRATEGY_CHANGE_COOLDOWN = settings.scalping.SCALPING_STRATEGY_COOLDOWN_SEC
PARAM_UPDATE_COOLDOWN = settings.scalping.SCALPING_PARAM_UPDATE_COOLDOWN_SEC
THRESHOLD_CHANGE_COOLDOWN = 1800  # 30 minuti
RESUME_GUARD_MIN_CONFIDENCE = 0.7  # TASK-908: soglia minima regime per bloccare resume


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
        # TASK-859: usa symbol corretto invece del default BTCUSDT
        self._score_engine = score_engine or SignalScoreEngine.get_or_create(symbol=symbol)
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._loop: Optional[ExecutionLoop] = None
        self._last_strategy_change: float = 0.0
        self._last_param_update: float = 0.0
        self._last_threshold_change: float = 0.0
        self._current_strategy: Optional[str] = None
        # TASK-866: budget giornaliero chiamate AI
        self._daily_ai_calls: int = 0
        self._last_reset_day: str = ""

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
        trade_history: Optional[list] = None,  # TASK-858
    ):
        """Salva la decisione del supervisor nella tabella supervisor_memory."""
        try:
            from app.db.supabase_client import get_supabase

            session_id = getattr(self._loop, "session_id", None) if self._loop else None
            if not session_id:
                logger.debug("_save_decision_to_memory: no session_id, skipping")
                return

            regime_name = self._loop.regime.regime if self._loop and self._loop.regime else "unknown"
            market_context = {"regime": regime_name}

            # TASK-858: session_perf dalla trade_history passata esplicitamente
            session_perf = {}
            try:
                if trade_history:
                    closed = [t for t in trade_history if t.get("exit_price")]
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

    async def _count_recent_blocks(self, minutes: int = 20) -> int:
        """Conta quante decisioni bloccate consecutive ci sono state."""
        try:
            from app.db.supabase_client import get_supabase
            from datetime import datetime, timedelta, timezone

            def _fetch():
                supabase = get_supabase()
                cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
                resp = supabase.table("supervisor_memory") \
                    .select("was_applied,action") \
                    .eq("symbol", self._symbol) \
                    .gte("decided_at", cutoff.isoformat()) \
                    .order("decided_at", desc=True) \
                    .limit(50) \
                    .execute()
                return resp.data if resp.data else []

            records = await asyncio.to_thread(_fetch)

            # Conta blocchi consecutivi (dal più recente)
            blocks = 0
            for r in records:
                if not r.get("was_applied", True) or r.get("action") in ("no_action",):
                    blocks += 1
                else:
                    break  # fermati al primo blocco non consecutivo
            return blocks
        except Exception:
            return 0

    async def _auto_adjust_threshold(self) -> None:
        """Logica hardcoded di auto-aggiustamento soglia, indipendente dall'AI.
        
        Se il sistema è bloccato da troppi minuti consecutivi, riduce
        gradualmente la soglia per evitare stallo permanente.
        """
        try:
            from app.scalping.config_loader import get_scalping_config
            current = get_scalping_config().signal_strength_threshold
            
            # 1) Se vol_anomaly è True, abbassa immediatamente a 8.0 (segnali forti)
            if self._loop and getattr(self._loop, "_candle_buffer", None):
                from app.scalping.engine.ta_analyzer import TAAnalyzer
                history = [c.model_dump() for c in self._loop._candle_buffer.get()]
                if len(history) >= 10:
                    vol_anomaly = TAAnalyzer.detect_volume_anomaly(history, multiplier=2.0)
                    if vol_anomaly and current > 8.0:
                        logger.warning(
                            f"⚡ Auto-decay: vol_anomaly rilevato! Soglia {current} → 8.0"
                        )
                        await self._updater.apply(SupervisorDecision(
                            action="update_threshold",
                            reason="Auto-decay: volume anomaly detected, lowering threshold to allow breakout trades",
                            confidence=0.9,
                            new_params={"signal_strength_threshold": 8.0},
                        ))
                        self._last_threshold_change = time.time()
                        return
            
            # 2) Se bloccato da >20 minuti consecutivi, riduci gradualmente
            blocks = await self._count_recent_blocks(minutes=20)
            if blocks >= 15 and current > 8.0:
                new_val = max(8.0, current - 2.0)
                logger.warning(
                    f"⚡ Auto-decay: {blocks} blocchi consecutivi in 20min. "
                    f"Soglia {current} → {new_val}"
                )
                await self._updater.apply(SupervisorDecision(
                    action="update_threshold",
                    reason=f"Auto-decay: {blocks} blocked decisions in 20min, reducing threshold from {current} to {new_val}",
                    confidence=0.8,
                    new_params={"signal_strength_threshold": new_val},
                ))
                self._last_threshold_change = time.time()
                
        except Exception as e:
            logger.warning(f"Auto-decay threshold error: {e}")

    async def _tick(self) -> Optional[SupervisorDecision]:
        if not self._running:
            logger.debug("Supervisor tick skipped: scheduler not running")
            return None

        # Auto-aggiustamento soglia (hardcoded, indipendente dall'AI)
        await self._auto_adjust_threshold()

        # TASK-866: check budget giornaliero
        today = date.today().isoformat()
        if self._last_reset_day != today:
            self._daily_ai_calls = 0
            self._last_reset_day = today
        max_calls = getattr(settings.scalping, "SCALPING_SUPERVISOR_MAX_DAILY_CALLS", 100)
        if self._daily_ai_calls >= max_calls:
            logger.warning(f"Supervisor daily AI call budget exhausted ({max_calls}). Skipping tick.")
            return None
        self._daily_ai_calls += 1

        # TASK-858: recupera trade_history dal router state (ExecutionLoop non ha _execution_state)
        trade_history: list = []
        try:
            from app.scalping.router import _execution_state as _router_state
            trade_history = list(_router_state.get("trade_history", []))
        except Exception:
            pass

        snapshot = await self._score_engine.get_snapshot()
        score = await self._score_engine.compute()

        if not self._running:
            logger.debug("Supervisor tick aborted after data collection: scheduler stopped")
            return None

        regime = self._loop.regime if self._loop else None
        self._current_strategy = self._loop.strategy.name if self._loop and self._loop.strategy else None
        session_id = getattr(self._loop, "session_id", None) if self._loop else None

        # Extract TA data for supervisor
        ta_patterns = None
        vol_anomaly = False
        try:
            if self._loop and getattr(self._loop, "_candle_buffer", None):
                from app.scalping.engine.ta_analyzer import TAAnalyzer
                history = [c.model_dump() for c in self._loop._candle_buffer.get()]
                if len(history) >= 10:
                    ta_patterns = TAAnalyzer.analyze_candlesticks(history)
                    vol_anomaly = TAAnalyzer.detect_volume_anomaly(history, multiplier=2.0)
        except Exception as e:
            logger.warning(f"Failed to calculate TA for supervisor: {e}")

        # TASK-860: passa trade_history al client per arricchire il context
        decision = await self._client.decide(
            symbol=self._symbol,
            snapshot=snapshot,
            regime=regime,
            score=score,
            session_id=session_id,
            trade_history=trade_history,
            ta_patterns=ta_patterns,
            vol_anomaly=vol_anomaly,
        )

        if not self._running:
            logger.debug("Supervisor tick aborted after AI call: scheduler stopped")
            return None

        logger.debug(
            f"Supervisor decision: action={decision.action} | reason={decision.reason} | "
            f"confidence={decision.confidence} | bias={decision.market_bias or 'N/A'} | "
            f"new_strategy={decision.new_strategy} | new_params={decision.new_params}"
        )

        now = time.time()
        blocked_reason = None
        was_applied = True

        if decision.action == "change_strategy":
            elapsed = now - self._last_strategy_change
            if elapsed < STRATEGY_CHANGE_COOLDOWN:
                remaining_min = int((STRATEGY_CHANGE_COOLDOWN - elapsed) / 60)
                logger.info(f"⏳ Strategy change cooldown attivo — {remaining_min} min rimanenti.")
                blocked_reason = f"cooldown: {remaining_min} min rimanenti"
                was_applied = False

        if decision.action == "update_params":
            elapsed = now - self._last_param_update
            if elapsed < PARAM_UPDATE_COOLDOWN:
                remaining_min = int((PARAM_UPDATE_COOLDOWN - elapsed) / 60)
                logger.info(f"⏳ Param update cooldown attivo — {remaining_min} min rimanenti.")
                blocked_reason = f"cooldown: {remaining_min} min rimanenti"
                was_applied = False

        if decision.action == "update_threshold":
            elapsed = now - self._last_threshold_change
            if elapsed < THRESHOLD_CHANGE_COOLDOWN:
                remaining_min = int((THRESHOLD_CHANGE_COOLDOWN - elapsed) / 60)
                logger.info(f"⏳ Threshold change cooldown attivo — {remaining_min} min rimanenti.")
                blocked_reason = f"cooldown: {remaining_min} min rimanenti"
                was_applied = False

        if decision.action == "change_strategy" and decision.new_strategy:
            current_regime = self._loop.regime.regime if self._loop and self._loop.regime else "unknown"
            # TASK-904: legge da config_loader (DB-driven) con fallback hardcoded
            try:
                from app.scalping.config_loader import get_scalping_config
                allowed = get_scalping_config().regime_allowed_strategies.get(current_regime, ["momentum_base"])
            except Exception:
                allowed = _FALLBACK_REGIME_ALLOWED_STRATEGIES.get(current_regime, ["momentum_base"])
            if decision.new_strategy not in allowed:
                logger.warning(
                    f"⛔ Supervisor ha proposto '{decision.new_strategy}' "
                    f"ma regime={current_regime} (allowed={allowed}) — strategia invariata"
                )
                self._last_strategy_change = 0.0
                blocked_reason = f"regime mismatch: {decision.new_strategy} not in {allowed}"
                was_applied = False

        # TASK-908: blocca resume in regime bearish senza possibilità di short
        if decision.action == "resume_trading" and was_applied:
            current_regime = self._loop.regime if self._loop else None
            regime_name = current_regime.regime if current_regime else "unknown"
            regime_confidence = current_regime.confidence if current_regime else 0.0

            has_position = False
            if self._loop and hasattr(self._loop, '_position_manager') and self._loop._position_manager:
                has_position = self._loop._position_manager.has_open()

            if (
                regime_name == "trending_down"
                and regime_confidence >= RESUME_GUARD_MIN_CONFIDENCE
                and not has_position
            ):
                logger.warning(
                    f"⛔ Resume BLOCKED: regime={regime_name} confidence={regime_confidence:.2f} "
                    f"no_position — mercato in downtrend, nessuna posizione da proteggere"
                )
                blocked_reason = (
                    f"resume blocked: regime={regime_name} confidence={regime_confidence:.2f} "
                    f"no_position — bearish senza short"
                )
                was_applied = False

        if was_applied:
            await self._updater.apply(decision)
        else:
            await self._save_decision_to_memory(
                decision, was_applied=False, blocked_reason=blocked_reason,
                trade_history=trade_history,
            )
            return decision

        if decision.action == "change_strategy":
            self._last_strategy_change = now
            self._current_strategy = decision.new_strategy
        elif decision.action == "update_params":
            self._last_param_update = now
        elif decision.action == "update_threshold":
            self._last_threshold_change = now

        await self._save_decision_to_memory(decision, was_applied=True, trade_history=trade_history)

        try:
            from app.scalping.router import broadcast_scalping_event
            now_iso = decision.decided_at.isoformat() if decision.decided_at else None
            action_map = {
                "update_params": "update_params",
                "change_strategy": "change_strategy",
                "update_threshold": "update_threshold",
                "pause_trading": "pause_trading",
                "resume_trading": "resume_trading",
                "no_action": "no_action",
            }
            await broadcast_scalping_event("supervisor", {
                "action": action_map.get(decision.action, decision.action),
                "reason": decision.reason,
                "confidence": decision.confidence,
                "market_bias": decision.market_bias or "neutral",
                "primary_signal": decision.primary_signal or "",
                "new_strategy": decision.new_strategy,
                "new_params": decision.new_params,
                "decided_at": now_iso,
                "timestamp": now_iso,
            })
            logger.info(f"Supervisor decision broadcasted: action={decision.action}")
        except Exception as broadcast_err:
            logger.warning(f"Could not broadcast supervisor decision to frontend: {broadcast_err}")

        return decision
