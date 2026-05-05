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

### v0.4.0 — Frontend Angular
- [ ] Dark terminal UI completa
- [ ] Tutte le pagine (Login, Dashboard, Strategies, ActiveTrade, Logs)

### v0.5.0 — Execution Engine + AI
- [ ] `execution/schemas.py` (Signal, OrderRequest, OrderResult, RiskCheckResult, PositionSnapshot)
- [ ] `execution/risk_manager.py` (RiskConfig, validate_signal, SL/TP calc)
- [ ] `execution/order_tracker.py` (open/close/get positions, unrealized P&L)
- [ ] `execution/signal_resolver.py` (SignalResolverProtocol + DefaultSignalResolver)
- [ ] `execution/execution_engine.py` (process_signal, check_exit_conditions)
- [ ] `scheduler/jobs.py` (APScheduler: pipeline, monitor, heartbeat)

### v0.6.0 — AI Evaluator
- [ ] `ai/schemas.py` (MarketContext, StrategyContext, EvalPromptInput, EvalResult, ModelResponse)
- [ ] `ai/context_builder.py` (build_market_context, detect_market_regime)
- [ ] `ai/prompt_builder.py` (build_prompt, build_system_prompt, token budget)
- [ ] `ai/model_client.py` (httpx, retry backoff, fallback, custom errors)
- [ ] `ai/eval_parser.py` (parse_eval_result, EvalParseError, markdown strip)
- [ ] `ai/cache.py` (get_cached_eval, save_eval, TTL Supabase)
- [ ] `ai/evaluator.py` (evaluate_strategy, evaluate_all con Semaphore)
- [ ] `api/eval.py` (GET eval, POST refresh, BackgroundTasks)
- [ ] Integrazione in `run_pipeline.py` (PROMOTE/DEMOTE/HOLD logic)
- [ ] Broadcast WS `eval_complete`

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

- **Task completati:** 71 (Fase 0+1+2 + 3.0/3.1/3.2/3.3/3.4)
- **Test passati:** 114 backend + 45 frontend
- **Test coverage:** ~80% backend

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

**Ultima modifica:** 2025-01-15 — Amazon Q
