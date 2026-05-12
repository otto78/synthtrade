# Handoff Protocol — SynthTrade

---

## 🔄 Ultimo Handoff

### Da: Cline → prossima sessione

**Data:** 2026-05-12

**Contesto:** Completato il Fix Allucinazioni (v1.2.0). `generate_for_request()` ora usa backtest reale su dati Binance invece di random.uniform(). TUTTI i 21 test PASS.

---

### ✅ FIX COMPLETATO (sessione 2026-05-12)

**Fix Allucinazioni (TASK-FIX-001 → 011)** — PRIORITÀ ASSOLUTA

**Cosa è stato fatto:**
- `strategy_generator.py` riscritto: rimosso `import random`, `random.uniform()`, `random.choice()`, `random.shuffle()`
- `generate_for_request()` ora: fetch OHLCV da Binance (90gg) → backtest reale → compute_score → filtraggio
- `StrategyParams` aggiornato: `ai_score` → `score` (range [0,1]), nuovi campi backtest (backtest_pnl, win_rate, sharpe, drawdown, trades, data_source)
- Nomi deterministici (template + pair), rimossi nomi casuali tipo "Il Seguace"
- `pipeline.py`: salva `backtest` completo nel DB, WS progress events, gestione lista vuota
- `test_random_proof.py`: ora test PASS (determinismo verificato, score range [0,1])
- Nuovo `test_e2e_pipeline.py`: test E2E con mock OHLCV (21/21 test PASS)

---

### 📊 Stato Attuale


**Fase corrente:** Fase 6 — Hardening & Deploy

**Completato:**
- ✅ Fase 0 — Setup & Infrastruttura
- ✅ Fase 1 — Core Engine
- ✅ Fase 2 — Backend API
- ✅ Fase 3 — Frontend Angular (116 test)
- ✅ Fase 4 — Execution Engine (49 test)
- ✅ **Fase 5 — AI Evaluator** (51 test)
  - 5.0 Config + Schemas
  - 5.1 ContextBuilder (7) · 5.2 PromptBuilder (6) · 5.3 ModelClient (7)
  - 5.4 EvalParser (8) · 5.5 EvalCache (4) · 5.6 Evaluator (7)
  - 5.7 API eval endpoint (4) · 5.8 Pipeline AI (4) · 5.9 Integration (5)

**Totale test:** 214 backend + 116 frontend = 330

**In corso:** Fase 6 — Hardening & Deploy

**Fase 4 dettagliata:** lista task completa aggiunta in TASKS.md (4.0→4.6)
- Struttura: `backend/app/execution/` + `backend/app/scheduler/`
- Nuovi schemi: `Signal`, `OrderRequest`, `OrderResult`, `RiskCheckResult`, `PositionSnapshot`
- `SignalResolverProtocol` pluggabile via `importlib`
- Scheduler APScheduler con job: pipeline, monitor_positions, heartbeat
- 4 integration test scenari: pipeline completa, stop loss, risk reject, drawdown

**Fase 6 dettagliata:** lista task completa aggiunta in TASKS.md (6.0→6.9)
- Architettura: Supabase Cloud + VPS Linux + Docker + Nginx + HTTPS
- Docker multi-stage: backend python:3.12-slim, frontend node:20-alpine + nginx:alpine
- Nginx: reverse proxy, WebSocket upgrade, security headers, rate limiting login
- Certbot/Let's Encrypt con rinnovo automatico senza downtime
- Logging strutturato JSON con `request_id` middleware
- Error handling globale con eccezioni custom
- `scripts/deploy.sh` + `scripts/rollback.sh` + `scripts/smoke_test.sh`
- Checklist pre-go-live: RLS, CORS, no hardcoded secrets, bundle size
- Struttura: `backend/app/ai/` con 7 moduli
- `EvalResult` con verdict PROMOTE/HOLD/DEMOTE, score, confidence, model_used
- `ModelClient` con retry backoff + fallback primario/secondario
- `EvalCache` su Supabase con TTL configurabile
- `evaluate_all()` con `asyncio.Semaphore` per concorrenza limitata
- Broadcast WS `eval_complete` + integrazione in `run_pipeline()`

---

### 📁 Direttive LOOM da leggere prima di iniziare la Fase 3

```
loom/directives/frontend-angular.md    ← regole Angular 17+, pattern HTTP/WS, test Jest
loom/directives/scss-tokens.md         ← tutti i design token (colori, font, spacing)
loom/directives/component-patterns.md ← interfacce TS, pattern componenti, checklist pagine
```

---

### 🎯 Prossimi Step (in ordine)

1. **3.0 Bootstrap** — `ng new`, rimuovere Karma, installare Jest, environments, proxy, eslint
2. **3.1 Design Tokens** — `_variables.scss`, `_mixins.scss`, `_reset.scss`, `_animations.scss`
3. **3.2 Modelli** — interfacce TypeScript per Strategy, Trade, Dashboard, Log, WsMessage
4. **3.3 Interceptors & Guards** — TDD su auth interceptor, error interceptor, auth guard, no-auth guard
5. **3.4 Services** — TDD su TokenStorage, Auth, Strategy, Dashboard, Log, WebSocket
6. **3.5 Shared** — TDD su StatCard, BadgeStatus, PriceTicker, ConfirmDialog, pipes
7. **3.6 Layout** — Sidebar, Topbar, AppShell
8. **3.7 Routing** — lazy loading, guards
9. **3.8 Pagine** — Login, Dashboard, Strategies, ActiveTrade, Logs
10. **3.9 E2E** — Playwright

---

### 📝 Note Importanti

- Frontend va in `synthtrade/frontend/synthtrade-ui/` (dentro la struttura monorepo)
- Backend gira su `localhost:8008` — usare proxy Angular per dev (porta 4208)
- Design system completo in `PROJECT.md` e nelle direttive LOOM
- `PAPER_TRADING=true` default — non toccare fino alla Fase 6
- Comando test backend: `set PYTHONPATH=synthtrade\backend && .venv\Scripts\pytest`

---

**Ultima modifica:** 2025-01-15 — Amazon Q
