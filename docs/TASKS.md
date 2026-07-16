# TASKS.md — SynthTrade Task Tracking

> **Aggiornato:** 2026-07-16 16:10. Task completati in `docs/ARCHIVE_TASKS.md`.

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

**Status:** Pending (in attesa del prossimo drop di mercato per raccogliere dati reali)
**Priorità:** ALTA

**Obiettivo:** Bloccare trade in "mean-reversion" durante crolli verticali improvvisi.

**Stato attuale (analisi 15/07):** `signal_aggregator.py:277-293` approva mean-reversion BUY incondizionatamente quando `bias == "bearish"`. Trend/velocity (`trend_5m`, `trend_direction`) esistono in `SignalScore` e vengono loggati in `session_signal_log`, ma **mai usati come filtro decisionale**. Serve: (1) calibrare soglia da dati reali, (2) aggiungere guard in `signal_aggregator.py`.

**Task:**
1. **Data Collection:** Monitorare log durante cali per registrare velocità (`trend_5m`) in fase "diverging"
2. **Rule Definition:** Soglia dinamica (`if trend_direction == "diverging" and trend_5m <= -X`)
3. **Implementation:** Aggiornare `signal_aggregator.py` bloccando trade in mean-reversion
4. **Verifica:** Prevenga falling knife senza bloccare mean-reversion legittimo

---

## TASK-903 — RegimeDetector: isteresi K candele

**Status:** Pending
**Priorità:** MEDIA
**Effort:** 1-2 ore

**Problema:** `RegimeDetector` è completamente **stateless** (nessun `__init__`, zero attributi). Ogni chiamata a `detect()` produce un regime da zero basato sulle ultime 20 candele. Le soglie (volatility_ratio > 0.01, price_change > 0.003) causano flickering quando il prezzo oscilla vicino ai boundary. L'`ExecutionLoop` (line 162-175) sovrascrive `_current_regime` ad ogni tick senza smoothing. Il supervisor riceve contesti contraddittori.

**File:** `synthtrade/backend/app/scalping/engine/regime_detector.py` (115 righe)

**Implementazione:**
- Aggiungere `_pending_regime: Optional[str]` e `_pending_count: int`
- Regime committed cambia SOLO se lo stesso candidato si osserva per K candele consecutive (default K=3)
- Se il candidato cambia prima di K → reset counter
- Proprietà pubblica `pending_regime` per debug

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

**Status:** Pending — *pronto ma bloccato su query DB live*
**Priorità:** BASSA
**Dipendenze:** TASK-895 + query Supabase

**Prerequisito:** La pipeline dati è operativa (`trend_direction` salvato in `session_signal_log` su 5/6 path di logging). Manca solo la verifica che ci sono ≥20 trade chiusi con `signal_log_id` e `trend_direction` non null.

```sql
SELECT COUNT(*) FROM scalping_trades t
JOIN session_signal_log sl ON sl.id = t.signal_log_id
WHERE t.status = 'closed' AND sl.trend_direction IS NOT NULL;
```
Se ≥20 → il task può partire. Se <20 → aspettare.

**File da creare:** `docs/trend_analysis_report.md`

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
