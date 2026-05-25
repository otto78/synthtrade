"""Modelli Pydantic per AI Supervisor."""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SupervisorDecision(BaseModel):
    """Decisione del supervisor AI."""
    model_config = ConfigDict(frozen=True)

    action: str = Field(..., pattern=r"^(update_params|change_strategy|pause_trading|resume_trading|no_action)$")
    reason: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    market_bias: Optional[str] = Field(default=None, pattern=r"^(bullish|bearish|neutral)$")
    primary_signal: Optional[str] = None
    new_params: Optional[dict] = None
    new_strategy: Optional[str] = None
    decided_at: datetime = Field(default_factory=_utcnow)