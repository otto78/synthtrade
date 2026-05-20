"""
TASK-431: API per leggere/cambiare la modalità TEST/LIVE a runtime.

GET  /api/config/mode  →  {mode: "test"|"live", allow_live: bool}
POST /api/config/mode  →  {mode: "test"|"live"}  (cambia modalità)
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from app.config import settings
from app.dependencies import get_current_user
from app.core.exchange_factory import reconnect, reset as reset_exchange

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

    # Forza riconnessione exchange
    reconnect()

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
    if mode == 'test':
        segment = "Paper Trading su Binance Testnet"
    else:
        segment = "Live Trading su Binance Produzione"
    return segment