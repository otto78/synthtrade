from dataclasses import dataclass, field
from typing import Literal
from datetime import datetime


@dataclass
class OhlcvSummary:
    symbol: str
    timeframe: str
    candles: int
    price_min: float
    price_max: float
    price_last: float
    volume_avg: float
    volatility_pct: float
    trend_pct: float  # % change first→last


@dataclass
class MarketContext:
    symbol: str
    timeframe: str
    regime: Literal["trending", "volatile", "ranging"]
    summary: OhlcvSummary
    generated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class StrategyContext:
    strategy_id: str
    title: str
    template: str
    params: dict
    pnl_pct: float
    win_rate: float
    sharpe: float
    max_drawdown_pct: float
    num_trades: int
    score: float


@dataclass
class EvalPromptInput:
    market: MarketContext
    strategy: StrategyContext


@dataclass
class EvalResult:
    strategy_id: str
    score: float                          # 0.0 – 1.0
    verdict: Literal["PROMOTE", "HOLD", "DEMOTE"]
    reasoning: str
    confidence: float                     # 0.0 – 1.0
    model_used: str
    tokens_used: int = 0
    evaluated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ModelResponse:
    content: str
    model: str
    tokens_used: int
