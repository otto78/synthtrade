# SynthTrade — TASKS

> Aggiornato automaticamente. Metodologia TDD: 🔴 Red → 🟢 Green → 🔵 Refactor

---

## 🔵 Fase 0 — Setup & Infrastruttura

### Monorepo & Tooling
- [x] Creare struttura cartelle `synthtrade/` con `backend/`, `supabase/`
- [x] Inizializzare Git con `.gitignore`
- [x] Creare `README.md` con istruzioni setup locale

### Backend Bootstrap
- [x] Creare `requirements.txt` con tutte le dipendenze
- [x] Creare `config.py` con `Settings` via `pydantic-settings`
- [x] Creare `main.py` con lifespan, CORS, router placeholder
- [x] 🔴 Test: `test_main.py` → `GET /health` restituisce `{"status": "ok"}` ✅
- [x] 🟢 Implementare route `/health` ✅
- [x] Creare `pytest.ini` con `asyncio_mode = auto`
- [x] Creare `conftest.py` con fixture `mock_supabase`

### Supabase Setup
- [x] Creare le 4 migration SQL (strategies, trades, logs, ohlcv_cache)
- [x] Creare `seed.sql` con 3 strategie di esempio PENDING
- [x] Creare `supabase_client.py` singleton

### Docker
- [x] `docker-compose.yml` per backend (porta 8000)
- [x] `Dockerfile` backend

---

## 🟡 Fase 1 — Core Engine

### Indicatori tecnici
- [x] 🔴 Test `test_indicators.py` ✅ 17 test
- [x] 🟢 Implementare `indicators.py` ✅
- [x] 🔵 Refactor: costante `LOOKBACK_PERIODS` ✅

### Strategy Generator
- [x] 🔴 Test `test_generator.py` ✅ 8 test
- [x] 🟢 Implementare `strategy_generator.py` ✅
- [ ] 🔵 Refactor: `TEMPLATES` configurabile via JSON

### Backtester
- [x] 🔴 Test `test_backtester.py` ✅ 14 test
- [x] 🟢 Implementare `backtester.py` ✅
- [ ] 🔵 Refactor: `StopLossManager` separato

### Ranker
- [x] 🔴 Test `test_ranker.py` ✅ 15 test
- [x] 🟢 Implementare `ranker.py` ✅
- [ ] 🔵 Refactor: `RankConfig` da `.env`

### Market Data + Cache Supabase
- [x] 🔴 Test `test_market_data.py` ✅ 7 test
- [x] 🟢 Implementare `market_data.py` ✅
- [ ] 🔵 Refactor: separare `exchange.py`

### Pipeline Batch
- [x] 🔴 Test `test_pipeline.py` (integration) ✅ 5 test
- [x] 🟢 Implementare `run_pipeline.py` ✅
- [ ] 🔵 Refactor: progress logging + gestione eccezioni

---

## 🟠 Fase 2 — Backend API

### Auth
- [x] 🔴 Test `test_api_auth.py` ✅ 7 test
- [x] 🟢 Implementare `api/auth.py` + JWT ✅
- [x] 🟢 Implementare `dependencies.py` → `get_current_user` ✅
- [x] 🔵 Refactor: `core/auth_utils.py` ✅

### Strategies API
- [x] 🔴 Test `test_api_strategies.py` ✅ 12 test
- [x] 🟢 Implementare `api/strategies.py` ✅
- [ ] 🔵 Refactor: `StrategyRepository`

### Dashboard API
- [x] 🔴 Test `test_api_dashboard.py` ✅ 10 test
- [x] 🟢 Implementare `api/dashboard.py` ✅
- [ ] 🔵 Refactor: cache balance 30s

### Logs API
- [x] 🔴 Test `test_api_logs.py` ✅ 12 test
- [x] 🟢 Implementare `api/logs.py` ✅
- [ ] 🔵 Refactor: filtri aggiuntivi

### WebSocket
- [x] 🔴 Test `test_ws.py` ✅ 6 test
- [x] 🟢 Implementare `api/ws.py` ✅
- [x] 🔵 Refactor: broadcast per tipo ✅

---

