# Changelog — SynthTrade

All notable changes to this project will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Fase 1: `strategy_generator.py`, `backtester.py`, `ranker.py`, `market_data.py`

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
