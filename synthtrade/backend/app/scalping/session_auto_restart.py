"""TASK-1255 — Stop & Go: auto-restart settimanale sessione.

Ogni 15 minuti controlla se la sessione corrente ha superato MAX_SESSION_AGE_DAYS (7).
Se sì e non ci sono posizioni aperte → stop + restart automatico.
Se sì ma c'è una posizione aperta → imposta restart_pending=True e aspetta.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

MAX_SESSION_AGE_DAYS = 7

# Stato del restart pending (in-memory, non persistito su DB)
_restart_pending = False


async def check_and_auto_restart() -> None:
    """Entry point del job APScheduler. Ogni 15 minuti verifica se serve restart."""
    from app.scalping._state import _execution_state

    session = _execution_state.get("session", {})
    global _restart_pending

    # Skip se non attivo
    if session.get("status") != "running":
        return
    if not session.get("auto_restart_weekly"):
        return

    # Calcola età sessione
    started_at = session.get("started_at")
    if not started_at:
        return

    try:
        if isinstance(started_at, str):
            started_dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        elif isinstance(started_at, datetime):
            started_dt = started_at if started_at.tzinfo else started_dt.replace(tzinfo=timezone.utc)
        else:
            return
    except Exception as e:
        logger.warning(f"[AutoRestart] Failed to parse started_at: {e}")
        return

    now = datetime.now(timezone.utc)
    session_age = now - started_dt

    if session_age < timedelta(days=MAX_SESSION_AGE_DAYS):
        # Log solo una volta al giorno (a mezzanotte circa)
        remaining = timedelta(days=MAX_SESSION_AGE_DAYS) - session_age
        hours_left = int(remaining.total_seconds() / 3600)
        if hours_left <= 24 and hours_left % 6 == 0:
            logger.info(f"[AutoRestart] Session age {session_age.days}d {hours_left}h remaining until auto-restart")
        return

    # Sessione è vecchia — verifica posizioni aperte
    pm = _execution_state.get("position_manager")
    if pm and pm.has_open():
        if not _restart_pending:
            _restart_pending = True
            session["restart_pending"] = True
            logger.warning(f"[AutoRestart] Session age {session_age.days}d exceeds {MAX_SESSION_AGE_DAYS}d limit. "
                          f"Position open — waiting for close before restart.")
            from app.scalping.broadcast import broadcast_scalping_event
            await broadcast_scalping_event("session_restart_pending", {
                "session_id": session.get("session_id"),
                "session_age_days": session_age.days,
            })
        return

    # Nessuna posizione aperta → restart
    if _restart_pending or session_age >= timedelta(days=MAX_SESSION_AGE_DAYS):
        logger.info(f"[AutoRestart] Session age {session_age.days}d — performing auto-restart")
        await _do_stop_and_restart(session)


async def _do_stop_and_restart(session: dict) -> None:
    """Cattura parametri, ferma, e riavvia la sessione."""
    from app.scalping._state import _execution_state
    from app.scalping.broadcast import broadcast_scalping_event
    from app.scalping.rest.session import control_session

    global _restart_pending

    # Cattura parametri della sessione corrente
    captured = {
        "symbol": session.get("symbol"),
        "trade_value": session.get("trade_value"),
        "mode": session.get("mode"),
        "strategy": session.get("strategy"),
        "auto_restart_weekly": True,  # mantieni attivo per il prossimo ciclo
    }
    previous_session_id = session.get("session_id")
    previous_db_session_id = session.get("db_session_id")

    logger.info(f"[AutoRestart] Captured params: {captured} (previous_session={previous_session_id})")

    # Stop della sessione corrente
    try:
        await control_session({"action": "stop"})
        logger.info(f"[AutoRestart] Session {previous_session_id} stopped successfully")
    except Exception as e:
        logger.error(f"[AutoRestart] Failed to stop session: {e}")
        return

    # Attendi che il WS si aggiorni
    await asyncio.sleep(3)

    # Restart con i parametri catturati
    try:
        await control_session({
            "action": "start",
            **captured,
        })
        logger.info(f"[AutoRestart] Session restarted successfully")

        # Broadcast evento
        new_session = _execution_state.get("session", {})
        await broadcast_scalping_event("session_auto_restarted", {
            "previous_session_id": previous_session_id,
            "previous_db_session_id": previous_db_session_id,
            "new_session_id": new_session.get("session_id"),
            "new_db_session_id": new_session.get("db_session_id"),
        })
    except Exception as e:
        logger.error(f"[AutoRestart] Failed to restart session: {e}")

    # Reset pending state
    _restart_pending = False
    session["restart_pending"] = False


def get_restart_countdown(session: dict) -> str:
    """Calcola il countdown al prossimo restart in formato leggibile."""
    started_at = session.get("started_at")
    if not started_at:
        return ""

    try:
        if isinstance(started_at, str):
            started_dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        elif isinstance(started_at, datetime):
            started_dt = started_at if started_at.tzinfo else started_at.replace(tzinfo=timezone.utc)
        else:
            return ""
    except Exception:
        return ""

    now = datetime.now(timezone.utc)
    restart_at = started_dt + timedelta(days=MAX_SESSION_AGE_DAYS)
    remaining = restart_at - now

    if remaining.total_seconds() <= 0:
        return "in corso"

    days = remaining.days
    hours = int(remaining.seconds / 3600)

    if days > 0:
        return f"{days}g {hours}h"
    elif hours > 0:
        minutes = int((remaining.seconds % 3600) / 60)
        return f"{hours}h {minutes}m"
    else:
        minutes = int(remaining.seconds / 60)
        return f"{minutes}m"
