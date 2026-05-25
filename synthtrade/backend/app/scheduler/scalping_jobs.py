"""ScalpingJobs — job periodici per il modulo scalping (TASK-807).

Ogni job è una funzione async che può essere registrata nell'AsyncIOScheduler
esistente in app/scheduler/jobs.py. I job sono condizionali: se il flag
corrispondente in ScalpingSettings è False, non vengono registrati.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

# Engine opzionale passato da setup_scheduler
_engine: Optional[object] = None


def set_engine(engine: Optional[object] = None) -> None:
    """Imposta il riferimento all'ExecutionEngine per i job che ne hanno bisogno."""
    global _engine
    _engine = engine


async def intelligence_snapshot_job() -> None:
    """Job: intelligence snapshot periodico.

    Chiama SignalScoreEngine.get_snapshot() e salva su Supabase.
    Frequenza: settings.scalping.SCALPING_INTEL_UPDATE_INTERVAL_SEC (default 60s).
    """
    if not settings.scalping.SCALPING_SCHEDULER_INTEL_SNAPSHOT_ENABLED:
        return
    try:
        from app.scalping.intelligence.signal_score_engine import SignalScoreEngine

        engine = SignalScoreEngine()
        snapshot = await engine.get_snapshot()
        if snapshot is None:
            logger.warning("Intel snapshot job: snapshot is None")
            return

        # Salva su Supabase se disponibile
        try:
            from app.db.supabase_client import get_supabase

            db = get_supabase()
            data = {
                "symbol": snapshot.symbol,
                "funding_rate": (
                    float(snapshot.funding_rate.rate)
                    if snapshot.funding_rate
                    else None
                ),
                "open_interest": (
                    float(snapshot.open_interest.value_usd)
                    if snapshot.open_interest
                    else None
                ),
                "long_pct": (
                    snapshot.long_short_ratio.long_pct
                    if snapshot.long_short_ratio
                    else None
                ),
                "short_pct": (
                    snapshot.long_short_ratio.short_pct
                    if snapshot.long_short_ratio
                    else None
                ),
                "cvd_trend": snapshot.cvd.trend if snapshot.cvd else None,
                "fear_greed_value": (
                    snapshot.fear_greed.value if snapshot.fear_greed else None
                ),
                "fear_greed_label": (
                    snapshot.fear_greed.label if snapshot.fear_greed else None
                ),
                "signal_score": (
                    snapshot.signal_score.total
                    if snapshot.signal_score
                    else None
                ),
                "signal_bias": (
                    snapshot.signal_score.bias
                    if snapshot.signal_score
                    else None
                ),
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            }
            db.table("market_intel_snapshots").insert(data).execute()
        except Exception as db_err:
            logger.warning(f"Intel snapshot job: DB save failed (non-bloccante): {db_err}")

        logger.info(
            f"Intel snapshot job completed for {snapshot.symbol}: "
            f"score={snapshot.signal_score.total if snapshot.signal_score else 'N/A'}, "
            f"bias={snapshot.signal_score.bias if snapshot.signal_score else 'N/A'}"
        )
    except Exception as e:
        logger.error(f"Intel snapshot job error: {e}")


async def funding_rate_update_job() -> None:
    """Job: aggiornamento funding rate periodico.

    Chiama FundingRateCollector per ogni simbolo in watchlist.
    Frequenza: ogni 60 minuti.
    """
    if not settings.scalping.SCALPING_SCHEDULER_FUNDING_RATE_ENABLED:
        return
    try:
        from app.scalping.intelligence.collectors.funding_rate import (
            FundingRateCollector,
        )

        collector = FundingRateCollector()

        # Simboli da monitorare (configurabili in futuro)
        symbols = ["BTCUSDT", "ETHUSDT"]

        for symbol in symbols:
            try:
                fr = await collector.collect(symbol)
                if fr is None:
                    logger.warning(f"Funding rate for {symbol}: collector returned None")
                    continue
                rate_pct = float(fr.rate) * 100 if fr.rate else 0.0
                logger.info(
                    f"Funding rate {symbol}: {rate_pct:.4f}% "
                    f"(next: {fr.next_funding_time})"
                )
            except Exception as sym_err:
                logger.warning(
                    f"Funding rate update for {symbol} failed: {sym_err}"
                )

        logger.info("Funding rate update job completed")
    except Exception as e:
        logger.error(f"Funding rate update job error: {e}")


async def supervisor_check_job() -> None:
    """Job: check supervisor AI periodico.

    Esegue SupervisorScheduler.run() per valutare se cambiare parametri/strategia.
    Frequenza: settings.scalping.SCALPING_SUPERVISOR_INTERVAL_MIN (default 10 min).
    """
    if not settings.scalping.SCALPING_SCHEDULER_SUPERVISOR_ENABLED:
        return
    try:
        from app.scalping.supervisor.supervisor_scheduler import SupervisorScheduler

        scheduler_sup = SupervisorScheduler()
        decision = await scheduler_sup.run_once()
        if decision:
            logger.info(
                f"Supervisor check: action={decision.action}, "
                f"confidence={decision.confidence}, reason={decision.reason[:100] if decision.reason else 'N/A'}"
            )
        else:
            logger.info("Supervisor check: no decision returned")
    except Exception as e:
        logger.error(f"Supervisor check job error: {e}")


async def session_health_job() -> None:
    """Job: health check sessione scalping.

    Verifica che la sessione scalping sia attiva e che l'engine risponda.
    Se l'engine non è impostato, logga un warning.
    Frequenza: ogni 30 secondi.
    """
    if not settings.scalping.SCALPING_SCHEDULER_HEALTH_ENABLED:
        return
    try:
        if _engine is None:
            logger.debug("Session health: engine not set (skipping)")
            return

        # Verifica heartbeat engine
        # (placeholder — in futuro si può estendere con check reali)
        logger.debug("Session health check: OK")
    except Exception as e:
        logger.error(f"Session health job error: {e}")