## 🟢 Fase 3 — Frontend Angular

### 3.0 Bootstrap & Configurazione
- [x] Creare Angular app: `ng new synthtrade-ui --style=scss --routing --standalone`
- [x] Rimuovere Karma/Jasmine, installare `jest-preset-angular`, creare `jest.config.ts` e `setup-jest.ts`
- [x] Creare `tsconfig.spec.json` per Jest
- [x] Configurare `environment.ts` / `environment.prod.ts` con `apiUrl`, `wsUrl`, `supabaseUrl`, `supabaseAnonKey`
- [x] Configurare `proxy.conf.json` per dev: `/api → localhost:8000`, `/ws → localhost:8000`
- [x] Aggiungere script npm: `start:proxy`, `test:watch`, `test:ci`, `test:coverage`
- [x] Installare e configurare `eslint` + `prettier` con regole Angular
- [x] Configurare `jest --coverage` con soglia minima 80% su `core/` e `shared/`

### 3.1 Design Tokens & Tema
- [x] Creare `src/styles/_variables.scss`
- [x] Creare `src/styles/_mixins.scss`
- [x] Creare `src/styles/_reset.scss`
- [x] Creare `src/styles/_animations.scss`
- [x] Creare `src/styles/theme-dark.scss`
- [x] Importare tutto in `styles.scss`

### 3.2 Modelli & Interfacce
- [x] `core/models/user.model.ts` → `User`, `AuthTokens`, `JwtPayload`
- [x] `core/models/strategy.model.ts` → `Strategy`, `StrategyStatus`, `StrategyCreateDto`, `StrategyMetrics`
- [x] `core/models/trade.model.ts` → `Trade`, `TradeDirection`, `TradeStatus`
- [x] `core/models/dashboard.model.ts` → `DashboardStats`, `BalanceSnapshot`, `PipelineStatus`
- [x] `core/models/log.model.ts` → `OperationLog`, `LogLevel`, `LogFilters`, `PaginatedLogs`
- [x] `core/models/ws-message.model.ts` → `WsMessage<T>`, `WsMessageType` (enum)

### 3.3 Interceptors & Guards
- [x] 🔴 Test `auth.interceptor.spec.ts` ✅ 2 test
- [x] 🟢 Implementare `core/interceptors/auth.interceptor.ts` ✅
- [x] 🔴 Test `error.interceptor.spec.ts` ✅ 3 test
- [x] 🟢 Implementare `core/interceptors/error.interceptor.ts` ✅
- [x] 🔴 Test `auth.guard.spec.ts` ✅ 3 test
- [x] 🟢 Implementare `core/guards/auth.guard.ts` ✅
- [x] 🔴 Test `no-auth.guard.spec.ts` ✅ 2 test
- [x] 🟢 Implementare `core/guards/no-auth.guard.ts` ✅

### 3.4 Services
- [x] 🔴 Test `token-storage.service.spec.ts` ✅ 7 test
- [x] 🟢 Implementare `core/services/token-storage.service.ts` ✅
- [x] 🔴 Test `auth.service.spec.ts` ✅ 7 test
- [x] 🟢 Implementare `core/services/auth.service.ts` ✅
- [x] 🔴 Test `strategy.service.spec.ts` ✅ 5 test
- [x] 🟢 Implementare `core/services/strategy.service.ts` ✅
- [x] 🔴 Test `dashboard.service.spec.ts` ✅ 4 test (incl. cache 30s)
- [x] 🟢 Implementare `core/services/dashboard.service.ts` ✅
- [ ] 🔵 Refactor: cache con `shareReplay(1)` + invalidazione dopo 30s
- [x] 🔴 Test `log.service.spec.ts` ✅ 5 test
- [x] 🟢 Implementare `core/services/log.service.ts` ✅
- [x] 🔴 Test `ws.service.spec.ts` ✅ 5 test
- [x] 🟢 Implementare `core/services/ws.service.ts` ✅
- [x] 🔵 Refactor: `on<T>(type)` helper tipizzato ✅

