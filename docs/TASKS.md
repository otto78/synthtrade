# TASKS.md — SynthTrade Task Tracking

> **Aggiornato:** 2026-07-16 17:10. Task completati in `docs/ARCHIVE_TASKS.md`.

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

## TASK-906 — Trend Analysis: Prevenzione Falling Knife in Mean-Reversion

**Status:** ✅ Implemented (16/07/2026)
**Priorità:** ALTA
**Effort:** 3 ore

**Problema:** `signal_aggregator.py:277-293` approvava mean-reversion BUY incondizionatamente quando `bias == "bearish"`. Durante un crash verticale, RSI+Bollinger segnalava BUY (oversold) ma il prezzo continuava a cadere → stop loss.

**Fix:** Aggiunta guard `FALLING_KNIFE_TREND_THRESHOLD = -20.0` in `signal_aggregator.py`. Se `trend_direction == "diverging"` AND `trend_5m < -20.0` (score drop di 20+ punti in 5 minuti), il mean-reversion BUY viene bloccato.

**Logica:**
- `trend_5m`: variazione dello score negli ultimi 5 minuti (es: -35.0 = score dropato 35 punti)
- `trend_direction`: `"diverging"` = score si allontana da zero (crash), `"converging"` = score si avvicina a zero (recovery)
- Guard attiva SOLO per mean-reversion BUY (rsi_bollinger, stoch_rsi_bb_squeeze)
- Non influenza: CLOSE, SELL, BUY normali, mean-reversion SELL

**File modificati:**
- `signal_aggregator.py` — costante + guard
- `test_task_906.py` — 12 nuovi test

---

## TASK-903 — RegimeDetector: isteresi K candele

**Status:** ✅ Completed (16/07/2026)
**Priorità:** MEDIA
**Effort:** 1-2 ore

**Problema:** `RegimeDetector` era stateless → flickering ogni tick ai boundary.

**Fix:** Aggiunta isteresi K=3 in `regime_detector.py`. Il regime committed cambia solo se lo stesso candidato si osserva per 3 candele consecutive. Proprietà `pending_regime` e `pending_count` per debug. 15 test in `test_task_903.py`.

---

## TASK-904 — StrategySelector DB-driven

**Status:** Pending
**Priorità:** BASSA
**Dipendenze:** TASK-902

**Problema:** Mapping `regime → strategia_consentita` hardcoded in due posti.

**File:**
- `strategy_selector.py` — leggere da `scalping_runtime_config`
- `supervisor_scheduler.py` — sostituire dict hardcoded con lettura da DB
- Migration: chiavi `regime_strategy_*` a `scalping_runtime_config`

---

## TASK-898 — Analisi Trend basata su dati persistiti

**Status:** ✅ Completed (16/07/2026)
**Priorità:** BASSA

**Risultato:** 19 trade chiusi con trend data analizzati. Nessuna correlazione significativa (r=0.004). Il 100% dei trade è BUY, 84% stop loss. Regime sempre "unknown". Report: `docs/trend_analysis_report.md`.

**Finding chiave:** TASK-906 (falling knife) e TASK-908 (resume guard) mitigano i problemi identificati. Serve più dati (≥100 trade) per analisi statistica significativa.

---

## Task da Investigare — Aperti/Parziali

> Da `MASTER_RECAP.md` 26/06/2026. Verifica 01/07/2026.

| Task | Status | Note |
|------|--------|------|
| TASK-INVEST-011 — Regime misclassification (volume-confirmed) | 🟡 APERTO | Nessuna logica volume-confirmed in `regime_detector.py` |
| TASK-INVEST-012 — Falling Knife Protection | 🟡 APERTO | Allineata a TASK-906 (in attesa dati reali) |
| TASK-INVEST-013 — trend_direction troppo sensibile | ⚠️ PARZIALE | Codice presente ma soglia troppo sensibile |
| TASK-INVEST-017 — Bias outcome_label Supervisor | ⚠️ PARZIALE | Usa solo PnL (no bias regime) |
| TASK-INVEST-018 — Soglia dinamica senza decadimento | ⚠️ PARZIALE | Decay/degradation non implementato |
| TASK-INVEST-020 — Slope filter su EMA Cross | 🟡 APERTO | Nessuno slope filter in `ema_cross.py` |
