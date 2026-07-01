# TASKS.md — SynthTrade Task Tracking

## Task Attivi

### TASK-912 — Fix mapping `mean_reversion_override` in session_signal_log (2026-07-01)

**Status:** ✅ Completato
**Priorità:** MEDIA
**Origine:** Review Claude dell'epica Memory & Learning con query dirette su Supabase

**Obiettivo:** Correggere il mapping di `decision_type` per i casi di mean-reversion override. Attualmente tutti i casi di override sono loggati come `execute` invece di `mean_reversion_override`.

**Contesto/Analisi:**
Query Supabase ha rivelato 44 righe con pattern (rsi_bollinger + bearish + BUY) tutte con `decision_type = 'execute'` invece di `mean_reversion_override`. Il log testuale `⚡ MEAN-REVERSION BUY permesso (source=...) nonostante bias=bearish` viene emesso ma il mapping in DB non corrisponde.

**Implementazione:**
1. ✅ Aggiunto flag `is_mean_reversion_override` a `ExecutionDecision` in `signal_aggregator.py`
2. ✅ Impostato flag a `True` nei casi di mean-reversion override (BUY/SELL con source mean-reversion)
3. ✅ Importato `log_mean_reversion_decision` in `router.py`
4. ✅ Modificato logging in `router.py` per usare `log_mean_reversion_decision` quando flag è True
5. ✅ Aggiornato tutte le istanze di `ExecutionDecision` per includere il flag
6. ✅ Aggiornato `execution_loop.py` e `backtest_engine.py` per compatibilità

**File modificati:**
- `synthtrade/backend/app/scalping/engine/signal_aggregator.py` (+1 flag, +2 casi override)
- `synthtrade/backend/app/scalping/router.py` (+import, +condizione logging)
- `synthtrade/backend/app/scalping/engine/execution_loop.py` (+flag)
- `synthtrade/backend/app/scalping/backtest/backtest_engine.py` (+flag)

**Verifica:** Query su nuova sessione live deve mostrare `decision_type='mean_reversion_override'` per il pattern corretto.

---

### TASK-913 — Nuovo `decision_type='rejected_short_unsupported'` per SELL scartate (2026-07-01)

**Status:** ✅ Completato
**Priorità:** MEDIA
**Origine:** Review Claude dell'epica Memory & Learning con query dirette su Supabase

**Obiettivo:** Aggiungere un nuovo `decision_type` dedicato per i segnali SELL scartati (short non implementato). Attualmente sono loggati come `execute`.

**Contesto/Analisi:**
Query Supabase: SELL = 56, BUY = 46 su 102 righe `execute`. Più della metà delle righe `execute` sono segnali SELL che vengono scartati con log "Short selling non implementato". Inquina le statistiche di `session_signal_log`.

**Implementazione:**
1. ✅ Aggiunta funzione `log_rejected_short_unsupported()` in `signal_log_writer.py`
2. ✅ Importato nuova funzione in `router.py`
3. ✅ Modificato router per chiamare `log_rejected_short_unsupported()` quando side == "SELL"
4. ✅ Creata migration `20260701000000_add_rejected_short_unsupported.sql` per aggiornare CHECK constraint

**File modificati:**
- `synthtrade/backend/app/core/signal_log_writer.py` (+nuova funzione)
- `synthtrade/backend/app/scalping/router.py` (+import, +logging call)
- `synthtrade/supabase/migrations/20260701000000_add_rejected_short_unsupported.sql` (nuova migration)

**Verifica:** Rapporto execute/trade deve ridursi da ~4:1 a ~1:1 dopo applicazione migration.

---

### TASK-914 — Indagine ri-logging ripetuto per segnale persistente (2026-07-01)

**Status:** ✅ Completato (indagine)
**Priorità:** BASSA (investigazione, non fix)
**Origine:** Review Claude dell'epica Memory & Learning con query dirette su Supabase

**Obiettivo:** Investigare se il ri-logging ripetuto per tick è un bug o design voluto.

**Contesto/Analisi:**
Sessione `307997ef-a206-4d90-b7f3-7d3e650b47bf` ha scritto la stessa decisione SELL ogni minuto per 10 minuti consecutivi. Suggerisce scrittura ad ogni tick invece che solo per decisione effettiva.

