# TASKS.md — SynthTrade Task Tracking

> **Aggiornato:** 2026-07-16 12:00. Task completati spostati in `docs/ARCHIVE_TASKS.md`.

---

## EPICA AUDIT POST-OKX — Task pending

**Status:** In corso (task completati spostati in ARCHIVE_TASKS.md)
**Priorità:** CRITICA
**Recap audit:** `docs/recap/2026-07-15_full-audit-recap.md`

### TASK-1166 — Refactor router.py: estrazione moduli

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

## TASK-1130/1131 — Reverted (riferimento)

### TASK-1130 — Fix: Missing _get_ccxt_symbol method in OkxExchangeAdapter

**Status:** ⚠️ REVERTED (2026-07-13)
**Priorità:** ALTA

Il sistema funziona con i fix precedenti (TASK-1126) e il fallback REST polling gestisce correttamente gli eventi.

### TASK-1131 — CCXT REST fallback per OKX EU accounts

**Status:** ⚠️ REVERTED (2026-07-13)
**Priorità:** CRITICA

Il fallback REST polling è operativo e gestisce gli eventi di fill senza errori critici. WS private failure (60032) non è bloccante.

---

## TASK-1116.G — Instrument discovery environment-aware (Demo vs Live)

**Status:** ✅ Committed (`HEAD` 16/07/2026)
**Priorità:** ALTA
**Effort:** 4 ore

**Sottotask completati:**
1. ✅ **1116.G.1** — Cache `(symbol, demo_flag)` in `okx_exchange.py`, header `x-simulated-trading` in `_direct_fetch_symbol_rules()` e `list_instruments()`
2. ✅ **1116.G.2** — Endpoint `/exchange/instruments` accetta `?mode=test|live`, passa header demo
3. ✅ **1116.G.3** — Validazione pre-sessione: `get_symbol_rules()` prima del balance check, errore `SYMBOL_NOT_AVAILABLE`
4. ✅ **1116.G.4** — Frontend: `getInstruments(mode?)` passa mode come query param, re-fetch su cambio mode
5. ✅ **1116.G.5** — Mode badge (DEMO/LIVE) con tooltip nei session controls
6. ✅ **1116.G.6** — 8 nuovi test unit (cache partition, demo header, list_instruments, symbol validation)

**File modificati:** `okx_exchange.py`, `router.py`, `exchange-symbols.service.ts`, `session-controls.component.ts`, `test_task_1116g.py`

---

## EPICA COLLECTOR INTELLIGENCE — Task pending

> Task completati (TASK-1159, 1170, 1171, 1172) spostati in `docs/ARCHIVE_TASKS.md`.

---

## Task pending (non OKX-specific)

### TASK-906 — Trend Analysis: Prevenzione Falling Knife in Mean-Reversion

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

### TASK-903 — RegimeDetector: isteresi K candele

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

### TASK-904 — StrategySelector DB-driven

**Status:** Pending
**Priorità:** BASSA
**Dipendenze:** TASK-902

**Problema:** Mapping `regime → strategia_consentita` hardcoded in due posti.

**File:**
- `strategy_selector.py` — leggere da `scalping_runtime_config`
- `supervisor_scheduler.py` — sostituire dict hardcoded con lettura da DB
- Migration: chiavi `regime_strategy_*` a `scalping_runtime_config`

---

### TASK-898 — Analisi Trend basata su dati persistiti

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

### TASK-907 — Bug Frontend: dati mancanti su reload con sessione PAUSED

**Status:** ✅ Implemented (16/07/2026)
**Priorità:** ALTA — fix 2 righe
**Effort:** 30 min

**Problema:** `trade-log.component.ts:97` e `performance-panel.component.ts:186` usano `else if (session.status === 'running')` — il branch `'paused'` non esiste. Risk controls funziona (fetch incondizionato).

**Fix identificato:** In entrambi i file, cambiare:
```typescript
} else if (session.status === 'running') {
```
in:
```typescript
} else if (session.status !== 'idle') {
```
Questo gestisce anche `'stopped'` per vedere storico dopo sessione finita.

---

### TASK-908 — Hardcoded Resume Guard (no-short, regime bearish)

**Status:** Riservato per analisi (richiesta Andrea 14/07/2026) — non implementare ora
**Priorità:** ALTA — *sospesa: da analizzare assieme a TASK-909*

**Obiettivo:** Impedire `resume_trading` quando regime bearish, confidence alta, `allows_short=False` e nessuna posizione aperta — indipendentemente dal giudizio AI.

**Stato attuale (analisi 15/07):** `_resume()` in `parameter_updater.py:177-185` è incondizionato — nessun check su regime/confidence/short. `short_enabled` non esiste nel codice (solo in arch docs). L'infrastruttura `was_applied`/`blocked_reason` in `supervisor_scheduler.py:299-345` è pronta ma nessun branch `resume_trading` la usa. Servono: (1) `_check_resume_guard()`, (2) esporre `short_enabled` nel context, (3) 6 test.