### 3.5 Shared — Componenti Atomici
- [x] 🔴 Test `stat-card.component.spec.ts` (label, value, delta, skeleton) ✅ 4 test
- [x] 🟢 Implementare `shared/components/stat-card/` ✅
- [x] 🔴 Test `badge-status.component.spec.ts` (testo e classe CSS per ogni status) ✅ 6 test
- [x] 🟢 Implementare `shared/components/badge-status/` ✅
- [x] 🔴 Test `price-ticker.component.spec.ts` (decimali, flash-up, flash-down, rimozione classe) ✅ 4 test
- [x] 🟢 Implementare `shared/components/price-ticker/` ✅
- [x] 🔴 Test `confirm-dialog.component.spec.ts` (confirmed, cancelled, Escape) ✅ 5 test
- [x] 🟢 Implementare `shared/components/confirm-dialog/` ✅
- [x] 🟢 Implementare `shared/components/empty-state/` ✅
- [x] 🔴 Test `relative-time.pipe.spec.ts` ✅ 5 test
- [x] 🟢 Implementare `shared/pipes/relative-time.pipe.ts` ✅
- [x] 🔴 Test `format-number.pipe.spec.ts` (K/M suffisso) ✅ 5 test
- [x] 🟢 Implementare `shared/pipes/format-number.pipe.ts` ✅
- [x] 🔴 Test `signed-number.pipe.spec.ts` ✅ 4 test
- [x] 🟢 Implementare `shared/pipes/signed-number.pipe.ts` ✅

### 3.6 Layout Shell
- [x] 🔴 Test `sidebar.component.spec.ts` (voce attiva, toggle collapsed) ✅ 4 test
- [x] 🟢 Implementare `layout/sidebar/` (Dashboard, Strategies, Active Trade, Logs) ✅
- [x] 🔴 Test `topbar.component.spec.ts` (username, logout) ✅ 2 test
- [x] 🟢 Implementare `layout/topbar/` ✅
- [x] 🟢 Implementare `layout/app-shell/` ✅
- [ ] 🔵 Refactor: stato collapsed persistito in localStorage

### 3.7 Routing
- [x] Creare `app.routes.ts` con lazy loading (login, dashboard, strategies, active-trade, logs) ✅
- [x] 🔴 Test routing: `''` → `/login` senza token, `''` → `/dashboard` con token ✅ 6 test
- [x] 🔴 Test: `authGuard` redirige a `/login` senza token ✅

### 3.8 Pagine

#### LoginPage
- [x] 🔴 Test `login.component.spec.ts` (form invalido, submit, 401, redirect, spinner) ✅ 7 test
- [x] 🟢 Implementare `pages/login/login.page.ts` ✅
- [ ] 🔵 Refactor: estrarre `LoginFormComponent`

#### DashboardPage
- [x] 🔴 Test `dashboard.component.spec.ts` (getStats, 4 StatCard, WS stats_update, loading) ✅ 4 test
- [x] 🟢 Implementare `pages/dashboard/dashboard.page.ts` ✅
- [ ] 🟢 Aggiungere grafico balance history
- [ ] 🔵 Refactor: `DashboardStore` con Angular Signals

#### StrategiesPage
- [x] 🔴 Test `strategies.component.spec.ts` (list, activate, delete+confirm, filtro, empty state) ✅ 5 test
- [x] 🟢 Implementare `pages/strategies/strategies.page.ts` ✅
- [ ] 🔵 Refactor: `StrategyListComponent` + `StrategyRowComponent`

#### ActiveTradePage
- [x] 🔴 Test `active-trade.component.spec.ts` (empty state, render trade, WS price_update, P&L classi) ✅ 5 test
- [x] 🟢 Implementare `pages/active-trade/active-trade.page.ts` ✅

#### LogsPage
- [x] 🔴 Test `logs.component.spec.ts` (getLogs, filtro level, paginazione, riga, WS new_log) ✅ 5 test
- [x] 🟢 Implementare `pages/logs/logs.page.ts` ✅
- [ ] 🔵 Refactor: `LogFiltersComponent` + query params sync

