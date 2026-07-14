## Goal
- TASK-1151/1152 completati. TASK-1152 = collector + modello, wiring OFF. Obiettivo aggiuntivo: rendere il log diagnostico collector leggibile (multi-riga) e far comparire lo spread nella lista diagnostic, pur restando non cablato.

## Constraints & Preferences
- Nessuna regressione. Pesi engine relativi/normalizzati (somma NON=1.0).
- Log diagnostico temporaneo `[COLLECTORS_DIAG_TEMP]` multi-riga (una riga/collector) finché serve debug, poi ricompattare.

## Progress
### Done
- **TASK-1151 — committato (`203829e`)**.
- **TASK-1152 — collector+modello committato (`f9fba77`)**: `collectors/spread.py`, `SpreadSnapshot` in `models/intelligence.py`, export, `test_spread.py` (8 verdi). Wiring OFF.
- **Refactor diagnostico committato (`7579e44`)**:
  - `signal_score_engine.py`: istanzia + chiama `SpreadCollector` (risultato `results[8]`); log `[COLLECTORS_DIAG_TEMP]` ora **multi-riga** (`symbol=%-10s | collector=%-20s | active=%-3s | status=...`), uno per collector + riga `cvd`.
  - `spread` ora **compare nella lista** con `status=OK/NONE/ERROR`, ma resta `wiring OFF` (non entra nello score).
  - Loop error-warning esteso a spread (index 8).
  - Doc aggiornate (HANDOFF + plan): nota formato multi-riga temporaneo, spread visibile in diag.
- Verifica live OKB-EUR: spread `status=OK` (spread_pct~0.07%), righe diag allineate; funding_rate/open_interest/long_short_ratio `active=off` (OKB-EUR non ha perpetual USDT), obi `OK`, cvd `off` (nessun WS).
- Regressioni: 0 nuove. Nota: `test_signal_score_engine.py::test_compute_with_cvd` FAIL prestante (baseline, confermato con `git stash`).

### In Progress
- (none)

### Blocked
- (none)

## Key Decisions
- Spread in lista ma wiring OFF: `DEFAULT_WEIGHTS` non contiene `spread`; score non influenzato. Da decidere gate-vs-peso in `signal_aggregator.py` prima di cablare.
- `results` order NOW: [0 funding_rate,1 open_interest,2 long_short,3 fear_greed,4 sentiment,5 whale,6 onchain,7 order_book_imbalance,8 spread]. `_diag` list deve restare sincrona con `collector_tasks`.

## Next Steps
- (Opzionale) Ricompattare il log diagnostico in unica riga quando il debug non serve.
- TASK-1153 — CollectorAdapter provider-aware (BTC/ETH perpetual).
- TASK-1154/1155 — Whale Alert API per OKB-EUR; TASK-1157 — CVD grace period; Fase 6 — ricalibrazione pesi.
- Push dei commit locali (f9fba77, 7579e44) quando richiesto.

## Critical Context
- `git status`: pulito tranne `.kilo/AGENTS_context/` (untracked, generato, escluso). Branch ahead of origin/main di 2 commit (non pushati).
- OKX public: OBI `/market/books?instId=&sz=20`; Spread `/market/ticker?instId=` (JSON sync `.json()` → mock con `MagicMock`).
- Diagnostic: ogni collector 1 riga `symbol | collector | active=on/off | status=OK/NONE/ERROR`. cvd ha riga propria.
- `get_configurable_weight_total` esclude funding_rate/oi/long_short se `is_symbol_supported(symbol)==False` (per OKB-EUR → off).

## Relevant Files
- `synthtrade/backend/app/scalping/intelligence/signal_score_engine.py` (diag multi-riga + spread in lista, `_build_snapshot` collector_tasks)
- `synthtrade/backend/app/scalping/intelligence/collectors/spread.py` (collector, log proprio `[COLLECTORS_DIAG_TEMP] spread ... (wiring OFF)`)
- `synthtrade/backend/app/scalping/models/intelligence.py` (`SpreadSnapshot`)
- `synthtrade/backend/tests/scalping/test_spread.py` (8 test)
- `docs/HANDOFF.md`, `docs/plans/collector-intelligence-implementation-plan.md` (aggiornati)
