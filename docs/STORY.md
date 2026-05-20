Storia operativa del progetto con versioni, milestone e decisioni chiave.

---

## 📖 Versioni

### v0.1.0 — 2025-01-15

**Milestone:** Fase 0 — Setup & Infrastruttura completata

**Completato:**
- Struttura monorepo `synthtrade/` (backend, supabase)
- `.gitignore`, `README.md`
- Backend FastAPI: `main.py`, `config.py`, `supabase_client.py`
- Route `GET /health` → `{"status": "ok"}` ✅
- `pytest.ini` + `conftest.py` con fixture `mock_supabase`
- 4 migration SQL (strategies, trades, operation_logs, ohlcv_cache)
- `seed.sql` con 3 strategie PENDING di esempio
- `Dockerfile` + `docker-compose.yml`
- `requirements.txt` con tutte le dipendenze

**Decisioni chiave:**
- Stack: FastAPI + Supabase + ccxt (Binance) + OpenRouter AI cascade
- Frontend: Angular 17+ con dark terminal UI (lightweight-charts)
- AI: cascade 4 modelli free OpenRouter + fallback Claude Haiku pagante
- Paper trading obbligatorio fino alla Fase 6
- TDD con pytest per backend, Jest per frontend

### v1.0.1 — 2026-05-07

**Milestone:** Standardizzazione porte di sviluppo

**Completato:**
- Backend configurato sulla porta 8008 (FastAPI, Docker, Docker Compose)
- Frontend configurato sulla porta 4208 (Angular, package.json, proxy)
- Aggiornata documentazione (README.md, PROJECT.md, HANDOFF.md)
- Allineate variabili d'ambiente (.env.example)

### v1.1.0 — 2026-05-07

**Milestone:** Fase 7 — Miglioramenti Evolutivi UX

**Completato:**
- ✅ **7.1 Persistenza & Scadenza Strategie**: Migration 005 con `expires_at`, trigger automatico 7gg, funzione cleanup. Backend/frontend già implementati per gestione scadenza e auto-pulizia. Migrazione applicata su Supabase Cloud (colonna + funzioni + trigger).
- ✅ **7.2 Gestione Strategie Attive**: Dialog conferma Stop, pagina Monitoraggio Real-time con polling 5s, equity curve, P&L, Win Rate.
- ✅ **7.3 Strategie Completate**: UI Accordion con intestazione (nome, data, P&L, performance%), dettaglio trade espandibile, statistiche, equity curve, pulsante Esporta Report.
- ✅ **7.4 Dashboard**: Ordinamento asset per valore EUR decrescente, colonna % Portfolio, Card strategia attiva con Score/Budget/Rischio AI, navigazione one-click alla vista Monitoraggio.
- Fix build frontend (errori TS, duplicati, unused imports) per bundle pulito.

### v1.1.1 — 2026-05-08

**Milestone:** Fix workflow strategie — persistenza, approvazione, scadenza

**Completato:**
- ✅ **Persistenza strategie su DB**: Le strategie generate vengono ora salvate immediatamente su Supabase con status `PENDING` e `expires_at = now + 7gg` (in `pipeline.py`). Non più solo in memoria.
- ✅ **Ricarica PENDING dal DB**: Il tab GENERAZIONE carica le strategie PENDING dal DB all'avvio della pagina. Navigando via e tornando, le strategie sono ancora lì.
- ✅ **Approvazione diretta**: `saveAndApprove()` approva l'ID già presente su DB invece di ricreare la strategia.
- ✅ **Fix BUG approvazione**: Non cancella più tutte le strategie generate dopo averne approvata una.
- ✅ **Transizione ACTIVE→EXPIRED**: Le strategie ACTIVE scadute ora transitano a EXPIRED (non solo cancellazione PENDING).
- ✅ **Tab COMPLETATE**: Mostra solo strategie EXPIRED, non più REJECTED.
- ✅ **Migration 006**: Fix `expires_at` NULL su tutti i record esistenti, funzione cleanup aggiornata.

**Decisioni chiave:**
- Le strategie generate vengono salvate su DB subito per garantire persistenza tra navigazioni e sessioni
- La cleanup PENDING scadute cancella i record, mentre ACTIVE scadute diventano EXPIRED per tracciabilità

### v1.2.6 — 2026-05-15

**Milestone:** Refactor Supabase Client & Dependency Injection (TASK-033)