### 3.9 E2E
- [ ] Installare e configurare Playwright
- [ ] 🔴 E2E `auth.spec.ts` (login errato → errore; login corretto → /dashboard)
- [ ] 🔴 E2E `strategies.spec.ts` (attivazione e disattivazione end-to-end)
- [ ] 🔴 E2E `logs.spec.ts` (filtro level aggiorna lista)

---

## 🔴 Fase 4 — Execution Engine

> Struttura: `synthtrade/backend/app/execution/` + `synthtrade/backend/app/scheduler/`

### 4.0 Modelli & Configurazione
- [x] Aggiungere in `config.py`: `MAX_CONCURRENT_POSITIONS`, `MAX_EXPOSURE_PER_SYMBOL_PCT`, `MAX_DRAWDOWN_PCT`, `DEFAULT_POSITION_SIZE_PCT`, `DEFAULT_STOP_LOSS_PCT`, `DEFAULT_TAKE_PROFIT_PCT`, `SCHEDULER_PIPELINE_INTERVAL_MIN` ✅
- [x] Creare `execution/schemas.py`: `Signal`, `OrderRequest`, `OrderResult`, `RiskCheckResult`, `PositionSnapshot` ✅

### 4.1 RiskManager
- [x] 🔴 Test `test_risk_manager.py` ✅ 13 test
- [x] 🟢 Implementare `execution/risk_manager.py` ✅
- [ ] 🔵 Refactor: `RiskConfig` dataclass iniettabile nei test

### 4.2 OrderTracker
- [x] 🔴 Test `test_order_tracker.py` ✅ 7 test
- [x] 🟢 Implementare `execution/order_tracker.py` ✅

### 4.3 SignalResolver
- [x] 🔴 Test `test_signal_resolver.py` ✅ 5 test
- [x] 🟢 Implementare `execution/signal_resolver.py` con `SignalResolverProtocol` + `DefaultSignalResolver` ✅
- [ ] 🔵 Refactor: pluggabile via `config.py` con `importlib`

### 4.4 ExecutionEngine
- [x] 🔴 Test `test_execution_engine.py` ✅ 11 test
- [x] 🟢 Implementare `execution/execution_engine.py` ✅
- [ ] 🔵 Refactor: `SignalResolver` iniettato nel costruttore

### 4.5 Scheduler
- [x] 🔴 Test `test_scheduler.py` ✅ 4 test
- [x] 🟢 Implementare `scheduler/jobs.py` con `AsyncIOScheduler` ✅
- [x] 🟢 Aggiungere `GET /api/scheduler/status` ✅
- [x] 🟢 Registrare scheduler nel lifespan di `main.py` ✅
- [ ] 🔵 Refactor: intervalli configurabili da `Settings`

### 4.6 Integration Tests
- [x] 🔴 Test `test_execution_integration.py` → pipeline completa: Signal → trade aperto su Supabase ✅
- [x] 🔴 Test → scenario stop loss: posizione aperta → SL raggiunto → posizione chiusa ✅
- [x] 🔴 Test → scenario risk reject: portfolio al limite → nessun ordine → log con reason ✅
- [x] 🔴 Test → scenario drawdown: drawdown oltre soglia → tutti i signal rigettati ✅
- [x] 🟢 `api/trades.py`: `GET /api/trades`, `GET /api/trades/open` ✅ 5 test

---

## 🟣 Fase 5 — AI Evaluator

> Struttura: `synthtrade/backend/app/ai/` con `schemas.py`, `context_builder.py`, `prompt_builder.py`, `model_client.py`, `eval_parser.py`, `cache.py`, `evaluator.py`

### 5.0 Config & Schemas
- [ ] Aggiungere in `config.py`: `AI_PRIMARY_PROVIDER`, `AI_PRIMARY_MODEL`, `AI_FALLBACK_PROVIDER`, `AI_FALLBACK_MODEL`, `AI_API_KEY`, `AI_API_BASE_URL`, `AI_MAX_TOKENS`, `AI_TEMPERATURE`, `AI_TIMEOUT_SECONDS`, `AI_MAX_RETRIES`, `AI_BACKOFF_BASE`, `AI_EVAL_CACHE_TTL_MINUTES`
- [ ] Creare `ai/schemas.py`: `MarketContext`, `StrategyContext`, `EvalPromptInput`, `EvalResult` (score, verdict, reasoning, confidence, model_used, tokens), `ModelResponse`

