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
- [ ] 🔴 Test `test_generator.py`
- [ ] 🟢 Implementare `strategy_generator.py`
- [ ] 🔵 Refactor: `TEMPLATES` configurabile via JSON

### Backtester
- [ ] 🔴 Test `test_backtester.py`
- [ ] 🟢 Implementare `backtester.py`
- [ ] 🔵 Refactor: `StopLossManager` separato

### Ranker
- [ ] 🔴 Test `test_ranker.py`
- [ ] 🟢 Implementare `ranker.py`
- [ ] 🔵 Refactor: `RankConfig` da `.env`

### Market Data + Cache Supabase
- [ ] 🔴 Test `test_market_data.py`
- [ ] 🟢 Implementare `market_data.py`
- [ ] 🔵 Refactor: separare `exchange.py`

### Pipeline Batch
- [ ] 🔴 Test `test_pipeline.py` (integration)
- [ ] 🟢 Implementare `run_pipeline.py`
- [ ] 🔵 Refactor: progress logging + gestione eccezioni

---

## 🟠 Fase 2 — Backend API

### Auth
- [ ] 🔴 Test `test_api_auth.py`
- [ ] 🟢 Implementare `api/auth.py` + JWT
- [ ] 🟢 Implementare `dependencies.py` → `get_current_user`
- [ ] 🔵 Refactor: `core/auth_utils.py`

### Strategies API
- [ ] 🔴 Test `test_api_strategies.py`
- [ ] 🟢 Implementare `api/strategies.py`
- [ ] 🔵 Refactor: `StrategyRepository`

### Dashboard API
- [ ] 🔴 Test `test_api_dashboard.py`
- [ ] 🟢 Implementare `api/dashboard.py`
- [ ] 🔵 Refactor: cache balance 30s

### Logs API
- [ ] 🔴 Test `test_api_logs.py`
- [ ] 🟢 Implementare `api/logs.py`
- [ ] 🔵 Refactor: filtri aggiuntivi

### WebSocket
- [ ] 🔴 Test `test_ws.py`
- [ ] 🟢 Implementare `api/ws.py`
- [ ] 🔵 Refactor: broadcast per tipo

---

## 🟢 Fase 3 — Frontend Angular

- [ ] Bootstrap Angular app con Jest
- [ ] Design tokens `_variables.scss`
- [ ] Core services (Auth, Strategy, Dashboard, Log, WS)
- [ ] Componenti shared (StatCard, BadgeStatus, PriceTicker, pipes)
- [ ] Layout (Sidebar, Topbar, AppShell)
- [ ] Pagine: Login, Dashboard, Strategies, ActiveTrade, Logs

---

## 🔴 Fase 4 — Execution Engine

- [ ] 🔴 Test `test_risk_manager.py`
- [ ] 🟢 Implementare `risk_manager.py`
- [ ] 🔴 Test `test_execution_engine.py`
- [ ] 🟢 Implementare `execution_engine.py`
- [ ] 🟢 APScheduler in `scheduler/jobs.py`
- [ ] 🔵 Refactor: `SignalResolver` pluggabile

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
