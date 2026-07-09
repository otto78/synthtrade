"""
TASK-431: API per leggere/cambiare la modalità TEST/LIVE a runtime.

GET  /api/config/mode  →  {mode: "test"|"live", allow_live: bool}
POST /api/config/mode  →  {mode: "test"|"live"}  (cambia modalità)
"""

import asyncio
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from app.config import settings
from app.dependencies import get_current_user
from app.core.exchange_factory import get_adapter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/config", tags=["config"])


class ModeResponse(BaseModel):
    mode: str = Field(..., description="Modalità corrente: 'test' | 'live'")
    allow_live: bool = Field(..., description="Se True, è permesso passare a LIVE")
    details: str = Field(..., description="Descrizione leggibile")


class ModeUpdateRequest(BaseModel):
    mode: str = Field(..., description="Nuova modalità: 'test' | 'live'")


@router.get("/mode")
def get_mode(_user: str = Depends(get_current_user)) -> ModeResponse:
    """Legge la modalità corrente."""
    details = _build_details(settings.TRADING_MODE)
    return ModeResponse(
        mode=settings.TRADING_MODE,
        allow_live=settings.ALLOW_LIVE_MODE,
        details=details,
    )


@router.post("/mode", status_code=status.HTTP_200_OK)
def set_mode(
    req: ModeUpdateRequest,
    _user: str = Depends(get_current_user),
) -> ModeResponse:
    """Cambia la modalità a runtime.

    Per passare a LIVE, ALLOW_LIVE_MODE deve essere True in .env.
    Il cambio modalità:
    1. Aggiorna settings.TRADING_MODE
    2. Forza la riconnessione dell'exchange (nuove key/URL)
    3. I repository filtreranno automaticamente i dati della nuova modalità
    """
    new_mode = req.mode.lower().strip()

    if new_mode not in ("test", "live"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Modalità '{new_mode}' non valida. Usa 'test' o 'live'.",
        )

    if new_mode == settings.TRADING_MODE:
        # Già in questa modalità
        return ModeResponse(
            mode=settings.TRADING_MODE,
            allow_live=settings.ALLOW_LIVE_MODE,
            details=f"Già in modalità {_build_details(new_mode)}",
        )

    if new_mode == "live" and not settings.ALLOW_LIVE_MODE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Passaggio a LIVE non permesso. "
                "Imposta ALLOW_LIVE_MODE=true nel file .env per abilitare."
            ),
        )

    # Log del cambio
    old_mode = settings.TRADING_MODE
    logger.info(
        "Cambio modalità: %s → %s (richiesto da utente %s)",
        old_mode, new_mode, _user,
    )

    # Aggiorna settings — il singleton settings viene ricaricato
    # Nota: pydantic_settings non supporta reassign a runtime facilmente.
    # Usiamo l'override diretto del campo bypassando il modello.
    object.__setattr__(settings, 'TRADING_MODE', new_mode)

    # Forza riconnessione exchange con il provider corretto
    try:
        get_adapter()
        logger.info(
            "ExchangeFactory: adapter ricreato per provider=%s demo=%s mode=%s",
            settings.EXCHANGE_PROVIDER,
            settings.exchange_demo,
            settings.TRADING_MODE,
        )
    except Exception as exc:
        logger.warning("ExchangeFactory: riconnessione adapter fallita: %s", exc)

    # Stop scalping session if mode is inconsistent
    # A live session cannot run in test mode and vice versa
    try:
        from app.scalping.router import _execution_state as scalping_state

        scalping_session = scalping_state.get("session", {})
        if scalping_session.get("status") == "running":
            sess_mode = scalping_session.get("mode", "").lower()
            if sess_mode != new_mode:
                logger.warning(
                    "Mode change %s → %s: stopping scalping session because its mode=%s is now inconsistent.",
                    old_mode, new_mode, sess_mode,
                )
                # Stop the scalping session
                scalping_session["status"] = "idle"
                
                # Stop WS broadcast if running
                if scalping_state.get("loop") or scalping_state.get("ws_client"):
                    from app.scalping.router import _stop_ws_broadcast
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            loop.create_task(_stop_ws_broadcast())
                    except RuntimeError:
                        pass
                
                # Mark DB session as stopped
                db_sid = scalping_session.get("db_session_id")
                if db_sid:
                    try:
                        from app.db.supabase_client import get_supabase
                        supabase = get_supabase()
                        supabase.table("scalping_sessions").update({
                            "status": "stopped",
                            "stopped_at": datetime.utcnow().isoformat()
                        }).eq("id", db_sid).execute()
                    except Exception as db_e:
                        logger.warning(f"Failed to update scalping session in DB: {db_e}")
                
                logger.info("Scalping session stopped due to mode change from %s to %s", old_mode, new_mode)
    except Exception as e:
        logger.warning(f"Error checking scalping session on mode change: {e}")

    logger.info(
        "Modalità cambiata con successo: %s → %s (exchange riconnesso)",
        old_mode, new_mode,
    )

    return ModeResponse(
        mode=new_mode,
        allow_live=settings.ALLOW_LIVE_MODE,
        details=f"Passato a {_build_details(new_mode)}",
    )


def _build_details(mode: str) -> str:
    """Restituisce una descrizione leggibile della modalità."""
    provider = settings.EXCHANGE_PROVIDER.upper()
    if mode == 'test':
        segment = f"{provider} Demo Trading"
    else:
        segment = f"{provider} Live Trading"
    return segment