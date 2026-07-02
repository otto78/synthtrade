# SynthTrade — Piano di Sviluppo: Modulo Scalping
**Versione:** 2.0  
**Data:** Maggio 2026  
**Autore:** SynthTrade Dev Plan

> **v2.0** — Aggiunta architettura Signal Intelligence con dati di mercato reali
> (Funding Rate, CVD, Open Interest, On-Chain, Sentiment, Opportunity Monitor).
> Le strategie tecniche classiche diventano filtri secondari, non segnali primari.

---

## Indice

1. [Overview del Modulo](#1-overview-del-modulo)
2. [Architettura Generale](#2-architettura-generale)
3. [Struttura File e Directory](#3-struttura-file-e-directory)
4. [Componenti Backend (FastAPI)](#4-componenti-backend-fastapi)
5. [Componenti Frontend (Angular)](#5-componenti-frontend-angular)
6. [Integrazione Agente AI (Claude)](#6-integrazione-agente-ai-claude)
7. [Signal Intelligence — Dati di Mercato Reali](#7-signal-intelligence--dati-di-mercato-reali)
8. [Opportunity Monitor](#8-opportunity-monitor)
9. [Database — Supabase](#9-database--supabase)
10. [Fasi di Sviluppo](#10-fasi-di-sviluppo)
11. [Testing Strategy](#11-testing-strategy)
12. [Rischi e Mitigazioni](#12-rischi-e-mitigazioni)

---

## 1. Overview del Modulo

### Obiettivo
Aggiungere a SynthTrade la capacità di operare in modalità **scalping intraday** in modo semi-automatico: l'app viene avviata la mattina, opera autonomamente durante le ore lavorative, e viene chiusa a fine giornata. Nessuna posizione aperta overnight.

### Principio di Funzionamento
Il modulo si divide in **due layer indipendenti** che operano a velocità diverse:

| Layer | Nome | Velocità | Responsabilità |
|---|---|---|---|
| L1 | Execution Engine | 500ms–2s | Esegue ordini, gestisce SL/TP |
| L2 | AI Supervisor | 5–15 min | Analizza performance, aggiorna parametri |

### Modalità Operative
- **BACKTEST** — Simulazione su dati storici, zero rischio
- **PAPER** — Live su Binance Testnet, zero rischio
- **LIVE** — Reale su Binance Mainnet, rischio reale

---

## 2. Architettura Generale

```
┌──────────────────────────────────────────────────────────────────────┐
│                          ANGULAR FRONTEND                            │
│                                                                      │
│  ScalpingDashboard  StrategyPanel   PerformancePanel                 │
│  LiveChart          SupervisorLog   RiskControls                     │
│  MarketIntelPanel   OpportunityFeed SignalScorecard                  │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ HTTP / WebSocket
┌──────────────────────────────▼───────────────────────────────────────┐
│                          FASTAPI BACKEND                             │
│                                                                      │
│  ┌───────────────────────┐    ┌─────────────────────────────────┐   │
│  │   EXECUTION ENGINE    │    │        AI SUPERVISOR            │   │
│  │   (Layer 1 — veloce)  │    │        (Layer 2 — lento)        │   │
│  │                       │◀───│                                 │   │
│  │  SignalAggregator     │    │  ContextBuilder (arricchito)    │   │
│  │  RegimeDetector       │    │  ClaudeAPIClient                │   │
│  │  StrategySelector     │    │  ParameterUpdater               │   │
│  │  OrderExecutor        │    │  SupervisorScheduler            │   │
│  │  PositionManager      │    └─────────────────────────────────┘   │
│  │  RiskManager          │                                           │
│  └───────────┬───────────┘                                           │
│              │                                                        │
│  ┌───────────▼──────────────────────────────────────────────────┐   │
│  │               SIGNAL INTELLIGENCE (nuovo)                    │   │
│  │                                                              │   │
│  │  FundingRateCollector    OpenInterestCollector               │   │
│  │  CVDCalculator           LongShortRatioCollector             │   │
│  │  FearGreedCollector      OnChainCollector                    │   │
│  │  SentimentCollector      SignalScoreEngine                   │   │
│  └───────────┬──────────────────────────────────────────────────┘   │
│              │                                                        │
│  ┌───────────▼──────────────────────────────────────────────────┐   │
│  │               OPPORTUNITY MONITOR (nuovo)                    │   │
│  │                                                              │   │
│  │  BinanceRSSPoller        CryptoPanicPoller                   │   │
│  │  CoinGeckoPoller         WhaleAlertPoller                    │   │
│  │  AnnouncementClassifier  OpportunityRouter                   │   │
│  └───────────┬──────────────────────────────────────────────────┘   │
│              │                                                        │
│  ┌───────────▼──────────┐    ┌──────────────────────────────────┐   │
│  │  WebSocket Manager   │    │  REST API Router                 │   │
│  │  (Binance feed)      │    │  /scalping/* /intelligence/*     │   │
│  └──────────────────────┘    └──────────────────────────────────┘   │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
         ┌─────────────────────┼───────────────────────┐
         │                     │                        │
┌────────▼───────┐  ┌──────────▼──────────┐  ┌────────▼────────────┐
│  BINANCE API   │  │  EXTERNAL APIs      │  │  SUPABASE           │
│                │  │                     │  │                     │
│  WS streams    │  │  CryptoPanic        │  │  trades             │
│  REST orders   │  │  CoinGecko          │  │  signal_snapshots   │
│  Futures API   │  │  Alternative.me     │  │  opportunities      │
│  (funding,OI)  │  │  Whale Alert        │  │  supervisor_log     │
│  Binance RSS   │  │  Glassnode (free)   │  │  market_intel_log   │
└────────────────┘  └─────────────────────┘  └─────────────────────┘
```

### Principio chiave v2.0
> Le strategie tecniche (EMA, RSI, BB) diventano **filtri di timing**,
> non sorgenti di segnale primarie. Il segnale primario viene da
> **Funding Rate + CVD + Open Interest + Sentiment**.
> Una strategia tecnica si attiva solo se il contesto macro lo supporta.

```
PRIMA (v1.0):
  EMA cross → BUY

ORA (v2.0):
  Funding Rate overleveraged long     ┐
  + CVD negativo (pressione sell)     ├─→ SHORT con alta confidenza
  + OI in crescita (esposizione alta) │
  + Fear & Greed > 75 (euforia)       ┘
  + EMA cross conferma (filtro timing)
```

---

## 3. Struttura File e Directory

### Backend (FastAPI)

```
app/
└── scalping/
    ├── __init__.py
    │
    ├── models/                          # Pydantic models
    │   ├── strategy.py                  # ScalpingStrategy, StrategyParams
    │   ├── signal.py                    # Signal, SignalType, SignalStrength
    │   ├── position.py                  # Position, PositionStatus
    │   ├── trade.py                     # Trade, TradeResult
    │   ├── market.py                    # Candle, OrderBook, MarketRegime
    │   ├── supervisor.py                # SupervisorDecision, SupervisorContext
    │   ├── intelligence.py              # FundingRate, OpenInterest, CVD, ...
    │   └── opportunity.py               # Opportunity, OpportunityCategory
    │
    ├── strategies/                      # Implementazioni strategie
    │   ├── base.py                      # AbstractScalpingStrategy
    │   ├── ema_cross.py                 # EMA 9/21 (filtro timing)
    │   ├── rsi_bollinger.py             # RSI + BB (filtro timing)
    │   ├── vwap_reversion.py            # VWAP (filtro timing)
    │   └── registry.py                  # StrategyRegistry
    │
    ├── engine/                          # Layer 1 - Execution
    │   ├── signal_aggregator.py         # ★ NUOVO — combina tutti i segnali
    │   ├── regime_detector.py           # Identifica regime di mercato
    │   ├── strategy_selector.py         # Sceglie strategia dal regime
    │   ├── signal_generator.py          # Genera segnali tecnici (ora secondari)
    │   ├── order_executor.py            # Invia ordini a Binance
    │   ├── position_manager.py          # Gestisce posizioni aperte
    │   ├── risk_manager.py              # Circuit breaker, max drawdown
    │   └── execution_loop.py            # Main loop asincrono
    │
    ├── intelligence/                    # ★ NUOVO — Signal Intelligence
    │   ├── collectors/
    │   │   ├── funding_rate.py          # Binance Futures API funding rate
    │   │   ├── open_interest.py         # Binance Futures API open interest
    │   │   ├── long_short_ratio.py      # Binance long/short ratio
    │   │   ├── cvd_calculator.py        # Cumulative Volume Delta (da WS trades)
    │   │   ├── fear_greed.py            # alternative.me API
    │   │   ├── onchain.py               # Glassnode free tier
    │   │   └── sentiment.py             # CryptoPanic API
    │   ├── signal_score_engine.py       # Combina tutti i segnali in score 0-100
    │   ├── market_context.py            # Snapshot aggregato del contesto
    │   └── intelligence_scheduler.py   # Aggiorna dati ogni N secondi/minuti
    │
    ├── opportunity/                     # ★ NUOVO — Opportunity Monitor
    │   ├── pollers/
    │   │   ├── binance_rss.py           # RSS Binance announcements
    │   │   ├── cryptopanic.py           # CryptoPanic news feed
    │   │   ├── coingecko.py             # Trending, nuove listing
    │   │   └── whale_alert.py           # Whale Alert API
    │   ├── classifier.py                # Claude API: classifica opportunità
    │   ├── opportunity_router.py        # Smista per categoria e urgenza
    │   ├── deduplicator.py              # Evita duplicati tra fonti diverse
    │   └── opportunity_scheduler.py    # Polling ogni 5 minuti
    │
    ├── supervisor/                      # Layer 2 - AI Supervisor
    │   ├── context_builder.py           # Assembla contesto (ora include intel)
    │   ├── claude_client.py             # Chiamate API Claude
    │   ├── parameter_updater.py         # Applica nuovi parametri
    │   ├── decision_parser.py           # Parsa risposta Claude → oggetto
    │   └── supervisor_scheduler.py      # Task periodico (APScheduler)
    │
    ├── indicators/                      # Calcolo indicatori tecnici (ora secondari)
    │   ├── moving_averages.py           # EMA, SMA, VWAP
    │   ├── oscillators.py               # RSI, MACD, Stochastic
    │   ├── volatility.py                # ATR, Bollinger Bands
    │   └── volume.py                    # OBV, Volume Profile
    │
    ├── data/
    │   ├── candle_buffer.py
    │   ├── market_snapshot.py
    │   └── historical_loader.py
    │
    ├── backtest/
    │   ├── backtest_engine.py
    │   ├── performance_calculator.py
    │   └── report_generator.py
    │
    ├── session/
    │   ├── session_manager.py
    │   ├── daily_summary.py
    │   └── session_state.py
    │
    └── router.py                        # FastAPI router /scalping/* /intelligence/* /opportunities/*
```

### Frontend (Angular)

```
src/app/
└── scalping/
    ├── scalping.module.ts
    ├── scalping-routing.module.ts
    │
    ├── models/
    │   ├── strategy.model.ts
    │   ├── signal.model.ts
    │   ├── position.model.ts
    │   ├── trade.model.ts
    │   ├── session.model.ts
    │   ├── intelligence.model.ts        # ★ NUOVO
    │   └── opportunity.model.ts         # ★ NUOVO
    │
    ├── services/
    │   ├── scalping-api.service.ts
    │   ├── scalping-ws.service.ts
    │   ├── session.service.ts
    │   ├── performance.service.ts
    │   ├── intelligence-api.service.ts  # ★ NUOVO
    │   └── opportunity-api.service.ts   # ★ NUOVO
    │
    ├── store/
    │   ├── scalping.actions.ts
    │   ├── scalping.reducer.ts
    │   ├── scalping.effects.ts
    │   └── scalping.selectors.ts
    │
    └── components/
        ├── scalping-dashboard/
        ├── session-controls/
        ├── strategy-panel/
        ├── live-chart/
        ├── position-ticker/
        ├── trade-log/
        ├── performance-panel/
        ├── supervisor-log/
        ├── risk-controls/
        │
        ├── market-intel-panel/          # ★ NUOVO
        │   ├── market-intel-panel.component.ts
        │   └── market-intel-panel.component.html
        │   # Mostra: funding rate, OI, CVD, Fear&Greed, Long/Short ratio
        │
        ├── signal-scorecard/            # ★ NUOVO
        │   ├── signal-scorecard.component.ts
        │   └── signal-scorecard.component.html
        │   # Score aggregato 0-100 con breakdown per categoria
        │
        └── opportunity-feed/            # ★ NUOVO
            ├── opportunity-feed.component.ts
            └── opportunity-feed.component.html
            # Feed real-time opportunità classificate dall'AI
```

---

## 4. Componenti Backend (FastAPI)

### 4.1 Models (`models/`)

```python
# models/strategy.py
from pydantic import BaseModel
from enum import Enum

class StrategyType(str, Enum):
    EMA_CROSS = "ema_cross"
    RSI_BOLLINGER = "rsi_bollinger"
    VWAP_REVERSION = "vwap_reversion"

class StrategyParams(BaseModel):
    stop_loss_pct: float = 0.005        # 0.5%
    take_profit_pct: float = 0.010      # 1.0%
    position_size_pct: float = 0.05     # 5% del capitale
    max_trades_per_day: int = 20
    min_volume_multiplier: float = 1.2  # volume > 1.2x media
    # Parametri specifici per strategia
    ema_fast: int = 9
    ema_slow: int = 21
    rsi_period: int = 14
    rsi_oversold: float = 35.0
    rsi_overbought: float = 65.0
    bb_period: int = 20
    bb_std: float = 2.0

class ScalpingStrategy(BaseModel):
    id: str
    type: StrategyType
    params: StrategyParams
    is_active: bool = False
    created_at: datetime
    updated_at: datetime

# models/market.py
class MarketRegime(str, Enum):
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    LATERAL = "lateral"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"

class Candle(BaseModel):
    open_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    close_time: datetime

# models/signal.py
class SignalType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    CLOSE = "CLOSE"         # chiudi posizione aperta

class Signal(BaseModel):
    type: SignalType
    strategy_type: StrategyType
    price: float
    timestamp: datetime
    confidence: float       # 0.0 - 1.0
    reason: str             # descrizione leggibile del segnale

# models/supervisor.py
class SupervisorAction(str, Enum):
    UPDATE_PARAMS = "update_params"
    CHANGE_STRATEGY = "change_strategy"
    PAUSE_TRADING = "pause_trading"
    RESUME_TRADING = "resume_trading"
    NO_ACTION = "no_action"

class SupervisorDecision(BaseModel):
    action: SupervisorAction
    reason: str
    new_params: StrategyParams | None = None
    new_strategy: StrategyType | None = None
    confidence: float
    timestamp: datetime
```

### 4.2 Strategie (`strategies/`)

```python
# strategies/base.py
from abc import ABC, abstractmethod

class AbstractScalpingStrategy(ABC):
    def __init__(self, params: StrategyParams):
        self.params = params

    @abstractmethod
    def evaluate(self, candles: list[Candle], indicators: dict) -> Signal:
        """Valuta le candele e restituisce un segnale."""
        pass

    @abstractmethod
    def get_required_candles(self) -> int:
        """Numero minimo di candele necessarie."""
        pass

# strategies/ema_cross.py
class EMACrossStrategy(AbstractScalpingStrategy):
    """
    Segnale BUY:  EMA fast incrocia sopra EMA slow
                  + volume > media * multiplier
                  + candle close > open (candela rialzista)
    
    Segnale SELL: EMA fast incrocia sotto EMA slow
                  + posizione aperta

    Funziona in: mercato TRENDING
    Evitare in:  mercato LATERAL (molti falsi segnali)
    """
    def evaluate(self, candles: list[Candle], indicators: dict) -> Signal:
        ema_fast = indicators['ema_fast']
        ema_slow = indicators['ema_slow']
        volume = indicators['volume_avg']
        current_candle = candles[-1]

        # Cross detection: confronto t-1 con t
        prev_diff = ema_fast[-2] - ema_slow[-2]
        curr_diff = ema_fast[-1] - ema_slow[-1]

        volume_ok = current_candle.volume > volume * self.params.min_volume_multiplier
        bullish_candle = current_candle.close > current_candle.open

        if prev_diff < 0 and curr_diff > 0 and volume_ok and bullish_candle:
            return Signal(type=SignalType.BUY, ...)

        if prev_diff > 0 and curr_diff < 0:
            return Signal(type=SignalType.CLOSE, ...)

        return Signal(type=SignalType.HOLD, ...)

# strategies/rsi_bollinger.py
class RSIBollingerStrategy(AbstractScalpingStrategy):
    """
    Segnale BUY:  RSI < rsi_oversold
                  + prezzo tocca/supera banda inferiore BB
                  + candela mostra rimbalzo (close > open)

    Segnale SELL: RSI > rsi_overbought
                  + prezzo tocca/supera banda superiore BB

    Funziona in: mercato LATERAL
    Evitare in:  mercato TRENDING (il prezzo può rimanere overbought a lungo)
    """
    ...

# strategies/vwap_reversion.py
class VWAPReversionStrategy(AbstractScalpingStrategy):
    """
    Ogni sessione la VWAP si resetta alla mezzanotte.
    Il prezzo tende a tornare alla VWAP durante la giornata.

    Segnale BUY:  prezzo scende > 0.3% sotto VWAP
                  + RSI < 40
                  + Volume in aumento

    Target:       ritorno alla VWAP (take profit dinamico)

    Funziona in:  qualsiasi regime (specialmente intraday)
    Perfetta per: scenario "trader a giornata" (VWAP si resetta ogni mattina)
    """
    ...
```

### 4.3 Engine — Layer 1 (`engine/`)

```python
# engine/regime_detector.py
class RegimeDetector:
    """
    Analizza le ultime N candele e determina il regime di mercato.
    
    Indicatori usati:
    - ADX (Average Directional Index): misura forza del trend
    - ATR (Average True Range): misura volatilità
    - BB Width: larghezza bande di Bollinger (volatilità relativa)
    """

    def detect(self, candles: list[Candle], indicators: dict) -> MarketRegime:
        adx = indicators['adx'][-1]
        atr = indicators['atr'][-1]
        atr_avg = sum(indicators['atr'][-20:]) / 20
        bb_width = indicators['bb_upper'][-1] - indicators['bb_lower'][-1]

        if atr > atr_avg * 2.0:
            return MarketRegime.HIGH_VOLATILITY     # pausa o VWAP

        if adx > 25:
            if indicators['ema_fast'][-1] > indicators['ema_slow'][-1]:
                return MarketRegime.TRENDING_UP     # EMA Cross
            else:
                return MarketRegime.TRENDING_DOWN   # EMA Cross (short)

        if adx < 20 and bb_width < bb_width_avg * 0.8:
            return MarketRegime.LOW_VOLATILITY      # RSI+BB

        return MarketRegime.LATERAL                 # RSI+BB o VWAP


# engine/risk_manager.py
class RiskManager:
    """
    Circuit breaker: blocca il trading in caso di:
    - Max drawdown giornaliero superato
    - Troppi trade consecutivi in perdita
    - Perdita singola posizione > soglia
    - Mercato in HIGH_VOLATILITY prolungata
    """

    def __init__(self, config: RiskConfig):
        self.max_daily_loss_pct = config.max_daily_loss_pct     # es. 3%
        self.max_consecutive_losses = config.max_consecutive_losses  # es. 5
        self.consecutive_losses = 0
        self.daily_pnl = 0.0

    def check_pre_trade(self, capital: float) -> RiskCheckResult:
        """Chiamato PRIMA di ogni ordine."""
        if self.daily_pnl < -(capital * self.max_daily_loss_pct):
            return RiskCheckResult(allowed=False, reason="Max daily loss reached")

        if self.consecutive_losses >= self.max_consecutive_losses:
            return RiskCheckResult(allowed=False, reason="Too many consecutive losses")

        return RiskCheckResult(allowed=True)

    def on_trade_closed(self, trade: TradeResult):
        """Aggiorna stato dopo ogni trade chiuso."""
        self.daily_pnl += trade.pnl
        if trade.pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0


# engine/execution_loop.py
class ExecutionLoop:
    """
    Main loop del Layer 1. Gira ogni 500ms-2s.
    Non contiene logica di business: delega tutto ai componenti.
    """

    def __init__(self, ...):
        self.running = False
        self.paused = False
        self.candle_buffer = CandleBuffer(symbol, timeframe)
        self.regime_detector = RegimeDetector()
        self.strategy_selector = StrategySelector()
        self.signal_generator = SignalGenerator()
        self.position_manager = PositionManager()
        self.risk_manager = RiskManager(config.risk)
        self.order_executor = OrderExecutor(binance_client)

    async def start(self):
        self.running = True
        async for candle in self.ws_manager.stream(self.symbol):
            if not self.running:
                break
            if self.paused:
                continue
            await self._process_candle(candle)

    async def _process_candle(self, candle: Candle):
        self.candle_buffer.add(candle)

        if not self.candle_buffer.is_ready():
            return

        candles = self.candle_buffer.get()
        indicators = self.indicator_engine.calculate(candles)

        # 1. Detecta regime
        regime = self.regime_detector.detect(candles, indicators)

        # 2. Seleziona strategia appropriata
        strategy = self.strategy_selector.select(regime)

        # 3. Genera segnale
        signal = strategy.evaluate(candles, indicators)

        # 4. Risk check
        risk_result = self.risk_manager.check_pre_trade(self.capital)
        if not risk_result.allowed:
            await self._emit_event("risk_block", risk_result.reason)
            return

        # 5. Esegui se segnale valido
        if signal.type == SignalType.BUY and not self.position_manager.has_open():
            order = await self.order_executor.buy(signal)
            await self.position_manager.open(order, signal)

        elif signal.type in (SignalType.SELL, SignalType.CLOSE):
            if self.position_manager.has_open():
                order = await self.order_executor.close()
                trade = await self.position_manager.close(order)
                self.risk_manager.on_trade_closed(trade)
                await self._save_trade(trade)

        # 6. Emetti evento WebSocket verso frontend
        await self._emit_market_update(candle, signal, indicators)
```

### 4.4 Supervisor — Layer 2 (`supervisor/`)

```python
# supervisor/context_builder.py
class ContextBuilder:
    """
    Assembla il contesto da passare a Claude per l'analisi.
    Include: trade recenti, performance, regime attuale, parametri attivi.
    """

    async def build(self, session: Session) -> SupervisorContext:
        recent_trades = await self.db.get_recent_trades(limit=30)
        win_rate = self._calculate_win_rate(recent_trades)
        avg_pnl = self._calculate_avg_pnl(recent_trades)
        current_regime = self.execution_loop.current_regime
        active_params = self.execution_loop.active_strategy.params
        market_snapshot = self.execution_loop.last_snapshot

        return SupervisorContext(
            session_id=session.id,
            elapsed_minutes=session.elapsed_minutes,
            recent_trades=recent_trades,
            win_rate=win_rate,
            avg_pnl=avg_pnl,
            current_regime=current_regime,
            active_strategy=self.execution_loop.active_strategy.type,
            active_params=active_params,
            current_atr=market_snapshot.atr,
            current_volume=market_snapshot.volume,
            daily_pnl=session.daily_pnl,
            consecutive_losses=self.risk_manager.consecutive_losses,
        )


# supervisor/claude_client.py
SUPERVISOR_SYSTEM_PROMPT = """
Sei un supervisore esperto di trading algoritmico specializzato in scalping intraday su criptovalute.

Il tuo compito è analizzare le performance recenti di una strategia di scalping automatica
e decidere se aggiornare i parametri, cambiare strategia, o sospendere il trading.

Rispondi ESCLUSIVAMENTE con un JSON valido nel seguente formato:
{
  "action": "update_params" | "change_strategy" | "pause_trading" | "resume_trading" | "no_action",
  "reason": "spiegazione della decisione in italiano",
  "confidence": 0.0-1.0,
  "new_params": { ... } | null,
  "new_strategy": "ema_cross" | "rsi_bollinger" | "vwap_reversion" | null
}

Principi da seguire:
- Un win rate < 40% su 15+ trade è un segnale di allarme
- Un ATR aumentato del 50%+ rispetto alla media indica alta volatilità: allarga SL/TP
- Più di 5 perdite consecutive: valuta pausa o cambio strategia
- Il mercato LATERAL con EMA Cross attiva genera falsi segnali: suggerisci RSI+BB
- VWAP Reversion è sempre sicura per scenario intraday, soprattutto nelle prime ore
"""

class ClaudeClient:
    async def analyze(self, context: SupervisorContext) -> SupervisorDecision:
        prompt = self._build_prompt(context)

        response = await anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=SUPERVISOR_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )

        raw_json = response.content[0].text
        return self.decision_parser.parse(raw_json)

    def _build_prompt(self, ctx: SupervisorContext) -> str:
        return f"""
Analisi sessione di scalping:

📊 PERFORMANCE (ultimi {len(ctx.recent_trades)} trade):
- Win Rate: {ctx.win_rate:.1%}
- PNL medio per trade: {ctx.avg_pnl:.4f} USDT
- PNL giornaliero totale: {ctx.daily_pnl:.4f} USDT
- Perdite consecutive: {ctx.consecutive_losses}

📈 MERCATO ATTUALE:
- Regime: {ctx.current_regime}
- ATR corrente: {ctx.current_atr:.6f}
- Volume relativo: {ctx.current_volume:.2f}x media

⚙️ CONFIGURAZIONE ATTIVA:
- Strategia: {ctx.active_strategy}
- Stop Loss: {ctx.active_params.stop_loss_pct:.3%}
- Take Profit: {ctx.active_params.take_profit_pct:.3%}
- Position Size: {ctx.active_params.position_size_pct:.1%}

Decidi cosa fare.
"""
```

### 4.5 REST API Router (`router.py`)

```python
# router.py
from fastapi import APIRouter

router = APIRouter(prefix="/scalping", tags=["scalping"])

# Sessione
POST   /scalping/session/start          # avvia sessione
POST   /scalping/session/stop           # ferma sessione
POST   /scalping/session/pause          # pausa
GET    /scalping/session/status         # stato corrente

# Strategie
GET    /scalping/strategies             # lista strategie disponibili
GET    /scalping/strategies/active      # strategia attiva + parametri
PATCH  /scalping/strategies/params      # aggiorna parametri manualmente

# Trade
GET    /scalping/trades                 # storico trade sessione corrente
GET    /scalping/trades/open            # posizione aperta (se esiste)
GET    /scalping/performance            # metriche performance sessione

# Supervisor
GET    /scalping/supervisor/log         # log decisioni AI
POST   /scalping/supervisor/trigger     # forza analisi manuale

# Backtest
POST   /scalping/backtest/run           # avvia backtest
GET    /scalping/backtest/{id}/result   # risultato backtest

# WebSocket
WS     /ws/scalping                     # stream eventi real-time
```

---

## 5. Componenti Frontend (Angular)

### 5.1 WebSocket Service

```typescript
// services/scalping-ws.service.ts
export interface ScalpingEvent {
  type: 'candle' | 'signal' | 'order' | 'position' | 'supervisor' | 'risk_block';
  payload: any;
  timestamp: string;
}

@Injectable({ providedIn: 'root' })
export class ScalpingWsService {
  private ws$: WebSocketSubject<ScalpingEvent>;
  
  // Subject separati per tipo evento
  candle$ = new Subject<CandleEvent>();
  signal$ = new Subject<SignalEvent>();
  position$ = new Subject<PositionEvent>();
  supervisorDecision$ = new Subject<SupervisorDecision>();
  riskBlock$ = new Subject<RiskBlockEvent>();

  connect(): void {
    this.ws$ = webSocket<ScalpingEvent>('ws://localhost:8000/ws/scalping');
    this.ws$.pipe(
      retryWhen(errors => errors.pipe(delay(3000)))  // auto-reconnect
    ).subscribe(event => this._dispatch(event));
  }

  private _dispatch(event: ScalpingEvent): void {
    switch (event.type) {
      case 'candle':     this.candle$.next(event.payload); break;
      case 'signal':     this.signal$.next(event.payload); break;
      case 'position':   this.position$.next(event.payload); break;
      case 'supervisor': this.supervisorDecision$.next(event.payload); break;
      case 'risk_block': this.riskBlock$.next(event.payload); break;
    }
  }
}
```

### 5.2 Session Controls Component

```typescript
// components/session-controls/session-controls.component.ts
@Component({
  selector: 'app-session-controls',
  template: `
    <div class="session-controls">
      <div class="mode-selector">
        <button [class.active]="mode === 'PAPER'" (click)="setMode('PAPER')">Paper</button>
        <button [class.active]="mode === 'LIVE'" (click)="setMode('LIVE')">Live</button>
      </div>

      <div class="pair-selector">
        <select [(ngModel)]="selectedPair">
          <option value="BTCUSDT">BTC/USDT</option>
          <option value="ETHUSDT">ETH/USDT</option>
          <option value="BNBUSDT">BNB/USDT</option>
        </select>
      </div>

      <div class="actions">
        <button 
          *ngIf="!session || session.status === 'stopped'"
          (click)="startSession()" 
          class="btn-start">
          ▶ Avvia Sessione
        </button>
        
        <button 
          *ngIf="session?.status === 'running'"
          (click)="pauseSession()" 
          class="btn-pause">
          ⏸ Pausa
        </button>

        <button 
          *ngIf="session?.status === 'running' || session?.status === 'paused'"
          (click)="stopSession()" 
          class="btn-stop">
          ⏹ Ferma
        </button>
      </div>

      <div class="session-info" *ngIf="session">
        <span class="status-badge" [class]="session.status">
          {{ session.status | uppercase }}
        </span>
        <span>{{ session.elapsed | duration }}</span>
        <span>Trade oggi: {{ session.tradeCount }}</span>
      </div>
    </div>
  `
})
export class SessionControlsComponent { ... }
```

### 5.3 Live Chart Component

```typescript
// components/live-chart/live-chart.component.ts
// Usa lightweight-charts (libreria TradingView) per candlestick
@Component({
  selector: 'app-live-chart',
  template: `
    <div class="chart-container">
      <div class="chart-header">
        <span class="pair">{{ pair }}</span>
        <span class="regime-badge" [class]="regime">{{ regime }}</span>
        <span class="strategy-badge">{{ activeStrategy }}</span>
      </div>
      
      <div #chartContainer class="chart"></div>
      
      <!-- Overlay segnali -->
      <div class="signal-overlay">
        <div *ngFor="let signal of recentSignals" 
             class="signal-marker"
             [class.buy]="signal.type === 'BUY'"
             [class.sell]="signal.type === 'SELL'">
          {{ signal.type }} @ {{ signal.price | currency:'EUR' }}
        </div>
      </div>
    </div>
  `
})
export class LiveChartComponent implements AfterViewInit, OnDestroy {
  @ViewChild('chartContainer') chartContainer!: ElementRef;
  
  private chart: IChartApi;
  private candleSeries: ISeriesApi<'Candlestick'>;

  ngAfterViewInit(): void {
    this.chart = createChart(this.chartContainer.nativeElement, {
      width: 800,
      height: 400,
      layout: { background: { color: '#1a1a2e' }, textColor: '#ffffff' },
      grid: { vertLines: { color: '#2a2a4a' }, horzLines: { color: '#2a2a4a' } }
    });

    this.candleSeries = this.chart.addCandlestickSeries();

    // Subscribe al WebSocket
    this.wsService.candle$.pipe(takeUntil(this.destroy$))
      .subscribe(candle => {
        this.candleSeries.update({
          time: candle.closeTime / 1000,
          open: candle.open,
          high: candle.high,
          low: candle.low,
          close: candle.close
        });
      });
  }
}
```

### 5.4 Performance Panel

```typescript
// components/performance-panel/performance-panel.component.ts
// Mostra metriche chiave della sessione corrente

interface PerformanceMetrics {
  totalPnl: number;
  totalPnlPct: number;
  winRate: number;
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
  avgWin: number;
  avgLoss: number;
  profitFactor: number;      // gross profit / gross loss
  maxDrawdown: number;
  consecutiveLosses: number;
  sharpeRatio: number;       // opzionale, calcolato su sessioni storiche
}
```

---

## 6. Integrazione Agente AI (Claude)

### 6.1 Flusso Supervisor (arricchito v2.0)

```
Ogni 10 minuti:

1. ContextBuilder assembla snapshot completo:
   - Trade recenti + performance
   - Signal Intelligence snapshot (funding, OI, CVD, sentiment)
   - Opportunità recenti dal feed
   - Regime di mercato attuale
2. ClaudeClient invia a claude-sonnet-4-20250514
3. DecisionParser valida e parsa JSON risposta
4. ParameterUpdater applica aggiornamenti all'ExecutionLoop
5. Evento WebSocket → frontend mostra log decisione
6. SupervisorDecision salvata su Supabase
```

### 6.2 Tipi di Decisione

| Azione | Trigger tipico | Effetto |
|---|---|---|
| `update_params` | ATR cambiato, win rate in calo | Aggiorna SL/TP/size senza fermare |
| `change_strategy` | Regime cambiato | Swap strategia al prossimo candle |
| `pause_trading` | Mercato caotico, troppe perdite | Ferma loop |
| `resume_trading` | Dopo pausa, condizioni migliorate | Riavvia loop |
| `no_action` | Tutto ok | Log di conferma |

### 6.3 System Prompt Supervisor v2.0

```python
SUPERVISOR_SYSTEM_PROMPT = """
Sei un supervisore esperto di trading algoritmico specializzato in scalping
intraday su criptovalute. Hai accesso a dati di mercato reali, non solo
indicatori tecnici.

Il tuo compito è analizzare il CONTESTO COMPLETO del mercato e decidere
se aggiornare i parametri, cambiare strategia, o sospendere il trading.

GERARCHIA DEI SEGNALI che devi considerare (in ordine di importanza):
1. Funding Rate — se > 0.1% il mercato è overleveraged long → short bias
2. CVD (Cumulative Volume Delta) — pressione reale buy/sell
3. Open Interest — se cresce + prezzo laterale → breakout imminente
4. Long/Short Ratio — contrarian: se > 70% long, il mercato è esposto
5. Fear & Greed — estremi (< 20 o > 80) = potenziale inversione
6. On-chain Exchange Flow — BTC entra negli exchange = sell pressure
7. Sentiment news — solo come conferma, non come segnale primario
8. Indicatori tecnici (EMA, RSI, BB) — solo come filtri di timing

Rispondi ESCLUSIVAMENTE con JSON valido:
{
  "action": "update_params|change_strategy|pause_trading|resume_trading|no_action",
  "reason": "spiegazione in italiano con riferimento ai dati reali",
  "confidence": 0.0-1.0,
  "market_bias": "bullish|bearish|neutral",
  "primary_signal": "quale segnale ha guidato la decisione",
  "new_params": { ... } | null,
  "new_strategy": "ema_cross|rsi_bollinger|vwap_reversion" | null
}
"""
```

### 6.4 Opportunity Classifier

```python
CLASSIFIER_SYSTEM_PROMPT = """
Analizza annunci e news crypto e classifica le opportunità di trading.

Rispondi SOLO con JSON:
{
  "category": "new_listing|launchpool|promotion|delisting|maintenance|irrelevant",
  "urgency": "high|medium|low",
  "scalping_opportunity": true|false,
  "action": "descrizione azione consigliata",
  "symbol": "es. NOTUSDT o null",
  "time_sensitive": true|false,
  "expected_volatility": "high|medium|low|unknown"
}
"""
```

---

## 7. Signal Intelligence — Dati di Mercato Reali

### 7.1 Panoramica Fonti

| Fonte | Dati | Endpoint/URL | Frequenza aggiornamento | Costo |
|---|---|---|---|---|
| Binance Futures API | Funding Rate | `/fapi/v1/fundingRate` | Ogni 8h (snapshot ogni 1min) | Gratuito |
| Binance Futures API | Open Interest | `/fapi/v1/openInterest` | Real-time | Gratuito |
| Binance Futures API | Long/Short Ratio | `/futures/data/globalLongShortAccountRatio` | 5min | Gratuito |
| WebSocket Binance | CVD (da trade stream) | `wss://stream.binance.com/ws/<symbol>@trade` | Real-time | Gratuito |
| Alternative.me | Fear & Greed Index | `https://api.alternative.me/fng/` | 1 volta al giorno | Gratuito |
| CryptoPanic | News + Sentiment | `https://cryptopanic.com/api/v1/posts/` | 5min | Free tier |
| Glassnode | On-chain (Exchange Flow) | `https://api.glassnode.com/v1/metrics/` | 1h (free tier) | Free tier |
| Binance RSS | Annunci ufficiali | `https://www.binance.com/en/support/announcement/rss` | 5min | Gratuito |
| CoinGecko | Trending, listing | `https://api.coingecko.com/api/v3/` | 5min | Free tier |
| Whale Alert | Grandi transazioni | `https://api.whale-alert.io/v1/transactions` | 1min | Free tier |

### 7.2 Implementazione Collectors

```python
# intelligence/collectors/funding_rate.py
class FundingRateCollector:
    """
    Recupera il funding rate corrente dal mercato futures Binance.

    Funding Rate positivo  → i long pagano gli short
                           → mercato overleveraged long
                           → bias verso SHORT o cautela sui long
    
    Funding Rate negativo  → gli short pagano i long
                           → mercato overleveraged short
                           → bias verso LONG
    
    Soglie indicative:
    > +0.10%  = fortemente overleveraged long (segnale contrarian short)
    > +0.05%  = moderatamente rialzista
    0%        = equilibrio
    < -0.05%  = moderatamente ribassista
    < -0.10%  = fortemente overleveraged short (segnale contrarian long)
    """
    BASE_URL = "https://fapi.binance.com"

    async def fetch(self, symbol: str = "BTCUSDT") -> FundingRateSnapshot:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.BASE_URL}/fapi/v1/fundingRate",
                params={"symbol": symbol, "limit": 1}
            ) as resp:
                data = await resp.json()
                return FundingRateSnapshot(
                    symbol=symbol,
                    rate=float(data[0]['fundingRate']),
                    next_funding_time=data[0]['fundingTime'],
                    timestamp=datetime.utcnow()
                )


# intelligence/collectors/cvd_calculator.py
class CVDCalculator:
    """
    Cumulative Volume Delta — calcola la pressione netta buy vs sell
    in tempo reale dal WebSocket trades di Binance.

    Ogni trade ha un lato "maker" (chi aspettava) e "taker" (chi ha eseguito).
    - Taker BUY  = buy aggressivo → +volume al CVD
    - Taker SELL = sell aggressivo → -volume al CVD

    CVD crescente  = più pressione buy reale → momentum rialzista
    CVD calante    = più pressione sell reale → momentum ribassista
    CVD divergente dal prezzo = segnale forte di inversione imminente
    """

    def __init__(self):
        self._cvd: float = 0.0
        self._history: deque[CVDPoint] = deque(maxlen=500)

    def on_trade(self, trade: BinanceTrade):
        delta = trade.quantity if not trade.is_buyer_maker else -trade.quantity
        self._cvd += delta
        self._history.append(CVDPoint(cvd=self._cvd, timestamp=trade.time))

    def get_snapshot(self) -> CVDSnapshot:
        return CVDSnapshot(
            current=self._cvd,
            trend=self._calculate_trend(),  # crescente/calante/neutro
            divergence=self._check_price_divergence()
        )


# intelligence/collectors/long_short_ratio.py
class LongShortRatioCollector:
    """
    Rapporto tra posizioni long e short sul mercato futures Binance.
    
    > 70% long  = mercato eccessivamente ottimista → contrarian short
    < 30% long  = mercato eccessivamente pessimista → contrarian long
    
    NON va usato da solo — è un segnale contrarian che funziona
    meglio vicino a estremi di mercato.
    """
    ...


# intelligence/collectors/fear_greed.py
class FearGreedCollector:
    """
    Alternative.me Fear & Greed Index: 0 (Extreme Fear) → 100 (Extreme Greed)
    
    < 20  = Extreme Fear  → storico: buon momento per comprare
    20-40 = Fear
    40-60 = Neutral
    60-80 = Greed
    > 80  = Extreme Greed → storico: attenzione, possibile correzione
    
    Si aggiorna una volta al giorno. Da usare come contesto,
    non come segnale intraday.
    """
    API_URL = "https://api.alternative.me/fng/"

    async def fetch(self) -> FearGreedSnapshot:
        async with aiohttp.ClientSession() as session:
            async with session.get(self.API_URL) as resp:
                data = await resp.json()
                return FearGreedSnapshot(
                    value=int(data['data'][0]['value']),
                    classification=data['data'][0]['value_classification'],
                    timestamp=datetime.utcnow()
                )
```

### 7.3 Signal Score Engine

```python
# intelligence/signal_score_engine.py
class SignalScoreEngine:
    """
    Combina tutti i segnali in un punteggio aggregato da -100 a +100.
    
    +100 = segnale BUY fortissimo (tutti i segnali allineati al rialzo)
    -100 = segnale SELL fortissimo (tutti i segnali allineati al ribasso)
       0 = neutro / segnali contrastanti → meglio non tradare
    
    Pesi per segnale (calibrabili dall'AI Supervisor):
    """

    WEIGHTS = {
        'funding_rate':    0.25,  # segnale contrarian più affidabile
        'cvd':             0.25,  # pressione reale di mercato
        'open_interest':   0.15,  # contesto esposizione
        'long_short_ratio':0.15,  # sentiment contrarian
        'fear_greed':      0.10,  # contesto macro
        'onchain':         0.10,  # flussi exchange
    }

    def calculate(self, context: MarketContext) -> SignalScore:
        scores = {}

        # Funding Rate: positivo → score negativo (contrarian)
        fr = context.funding_rate.rate
        if fr > 0.001:    scores['funding_rate'] = -min(fr / 0.001 * 50, 100)
        elif fr < -0.001: scores['funding_rate'] = min(abs(fr) / 0.001 * 50, 100)
        else:             scores['funding_rate'] = 0

        # CVD: crescente → positivo, calante → negativo
        scores['cvd'] = context.cvd.trend_score  # -100 a +100

        # Long/Short: > 70% long → negativo (contrarian)
        ls = context.long_short_ratio.long_pct
        if ls > 70:   scores['long_short_ratio'] = -(ls - 70) * 3.33
        elif ls < 30: scores['long_short_ratio'] = (30 - ls) * 3.33
        else:         scores['long_short_ratio'] = 0

        # Fear & Greed: estremi → contrarian
        fg = context.fear_greed.value
        if fg > 80:   scores['fear_greed'] = -(fg - 80) * 5
        elif fg < 20: scores['fear_greed'] = (20 - fg) * 5
        else:         scores['fear_greed'] = 0

        # Score finale pesato
        total = sum(scores[k] * self.WEIGHTS[k] for k in scores)

        return SignalScore(
            total=round(total, 2),
            breakdown=scores,
            bias='bullish' if total > 20 else 'bearish' if total < -20 else 'neutral',
            tradeable=abs(total) > 30  # solo se segnale abbastanza forte
        )
```

### 7.4 Come i segnali influenzano l'esecuzione

```python
# engine/signal_aggregator.py — il nuovo cuore dell'execution engine
class SignalAggregator:
    """
    Combina segnale tecnico (strategia) + score intelligenza di mercato.
    
    Un ordine viene eseguito SOLO se entrambi sono allineati:
    - Score intelligenza > soglia (default: 30)
    - Strategia tecnica conferma (filtro timing)
    
    Questo elimina i falsi segnali tecnici quando il contesto macro
    dice il contrario.
    """

    def should_execute(
        self,
        technical_signal: Signal,
        market_score: SignalScore
    ) -> ExecutionDecision:

        # Gate 1: il mercato deve dare un segnale chiaro
        if not market_score.tradeable:
            return ExecutionDecision(
                execute=False,
                reason=f"Score intelligenza insufficiente ({market_score.total})"
            )

        # Gate 2: allineamento direzione
        score_bullish = market_score.bias == 'bullish'
        signal_buy    = technical_signal.type == SignalType.BUY

        if score_bullish != signal_buy:
            return ExecutionDecision(
                execute=False,
                reason=f"Segnale tecnico ({technical_signal.type}) in conflitto "
                       f"con intelligenza di mercato ({market_score.bias})"
            )

        return ExecutionDecision(
            execute=True,
            confidence=market_score.total / 100,
            reason=f"Segnali allineati: {market_score.primary_driver}"
        )
```

---

## 8. Opportunity Monitor

### 8.1 Flusso completo

```
Ogni 5 minuti:
1. Tutti i Poller recuperano nuovi contenuti
2. Deduplicator filtra già visti (hash del contenuto)
3. Classifier (Claude API) classifica ogni nuovo item
4. OpportunityRouter smista per categoria e urgenza
5. Se urgenza HIGH + scalping_opportunity → notifica immediata frontend
6. Se nuovo simbolo da monitorare → aggiunge a watchlist engine
7. Salva tutto su Supabase
```

### 8.2 Implementazione Pollers

```python
# opportunity/pollers/binance_rss.py
class BinanceRSSPoller:
    """
    Legge il feed RSS ufficiale Binance.
    Preferito allo scraping: stabile, no rischio ban, stesso contenuto.
    """
    RSS_URL = "https://www.binance.com/en/support/announcement/rss"

    async def poll(self) -> list[RawAnnouncement]:
        async with aiohttp.ClientSession() as session:
            async with session.get(self.RSS_URL) as resp:
                content = await resp.text()
                feed = feedparser.parse(content)
                return [
                    RawAnnouncement(
                        source="binance_rss",
                        title=entry.title,
                        summary=entry.summary,
                        url=entry.link,
                        published=entry.published_parsed,
                    )
                    for entry in feed.entries
                ]


# opportunity/pollers/cryptopanic.py
class CryptoPanicPoller:
    """
    CryptoPanic aggrega news da 50+ fonti crypto con score sentiment.
    Filter "important" restituisce solo news ad alto impatto.
    """
    BASE_URL = "https://cryptopanic.com/api/v1/posts/"

    async def poll(self, currencies: list[str] = ["BTC", "ETH"]) -> list[RawAnnouncement]:
        params = {
            "auth_token": settings.CRYPTOPANIC_TOKEN,
            "filter": "important",
            "currencies": ",".join(currencies),
            "public": "true"
        }
        # ... fetch e parsing


# opportunity/pollers/coingecko.py
class CoinGeckoPoller:
    """
    CoinGecko trending: le 7 coin più cercate nelle ultime 24h.
    Se una coin è trending e non ancora listata su Binance → opportunità.
    """
    TRENDING_URL = "https://api.coingecko.com/api/v3/search/trending"
    ...
```

### 8.3 Opportunity Feed nel Frontend

```typescript
// models/opportunity.model.ts
export interface Opportunity {
  id: string;
  source: 'binance_rss' | 'cryptopanic' | 'coingecko' | 'whale_alert';
  category: 'new_listing' | 'launchpool' | 'promotion' | 'delisting' | 'irrelevant';
  urgency: 'high' | 'medium' | 'low';
  scalpingOpportunity: boolean;
  title: string;
  action: string;
  symbol: string | null;
  expectedVolatility: 'high' | 'medium' | 'low' | 'unknown';
  timeSensitive: boolean;
  detectedAt: string;
  url: string;
}

// components/opportunity-feed — UI
/*
┌──────────────────────────────────────────────────┐
│  🔔 OPPORTUNITÀ RILEVATE            [filtri ▼]   │
├──────────────────────────────────────────────────┤
│  🔴 HIGH  │ 🚀 New Listing: NOTUSDT             │
│           │ "Scalping prime 2h dalla listing"   │
│           │ Volatilità attesa: ALTA             │
│           │ [Monitora]  [Ignora]      14:32     │
├──────────────────────────────────────────────────┤
│  🟡 MED   │ 📰 CryptoPanic: BTC ETF news        │
│           │ "Sentiment positivo, +momentum"     │
│           │ Fonte: Bloomberg  Sentiment: 0.78   │
│           │ [Dettagli]  [Ignora]      13:15     │
├──────────────────────────────────────────────────┤
│  🔵 LOW   │ 💰 Earn: USDT Flexible 8.5% APR     │
│           │ "Promozione settimanale attiva"     │
│           │ [Dettagli]  [Ignora]      12:00     │
└──────────────────────────────────────────────────┘
*/
```

### 8.4 Nuovi endpoint API

```
# Intelligence
GET  /intelligence/snapshot          # contesto mercato corrente completo
GET  /intelligence/funding-rate      # funding rate storico + corrente
GET  /intelligence/open-interest     # OI storico + corrente
GET  /intelligence/cvd               # CVD ultimi N minuti
GET  /intelligence/signal-score      # score aggregato corrente

# Opportunities
GET  /opportunities                  # lista con filtri (urgency, category)
GET  /opportunities/live             # WebSocket stream nuove opportunità
POST /opportunities/{id}/watchlist   # aggiungi simbolo a watchlist engine
POST /opportunities/{id}/ignore      # marca come ignorata
```

---

## 9. Database — Supabase

### Schema tabelle

```sql
-- Sessioni di trading
CREATE TABLE scalping_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users,
    mode TEXT CHECK (mode IN ('PAPER', 'LIVE', 'BACKTEST')),
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    status TEXT CHECK (status IN ('running', 'paused', 'stopped')),
    started_at TIMESTAMPTZ NOT NULL,
    stopped_at TIMESTAMPTZ,
    total_pnl NUMERIC(12,6) DEFAULT 0,
    trade_count INTEGER DEFAULT 0,
    win_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trade eseguiti
CREATE TABLE scalping_trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES scalping_sessions(id),
    symbol TEXT NOT NULL,
    side TEXT CHECK (side IN ('BUY', 'SELL')),
    entry_price NUMERIC(12,6) NOT NULL,
    exit_price NUMERIC(12,6),
    quantity NUMERIC(12,8) NOT NULL,
    pnl NUMERIC(12,6),
    pnl_pct NUMERIC(8,4),
    strategy_type TEXT NOT NULL,
    signal_reason TEXT,
    -- ★ NUOVO: contesto intelligenza al momento del trade
    signal_score NUMERIC(6,2),          -- score aggregato -100/+100
    funding_rate_at_entry NUMERIC(10,6),
    fear_greed_at_entry INTEGER,
    cvd_trend_at_entry TEXT,
    entry_time TIMESTAMPTZ NOT NULL,
    exit_time TIMESTAMPTZ,
    status TEXT CHECK (status IN ('open', 'closed', 'cancelled')),
    binance_order_id TEXT
);

-- Decisioni del supervisore AI
CREATE TABLE supervisor_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES scalping_sessions(id),
    action TEXT NOT NULL,
    reason TEXT NOT NULL,
    confidence NUMERIC(4,3),
    market_bias TEXT,
    primary_signal TEXT,               -- ★ NUOVO: quale segnale ha guidato
    previous_params JSONB,
    new_params JSONB,
    previous_strategy TEXT,
    new_strategy TEXT,
    decided_at TIMESTAMPTZ DEFAULT NOW()
);

-- Configurazione strategie per utente
CREATE TABLE scalping_strategies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users,
    type TEXT NOT NULL,
    params JSONB NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ★ NUOVO: Snapshot intelligenza di mercato (storico)
CREATE TABLE market_intel_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol TEXT NOT NULL,
    funding_rate NUMERIC(10,6),
    open_interest NUMERIC(20,2),
    long_pct NUMERIC(5,2),
    short_pct NUMERIC(5,2),
    cvd_trend TEXT,
    fear_greed_value INTEGER,
    fear_greed_label TEXT,
    signal_score NUMERIC(6,2),
    signal_bias TEXT,
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);
-- Indice per query storiche efficienti
CREATE INDEX idx_intel_symbol_time ON market_intel_snapshots(symbol, recorded_at DESC);

-- ★ NUOVO: Opportunità rilevate dall'Opportunity Monitor
CREATE TABLE opportunities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source TEXT NOT NULL,              -- binance_rss, cryptopanic, coingecko, whale_alert
    category TEXT NOT NULL,            -- new_listing, launchpool, promotion, ...
    urgency TEXT NOT NULL,             -- high, medium, low
    scalping_opportunity BOOLEAN DEFAULT FALSE,
    title TEXT NOT NULL,
    action TEXT,
    symbol TEXT,
    expected_volatility TEXT,
    time_sensitive BOOLEAN DEFAULT FALSE,
    url TEXT,
    raw_content TEXT,
    content_hash TEXT UNIQUE,          -- deduplicazione cross-source
    classified_by_ai BOOLEAN DEFAULT FALSE,
    user_action TEXT CHECK (user_action IN ('watched', 'ignored', 'acted')),
    detected_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_opp_urgency_time ON opportunities(urgency, detected_at DESC);
CREATE INDEX idx_opp_symbol ON opportunities(symbol) WHERE symbol IS NOT NULL;
```

---

## 10. Fasi di Sviluppo

### Fase 1 — Foundation (Settimana 1-2)
**Obiettivo:** Modelli, indicatori, struttura base

- [ ] Creare struttura directory `scalping/`
- [ ] Implementare tutti i Pydantic models (inclusi `intelligence.py`, `opportunity.py`)
- [ ] Implementare `indicators/` (EMA, SMA, RSI, BB, ATR, ADX, VWAP)
- [ ] Implementare `CandleBuffer` con buffer circolare
- [ ] Scrivere unit test per ogni indicatore
- [ ] Creare schema Supabase completo v2.0 con migration

**Deliverable:** Indicatori tecnici testati + schema DB aggiornato

---

### Fase 2 — Signal Intelligence (Settimana 2-3)
**Obiettivo:** ★ NUOVO — Raccolta e aggregazione dati di mercato reali

- [ ] Implementare `FundingRateCollector` + test
- [ ] Implementare `CVDCalculator` dal WS trades + test
- [ ] Implementare `OpenInterestCollector` + test
- [ ] Implementare `LongShortRatioCollector` + test
- [ ] Implementare `FearGreedCollector` + test
- [ ] Implementare `OnChainCollector` (Glassnode free) + test
- [ ] Implementare `SignalScoreEngine` con pesi configurabili + test
- [ ] Implementare `IntelligenceScheduler` (APScheduler)
- [ ] Endpoint `GET /intelligence/snapshot`
- [ ] Salvare snapshot su `market_intel_snapshots`

**Deliverable:** Dashboard intelligenza di mercato funzionante con dati reali

---

### Fase 3 — Strategie + Signal Aggregator (Settimana 3-4)
**Obiettivo:** Strategie tecniche come filtri + aggregazione segnali

- [ ] Implementare `AbstractScalpingStrategy`
- [ ] Implementare `EMACrossStrategy` (ora filtro timing) + test
- [ ] Implementare `RSIBollingerStrategy` (ora filtro timing) + test
- [ ] Implementare `VWAPReversionStrategy` (ora filtro timing) + test
- [ ] Implementare `RegimeDetector` + test
- [ ] Implementare `StrategySelector` (regime → strategia)
- [ ] Implementare `SignalAggregator` (intelligence + tecnico) + test
- [ ] Test integrazione: segnali tecnici bloccati quando intelligence contraddice

**Deliverable:** Sistema segnali ibrido intelligence+tecnico funzionante

---

### Fase 4 — Backtest Engine (Settimana 4-5)
**Obiettivo:** Validare su dati storici prima di toccare soldi reali

- [ ] Implementare `HistoricalLoader` (scarica OHLCV da Binance API)
- [ ] Implementare loader dati storici funding rate e OI
- [ ] Implementare `BacktestEngine` con supporto SignalAggregator
- [ ] Implementare `PerformanceCalculator` (win rate, drawdown, Sharpe, profit factor)
- [ ] Confronto backtest: strategia sola vs strategia + intelligence
- [ ] Endpoint `POST /scalping/backtest/run`
- [ ] Frontend: pagina risultati backtest con grafici comparativi

**Deliverable:** Backtest su 90 giorni BTC/USDT con e senza intelligence layer

---

### Fase 5 — Execution Engine (Settimana 5-6)
**Obiettivo:** Layer 1 funzionante in modalità PAPER

- [ ] Implementare `OrderExecutor` (integrazione Binance REST + Testnet)
- [ ] Implementare `PositionManager`
- [ ] Implementare `RiskManager` con circuit breaker
- [ ] Implementare `ExecutionLoop` con `SignalAggregator` integrato
- [ ] Implementare `SessionManager` (start/stop/pause)
- [ ] Salvataggio trade con contesto intelligenza (`signal_score`, `funding_rate_at_entry`, ecc.)
- [ ] WebSocket events verso frontend
- [ ] Test completo modalità PAPER su Testnet

**Deliverable:** Sessione Paper trading end-to-end con segnali reali

---

### Fase 6 — Opportunity Monitor (Settimana 6-7)
**Obiettivo:** ★ NUOVO — Rilevamento automatico opportunità di mercato

- [ ] Implementare `BinanceRSSPoller` + test
- [ ] Implementare `CryptoPanicPoller` + test
- [ ] Implementare `CoinGeckoPoller` (trending) + test
- [ ] Implementare `WhaleAlertPoller` + test
- [ ] Implementare `Deduplicator` (hash content)
- [ ] Implementare `OpportunityClassifier` (Claude API)
- [ ] Implementare `OpportunityRouter` (smista per urgenza)
- [ ] `OpportunityScheduler` ogni 5 minuti
- [ ] Endpoint `GET /opportunities` + WebSocket stream
- [ ] `OpportunityFeedComponent` nel frontend

**Deliverable:** Feed opportunità live classificate dall'AI

---

### Fase 7 — Frontend Dashboard Completa (Settimana 7-8)
**Obiettivo:** UI completa con tutti i nuovi componenti

- [ ] Scaffolding modulo Angular `scalping/`
- [ ] `ScalpingWsService` con auto-reconnect
- [ ] `SessionControlsComponent`
- [ ] `LiveChartComponent` (lightweight-charts + overlay segnali)
- [ ] `StrategyPanelComponent`
- [ ] `PositionTickerComponent`
- [ ] `TradeLogComponent` (con colonna signal_score)
- [ ] `PerformancePanelComponent`
- [ ] `RiskControlsComponent`
- [ ] `MarketIntelPanelComponent` ★ NUOVO
- [ ] `SignalScorecardComponent` ★ NUOVO
- [ ] `OpportunityFeedComponent` ★ NUOVO
- [ ] `SupervisorLogComponent`
- [ ] Routing e lazy loading

**Deliverable:** Dashboard completa con intelligence panel e opportunity feed

---

### Fase 8 — AI Supervisor (Settimana 8-9)
**Obiettivo:** Layer 2 operativo con contesto arricchito

- [ ] Implementare `ContextBuilder` v2.0 (include intelligence snapshot)
- [ ] Implementare `ClaudeClient` con system prompt v2.0
- [ ] Implementare `DecisionParser` con validazione JSON + campo `primary_signal`
- [ ] Implementare `ParameterUpdater` (hot-swap parametri)
- [ ] Implementare `SupervisorScheduler` ogni 10 minuti
- [ ] Test: simulare scenari con funding rate alto, CVD negativo, ecc.
- [ ] Verifica: il supervisore cita correttamente i segnali reali nelle decisioni

**Deliverable:** Supervisore AI che ragiona su dati reali, non solo su performance

---

### Fase 9 — Go Live (Settimana 9-10)
**Obiettivo:** Prima sessione LIVE con piccolo capitale

- [ ] Review completa codice (focus sicurezza ordini)
- [ ] Stop loss sempre su Binance server-side — doppia verifica
- [ ] Test LIVE con trade minimo (€5) su coppia liquida (BTC/USDT)
- [ ] Monitoraggio manuale prima settimana
- [ ] Analisi correlazione: signal_score al trade entry vs outcome trade
- [ ] Documentazione operativa

**Deliverable:** Prima settimana live documentata con analisi signal intelligence

---

## 11. Testing Strategy

### Unit Test (pytest)
```
test_indicators.py           → ogni indicatore con valori noti
test_strategies.py           → segnali corretti su sequenze candele mock
test_regime_detector.py      → regime corretto su scenari diversi
test_risk_manager.py         → circuit breaker attivato correttamente
test_signal_score_engine.py  → score calcolato correttamente per ogni scenario
test_cvd_calculator.py       → CVD aggiornato correttamente su stream trade
test_funding_rate.py         → parsing risposta API + soglie
test_decision_parser.py      → parsing JSON Claude in tutti i casi edge
test_opportunity_classifier  → classificazione corretta su esempi reali
test_deduplicator.py         → hash collision detection
```

### Integration Test
```
test_signal_aggregator.py    → segnale tecnico bloccato se intelligence contraddice
test_execution_loop.py       → loop completo con Binance mock
test_intelligence_pipeline.py→ collector → score → snapshot
test_opportunity_pipeline.py → poller → classifier → router
test_supervisor.py           → ciclo completo con Claude mock arricchito
test_api_router.py           → tutti gli endpoint con client di test
```

### E2E Test (Playwright)
```
scalping-session.spec.ts     → avvio, pausa, stop sessione
live-chart.spec.ts           → aggiornamento real-time grafico
market-intel.spec.ts         → aggiornamento pannello intelligence
opportunity-feed.spec.ts     → notifica opportunità alta urgenza
supervisor-log.spec.ts       → visualizzazione decisioni AI con primary_signal
```

### Test specifico Signal Intelligence
```python
# Scenario: funding rate alto + CVD negativo → nessun BUY
def test_signal_aggregator_blocks_buy_when_overleveraged():
    score = SignalScore(total=-45, bias='bearish', tradeable=True)
    technical = Signal(type=SignalType.BUY, confidence=0.8)
    
    result = aggregator.should_execute(technical, score)
    
    assert result.execute == False
    assert "conflitto" in result.reason.lower()

# Scenario: tutti i segnali allineati → BUY eseguito
def test_signal_aggregator_allows_buy_when_aligned():
    score = SignalScore(total=+65, bias='bullish', tradeable=True)
    technical = Signal(type=SignalType.BUY, confidence=0.8)
    
    result = aggregator.should_execute(technical, score)
    
    assert result.execute == True
    assert result.confidence > 0.5
```

---

## 12. Rischi e Mitigazioni

| Rischio | Probabilità | Impatto | Mitigazione |
|---|---|---|---|
| Posizione aperta al crash dell'app | Media | Alto | Stop loss sempre su Binance server-side |
| Supervisore AI prende decisione sbagliata | Bassa | Medio | Confidence threshold min 0.7, log tutto |
| Signal score errato per API esterna down | Media | Medio | Fallback: usa ultimo score valido, log warning |
| CryptoPanic / Glassnode API rate limit | Media | Basso | Cache locale 5min, backoff esponenziale |
| Classificatore opportunità falso positivo | Media | Basso | Richiede conferma utente per azioni su nuovi simboli |
| Slippage alto su ordini market | Alta | Medio | Limit orders con timeout, fallback market |
| Binance Futures API non disponibile per spot | Bassa | Medio | Funding/OI disponibili solo per coppie futures; usare proxy BTCUSDT per proxy |
| CVD distorto da wash trading | Media | Medio | Filtra trade sotto soglia volume minimo |
| Connessione internet cade | Media | Alto | SL/TP server-side proteggono posizione |
| Claude API down durante supervisione | Bassa | Basso | Mantieni parametri correnti, riprova al prossimo ciclo |
| Drawdown giornaliero eccessivo | Media | Alto | RiskManager hard stop al 3% giornaliero |
| Nuova listing con liquidità insufficiente | Alta | Alto | Verifica volume minimo prima di entrare su simbolo nuovo |

---

## Note Finali

### Ordine di Priorità v2.0
1. **Signal Intelligence** — prima di qualunque strategia, servono dati reali
2. **Backtest comparativo** — con e senza intelligence layer, per misurare il delta
3. **Paper trading** almeno 2 settimane con intelligence attiva
4. **Supervisore AI** dopo che il Layer 1 è stabile e ha dati reali
5. **Live trading** solo con risultati paper positivi e intelligence validata

### Principio Guida
> Le strategie tecniche classiche sono overfittate sul passato e già scontate
> dal mercato. Il vero edge viene da dati che pochi sanno interpretare:
> funding rate, CVD, open interest, on-chain flow.
> Gli indicatori tecnici servono solo a trovare il timing di ingresso,
> non a decidere se entrare.

### API Keys necessarie
```
BINANCE_API_KEY          → trading + futures data
BINANCE_API_SECRET       → trading + futures data
BINANCE_TESTNET_KEY      → paper trading
BINANCE_TESTNET_SECRET   → paper trading
CRYPTOPANIC_TOKEN        → news sentiment (free tier)
GLASSNODE_API_KEY        → on-chain data (free tier)
WHALE_ALERT_API_KEY      → whale transactions (free tier)
ANTHROPIC_API_KEY        → supervisor + classifier
# CoinGecko e Alternative.me: no API key richiesta sul free tier
```
