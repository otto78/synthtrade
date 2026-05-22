"""Schemas Pydantic per il modulo Scalping v2.0.

Corrispondono alle tabelle Supabase create in TASK-802.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# ScalpingSession
# ──────────────────────────────────────────────

class ScalpingSessionCreate(BaseModel):
    mode: str = Field(..., pattern=r"^(PAPER|LIVE|BACKTEST)$")
    symbol: str
    timeframe: str = "1m"
    status: str = "running"


class ScalpingSession(BaseModel):
    id: str
    mode: Optional[str] = None
    symbol: str
    timeframe: str
    status: Optional[str] = None
    started_at: datetime
    stopped_at: Optional[datetime] = None
    total_pnl: Optional[Decimal] = Decimal("0")
    trade_count: Optional[int] = 0
    win_count: Optional[int] = 0
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────
# ScalpingTrade
# ──────────────────────────────────────────────

class ScalpingTradeCreate(BaseModel):
    session_id: str
    symbol: str
    side: str = Field(..., pattern=r"^(BUY|SELL)$")
    entry_price: Decimal
    quantity: Decimal
    strategy_type: str
    signal_reason: Optional[str] = None
    signal_score: Optional[Decimal] = None
    funding_rate_at_entry: Optional[Decimal] = None
    fear_greed_at_entry: Optional[int] = None
    cvd_trend_at_entry: Optional[str] = None
    binance_order_id: Optional[str] = None


class ScalpingTrade(BaseModel):
    id: str
    session_id: Optional[str] = None
    symbol: str
    side: Optional[str] = None
    entry_price: Decimal
    exit_price: Optional[Decimal] = None
    quantity: Decimal
    pnl: Optional[Decimal] = None
    pnl_pct: Optional[Decimal] = None
    strategy_type: str
    signal_reason: Optional[str] = None
    signal_score: Optional[Decimal] = None
    funding_rate_at_entry: Optional[Decimal] = None
    fear_greed_at_entry: Optional[int] = None
    cvd_trend_at_entry: Optional[str] = None
    entry_time: datetime
    exit_time: Optional[datetime] = None
    status: Optional[str] = None
    binance_order_id: Optional[str] = None

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────
# SupervisorDecision
# ──────────────────────────────────────────────

class SupervisorDecisionCreate(BaseModel):
    session_id: str
    action: str
    reason: str
    confidence: Optional[Decimal] = None
    market_bias: Optional[str] = None
    primary_signal: Optional[str] = None
    previous_params: Optional[dict] = None
    new_params: Optional[dict] = None
    previous_strategy: Optional[str] = None
    new_strategy: Optional[str] = None


class SupervisorDecision(BaseModel):
    id: str
    session_id: Optional[str] = None
    action: str
    reason: str
    confidence: Optional[Decimal] = None
    market_bias: Optional[str] = None
    primary_signal: Optional[str] = None
    previous_params: Optional[dict] = None
    new_params: Optional[dict] = None
    previous_strategy: Optional[str] = None
    new_strategy: Optional[str] = None
    decided_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────
# MarketIntelSnapshot
# ──────────────────────────────────────────────

class MarketIntelSnapshotCreate(BaseModel):
    symbol: str
    funding_rate: Optional[Decimal] = None
    open_interest: Optional[Decimal] = None
    long_pct: Optional[Decimal] = None
    short_pct: Optional[Decimal] = None
    cvd_trend: Optional[str] = None
    fear_greed_value: Optional[int] = None
    fear_greed_label: Optional[str] = None
    signal_score: Optional[Decimal] = None
    signal_bias: Optional[str] = None


class MarketIntelSnapshot(BaseModel):
    id: str
    symbol: str
    funding_rate: Optional[Decimal] = None
    open_interest: Optional[Decimal] = None
    long_pct: Optional[Decimal] = None
    short_pct: Optional[Decimal] = None
    cvd_trend: Optional[str] = None
    fear_greed_value: Optional[int] = None
    fear_greed_label: Optional[str] = None
    signal_score: Optional[Decimal] = None
    signal_bias: Optional[str] = None
    recorded_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────
# Opportunity
# ──────────────────────────────────────────────

class OpportunityCreate(BaseModel):
    source: str
    category: str
    urgency: str
    scalping_opportunity: bool = False
    title: str
    action: Optional[str] = None
    symbol: Optional[str] = None
    expected_volatility: Optional[str] = None
    time_sensitive: bool = False
    url: Optional[str] = None
    raw_content: Optional[str] = None
    content_hash: str
    classified_by_ai: bool = False


class Opportunity(BaseModel):
    id: str
    source: str
    category: str
    urgency: str
    scalping_opportunity: Optional[bool] = False
    title: str
    action: Optional[str] = None
    symbol: Optional[str] = None
    expected_volatility: Optional[str] = None
    time_sensitive: Optional[bool] = False
    url: Optional[str] = None
    raw_content: Optional[str] = None
    content_hash: Optional[str] = None
    classified_by_ai: Optional[bool] = False
    user_action: Optional[str] = None
    detected_at: Optional[datetime] = None

    class Config:
        from_attributes = True