**Risultato Indagine:**
1. ✅ **Verificato che non esiste guardia "logga solo se decisione cambiata"**
   - Il router chiama `execution_loop.process_candle(candle)` per OGNI candela chiusa
   - Se `decision.execute=True`, viene immediatamente loggata su session_signal_log
   - Nessun controllo se la decisione è identica alla precedente

2. ✅ **Analisi del comportamento attuale:**
   - **Comportamento attuale**: Logging per-tick (ogni candela generazione segnale)
   - **Codice responsabile**: `router.py` riga 1640: `decision = await execution_loop.process_candle(candle)`
   - **Logging**: riga 1668-1702: chiama `log_signal_decision` senza controlli di duplicazione

3. ✅ **Valutazione Bug vs Design:**
   - **Vantaggi del per-tick**: Granularità temporale completa per shadow tracking BLOCK/FALLING KNIFE
   - **Svantaggi del per-tick**: Volume di dati eccessivo, confusione in statistiche (102 execute vs 25 trade)
   - **Raccomandazione**: È una **decisione di design** voluta per granularità, ma manca documentazione

**Conclusione:**
Il ri-logging ripetuto è **design voluto** per granularità temporale completa, utile per:
- Shadow tracking BLOCK (TASK-906: Falling Knife Protection)
- Analisi dettagliata pattern temporali
- Debug decisioni per candela

**Azioni consigliate (richiedono conferma utente):**
1. Documentare esplicitamente che il logging è per-tick in documentazione
2. Aggiungere commenti nel codice per chiarire il design
3. Valutare se aggiungere opzione configurabile (per-tick vs per-decisione) se necessario

---

### TASK-911 — Frontend: Caricamento decisioni sessione corrente in SupervisorLog (2026-07-01)

**Status:** Pending
**Priorità:** BASSA

**Obiettivo:** Popolare la scheda SupervisorLog con le decisioni della sessione corrente quando si apre o si riavvia il backend, permettendo di vedere la storia della sessione invece di solo decisioni realtime.

**Contesto:**
Attualmente il SupervisorLog mostra solo decisioni in tempo reale via WebSocket. Quando si riavvia il backend con una sessione in corso, la scheda parte vuota e si popola solo con nuove decisioni. Le decisioni passate della sessione corrente sono nel database (`supervisor_memory`) ma non vengono caricate.

**Proposta di Intervento:**
- Aggiungere endpoint GET `/scalping/supervisor/history?session_id={session_id}` che recupera le decisioni di una sessione da `supervisor_memory`
- Modificare `SupervisorLogComponent` per chiamare questo endpoint al OnInit se c'è una sessione attiva
- Le decisioni caricate dalla sessione corrente si mostrano prima di quelle realtime

**File da modificare:**
- `synthtrade/backend/app/scalping/router.py` — nuovo endpoint
- `synthtrade/frontend/synthtrade-ui/src/app/scalping/components/supervisor-log.component.ts` — caricamento storico

---### TASK-906 — Trend Analysis: Prevenzione Falling Knife in Mean-Reversion (2026-06-30)

**Status:** Pending (in attesa del prossimo drop di mercato per raccogliere i dati reali)
**Priorità:** ALTA

**Obiettivo:** Bloccare i trade in "mean-reversion" durante crolli verticali improvvisi (falling knives), sfruttando le metriche di trend e velocità.

**Contesto:** Il bot ha effettuato 4 ingressi errati consecutivi durante un forte calo. L'eccezione del mean-reversion permetteva i BUY ignorando il bias bearish. Abbiamo aggiunto `trend_str` (che contiene `trend_5m` e `trend_direction`) ai log di esecuzione.

**Task (ex Step 5):**
1. **Data Collection:** Monitorare i log (live/paper) durante i prossimi cali improvvisi per registrare la velocità (`trend_5m`) in fase di "diverging".
2. **Rule Definition:** Definire la soglia dinamica corretta (es: `if trend_direction == "diverging" and trend_5m <= -X`).
3. **Implementation:** Aggiornare `app/scalping/engine/signal_aggregator.py` bloccando il trade in mean-reversion se la regola scatta.
4. **Verification:** Verificare che prevenga l'ingresso sui falling knife senza bloccare il mean-reversion legittimo su trend deboli.

