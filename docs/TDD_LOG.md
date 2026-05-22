# TDD Log

## 2026-05-22 — TASK-801: Estensione Moduli Core (GREEN)

**Test scritti:** 52 nuovi test + 33 esistenti regression-free = 85 totali passati ✅

### Moduli modificati
1. **`app/core/indicators.py`** — Aggiunte funzioni `vwap()`, `adx()`, `detect_trend()`, `detect_volatility()`
2. **`app/api/ws.py`** — Aggiunti metodi `broadcast_scalping_tick()`, `broadcast_intel_score()`
3. **`app/execution/risk_manager.py`** — Aggiunti controlli `check_max_daily_loss()`, `check_max_consecutive_losses()` + parametri opzionali in `validate_signal()`
4. **`app/execution/exchange.py`** — Aggiunti `place_oco_order()`, `_place_oco_synthetic()`, `place_stop_loss_order()`, `place_limit_order()`

### Test creati
- `tests/unit/test_indicators_vwap_adx.py` — 19 test (VWAP, ADX, regime detection)
- `tests/unit/test_ws_scalping.py` — 8 test (broadcast scalping + intel score)
- `tests/unit/test_risk_manager_intraday.py` — 16 test (daily loss, consecutive losses)
- `tests/unit/test_exchange_oco.py` — 9 test (OCO, stop loss, limit orders)

### Workflow TDD
- 🔴 RED: Tutti i test hanno fallito all'inizio (ImportError per funzioni mancanti)
- 🟢 GREEN: 52/52 test nuovi + 33/33 test esistenti = 85 passati ✅
- 🔵 REFACTOR: Codice pulito, nessuna duplicazione, retrocompatibilità mantenuta