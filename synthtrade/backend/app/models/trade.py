from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, Literal

class Trade(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    strategy_id: str
    pair: str
    action: Literal["BUY", "SELL"]
    status: Literal["OPEN", "CLOSED"]
    price: float
    quantity: float
    pnl_pct: Optional[float] = None
    pnl_eur: Optional[float] = None
    executed_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