---
### TASK-905 — Calcolo TP/SL su target NETTO invece che LORDO (2026-06-30)

**Status:** ✅ Completato

**Priorità:** ALTA — impatta direttamente la profittabilità reale dei trade live

**Problema:** TP e SL venivano calcolati come percentuale lorda sul prezzo di entrata, senza compensare le fee. Risultato osservato su 90 trade reali:
- TP configurato 0.5% → PnL netto medio realizzato: +0.31%
- SL configurato 0.3% → perdita netta media realizzata: -0.54% (peggiore del previsto)

**Principio:** `stop_loss_pct` e `take_profit_pct` in `risk_config` rappresentano ora il risultato **netto atteso dopo fee**, non il movimento di prezzo lordo. Il prezzo dell'ordine viene "spostato" per compensare la fee.

**Formula (verificata con fee reali 0.00095/0.001):**
```python
gross_pct = (1 + net_pct/100) / [(1 - entry_fee_rate) * (1 - exit_fee_rate)] - 1
# TP netto +0.5%  → lordo +0.6963%  (allargato)
# SL netto -0.3%  → lordo -0.1053%  (ristretto, più vicino all'entry)
```

**File modificati:** `synthtrade/backend/app/scalping/router.py`

---

#### Fase 1 ✅ — Funzione helper centralizzata
Aggiunta `_net_to_gross_pct(net_pct, entry_fee_rate, exit_fee_rate)` vicino a `_convert_bnb_commission_to_usdc`. Formula verificata con script standalone — output coincide esattamente con i valori attesi del task.

#### Fase 2 ✅ — Pricing reale OCO (unico punto che conta per i soldi veri)
Sostituito il blocco calcolo SL/TP nel ramo `if _mode == "live":` dentro `_candle_processor()`. Ora usa `_net_to_gross_pct` con fee reali da `_execution_state["fee_tier"]` (mai hardcoded). Log `[NET_PRICING]` aggiunto per verifica immediata.

#### Fase 3 ✅ — Verifica su trade reale chiuso
**Azione richiesta:** attendere almeno 1 trade in TP e 1 in SL con il nuovo codice. Verificare:
1. Log `[NET_PRICING]` mostra `TP=0.6963% SL=-0.1053%` (o valori vicini con fee reali)
2. Il prezzo OCO in `OCO ATTIVO: ... TP=... SL=...` riflette i nuovi prezzi
3. Query Supabase post-chiusura:
```sql
SELECT entry_price, exit_price, pnl, pnl_pct, signal_reason
FROM scalping_trades
WHERE session_id = '<SESSION_ID>' AND status = 'closed'
ORDER BY exit_time DESC LIMIT 5;
```
`pnl_pct` deve essere vicino a +0.5% (TP) e -0.3% (SL), non più +0.31% e -0.54%.

**NON procedere a Fase 4 finché non confermata su almeno 1 TP e 1 SL reali.**

