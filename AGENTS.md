# AGENTS.md — SynthTrade

> Source of truth: `AGENT.md` (loom framework, task management, commit protocol).
> This file: operational facts for AI agents working in the codebase.

---

## Project Structure

```
synthtrade/
  backend/
    app/                    ← FastAPI app (entry: main.py)
      main.py               ← App lifespan, session restore, startup logic
      config.py             ← Pydantic Settings, reads .env from synthtrade/backend/.env
      scalping/
        router.py           ← Core scalping logic, _execution_state, trade execution (~4000 lines)
        engine/             ← ExecutionLoop, PositionManager, WS clients
        intelligence/       ← Signal scoring, collectors
        supervisor/         ← AI supervisor
      execution/            ← Exchange adapters (OKX, Binance), order execution
        exchange_factory.py ← Provider-neutral factory: build_exchange_adapter(), build_ws_client()
        exchange_models.py  ← SymbolRef, SymbolRules, ExchangeAdapterProtocol
        okx_exchange.py     ← OKX adapter (CCXT + direct REST)
        exchange.py         ← Binance adapter (legacy)
      api/                  ← REST endpoints + WS (ws.py = ConnectionManager singleton)
      scheduler/            ← APScheduler jobs
  frontend/
    synthtrade-ui/          ← Angular app (port 4208)
```

## How to Start

```bash
# Backend (port 8888) — from synthtrade/backend/
.venv/Scripts/activate  # Windows
uvicorn app.main:app --port 8888 --ws-ping-interval 60 --ws-ping-timeout 30

# Or use PowerShell scripts from project root:
.\start_all.ps1    # backend + frontend
.\start_be.ps1     # backend only
```

**Critical: Do NOT use `--reload` for uvicorn during live trading.** WatchFiles reload kills WebSocket connections, causing "unknown" regime and pipeline blocks. The comment in `main.py:11-14` explains this.

## How to Test

```bash
# Backend — from project root (conftest.py adds synthtrade/backend/app to sys.path)
pytest synthtrade/backend/tests/
pytest synthtrade/backend/tests/integration/test_okx_integration.py  # single file
pytest -k "test_1111e"  # single test by name

# Frontend — from synthtrade/frontend/synthtrade-ui/
npm test              # Jest
npm run test:e2e      # Playwright
```

Backend conftest at `synthtrade/backend/tests/conftest.py` mocks Supabase via `mock_supabase` fixture.

## How to Lint

```bash
ruff check synthtrade/backend/app/main.py synthtrade/backend/app/scalping/router.py
python -m py_compile synthtrade/backend/app/main.py  # syntax check
```

Note: The codebase has pre-existing ruff warnings (unused imports, undefined names in Binance legacy paths). Don't fix unrelated warnings.

## Exchange Provider Pattern

Configured via `EXCHANGE_PROVIDER` env var (`okx` | `binance`) and `TRADING_MODE` (`test` | `live`).

- **OKX primary**: `OkxExchangeAdapter` in `okx_exchange.py`, symbol format `BTC-EUR`
- **Binance legacy**: `BinanceExchangeAdapter` in `exchange.py`, symbol format `btceur`
- **Factory**: `build_exchange_adapter()`, `build_ws_client()`, `build_order_stream()` in `exchange_factory.py`
- **Protocol**: `ExchangeAdapterProtocol` in `exchange_models.py` — both adapters implement it

Symbol parsing: `SymbolRef.from_okx("BTC-EUR")` or `SymbolRef.from_compact("BTCEUR")` → `.base`, `.quote`, `.okx`, `.compact`, `.ccxt` properties.

## Key Architecture: `_execution_state`

Global state dict in `scalping/router.py` (line ~83). Contains:
- `exchange` — active ExchangeAdapter instance
- `position_manager` — PositionManager (in-memory positions)
- `session` — session config (symbol, mode, balance, status)
- `fee_tier` — can be dict or FeeTier dataclass (use `_get_fee_rate()` to normalize)
- `signal_engine`, `ws_client`, `risk_config`

Import pattern: `from app.scalping.router import _execution_state, _get_fee_rate, broadcast_scalping_event`

## Windows Gotcha

Loom scripts (`loom/scripts/task.py`) print emoji. On Windows with cp1252 encoding, this crashes. Prefix with:
```bash
PYTHONIOENCODING=utf-8 python loom/scripts/task.py start TASK-XXX "desc"
```

## .env Location

`synthtrade/backend/.env` (NOT project root). Loaded by `config.py` via `pydantic-settings`.

Key env vars: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `EXCHANGE_PROVIDER`, `TRADING_MODE`, `OKX_API_KEY*`, `OPENROUTER_API_KEY`.

## Python Path

`conftest.py` at project root adds `synthtrade/backend/app` to `sys.path`. `pyrightconfig.json` sets `extraPaths: ["synthtrade/backend"]`. Tests import as `from app.xxx import ...`.

## Locom Commands

All loom commands require `PYTHONIOENCODING=utf-8` on Windows. See `AGENT.md` for full command reference.
