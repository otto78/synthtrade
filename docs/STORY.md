# Project Story — SynthTrade

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
- [ ] Fase 5 AI Evaluator

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

- **Task completati:** 361 (Fase 0–2.B complete, Loom migration)
- **Test passati:** 214 backend + 116 frontend + 21 nuovi = 351 totali
- **Test coverage:** ~82% backend, ~85% frontend core/shared

---

## 📝 Decisioni Architetturali

**2026-05-06 — Implementazione Exchange Adapter e Pipeline Intelligente**
- Problema: Necessità di interfacciarsi con Binance e generare strategie guidate dall'utente.
- Soluzione: Implementato `BinanceExchangeAdapter` con CCXT e `StrategyRequest` con arricchimento AI.
- Beneficio: Trading reale/paper sicuro e UX migliorata per la generazione di strategie.

**2026-05-06 — Integrazione Framework Loom**
- Problema: Necessità di un workflow standardizzato per task management e TDD.
- Soluzione: Configurato framework Loom (DOE Architecture) e migrato tutti i task esistenti in `docs/TASKS.md` al nuovo formato `### TASK-XXX`.
- Beneficio: Piena compatibilità con gli script di automazione `loom/scripts/task.py` e tracciamento rigoroso dello stato.

**2026-05-05 — AI cascade con lista modelli configurabile**
- Problema: lista modelli free OpenRouter cambia spesso
- Soluzione: `AI_CASCADE_MODELS` come stringa CSV in `.env`, property `ai_cascade_models_list` in `Settings`
- Beneficio: cambio modelli senza deploy, fallback Claude Haiku solo se tutti i free falliscono

**2026-05-05 — run_pipeline ora async**
- Problema: AI eval richiede `await`, pipeline era sync
- Soluzione: `run_pipeline` diventa `async def`, scheduler usa `await run_pipeline()`
- Beneficio: nessun thread blocking, compatibile con APScheduler AsyncIO

---

## 📝 Decisioni Architetturali

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

**Ultima modifica:** 2026-05-06 — Trae (Loom Integration)