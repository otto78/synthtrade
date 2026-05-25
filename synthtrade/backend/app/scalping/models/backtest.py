"""Modelli Pydantic per Backtest Engine (TASK-808)."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BacktestConfig(BaseModel):
    """Configurazione per un backtest."""
    model_config = ConfigDict(frozen=True)

    symbol: str = Field(..., description="Simbolo da testare, es: BTCUSDT")
    timeframe: str = Field(default="1h", description="Intervallo candele: 1m, 5m, 15m, 1h, 4h, 1d")
    start_date: datetime = Field(..., description="Data inizio backtest")
    end_date: datetime = Field(..., description="Data fine backtest")
    initial_capital: Decimal = Field(default=Decimal("1000"), ge=Decimal("10"), description="Capitale iniziale in USDT")
    use_intelligence: bool = Field(default=True, description="Usa SignalScoreEngine per validare segnali")
    min_confidence: float = Field(default=0.6, ge=0.0, le=1.0, description="Confidenza minima per eseguire trade")
    max_positions: int = Field(default=1, ge=1, le=10, description="Massimo posizioni contemporanee")
    commission_pct: Decimal = Field(default=Decimal("0.001"), ge=Decimal("0"), le=Decimal("0.01"),
                                    description="Commissione per trade (es: 0.001 = 0.1%%)")
    slippage_pct: Decimal = Field(default=Decimal("0.0005"), ge=Decimal("0"), le=Decimal("0.01"),
                                  description="Slippage stimato (es: 0.0005 = 0.05%%)")

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v: datetime, info: Any) -> datetime:
        start = info.data.get("start_date")
        if start and v <= start:
            raise ValueError("end_date must be after start_date")
        return v

    @field_validator("timeframe")
    @classmethod
    def valid_timeframe(cls, v: str) -> str:
        allowed = {"1m", "5m", "15m", "30m", "1h", "4h", "1d"}
        if v not in allowed:
            raise ValueError(f"timeframe must be one of {allowed}")
        return v

    @property
    def duration_hours(self) -> float:
        """Durata del backtest in ore."""
        delta = self.end_date - self.start_date
        return delta.total_seconds() / 3600


class SimulatedTrade(BaseModel):
    """Trade simulato eseguito durante il backtest."""
    model_config = ConfigDict(frozen=True)

    entry_time: datetime
    exit_time: Optional[datetime] = None
    symbol: str
    side: str = Field(..., pattern=r"^(BUY|SELL)$")
    entry_price: Decimal
    exit_price: Optional[Decimal] = None
    quantity: Decimal
    pnl: Optional[Decimal] = None  # P&L in USDT
    pnl_pct: Optional[Decimal] = None  # P&L percentuale
    signal_score: Optional[float] = None  # SignalScore al momento dell'entry
    signal_bias: Optional[str] = None  # 'bullish', 'bearish', 'neutral'
    signal_type: str = Field(default="TECHNICAL", pattern=r"^(TECHNICAL|INTELLIGENCE|HYBRID)$")
    strategy: Optional[str] = None  # Nome strategia usata
    commission_paid: Decimal = Decimal("0")
    status: str = Field(default="open", pattern=r"^(open|closed)$")

    @property
    def is_closed(self) -> bool:
        return self.status == "closed" and self.exit_price is not None

    def close(self, exit_price: Decimal, exit_time: datetime, commission: Decimal = Decimal("0")) -> None:
        """Chiude il trade calcolando P&L."""
        object.__setattr__(self, "exit_price", exit_price)
        object.__setattr__(self, "exit_time", exit_time)
        object.__setattr__(self, "status", "closed")

        if self.side == "BUY":
            raw_pnl = (exit_price - self.entry_price) * self.quantity
        else:
            raw_pnl = (self.entry_price - exit_price) * self.quantity

        total_commission = commission * 2  # Entry + exit
        object.__setattr__(self, "commission_paid", total_commission)
        net_pnl = raw_pnl - total_commission
        object.__setattr__(self, "pnl", net_pnl)

        entry_value = self.entry_price * self.quantity
        if entry_value > 0:
            object.__setattr__(self, "pnl_pct", (net_pnl / entry_value) * 100)


class BacktestMetric(BaseModel):
    """Metrica singola per il report."""
    label: str
    value: float
    unit: str = ""
    higher_is_better: bool = True


class BacktestResult(BaseModel):
    """Risultato completo di un backtest."""
    model_config = ConfigDict(frozen=False)

    id: str = Field(default="", description="UUID del backtest")
    config: BacktestConfig
    trades: List[SimulatedTrade] = Field(default_factory=list)
    metrics: Dict[str, float] = Field(default_factory=dict)
    metrics_detail: List[BacktestMetric] = Field(default_factory=list)
    correlation_data: Dict[str, float] = Field(default_factory=dict)
    equity_curve: List[Dict[str, Any]] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=_utcnow)
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    @property
    def total_trades(self) -> int:
        return len([t for t in self.trades if t.is_closed])

    @property
    def winning_trades(self) -> int:
        return len([t for t in self.trades if t.is_closed and t.pnl is not None and t.pnl > 0])

    @property
    def losing_trades(self) -> int:
        return len([t for t in self.trades if t.is_closed and t.pnl is not None and t.pnl <= 0])