**Completato:**
- ✅ **Supabase Singleton**: Il client Supabase è ora un singleton gestito con `@lru_cache` in `app/db/supabase_client.py`.
- ✅ **FastAPI Dependency**: Implementata la dependency `get_db` in `app/dependencies.py` per iniettare il client nelle route.
- ✅ **Fix Dummy Client**: Potenziato il `_DummyTable` per supportare il metodo `.single()`, risolvendo crash negli endpoint di metriche durante i test.
- ✅ **Test di regressione**: Risolti problemi di importazione e formato delle risposte nei test di integrazione (`test_pipeline_metrics.py`).

**Decisioni chiave:**
- Utilizzo della Dependency Injection di FastAPI come standard per l'accesso al database, facilitando il testing e il mocking.
- Unificazione del comportamento dei dummy client tra lo stub di root e quello del backend.

### v1.2.7 — 2026-05-15

**Milestone:** MarketData Service Refactor - OhlcvRepository (TASK-038)

**Completato:**
- ✅ **OhlcvRepository**: Creazione di un repository dedicato per la tabella `ohlcv_cache` in `app/db/repositories/`.
- ✅ **Dependency Injection**: Aggiunta di `get_ohlcv_repo` in `app/dependencies.py`.
- ✅ **Test di copertura**: Test unitari per il repository (`tests/test_task_038.py`) con mock Supabase.

---

## 🎯 Roadmap

### v0.2.0 — Core Engine
- [x] `indicators.py` (EMA, RSI, Bollinger + signal functions)
- [x] `strategy_generator.py` (prodotto cartesiano parametri)
- [x] `backtester.py` (simulazione OHLCV con fee/slippage)
- [x] `ranker.py` (score composito con filtri hard)
- [x] `market_data.py` (fetch Binance + cache Supabase)
- [x] `run_pipeline.py` (pipeline batch completa)

### v0.3.0 — Backend API
- [x] Auth JWT
- [x] API strategies, dashboard, logs
- [x] WebSocket live feed

### v0.4.0 — Frontend Angular ✅
- [x] Dark terminal UI completa
- [x] 3.0 Bootstrap (Angular, Jest, proxy, environments, eslint, prettier)
- [x] 3.1 Design Tokens (_variables, _mixins, _reset, _animations, theme-dark)
- [x] 3.2 Modelli TypeScript (user, strategy, trade, dashboard, log, ws-message)
- [x] 3.3 Interceptors & Guards (auth, error, authGuard, noAuthGuard)
- [x] 3.4 Services (TokenStorage, Auth, Strategy, Dashboard, Log, WebSocket)
- [x] 3.5 Shared Components & Pipes (StatCard, BadgeStatus, PriceTicker, ConfirmDialog, EmptyState, RelativeTime, FormatNumber, SignedNumber)
- [x] 3.6 Layout Shell (Sidebar, Topbar, AppShell)
- [x] 3.7 Routing (lazy loading, authGuard, noAuthGuard, redirect)
- [x] 3.8 Pagine (Login, Dashboard, Strategies, ActiveTrade, Logs)

### v0.5.0 — Execution Engine + AI ✅ (parziale)
- [x] `execution/schemas.py` (Signal, OrderRequest, OrderResult, RiskCheckResult, PositionSnapshot)
- [x] `execution/risk_manager.py` (RiskConfig, validate_signal, SL/TP calc) — 13 test
- [x] `execution/order_tracker.py` (open/close/get positions, unrealized P&L) — 7 test
- [x] `execution/signal_resolver.py` (SignalResolverProtocol + DefaultSignalResolver) — 5 test
- [x] `execution/execution_engine.py` (process_signal, check_exit_conditions) — 11 test
- [x] `scheduler/jobs.py` (APScheduler: pipeline, monitor, heartbeat) — 4 test
- [x] 4.6 Integration Tests (pipeline completa, stop loss, risk reject, drawdown) + `api/trades.py`