**Contesto:** Sessione live 30/06 — 6 stop_loss consecutivi, 5 segnali SELL scartati, `resume_trading` con motivazione debole mentre regime era ancora `trending_down`.

**File:**
- `parameter_updater.py`
- `supervisor_scheduler.py`
- `context_builder.py`

#### Red — Test
- [ ] `test_blocks_resume_when_trending_down_and_no_short`
- [ ] `test_allows_resume_when_regime_not_bearish`
- [ ] `test_allows_resume_when_short_enabled`
- [ ] `test_allows_resume_when_confidence_low`
- [ ] `test_guard_does_not_affect_other_actions`
- [ ] `test_was_applied_false_and_reason_logged`

#### Green — Implementazione
- [ ] `short_enabled: bool` e `regime_confidence: float` in `SupervisorContext`
- [ ] `_check_resume_guard(decision, context) -> tuple[bool, str | None]` in `parameter_updater.py`
- [ ] `RESUME_GUARD_MIN_CONFIDENCE = 0.7` (costante hardcoded)
- [ ] Applicare guard PRIMA di eseguire `Resuming trading`
- [ ] Se bloccato: log warning + persistere `was_applied=False, blocked_reason=...`

#### Refactor
- [ ] Costanti `RESUME_GUARD_MIN_CONFIDENCE` e `{"trending_down"}` in costanti di modulo
- [ ] Campo `short_enabled` nel payload broadcast WS decisione supervisor

---

## EPICA SHORT SELLING — Superseded

### TASK-1000 — WalletOrchestrator: Fase 1 (resolve puro + snapshot)

**Status:** Superseded by EPICA OKX (non avviare prima di TASK-1113)
**Priorità:** SOSPESA

**Nota:** Il modello Binance Margin non è più il percorso primario. OKX usa un modello diverso con Trading Account/tdMode. Da ripianificare dopo migrazione OKX.

**Riferimento:** `SynthTrade_Short_Selling_Architecture.md` §3, §11 Fasi 2-6.

### TASK-1173 — LiveChartComponent: prezzo non si aggiorna (Angular Change Detection)

**Status:** ✅ Implemented (15/07/2026)
**Priorità:** 🔴 ALTA
**Effort:** 30 min
**Dipendenze:** nessuna

**Problema:** Il prezzo nel live chart non si aggiorna mai all'avvio della pagina. Lo spinner resta "pending" indefinitamente. Il prezzo appare solo quando l'utente clicca sulla select dei simboli (anche senza cambiarlo).

**Root cause:** `LiveChartComponent` muta `lastPrice` e `loading` nei callback RxJS (WS e HTTP) ma **non triggera Angular Change Detection**. Il template usa `*ngIf="lastPrice > 0"` ma Angular non sa che la proprietà è cambiata.

Tutti gli altri componenti scalping (`position-ticker`, `trade-log`, `session-controls`, `market-intel-panel`, ecc.) usano `cdr.detectChanges()` dopo ogni mutazione di stato da WS. `LiveChartComponent` era l'unico senza.

**Perché il click sulla select funziona:** Ogni DOM event (click) entra nella Angular zone → zone.js triggera change detection → Angular legge `lastPrice` già aggiornato e lo renderizza.

**Fix:** Iniettare `ChangeDetectorRef`, chiamare `this.cdr.detectChanges()` dopo ogni mutazione:
1. `switchMap` body — dopo `this.loading = true` + `this.lastPrice = 0`
2. `finalize` callback — dopo `this.loading = false`
3. `_applyCandles()` — dopo `this.lastPrice = chartData[...]`
4. `_subscribeToWsCandles()` — dopo `this.lastPrice = candle.close`

**File modificati:**
- `synthtrade/frontend/synthtrade-ui/src/app/scalping/components/live-chart.component.ts`

---

### TASK-1174 — Fix P1: get_symbol_rules failure silently skips restore reconcile

**Status:** ✅ Implemented (16/07/2026)
**Priorità:** 🔴 ALTA
**Effort:** 15 min
**Dipendenze:** commit precedente (restore reconcile post-WS)

**Problema:** Nel blocco restore di `_start_ws_broadcast`, il pre-check holdings + `get_symbol_rules` era nello stesso try/except. Se `get_symbol_rules` falliva (timeout, rate limit), `min_qty` non veniva assegnato → `NameError` → l'intera riconciliazione veniva silenziosamente saltata. La posizione restava in memoria come "aperta" anche se chiusa su exchange.

**Fix:** Rimosso il pre-check ridondante. Il blocco restore delega interamente a `_reconcile_position_with_exchange` che gestisce internamente: fallback holdings→balance, `get_symbol_rules` con fallback, e retry su algo history.

