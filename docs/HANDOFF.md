# Handoff Protocol — SynthTrade

---

## 🔄 Ultimo Handoff

### Da: Amazon Q → A: prossima sessione

**Data:** 2025-01-15

**Contesto:** Fase 0 completata + `indicators.py` (Fase 1) completato. Repo Git inizializzata con primo commit `9508d8c`.

---

### 📊 Stato Attuale

**Fase corrente:** Fase 1 — Core Engine (in corso)

**Completato oggi:**
- ✅ Fase 0 intera (monorepo, FastAPI, Supabase migrations, Docker)
- ✅ `indicators.py` — EMA, RSI, Bollinger + 3 signal functions (17/17 test verdi)

**Prossimo task:** `strategy_generator.py` — TDD prodotto cartesiano parametri

**Ultimo commit:** `9508d8c` — "feat: Fase 0 completa + indicators.py (Fase 1 iniziata)"

**Test totali:** 18 (1 health + 17 indicators) — tutti ✅

**Virtualenv:** `.venv/` nella root del workspace (Python 3.12)

---

### 📁 File rilevanti Fase 1 (in corso)

```
synthtrade/backend/app/core/indicators.py        ✅ completo
synthtrade/backend/tests/unit/test_indicators.py ✅ 17 test
```

**Da creare:**
```
synthtrade/backend/app/core/strategy_generator.py
synthtrade/backend/app/core/backtester.py
synthtrade/backend/app/core/ranker.py
synthtrade/backend/app/core/market_data.py
synthtrade/backend/app/core/run_pipeline.py
synthtrade/backend/tests/unit/test_generator.py
synthtrade/backend/tests/unit/test_backtester.py
synthtrade/backend/tests/unit/test_ranker.py
synthtrade/backend/tests/unit/test_market_data.py
synthtrade/backend/tests/integration/test_pipeline.py
```

---

### 🎯 Prossimi Step

1. **`strategy_generator.py`** — TDD
   - Test: ≥200 varianti, ID deterministico, no duplicati su 500
   - Implementare con prodotto cartesiano `TEMPLATES`

2. **`backtester.py`** — TDD
   - Test: PnL corretto, fee applicate, equity_curve lunghezza, no look-ahead
   - Implementare con fee 0.1% + slippage 0.07%

3. **`ranker.py`** — TDD
   - Test: filtri hard (min_trades, max_drawdown, min_sharpe, min_pnl)
   - Implementare score composito

4. **`market_data.py`** — TDD con mock Supabase + mock Binance

5. **`run_pipeline.py`** — integration test

---

### 📝 Note Importanti

- Comando test: `set PYTHONPATH=synthtrade\backend && .venv\Scripts\pytest`
- `.env` non esiste — copiare da `.env.example` e compilare prima di avviare il server
- Supabase locale non avviato — serve `supabase start` in `synthtrade/supabase/`
- `PAPER_TRADING=true` default — non toccare fino alla Fase 6
- Fix RSI già applicato: `loss=0` → RSI=100 (non NaN)

---

**Ultima modifica:** 2025-01-15 — Amazon Q
