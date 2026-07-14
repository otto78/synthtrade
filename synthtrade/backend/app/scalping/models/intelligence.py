"""Modelli Pydantic per Signal Intelligence (TASK-804).

Questi modelli rappresentano i dati grezzi raccolti dai vari collector
e lo score aggregato calcolato dal SignalScoreEngine.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Optional, List
from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ──────────────────────────────────────────────
# Dati grezzi dei collector
# ──────────────────────────────────────────────


class FundingRate(BaseModel):
    """Funding rate di un simbolo da Binance Futures.

    Funding Rate positivo -> i long pagano gli short (mercato overleveraged long).
    Funding Rate negativo -> gli short pagano i long (mercato overleveraged short).
    """
    model_config = ConfigDict(frozen=True)

    symbol: str
    rate: Decimal = Field(..., description="Funding rate in formato decimale (es: 0.0001 = 0.01%)")
    timestamp: datetime
    next_funding_time: Optional[datetime] = None
    collected_at: datetime = Field(default_factory=_utcnow)


class OpenInterest(BaseModel):
    """Open Interest di un simbolo da Binance Futures."""
    model_config = ConfigDict(frozen=True)

    symbol: str
    value_usd: Decimal = Field(..., description="Open Interest in USD")
    asset: Optional[str] = None  # es: 'BTC', 'ETH'
    timestamp: datetime
    collected_at: datetime = Field(default_factory=_utcnow)


class LongShortRatio(BaseModel):
    """Long/Short ratio da Binance Futures.

    > 70% long  -> mercato esposto a short squeeze
    > 70% short -> mercato esposto a long squeeze
    """
    model_config = ConfigDict(frozen=True)

    symbol: str
    long_pct: Decimal = Field(..., ge=0, le=100, description="Percentuale posizioni long")
    short_pct: Decimal = Field(..., ge=0, le=100, description="Percentuale posizioni short")
    timestamp: datetime
    collected_at: datetime = Field(default_factory=_utcnow)

    @property
    def ratio(self) -> float:
        """Long/Short ratio. > 1 = piu long, < 1 = piu short."""
        if self.short_pct == 0:
            return float("inf")
        return float(self.long_pct) / float(self.short_pct)


class CVDData(BaseModel):
    """Cumulative Volume Delta - pressione netta buy vs sell.

    CVD crescente  = piu pressione buy  -> momentum rialzista
    CVD calante    = piu pressione sell -> momentum ribassista
    CVD divergente dal prezzo = forte segnale inversione imminente
    """
    model_config = ConfigDict(frozen=True)

    symbol: str
    cvd: Decimal = Field(..., description="Valore cumulativo del CVD")
    delta: Decimal = Field(default=Decimal("0"), description="Delta nell'ultimo periodo")
    trend: Optional[str] = Field(default=None, description="'rising', 'falling', 'neutral'")
    timestamp: datetime
    collected_at: datetime = Field(default_factory=_utcnow)


class FearGreedData(BaseModel):
    """Fear & Greed Index da Alternative.me.

    Valori:
    0-24  = Extreme Fear
    25-44 = Fear
    45-54 = Neutral
    55-74 = Greed
    75-100 = Extreme Greed
    """
    model_config = ConfigDict(frozen=True)

    value: int = Field(..., ge=0, le=100)
    label: Optional[str] = None  # 'Extreme Fear', 'Fear', 'Neutral', 'Greed', 'Extreme Greed'
    timestamp: datetime
    collected_at: datetime = Field(default_factory=_utcnow)


class OnChainData(BaseModel):
    """Dati On-Chain da Blockchain.com, Blockchair e Dune.

    Include exchange inflows/outflows, active addresses, network growth.
    """
    model_config = ConfigDict(frozen=True)

    symbol: str
    exchange_net_flow: Optional[Decimal] = Field(default=None, description="Inflow - Outflow verso gli exchange")
    active_addresses: Optional[int] = Field(default=None, description="Indirizzi attivi nelle ultime 24h")
    transaction_count: Optional[int] = Field(default=None, description="Numero di transazioni nelle ultime 24h")
    hash_rate: Optional[Decimal] = Field(default=None, description="Hash rate della rete (se applicabile)")
    source: str = "combined"
    timestamp: datetime
    collected_at: datetime = Field(default_factory=_utcnow)


class SentimentData(BaseModel):
    """Sentiment da News e Social (CryptoCompare, NewsAPI).

    Basato su analisi aggregata di titoli e frequenza news.
    """
    model_config = ConfigDict(frozen=True)

    symbol: str
    score: float = Field(..., ge=-1.0, le=1.0, description="Sentiment score: -1 (bearish) a +1 (bullish)")
    news_count: int = Field(default=0, description="Numero di news analizzate nell'ultimo periodo")
    top_headlines: List[str] = Field(default_factory=list, description="Titoli principali")
    source: str = "news_aggregator"
    collected_at: datetime = Field(default_factory=_utcnow)


class WhaleData(BaseModel):
    """Whale Movements da Whale Alert e Blockchair.

    Monitora grandi trasferimenti on-chain.
    """
    model_config = ConfigDict(frozen=True)

    symbol: str
    whale_transaction_count: int = Field(default=0, description="Numero di grandi transazioni rilevate")
    large_transfer_volume: Decimal = Field(default=Decimal("0"), description="Volume totale dei grandi trasferimenti")
    recent_whale_activity: bool = Field(default=False, description="True se c'è stata attività massiccia recente")
    timestamp: datetime
    collected_at: datetime = Field(default_factory=_utcnow)


class OrderBookImbalance(BaseModel):
    """Order Book Imbalance da OKX public market data (endpoint /market/books).

    Funziona su qualsiasi coppia spot OKX (incluso OKB-EUR) perché non dipende
    da un mercato futures.

    imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth)
      > 0 -> piu liquidita' bid -> pressione rialzista
      < 0 -> piu liquidita' ask -> pressione ribassista
    """
    model_config = ConfigDict(frozen=True)

    symbol: str
    bid_depth: Decimal = Field(..., description="Somma delle quantità sui primi N livelli bid")
    ask_depth: Decimal = Field(..., description="Somma delle quantità sui primi N livelli ask")
    imbalance: float = Field(..., ge=-1.0, le=1.0, description="Imbalance normalizzato: -1.0 (solo ask) a +1.0 (solo bid)")
    timestamp: datetime
    collected_at: datetime = Field(default_factory=_utcnow)


class SpreadSnapshot(BaseModel):
    """Bid/ask spread relativo da OKX public ticker (/market/ticker).

    NON è direzionale: è un flag di affidabilità/cautela. Uno spread ampio
    rispetto alla media mobile recente indica bassa liquidità / rischio di
    slippage, non un bias direzionale (bullish/bearish).

    spread_pct = (ask - bid) / mid_price * 100
    ratio_vs_avg = spread_pct / rolling_avg_pct  (1.0 = nella norma)
    """
    model_config = ConfigDict(frozen=True)

    symbol: str
    bid: Decimal = Field(..., description="Prezzo bid (miglior denaro)")
    ask: Decimal = Field(..., description="Prezzo ask (miglior lettera)")
    mid_price: Decimal = Field(..., description="(bid + ask) / 2")
    spread_abs: Decimal = Field(..., description="ask - bid")
    spread_pct: float = Field(..., description="(ask - bid) / mid * 100")
    rolling_avg_pct: float = Field(..., description="Media mobile degli ultimi N campioni di spread_pct")
    ratio_vs_avg: float = Field(..., description="spread_pct / rolling_avg_pct (1.0 = nella norma)")
    is_anomalous: bool = Field(default=False, description="True se ratio_vs_avg >= soglia anomalia (es. 3.0)")
    sample_count: int = Field(default=0, description="Numero di campioni nella finestra mobile")
    timestamp: datetime
    collected_at: datetime = Field(default_factory=_utcnow)


# ──────────────────────────────────────────────
# Score aggregato
# ──────────────────────────────────────────────


class SignalScore(BaseModel):
    """Score intelligence aggregato da -100 a +100.

    Valori negativi -> bias SHORT (bearish)
    Valori positivi -> bias LONG (bullish)
    |score| < SOGLIA = mercato indistinto, no trade
    """
    model_config = ConfigDict(frozen=True)

    total: float = Field(..., ge=-100.0, le=100.0)
    bias: Optional[str] = Field(default=None, pattern=r"^(bullish|bearish|neutral)$")
    tradeable: bool = Field(default=False)
    breakdown: Dict[str, float] = Field(
        default_factory=dict,
        description="Contributo di ogni collector allo score totale"
    )
    signal_strength: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    
    # Campi per analisi del trend (TASK-866)
    trend_5m: Optional[float] = Field(default=None, description="Variazione assoluta dello score negli ultimi 5 minuti")
    velocity: Optional[float] = Field(default=None, description="Variazione media per minuto")
    trend_direction: Optional[str] = Field(default=None, description="'converging', 'diverging', o 'stable'")
    
    symbol: str = "BTCUSDT"
    computed_at: datetime = Field(default_factory=_utcnow)


# ──────────────────────────────────────────────
# Snapshot aggregato
# ──────────────────────────────────────────────


class MarketIntelSnapshot(BaseModel):
    """Snapshot completo del contesto di mercato per un simbolo.

    E' cio' che viene salvato su Supabase (tabella market_intel_snapshots)
    e passato al Supervisor AI.
    """
    symbol: str
    funding_rate: Optional[FundingRate] = None
    open_interest: Optional[OpenInterest] = None
    long_short_ratio: Optional[LongShortRatio] = None
    cvd: Optional[CVDData] = None
    fear_greed: Optional[FearGreedData] = None
    onchain: Optional[OnChainData] = None
    sentiment: Optional[SentimentData] = None
    whale: Optional[WhaleData] = None
    order_book_imbalance: Optional[OrderBookImbalance] = None
    signal_score: Optional[SignalScore] = None
    snapshot_at: datetime = Field(default_factory=_utcnow)