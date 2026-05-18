# Active Tasks — SynthTrade

> **Fonte di verità:** questo file contiene il lavoro in corso e programmato.
> I task completati sono spostati in [ARCHIVE_TASKS.md](file:///c:/Users/andrea.mazzarotto/myJobs/SynthTrade/docs/ARCHIVE_TASKS.md).
> Le idee generali e i piani a lungo termine sono in [BACKLOG.md](file:///c:/Users/andrea.mazzarotto/myJobs/SynthTrade/docs/BACKLOG.md).

---

## 🛠️ Fase 6A — Refactoring & Logica Applicativa

> **Obiettivo:** Risolvere il debito tecnico architetturale, configurazioni dinamiche e comunicazione in tempo reale.

### TASK-187 — 🟢 Fix `dashboard.page.ts` e `dashboard.service.ts`
**Status:** To Do  
**Priorità:** Alta  
**Dettagli:** Gestire correttamente la sottoscrizione ai dati del backend e i casi di errore/timeout.

### TASK-209 — 🔵 Refactor: `RiskConfig` dataclass iniettabile nei test
**Status:** In Progress  
**Priorità:** Media

### TASK-214 — 🔵 Refactor: pluggabile via `config.py` con `importlib`
**Status:** In Progress  
**Priorità:** Media

### TASK-217 — 🔵 Refactor: `SignalResolver` iniettato nel costruttore
**Status:** In Progress  
**Priorità:** Media

### TASK-222 — 🔵 Refactor: intervalli configurabili da `Settings`
**Status:** In Progress  
**Priorità:** Media

### TASK-232 — 🔵 Refactor: `MarketRegimeDetector` con soglie configurabili
**Status:** In Progress  
**Priorità:** Media

### TASK-235 — 🔵 Refactor: template `.jinja2` separato da logica
**Status:** In Progress  
**Priorità:** Media

### TASK-238 — 🔵 Refactor: `@async_retry` decorator in `ai/retry.py`
**Status:** In Progress  
**Priorità:** Media

### TASK-245 — 🔵 Refactor: `MAX_CONCURRENT_EVALS` da `Settings`
**Status:** In Progress  
**Priorità:** Media

### TASK-250 — 🟢 Broadcast WS `eval_complete` con strategy_id, verdict, score
**Status:** In Progress  
**Priorità:** Media

---

## 🧪 Fase 6B — Test Suite & Stabilità Frontend

> **Obiettivo:** Garantire la massima stabilità della UI ed eliminare regressioni tramite test E2E e unitari.

### TASK-176 — 🔴 E2E `auth.spec.ts` (login errato → errore; login corretto → /dashboard)
**Status:** To Do  
**Priorità:** Alta

### TASK-177 — 🔴 E2E `strategies.spec.ts` (attivazione e disattivazione end-to-end)
**Status:** To Do  
**Priorità:** Alta

### TASK-178 — 🔴 E2E `logs.spec.ts` (filtro level aggiorna lista)
**Status:** To Do  
**Priorità:** Alta

### TASK-186 — Unit Test `dashboard.page.spec.ts`
**Status:** To Do  
**Priorità:** Media

### TASK-421 — Unit Test `active-trade.page.spec.ts`
**Status:** To Do  
**Priorità:** Media

---

## 📈 EPIC-400 — Pipeline di Esecuzione (Finalizzazione)

> **Obiettivo:** Completare l'integrazione del motore di trading reale e la visualizzazione avanzata dei trade.

### TASK-418 — Refactor `active-trade.page.ts`: supporto multi-strategia
**Status:** To Do  
**Priorità:** Critica  
**Dettagli:**
- Rimuovere dipendenza da "una singola strategia attiva".
- GET /api/trades/active per snapshot iniziale.
- WS trade_opened/closed per aggiornamento real-time.
- Trade raggruppati per strategia con header collassabili.

### TASK-419 — Componente `ActiveTradeRowComponent`
**Status:** To Do  
**Priorità:** Alta  
**Dettagli:**
- P&L unrealizzato aggiornato da WS price.
- Badge BUY/SELL con animazioni flash al cambio prezzo.
- Calcolo valore posizione in EUR in tempo reale.

### TASK-427 — Frontend: selezione multi-crypto nel form generazione
**Status:** To Do  
**Priorità:** Media  
**Dettagli:**
- Form con aggiunta di più crypto e slider percentuale.
- Validazione: somma delle percentuali = 100%.

### TASK-429 — Gestione errori e retry per exchange failures nel signal loop
**Status:** To Do  
**Priorità:** Alta  
**Dettagli:** Gestione di `asyncio.gather` con `return_exceptions=True` e broadcast di errori via WebSocket.

### TASK-430 — Dashboard: KPI globali strategie attive e trade aperti
**Status:** To Do  
**Priorità:** Media  
**Dettagli:** Aggiunta di `active_strategies_count` e `total_active_pnl_pct` alle statistiche dashboard.


---

## 🚀 Roadmap Futura

### Fase 7 — Produzione & Deployment

> **Obiettivo:** Migrazione all'ambiente di produzione solo dopo che il sistema è perfettamente funzionante.
> Architettura Scelta: **All-in-One Docker VPS** (Supabase Cloud per i dati + VPS Linux per l'intero stack applicativo).

### 7.1 Infrastruttura & Cloud Setup
#### TASK-252 — Setup Progetto Supabase Produzione
- Configurazione progetto su Supabase Cloud (Region: West Europe)
- Recupero credenziali di produzione (URL, Anon Key, Service Role)
**Status:** To Do

#### TASK-253 — Migrazione Schema DB e Seed Iniziale
- Applicazione di tutte le migrazioni (001-013) sull'istanza di produzione
- Caricamento dati di base (Seed) per configurazioni globali
**Status:** To Do

#### TASK-254 — Configurazione Variabili d'Ambiente (Secrets)
- Configurazione dei segreti sul VPS per Backend (API Keys Binance Live, OpenRouter, Supabase)
- Configurazione variabili build-time per Frontend (Production API URL)
**Status:** To Do

### 7.2 Hardening & Sicurezza
#### TASK-255 — Audit Row Level Security (RLS)
- Verifica che TUTTE le tabelle (strategies, trades, logs) abbiano RLS attivo
- Implementazione policy: `auth.uid() = user_id` per ogni operazione
- Test di "leakage" tra utenti diversi
**Status:** To Do

#### TASK-256 — Protezione API e Rate Limiting
- Configurazione Nginx/Cloudflare per limitare le richieste agli endpoint sensibili (/auth, /pipeline)
- Disabilitazione registrazione pubblica su Supabase Auth (solo admin invite)
**Status:** To Do

#### TASK-257 — Gestione Sessioni e JWT
- Configurazione durata token JWT e refresh token strategy
- Implementazione logout centralizzato (invalidation)
**Status:** To Do

### 7.3 Docker & CI/CD (Unified Stack)
#### TASK-264 — Refactoring Backend Dockerfile (Hardening & Optimization)
- Implementazione Hardening: utente non-root, rimozione package manager in runtime
- Configurazione env: `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUNBUFFERED=1`
- Creazione `.dockerignore` per evitare leak di `.env` o `tests/`
**Status:** To Do

#### TASK-265 — Dockerizzazione Frontend (Angular + Nginx)
- Creazione `frontend/Dockerfile` multi-stage (node builder + nginx runtime)
- Configurazione Nginx interno per gestire il fallback SPA (routing Angular)
- Ottimizzazione caching file statici
**Status:** To Do

#### TASK-266 — Orchestrazione docker-compose.prod.yml (Full Stack)
- Configurazione servizi: `backend`, `frontend`, `nginx-proxy` (Gateway), `certbot`
- Network isolation tra frontend e backend
- Gestione automatica volumi per certificati SSL
**Status:** To Do

#### TASK-273 — Pipeline CI/CD (GitHub Actions)
- Automatizzazione test asincroni (pytest) ad ogni push
- Build automatica immagini Docker e push su registry
- Trigger deploy automatico sul VPS tramite SSH
**Status:** To Do

### 7.4 Rilascio & Monitoraggio
#### TASK-305 — Deploy Backend su VPS
- Setup Healthcheck (`/health`) per zero-downtime deployment
**Status:** To Do

#### TASK-309 — Smoke Test Post-Deploy (Checklist Finale)
- Verifica connettività Binance Live (saldo reale, ticker)
- Verifica integrità WebSocket in produzione
- Verifica persistenza dati su Supabase Cloud
**Status:** To Do

---

## 🎯 EPIC-600 — Modulo Scalping Intraday (v2.0 Signal Intelligence)

> **Obiettivo:** Aggiungere a SynthTrade la capacità di operare in modalità scalping intraday semi-automatico con un'architettura a due layer: L1 Execution Engine (500ms–2s) e L2 AI Supervisor (ogni 10 min). Il segnale primario viene da dati di mercato reali (Funding Rate, CVD, OI, Sentiment); gli indicatori tecnici sono solo filtri di timing.
> **Ref. documento completo:** `docs/SynthTrade_ScalpingModule_Plan.md`
> **Modalità:** BACKTEST → PAPER → LIVE
> **Fasi:** 9 (Foundation → Go Live)

---

### FASE 1 — Foundation: Struttura Base + DB

#### TASK-601 — Creare struttura directory `app/scalping/`
**Status:** To Do
**Priorità:** Critica
**Dettagli:**
- Creare layout directory completo: `models/`, `strategies/`, `engine/`, `intelligence/`, `opportunity/`, `supervisor/`, `indicators/`, `data/`, `backtest/`, `session/`
- Aggiungere tutti i `__init__.py`
- Aggiungere `scalping/router.py` scheletro registrato in `main.py`

#### TASK-602 — Implementare Pydantic models completi
**Status:** To Do
**Priorità:** Critica
**Dettagli:**
- `models/strategy.py`: `StrategyType`, `StrategyParams`, `ScalpingStrategy`
- `models/signal.py`: `SignalType`, `Signal`, `ExecutionDecision`
- `models/position.py`: `Position`, `PositionStatus`
- `models/trade.py`: `Trade`, `TradeResult`
- `models/market.py`: `Candle`, `OrderBook`, `MarketRegime`
- `models/supervisor.py`: `SupervisorAction`, `SupervisorDecision`, `SupervisorContext`
- `models/intelligence.py`: `FundingRateSnapshot`, `CVDSnapshot`, `OpenInterestSnapshot`, `LongShortSnapshot`, `FearGreedSnapshot`, `SignalScore`, `MarketContext`
- `models/opportunity.py`: `Opportunity`, `OpportunityCategory`, `RawAnnouncement`

#### TASK-603 — Implementare `indicators/` (calcolo indicatori tecnici)
**Status:** To Do
**Priorità:** Alta
**Dettagli:**
- `moving_averages.py`: `ema()`, `sma()`, `vwap()` su lista candele
- `oscillators.py`: `rsi()`, `macd()`, `stochastic()`
- `volatility.py`: `atr()`, `bollinger_bands()`, `adx()`
- `volume.py`: `obv()`, `volume_profile()`
- Tutti i calcoli su `list[float]` puro, senza dipendenze esterne oltre `numpy`

#### TASK-604 — Implementare `data/candle_buffer.py`
**Status:** To Do
**Priorità:** Alta
**Dettagli:**
- Buffer circolare con `maxlen` configurabile
- Metodi: `add(candle)`, `get()`, `is_ready()`, `reset()`
- Thread-safe per uso asincrono

#### TASK-605 — Unit test completi per indicatori e buffer
**Status:** To Do
**Priorità:** Alta
**Dettagli:**
- `tests/scalping/test_indicators.py`: ogni funzione con valori noti e attesi
- `tests/scalping/test_candle_buffer.py`: overflow, readiness, reset
- Coverage >= 90%

#### TASK-606 — Migrazione Supabase schema scalping v2.0
**Status:** To Do
**Priorità:** Critica
**Dettagli:**
- Creare migration `014_scalping_schema.sql`
- Tabelle: `scalping_sessions`, `scalping_trades`, `supervisor_decisions`, `scalping_strategies`, `market_intel_snapshots`, `opportunities`
- Tutti gli indici per query storiche (symbol+time, urgency+time)
- Applicare su Supabase (via MCP o CLI)
- Aggiungere RLS policy per `user_id = auth.uid()` su tutte le tabelle

---

### FASE 2 — Signal Intelligence: Dati di Mercato Reali

#### TASK-610 — Implementare `intelligence/collectors/funding_rate.py`
**Status:** To Do
**Priorità:** Critica
**Dettagli:**
- `FundingRateCollector.fetch(symbol)` → `FundingRateSnapshot`
- Endpoint: `GET https://fapi.binance.com/fapi/v1/fundingRate`
- Gestione errori: timeout, rate limit, risposta vuota
- Test con mock HTTP (pytest-httpx)

#### TASK-611 — Implementare `intelligence/collectors/cvd_calculator.py`
**Status:** To Do
**Priorità:** Critica
**Dettagli:**
- `CVDCalculator`: si alimenta dallo stream WS `<symbol>@trade`
- `on_trade(BinanceTrade)` → aggiorna CVD cumulativo
- `get_snapshot()` → `CVDSnapshot` con trend (crescente/calante/neutro) e divergenza prezzo
- Buffer history `deque(maxlen=500)`
- Test: sequenza trade mock → CVD atteso

#### TASK-612 — Implementare `intelligence/collectors/open_interest.py`
**Status:** To Do
**Priorità:** Alta
**Dettagli:**
- `OpenInterestCollector.fetch(symbol)` → `OpenInterestSnapshot`
- Endpoint: `GET https://fapi.binance.com/fapi/v1/openInterest`
- Test con mock

#### TASK-613 — Implementare `intelligence/collectors/long_short_ratio.py`
**Status:** To Do
**Priorità:** Alta
**Dettagli:**
- `LongShortRatioCollector.fetch(symbol, period)` → `LongShortSnapshot`
- Endpoint: `/futures/data/globalLongShortAccountRatio`
- Test con mock

#### TASK-614 — Implementare `intelligence/collectors/fear_greed.py`
**Status:** To Do
**Priorità:** Media
**Dettagli:**
- `FearGreedCollector.fetch()` → `FearGreedSnapshot`
- Endpoint: `https://api.alternative.me/fng/`
- Cache locale 24h (si aggiorna una volta al giorno)
- Test con mock

#### TASK-615 — Implementare `intelligence/collectors/sentiment.py` (CryptoPanic)
**Status:** To Do
**Priorità:** Media
**Dettagli:**
- `SentimentCollector.fetch(currencies)` → score sentiment aggregato
- Endpoint: `https://cryptopanic.com/api/v1/posts/` con `filter=important`
- Richiede `CRYPTOPANIC_TOKEN` in settings
- Test con mock

#### TASK-616 — Implementare `intelligence/signal_score_engine.py`
**Status:** To Do
**Priorità:** Critica
**Dettagli:**
- `SignalScoreEngine.calculate(context: MarketContext)` → `SignalScore` (-100…+100)
- Pesi configurabili: funding_rate=0.25, cvd=0.25, open_interest=0.15, long_short=0.15, fear_greed=0.10, onchain=0.10
- `bias`: `bullish` (>20) / `bearish` (<-20) / `neutral`
- `tradeable`: True se `abs(total) > 30`
- Test: ogni scenario di mercato → score atteso

#### TASK-617 — Implementare `intelligence/intelligence_scheduler.py`
**Status:** To Do
**Priorità:** Alta
**Dettagli:**
- APScheduler job: aggiorna tutti i collector ogni 60s (funding, OI, L/S ratio)
- CVD: aggiornato real-time da WS (non schedulato)
- Fear&Greed: una volta al giorno
- Salva snapshot su `market_intel_snapshots`
- Endpoint `GET /intelligence/snapshot` restituisce contesto corrente

---

### FASE 3 — Strategie + Signal Aggregator

#### TASK-620 — Implementare `strategies/base.py` e `strategies/registry.py`
**Status:** To Do
**Priorità:** Alta
**Dettagli:**
- `AbstractScalpingStrategy` con metodi astratti `evaluate()` e `get_required_candles()`
- `StrategyRegistry`: dizionario `StrategyType → class`, metodo `get(type)`

#### TASK-621 — Implementare `strategies/ema_cross.py`
**Status:** To Do
**Priorità:** Alta
**Dettagli:**
- `EMACrossStrategy.evaluate(candles, indicators)` → `Signal`
- BUY: EMA fast cross sopra EMA slow + volume > media * multiplier + candela bullish
- CLOSE: EMA fast cross sotto EMA slow
- Regime ottimale: TRENDING

#### TASK-622 — Implementare `strategies/rsi_bollinger.py`
**Status:** To Do
**Priorità:** Alta
**Dettagli:**
- BUY: RSI < oversold + prezzo tocca BB lower + rimbalzo
- SELL: RSI > overbought + prezzo tocca BB upper
- Regime ottimale: LATERAL

#### TASK-623 — Implementare `strategies/vwap_reversion.py`
**Status:** To Do
**Priorità:** Alta
**Dettagli:**
- BUY: prezzo > 0.3% sotto VWAP + RSI < 40 + volume crescente
- Target: ritorno a VWAP (take profit dinamico)
- VWAP si resetta a mezzanotte

#### TASK-624 — Implementare `engine/regime_detector.py`
**Status:** To Do
**Priorità:** Alta
**Dettagli:**
- Input: `list[Candle]` + `dict` indicatori
- Usa ADX, ATR, BB Width per classificare: TRENDING_UP, TRENDING_DOWN, LATERAL, HIGH_VOLATILITY, LOW_VOLATILITY
- Test: ogni regime su candele mock

#### TASK-625 — Implementare `engine/strategy_selector.py`
**Status:** To Do
**Priorità:** Media
**Dettagli:**
- Mappa `MarketRegime → StrategyType`
- HIGH_VOLATILITY → pausa o VWAP
- TRENDING → EMA Cross
- LATERAL/LOW_VOLATILITY → RSI+BB

#### TASK-626 — Implementare `engine/signal_aggregator.py` ★ CORE
**Status:** To Do
**Priorità:** Critica
**Dettagli:**
- `SignalAggregator.should_execute(technical_signal, market_score)` → `ExecutionDecision`
- Gate 1: `market_score.tradeable` deve essere True
- Gate 2: direzione tecnica e bias intelligence devono essere allineati
- Se conflitto → `execute=False` con reason dettagliata
- Test: ogni combinazione allineato/conflitto

---

### FASE 4 — Backtest Engine

#### TASK-630 — Implementare `data/historical_loader.py`
**Status:** To Do
**Priorità:** Alta
**Dettagli:**
- Download OHLCV da Binance REST API per symbol, timeframe, date range
- Supporto funding rate e OI storici (Binance futures)
- Cache locale su file per evitare download ripetuti

#### TASK-631 — Implementare `backtest/backtest_engine.py`
**Status:** To Do
**Priorità:** Alta
**Dettagli:**
- Replay candele storiche con `SignalAggregator` integrato
- Simula esecuzione ordini (senza API reale)
- Supporto due modalità: con/senza intelligence layer (per confronto)
- Endpoint `POST /scalping/backtest/run` con parametri configurabili

#### TASK-632 — Implementare `backtest/performance_calculator.py`
**Status:** To Do
**Priorità:** Alta
**Dettagli:**
- Calcola: win rate, avg PnL, max drawdown, Sharpe ratio, profit factor
- Report comparativo: strategia sola vs strategia + intelligence
- Endpoint `GET /scalping/backtest/{id}/result`

#### TASK-633 — Frontend: pagina risultati backtest
**Status:** To Do
**Priorità:** Media
**Dettagli:**
- Tabella trade con signal_score evidenziato
- Grafico equity curve con lightweight-charts
- Comparativo KPI: con/senza intelligence layer

---

### FASE 5 — Execution Engine (Layer 1)

#### TASK-640 — Implementare `engine/order_executor.py`
**Status:** To Do
**Priorità:** Critica
**Dettagli:**
- Integrazione Binance REST API (spot + testnet)
- `buy(signal)` → order market/limit con SL/TP server-side
- `close()` → chiudi posizione aperta
- Gestione errori: insufficient funds, API down, timeout
- Test con Binance Testnet

#### TASK-641 — Implementare `engine/position_manager.py`
**Status:** To Do
**Priorità:** Critica
**Dettagli:**
- Traccia posizione aperta corrente
- `open(order, signal)`, `close(order)` → `TradeResult`
- Salva contesto intelligenza al momento dell'apertura (signal_score, funding_rate, fear_greed, cvd_trend)

#### TASK-642 — Implementare `engine/risk_manager.py`
**Status:** To Do
**Priorità:** Critica
**Dettagli:**
- `check_pre_trade(capital)` → `RiskCheckResult`
- Circuit breaker: max daily loss (3%), max consecutive losses (5)
- `on_trade_closed(trade)` aggiorna stato
- Hard stop: blocca tutto se limite superato

#### TASK-643 — Implementare `engine/execution_loop.py`
**Status:** To Do
**Priorità:** Critica
**Dettagli:**
- Main loop asincrono ogni 500ms–2s
- Sequenza: aggiorna buffer → calcola indicatori → detecta regime → seleziona strategia → genera segnale → check intelligence → check risk → esegui ordine → emit WS
- Supporto `start()`, `pause()`, `stop()`

#### TASK-644 — Implementare `session/session_manager.py`
**Status:** To Do
**Priorità:** Alta
**Dettagli:**
- Gestione stato sessione: `running`, `paused`, `stopped`
- Salva sessione su `scalping_sessions` Supabase
- `daily_summary.py`: riepilogo fine giornata automatico
- Endpoint REST: `POST /scalping/session/start|stop|pause`, `GET /scalping/session/status`

#### TASK-645 — WebSocket events verso frontend
**Status:** To Do
**Priorità:** Alta
**Dettagli:**
- WS endpoint `ws://host/ws/scalping`
- Eventi: `candle`, `signal`, `order`, `position`, `supervisor`, `risk_block`
- Ogni evento include payload tipizzato
- Test paper trading end-to-end su Binance Testnet

---

### FASE 6 — Opportunity Monitor

#### TASK-650 — Implementare `opportunity/pollers/binance_rss.py`
**Status:** To Do
**Priorità:** Alta
**Dettagli:**
- Poll RSS `https://www.binance.com/en/support/announcement/rss` ogni 5 min
- Parsing con `feedparser`
- Restituisce `list[RawAnnouncement]`

#### TASK-651 — Implementare `opportunity/pollers/cryptopanic.py`
**Status:** To Do
**Priorità:** Alta
**Dettagli:**
- Poll CryptoPanic API (filter=important) ogni 5 min
- Richiede `CRYPTOPANIC_TOKEN`

#### TASK-652 — Implementare `opportunity/pollers/coingecko.py` e `whale_alert.py`
**Status:** To Do
**Priorità:** Media
**Dettagli:**
- CoinGecko: trending coin (top 7 ultime 24h)
- WhaleAlert: transazioni > soglia (richiede `WHALE_ALERT_API_KEY`)

#### TASK-653 — Implementare `opportunity/deduplicator.py`
**Status:** To Do
**Priorità:** Alta
**Dettagli:**
- Hash SHA256 del contenuto (title+url) per deduplicazione cross-source
- Usa `content_hash UNIQUE` su tabella `opportunities`

#### TASK-654 — Implementare `opportunity/classifier.py` (Claude API)
**Status:** To Do
**Priorità:** Alta
**Dettagli:**
- Classifica ogni annuncio: `category`, `urgency`, `scalping_opportunity`, `expected_volatility`, `symbol`
- System prompt dedicato (JSON-only response)
- Gestione errori Claude API down → salva non classificato

#### TASK-655 — Implementare `opportunity/opportunity_router.py` e scheduler
**Status:** To Do
**Priorità:** Alta
**Dettagli:**
- Router: se urgency=HIGH + scalping_opportunity=True → notifica immediata via WS
- Se nuovo simbolo rilevante → aggiungi a watchlist engine
- Scheduler APScheduler ogni 5 minuti
- Endpoint: `GET /opportunities`, `WS /opportunities/live`

---

### FASE 7 — Frontend Dashboard Completa (Angular)

#### TASK-660 — Scaffolding modulo Angular `scalping/`
**Status:** To Do
**Priorità:** Alta
**Dettagli:**
- `scalping.module.ts`, `scalping-routing.module.ts` con lazy loading
- Tutti i file `models/*.model.ts` (strategy, signal, position, trade, session, intelligence, opportunity)
- Route `/scalping` registrata nell'app routing

#### TASK-661 — `ScalpingWsService` con auto-reconnect
**Status:** To Do
**Priorità:** Critica
**Dettagli:**
- `WebSocketSubject<ScalpingEvent>` con `retryWhen(delay(3000))`
- Subject separati per tipo: `candle$`, `signal$`, `position$`, `supervisorDecision$`, `riskBlock$`
- `intelligence$` per aggiornamenti Signal Intelligence
- `opportunity$` per feed opportunità

#### TASK-662 — `SessionControlsComponent`
**Status:** To Do
**Priorità:** Alta
**Dettagli:**
- Selettore modalità: PAPER / LIVE
- Selettore coppia: BTC/USDT, ETH/USDT, BNB/USDT
- Pulsanti: Avvia, Pausa, Ferma con stato dinamico
- Badge status sessione + elapsed time + trade count

#### TASK-663 — `LiveChartComponent` (TradingView lightweight-charts)
**Status:** To Do
**Priorità:** Alta
**Dettagli:**
- Candlestick real-time con `createChart()` da `lightweight-charts`
- Overlay segnali (marker BUY/SELL/CLOSE sulla candela)
- Badge regime mercato e strategia attiva in header
- Dark theme: background `#1a1a2e`

#### TASK-664 — `StrategyPanelComponent` e `RiskControlsComponent`
**Status:** To Do
**Priorità:** Media
**Dettagli:**
- StrategyPanel: mostra strategia attiva, parametri SL/TP/size, pulsante override manuale
- RiskControls: drawdown giornaliero, perdite consecutive, stato circuit breaker

#### TASK-665 — `PerformancePanelComponent` e `TradeLogComponent`
**Status:** To Do
**Priorità:** Alta
**Dettagli:**
- PerformancePanel: total PnL, win rate, profit factor, max drawdown, Sharpe
- TradeLog: tabella trade con colonne: entry/exit, PnL, signal_score, strategy, motivo

#### TASK-666 — `MarketIntelPanelComponent` ★ NUOVO
**Status:** To Do
**Priorità:** Alta
**Dettagli:**
- Mostra real-time: Funding Rate (con color coding), Open Interest, CVD trend, Long/Short Ratio, Fear&Greed gauge
- Score aggregato -100/+100 con breakdown per componente
- Aggiornamento via WS ogni 60s

#### TASK-667 — `SignalScorecardComponent` ★ NUOVO
**Status:** To Do
**Priorità:** Alta
**Dettagli:**
- Score aggregato visuale con barra -100 → +100
- Breakdown per segnale con peso e contributo
- Badge `bias`: bullish/bearish/neutral
- Indicatore `tradeable` (verde/rosso)

#### TASK-668 — `OpportunityFeedComponent` ★ NUOVO
**Status:** To Do
**Priorità:** Media
**Dettagli:**
- Lista opportunità ordinate per urgency (HIGH prima)
- Badge colorati: 🔴 HIGH, 🟡 MED, 🔵 LOW
- Azioni: [Monitora] [Ignora]
- Aggiornamento real-time via WS
- Filtri per categoria e urgency

#### TASK-669 — `SupervisorLogComponent`
**Status:** To Do
**Priorità:** Media
**Dettagli:**
- Log cronologico decisioni AI Supervisor
- Mostra: action, reason, confidence, `primary_signal` (campo v2.0), before/after params

---

### FASE 8 — AI Supervisor (Layer 2)

#### TASK-680 — Implementare `supervisor/context_builder.py` v2.0
**Status:** To Do
**Priorità:** Alta
**Dettagli:**
- Assembla `SupervisorContext` con: trade recenti, performance, Signal Intelligence snapshot, opportunità recenti, regime attuale, parametri attivi
- Include tutti i campi v2.0: `funding_rate`, `cvd_trend`, `signal_score`, `market_bias`

#### TASK-681 — Implementare `supervisor/claude_client.py` con system prompt v2.0
**Status:** To Do
**Priorità:** Critica
**Dettagli:**
- System prompt v2.0 con gerarchia segnali (funding rate > CVD > OI > L/S > F&G > onchain > tecnico)
- Response JSON con campo `primary_signal` e `market_bias`
- Model: `claude-sonnet-4-20250514`

#### TASK-682 — Implementare `supervisor/decision_parser.py` e `parameter_updater.py`
**Status:** To Do
**Priorità:** Alta
**Dettagli:**
- Parser: valida JSON Claude, gestisce tutti gli edge case, fallback su errore
- ParameterUpdater: hot-swap parametri sull'ExecutionLoop senza restart
- Test: tutti i tipi di azione + casi di JSON malformato

#### TASK-683 — Implementare `supervisor/supervisor_scheduler.py`
**Status:** To Do
**Priorità:** Alta
**Dettagli:**
- APScheduler job ogni 10 minuti durante sessione attiva
- Endpoint `POST /scalping/supervisor/trigger` per analisi manuale forzata
- Salva ogni `SupervisorDecision` su Supabase con `primary_signal`
- Emit evento WS `supervisor` al frontend

---

### FASE 9 — Go Live

#### TASK-690 — Security review pre-live
**Status:** To Do
**Priorità:** Critica
**Dettagli:**
- Stop loss SEMPRE su Binance server-side — verifica doppia nel codice
- Review `RiskManager`: max daily loss 3%, consecutive losses 5
- Verifica che mode=LIVE richieda conferma esplicita dell'utente (double confirmation dialog)
- Audit tutte le chiamate API Binance: nessuna operazione critica senza validazione

#### TASK-691 — Test LIVE con capitale minimo
**Status:** To Do
**Priorità:** Alta
**Dettagli:**
- Prima sessione: €5 su BTC/USDT, solo modalità VWAP Reversion
- Monitoraggio manuale prima settimana
- Analisi correlazione: signal_score al trade entry vs outcome (target: score>30 → win rate > 55%)
- Documentazione risultati in `docs/LIVE_LOG.md`

#### TASK-692 — Documentazione operativa e API keys setup
**Status:** To Do
**Priorità:** Alta
**Dettagli:**
- Aggiornare `.env.example` con tutte le nuove API keys: `BINANCE_TESTNET_KEY/SECRET`, `CRYPTOPANIC_TOKEN`, `GLASSNODE_API_KEY`, `WHALE_ALERT_API_KEY`
- Guida operativa: avvio mattutino, monitoraggio, chiusura serale
- Documentare tutte le soglie del Signal Score Engine

---

### FASE TEST — Testing Suite Scalping

#### TASK-695 — Unit test Signal Intelligence + Opportunity
**Status:** To Do
**Priorità:** Alta
**Dettagli:**
- `test_signal_score_engine.py`: ogni scenario (funding alto, CVD negativo, F&G estremi)
- `test_cvd_calculator.py`: stream trade mock → CVD atteso
- `test_funding_rate.py`: parsing API + soglie
- `test_decision_parser.py`: JSON Claude valido, malformato, incompleto
- `test_opportunity_classifier.py`: classificazione su esempi reali
- `test_deduplicator.py`: hash collision + cross-source dedup

#### TASK-696 — Integration test pipeline completa
**Status:** To Do
**Priorità:** Alta
**Dettagli:**
- `test_signal_aggregator.py`: segnale tecnico bloccato quando intelligence contraddice (funding +0.15% + CVD negativo → no BUY)
- `test_execution_loop.py`: loop completo con Binance mock
- `test_intelligence_pipeline.py`: collector → score → snapshot → DB
- `test_opportunity_pipeline.py`: poller → classifier → router → WS
- `test_supervisor.py`: ciclo completo con Claude mock arricchito v2.0

#### TASK-697 — E2E test Playwright modulo scalping
**Status:** To Do
**Priorità:** Media
**Dettagli:**
- `scalping-session.spec.ts`: avvio paper, pausa, stop, verifica stato
- `market-intel.spec.ts`: aggiornamento pannello intelligence ogni 60s
- `opportunity-feed.spec.ts`: notifica opportunità urgency HIGH
- `supervisor-log.spec.ts`: visualizzazione decisione AI con `primary_signal`

---

> [!TIP]
> **Hai bisogno di nuovi task?** Se devi aggiungere nuove funzionalità o miglioramenti non presenti in questa lista, consulta prima il file [BACKLOG.md](file:///c:/Users/andrea.mazzarotto/myJobs/SynthTrade/docs/BACKLOG.md) per vedere se sono già stati discussi o pianificati. Converti un'idea dal backlog in task solo quando è pronta per essere implementata.
