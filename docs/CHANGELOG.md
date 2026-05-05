# Changelog — SynthTrade

All notable changes to this project will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Fase 2: WebSocket

---

## [0.2.3] — 2025-01-16

### Added
- `api/logs.py`: GET /logs (paginato, filtri action/strategy_id) + GET /logs/export (CSV)
- `tests/integration/test_api_logs.py`: 12 test

---

## [0.2.2] — 2025-01-16

### Added
- `api/dashboard.py`: GET /dashboard (balance, pnl_today, active_strategy, engine_status)
- `api/dashboard.py`: GET /dashboard/equity-history (lista ts+value ordinata)
- `tests/integration/test_api_dashboard.py`: 10 test

### Fixed
- `build_strategy_id` ora usa `hashlib.md5` invece di `hash()` — ID stabili indipendentemente dal seed Python

---

## [0.2.1] — 2025-01-16

### Added
- `api/strategies.py`: GET list/detail, POST approve/reject con mock Supabase
- `tests/integration/test_api_strategies.py`: 12 test (list, filter, detail, approve, reject, 404, 409, auth)

---

## [0.2.0] — 2025-01-16

### Added
- `app/core/auth_utils.py`: `create_access_token`, `verify_token` via python-jose
- `app/dependencies.py`: `get_current_user` con HTTPBearer (auto_error=False → 401)
- `app/api/auth.py`: `POST /auth/login` con password da env
- `app/api/strategies.py`: stub protetto con approve/reject
- `tests/integration/test_api_auth.py`: 7 test (login, token scaduto, route protette)

---

## [0.1.6] — 2025-01-16

### Added
- `app/core/run_pipeline.py`: pipeline batch completa (genera → backtest → rank → upsert Supabase)
- Cache OHLCV in-memory per evitare fetch ripetuti nella stessa pipeline run
- Gestione eccezioni per strategia: errori singoli non bloccano la pipeline
- `tests/integration/test_pipeline.py`: 5 test integration

---

## [0.1.5] — 2025-01-16

### Added
- `app/core/market_data.py`: fetch OHLCV Binance con cache Supabase, fetch solo delta mancante
- `get_current_price()` per prezzo live
- `tests/unit/test_market_data.py`: 7 test con mock Supabase e Binance

---

## [0.1.4] — 2025-01-16

### Added
- `app/core/ranker.py`: filtri hard (min_trades, max_drawdown, min_sharpe, min_pnl) + score composito
- `RankConfig` dataclass con pesi configurabili
- `tests/unit/test_ranker.py`: 15 test (filtri, score range, ordinamento, config custom)

---

## [0.1.3] — 2025-01-16

### Added
- `app/core/backtester.py`: simulazione OHLCV con fee 0.1% e slippage 0.07%
- Chiusura automatica posizione aperta a fine serie
- `tests/unit/test_backtester.py`: 14 test (PnL, fee, equity_curve, no look-ahead)

### Fixed
- PnL calcolato correttamente anche su posizioni mai chiuse da segnale esplicito

---

## [0.1.2] — 2025-01-16

### Added
- `app/core/strategy_generator.py`: prodotto cartesiano parametri, 3 template (trend_ema, mean_reversion_rsi, breakout_bb)
- `StrategyParams` dataclass frozen con hash per ID deterministico
- `build_strategy_id()`: ID univoco da hash parametri
- `tests/unit/test_generator.py`: 8 test (>200 varianti, no duplicati, ID deterministico)

---

## [0.1.1] — 2025-01-15

### Added
- `app/core/indicators.py`: EMA, RSI (con gestione loss=0), Bollinger Bands
- Signal functions: `signal_ema_crossover`, `signal_rsi_reversion`, `signal_breakout_bb` (no look-ahead)
- `LOOKBACK_PERIODS` costante per warm-up minimo
- `tests/unit/test_indicators.py`: 17 test tutti verdi

---

## [0.1.0] — 2025-01-15

### Added
- Struttura monorepo `synthtrade/` (backend, supabase)
- `.gitignore`, `README.md`, `docker-compose.yml`
- FastAPI app con `GET /health` → `{"status": "ok"}`
- `config.py` con `Settings` via pydantic-settings
- `supabase_client.py` singleton con `lru_cache`
- `pytest.ini` (asyncio_mode=auto) + `conftest.py` (fixture `client`, `mock_supabase`)
- 4 migration SQL: strategies, trades, operation_logs, ohlcv_cache
- `seed.sql` con 3 strategie PENDING di esempio
- `Dockerfile` multi-stage + `docker-compose.yml`
- `requirements.txt` con tutte le dipendenze
- `docs/` con TASKS.md, STORY.md, CHANGELOG.md, BACKLOG.md, HANDOFF.md

---

<!-- Versioning guide:
  MAJOR (1.0.0) — breaking changes
  MINOR (0.1.0) — new features, backward compatible
  PATCH (0.0.1) — bug fixes
-->