**File modificati:**
- `synthtrade/backend/app/scalping/router.py` (blocco restore in `_start_ws_broadcast`)

---

### TASK-1175 — Fix P1: Algo history retry si blocca su risultati vuoti

**Status:** ✅ Implemented (16/07/2026)
**Priorità:** 🔴 ALTA
**Effort:** 15 min
**Dipendenze:** commit precedente (restore reconcile)

**Problema:** Nella fallback di `_reconcile_position_with_exchange`, quando `get_algo_orders_history` restituiva dati ma senza match per il bracket_id, il `break` usciva dal ciclo di retry al primo tentativo. Se OKX non aveva ancora propagato il fill (1-5s), il prezzo veniva perso.

**Fix:** Il ciclo di retry ora esegue sempre 3 tentativi con delay di 1.5s tra uno e l'altro. Il `break` viene eseguito solo quando il fill è stato trovato. Se dopo 3 tentativi non c'è match, viene loggato un warning.

**File modificati:**
- `synthtrade/backend/app/scalping/router.py` (fallback algo history in `_reconcile_position_with_exchange`)

---

### TASK-1176 — Fix P2: Adapter init failure durante restore loggato a error level

**Status:** ✅ Implemented (16/07/2026)
**Priorità:** 🟡 MEDIA
**Effort:** 5 min
**Dipendenze:** commit precedente (restore reconcile)

**Problema:** Se `build_exchange_adapter()` falliva durante il restore, l'eccezione veniva loggata solo come `warning`. Per una sessione live trading, un fallimento dell'adapter è critico e deve essere visibile nei log a livello `error`.

**Fix:** Cambiato `logger.warning` → `logger.error` con `exc_info=True` per avere il traceback completo.

**File modificati:**
- `synthtrade/backend/app/main.py` (blocco adapter init in `_restore_scalping_session`)

### TASK-1177 — Reconcile fill reali + bug critico supabase stub

**Status:** ✅ Implemented (16/07/2026)
**Priorità:** 🔴 CRITICA
**Effort stimato:** 2 ore
**Dipendenze:** TASK-1160, TASK-1174

**Problemi:**
1. Reconcile usava ticker price come approssimazione del fill (non il fill reale di OKX) → PnL sbagliato
2. `supabase/` test stub alla root oscurava il pacchetto `supabase` reale → `get_supabase()` restituiva `_DummyClient` → DB mai letto/scritto
3. Trade log mostrava 4 entry duplicate con dati misti

**Fix:**
- `router.py:167-231`: Reconcile ora fetcha fill reali da OKX (`/api/v5/trade/fills`), matcha per `bracket_id` oppure per `exit_side`. Rimosso ticker approximation.
- Rinominato `supabase/` → `_supabase_test_stub/`
- Trade log ripulito con dati OKX reali (2 trade chiusi con PnL=-0.24 ciascuno, 1 aperto)

**File coinvolti:**
- `synthtrade/backend/app/scalping/router.py` (lines 167-231)
- `_supabase_test_stub/__init__.py` (rinominato)

**Acceptance Criteria:**
- Trade log mostra 2 trade chiusi con fill price reale OKX ✅
- `get_supabase()` restituisce `SyncClient` reale ✅
- `python -m py_compile synthtrade/backend/app/scalping/router.py` OK ✅
- Recap: `docs/recap/2026-07-16_reconcile-fix.md` ✅

**Note:**
- L'endpoint `/api/v5/trade/fills` non restituisce `algoId` per ordini OCO/bracket → il matching per bracket_id non funziona. Usare matching per `exit_side`
- `get_supabase()` usa `lru_cache` — DummyClient una volta cachato resta per tutta la sessione

---

## Task da Investigare — Aperti/Parziali

> Da `MASTER_RECAP.md` 26/06/2026. Verifica 01/07/2026. Aggiornato 16/07/2026.

| Task | Status | Note |
|------|--------|------|
| TASK-INVEST-011 — Regime misclassification (volume-confirmed) | 🟡 APERTO | Nessuna logica volume-confirmed in `regime_detector.py` |
| TASK-INVEST-012 — Falling Knife Protection | 🟡 APERTO | Allineata a TASK-906 (in attesa dati reali) |
| TASK-INVEST-013 — trend_direction troppo sensibile | ⚠️ PARZIALE | Codice presente ma soglia troppo sensibile |
| TASK-INVEST-017 — Bias outcome_label Supervisor | ⚠️ PARZIALE | Usa solo PnL (no bias regime) |
| TASK-INVEST-018 — Soglia dinamica senza decadimento | ⚠️ PARZIALE | Decay/degradation non implementato |
| TASK-INVEST-020 — Slope filter su EMA Cross | 🟡 APERTO | Nessuno slope filter in `ema_cross.py` |

**Nota:** TASK-INVEST-019 (5/8 collector non funzionanti) è ora risolto con provider-aware collectors (TASK-1153).