### 5.1 MarketContext Builder
- [ ] 🔴 Test `test_context_builder.py` → `build_ohlcv_summary()` aggrega N candles in statistiche
- [ ] 🔴 Test → `ValueError` se candles vuoti o sotto il minimo
- [ ] 🔴 Test → `detect_market_regime()` → `trending`/`volatile`/`ranging` in base ad ADX/ATR
- [ ] 🔴 Test → `build_market_context()` compone `MarketContext` completo da Supabase
- [ ] 🔴 Test → usa cache Supabase se disponibile e non scaduta
- [ ] 🟢 Implementare `ai/context_builder.py`
- [ ] 🔵 Refactor: `MarketRegimeDetector` con soglie configurabili da `Settings`

### 5.2 Prompt Builder
- [ ] 🔴 Test `test_prompt_builder.py` → `build_prompt()` include symbol, timeframe, metriche, indicatori
- [ ] 🔴 Test → include istruzioni JSON con campi `EvalResult`
- [ ] 🔴 Test → tronca se supera token budget (`AI_MAX_TOKENS`)
- [ ] 🔴 Test → `build_system_prompt()` restituisce ruolo analista quantitativo
- [ ] 🟢 Implementare `ai/prompt_builder.py`
- [ ] 🔵 Refactor: template `.jinja2` separato da logica

### 5.3 Model Client
- [ ] 🔴 Test `test_model_client.py` → `_call_model()` POST corretto con headers e body
- [ ] 🔴 Test → restituisce `ModelResponse` con content e token usage
- [ ] 🔴 Test → retry con backoff esponenziale su 429/503 fino a `AI_MAX_RETRIES`
- [ ] 🔴 Test → esauriti retry → `ModelClientError`
- [ ] 🔴 Test → timeout → `ModelTimeoutError`
- [ ] 🔴 Test → `_call_model_with_fallback()` tenta primario poi fallback
- [ ] 🔴 Test → entrambi falliscono → `AllModelsUnavailableError`
- [ ] 🟢 Implementare `ai/model_client.py` con `httpx.AsyncClient`
- [ ] 🔵 Refactor: `@async_retry` decorator in `ai/retry.py`

### 5.4 EvalResult Parser & Validator
- [ ] 🔴 Test `test_eval_parser.py` → `parse_eval_result()` deserializza JSON in `EvalResult`
- [ ] 🔴 Test → estrae JSON da blocchi markdown ` ```json ... ``` `
- [ ] 🔴 Test → `score` fuori [0,1] viene clampato con warning
- [ ] 🔴 Test → `verdict` non valido → `EvalParseError`
- [ ] 🔴 Test → `reasoning` mancante/vuoto → `EvalParseError`
- [ ] 🔴 Test → JSON malformato → `EvalParseError` (non `JSONDecodeError` nuda)
- [ ] 🟢 Implementare `ai/eval_parser.py`

### 5.5 EvalCache
- [ ] 🔴 Test `test_eval_cache.py` → `get_cached_eval()` restituisce `EvalResult` se non scaduto
- [ ] 🔴 Test → `None` se assente o oltre `AI_EVAL_CACHE_TTL_MINUTES`
- [ ] 🔴 Test → `save_eval()` upsert su Supabase per `strategy_id`
- [ ] 🟢 Implementare `ai/cache.py`

### 5.6 Evaluator (orchestratore)
- [ ] 🔴 Test `test_evaluator.py` → `evaluate_strategy()` chiama context builder + prompt builder + modello
- [ ] 🔴 Test → cache hit → restituisce senza chiamare il modello
- [ ] 🔴 Test → chiama `_call_model_with_fallback()` poi `parse_eval_result()`
- [ ] 🔴 Test → persiste via `EvalCache.save_eval()` dopo parsing riuscito
- [ ] 🔴 Test → `EvalParseError` → logga su Supabase, restituisce `None`
- [ ] 🔴 Test → `AllModelsUnavailableError` → logga su Supabase, restituisce `None`
- [ ] 🔴 Test → `evaluate_all()` con `asyncio.Semaphore` per concorrenza limitata
- [ ] 🟢 Implementare `ai/evaluator.py`
- [ ] 🔵 Refactor: `MAX_CONCURRENT_EVALS` da `Settings`

