# Handoff Protocol — SynthTrade

---

## 🔄 Ultimo Handoff

### Da: Cline → prossima sessione

**Data:** 2026-05-14

**Contesto:** Completata la **Fase A dell'Epica Execution (EPIC-400)**. Le strategie ora possono essere attivate operativamente con esecuzione di ordini reali e allocazione del capitale su Binance.

---

### ✅ FASE COMPLETATA: Execution Phase A (2026-05-14)

**Cosa è stato fatto:**
- Implementato `execution/capital_allocator.py` per il calcolo delle quote iniziali.
- Esteso `POST /api/strategies/{id}/activate` per integrare l'esecuzione degli ordini tramite `ccxt`.
- Aggiunto controllo `insufficient_funds` (TASK-403) con rollback dello stato.
- Allineato lo schema DB (Migration 008 e 009) per tracciare `activated_at` e `initial_capital_usdt`.

---

### 📊 Stato Attuale


**Fase corrente:** Fase 6 — Hardening & Deploy

**Completato:**
- ✅ Fase 0 — Setup & Infrastruttura
- ✅ Fase 1 — Core Engine
- ✅ Fase 2 — Backend API
- ✅ Fase 3 — Frontend Angular (116 test)
- ✅ Fase 4 — Execution Engine (Phase A Ready)
- ✅ **Fase 5 — AI Evaluator** (51 test)

**Totale test:** 230 backend + 116 frontend = 346

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
