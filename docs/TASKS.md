# TASKS.md — SynthTrade Task Tracking

> **Aggiornato:** 2026-07-16 18:00. Task completati in `docs/ARCHIVE_TASKS.md`. Recap sessione: `docs/recap/2026-07-16_trading-safety-improvements.md`.

---

## TASK-1166 — Refactor router.py: estrazione moduli

**Status:** Pending
**Priorità:** 🟡 MEDIA
**Effort stimato:** 2-3 giorni
**Dipendenze:** TASK-1160, TASK-1164 (completati)

**Problema:** `router.py` è un monolite di ~4200 righe. `_candle_processor()` è una inner function di ~750 righe. Nessun file dovrebbe superare 500 righe (perdita contesto).

**Decomposizione proposta:**

| Nuovo modulo | Contenuto | Righe stimate |
|---|---|---|
| `router/pricing.py` | `_net_to_gross_pct`, fee helpers, `calculate_pnl()` unico | ~200 |
| `router/session_lifecycle.py` | `_start_session`, `_stop_session`, `_restore_scalping_session` | ~400 |
| `router/trade_executor.py` | `_candle_processor` → `TradeExecutor` class | ~800 |
| `router/ws_broadcast.py` | `_start_ws_broadcast`, `_stop_ws_broadcast`, `broadcast_scalping_event` | ~300 |
| `router/db_ops.py` | `_open_position`, `_close_position_and_record`, `_update_closed_position_in_db` | ~300 |
| `router/rest_endpoints.py` | Tutti gli `@router.get/post` | ~600 |

`router.py` resterebbe come orchestratore leggero (~200 righe) che importa e collega i moduli.

**Acceptance Criteria:**
- Nessun file in `router/` supera 500 righe
- `router.py` è < 300 righe (orchestratore)
- Tutti i test passano
- Nessuna modifica al comportamento osservabile

---

## Task da Investigare — Aperti/Parziali

> Da `MASTER_RECAP.md` 26/06/2026. Verifica 01/07/2026.

| Task | Status | Note |
|------|--------|------|
| TASK-INVEST-011 — Regime misclassification (volume-confirmed) | 🟡 APERTO | Nessuna logica volume-confirmed in `regime_detector.py` |
| TASK-INVEST-012 — Falling Knife Protection | ✅ ALLINEATO | TASK-906 completato. Monitorare in live. |
| TASK-INVEST-013 — trend_direction troppo sensibile | ⚠️ PARZIALE | Codice presente ma soglia troppo sensibile |
| TASK-INVEST-017 — Bias outcome_label Supervisor | ⚠️ PARZIALE | Usa solo PnL (no bias regime) |
| TASK-INVEST-018 — Soglia dinamica senza decadimento | ⚠️ PARZIALE | Decay/degradation non implementato |
| TASK-INVEST-020 — Slope filter su EMA Cross | 🟡 APERTO | Nessuno slope filter in `ema_cross.py` |
