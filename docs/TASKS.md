# TASKS.md — SynthTrade Task Tracking

> **Aggiornato:** 2026-07-16 20:00. Task completati in `docs/ARCHIVE_TASKS.md`. Recap sessione: `docs/recap/2026-07-16_trading-safety-improvements.md`.

---

## TASK-1166 — Refactor router.py: estrazione moduli

**Status:** Pending
**Priorita:** MEDIA
**Effort stimato:** 2-3 giorni
**Dipendenze:** TASK-1160, TASK-1164 (completati)

**Problema:** `router.py` e un monolite di 4310 righe. `_candle_processor()` e una inner function di 839 righe. Nessun file dovrebbe superare 500 righe (perdita contesto).

**Architettura attuale (line ranges):**
- L18-61: imports
- L62-68: `_get_fee_rate`
- L70-239: `_reconcile_position_with_exchange`
- L242-299: state dicts (`_execution_state`, `_scalping_ws_connections`, `_bnb_price_cache`, etc.)
- L301-472: pricing helpers (`_throttled_warning`, `_is_valid_uuid`, `_exit_price_ratio`, `_net_to_gross_pct`, `_round_trip_fee_drag_pct`, `_expected_net_pct_at_exit`, `_tp_price_from_entry`, `_sl_gross_fraction`, `_sl_price_from_entry`, `_convert_bnb_commission_to_usdc`)
- L480-619: `scalping_websocket` endpoint + `broadcast_scalping_event` + `_now`
- L625-684: session helpers (`_enrich_session_with_threshold`, `_sync_session_load_guard`, `_refresh_session_balance`)
- L686-786: `_live_close_position`
- L788-951: db_ops (`_save_open_position_to_db`, `_update_closed_position_in_db`)
- L954-1349: trade callbacks (`_on_order_update`, `_on_uds_reconnect_sync`, `_start_uds_if_needed`, `_handle_bracket_failed`, `_close_position_and_record`, `_check_daily_loss`, `_check_drawdown`)
- L1351-2597: `_start_ws_broadcast` (1247 lines!) containing `_candle_processor` (839 lines), `_trade_processor` (120 lines), `_intelligence_processor` (36 lines)
- L2600-3116: REST endpoints (backtest, market data, session, intel, health, etc.)
- L3120-3650: `control_session` (POST /session, 495 lines)
- L3660-4310: more REST endpoints (logs, positions, config, performance, opportunities, supervisor)

**External consumers of router.py:**
| File | Imports |
|---|---|
| `app/main.py` | `router`, `ws_scalping_router`, `_execution_state`, `_start_ws_broadcast`, `_reconcile_position_with_exchange`, `broadcast_scalping_event`, `_get_fee_rate` |
| `app/api/config_api.py` | `_execution_state`, `_stop_ws_broadcast` |
| `app/scheduler/scalping_jobs.py` | `_execution_state`, `_refresh_session_balance`, `broadcast_scalping_event` |
| `app/execution/user_data_stream.py` | `_execution_state` |
| `app/scalping/supervisor/parameter_updater.py` | `_execution_state`, `broadcast_scalping_event` |
| `app/scalping/supervisor/supervisor_scheduler.py` | `_execution_state`, `broadcast_scalping_event` |

---

### Sub-TASK-1166.A — Shared state module (`_state.py`)

**Effort:** ~30 min
**Crea:** `scalping/_state.py` (~50 righe)

Estrarre `_execution_state`, `_scalping_ws_connections`, `_bnb_price_cache`, `_bnb_price_cache_ttl`, `_last_warning`, `_warning_throttle_sec` in un modulo condiviso. Tutti gli altri moduli importano da qui.

```python
# _state.py
_execution_state: Dict[str, Any] = { ... }
_scalping_ws_connections: List[WebSocket] = []
_bnb_price_cache: Dict[str, float] = {}
_bnb_price_cache_ttl: int = 60
_last_warning: Dict[str, float] = {}
_warning_throttle_sec: float = 10.0
```