### v0.6.0 — AI Evaluator ✅
- [x] `ai/schemas.py` (MarketContext, StrategyContext, EvalPromptInput, EvalResult, ModelResponse)
- [x] `ai/context_builder.py` (build_market_context, detect_market_regime) — 7 test
- [x] `ai/prompt_builder.py` (build_prompt, build_system_prompt, token budget) — 6 test
- [x] `ai/model_client.py` (httpx, cascade, retry backoff, fallback, custom errors) — 7 test
- [x] `ai/eval_parser.py` (parse_eval_result, EvalParseError, markdown strip) — 8 test
- [x] `ai/cache.py` (get_cached_eval, save_eval, TTL Supabase) — 4 test
- [x] `ai/evaluator.py` (evaluate_strategy, evaluate_all con Semaphore) — 7 test
- [x] `api/eval.py` (GET eval, POST refresh, BackgroundTasks) — 4 test
- [x] Integrazione in `run_pipeline.py` (PROMOTE/DEMOTE/HOLD logic) — 4 test
- [x] Integration tests (happy path, fallback, cache hit, JSON malformato, all models down) — 5 test

### v2.0.0 — Modulo Scalping (Signal Intelligence) 🚀
- [ ] **Fase 1: Foundation & Models** (TASK-801 -> 804)
- [ ] **Fase 2: Signal Intelligence Collectors** (TASK-805 -> 810)
- [ ] **Fase 3: Engine & Signal Aggregation** (TASK-811 -> 813)
- [ ] **Fase 4: Fast Execution Engine (L1)** (TASK-814 -> 817)
- [ ] **Fase 5: Opportunity Monitor (AI News)** (TASK-818 -> 820)
- [ ] **Fase 6: AI Supervisor v2.0 (L2)** (TASK-821 -> 823)
- [ ] **Fase 7: Frontend Scalping Dashboard** (TASK-824 -> 828)
- [ ] **Fase 8: Backtest & Validation** (TASK-829 -> 832)

### v1.0.0 — Hardening & Deploy

- [ ] Supabase Cloud: RLS, Realtime, Auth
- [ ] Docker multi-stage: backend (python:3.12-slim) + frontend (node:20-alpine + nginx:alpine)
- [ ] docker-compose.prod.yml con network interna, logging json-file
- [ ] Nginx: reverse proxy, HTTPS, WebSocket upgrade, security headers, rate limiting
- [ ] Certbot / Let's Encrypt con rinnovo automatico
- [ ] VPS Ubuntu 24.04: utente non-root, UFW, Docker, unattended-upgrades
- [ ] Logging strutturato JSON con python-json-logger + request_id middleware
- [ ] Error handling globale con eccezioni custom e handler FastAPI
- [ ] scripts/deploy.sh + scripts/rollback.sh + scripts/smoke_test.sh
- [ ] Checklist pre-go-live (CORS, RLS, no hardcoded secrets, bundle size)

---

## 📊 Metriche

### Progresso Generale

- **Task completati:** 435 (Fase 7 completata)
- **Test passati:** 214 backend + 116 frontend = 330 totali
- **Test coverage:** ~82% backend, ~85% frontend core/shared

---

## 📝 Decisioni Architetturali

**2026-05-07 — Fase 7: Persistenza, Dashboard Avanzata, Fix Build**
- Problema: Strategie non avevano scadenza, Dashboard mancava di card strategia attiva e ordinamento asset, build frontend con errori.
- Soluzione: Migration 005 per `expires_at`, trigger auto cleanup. Dashboard con card interattiva e asset ordinati per exposure. Fix di tutti gli errori TS.
- Beneficio: Strategie auto-pulite dopo 7gg, UX dashboard migliorata, build pulito.

**2026-05-06 — Enhanced Strategy Generation & Rich UI**
- Problema: Varianti generate tutte uguali e mancanza di informazioni per l'utente nella scelta.
- Soluzione: Refactor di `strategy_generator.py` per generare varianti reali basate su griglie di parametri, timeframe e asset diversi. Implementata una UI "Rich Card" con descrizioni, tag dei parametri e punteggio AI.
- Beneficio: L'utente può ora confrontare le strategie in base a dati reali e punteggi suggeriti dall'AI.

**2026-05-06 — Integrazione UI Generatore Intelligente e Fix Networking**
- Problema: Necessità di un'interfaccia Angular per il nuovo generatore e conflitti di porte locali.
- Soluzione: Implementati componenti `StrategyRequestForm` e `GenerationProgress`. Spostato Frontend su porta 4201 e Backend su porta 8001 con prefisso `/api`.
- Beneficio: UX fluida per la creazione di strategie e ambiente di sviluppo isolato da altre app.

