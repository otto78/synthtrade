# TASK-1166 — Fase 3: Piano di completamento refactoring router.py

## Stato attuale

`router.py`: **2187 righe** (da 4310 originali, -49%).

### Completato (Fase 1 + 2)
| Sub-TASK | File creato | Righe | Stato |
|----------|-------------|-------|-------|
| 1166.A | `_state.py` | 57 | DONE |
| 1166.B1 | `pricing.py` | 180 | DONE |
| 1166.B2 | `reconciliation.py` | 179 | DONE |
| 1166.B3 | `db_ops.py` | 176 | DONE |
| 1166.C1 | `trade_executor.py` | 518 | DONE |
| 1166.C2 | `session_lifecycle.py` | 72 | DONE |
| — | `market_processors.py` | 1063 | DONE (D1/D2/D3 già estratti) |

### Da fare

| Sub-TASK | Descrizione | Righe stimate |
|----------|-------------|---------------|
| **FIX** | Bug critici da fixare prima di proseguire | — |
| 1166.D | Pipeline: `_start_ws_broadcast` → `pipeline.py`, `broadcast_scalping_event` → `broadcast.py` | ~260 righe |
| 1166.E | REST endpoints → `rest/` sottomoduli | ~1170 righe |
| 1166.F | `router.py` orchestratore finale + backward compat | target <500 righe |

---

## PASSO 0: Fix critici (pre-requisito)

### BUG-1: Import mancanti in `router.py`
`router.py` chiama 5 funzioni che non importa (NameError a runtime):

| Funzione | Chiamata a riga | Definita in |
|----------|-----------------|-------------|
| `_refresh_session_balance()` | L1006, L1496 | `session_lifecycle.py` |
| `_sync_session_load_guard()` | L1085, L1129, L1146 | `session_lifecycle.py` |
| `_update_closed_position_in_db()` | L446 | `db_ops.py` |
| `_handle_bracket_failed()` | L1346 | `trade_executor.py` |
| `_close_position_and_record()` | L1399 | `trade_executor.py` |

**Fix:** Aggiungere import in cima a `router.py`:
```python
from app.scalping.session_lifecycle import _refresh_session_balance, _sync_session_load_guard
from app.scalping.db_ops import _save_open_position_to_db, _update_closed_position_in_db
from app.scalping.trade_executor import (
    _live_close_position, _on_order_update, _on_uds_reconnect_sync,
    _start_uds_if_needed, _handle_bracket_failed, _close_position_and_record,
    _check_daily_loss, _check_drawdown,
)
```

### BUG-2: Codice loose in `market_processors.py` L1036-1063
Codice a livello di modulo con `await` che viene eseguito all'import time. Contiene anche una sintassi errata (`supervisor.set__execution_state.get('loop')`). Questo codice dovrebbe essere dentro una funzione o rimosso.

**Fix:** Avvolgere in una funzione `_restore_mode_setup(symbol)` e chiamarla dal context corretto, oppure rimuovere se già gestito altrove.

### BUG-3: `fix_trade_processor.py` — codice morto
Script one-shot (19 righe) che applica una patch testuale. Non è un modulo runtime. **Da eliminare.**

---

## PASSO 1: Sub-TASK-1166.D — Broadcast + Pipeline

### D0: `broadcast.py` (~25 righe)
Spostare `broadcast_scalping_event` (L221-239) + `_now()` (L246-247) in `scalping/broadcast.py`.

Questo rompe il ciclo circolare: `market_processors.py` importa `broadcast_scalping_event` da `router.py`. Dopo questo cambio, importa da `broadcast.py`.

```python
# broadcast.py
async def broadcast_scalping_event(event_type: str, data: dict):
    from app.scalping._state import _scalping_ws_connections
    ...

def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
```

**Aggiornare:**
- `market_processors.py` L27: `from app.scalping.broadcast import broadcast_scalping_event`
- `trade_executor.py`: aggiungere import locale dentro le funzioni che lo usano
- `session_lifecycle.py`: idem
- `router.py`: re-export per backward compat

### D4: `pipeline.py` (~250 righe)
Spostare `_start_ws_broadcast` (L252-474) + `_stop_ws_broadcast` (L712-731) in `scalping/pipeline.py`.