**Acceptance Criteria:**
- Tutti gli import di `_execution_state` da router.py puntano a `_state.py`
- Nessuna modifica al comportamento osservabile
- I test esistenti passano senza modifiche

---

### Sub-TASK-1166.B — Moduli foglia (pricing, reconciliation, db_ops)

**Effort:** ~1-2h
**Dipende da:** 1166.A
**Crea:** 3 moduli

#### B1: `scalping/pricing.py` (~200 righe)
Estrarre: `_get_fee_rate`, `_exit_price_ratio`, `_net_to_gross_pct`, `_round_trip_fee_drag_pct`, `_expected_net_pct_at_exit`, `_tp_price_from_entry`, `_sl_gross_fraction`, `_sl_price_from_entry`, `_convert_bnb_commission_to_usdc`, `_throttled_warning`

- Tutte funzioni pure tranne `_convert_bnb_commission_to_usdc` (legge `_execution_state["fee_tier"]` e `_execution_state["session"]`)
- `_throttled_warning` si muove qui (usa `_last_warning`, `_warning_throttle_sec` da `_state.py`)
- Nessun rischio di dipendenza circolare

#### B2: `scalping/reconciliation.py` (~170 righe)
Estrarre: `_reconcile_position_with_exchange`

- Funzione leaf, legge solo `_execution_state["exchange"]` come fallback
- Nessun rischio di dipendenza circolare

#### B3: `scalping/db_ops.py` (~165 righe)
Estrarre: `_save_open_position_to_db`, `_update_closed_position_in_db`

- Funzioni leaf, leggono `_execution_state["session"]` per `db_session_id`, `strategy`
- Nessun rischio di dipendenza circolare

**Acceptance Criteria:**
- Ogni modulo e <300 righe
- Tutti i test passano
- `_get_fee_rate` mantiene la stessa signature per backward compat
- Aggiungere re-export in `router.py` per compatibilita esterna

---

### Sub-TASK-1166.C — Trade executor + session lifecycle

**Effort:** ~2h
**Dipende da:** 1166.A, 1166.B
**Crea:** 2 moduli

#### C1: `scalping/trade_executor.py` (~300 righe)
Estrarre: `_live_close_position`, `_on_order_update`, `_on_uds_reconnect_sync`, `_start_uds_if_needed`, `_handle_bracket_failed`, `_close_position_and_record`, `_check_daily_loss`, `_check_drawdown`

- Dipende da: pricing (get_fee_rate, convert_bnb), reconciliation, db_ops, ws_broadcast (broadcast, refresh)
- Chiamato da: `_candle_processor`, `_trade_processor`, `control_session`

#### C2: `scalping/session_lifecycle.py` (~80 righe)
Estrarre: `_enrich_session_with_threshold`, `_sync_session_load_guard`, `_refresh_session_balance`

- Funzioni helper piccole, dipendono da `_execution_state` e broadcast
- `control_session` (495 righe) resta in `router.py` come orchestratore principale

**Acceptance Criteria:**
- Ogni modulo e <400 righe
- Tutti i test passano
- Re-export in `router.py` per compatibilita

---

### Sub-TASK-1166.D — Pipeline extraction (`_start_ws_broadcast`)

**Effort:** ~3-4h (il piu complesso)
**Dipende da:** 1166.A, 1166.B, 1166.C
**Crea:** 1 modulo grande + 2-3 sottomoduli

`_start_ws_broadcast` (L1351-2597, 1247 righe) contiene 3 inner functions che sono i veri target:

#### D1: `scalping/processors/candle_processor.py` (~850 righe)
Estrarre `_candle_processor` (L1563-2401) come classe `CandleProcessor`:
```python
class CandleProcessor:
    def __init__(self, *, symbol, state, execution_loop, broadcast_fn, ...):
        self.symbol = symbol
        self._state = state
        ...
    async def run(self):
        """Main loop replacing _candle_processor."""
```

