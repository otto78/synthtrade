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
- [ ] 🔴 Test `token-storage.service.spec.ts` (setTokens, getAccessToken, clear, isTokenExpired)
- [ ] 🟢 Implementare `core/services/token-storage.service.ts`
- [ ] 🔴 Test `auth.service.spec.ts` (login, logout, refreshToken, isAuthenticated)
- [ ] 🟢 Implementare `core/services/auth.service.ts`
- [ ] 🔴 Test `strategy.service.spec.ts` (getStrategies, getStrategy, activate, deactivate, delete)
- [ ] 🟢 Implementare `core/services/strategy.service.ts`
- [ ] 🔴 Test `dashboard.service.spec.ts` (getStats, getBalanceHistory, getPipelineStatus, cache 30s)
- [ ] 🟢 Implementare `core/services/dashboard.service.ts`
- [ ] 🔵 Refactor: cache con `shareReplay(1)` + invalidazione dopo 30s
- [ ] 🔴 Test `log.service.spec.ts` (getLogs con filtri e paginazione)
- [ ] 🟢 Implementare `core/services/log.service.ts`
- [ ] 🔴 Test `ws.service.spec.ts` (connect, messages$, disconnect, reconnect backoff)
- [ ] 🟢 Implementare `core/services/ws.service.ts`
- [ ] 🔵 Refactor: `on<T>(type)` helper tipizzato

### 3.5 Shared — Componenti Atomici
- [ ] 🔴 Test `stat-card.component.spec.ts` (label, value, delta, skeleton)
- [ ] 🟢 Implementare `shared/components/stat-card/`
- [ ] 🔴 Test `badge-status.component.spec.ts` (testo e classe CSS per ogni status)
- [ ] 🟢 Implementare `shared/components/badge-status/`
- [ ] 🔴 Test `price-ticker.component.spec.ts` (decimali, flash-up, flash-down, rimozione classe)
- [ ] 🟢 Implementare `shared/components/price-ticker/`
- [ ] 🔴 Test `confirm-dialog.component.spec.ts` (confirmed, cancelled, Escape)
- [ ] 🟢 Implementare `shared/components/confirm-dialog/`
- [ ] 🟢 Implementare `shared/components/empty-state/`
- [ ] 🔴 Test `relative-time.pipe.spec.ts`
- [ ] 🟢 Implementare `shared/pipes/relative-time.pipe.ts`
- [ ] 🔴 Test `format-number.pipe.spec.ts` (K/M suffisso)
- [ ] 🟢 Implementare `shared/pipes/format-number.pipe.ts`
- [ ] 🔴 Test `signed-number.pipe.spec.ts`
- [ ] 🟢 Implementare `shared/pipes/signed-number.pipe.ts`

### 3.6 Layout Shell
- [ ] 🔴 Test `sidebar.component.spec.ts` (voce attiva, toggle collapsed)
- [ ] 🟢 Implementare `layout/sidebar/` (Dashboard, Strategies, Active Trade, Logs)
- [ ] 🔴 Test `topbar.component.spec.ts` (username, logout)
- [ ] 🟢 Implementare `layout/topbar/`
- [ ] 🟢 Implementare `layout/app-shell/`
- [ ] 🔵 Refactor: stato collapsed persistito in localStorage

### 3.7 Routing
- [ ] Creare `app.routes.ts` con lazy loading (login, dashboard, strategies, active-trade, logs)
- [ ] 🔴 Test routing: `''` → `/dashboard`, `**` → `/dashboard`
- [ ] 🔴 Test: `authGuard` redirige a `/login` senza token

### 3.8 Pagine

#### LoginPage
- [ ] 🔴 Test `login.component.spec.ts` (form invalido, submit, 401, redirect, spinner)
- [ ] 🟢 Implementare `pages/login/login.component.ts`
- [ ] 🔵 Refactor: estrarre `LoginFormComponent`

#### DashboardPage
- [ ] 🔴 Test `dashboard.component.spec.ts` (getStats, 4 StatCard, WS stats_update, PipelineStatus)
- [ ] 🟢 Implementare `pages/dashboard/dashboard.component.ts`
- [ ] 🟢 Aggiungere grafico balance history
- [ ] 🔵 Refactor: `DashboardStore` con Angular Signals

#### StrategiesPage
- [ ] 🔴 Test `strategies.component.spec.ts` (list, activate, delete+confirm, filtro, empty state)
- [ ] 🟢 Implementare `pages/strategies/strategies.component.ts`
- [ ] 🔵 Refactor: `StrategyListComponent` + `StrategyRowComponent`

#### ActiveTradePage
- [ ] 🔴 Test `active-trade.component.spec.ts` (empty state, render trade, WS price_update, P&L classi)
- [ ] 🟢 Implementare `pages/active-trade/active-trade.component.ts`

#### LogsPage
- [ ] 🔴 Test `logs.component.spec.ts` (getLogs, filtro level, paginazione, riga, WS new_log)
- [ ] 🟢 Implementare `pages/logs/logs.component.ts`
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
- [ ] Aggiungere in `config.py`: `MAX_CONCURRENT_POSITIONS`, `MAX_EXPOSURE_PER_SYMBOL_PCT`, `MAX_DRAWDOWN_PCT`, `DEFAULT_POSITION_SIZE_PCT`, `DEFAULT_STOP_LOSS_PCT`, `DEFAULT_TAKE_PROFIT_PCT`, `SCHEDULER_PIPELINE_INTERVAL_MIN`
- [ ] Creare `execution/schemas.py`: `Signal`, `OrderRequest`, `OrderResult`, `RiskCheckResult`, `PositionSnapshot`

