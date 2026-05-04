# Handoff Protocol — SynthTrade

---

## 🔄 Ultimo Handoff

### Da: Amazon Q → A: prossimo agente / sessione

**Data:** 2025-01-15

**Contesto:** Fase 0 completata. Il backend FastAPI è bootstrappato, il test `/health` è verde, le migration SQL sono pronte.

---

### 📊 Stato Attuale

**Fase corrente:** Fase 1 — Core Engine (da iniziare)

**Prossimo task:** `indicators.py` — TDD su EMA, RSI, Bollinger + signal functions

**Ultimo test:** `tests/test_main.py::test_health` — ✅ PASSED

**Virtualenv:** `.venv/` nella root del workspace (Python 3.12)

---

### 📁 File Creati in Fase 0

```
.gitignore
README.md
docker-compose.yml
docs/TASKS.md, STORY.md, CHANGELOG.md, BACKLOG.md, HANDOFF.md
synthtrade/backend/
  app/main.py, config.py
  app/db/supabase_client.py
  tests/conftest.py, test_main.py
  requirements.txt, pytest.ini, .env.example, Dockerfile
synthtrade/supabase/
  migrations/ (4 SQL)
  seed.sql
```

---

### 🎯 Prossimi Step

1. **Fase 1 — `indicators.py`**
   - Scrivere `tests/unit/test_indicators.py` (🔴 Red)
   - Implementare `app/core/indicators.py` (🟢 Green)
   - Test: EMA, RSI, Bollinger, signal functions, no look-ahead

2. **Fase 1 — `strategy_generator.py`**
   - Test: almeno 200 varianti, ID deterministico, no duplicati
   - Implementare `app/core/strategy_generator.py`

3. **Fase 1 — `backtester.py`**
   - Test: PnL corretto, fee applicate, equity_curve lunghezza, no look-ahead
   - Implementare `app/core/backtester.py`

---

### 📝 Note Importanti

- Eseguire i test con: `set PYTHONPATH=synthtrade\backend && .venv\Scripts\pytest`
- Il file `.env` non esiste ancora — copiare da `.env.example` e compilare
- Supabase locale non ancora avviato — serve `supabase start` in `synthtrade/supabase/`
- `PAPER_TRADING=true` è il default — non modificare fino alla Fase 6

---

**Ultima modifica:** 2025-01-15 — Amazon Q
