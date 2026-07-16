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
    Usa il simbolo della sessione scalping attiva, se presente;
    altrimenti usa BTCUSDT come fallback.
    Frequenza: settings.scalping.SCALPING_INTEL_UPDATE_INTERVAL_SEC (default 60s).
    """
    if not settings.scalping.SCALPING_SCHEDULER_INTEL_SNAPSHOT_ENABLED:
        return
    try:
        from app.scalping.intelligence.signal_score_engine import SignalScoreEngine

        # Legge il simbolo dalla sessione attiva
        # Solo se c'è una sessione running, altrimenti skip (non fare snapshot su fallback)
        active_symbol = None
        try:
            from app.scalping.router import _execution_state
            session_symbol = _execution_state.get("session", {}).get("symbol")
            session_status = _execution_state.get("session", {}).get("status", "idle")
            if session_symbol and session_status == "running":
                active_symbol = session_symbol
        except Exception:
            pass

        if not active_symbol:
            logger.debug("Intel snapshot job: no active session — skipping")
            return

        # Usa singleton per garantire che snapshot_job e execution_loop usino la STESSA istanza
        engine = SignalScoreEngine.get_or_create(symbol=active_symbol)
        snapshot = await engine.get_snapshot(force_refresh=True)
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
                    float(snapshot.long_short_ratio.long_pct)
                    if snapshot.long_short_ratio
                    else None
                ),
                "short_pct": (
                    float(snapshot.long_short_ratio.short_pct)
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
            import asyncio
            def _db_op():
                db.table("market_intel_snapshots").insert(data).execute()
            await asyncio.to_thread(_db_op)
        except Exception as db_err:
            logger.warning(f"Intel snapshot job: DB save failed (non-bloccante): {db_err}")

        logger.info(
            f"Intel snapshot job completed for {snapshot.symbol}: "
            f"score={snapshot.signal_score.total if snapshot.signal_score else 'N/A'}, "
            f"bias={snapshot.signal_score.bias if snapshot.signal_score else 'N/A'}, "
            f"engine_id={id(engine)}"
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

        # Legge il simbolo dalla sessione attiva (stesso pattern di intelligence_snapshot_job)
        active_symbol = None
        try:
            from app.scalping.router import _execution_state
            session_symbol = _execution_state.get("session", {}).get("symbol")
            session_status = _execution_state.get("session", {}).get("status", "idle")
            if session_symbol and session_status == "running":
                active_symbol = session_symbol
        except Exception:
            pass

        if not active_symbol:
            logger.debug("Supervisor check job: no active session — skipping")
            return

        scheduler_sup = SupervisorScheduler(symbol=active_symbol)
        decision = await scheduler_sup.run_once()
        if decision:
            logger.info(
                f"Supervisor check: action={decision.action}, "
                f"confidence={decision.confidence}, reason={decision.reason[:100] if decision.reason else 'N/A'}"
            )
        else:
            logger.debug("Supervisor check: no decision returned (scheduler not running)")
    except Exception as e:
        logger.error(f"Supervisor check job error: {e}")


async def session_health_job() -> None:
    """Job: health check sessione scalping.

    Verifica che la sessione scalping sia attiva, che il WS client sia connesso,
    che il buffer candele riceva dati e che i task principali siano vivi.
    Frequenza: ogni 30 secondi.
    """
    if not settings.scalping.SCALPING_SCHEDULER_HEALTH_ENABLED:
        return
    try:
        if _engine is None:
            logger.debug("Session health: engine not set (skipping)")
            return

        from app.scalping.router import _execution_state
        session = _execution_state.get("session", {})
        status = session.get("status", "idle")
        symbol = session.get("symbol", "N/A")
        mode = session.get("mode", "N/A")

        checks = {
            "session_running": status in ("running", "paused"),
            "symbol_set": symbol != "N/A",
            "mode_valid": mode in ("paper", "live", "test"),
        }

        ws_client = _execution_state.get("ws_client")
        if ws_client:
            checks["ws_connected"] = not ws_client._stop_event.is_set()
        else:
            checks["ws_connected"] = False

        loop = _execution_state.get("loop")
        if loop:
            buf = getattr(loop, "_candle_buffer", None)
            checks["buffer_has_data"] = len(buf) >= 50 if buf else False
        else:
            checks["buffer_has_data"] = False

        ws_tasks = _execution_state.get("ws_tasks", [])
        dead_tasks = [t.get_name() for t in ws_tasks if t.done()]
        checks["tasks_alive"] = len(dead_tasks) == 0

        failed = [k for k, v in checks.items() if not v]
        if failed:
            # Se la sessione è intenzionalmente idle, logga a DEBUG invece di WARNING
            if status == "idle":
                logger.debug(
                    f"Session health: idle (no active session) — {failed} "
                    f"(symbol={symbol}, mode={mode})"
                )
            else:
                logger.warning(
                    f"Session health check FAILED: {failed} "
                    f"(status={status}, symbol={symbol}, mode={mode})"
                )
        else:
            logger.debug(
                f"Session health check OK: status={status}, symbol={symbol}, "
                f"mode={mode}, tasks={len(ws_tasks)}, buffer_ready={checks['buffer_has_data']}"
            )
    except Exception as e:
        logger.error(f"Session health job error: {e}")


async def spot_reconciliation_job() -> None:
    """Job: verifica periodica del saldo Spot (ogni 2 ore).

    Solo in live mode: chiama _refresh_session_balance() per aggiornare
    il balance Spot reale da Binance. Se lo Spot è vuoto (fondi finiti
    in Simple Earn durante l'inattività), mette la sessione in pausa.
    """
    if not settings.scalping.SCALPING_SCHEDULER_HEALTH_ENABLED:
        return
    try:
        from app.scalping.router import _execution_state
        session = _execution_state.get("session", {})
        if session.get("status") not in ("running", "paused") or session.get("mode") != "live":
            logger.debug("Spot reconciliation: no active live session — skipping")
            return

        from app.scalping.router import _refresh_session_balance
        from app.scalping.router import broadcast_scalping_event

        logger.info("🔄 PERIODIC SPOT RECONCILIATION: refreshing balance...")
        await _refresh_session_balance()

        bal = session.get("live_balance", 0)
        trade_val = float(session.get("trade_value", 10.0))
        if bal is None or bal <= 0 or bal < trade_val:
            logger.warning(
                f"\033[91m⚠️ PERIODIC CHECK: Spot balance={bal} < trade_value={trade_val}. "
                f"All funds may be in Earn. Pausing session.\033[0m"
            )
            if session.get("status") != "paused":
                session["status"] = "paused"
                await broadcast_scalping_event("session_restored", {
                    **session.copy(),
                    "status": "paused",
                    "pause_reason": "SPOT_BALANCE_ZERO",
                    "pause_message": "I tuoi fondi sono in Simple Earn. Spostali su Spot e fai Resume.",
                })
        else:
            logger.info(f"🔄 PERIODIC SPOT RECONCILIATION: Spot balance OK: {bal}")
            # Se era in pausa e ora spot è tornato, resuma automaticamente
            if session.get("status") == "paused":
                logger.info("🔄 Spot balance restored — auto-resuming session.")
                session["status"] = "running"
                await broadcast_scalping_event("session_restored", session.copy())
    except Exception as e:
        logger.warning(f"Spot reconciliation job error (non-fatal): {e}")


async def opportunity_monitor_job() -> None:
    """Job: opportunity monitor periodico.

    Esegue polling multi-fonte ogni 5 minuti e classifica opportunità.
    Frequenza: 5 minuti (300 secondi).
    """
    if not settings.scalping.SCALPING_SCHEDULER_OPPORTUNITY_ENABLED:
        return
    try:
        from app.scalping.opportunity.scheduler import OpportunityScheduler

        scheduler = OpportunityScheduler()
        results = await scheduler.run_once()

        logger.info(f"Opportunity monitor job: {len(results)} new items processed")

    except Exception as e:
        logger.error(f"Opportunity monitor job error: {e}")


async def verify_supervisor_outcomes_job() -> None:
    """TASK-863: Verifica outcome delle decisioni supervisor applicate 25-35 min fa.

    Query decisioni applicate senza outcome, calcola pnl_delta vs sessione corrente
    e classifica l'outcome come positive/negative/neutral.
    """
    try:
        import asyncio
        from datetime import timedelta
        from app.db.supabase_client import get_supabase

        now = datetime.now(timezone.utc)
        cutoff_from = (now - timedelta(minutes=35)).isoformat()
        cutoff_to = (now - timedelta(minutes=25)).isoformat()

        def _fetch():
            db = get_supabase()
            return db.table("supervisor_memory") \
                .select("id, decided_at") \
                .eq("was_applied", True) \
                .is_("outcome_verified_at", "null") \
                .gte("decided_at", cutoff_from) \
                .lte("decided_at", cutoff_to) \
                .execute()

        result = await asyncio.to_thread(_fetch)
        records = result.data or []
        if not records:
            return

        # Calcola PnL corrente dalla sessione attiva
        current_pnl = 0.0
        try:
            from app.scalping.router import _execution_state
            trade_history = _execution_state.get("trade_history", [])
            current_pnl = sum((t.get("pnl") or 0) for t in trade_history if t.get("exit_price"))
        except Exception:
            pass

        label = "positive" if current_pnl > 0.01 else ("negative" if current_pnl < -0.01 else "neutral")
        now_iso = now.isoformat()

        def _update(record_id):
            db = get_supabase()
            db.table("supervisor_memory").update({
                "outcome_verified_at": now_iso,
                "outcome_pnl_delta": round(current_pnl, 2),
                "outcome_label": label,
            }).eq("id", record_id).execute()

        for rec in records:
            await asyncio.to_thread(_update, rec["id"])

        logger.info(f"verify_supervisor_outcomes_job: updated {len(records)} records (label={label})")
    except Exception as e:
        logger.warning(f"verify_supervisor_outcomes_job error: {e}")