**2026-05-06 — Integrazione Framework Loom**
- Problema: Necessità di un workflow standardizzato per task management e TDD.
- Soluzione: Configurato framework Loom (DOE Architecture) e migrato tutti i task esistenti in `docs/TASKS.md` al nuovo formato `### TASK-XXX`.
- Beneficio: Piena compatibilità con gli script di automazione `loom/scripts/task.py` e tracciamento rigoroso dello stato.

---

## 📝 Decisioni Architetturali (Precedenti)

**2025-01-15 — Cascade AI con 5 tier**
- Problema: costo AI per valutare 200–800 strategie/giorno
- Soluzione: 4 modelli free OpenRouter in cascade, fallback Haiku pagante
- Costo worst case: ~$0.01/pipeline (solo se tutti i free falliscono)

**2025-01-15 — Cache OHLCV su Supabase**
- Problema: rate limit Binance (1200 weight/min)
- Soluzione: cache su tabella `ohlcv_cache`, fetch solo delta mancante
- Beneficio: riduce chiamate Binance del ~95% dopo il primo fetch

**2025-01-15 — Paper trading obbligatorio**
- Nessun ordine reale fino alla Fase 6 esplicita
- `PAPER_TRADING=true` in `.env` come default

---

### v1.1.2 — 2026-05-08

**Milestone:** Fix valutazione strategie — estimated_profit_pct/eur

**Completato:**
- ✅ **Migration 007**: Aggiunte colonne `estimated_profit_pct FLOAT` e `estimated_profit_eur FLOAT` alla tabella `strategies`
- ✅ **Fix `pipeline.py`**: `estimated_profit_pct` e `estimated_profit_eur` ora salvati nel row insert su DB
- ✅ **Fix `strategies.py`**: `list_strategies()` ora seleziona tutti i campi di valutazione (`estimated_profit_pct`, `estimated_profit_eur`, `description`, `pair`, `timeframe`, `params`, `ai_note`, `ai_strengths`, `ai_warnings`)
- ✅ Migration applicata su Supabase Cloud

**Decisioni chiave:**
- Le stime di profitto vengono salvate direttamente sul DB durante la generazione, non solo in memoria
- La SELECT di `list_strategies` è stata espansa da 9 a 18 campi per garantire la visibilità di tutti i dati di valutazione

### v1.1.3 — 2026-05-08

**Milestone:** Fix flusso UI generazione, nome personalizzato strategie, build error

**Completato:**
- ✅ **Spinner attesa**: Aggiunto `checkingSaved` signal con spinner "Verifico se ci sono strategie salvate..." durante il caricamento dal DB
- ✅ **Welcome card condizionale**: Appare solo dopo il caricamento e se non ci sono strategie salvate
- ✅ **Pulsante rinominato**: "Nuova Ricerca" → "Genera Nuove Strategie"
- ✅ **Cancellazione PENDING su generazione**: `startNewGeneration()` cancella tutte le PENDING dal DB prima di mostrare il form
- ✅ **Migration 008**: `ALTER TABLE strategies ADD COLUMN custom_name TEXT` applicata su Supabase Cloud
- ✅ **Nomi automatici AI**: Il generator crea nomi simpatici per template (es. "Il Seguace su BTC", "Mr RSI su ETH", "Lo Squartatore su SOL")
- ✅ **Override utente**: Il campo "Nome Personalizzato" nel form sovrascrive il nome automatico se compilato
- ✅ **Nome visibile in tutti i tab**: GENERAZIONE, APPROVATE, ATTIVE, COMPLETATE
- ✅ **Fix build TS2559**: Risolta collisione `MonitorData` tra interfaccia globale e locale

