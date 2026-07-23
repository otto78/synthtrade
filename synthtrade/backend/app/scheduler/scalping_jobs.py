"""ScalpingJobs — job periodici per il modulo scalping (TASK-807).

Ogni job è una funzione async che può essere registrata nell'AsyncIOScheduler
esistente in app/scheduler/jobs.py. I job sono condizionali: se il flag
corrispondente in ScalpingSettings è False, non vengono registrati.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
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

        # TASK-XXXX: Detect dead order event stream (REST polling fallback).
        # If the polling task crashed silently, restart it automatically.
        order_stream = _execution_state.get("user_data_stream")
        if order_stream:
            stream_task = getattr(order_stream, "_listen_task", None)
            if stream_task and stream_task.done():
                exc = stream_task.exception()
                logger.warning(
                    "Order event stream task is DEAD (exc=%s). Restarting...",
                    exc,
                )
                try:
                    # Stop the dead stream cleanly, then restart
                    await order_stream.stop()
                except Exception:
                    pass
                _execution_state.pop("user_data_stream", None)
                try:
                    from app.scalping.trade_executor import _start_uds_if_needed
                    await _start_uds_if_needed()
                    checks["order_stream_alive"] = True
                    logger.info("Order event stream restarted successfully")
                except Exception as restart_err:
                    logger.error("Order event stream restart FAILED: %s", restart_err)
                    checks["order_stream_alive"] = False
            else:
                checks["order_stream_alive"] = True
        else:
            # No stream yet — OK if no active position, warn otherwise
            position_manager = _execution_state.get("position_manager")
            has_position = bool(position_manager and position_manager.get_open())
            checks["order_stream_alive"] = not has_position

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


async def short_timestop_job() -> None:
    """TASK-1225.D: Time-stop fisso per posizioni short.

    Ogni 30 min controlla se la posizione SHORT aperta ha superato
    il limite massimo di ore (default 48h). Se sì:
    1. Cancella bracket ordini (TP/SL)
    2. Market buy di chiusura (repay automatico su OKX spot margin)
    3. Registra il trade con exit_reason="timestop_fixed"

    Pattern job-based (non asyncio.sleep): sopravvive a restart dell'app.
    """
    try:
        from app.scalping.router import _execution_state
        from app.scalping.broadcast import broadcast_scalping_event

        session = _execution_state.get("session", {})
        status = session.get("status", "idle")
        if status not in ("running", "paused"):
            return

        pm = _execution_state.get("position_manager")
        if pm is None:
            return

        pos = pm.get_open()
        if pos is None:
            return

        # Solo posizioni SHORT (side="SELL")
        if pos.side != "SELL":
            return

        # Calcola durata posizione
        max_hours = settings.scalping.SCALPING_SHORT_TIMESTOP_HOURS
        age = datetime.now(timezone.utc) - pos.entry_time
        age_hours = age.total_seconds() / 3600

        if age_hours < max_hours:
            remaining = max_hours - age_hours
            logger.debug(
                f"Short timestop: {pos.symbol} age={age_hours:.1f}h < {max_hours}h "
                f"(remaining={remaining:.1f}h) — no action"
            )
            return

        # ── TIME-STOP EXPIRED: close position ──
        logger.warning(
            f"\033[91m⏰ SHORT TIMESTOP: {pos.symbol} age={age_hours:.1f}h > {max_hours}h — "
            f"CLOSING position @ market\033[0m"
        )

        mode = session.get("mode", "paper")
        exchange = _execution_state.get("exchange")
        close_price = float(pos.entry_price)

        if mode in ("live", "test") and exchange:
            # Live/demo: cancel bracket + market buy
            from app.execution.exchange_models import SymbolRef, ClosePositionRequest

            sym_str = pos.symbol.upper()
            try:
                sym_ref = SymbolRef.from_okx(sym_str) if "-" in sym_str else SymbolRef.from_compact(sym_str)
            except Exception:
                sym_ref = SymbolRef.from_compact(sym_str)

            # 1. Cancel bracket orders
            try:
                await exchange.cancel_open_exit_orders(sym_ref)
                logger.info(f"[TIMESTOP] Cancelled bracket orders for {sym_str}")
            except Exception as cancel_e:
                logger.warning(f"[TIMESTOP] Failed to cancel bracket (non-blocking): {cancel_e}")

            # 2. Market buy to close short (with retry)
            from app.scalping.trade_executor import _live_close_position
            try:
                close_price = await _live_close_position(exchange, pos, float(pos.quantity))
                logger.info(f"[TIMESTOP] Market buy executed @ {close_price} for {sym_str}")
            except Exception as close_e:
                logger.error(f"[TIMESTOP] Market close failed: {close_e}")
                await broadcast_scalping_event("error", {
                    "code": "TIMESTOP_CLOSE_FAILED",
                    "message": f"Time-stop close failed for {sym_str}: {close_e}",
                })
                return
        else:
            # Paper mode: use current candle close price from buffer
            loop = _execution_state.get("loop")
            if loop and hasattr(loop, "_candle_buffer") and loop._candle_buffer and loop._candle_buffer.latest:
                close_price = float(loop._candle_buffer.latest.close)

        # 3. Record trade with exit_reason="timestop_fixed"
        from app.scalping.trade_executor import _close_position_and_record
        await _close_position_and_record(pm, close_price, pos, reason="timestop_fixed")

        logger.warning(
            f"\033[91m⏰ SHORT TIMESTOP CLOSED: {pos.symbol} @ {close_price} | "
            f"age={age_hours:.1f}h (limit={max_hours}h)\033[0m"
        )
    except Exception as e:
        logger.error(f"Short timestop job error: {e}")