`_start_ws_broadcast` resta un'async function con la stessa signature. Dipende da:
- `_state.py` (execution_state)
- `broadcast.py` (broadcast_scalping_event)
- `pricing.py` (_get_fee_rate)
- `trade_executor.py` (_update_closed_position_in_db via db_ops)
- `reconciliation.py`
- `market_processors.py` (i 3 processori)

**Aggiornare:**
- `main.py` L412: `from app.scalping.pipeline import _start_ws_broadcast`
- `config_api.py` L122: `from app.scalping.pipeline import _stop_ws_broadcast`
- `router.py`: re-export per backward compat

### Verifica
Dopo questo passo, il dependency graph diventa:
```
_state.py          (Layer 0)
pricing.py         (Layer 1) → _state
reconciliation.py  (Layer 1) → _state
db_ops.py          (Layer 1) → _state
session_lifecycle.py(Layer 1) → _state, broadcast
broadcast.py       (Layer 1) → _state
trade_executor.py  (Layer 2) → _state, pricing, reconciliation, db_ops, broadcast
market_processors.py(Layer 3) → _state, pricing, db_ops, trade_executor, session_lifecycle, broadcast
pipeline.py        (Layer 3) → _state, broadcast, pricing, reconciliation, db_ops, market_processors, trade_executor
```

Zero cicli circolari.

---

## PASSO 2: Sub-TASK-1166.E — REST endpoints

Raggruppare i 31 endpoint REST in 3-4 moduli sotto `scalping/rest/`:

### E1: `rest/market_data.py` (~230 righe)
Endpoint di mercato e dati storici:
- `GET /binance/exchange-info` (L478-503, 26 righe)
- `GET /exchange/instruments` (L509-581, 73 righe)
- `GET /sessions` (L584-651, 68 righe)
- `GET /trade-history` (L655-681, 27 righe)
- `GET /candles/{symbol}` (L685-709, 25 righe)

### E2: `rest/backtest.py` (~80 righe)
- `POST /backtest/run` (L738-780, 43 righe)
- `GET /backtest/{id}/result` (L784-793, 10 righe)
- `GET /backtest/list` (L797-812, 16 righe)

### E3: `rest/session.py` (~580 righe)
Endpoint session/position/config/performance/logs:
- `GET /session` (L997-1030, 34 righe)
- `POST /session` — **`control_session`** (L1034-1527, 494 righe) — resta il pezzo grosso
- `GET /session/{id}/logs` (L1537-1575, 39 righe)
- `GET /session/{id}/logs/analysis` (L1579-1638, 60 righe)
- `GET /position` (L1646-1732, 87 righe)
- `GET /position/list` (L1736-1750, 15 righe)
- `GET/POST /config` (L1758-1775, 18 righe)
- `GET/POST /risk/config` (L1782-1819, 38 righe)
- `PATCH /session/trade-value` (L1823-1836, 14 righe)
- `GET /performance` (L1843-1955, 113 righe)
- `GET /health` (L959-993, 35 righe)

**NOTA:** `control_session` (494 righe) è il candidato per un'ulteriore estrazione futura (Sub-task 1166.C2 già fatto, ma `control_session` è ancora in router.py). Potrebbe diventare `session_controller.py`.

### E4: `rest/intel_opportunity.py` (~190 righe)
- `GET /intelligence/{symbol}/snapshot` (L820-874, 55 righe)
- `GET /intelligence/{symbol}/history` (L878-891, 14 righe)
- `_snapshot_to_dict` (L894-926, 33 righe) — helper condiviso con `market_processors.py`
- `GET /opportunities` (L2043-2091, 49 righe)
- `POST /opportunities/{id}/watchlist` (L2095-2106, 12 righe)
- `POST /opportunities/{id}/ignore` (L2110-2117, 8 righe)
- `GET /opportunities/watchlist` (L2121-2124, 4 righe)
- `GET /supervisor/history` (L2131-2187, 57 righe)
- `GET /debug/session-load` (L1963-1967, 5 righe)
- `GET /debug/pipeline` (L1971-2022, 52 righe)

### Pattern di registrazione
Ogni modulo rest è un `APIRouter` che viene incluso in `router`:

