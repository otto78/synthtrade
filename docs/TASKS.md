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

### TASK-806 — AI Supervisor (Integrazione moduli core esistenti)
**Status:** Done ✅
**Completato:** 2026-05-25
**Archiviato in:** `docs/ARCHIVE_TASKS.md`

---

### TASK-807 — Scheduler Centralizzato
**Status:** Done ✅
**Completato:** 2026-05-25
**Priorità:** Alta
**Dipende da:** TASK-805 ✅

**Risultati:**
- 4 nuovi job scalping registrati in `app/scheduler/scalping_jobs.py`:
  - `intelligence_snapshot_job` (ogni 60s): snapshot SignalScoreEngine → Supabase
  - `funding_rate_update_job` (ogni 60min): funding rate BTCUSDT/ETHUSDT
  - `supervisor_check_job` (ogni 10min): `SupervisorScheduler.run_once()`
  - `session_health_job` (ogni 30s): heartbeat sessione
- 4 flag di abilitazione in `ScalpingSettings` (default: `True`)
- Registrazione condizionale in `setup_scheduler()` basata su `SCALPING_DEFAULT_MODE`
- Nuovo metodo pubblico `run_once()` su `SupervisorScheduler`
- 15 test: 14 verde + 1 con `importlib.reload`

---

### TASK-809 — Frontend (Dashboard Scalping) [📎 Dettaglio]
See `plans/task809_frontend_scalping.md` for implementation plan.
**Status:** Done ✅
**Completato:** 2026-05-25
**Priorità:** Media

**Risultati:**
- Dashboard con 4 componenti integrati: MarketIntelPanel, SignalScorecard, OpportunityFeed, ScalpingDashboard
- Services REST API configurati con URL `/api/scalping/...` per intelligence, opportunities, backtest
- Router backend incluso in main.py con prefix `/api`
- Angular build passing

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

# NewsPollers — Fonti news crypto gratuite (senza API key):
#   CoinGecko:   https://api.coingecko.com/api/v3/news
#   Messari:     https://data.messari.io/api/v1/news
#   CryptoCompare: https://min-api.cryptocompare.com/data/v2/news/?lang=EN
#   NewsAPI:     https://newsapi.org/v2/everything?q=crypto OR bitcoin OR ethereum
#   RSS Feed:    https://cointelegraph.com/rss, https://coindesk.com/arc/outboundfeeds/rss/

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
1. Implementare `BinanceRSSPoller`, `NewsPoller` (aggregatore multi-fonte: CoinGecko News, Messari, CryptoCompare, NewsAPI, RSS feed), `CoinGeckoPoller`, `WhaleAlertPoller`.
2. Implementare `Deduplicator` (hash del contenuto per evitare duplicati cross-source).
3. Implementare `OpportunityClassifier` via `app/ai/model_client.py`.
4. Implementare `OpportunityRouter` per smistare per categoria e urgenza.
5. Salvare su tabella `opportunities` in Supabase.
6. Endpoint GET `/opportunities` e WebSocket stream `/opportunities/live`.

---

### TASK-811 — Regressione E2E [📎 Dettaglio]
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

### TASK-812 — Go Live & Deploy [📎 Dettaglio] ★ NUOVO
**Status:** To Do
**Priorità:** Media
**Dipende da:** TASK-805, TASK-808

**Dettagli:** Preparazione e prima esecuzione in modalità LIVE con capitale minimo.

**Piano:**
1. Review completa sicurezza ordini (doppia verifica SL server-side).
2. Test LIVE con trade minimo (€5) su BTC/USDT.
3. Monitoraggio manuale prima settimana.
4. Analisi correlazione: signal_score al trade entry vs outcome trade.

---

## 📋 Riepilogo Ordine di Esecuzione
1. ~~**TASK-800** (Setup config)~~ ✅
2. ~~**TASK-801** (Estensione moduli core — indicators, risk, ws, exchange)~~ ✅
3. ~~**TASK-802** (DB Migrations)~~ ✅
4. ~~**TASK-803** (Binance WsClient)~~ ✅
5. ~~**TASK-804** (Intelligence Layer — componenti NUOVI: collectors, score engine)~~ ✅
6. ~~**TASK-805** (TickProcessor + ExecutionLoop)~~ ✅
7. ~~**TASK-806** (AI Supervisor — estensione moduli core esistenti)~~ ✅
8. ~~**TASK-807** (Scheduler Centralizzato)~~ ✅
9. ~~**TASK-808** (Backtest Engine)~~ ✅
10. **TASK-809** (Frontend Dashboard Scalping)
11. **TASK-810** (Opportunity Monitor)
12. **TASK-811** (Regressione E2E)
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