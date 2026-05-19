from dataclasses import dataclass, field
from typing import Literal
from datetime import datetime
from pydantic import BaseModel, field_validator, model_validator, Field


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


class AllocationItem(BaseModel):
    """Single crypto allocation with percentage"""
    symbol: str = Field(..., min_length=6)
    percentage: float = Field(..., ge=0.0, le=100.0)

    @field_validator('symbol')
    @classmethod
    def symbol_uppercase(cls, v: str) -> str:
        return v.upper()


class StrategyRequest(BaseModel):
    """Strategy generation request with multi-crypto allocation support"""
    budget_eur: float = Field(..., gt=0)
    duration_days: int = Field(..., gt=0)
    asset_class: Literal["crypto", "stocks", "forex"]
    risk_level: Literal["low", "medium", "high"]
    symbols: list[str] | None = None
    allocation: list[AllocationItem] = Field(default_factory=list)
    free_text: str | None = None
    max_strategies: int = 5
    custom_name: str | None = None

    @model_validator(mode='after')
    def validate_allocation(self):
        """Validate allocation rules"""
        # Cannot have both symbols and allocation
        if self.symbols and self.allocation:
            raise ValueError("Cannot specify both 'symbols' and 'allocation'")

        # If allocation has items, validate them
        if self.allocation and len(self.allocation) > 0:
            # Check for duplicates
            symbols = [item.symbol for item in self.allocation]
            if len(symbols) != len(set(symbols)):
                raise ValueError("Duplicate symbols in allocation")

            # Sum must be 100%
            total = sum(item.percentage for item in self.allocation)
            if abs(total - 100.0) > 0.01:  # Allow small floating point errors
                raise ValueError(f"Allocation percentages must sum to 100, got {total}")

        return self