```python
# rest/market_data.py
from fastapi import APIRouter
router = APIRouter()

@router.get("/exchange/instruments")
async def exchange_instruments():
    ...

# router.py
from app.scalping.rest.market_data import router as market_data_router
from app.scalping.rest.backtest import router as backtest_router
from app.scalping.rest.session import router as session_router
from app.scalping.rest.intel_opportunity import router as intel_router

router.include_router(market_data_router)
router.include_router(backtest_router)
router.include_router(session_router)
router.include_router(intel_router)
```

---

## PASSO 3: Sub-TASK-1166.F — router.py orchestratore finale

Dopo i passi precedenti, `router.py` contiene solo:

1. **Definizioni router** (~10 righe): `router = APIRouter(...)`, `ws_scalping_router = APIRouter(...)`
2. **Re-export backward compat** (~30 righe): import da tutti i moduli + re-export
3. **WebSocket endpoint** `scalping_websocket` (L106-219, ~114 righe)
4. **Helper piccoli** che non si classificano altrove:
   - `_snapshot_to_dict` (se non spostato in intel_opportunity.py)
   - `_calc_session_entry_and_hold` (~23 righe)
   - `_get_opportunity_scheduler` (~7 righe)
   - `_is_valid_uuid` (già in pricing.py)

**Target**: <350 righe

### Backward compat (CRITICO)
`router.py` deve continuare a re-exportare tutto per non rompere:
- `main.py`: `_execution_state`, `_start_ws_broadcast`, `broadcast_scalping_event`, `_reconcile_position_with_exchange`, `_get_fee_rate`
- `config_api.py`: `_execution_state`, `_stop_ws_broadcast`
- `scalping_jobs.py`: `_execution_state`, `_refresh_session_balance`, `broadcast_scalping_event`
- `user_data_stream.py`: `_execution_state`
- `parameter_updater.py`: `_execution_state`, `broadcast_scalping_event`
- `supervisor_scheduler.py`: `_execution_state`, `broadcast_scalping_event`
- `test_okx_integration.py`: `_execution_state`, `_on_order_update`, `_save_open_position_to_db`, `_update_closed_position_in_db`, `_handle_bracket_failed`, `broadcast_scalping_event`

```python
# router.py — re-export block
from app.scalping._state import _execution_state, _backtest_results, ...
from app.scalping.broadcast import broadcast_scalping_event
from app.scalping.pricing import _get_fee_rate, _net_to_gross_pct, _sl_price_from_entry, ...
from app.scalping.reconciliation import _reconcile_position_with_exchange
from app.scalping.db_ops import _save_open_position_to_db, _update_closed_position_in_db
from app.scalping.trade_executor import (
    _on_order_update, _handle_bracket_failed, _close_position_and_record,
    _live_close_position, _on_uds_reconnect_sync, _start_uds_if_needed,
    _check_daily_loss, _check_drawdown,
)
from app.scalping.session_lifecycle import _refresh_session_balance, _sync_session_load_guard, _enrich_session_with_threshold
from app.scalping.pipeline import _start_ws_broadcast, _stop_ws_broadcast
```

---

## Ordine di esecuzione

```
PASSO 0 (FIX) → PASSO 1 (D: broadcast + pipeline) → PASSO 2 (E: REST) → PASSO 3 (F: cleanup)
```

### Stima effort
| Passo | Effort | Rischio |
|-------|--------|---------|
| PASSO 0: Fix bug critici | 30 min | Basso — solo import + fix sintassi |
| PASSO 1: broadcast.py + pipeline.py | 1-2h | Medio — rompe ciclo circolare |
| PASSO 2: REST endpoints (4 moduli) | 2-3h | Basso — mossa meccanica |
| PASSO 3: router.py cleanup + backward compat | 1h | Medio — verificare tutti gli import esterni |
| **Totale** | **5-7h** | |

### Test after each step
```bash
# Syntax check
python -m py_compile synthtrade/backend/app/scalping/router.py

# Integration tests
cd synthtrade/backend && python -m pytest tests/ -v

# Ruff lint
ruff check synthtrade/backend/app/scalping/router.py
```

### File da eliminare
- `fix_trade_processor.py` — codice morto