### 5.7 API Endpoint
- [ ] 🔴 Test `test_api_eval.py` → `GET /api/strategies/:id/eval` restituisce cache se presente
- [ ] 🔴 Test → se non in cache → `BackgroundTasks` + `202 Accepted`
- [ ] 🔴 Test → `POST /api/strategies/:id/eval/refresh` forza nuova valutazione
- [ ] 🔴 Test → endpoint protetti → 401 senza token
- [ ] 🟢 Implementare `api/eval.py` + registrare in `main.py`

### 5.8 Integrazione in Pipeline
- [ ] 🔴 Test `test_pipeline_ai.py` → `run_pipeline()` chiama `evaluate_all()` sulle top-N strategie
- [ ] 🔴 Test → `verdict=DEMOTE` → strategia disattivata automaticamente
- [ ] 🔴 Test → `verdict=PROMOTE` + `score ≥ soglia` → candidata per `ExecutionEngine`
- [ ] 🔴 Test → errori AI non bloccano la pipeline
- [ ] 🟢 Aggiornare `run_pipeline.py` con passo AI Evaluator
- [ ] 🟢 Broadcast WS `eval_complete` con `strategy_id`, `verdict`, `score`

### 5.9 Integration Tests
- [ ] 🔴 Test `test_ai_integration.py` → happy path: buone metriche → `PROMOTE` score ≥ 0.7
- [ ] 🔴 Test → fallback: primario timeout → fallback risponde → `model_used=fallback`
- [ ] 🔴 Test → cache hit: seconda chiamata entro TTL non chiama il modello
- [ ] 🔴 Test → JSON malformato → `EvalParseError` loggato → pipeline non interrotta
- [ ] 🔴 Test → tutti i modelli down → `AllModelsUnavailableError` → `run_pipeline()` completa senza eval

---

## ⚫ Fase 6 — Hardening & Deploy

> Architettura target: **Supabase Cloud** + **VPS Linux** con Docker + Nginx + HTTPS.

### 6.0 Supabase — Produzione
- [ ] Creare progetto Supabase Cloud (region EU)
- [ ] Eseguire 4 migration SQL + seed.sql
- [ ] Verificare schema tabelle
- [ ] Copiare `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`

#### RLS
- [ ] Abilitare RLS su `strategies`, `trades`, `operation_logs`, `ohlcv_cache`
- [ ] Policy `SELECT/INSERT/UPDATE/DELETE` solo per `auth.uid() = user_id`
- [ ] Testare policy con `SET LOCAL role = anon`

#### Realtime
- [ ] Abilitare Realtime su `operation_logs`
- [ ] Verificare eventi `INSERT` trasmessi correttamente

#### Auth
- [ ] Disabilitare registrazione pubblica
- [ ] Creare utente admin manualmente
- [ ] Configurare JWT expiry in linea con backend

### 6.1 Docker — Hardening Immagini

#### Backend multi-stage
- [ ] Stage `builder`: `python:3.12-slim`, virtualenv isolato
- [ ] Stage `runtime`: immagine pulita, solo virtualenv + codice
- [ ] Utente non-root `appuser`
- [ ] Nessun `pip`, `gcc`, cache `apt`, `.pyc` nell'immagine finale
- [ ] `HEALTHCHECK`: `curl -f http://localhost:8000/health || exit 1`
- [ ] `.dockerignore`: `__pycache__`, `*.pyc`, `.env`, `tests/`, `.git/`

#### Frontend multi-stage
- [ ] Stage `builder`: `node:20-alpine`, `npm ci` + `ng build --configuration production`
- [ ] Stage `runtime`: `nginx:alpine`, solo `dist/`
- [ ] `nginx.conf`: SPA fallback, cache headers, gzip

