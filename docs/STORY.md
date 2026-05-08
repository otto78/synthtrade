
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

**Ultima modifica:** 2026-05-08 — Cline (v1.1.3 + nuovi task)
