from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, Dict, Any

class Strategy(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: Optional[str] = None
    custom_name: Optional[str] = None
    description: Optional[str] = None
    template: Optional[str] = None
    pair: str
    timeframe: str
    status: str
    budget_eur: float = 100.0
    initial_capital_usdt: Optional[float] = None
    peak_equity_usdt: Optional[float] = None
    params: Dict[str, Any] = Field(default_factory=dict)
    score: Optional[float] = None
    ai_score: Optional[float] = None
    ai_risk: Optional[str] = None
    ai_note: Optional[str] = None
    ai_strengths: Optional[str] = None
    ai_warnings: Optional[str] = None
    estimated_profit_pct: Optional[float] = None
    estimated_profit_eur: Optional[float] = None
    backtest: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
