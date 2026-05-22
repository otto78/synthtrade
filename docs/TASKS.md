# Active Tasks — SynthTrade

> **Fonte di verità:** questo file contiene il lavoro in corso e programmato per l'Epica Scalping.
> I task completati sono spostati in [ARCHIVE_TASKS.md](ARCHIVE_TASKS.md).
> Le idee generali e i piani a lungo termine sono in [BACKLOG.md](BACKLOG.md).

---

## 🚀 EPIC-SCALP-800 — Modulo Scalping v2.0 (Signal Intelligence) - REFACTORED

> **Principio architetturale (Aggiornato):** Integrare e riutilizzare il più possibile le librerie core esistenti (`indicators.py`, `ws.py`, `risk_manager.py`, `exchange.py`) per evitare duplicazioni. Il modulo `app/scalping/` conterrà ESCLUSIVAMENTE la logica ad alta frequenza (connessioni WS live verso Binance, Tick Processing, AI Supervisor).
> I test vanno in `tests/scalping/` ma devono integrarsi con la test suite generale.
> **Standard:** TDD (`🔴 Red → 🟢 Green → 🔵 Refactor`) per ogni task.

### Architettura Generale (v2.0)

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
│  │  SignalAggregator    ★│    │  ContextBuilder (arricchito)     │   │
│  │  RegimeDetector      ★│    │  ClaudeAPIClient (esistente)     │   │
│  │  StrategySelector   ★ │    │  ParameterUpdater ★             │   │
│  │  OrderExecutor (core) │    │  SupervisorScheduler            │   │
│  │  PositionManager   ★  │    └─────────────────────────────────┘   │
│  │  RiskManager (core)   │                                           │
│  └───────────┬───────────┘                                           │
│              │                                                        │
│  ┌───────────▼──────────────────────────────────────────────────┐   │
│  │               SIGNAL INTELLIGENCE ★ NUOVO                    │   │
│  │                                                              │   │
│  │  FundingRateCollector    OpenInterestCollector               │   │
│  │  CVDCalculator           LongShortRatioCollector             │   │
│  │  FearGreedCollector      OnChainCollector                    │   │
│  │  SentimentCollector      SignalScoreEngine                   │   │
│  └───────────┬──────────────────────────────────────────────────┘   │
│              │                                                        │
│  ┌───────────▼──────────────────────────────────────────────────┐   │
│  │               OPPORTUNITY MONITOR ★ NUOVO                    │   │
│  │                                                              │   │
│  │  BinanceRSSPoller        CryptoPanicPoller                   │   │
│  │  CoinGeckoPoller         WhaleAlertPoller                    │   │
│  │  AnnouncementClassifier  OpportunityRouter                   │   │
│  └───────────┬──────────────────────────────────────────────────┘   │
│              │                                                        │
│  ┌───────────▼──────────┐    ┌──────────────────────────────────┐   │
│  │  WebSocket Manager   │    │  REST API Router                 │   │
│  │  (WS stream BS)      │    │  /scalping/* /intelligence/*     │   │
│  └──────────────────────┘    └──────────────────────────────────┘   │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
          ┌─────────────────────┼──────────────────────┐
          │                     │                        │
┌─────────▼───────┐  ┌──────────▼──────────┐  ┌────────▼────────┐
│  BINANCE API    │  │  EXTERNAL APIs      │  │  SUPABASE       │
│                 │  │                     │  │                 │
│  WS streams     │  │  CryptoPanic        │  │  scalping_trades│
│  REST orders    │  │  CoinGecko          │  │  signal_snapshots│
│  Futures API    │  │  Alternative.me     │  │  opportunities  │
│  (funding,OI)   │  │  Whale Alert        │  │  supervisor_log │
│  Binance RSS    │  │  Glassnode (free)   │  │  market_intel   │
└─────────────────┘  └─────────────────────┘  └─────────────────┘
```

**Legenda:** `★` = nuovo componente scalping-specifico | `(core)` = riusa modulo esistente

### Principio chiave v2.0
> Le strategie tecniche (EMA, RSI, BB) diventano **filtri di timing**,
> non sorgenti di segnale primarie. Il segnale primario viene da
> **Funding Rate + CVD + Open Interest + Sentiment**.
> Una strategia tecnica si attiva solo se il contesto macro lo supporta.

```
PRIMA (v1.0):   EMA cross → BUY

ORA (v2.0):
  Funding Rate overleveraged long     ┐
  + CVD negativo (pressione sell)     ├─→ SHORT con alta confidenza
  + OI in crescita (esposizione alta) │
  + Fear & Greed > 75 (euforia)       ┘
  + EMA cross (filtro timing)
```

---

### Struttura Directory — Solo ciò che è NUOVO in `app/scalping/`

> ⚠️ **Non duplicare moduli core esistenti:**
> - Indicatori tecnici → `app/core/indicators.py` (aggiungere VWAP, ADX lì)
> - Risk Manager → `app/execution/risk_manager.py` (aggiungere metodi intraday lì)
> - Exchange adapter → `app/execution/exchange.py` (BinanceExchangeAdapter)
> - WebSocket broadcast → `app/api/ws.py` (ConnectionManager)
> - AI Client (Claude) → `app/ai/model_client.py`
> - AI Context Builder → `app/ai/context_builder.py`
> - AI Parser → `app/ai/eval_parser.py`

```
app/scalping/                         # SOLO logica scalping-specifica
├── __init__.py
├── models/                            # ★ NUOVO: modelli Pydantic scalping
│   ├── strategy.py                    # ScalpingStrategy, StrategyParams
│   ├── signal.py                      # Signal, SignalType, SignalStrength
│   ├── position.py                    # Position, PositionStatus
│   ├── trade.py                       # Trade, TradeResult
│   ├── market.py                      # Candle, OrderBook, MarketRegime
│   ├── supervisor.py                  # SupervisorDecision, SupervisorContext
│   ├── intelligence.py                # FundingRate, OpenInterest, CVD, ...
│   └── opportunity.py                 # Opportunity, OpportunityCategory
│
├── strategies/                        # ★ NUOVO: strategie scalping (filtri timing)
│   ├── base.py                        # AbstractScalpingStrategy
│   ├── ema_cross.py                   # EMA 9/21 (filtro timing)
│   ├── rsi_bollinger.py               # RSI + BB (filtro timing)
│   ├── vwap_reversion.py              # VWAP (filtro timing)
│   └── registry.py                    # StrategyRegistry
│
├── engine/                            # ★ NUOVO: orchestrazione scalping
│   ├── signal_aggregator.py           # Combina intelligence + segnale tecnico
│   ├── regime_detector.py             # Identifica regime (usa indicators core)
│   ├── strategy_selector.py           # Sceglie strategia dal regime
│   ├── signal_generator.py            # Genera segnali tecnici (secondari)
│   ├── position_manager.py            # Gestisce posizioni aperte
│   └── execution_loop.py              # Main loop asincrono (usa exchange + risk core)
│   # NOTA: order_executor → usa app/execution/exchange.py
│   # NOTA: risk_manager → usa app/execution/risk_manager.py
│
├── intelligence/                      # ★ NUOVO: Signal Intelligence
│   ├── collectors/
│   │   ├── funding_rate.py            # Binance Futures API funding rate
│   │   ├── open_interest.py           # Binance Futures API open interest
│   │   ├── long_short_ratio.py        # Binance long/short ratio
│   │   ├── cvd_calculator.py          # Cumulative Volume Delta (da WS trades)
│   │   ├── fear_greed.py              # alternative.me API
│   │   ├── onchain.py                 # Glassnode free tier
│   │   └── sentiment.py               # CryptoPanic API
│   ├── signal_score_engine.py         # Combina tutti i segnali in score 0-100
│   ├── market_context.py              # Snapshot aggregato del contesto
│   └── intelligence_scheduler.py      # Aggiorna dati ogni N secondi/minuti
│
├── opportunity/                       # ★ NUOVO: Opportunity Monitor
│   ├── pollers/
│   │   ├── binance_rss.py             # RSS Binance announcements
│   │   ├── cryptopanic.py             # CryptoPanic news feed
│   │   ├── coingecko.py               # Trending, nuove listing
│   │   └── whale_alert.py             # Whale Alert API
│   ├── classifier.py                  # Claude API: classifica opportunità
│   ├── opportunity_router.py          # Smista per categoria e urgenza
│   ├── deduplicator.py                # Evita duplicati tra fonti diverse
│   └── opportunity_scheduler.py       # Polling ogni 5 minuti
│
├── supervisor/                        # ★ NUOVO (minimo): solo parameter_updater
│   ├── parameter_updater.py           # Applica nuovi parametri all'ExecutionLoop
│   └── supervisor_scheduler.py        # Task periodico (usa model_client core)
│   # NOTA: context_builder → usa app/ai/context_builder.py esteso
│   # NOTA: claude_client → usa app/ai/model_client.py
│   # NOTA: decision_parser → usa app/ai/eval_parser.py
│
├── data/
│   ├── candle_buffer.py               # Buffer circolare candele
│   ├── market_snapshot.py             # Snapshot per Supervisor
│   └── historical_loader.py           # Caricamento dati storici per backtest
│
├── backtest/                          # ★ NUOVO: Backtest Engine
│   ├── backtest_engine.py
│   ├── performance_calculator.py
│   └── report_generator.py
│
├── session/                           # ★ NUOVO: Session management
│   ├── session_manager.py
│   ├── daily_summary.py
│   └── session_state.py
│
└── router.py                          # Endpoint /scalping/* /intelligence/* /opportunities/*
```

### Struttura Directory Frontend

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
    │   ├── intelligence.model.ts        # ★ Nuovo
    │   └── opportunity.model.ts         # ★ Nuovo
    │
    ├── services/
    │   ├── scalping-api.service.ts
    │   ├── scalping-ws.service.ts
    │   ├── session.service.ts
    │   ├── performance.service.ts
    │   ├── intelligence-api.service.ts  # ★ Nuovo
    │   └── opportunity-api.service.ts   # ★ Nuovo
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
        ├── market-intel-panel/          # ★ Nuovo
        ├── signal-scorecard/            # ★ Nuovo
        └── opportunity-feed/            # ★ Nuovo
```

---

### TASK-800 — Setup Base & Configurazioni
**Status:** Done ✅
**Priorità:** Critica

**Dettagli:**
Aggiungere configurazioni scalping senza frammentare il sistema.

**Piano:**
1. ✅ In `app/config.py`, creare `ScalpingSettings` con 13 parametri scalping + property `settings.scalping`
2. ✅ Aggiunte variabili d'ambiente a `.env` (sezione `# Scalping Module v2.0`)
3. ✅ Test TDD: 30/30 test PASS (default, override via env, type coercion, access via settings)

---

### TASK-801 — Estensione Moduli Core (Indicators, Risk, WS, Exchange)
**Status:** To Do
**Priorità:** Critica
**Dipende da:** TASK-800

**Dettagli:**
Estendere i moduli pre-esistenti invece di creare cloni scalping-only.

**Piano:**
1. **Indicatori:** Aggiungere in `app/core/indicators.py` il calcolo `vwap`, `adx` e filtri regime (trend, vola), usando la libreria Pandas esistente.
2. **WebSocket:** Estendere `ConnectionManager` in `app/api/ws.py` aggiungendo metodi `broadcast_scalping_tick`, `broadcast_intel_score`.
3. **Risk Manager:** In `app/execution/risk_manager.py`, aggiungere controlli intraday: `check_max_daily_loss` (soglia -3%) e `check_max_consecutive_losses` (soglia 5).
4. **Exchange:** In `app/execution/exchange.py` (`BinanceExchangeAdapter`), estendere il supporto per piazzare ordini combinati OCO/OTO (se applicabile all'API), o implementare un synthetic OCO usando websockets.

---

### TASK-802 — Database Migrations (Tabelle Separate) [📎 Dettaglio]
**Status:** To Do
**Priorità:** Alta

**📎 Dettaglio Piano — Schema DB completo:**
```sql
-- Sessioni di trading
CREATE TABLE scalping_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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

-- Trade eseguiti (con contesto intelligenza)
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
    signal_score NUMERIC(6,2),
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
    primary_signal TEXT,
    previous_params JSONB,
    new_params JSONB,
    previous_strategy TEXT,
    new_strategy TEXT,
    decided_at TIMESTAMPTZ DEFAULT NOW()
);

-- Snapshot intelligenza di mercato (storico)
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
CREATE INDEX idx_intel_symbol_time ON market_intel_snapshots(symbol, recorded_at DESC);

-- Opportunità rilevate
CREATE TABLE opportunities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source TEXT NOT NULL,
    category TEXT NOT NULL,
    urgency TEXT NOT NULL,
    scalping_opportunity BOOLEAN DEFAULT FALSE,
    title TEXT NOT NULL,
    action TEXT,
    symbol TEXT,
    expected_volatility TEXT,
    time_sensitive BOOLEAN DEFAULT FALSE,
    url TEXT,
    raw_content TEXT,
    content_hash TEXT UNIQUE,
    classified_by_ai BOOLEAN DEFAULT FALSE,
    user_action TEXT CHECK (user_action IN ('watched', 'ignored', 'acted')),
    detected_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_opp_urgency_time ON opportunities(urgency, detected_at DESC);
CREATE INDEX idx_opp_symbol ON opportunities(symbol) WHERE symbol IS NOT NULL;
```

**⚠️ IMPORTANTE:** Non dimenticare di eseguire fisicamente le migrazioni Supabase (es. `supabase db push` o via UI SQL) per non far fallire le API in produzione!

**Dettagli:**
Creare le tabelle dedicate per non inquinare il logging swing.

**Piano:**
1. Nuova tabella `scalping_sessions` (id, status, start_time, end_time, daily_pnl).
2. Nuova tabella `scalping_trades` (id, session_id, pair, side, entry_price, exit_price, pnl, score_at_entry).
3. Tabelle metriche IA: `intel_snapshots`, `supervisor_decisions`.
4. Aggiornare `schemas.py` o creare `app/scalping/schemas.py` basandosi su questi campi.
5. Tabella `opportunities` per l'Opportunity Monitor (TASK-810).

---

### TASK-803 — Binance Live WS Client (Feed Dati) [📎 Dettaglio]
**Status:** To Do
**Priorità:** Alta

**📎 Dettaglio Piano:**
- Flussi WS Binance: `wss://stream.binance.com/ws/<symbol>@kline_1m` (candele), `<symbol>@trade` (trades per CVD)
- Emettere eventi asincroni consumati da `TickProcessor`
- Test su Testnet prima di Live

**Dettagli:**
L'engine swing usa REST. Lo scalping richiede uno stream in tempo reale.

**Piano:**
1. Creare `app/scalping/engine/ws_client.py`.
2. Implementare un client basato su `websockets` per ascoltare il kline stream (1s o 1m) e il trade stream di Binance Testnet/Live.
3. Emettere eventi asincroni che il `TickProcessor` potrà consumare.

---

### TASK-804 — Intelligence Layer & Signal Scoring [📎 Dettaglio]
**Status:** To Do
**Priorità:** Media

**📎 Dettaglio Piano — Fonti dati:**
| Fonte | Dati | Endpoint | Frequenza | Costo |
|---|---|---|---|---|
| Binance Futures | Funding Rate | `/fapi/v1/fundingRate` | Ogni 8h | Gratuito |
| Binance Futures | Open Interest | `/fapi/v1/openInterest` | Real-time | Gratuito |
| Binance Futures | Long/Short Ratio | `/futures/data/globalLongShortAccountRatio` | 5min | Gratuito |
| WS Binance | CVD (da trade stream) | `<symbol>@trade` | Real-time | Gratuito |
| Alternative.me | Fear & Greed | `https://api.alternative.me/fng/` | 1/giorno | Gratuito |
| CryptoPanic | News + Sentiment | `https://cryptopanic.com/api/v1/posts/` | 5min | Free tier |
| Glassnode | On-chain | `https://api.glassnode.com/v1/metrics/` | 1h | Free tier |

**📎 Dettaglio Piano — SignalScoreEngine (pesi):**
```python
WEIGHTS = {
    'funding_rate':     0.25,  # segnale contrarian più affidabile
    'cvd':              0.25,  # pressione reale di mercato
    'open_interest':    0.15,  # contesto esposizione
    'long_short_ratio': 0.15,  # sentiment contrarian
    'fear_greed':       0.10,  # contesto macro
    'onchain':          0.10,  # flussi exchange
}
```

**📎 Dettaglio Piano — FundingRateCollector:**
```
Funding Rate positivo  → i long pagano gli short → overleveraged long → bias SHORT
Funding Rate negativo  → gli short pagano i long → overleveraged short → bias LONG
Soglie: > +0.10% = fortemente overleveraged long (contrarian short)
        > +0.05% = moderatamente rialzista
        0%      = equilibrio
        < -0.05% = moderatamente ribassista
        < -0.10% = fortemente overleveraged short (contrarian long)
```

**📎 Dettaglio Piano — CVDCalculator:**
```python
class CVDCalculator:
    """Cumulative Volume Delta — pressione netta buy vs sell in tempo reale."""
    def on_trade(self, trade: BinanceTrade):
        delta = trade.quantity if not trade.is_buyer_maker else -trade.quantity
        self._cvd += delta
    # CVD crescente = più pressione buy → momentum rialzista
    # CVD calante = più pressione sell → momentum ribassista
    # CVD divergente dal prezzo = forte segnale inversione imminente
```

**📎 Dettaglio Piano — SignalAggregator (ibrido):**
```python
class SignalAggregator:
    """
    Un ordine viene eseguito SOLO se entrambi sono allineati:
    - Score intelligenza > soglia (default: 30)
    - Strategia tecnica conferma (filtro timing)
    """
    def should_execute(self, technical_signal, market_score):
        if not market_score.tradeable:
            return ExecutionDecision(execute=False)
        if (market_score.bias == 'bullish') != (technical_signal.type == 'BUY'):
            return ExecutionDecision(execute=False, reason="conflitto intelligence-tecnico")
        return ExecutionDecision(execute=True, confidence=market_score.total / 100)
```

**Dettagli:**
Collettori di mercato specifici ad alta frequenza e motore di scoring.

**Piano:**
1. Creare `FundingRateCollector`, `OpenInterestCollector`, `LongShortRatioCollector`, `FearGreedCollector`, `CVDCalculator`, `OnChainCollector`, `SentimentCollector`.
2. Creare `SignalScoreEngine` in `app/scalping/intelligence/`: aggrega tutti i collettori in uno score normalizzato (-100 a +100).
3. Creare `SignalAggregator` in `app/scalping/engine/` che combina score intelligence + segnale tecnico.

---

### TASK-805 — Scalping Engine & TickProcessor [📎 Dettaglio]
**Status:** To Do
**Priorità:** Critica
**Dipende da:** TASK-801, TASK-803, TASK-804

**📎 Dettaglio Piano — ExecutionLoop:**
```python
class ExecutionLoop:
    """Main loop scalping. Gira ogni 500ms-2s. Usa moduli core per order_executor e risk_manager."""
    
    async def _process_candle(self, candle):
        self.candle_buffer.add(candle)
        if not self.candle_buffer.is_ready():
            return
        
        candles = self.candle_buffer.get()
        indicators = self.indicators_core.calculate(candles)  # app/core/indicators.py
        
        # 1. Regime detection
        regime = self.regime_detector.detect(candles, indicators)
        
        # 2. Strategy selection
        strategy = self.strategy_selector.select(regime)
        
        # 3. Signal generation (tecnico = filtro timing)
        signal = strategy.evaluate(candles, indicators)
        
        # 4. Risk check (usa app/execution/risk_manager.py)
        risk_result = self.risk_manager_core.check_pre_trade(self.capital)
        if not risk_result.allowed:
            return
        
        # 5. Esegui se segnale valido + intelligence conferma
        if signal.type == 'BUY' and not self.position_manager.has_open():
            order = await self.exchange_core.buy(signal)  # app/execution/exchange.py
        
        elif signal.type in ('SELL', 'CLOSE'):
            if self.position_manager.has_open():
                order = await self.exchange_core.close()
                trade = await self.position_manager.close(order)
                self.risk_manager_core.on_trade_closed(trade)
        
        # 6. WS event verso frontend (app/api/ws.py)
        await self._emit_market_update(candle, signal, indicators)
```

**Dettagli:**
Il cuore del modulo scalping. Processa ogni tick live.

**Piano:**
1. Creare `TickProcessor` / `ExecutionLoop` in `app/scalping/engine/`: riceve dati da `ws_client.py`.
2. Ad ogni tick o chiusura candela 1m:
   - Chiama `SignalScoreEngine` (score intelligence).
   - Chiama `RegimeDetector` + `StrategySelector` + strategia (segnale tecnico).
   - Chiama `SignalAggregator` per combinare i due.
   - Se ok, chiama `RiskManager` core (`app/execution/risk_manager.py`).
   - Se ok, invia ordine via `BinanceExchangeAdapter` core (`app/execution/exchange.py`).
3. Broadcast immediato al frontend via `ConnectionManager` core (`app/api/ws.py`).

---

### TASK-806 — AI Supervisor (Integrazione moduli core esistenti) [📎 Dettaglio]
**Status:** To Do
**Priorità:** Bassa

**📎 Dettaglio Piano — Gerarchia segnali per ContextBuilder esteso:**
```
1. Funding Rate — se > 0.1% mercato overleveraged long → short bias
2. CVD — pressione reale buy/sell
3. Open Interest — se cresce + prezzo laterale → breakout imminente
4. Long/Short Ratio — contrarian: se > 70% long, mercato esposto
5. Fear & Greed — estremi (< 20 o > 80) = potenziale inversione
6. On-chain Exchange Flow — BTC entra negli exchange = sell pressure
7. Sentiment news — solo come conferma
8. Indicatori tecnici (EMA, RSI, BB) — solo come filtri di timing
```

**📎 Dettaglio Piano — Formato risposta Claude (da usare in app/ai/eval_parser.py):**
```json
{
  "action": "update_params|change_strategy|pause_trading|resume_trading|no_action",
  "reason": "spiegazione con riferimento ai dati reali",
  "confidence": 0.0-1.0,
  "market_bias": "bullish|bearish|neutral",
  "primary_signal": "quale segnale ha guidato la decisione",
  "new_params": { ... } | null,
  "new_strategy": "ema_cross|rsi_bollinger|vwap_reversion" | null
}
```

**📎 Dettaglio Piano — Tipi di Decisione:**
| Azione | Trigger tipico | Effetto |
|--------|---------------|---------|
| `update_params` | ATR cambiato, win rate in calo | Aggiorna SL/TP/size |
| `change_strategy` | Regime cambiato | Swap al prossimo candle |
| `pause_trading` | Mercato caotico, troppe perdite | Ferma loop |
| `resume_trading` | Dopo pausa, condizioni migliorate | Riavvia loop |
| `no_action` | Tutto ok | Log di conferma |

**📎 Dettaglio Piano — Flusso Supervisor (ogni 10 minuti):**
```
1. app/ai/context_builder.py esteso: include intelligence snapshot (funding, OI, CVD, Fear&Greed)
2. app/ai/model_client.py: chiamata Claude con system prompt arricchito
3. app/ai/eval_parser.py: parsing JSON risposta (con campi market_bias, primary_signal)
4. parameter_updater.py (NUOVO in app/scalping/supervisor/): applica aggiornamenti all'ExecutionLoop
5. Evento WebSocket → frontend mostra log decisione
6. SupervisorDecision salvata su Supabase
```

**Dettagli:**
Integrare LLM per leggere news ed emettere bias correttivi a costo quasi zero.

**Piano:**
1. **Estendere** `app/ai/context_builder.py` per includere intelligence snapshot (funding rate, CVD, OI, Fear&Greed).
2. **Arricchire** `app/ai/eval_parser.py` per parsare i campi aggiuntivi (`market_bias`, `primary_signal`).
3. **Arricchire** il system prompt in `app/ai/model_client.py` con la gerarchia dei segnali v2.0.
4. **Creare** `app/scalping/supervisor/parameter_updater.py`: applica parametri aggiornati all'ExecutionLoop.
5. **Creare** `app/scalping/supervisor/supervisor_scheduler.py`: task periodico che orchestra il ciclo.

---

### TASK-807 — Scheduler Centralizzato
**Status:** To Do
**Priorità:** Alta
**Dipende da:** TASK-805

**Dettagli:**
Gestione dei background job per scalping, unificata con il resto del bot.

**Piano:**
1. Creare `app/scheduler/scalping_jobs.py`.
2. Aggiungere i cronjob per `CryptoNewsPoller`, aggiornamento Funding Rate, e check salute sessione.
3. Importare e registrare questi job nell'istanza esistente di `AsyncIOScheduler` in `app/scheduler/jobs.py` (`setup_scheduler`).

---

### TASK-808 — Frontend (Dashboard Scalping) [📎 Dettaglio]
**Status:** To Do
**Priorità:** Media

**📎 Dettaglio Piano — WebSocket Service:**
```typescript
export interface ScalpingEvent {
  type: 'candle' | 'signal' | 'order' | 'position' | 'supervisor' | 'risk_block';
  payload: any;
  timestamp: string;
}

candle$ = new Subject<CandleEvent>();
signal$ = new Subject<SignalEvent>();
position$ = new Subject<PositionEvent>();
supervisorDecision$ = new Subject<SupervisorDecision>();
riskBlock$ = new Subject<RiskBlockEvent>();

connect(): void {
  this.ws$ = webSocket<ScalpingEvent>('ws://localhost:8000/ws/scalping');
  this.ws$.pipe(retryWhen(errors => errors.pipe(delay(3000))))
    .subscribe(event => this._dispatch(event));
}
```

**📎 Dettaglio Piano — PerformanceMetrics:**
```typescript
interface PerformanceMetrics {
  totalPnl: number;
  totalPnlPct: number;
  winRate: number;
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
  avgWin: number;
  avgLoss: number;
  profitFactor: number;
  maxDrawdown: number;
  consecutiveLosses: number;
}
```

**📎 Dettaglio Piano — Componenti UI:**
| Componente | Descrizione |
|-----------|-------------|
| **ScalpingDashboard** | Layout principale con griglia componenti |
| **SessionControls** | Start/Stop/Pausa, selezione modalità (Paper/Live) |
| **LiveChart** | Grafico candlestick real-time (lightweight-charts) |
| **StrategyPanel** | Strategia attiva e parametri correnti |
| **PositionTicker** | Posizione aperta con PnL in tempo reale |
| **TradeLog** | Storico trade sessione con colonna signal_score |
| **PerformancePanel** | Win rate, profit factor, drawdown |
| **SupervisorLog** | Log decisioni AI |
| **RiskControls** | Configurazione risk manager |
| **MarketIntelPanel** | Funding rate, OI, CVD, Fear&Greed |
| **SignalScorecard** | Score aggregato 0-100 con breakdown |
| **OpportunityFeed** | Feed real-time opportunità classificate dall'AI |

**Dettagli:**
UI in Angular per gestire lo scalping.

**Piano:**
1. Modulo lazy loaded per `/scalping`.
2. **Intel Panel:** Mostra i CVD e Funding Rate in tempo reale.
3. **Session Controls:** Bottone "Start/Stop Scalping Session".
4. Integrazione con i feed websocket (`/api/ws`) per aggiornamenti chart real-time.
5. **Signal Scorecard:** Score aggregato con breakdown per categoria.
6. **Opportunity Feed:** Notifiche in tempo reale.

---

### TASK-809 — Regressione E2E [📎 Dettaglio]
**Status:** To Do
**Priorità:** Media

**📎 Dettaglio Piano — Test Suite Scalping:**
```
Unit Test (pytest):
  test_strategies.py           → segnali su sequenze candele mock
  test_signal_score_engine.py  → score per ogni scenario
  test_cvd_calculator.py       → CVD su stream trade mock
  test_funding_rate.py         → parsing risposta API + soglie

Integration Test:
  test_signal_aggregator.py    → segnale bloccato se intelligence contraddice
  test_execution_loop.py       → loop completo con moduli core mockati
  test_intelligence_pipeline.py→ collector → score → snapshot

E2E Test (Playwright):
  scalping-session.spec.ts     → avvio, pausa, stop sessione
  market-intel.spec.ts         → aggiornamento pannello intelligence
  opportunity-feed.spec.ts     → notifica opportunità alta urgenza
```

**📎 Dettaglio Piano — Scenario test aggregatore:**
```python
def test_signal_aggregator_blocks_buy_when_overleveraged():
    score = SignalScore(total=-45, bias='bearish', tradeable=True)
    technical = Signal(type='BUY', confidence=0.8)
    result = aggregator.should_execute(technical, score)
    assert result.execute == False
    assert "conflitto" in result.reason.lower()

def test_signal_aggregator_allows_buy_when_aligned():
    score = SignalScore(total=+65, bias='bullish', tradeable=True)
    technical = Signal(type='BUY', confidence=0.8)
    result = aggregator.should_execute(technical, score)
    assert result.execute == True
    assert result.confidence > 0.5
```

**Dettagli:**
Testare l'intero workflow.

**Piano:**
1. Aggiornare i test Playwright per includere l'avvio e l'arresto della sessione scalping.
2. Assicurarsi che le suite esistenti (0 regressioni) continuino a passare dopo il deploy.

---

### TASK-810 — Opportunity Monitor [📎 Dettaglio] ★ NUOVO
**Status:** To Do
**Priorità:** Media
**Dipende da:** TASK-806

**📎 Dettaglio Piano — Architettura:**
```
Ogni 5 minuti:
1. Tutti i Poller recuperano nuovi contenuti
2. Deduplicator filtra già visti (hash del contenuto)
3. Classifier (Claude API via app/ai/model_client.py) classifica ogni nuovo item
4. OpportunityRouter smista per categoria e urgenza
5. Se urgenza HIGH + scalping_opportunity → notifica frontend
6. Se nuovo simbolo → aggiunge a watchlist engine
7. Salva tutto su Supabase (tabella opportunities)
```

**📎 Dettaglio Piano — Pollers:**
```python
# BinanceRSSPoller — Feed RSS ufficiale Binance
RSS_URL = "https://www.binance.com/en/support/announcement/rss"

# CryptoPanicPoller — News aggregate con score sentiment
BASE_URL = "https://cryptopanic.com/api/v1/posts/"
Params: filter="important", currencies="BTC,ETH"

# CoinGeckoPoller — Trending coins
TRENDING_URL = "https://api.coingecko.com/api/v3/search/trending"

# WhaleAlertPoller — Grandi transazioni
BASE_URL = "https://api.whale-alert.io/v1/transactions"
```

**📎 Dettaglio Piano — API Endpoints:**
```
GET  /opportunities                  # lista con filtri (urgency, category)
GET  /opportunities/live             # WebSocket stream nuove opportunità
POST /opportunities/{id}/watchlist   # aggiungi simbolo a watchlist engine
POST /opportunities/{id}/ignore      # marca come ignorata
```

**Dettagli:**
Rilevamento automatico di opportunità di mercato (nuove listing, launchpool, news, whale movements) tramite polling multi-fonte e classificazione AI.

**Piano:**
1. Implementare `BinanceRSSPoller`, `CryptoPanicPoller`, `CoinGeckoPoller`, `WhaleAlertPoller`.
2. Implementare `Deduplicator` (hash del contenuto per evitare duplicati cross-source).
3. Implementare `OpportunityClassifier` via `app/ai/model_client.py`.
4. Implementare `OpportunityRouter` per smistare per categoria e urgenza.
5. Salvare su tabella `opportunities` in Supabase.
6. Endpoint GET `/opportunities` e WebSocket stream `/opportunities/live`.

---

### TASK-811 — Backtest Engine [📎 Dettaglio] ★ NUOVO
**Status:** To Do
**Priorità:** Alta
**Dipende da:** TASK-804

**Dettagli:** Motore di backtest per validare le strategie scalping su dati storici prima del go-live.

**Piano:**
1. Implementare `HistoricalLoader` (scarica OHLCV da Binance API + funding rate + OI storici).
2. Implementare `BacktestEngine` con supporto `SignalAggregator` (confronto con/senza intelligence).
3. Implementare `PerformanceCalculator` (win rate, drawdown, Sharpe ratio, profit factor).
4. Endpoint `POST /scalping/backtest/run` e `GET /scalping/backtest/{id}/result`.

---

### TASK-812 — Go Live & Deploy [📎 Dettaglio] ★ NUOVO
**Status:** To Do
**Priorità:** Media
**Dipende da:** TASK-805, TASK-811

**Dettagli:** Preparazione e prima esecuzione in modalità LIVE con capitale minimo.

**Piano:**
1. Review completa sicurezza ordini (doppia verifica SL server-side).
2. Test LIVE con trade minimo (€5) su BTC/USDT.
3. Monitoraggio manuale prima settimana.
4. Analisi correlazione: signal_score al trade entry vs outcome trade.

---

## 📋 Riepilogo Ordine di Esecuzione
1. **TASK-800** (Setup config)
2. **TASK-801** (Estensione moduli core — indicators, risk, ws, exchange) 
3. **TASK-802** (DB Migrations)
4. **TASK-803** (Binance WsClient)
5. **TASK-804** (Intelligence Layer — componenti NUOVI: collectors, score engine)
6. **TASK-811** (Backtest Engine — prima di eseguire, per validare)
7. **TASK-805** (TickProcessor + ExecutionLoop)
8. **TASK-807** (Scheduler Centralizzato)
9. **TASK-808** (Frontend)
10. **TASK-806** (AI Supervisor — estensione moduli core esistenti)
11. **TASK-810** (Opportunity Monitor)
12. **TASK-809** (Regressione E2E)
13. **TASK-812** (Go Live)

---

## 🧪 Testing Strategy (Cross-Task) [📎 Dettaglio]

### Unit Test
```
tests/scalping/
  test_strategies.py           → segnali su sequenze candele mock
  test_signal_score_engine.py  → score per ogni scenario
  test_cvd_calculator.py       → CVD su stream trade mock
  test_funding_rate.py         → parsing risposta API + soglie
  test_opportunity_classifier  → classificazione su esempi reali
  test_deduplicator.py         → hash collision detection
```

### Integration Test
```
tests/integration/
  test_signal_aggregator.py    → segnale bloccato se intelligence contraddice
  test_execution_loop.py       → loop completo con moduli core mockati
  test_intelligence_pipeline.py→ collector → score → snapshot
  test_opportunity_pipeline.py → poller → classifier → router
  test_supervisor.py           → ciclo completo con Claude mock
```

### E2E Test (Playwright)
```
tests/e2e/
  scalping-session.spec.ts     → avvio, pausa, stop sessione
  market-intel.spec.ts         → aggiornamento pannello intelligence
  opportunity-feed.spec.ts     → notifica opportunità alta urgenza
  supervisor-log.spec.ts       → decisioni AI con primary_signal