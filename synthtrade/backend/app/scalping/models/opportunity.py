"""Modelli Pydantic per Opportunity Monitor (TASK-810).

Rappresenta opportunità di mercato rilevate da vari poller.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OpportunityCategory(str, Enum):
    """Categoria di opportunità."""
    LISTING = "listing"
    LAUNCHPOOL = "launchpool"
    NEWS = "news"
    WHALE = "whale"
    AIRDROP = "airdrop"
    STAKING = "staking"
    DELISTING = "delisting"
    OTHER = "other"


class OpportunityUrgency(str, Enum):
    """Urgenza dell'opportunità."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class OpportunitySource(str, Enum):
    """Fonte dell'opportunità."""
    BINANCE_RSS = "binance_rss"
    COINGECKO_NEWS = "coingecko_news"
    CRYPTOPANIC = "cryptopanic"
    COINGECKO_TRENDING = "coingecko_trending"
    WHALE_ALERT = "whale_alert"


class Opportunity(BaseModel):
    """Opportunità di mercato rilevata.

    Rappresenta un'opportunità di trading derivante da eventi di mercato.
    Viene salvato su Supabase tabella opportunities.
    """
    model_config = ConfigDict(validate_assignment=True)

    id: str = Field(default_factory=lambda: f"opp_{uuid.uuid4().hex[:8]}")
    symbol: Optional[str] = None  # Es: BTCUSDT, BNBUSDT
    category: OpportunityCategory
    urgency: OpportunityUrgency
    source: OpportunitySource
    title: str
    description: Optional[str] = None
    url: Optional[str] = None
    published_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=_utcnow)
    is_tradeable: bool = Field(default=False)
    confidence_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    ai_reasoning: Optional[str] = None  # Reasoning del classifier AI

    # Metadata per il frontend
    tags: List[str] = Field(default_factory=list)

    # Status tracking
    is_watched: bool = Field(default=False)
    is_ignored: bool = Field(default=False)


class PollerResult(BaseModel):
    """Risultato grezzo da un poller."""
    source: OpportunitySource
    title: str
    description: Optional[str] = None
    url: Optional[str] = None
    published_at: Optional[datetime] = None
    symbol: Optional[str] = None
    raw_data: Optional[dict] = None