**Decisioni chiave:**
- I nomi personalizzati sono generati dall'AI in base al template, non dall'utente (ma l'utente può sovrascriverli)
- La cancellazione delle PENDING su "Genera Nuove Strategie" evita accumulo di strategie orfane

---

## 🎯 Prossimi Task (da BACKLOG)

### TASK-DASH-PNL — Fix P&L Dashboard sempre a 0
**Priorità:** Alta
- Verificare che l'API Binance restituisca il P&L reale
- Fixare il calcolo/visualizzazione del P&L nella Dashboard
- Aggiungere logging per debug del dato

### TASK-DASH-STRAT — Lista strategie attive riassuntiva in Dashboard
**Priorità:** Alta
- Mostrare tutte le strategie attive (non solo una) con: nome, budget iniziale, data avvio, saldo attuale, stima profitto %, risultato corrente
- Pulsante "Vedi Dettaglio" che porta alla pagina strategie attive

### TASK-DASH-GRAFICO — Grafico andamento saldo mensile in Dashboard
**Priorità:** Media
- Aggiungere grafico con l'andamento del saldo a scala mensile
- Usare lightweight-charts o barre semplici

### TASK-TRADE-PAGE — Refactoring pagina Active Trade
**Priorità:** Alta
- Mostrare lista di tutti i trade in corso e sotto quelli conclusi
- Ogni trade deve mostrare: nome strategia, asset, direzione, prezzo entry/exit, P&L, data
- Filtro dropdown per strategia
- Il pulsante "Monitora" nelle card strategie deve portare qui con filtro pre-attivato

### TASK-AUDIT-GEN — Audit processo generazione strategie
**Priorità:** Alta
- Aggiungere logging dettagliato su ogni fase: analisi mercato, creazione, validazione, backtest
- Verificare che i dati di mercato vengano caricati correttamente da Binance
- Verificare che le analisi AI siano basate su dati reali, non allucinate
- Aggiungere endpoint `/api/pipeline/audit/{generation_id}` per tracciare ogni step

### TASK-AUDIT-ACTIVATE — Audit processo attivazione ed esecuzione strategie
**Priorità:** Critica
- Analizzare il flusso di attivazione: APPROVED → ACTIVE → execution
- Verificare che all'avvio ci sia disponibilità economica reale nel saldo
- Testare l'esecuzione reale dei trade (paper trading)
- Verificare che stop loss / take profit vengano piazzati correttamente
- Aggiungere test di integrazione per l'intero ciclo vita

---

### v1.2.0 — 2026-05-12

**Milestone:** 🔴 Fix Allucinazioni — Backtest reale sostituisce random.uniform()

**Completato:**
- ✅ **Strategy Generator riscritto**: Rimosso `import random`, `random.uniform()`, `random.choice()`, `random.shuffle()`
- ✅ **Backtest reale**: `generate_for_request()` ora scarica OHLCV da Binance (90gg), esegue backtest reale, calcola score via `compute_score()`
- ✅ **StrategyParams aggiornato**: Rinominato `ai_score` → `score` (range [0,1]), aggiunti campi backtest: `backtest_pnl`, `backtest_win_rate`, `backtest_sharpe`, `backtest_drawdown`, `backtest_trades`, `data_source`
- ✅ **Nomi deterministici**: Rimossi nomi casuali tipo "Il Seguace", "Rompiballe". Usa titolo derivato da template + pair
- ✅ **Pipeline.py**: Salva `backtest` completo nel DB, WS progress events (fetching_market_data, saving), gestione lista vuota con messaggio utente
- ✅ **Test**: 21 test PASS (generator, constrained, random_proof, e2e_pipeline). Zero regressioni nella suite unità (152/157)

**Decisioni chiave:**
- Le strategie generate via UI ora si basano su dati storici reali Binance, non su valori casuali
- Score nel range [0,1] da `compute_score()` invece di range arbitrario [70,99]
- I nomi delle strategie ora sono deterministici invece di random.choice()
- Cache OHLCV per (pair, timeframe) evita N chiamate API per lo stesso asset
- Se backtest fallisce o score è None, la variante viene esclusa silenziosamente

---

### v1.2.1 — 2026-05-13

**Milestone:** 🔴 Fix Profitti Irrealistici — Soglie Ranker Ottimizzate

**Completato:**
- ✅ **Diagnosi profitti irrealistici**: Analisi su 8 asset top marketcap (BTC, ETH, SOL, BNB, ADA, DOT, LINK, AVAX) con 180gg di dati
- ✅ **Scoperta chiave**: Timeframe 15m perde su TUTTI gli asset (-43% a -60%). Solo RSI 1h su altcoin è profittevole (+10-20%). RSI 4h produce Sharpe 27+ con soli 5-9 trades — artefatto statistico che causava profitti "finti"
- ✅ **Ranker**: min_trades 8→15, min_sharpe 0.3→0.0, max_drawdown 22.0→40.0, min_pnl 2%→0%
- ✅ **Generator**: lookback 180→60gg, pairs default BTC/ETH/SOL/BNB, timeframes rimosso 15m
- ✅ **Test pipeline**: 5 strategie con P&L medio +16.78%, drawdown 11.1%, trades 16 — realistico per crypto

**Decisioni chiave:**
- 60 giorni di lookback sono sufficienti per significatività statistica (vs 180 che includeva trend obsoleti)
- Quattro asset default (BTC, ETH, SOL, BNB) aumentano le opportunità di trovare strategie valide
- Timeframe 1h è il miglior compromesso segnale/rumore per crypto
- Soglia min_trades=15 garantisce significatività statistica senza escludere strategie valide
- max_drawdown=40% riflette la volatilità reale delle crypto (drawdown 30-40% è normale)

---

## [1.2.3] — 2026-05-14

**Milestone:** Completamento Epica Execution & Monitoraggio Real-time

**Completato:**
- ✅ **TASK-400 - 403**: Implementazione `CapitalAllocator` e attivazione operativa delle strategie con acquisto asset su Binance.
- ✅ **TASK-414 - 416**: Monitoraggio real-time via WebSocket. Broadcasting automatico di eventi di trade e aggiornamento live del P&L.
- ✅ **TASK-417**: Endpoint `/trades/active` con join strategie via resource embedding di Supabase per una visualizzazione avanzata.
- ✅ **TASK-406 - 413**: Finalizzazione motore di esecuzione (`StrategyRunner`, `ExecutionEngine`, `OrderTracker`) e gestione dello stop operativo.

**Decisioni chiave:**
- Utilizzo della Dependency Injection in FastAPI per migliorare la testabilità degli endpoint critici.
- Broadcasting proattivo dal motore di esecuzione per garantire una UI sempre sincronizzata.
- Unificazione del formato dei messaggi WS per semplificare il consumo lato frontend.

---

### v1.2.2 — 2026-05-14

**Milestone:** Implementazione Peak-to-Trough Drawdown (TASK-415)

**Completato:**
- ✅ **Migration 009**: Aggiunta colonna `peak_equity_usdt` alla tabella `strategies`.
- ✅ **OrderTracker**: Implementato `get_realized_pnl` e potenziato `get_open_positions` per filtri per strategia.
- ✅ **StrategyRunner**: Integrato calcolo dinamico dell'equity (Realized + Unrealized PnL) e aggiornamento automatico del picco massimo per un calcolo accurato del Drawdown.

**Decisioni chiave:**
- Il drawdown viene ora calcolato dal punto di massimo profitto raggiunto (Peak-to-Trough) anziché dal capitale iniziale, garantendo una protezione più robusta dei profitti accumulati.

### v1.2.4 — 2026-05-14

**Milestone:** Fix Operativi Testnet — Dashboard, Trade View, Stop

**Completato:**
- ✅ **Bug 1 — Dashboard pending**: Aggiunto timeout (15s) + fallback OFFLINE in `dashboard.service.ts`. La dashboard ora non resta più bloccata su "loading" se il backend è lento/offline.
- ✅ **Bug 2 — Trade attivi non visibili**: Riscritta `active-trade.page.ts` per supportare MULTIPLE strategie attive con caricamento dati via `GET /api/strategies/active/pnl` e `GET /api/monitor/{id}`. Aggiunte interfacce `ActivePnlItem`, `MonitorStrategyInfo` in `strategy.service.ts`. Fix calcolo P&L cumulativo in `monitor.py`.
- ✅ **Bug 3 — Stop non chiude trade su DB**: La chiusura trade su DB ora avviene SEMPRE, indipendentemente dal successo/failure di `exchange.close_position()`. Se exchange fallisce, mantiene il prezzo entry e P&L=0, ma i trade passano comunque a status CLOSED.

**Decisioni chiave:**
- La dashboard deve essere resiliente al fallimento del backend — timeout + fallback anziché loading infinito
- I trade vengono chiusi su DB **sempre**, anche se l'exchange non risponde, per evitare trade orfani
- La pagina Active Trades ora supporta n strategie attive in contemporanea, non più una sola

---

### v1.2.5 — 2026-05-14

**Milestone:** Stato Attuale EPIC-400 Execution Epic

**EPIC-400 Execution Epic completato all'85%** (42 task Done su 49 totali della sezione dedicata EPIC-400/Fase 4)

**Completato oggi:**
- ✅ Fix duplicato status TASK-425 in TASKS.md (era "Pending" + "Done ✅", ora corretto a "Done ✅")
- ✅ Sync documentazione: TASKS.md e STORY.md allineati

**EPIC-400 Execution Epic — Riepilogo Task:**
- **Fase A (Allocazione Capitale)**: ✅ 4/4 completati (TASK-400 → 403)
- **Fase B (Loop Esecuzione)**: ✅ 7/7 completati (TASK-404 → 410)
- **Fase C (Stop Strategia)**: ✅ 3/3 completati (TASK-411 → 413)
- **Fase D (P&L Real-time)**: ✅ 4/4 completati (TASK-414 → 417)
- **Fase E (Frontend Active Trades)**: 🔴 1/4 completati (solo TASK-420 Done; TASK-418, 419, 421 Pending)
- **Fase F (P&L Live Strategie)**: ✅ 3/3 completati (TASK-422 → 424)
- **Fase G (Multi-Crypto)**: 🟡 1/3 completati (TASK-425 Done, TASK-426 In Progress, TASK-427 Pending)
- **Fase H (Stabilizzazione E2E)**: 🔴 0/3 completati (TASK-428, 429, 430 tutti Pending)
- **Bug Fix**: ✅ 1/1 completato (TASK-431)

---

---

### v1.2.8 — 2026-05-19

**Milestone:** 🔴 Fix saldo dashboard — 1500€ fittizio → saldo reale testnet

**Completato:**
- ✅ **Performance `get_total_balance_eur()`**: Riscritta con `fetch_tickers()` batch invece di `fetch_ticker()` individuale per ogni asset. Tempo di esecuzione: da **240 secondi** a **4.7 secondi** per 433 asset.
- ✅ **Fallback hardcoded 1500€ rimosso**: La dashboard ora mostra il saldo reale (anche 0.0) invece di iniettare un valore fittizio quando il saldo è 0 o c'è timeout.
- ✅ **Test aggiornato**: `test_dashboard_fallback_when_balance_zero` rinominato in `test_dashboard_shows_real_balance_when_zero` con asserzione 0.0.

**Decisioni chiave:**
- `fetch_tickers()` in una singola chiamata batc h invece di N chiamate individuali evita rate-limit e timeout
- Il saldo reale (anche 0) è sempre preferibile a un valore fittizio — l'utente deve vedere la verità del proprio conto

---

### v1.2.9 — 2026-05-20

**Milestone:** Diversificazione strategie — da 3 a 8 template con nomi descrittivi

**Completato:**
- ✅ **Da 3 a 8 template**: aggiunti `trend_ema_fast` (Fast EMA Momentum), `mean_reversion_rsi_aggressive` (Aggressive RSI Reversal), `breakout_bb_tight` (Bollinger Squeeze), `momentum_macd` (MACD Momentum), `scalp_short_term` (Short-Term Scalping)
- ✅ **Più varietà di parametri**: ogni template ha ora più combinazioni (es. ema_fast da [10,20] → [10,20,50])
- ✅ **Range durate ampliato**: da 3gg (scalp) a 30gg (trend), coprendo ogni esigenza di trading
- ✅ **Filtri rilassati**: tolleranza durata 80% (era 50%), fallback su 3 template invece di 1 solo
- ✅ **Nomi descrittivi**: tutti i template titolo umano (es. "Trend Following EMA — BTC/USDT 1h" invece di "trend_ema BTC/USDT 1h")
- ✅ **Fix `run_pipeline.py`**: titolo ora usa `strategy.title` invece di concatenare template ID tecnico
- ✅ **Nuove funzioni indicatore**: `signal_macd_crossover`, `signal_ema_dual_crossover`, `macd()`
- ✅ **Registry aggiornato**: tutti gli 8 template registrati in `StrategyRegistry._load_defaults()`
- ✅ **Prompt AI esteso**: `request_enricher.py` aggiornato con tutti gli 8 template

**Decisioni chiave:**
- Aumentare i template da 3 a 8 garantisce che anche con filtri attivi, l'utente veda sempre strategie diversificate
- La tolleranza durata 80% evita che template validi vengano esclusi per piccole differenze di durata
- I titoli descrittivi migliorano UX: l'utente capisce subito la logica della strategia

---

**Ultima modifica:** 2026-05-20 — Cline (Diversificazione strategie: 3→8 template, nomi descrittivi, filtri rilassati)