### 6.2 docker-compose Produzione
- [ ] `docker-compose.prod.yml`: backend + frontend + nginx, nessun port binding diretto
- [ ] Network `internal` bridge isolata
- [ ] Volume named per certificati SSL (`certbot_certs`)
- [ ] Logging `json-file` con `max-size: 10m`, `max-file: 3`
- [ ] `.env.prod.example` con tutti i nomi variabili (senza valori)

### 6.3 Nginx — Reverse Proxy & HTTPS
- [ ] Redirect 301 HTTP → HTTPS
- [ ] `location /api/` → proxy_pass `backend:8000`
- [ ] `location /ws/` → proxy_pass con upgrade WebSocket
- [ ] `location /` → proxy_pass `frontend:80`
- [ ] Headers sicurezza: `X-Frame-Options`, `X-Content-Type-Options`, `HSTS`, `CSP`
- [ ] Rate limiting su `/api/auth/` (5 req/min per IP)
- [ ] `ssl-params.conf` con TLS 1.2+, no SSLv3

#### Certbot / Let's Encrypt
- [ ] Servizio `certbot` in `docker-compose.prod.yml`
- [ ] `scripts/init-letsencrypt.sh` (staging → production)
- [ ] `scripts/renew-certs.sh` (nginx reload, no downtime)

### 6.4 VPS — Provisioning
- [ ] `[provider]` VPS: Ubuntu 24.04 LTS, 2 vCPU / 4 GB RAM / 40 GB SSD
- [ ] `[provider]` SSH key, firewall porte 22/80/443, DNS record A
- [ ] Utente non-root `deploy` con sudo
- [ ] Disabilitare login SSH root
- [ ] UFW: `allow 22,80,443/tcp`
- [ ] Installare Docker + Docker Compose plugin
- [ ] `unattended-upgrades` per aggiornamenti sicurezza automatici

### 6.5 Logging Strutturato
- [ ] Installare `python-json-logger`
- [ ] `core/logging.py` con `setup_logging()` e `JsonFormatter`
- [ ] Chiamare `setup_logging()` nel lifespan di `main.py`
- [ ] Sostituire tutti i `print()` con `logger = logging.getLogger(__name__)`
- [ ] Middleware FastAPI con `request_id` (UUID) in ogni log

### 6.6 Error Handling Globale
- [ ] `core/exceptions.py`: `SynthTradeError`, `RiskViolationError`, `ModelUnavailableError`, `OrderExecutionError`
- [ ] Handler globale `Exception` → `{"error": "internal_server_error", "request_id": "..."}`
- [ ] Handler `HTTPException` con `request_id`
- [ ] Handler `RequestValidationError` con errori Pydantic leggibili
- [ ] Nessun stack trace esposto in produzione

### 6.7 Deploy & Script di Rilascio
- [ ] `scripts/deploy.sh`: git pull → build → up -d → image prune
- [ ] `scripts/rollback.sh`: riavvia immagine tag precedente
- [ ] Cron job rinnovo SSL: `0 3 * * *`
- [ ] Backup DB: verificare retention Supabase Cloud

### 6.8 Smoke Test Post-Deploy
- [ ] `scripts/smoke_test.sh`:
  - `GET /health` → 200 `{"status": "ok"}`
  - `POST /api/auth/login` → JWT token
  - `GET /api/strategies` con token → 200
  - `GET /api/dashboard/stats` con token → 200
  - WebSocket `wss://` → heartbeat ricevuto
  - Certificato SSL valido
- [ ] `smoke_test.sh` integrato in `deploy.sh` con rollback automatico su fallimento

### 6.9 Checklist Pre-Go-Live
- [ ] Nessuna variabile `.env` hardcodata (`grep -r "SECRET\|PASSWORD\|API_KEY"`)
- [ ] `DEBUG=False`, `ENVIRONMENT=production`
- [ ] CORS: `allow_origins` lista esplicita, no `*`
- [ ] Tutte le tabelle Supabase con RLS abilitato
- [ ] Nessun endpoint pubblico senza autenticazione
- [ ] `ng build --configuration production` senza warning critici
- [ ] `docker compose -f docker-compose.prod.yml config` senza errori
- [ ] Smoke test completato con tutti i check verdi
