from dataclasses import dataclass, field
from typing import Literal
from datetime import datetime


@dataclass
class Signal:
    strategy_id: str
    symbol: str
    direction: Literal["BUY", "SELL"]
    strength: float  # 0.0 – 1.0
    price: float
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class OrderRequest:
    strategy_id: str
    symbol: str
    direction: Literal["BUY", "SELL"]
    quantity: float
    price: float
    stop_loss: float
    take_profit: float
    paper: bool = True


@dataclass
class OrderResult:
    order_id: str
    status: Literal["FILLED", "REJECTED", "ERROR"]
    symbol: str
    direction: Literal["BUY", "SELL"]
    quantity: float
    price: float
    message: str = ""


@dataclass
class RiskCheckResult:
    approved: bool
    reason: str
    position_size: float = 0.0
    stop_loss_price: float = 0.0
    take_profit_price: float = 0.0


@dataclass
class PositionSnapshot:
    trade_id: str
    strategy_id: str
    symbol: str
    direction: Literal["BUY", "SELL"]
    entry_price: float
    quantity: float
    stop_loss: float
    take_profit: float
    opened_at: datetime
    unrealized_pnl: float = 0.0


@dataclass
class StrategyRequest:
    budget_eur: float
    duration_days: int
    asset_class: Literal["crypto", "stocks", "forex"]
    risk_level: Literal["low", "medium", "high"]
    symbols: list[str] | None = None
    free_text: str | None = None
    max_strategies: int = 5
