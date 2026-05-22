"""Modelli Pydantic per dati di mercato scalping."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Candle(BaseModel):
    """Candela 1m da Binance WS."""
    symbol: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    timestamp: datetime
    closed: bool = True

    class Config:
        frozen = True


class MarketRegime(BaseModel):
    """Regime di mercato identificato dal RegimeDetector."""
    regime: str  # 'trending_up', 'trending_down', 'ranging', 'volatile'
    confidence: float = Field(ge=0.0, le=1.0)
    detected_at: datetime = Field(default_factory=_utcnow)