### 4.1 RiskManager
- [ ] 🔴 Test `test_risk_manager.py` → `calculate_position_size()` basata su `DEFAULT_POSITION_SIZE_PCT`
- [ ] 🔴 Test → non supera `MAX_EXPOSURE_PER_SYMBOL_PCT`
- [ ] 🔴 Test → `check_max_positions()` → `approved=False` se ≥ `MAX_CONCURRENT_POSITIONS`
- [ ] 🔴 Test → `check_max_positions()` → `approved=True` se sotto limite
- [ ] 🔴 Test → `check_drawdown()` → `approved=False` se drawdown > `MAX_DRAWDOWN_PCT`
- [ ] 🔴 Test → `calculate_stop_loss_price()` e `calculate_take_profit_price()` per LONG e SHORT
- [ ] 🔴 Test → `validate_signal()` aggrega tutti i check con `reason` descrittiva
- [ ] 🟢 Implementare `execution/risk_manager.py`
- [ ] 🔵 Refactor: `RiskConfig` dataclass iniettabile nei test

### 4.2 OrderTracker
- [ ] 🔴 Test `test_order_tracker.py` → `open_position()` persiste su Supabase con stato `OPEN`
- [ ] 🔴 Test → `close_position()` aggiorna con `closed_at`, `exit_price`, `pnl`, stato `CLOSED`
- [ ] 🔴 Test → `get_open_positions()` restituisce solo trade `OPEN`
- [ ] 🔴 Test → `get_open_positions(symbol=...)` filtra per symbol
- [ ] 🔴 Test → `update_unrealized_pnl()` calcola P&L per LONG e SHORT
- [ ] 🟢 Implementare `execution/order_tracker.py`

### 4.3 SignalResolver
- [ ] 🔴 Test `test_signal_resolver.py` → `resolve()` filtra per `strength ≥ threshold`
- [ ] 🔴 Test → per stesso symbol, restituisce solo signal con strength maggiore
- [ ] 🔴 Test → filtra signal con strategia già in posizione aperta
- [ ] 🔴 Test → lista vuota se nessun signal supera i filtri
- [ ] 🟢 Implementare `execution/signal_resolver.py` con `SignalResolverProtocol` + `DefaultSignalResolver`
- [ ] 🔵 Refactor: pluggabile via `config.py` con `importlib`

### 4.4 ExecutionEngine
- [ ] 🔴 Test `test_execution_engine.py` → `process_signal()` chiama `RiskManager.validate_signal()`
- [ ] 🔴 Test → `approved=False` → nessun ordine, log su Supabase
- [ ] 🔴 Test → approvato → costruisce `OrderRequest` con SL/TP da RiskManager
- [ ] 🔴 Test → chiama `exchange.place_order()` con `OrderRequest` corretto
- [ ] 🔴 Test → `FILLED` → chiama `OrderTracker.open_position()` + log
- [ ] 🔴 Test → `REJECTED`/`ERROR` → log senza aprire posizioni
- [ ] 🔴 Test → `check_exit_conditions()` → `True` se prezzo raggiunge SL o TP
- [ ] 🔴 Test → `close_position_if_needed()` chiama `exchange.close_order()` + `OrderTracker.close_position()`
- [ ] 🔴 Test → eccezione exchange catturata e loggata senza crash
- [ ] 🟢 Implementare `execution/execution_engine.py`
- [ ] 🔵 Refactor: `SignalResolver` iniettato nel costruttore

### 4.5 Scheduler
- [ ] 🔴 Test `test_scheduler.py` → `run_pipeline_job` chiama `run_pipeline()` + log
- [ ] 🔴 Test → `monitor_positions_job` chiama `close_position_if_needed()` per ogni posizione
- [ ] 🔴 Test → `heartbeat_job` invia WS `heartbeat` con timestamp e stato
- [ ] 🔴 Test → eccezione in job catturata senza fermare lo scheduler
- [ ] 🟢 Implementare `scheduler/jobs.py` con `AsyncIOScheduler`
- [ ] 🟢 Aggiungere `GET /api/scheduler/status`
- [ ] 🟢 Registrare scheduler nel lifespan di `main.py`
- [ ] 🔵 Refactor: intervalli configurabili da `Settings`

### 4.6 Integration Tests
- [ ] 🔴 Test `test_execution_integration.py` → pipeline completa: Signal → trade aperto su Supabase
- [ ] 🔴 Test → scenario stop loss: posizione aperta → SL raggiunto → posizione chiusa
- [ ] 🔴 Test → scenario risk reject: portfolio al limite → nessun ordine → log con reason
- [ ] 🔴 Test → scenario drawdown: drawdown oltre soglia → tutti i signal rigettati

---

## 🟣 Fase 5 — AI Evaluator

- [ ] Config cascade in `config.py`
- [ ] Schema `EvalResult` Pydantic
- [ ] 🔴 Test `_call_model` (unit)
- [ ] 🟢 Implementare `_call_model()`
- [ ] 🔴 Test `evaluate_strategy` (cascade)
- [ ] 🟢 Implementare `evaluate_strategy()`
- [ ] 🔴 Test `EvalResult` validation
- [ ] 🔴 Test `build_market_context`
- [ ] 🟢 Implementare `build_market_context()`
- [ ] 🔴 Test pipeline AI integration
- [ ] 🟢 Integrare in `run_pipeline.py`
- [ ] 🔵 Refactor: backoff esponenziale

---

## ⚫ Fase 6 — Hardening & Deploy

- [ ] Error handling globale
- [ ] Logging strutturato JSON
- [ ] Dockerfile multi-stage ottimizzato
- [ ] Nginx + HTTPS
- [ ] Supabase RLS su tutte le tabelle
- [ ] Supabase Realtime su `operation_logs`
- [ ] Smoke test post-deploy
