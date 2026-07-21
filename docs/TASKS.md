# TASKS.md — SynthTrade Task Tracking

> **Aggiornato:** 2026-07-21. Task completati in `docs/ARCHIVE_TASKS.md`. Recap sessione: `docs/recap/2026-07-16_trading-safety-improvements.md`.

---



## TASK-1166 — Refactor router.py: estrazione moduli

**Status:** COMPLETATO ✅
**Priorita:** MEDIA
**Effort totale:** ~2 giorni
**Dipendenze:** TASK-1160, TASK-1164 (completati)

**Risultato:** `router.py` ridotto da 4310 a 197 righe (-95.4%). Moduli estratti verificati con 12/12 test di integrazione passanti.

**Architettura finale:**
| Modulo | Righe | Contenuto |
|--------|-------|-----------|
| `_state.py` | 50 | Variabili globali condivise |
| `pricing.py` | 149 | Funzioni pure pricing/size |
| `reconciliation.py` | 162 | Riconciliazione posizioni |
| `db_ops.py` | 169 | Operazioni database |
| `trade_executor.py` | 463 | Logica esecuzione trade |
| `session_lifecycle.py` | 59 | Lifecycle sessione |
| `broadcast.py` | 38 | Broadcasting eventi WS |
| `pipeline.py` | 244 | Orchestratore WS broadcast |
| `candle_processor.py` | 844 | Processore candele (loop principale) |
| `trade_processor.py` | 133 | Processore trade real-time |
| `intel_processor.py` | 75 | Processore intelligence + restore |
| `router.py` | 197 | Orchestratore + WS endpoint + re-export |

**REST endpoints:**
| Modulo | Righe | Contenuto |
|--------|-------|-----------|
| `rest/session.py` | 668 | control_session, health, get_session, logs |
| `rest/position.py` | 116 | get_position, list_positions |
| `rest/performance.py` | 144 | get_performance + helper |
| `rest/config.py` | 67 | config + risk config endpoints |
| `rest/market_data.py` | 245 | Dati mercato |
| `rest/intel_opportunity.py` | 243 | Intelligence + opportunity |
| `rest/backtest.py` | 75 | Backtest endpoints |

---

### [COMPLETATO] Sub-TASK-1166.A — Shared state module (`_state.py`)

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

### [COMPLETATO] Sub-TASK-1166.B — Moduli foglia (pricing, reconciliation, db_ops)

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

### [COMPLETATO] Sub-TASK-1166.C — Trade executor + session lifecycle

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

### [COMPLETATO] Sub-TASK-1166.D — Pipeline extraction (`_start_ws_broadcast`)

**Effort:** ~3-4h (il piu complesso)
**Dipende da:** 1166.A, 1166.B, 1166.C
**Crea:** 3 moduli

Estratto `_start_ws_broadcast` (1247 righe) contenente 3 inner functions:

#### D1: `scalping/candle_processor.py` (844 righe)
Estrarre `_candle_processor` come funzione async indipendente.

#### D2: `scalping/trade_processor.py` (133 righe)
Estrarre `_trade_processor` come funzione async indipendente.

#### D3: `scalping/intel_processor.py` (75 righe)
Estrarre `_intelligence_processor` + `restore_mode_post_start`.

#### D4: `scalping/pipeline.py` (244 righe)
`_start_ws_broadcast` ridotto a orchestratore che inizializza i processori e li avvia come asyncio tasks.

`market_processors.py` (10 righe) diventa modulo di re-export per backward compat.

**Acceptance Criteria:**
- ✅ Tutti i test passano
- ✅ Backward compat mantenuta (re-export in market_processors.py)
- ✅ 12/12 test integrazione passanti

---

### [COMPLETATO] Sub-TASK-1166.E — REST endpoints

**Effort:** ~1-2h
**Dipende da:** 1166.A, 1166.B
**Crea:** 3 moduli

Estrarre endpoint da `rest/session.py` (959 righe):

#### E1: `rest/position.py` (116 righe)
- `GET /position` — get_position
- `GET /position/list` — list_positions

#### E2: `rest/performance.py` (144 righe)
- `GET /performance` — get_performance
- `_calc_session_entry_and_hold` — helper condiviso

#### E3: `rest/config.py` (67 righe)
- `GET /config`, `POST /config/reload`, `POST /config/{key}`
- `GET /risk/config`, `POST /risk/config`

**Acceptance Criteria:**
- ✅ Tutti i test passano
- ✅ Router registration identica (stessi paths, stessi metodi)
- ✅ 12/12 test integrazione passanti

---

### [COMPLETATO] Sub-TASK-1166.F — router.py orchestratore + backward compat

**Effort:** ~1h
**Dipende da:** tutti i sub-task precedenti
**Modifica:** `router.py`

`router.py` ridotto a 197 righe contenente:
- Definizioni `router` e `ws_scalping_router`
- `_execution_state` re-export da `_state.py`
- Re-export di tutte le funzioni pubbliche per backward compat
- WebSocket endpoint `scalping_websocket`

**Acceptance Criteria:**
- ✅ `router.py` è 197 righe (<500)
- ✅ Tutti gli import esterni funzionano senza modifiche
- ✅ Tutti i test passano

---

### Ordine di esecuzione

```
1166.A (state) ✅  ──> 1166.B (leaf modules) ✅  ──> 1166.C (trade+session) ✅
                                                        ──> 1166.E (REST) ✅
                                                        ──> 1166.D (pipeline) ✅ ──> 1166.F (cleanup) ✅
```

**TASK-1166 COMPLETATO.** `router.py` ridotto da 4310 a 197 righe (-95.4%).

---