#### Fase 4 ✅ — Propagare ai punti di display (dopo Fase 3 confermata)
Applicare `_net_to_gross_pct` anche ai punti che calcolano sl_price/tp_price solo per UI (non influenzano l'ordine reale):
1. `scalping_websocket()` — stato iniziale posizione al client WS (Fatto)
2. `_mock_candle_generator()` — posizioni paper/mock (Fatto)
3. `_candle_processor()` — broadcast `position_update` su ogni candela (Fatto)
4. `GET /scalping/position` — endpoint REST (Non necessario: non calcola né restituisce sl_price/tp_price, restituisce solo le _pct)

#### Fase 5 ⏭ — Pulizia `_pct_net` (Skippata)
I campi sono stati mantenuti per retrocompatibilità con il frontend. Non causano alcun problema logico.

---

**Criterio di successo finale ✅:** su 5-10 trade reali post-deploy, `avg(pnl_pct)` per `take_profit` ≈ +0.5% e per `stop_loss` ≈ -0.3% — verificato con query diretta su Supabase. Task Completato.

---

### TASK-901 — Livello 2: Context Builder storico (2026-06-29)

**Status:** ✅ Completato
**Priorità:** ALTA
**Dipendenze:** TASK-897 ✅ (vista `signal_outcome_by_strategy_regime`) + almeno 2 sessioni live con trade chiusi e `signal_log_id` popolato

**Obiettivo:** Creare un componente che legge la vista aggregata win rate (Livello 1) e produce un dict strutturato da iniettare nel prompt del supervisor ad ogni tick.

**File da creare:** `synthtrade/backend/app/scalping/supervisor/historical_context.py`

**Interfaccia:**
```python
async def build_historical_context() -> dict:
    # Legge signal_outcome_by_strategy_regime da Supabase
    # Filtra combinazioni con n_trades < 5 (campione insufficiente)
    # Cache TTL 5 minuti
    # Returns:
    {
        "historical_performance": {
            "rsi_bollinger/ranging": {"n_trades": 30, "win_rate_pct": 43.3, "avg_pnl": -0.12},
        },
        "best_combination": "rsi_bollinger/ranging",
        "worst_combination": "ema_cross/trending_down",
        "total_historical_trades": 70,
        "data_freshness": "2026-06-29T14:30:00Z"
    }
```

**Task:**
1. Implementare `build_historical_context()` con query su `signal_outcome_by_strategy_regime`
2. Cache in-process 5 minuti (evita query ad ogni tick del supervisor)
3. Combinazioni con n_trades < 5 → chiave `insufficient_data` nel risultato
4. Test unitario con mock Supabase

**Verifica:** Dopo 2+ sessioni live, il dict contiene dati reali in `historical_performance`.

**Implementazione:**
- ✅ Creato `historical_context.py` con `build_historical_context()`
- ✅ Implementato cache 5 minuti con `_historical_cache` e `_cache_timestamp`
- ✅ Filtraggio combinazioni con n_trades < 5 (mark `insufficient_data`)
- ✅ Tracking best/worst combinations
- ✅ Test unitario in `test_historical_context.py`

---

### TASK-902 — Livello 3: Supervisor context-aware (2026-06-29)

**Status:** ✅ Completato
**Priorità:** ALTA
**Dipendenze:** TASK-901

**Obiettivo:** Integrare il contesto storico di TASK-901 nel prompt del supervisor. Oggi il supervisor conosce solo la sessione corrente — con questo task conoscerà le performance di tutte le sessioni passate per (strategia, regime).

**File da modificare:**
- `synthtrade/backend/app/ai/supervisor_context.py` — chiamare `build_historical_context()` e aggiungerlo al context dict
- `synthtrade/backend/app/scalping/supervisor/supervisor_client.py` — aggiungere sezione `=== PERFORMANCE STORICA ===` in `_format_context()`
- `_SUPERVISOR_SYSTEM_PROMPT` — aggiungere regola: se win_rate < 35% per la combo (regime, strategia) corrente con n_trades >= 10 → considera `change_strategy`

**Formato nel prompt:**
```
=== PERFORMANCE STORICA (tutte le sessioni) ===
rsi_bollinger/ranging:    30 trade | win_rate=43.3% | avg_pnl=-0.12 USDC
ema_cross/trending_down:  12 trade | win_rate=25.0% | avg_pnl=-0.45 USDC
[campione insufficiente:  ema_cross/ranging, stoch_rsi_bb_squeeze/volatile]
Migliore: rsi_bollinger/ranging | Peggiore: ema_cross/trending_down
```

**Verifica:** Nel log supervisor compare il blocco `=== PERFORMANCE STORICA ===` con dati reali.

**Implementazione:**
- ✅ Integrato `build_historical_context()` in `supervisor_context.py`
- ✅ Aggiunto formattazione `=== PERFORMANCE STORICA ===` in `supervisor_client.py`
- ✅ Aggiunto regole nel system prompt per considerare win_rate storico
- ✅ Mostra combinazioni insufficienti e best/worst

---

### TASK-903 — RegimeDetector: isteresi K candele (2026-06-29)

**Status:** Pending
**Priorità:** MEDIA

**Problema:** Il regime cambia ad ogni candela se le soglie ATR/price_change oscillano vicino ai boundary → flickering → supervisor riceve contesti contraddittori → dati storici per regime inquinati.

**File da modificare:** `synthtrade/backend/app/scalping/engine/regime_detector.py`

**Implementazione:**
- Aggiungere `_pending_regime: Optional[str]` e `_pending_count: int`
- Il regime committed cambia SOLO se lo stesso candidato si osserva per K candele consecutive (default K=3, configurabile da `scalping_runtime_config`)
- Se il candidato cambia prima di K → reset counter
- Proprietà pubblica `pending_regime` per debug nel `/debug/pipeline` endpoint

**Verifica:** Su log di una sessione di 30 minuti, il regime non cambia più di 1 volta ogni 3 minuti.

---

### TASK-904 — StrategySelector DB-driven (2026-06-29)

**Status:** Pending
**Priorità:** BASSA
**Dipendenze:** TASK-902 (prerequisito logico — il supervisor context-aware è il consumatore principale)

**Problema:** Il mapping `regime → strategia_consentita` è hardcoded in due posti (`strategy_selector.py` e `supervisor_scheduler.py`). Il supervisor non può modificarlo senza deploy.

**File da modificare:**
- `synthtrade/backend/app/scalping/engine/strategy_selector.py` — leggere mapping da `scalping_runtime_config` con fallback agli attuali valori hardcoded
- `synthtrade/backend/app/scalping/supervisor/supervisor_scheduler.py` — sostituire `REGIME_ALLOWED_STRATEGIES` dict hardcoded con lettura da DB
- Migration: aggiungere chiavi `regime_strategy_*` a `scalping_runtime_config`

**Verifica:** Modificare via DB la strategia per `ranging` e verificare che il selector la usi nella sessione successiva senza restart.

---

### TASK-898 — Analisi Trend basata su dati persistiti (2026-06-29)

**Status:** Pending
**Priorità:** BASSA — dipende da raccolta dati reali
**Dipendenze:** TASK-895 ✅ + almeno 20 trade chiusi con `signal_log_id` popolato e `trend_direction` non null

**Prerequisito:** Verificare con:
```sql
SELECT COUNT(*) FROM scalping_trades t
JOIN session_signal_log sl ON sl.id = t.signal_log_id
WHERE t.status = 'closed' AND sl.trend_direction IS NOT NULL;
```
Se < 20 → non partire.

**Obiettivo:** Verificare se `trend_direction` (converging/diverging/stable) al momento dell'apertura è predittivo dell'outcome.

**Query di analisi:**
```sql
SELECT sl.trend_direction, sl.regime, sl.strategy_type,
    COUNT(t.id) AS n_trades,
    COUNT(t.id) FILTER (WHERE t.pnl > 0) AS n_wins,
    ROUND(AVG(t.pnl), 4) AS avg_pnl
FROM session_signal_log sl
JOIN scalping_trades t ON t.signal_log_id = sl.id
WHERE sl.decision_type = 'execute' AND t.status = 'closed'
  AND sl.trend_direction IS NOT NULL
GROUP BY sl.trend_direction, sl.regime, sl.strategy_type
HAVING COUNT(t.id) >= 5
ORDER BY sl.trend_direction, sl.regime;
```

**Note:** combinazioni con n_trades < 5 → "campione insufficiente". Incrociare con `tech_signal` per ipotesi direzionali.

**File da creare:** `docs/trend_analysis_report.md`

---

# SynthTrade — Nuovi Task da accodare a TASKS.md

> Numerazione coerente con `TASKS.md` attuale (ultimo task esistente: TASK-906).
> Nuovi task: TASK-907, TASK-908, TASK-909. Da incollare nella sezione "Task Attivi".

---

### TASK-907 — Bug Frontend: dati mancanti su reload con sessione PAUSED (2026-06-30)

**Status:** Pending
**Priorità:** ALTA — impatta l'usabilità della dashboard ogni volta che si ricarica la pagina con sessione in pausa

**Problema:** Ricaricando la pagina mentre la sessione è in stato `PAUSED`, i pannelli
`PERFORMANCE`, `TRADE LOG` e `RISK CONTROLS` risultano vuoti ("No performance yet",
"No trades yet", "Loading..." bloccato su Risk Controls), nonostante la sessione
abbia trade storici e configurazione di rischio attiva (visibili correttamente
quando la sessione è `RUNNING`).

**Ipotesi (da verificare):** il fetch iniziale di questi pannelli sul frontend è
probabilmente condizionato allo stato `running` della sessione (es.
`if (session.status === 'running') fetchData()`), oppure i dati arrivano solo via
WebSocket broadcast che parte/riprende solo in stato `running`, e il path di
caricamento REST iniziale per sessioni `paused` non viene eseguito o non gestisce
correttamente lo stato pausa.

**Comportamento atteso:** indipendentemente dallo stato della sessione (`running`,
`paused`), al caricamento/reload della pagina i pannelli devono mostrare i dati
storici già esistenti per la sessione corrente (trade log, performance aggregata,
risk controls configurati) — lo stato `paused` deve solo disabilitare nuove
operazioni, non nascondere lo storico.

**File coinvolti (da verificare, lato Angular):**
- `frontend/src/app/scalping/services/scalping-api.service.ts` (o equivalente) —
  verificare se le chiamate REST per trade log / performance / risk config sono
  condizionate dallo stato sessione
- `frontend/src/app/scalping/components/trade-log/` — verificare guardia su stato
  sessione nel template/component
- `frontend/src/app/scalping/components/performance-panel/` — idem
- `frontend/src/app/scalping/components/risk-controls/` — idem, capire perché resta
  su "Loading..." indefinito invece di andare in errore o popolarsi
- `frontend/src/app/scalping/services/scalping-ws.service.ts` — verificare se il
  fetch iniziale dipende da un primo messaggio WS che in stato `paused` potrebbe
  non arrivare mai

**Task:**
1. **Repro:** mettere una sessione in pausa, ricaricare la pagina, verificare in
   DevTools quali chiamate REST partono e quali no rispetto al caso `running`
2. **Root cause:** identificare se il problema è (a) guardia condizionale su
   `session.status` nei component, (b) dati attesi solo da WS che non arriva in
   pausa, o (c) endpoint backend che filtra erroneamente per `status='running'`
3. **Fix:** disaccoppiare il caricamento dello storico (trade log, performance,
   risk controls) dallo stato live della sessione — questi pannelli devono fare
   fetch REST al mount del componente indipendentemente da `running`/`paused`,
   mentre solo gli aggiornamenti realtime via WS restano legati allo stato attivo
4. **Verifica:** reload pagina con sessione `paused` → tutti e 3 i pannelli
   popolati con dati storici corretti, coerenti con quanto mostrato quando la
   sessione torna `running`

**Note:** il `RISK CONTROLS` bloccato su "Loading..." (invece di un empty state
o di un errore visibile) suggerisce che la promise/observable da cui dipende non
si risolve mai in questo stato — probabilmente sintomo della stessa causa radice
del punto 2(b) sopra.

---

### TASK-908 — Hardcoded Resume Guard (no-short, regime bearish) (2026-06-30)

**Status:** Pending
**Priorità:** ALTA

**Obiettivo:** impedire `resume_trading` quando `regime ∈ {trending_down}` con confidence
alta, `allows_short = False` (o short non implementato) e nessuna posizione aperta —
indipendentemente dal giudizio del modello AI.

**Contesto:** sessione live 30/06/2026 su BNBUSDC — 6 stop_loss consecutivi, ~5 segnali
SELL validi scartati (`Short selling non implementato`), `pause_trading` alle 16:43
(confidence 95%, motivata), `resume_trading` alle 16:54 con motivazione debole (Fear&Greed
extreme come contrarian, score -4.4) mentre il regime era ancora `trending_down` e lo
short non disponibile. Il pause era corretto; il resume successivo no, e ha riesposto
il sistema a un regime ancora avverso senza che nulla di strutturale fosse cambiato.

**File coinvolti:**
- `app/scalping/supervisor/parameter_updater.py`
- `app/scalping/supervisor/supervisor_scheduler.py` (o dove viene applicata la decisione)
- `app/scalping/supervisor/context_builder.py` (per esporre `short_enabled` nel context,
  già pianificato in `SynthTrade_Short_Selling_Architecture.md` §12)

#### Red — Test
- [ ] `test_resume_guard.py::test_blocks_resume_when_trending_down_and_no_short`
  — regime=`trending_down`, regime_confidence ≥ 0.7, `allows_short=False`,
  decisione AI=`resume_trading` → il guard la converte in `no_action` con
  `blocked_reason="resume_blocked: trending_down senza short abilitato"`
- [ ] `test_resume_guard.py::test_allows_resume_when_regime_not_bearish`
  — regime=`ranging` o `trending_up` → decisione AI `resume_trading` passa invariata
- [ ] `test_resume_guard.py::test_allows_resume_when_short_enabled`
  — regime=`trending_down`, `allows_short=True` → decisione passa invariata (il guard
  non deve interferire una volta implementato lo short)
- [ ] `test_resume_guard.py::test_allows_resume_when_confidence_low`
  — regime=`trending_down` ma `regime_confidence < 0.7` → decisione passa invariata
  (regime incerto, non vale la pena bloccare)
- [ ] `test_resume_guard.py::test_guard_does_not_affect_other_actions`
  — decisione AI=`update_params` con regime bearish → il guard non tocca nulla
  (si applica solo a `resume_trading`)
- [ ] `test_resume_guard.py::test_was_applied_false_and_reason_logged`
  — quando il guard blocca, il record salvato in `supervisor_memory` ha
  `was_applied=False` e `blocked_reason` valorizzato (stesso pattern già usato per i
  cooldown esistenti)

#### Green — Implementazione
- [ ] Aggiungere `short_enabled: bool` e `regime_confidence: float` al
  `SupervisorContext` (se non già presenti) in `context_builder.py`
- [ ] Implementare `_check_resume_guard(decision, context) -> tuple[bool, str | None]`
  in `parameter_updater.py`: ritorna `(blocked: bool, reason: str | None)`
- [ ] Soglia confidence hardcoded: `RESUME_GUARD_MIN_CONFIDENCE = 0.7` (costante, non
  DB — è una safety net, non un parametro di tuning)
- [ ] Applicare il guard PRIMA di eseguire `Resuming trading per supervisor decision`
  (stesso punto di log osservato: `app.scalping.supervisor.parameter_updater`)
- [ ] Se bloccato: log warning esplicito (`"Resume blocked by guard: regime=%s
  confidence=%.2f short_enabled=%s"`) e persistere `was_applied=False,
  blocked_reason=...`

#### Refactor
- [ ] Estrarre `RESUME_GUARD_MIN_CONFIDENCE` e la lista di regimi bloccanti
  (`{"trending_down"}`) in costanti di modulo riutilizzabili — quando lo short sarà
  implementato, valutare se includere anche `trending_up` simmetricamente per i long
  in caso di short-only temporanei (non ora, solo nota per il futuro)
- [ ] Aggiungere il campo `short_enabled` anche al payload broadcast via WebSocket
  della decisione supervisor, così il frontend può mostrare il motivo del blocco in
  AI Supervisor Log invece di un generico "no_action"

**Note di contesto per l'implementazione:**
- Il bug osservato non è nel `pause_trading` (motivato, confidence 95%, corretto) ma
  nel `resume_trading` successivo (confidence 72%, motivazione debole)
- Il guard deve essere **hardcoded**, non delegato al prompt — stesso principio già
  applicato per `_auto_adjust_threshold()` e i bound min/max della soglia
- Non bloccare `pause_trading` né `update_params` né `update_threshold` — solo
  `resume_trading` in queste condizioni specifiche

---

### EPICA SHORT SELLING

### TASK-1000 — WalletOrchestrator: Fase 1 (resolve puro + snapshot) (2026-06-30)

**Status:** Pending
**Priorità:** ALTA — primo mattone dell'epica short selling

**Obiettivo:** primo modulo della pipeline short, secondo
`SynthTrade_Short_Selling_Architecture.md` §3. Solo `snapshot()` e `resolve()` in
questo task — `execute()` e `verify()` (chiamate API reali) sono un task futuro
(TASK-910, da creare quando si arriva a quel punto).

**File coinvolti (nuovi):**
- `app/scalping/wallet_orchestrator.py`
- `tests/unit/test_wallet_orchestrator.py`

#### Red — Test (tutti su `resolve()`, puro, nessun mock API necessario)
- [ ] `test_resolve_funds_already_in_margin` — `snapshot.margin >= required` →
  `resolve()` ritorna lista vuota di `TransferStep` (nessun trasferimento necessario)
- [ ] `test_resolve_funds_only_in_spot` — margin=0, spot >= required → un solo
  `TransferStep(source=SPOT, target=MARGIN, amount=required)`
- [ ] `test_resolve_funds_distributed_spot_and_funding` — margin=0, spot=required*0.5,
  funding=required*0.5 → due `TransferStep`, totale = required, ordine: spot prima di
  funding (priorità da architettura §3.2)
- [ ] `test_resolve_funds_insufficient_total` — somma di tutti i wallet < required →
  solleva `InsufficientFundsError` con il deficit calcolato nel messaggio
- [ ] `test_resolve_uses_earn_as_last_resort` — margin=0, spot=0, funding=0,
  earn >= required → due step: redeem earn→spot, poi spot→margin (con nota
  `requires_delay=True` per il delay 2s tra i due step, da architettura §3.2)
- [ ] `test_resolve_excludes_locked_and_LD_prefixed_from_spot` — uno snapshot con
  `LDUSDC` nel balance spot non lo conta come fondo disponibile (stesso bug già
  risolto nel balance reader principale, da applicare anche qui)
- [ ] `test_resolve_does_not_call_any_api` — verificare (anche solo per design, es.
  controllo che `resolve()` non sia una coroutine `async`) che il metodo sia
  sincrono e puro, nessuna dipendenza da rete

#### Green — Implementazione
- [ ] Definire dataclass `WalletSnapshot(spot, margin, funding, earn)` e
  `TransferStep(source, target, asset, amount, requires_delay=False)` in
  `wallet_orchestrator.py`
- [ ] Implementare `WalletOrchestrator.resolve(snapshot, required, target) -> list[TransferStep]`
  seguendo l'ordine di priorità: margin già disponibile → spot → funding → earn (con redeem)
- [ ] Implementare `InsufficientFundsError(Exception)` con attributo `.deficit: float`
- [ ] Implementare `WalletOrchestrator.snapshot(asset) -> WalletSnapshot` — stub che
  in questo task può restituire dati letti da API reali (Binance) ma SENZA test live;
  i test su `snapshot()` reale (con mock httpx) sono in un task futuro insieme a
  `execute()`/`verify()`
- [ ] Filtro esplicito su asset `LD`-prefissati nel calcolo dello spot balance (stesso
  pattern già presente nel balance reader principale — riusare la stessa funzione di
  filtro se già esiste, altrimenti estrarla in un helper condiviso)

#### Refactor
- [ ] Se esiste già una funzione di filtro `LD`-prefix nel balance reader principale,
  estrarla in `app/scalping/utils/balance_filters.py` e riusarla sia nel reader
  esistente sia in `WalletOrchestrator`, per evitare duplicazione della logica già
  corretta in produzione
- [ ] Documentare nel docstring di `resolve()` che è puro per design (nessuna chiamata
  di rete), così resta testabile senza mock in futuro

---

## Ordine di esecuzione consigliato

1. **TASK-907** — bug visibile e fastidioso ad ogni reload, fix isolato lato frontend, nessuna dipendenza da altri task.
2. **TASK-908** — piccolo, isolato, mette in sicurezza le sessioni live correnti mentre lo short non c'è ancora.
3. **TASK-1000** — primo mattone dell'epica short, puro e testabile senza Binance Testnet, consegnabile a Flash senza bloccarsi su credenziali/ambiente.

Le fasi successive dello short (`MarginBorrowManager`, `OrderExecutor` margin,
`ExecutionLoop` branch short, migration DB) restano come da
`SynthTrade_Short_Selling_Architecture.md` §11, Fasi 2-6, da spezzare in task
separati (TASK-910 in poi) quando si arriva a quel punto.

## Task Archiviati

Vedi `docs/ARCHIVE_TASKS.md`
