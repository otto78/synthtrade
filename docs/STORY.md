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
- [ ] `indicators.py` (EMA, RSI, Bollinger + signal functions)
- [ ] `strategy_generator.py` (prodotto cartesiano parametri)
- [ ] `backtester.py` (simulazione OHLCV con fee/slippage)
- [ ] `ranker.py` (score composito con filtri hard)
- [ ] `market_data.py` (fetch Binance + cache Supabase)
- [ ] `run_pipeline.py` (pipeline batch completa)

### v0.3.0 — Backend API
- [ ] Auth JWT
- [ ] API strategies, dashboard, logs
- [ ] WebSocket live feed

### v0.4.0 — Frontend Angular
- [ ] Dark terminal UI completa
- [ ] Tutte le pagine (Login, Dashboard, Strategies, ActiveTrade, Logs)

### v0.5.0 — Execution Engine + AI
- [ ] `risk_manager.py`
- [ ] `execution_engine.py` con APScheduler
- [ ] `ai_evaluator.py` cascade OpenRouter

### v1.0.0 — Hardening & Deploy
- [ ] Supabase RLS
- [ ] Nginx + HTTPS
- [ ] Smoke test post-deploy

---

## 📊 Metriche

### Progresso Generale

- **Fase completata:** 0 / 6 (Fase 1 in corso)
- **Task completati:** 17 (Fase 0 intera + indicators)
- **Test passati:** 18 (1 health + 17 indicators)
- **Test coverage:** ~15%

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
