# Active Tasks — SynthTrade

> **Fonte di verità:** questo file contiene il lavoro in corso e programmato.
> I task completati sono spostati in [ARCHIVE_TASKS.md](file:///c:/Users/andrea.mazzarotto/myJobs/SynthTrade/docs/ARCHIVE_TASKS.md).
> Le idee generali e i piani a lungo termine sono in [BACKLOG.md](file:///c:/Users/andrea.mazzarotto/myJobs/SynthTrade/docs/BACKLOG.md).

---

## 🛠️ Fase 6 — Stabilizzazione & Completamento (Debito Tecnico)

> **Obiettivo:** Chiudere tutti i task lasciati in sospeso nelle fasi precedenti per garantire un sistema "perfettamente funzionante" prima del deploy.

### TASK-035 — Refactor `StrategyRepository`

**Status:** In Progress  
**Priorità:** Alta  
**Dettagli:**
- Isolare la logica CRUD delle strategie.
- Implementare mapping robusto tra i tipi Supabase e i modelli Pydantic.
- Aggiungere caching per le strategie più richieste.

### TASK-038 — Refactor `MarketData` (Service pattern)
**Status:** In Progress  
**Priorità:** Alta  
**Dettagli:**
- Creazione di un `MarketDataService` centralizzato.
- Gestione trasparente della cache (OHLCV su Supabase) e del fetch da Binance.
- Implementazione di un sistema di "backoff" per i rate limit delle API.

### TASK-041 — Refactor `Ranker`
**Status:** In Progress  
**Priorità:** Media  
**Dettagli:**
- Ottimizzazione del calcolo dello score (Sharpe, PnL, Drawdown).
- Possibilità di pesare diversamente le metriche in base al `risk_level`.

### TASK-067 — Refactor `RankConfig`
**Status:** In Progress  
**Priorità:** Media

### TASK-068 — Refactor `StrategyGenerator`
**Status:** In Progress  
**Priorità:** Alta  
**Dettagli:**
- Ottimizzazione della generazione delle varianti di parametri.
- Miglioramento della stabilità durante la generazione massiva.

### TASK-069 — Refactor `StopLossManager`
**Status:** In Progress  
**Priorità:** Alta

### TASK-070 — Refactor `TradeExecutor`
**Status:** In Progress  
**Priorità:** Alta

### TASK-130 — Refactor Dashboard: cache con `shareReplay(1)` + invalidazione dopo 30s
**Status:** In Progress  
**Priorità:** Media  
**Dettagli:**
- Implementare `shareReplay(1)` nel `DashboardService` per evitare chiamate ridondanti.
- Aggiungere logica di invalidazione per forzare il refresh dei dati.

### TASK-169 — Refactor: `StrategyListComponent` + `StrategyRowComponent`
**Status:** In Progress  
**Priorità:** Media

### TASK-174 — Refactor: `LogFiltersComponent` + query params sync
**Status:** In Progress  
**Priorità:** Media

### TASK-175 — Installare e configurare Playwright
**Status:** In Progress  
**Priorità:** Alta  
**Dettagli:**
- Setup dell'ambiente di test Playwright.
- Configurazione dei browser (Chromium, Firefox) per i test cross-browser.

### TASK-176 — 🔴 E2E `auth.spec.ts` (login errato → errore; login corretto → /dashboard)
**Status:** In Progress  
**Priorità:** Alta

### TASK-177 — 🔴 E2E `strategies.spec.ts` (attivazione e disattivazione end-to-end)
**Status:** In Progress  
**Priorità:** Alta

### TASK-178 — 🔴 E2E `logs.spec.ts` (filtro level aggiorna lista)
**Status:** In Progress  
**Priorità:** Alta

### TASK-186 — 🔴 Test (Unit) `dashboard.page.spec.ts`
**Status:** To Do  
**Priorità:** Media  
**Dettagli:** Verifica che i componenti `StatCard` ricevano i dati corretti dal service e non mostrino "0" o "Loading" indefinitamente.

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

### TASK-421 — Test: `active-trade.page.spec.ts` aggiornato
**Status:** To Do  
**Priorità:** Media

### TASK-426 — StrategyRunner multi-simbolo
**Status:** In Progress  
**Priorità:** Alta  
**Dettagli:**
- `run_tick()` deve iterare su tutti i simboli in `allocation`.
- Generazione segnali indipendenti per ogni simbolo.
- Rispetto delle percentuali di budget per il calcolo della position size.

### TASK-427 — Frontend: selezione multi-crypto nel form generazione
**Status:** To Do  
**Priorità:** Media  
**Dettagli:**
- Form con aggiunta di più crypto e slider percentuale.
- Validazione: somma delle percentuali = 100%.

### TASK-428 — Test integrazione: flusso completo activate -> tick -> stop
**Status:** To Do  
**Priorità:** Alta  
**Dettagli:** Verifica con exchange mockato di tutti gli step del ciclo vita operativa.

### TASK-429 — Gestione errori e retry per exchange failures nel signal loop
**Status:** To Do  
**Priorità:** Alta  
**Dettagli:** Gestione di `asyncio.gather` con `return_exceptions=True` e broadcast di errori via WebSocket.

### TASK-430 — Dashboard: KPI globali strategie attive e trade aperti
**Status:** To Do  
**Priorità:** Media  
**Dettagli:** Aggiunta di `active_strategies_count` e `total_active_pnl_pct` alle statistiche dashboard.

---

## 🔍 Audit & Qualità (Pre-Deploy)

### TASK-AUDIT-001 — Verifica connettività API: Binance e OpenRouter
**Status:** To Do  
**Priorità:** Alta  
**File:** `synthtrade/backend/tests/test_connectivity.py`
**Step:** Leggere `.env`, chiamare `fetch_ticker`, verificare modelli OpenRouter.

### TASK-AUDIT-002 — Prova del Random (Verifica Allucinazioni)
**Status:** To Do  
**Priorità:** Alta  
**Descrizione:** Dimostrare che `generate_for_request()` non usa più valori casuali tramite test di determinismo.

### TASK-AUDIT-003 — Test AI Evaluator reale
**Status:** To Do  
**Priorità:** Alta  
**Descrizione:** Inviare prompt con dati reali a OpenRouter e verificare il parsing del JSON (score, verdict).

### TASK-AUDIT-004 — Verifica backtest con dati OHLCV reali di Binance
**Status:** To Do  
**Priorità:** Alta  
**Descrizione:** Confermare che il backtester produca risultati deterministici su dati storici.

### TASK-AUDIT-005 — Confronto DB: strategie manuali vs pipeline automatica
**Status:** To Do  
**Priorità:** Alta  
**Descrizione:** Verificare che tutte le strategie `PENDING` nel DB abbiano il campo `backtest` popolato.

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

> [!TIP]
> **Hai bisogno di nuovi task?** Se devi aggiungere nuove funzionalità o miglioramenti non presenti in questa lista, consulta prima il file [BACKLOG.md](file:///c:/Users/andrea.mazzarotto/myJobs/SynthTrade/docs/BACKLOG.md) per vedere se sono già stati discussi o pianificati. Converti un'idea dal backlog in task solo quando è pronta per essere implementata.