- Le closure variables (`client`, `execution_loop`, `symbol`, `guard`, `pm`, `_signal_log_id`) diventano attributi di istanza
- Dipende da: pricing, trade_executor, db_ops, reconciliation, ws_broadcast

#### D2: `scalping/processors/trade_processor.py` (~130 righe)
Estrarre `_trade_processor` (L2402-2521)

#### D3: `scalping/processors/intel_processor.py` (~50 righe)
Estrarre `_intelligence_processor` (L2524-2559)

#### D4: `scalping/pipeline.py` (~300 righe)
`_start_ws_broadcast` ridotto a orchestratore che:
1. Inizializza i processori
2. Gestisce WS client, CVD calculator, session restore
3. Avvia i 3 processori come asyncio tasks

**Acceptance Criteria:**
- Nessun file in `processors/` supera 500 righe
- `_start_ws_broadcast` ridotto a <300 righe
- Tutti i test passano
- Nessuna modifica al comportamento osservabile

---

### Sub-TASK-1166.E — REST endpoints

**Effort:** ~1-2h
**Dipende da:** 1166.A, 1166.B
**Crea:** 1-2 moduli (~850 righe totali, da splittare)

Estrarre tutti gli endpoint `@router.get/post/patch`:
- Backtest endpoints (L2600-2935)
- Market data (L2808-2832)
- Session/position/performance (L3120-3873, L3966-4078)
- Config endpoints (L3881-3959)
- Intelligence (L2943-3014)
- Opportunity (L4156-4247)
- Logs/debug (L3660-4145)

Se >500 righe, splittare in `rest/backtest.py`, `rest/session.py`, etc.

**Acceptance Criteria:**
- Nessun file supera 500 righe
- Tutti i test passano
- Router registration identica (stessi paths, stessi metodi)

---

### Sub-TASK-1166.F — router.py orchestratore + backward compat

**Effort:** ~1h
**Dipende da:** tutti i sub-task precedenti
**Modifica:** `router.py`

Ridurre `router.py` a ~250 righe contenente:
- Definizioni `router` e `ws_scalping_router`
- `_execution_state` re-export da `_state.py`
- Re-export di tutte le funzioni pubbliche per backward compat
- `control_session` (orchestratore principale, ~495 righe — e il candidato per estrazione futura)
- Funzioni helper piccole rimaste (`_snapshot_to_dict`, `_calc_session_entry_and_hold`, `_get_opportunity_scheduler`, `_is_valid_uuid`)

**Acceptance Criteria:**
- `router.py` e <500 righe
- Tutti gli import esterni funzionano senza modifiche
- Tutti i test passano

---

### Ordine di esecuzione consigliato

```
1166.A (state)  ──> 1166.B (leaf modules)  ──> 1166.C (trade+session)
                                              ──> 1166.E (REST)
                                              ──> 1166.D (pipeline) ──> 1166.F (cleanup)
```

1166.A e un prerequisito per tutti. 1166.B e prerequisito per C, D, E. 1166.F e l'ultimo.

---

## Task da Investigare — Aperti/Parziali

> Da `MASTER_RECAP.md` 26/06/2026. Verifica 01/07/2026.

| Task | Status | Note |
|------|--------|------|
| TASK-INVEST-011 — Regime misclassification (volume-confirmed) | APERTO | Nessuna logica volume-confirmed in `regime_detector.py` |
| TASK-INVEST-012 — Falling Knife Protection | ALLINEATO | TASK-906 completato. Monitorare in live. |
| TASK-INVEST-013 — trend_direction troppo sensibile | PARZIALE | Codice presente ma soglia troppo sensibile |
| TASK-INVEST-017 — Bias outcome_label Supervisor | PARZIALE | Usa solo PnL (no bias regime) |
| TASK-INVEST-018 — Soglia dinamica senza decadimento | PARZIALE | Decay/degradation non implementato |
| TASK-INVEST-020 — Slope filter su EMA Cross | APERTO | Nessuno slope filter in `ema_cross.py` |
