# TASKS.md — SynthTrade Task Tracking

## Task Attivi

### TASK-910 — Arricchimento contesto in `supervisor_memory.market_context` (2026-06-30)

**Status:** ✅ Completato
**Priorità:** ALTA

**Obiettivo:** Salvare lo snapshot completo del mercato (funding, cvd, fear/greed, pattern tecnici) all'interno del campo JSON `market_context` della tabella `supervisor_memory` per permettere l'apprendimento a posteriori dell'AI.

**Contesto/Analisi:**
Il modulo `router.py` sta già popolando correttamente tutti i campi estesi (macro e tecnici) sulla tabella `scalping_trades`. Tuttavia, le *decisioni* prese dal Supervisor vengono salvate in `supervisor_memory` tramite la funzione `_save_decision_to_memory` in `supervisor_scheduler.py`. Al momento, questa funzione registra un dizionario molto povero: `{"regime": regime_name}`. Di conseguenza, decisioni critiche come `pause_trading` (che non generano alcun trade su `scalping_trades`) rimangono orfane del contesto di mercato in cui sono state prese, rendendo impossibile capire a posteriori se l'AI ha stoppato il trading per un reale pericolo (es. CVD in caduta e pattern Bearish Engulfing) o per un falso allarme.

**Piano di Intervento:**
1. Modificare la firma della funzione `_save_decision_to_memory` in `supervisor_scheduler.py` per accettare gli argomenti opzionali `snapshot`, `score`, `ta_patterns` e `vol_anomaly`.
2. Aggiornare le chiamate a questa funzione all'interno del metodo `_tick()`, passandole variabili che vengono già calcolate un attimo prima di chiamare il client AI.
3. Arricchire il dizionario `market_context` prima di inviarlo al database (es. `market_context["cvd_trend"] = snapshot.cvd_trend`, `market_context["ta_patterns"] = ta_patterns`, `market_context["score"] = score.total_score`).
4. Nessuna modifica lato database (Supabase) è richiesta, poiché la colonna `market_context` è di tipo JSONB e accetta struttura dati arbitraria.

---

### TASK-907 — Fix Falso positivo `tasks_alive` e watchdog WS (2026-06-30)

**Status:** ✅ Completato
**Priorità:** ALTA

**Obiettivo:** Risolvere il fallimento perpetuo del job `session_health_job` e garantire il corretto riavvio di tutti i task dipendenti dal WebSocket dopo la ripresa dallo standby.

**Contesto/Analisi:**
Attualmente, il watchdog rileva il blocco dei dati dal WebSocket e istanzia un nuovo `BinanceWSClient`. Tuttavia, il riavvio avviene *all'interno* del solo task di lettura delle candele (`candle_task`). Quando il watchdog chiama `client.stop()`, chiude le code usate dagli altri stream (trade e user data), causando la morte irreversibile di `trade_task` (che calcola il CVD) e `user_data_task`. Il `candle_task` prosegue col nuovo client, ma gli altri task rimangono in stato "dead" in `_execution_state["ws_tasks"]`, facendo fallire perennemente il check `tasks_alive` e interrompendo funzionalità critiche.

**Proposta di Intervento:**
- Non sostituire il `client` a caldo dentro un singolo task.
- Il watchdog deve segnalare alla sessione di fare un restart completo della connessione WebSocket.
- La logica di restart deve cancellare esplicitamente tutti i vecchi task, istanziare il nuovo client, e ri-spawnare tutti i task di ricezione (richiamando `_start_ws_broadcast` in modo pulito).

---

### TASK-908 — Fix troncamento log eccezioni CCXT in ExchangeOrderError (2026-06-30)

**Status:** ✅ Completato
**Priorità:** MEDIA

**Obiettivo:** Garantire che il dettaglio dell'errore (il body restituito da Binance, es. `MIN_NOTIONAL` o `Insufficient balance`) sia correttamente visibile nei log e trasmesso alla UI, completando il fix precedente.

**Contesto/Analisi:**
Il fix applicato in `router.py` (controllo `isinstance(live_e, ccxt.BaseError)`) fallisce sempre. Il motivo è che in `exchange.py` tutte le eccezioni CCXT vengono catturate e ri-lanciate avvolte in `ExchangeOrderError(str(e))`. L'invocazione di `str(e)` su un'eccezione CCXT tronca il messaggio reale al solo header dell'errore. Di conseguenza, il blocco in `router.py` gestisce un `ExchangeOrderError` generico loggando solo "Live trade failed: ExchangeOrderError: binance POST...".

**Proposta di Intervento:**
- Modificare `exchange.py` per non nascondere il messaggio originale CCXT.
- Estrarre il body completo dell'eccezione prima di lanciare `ExchangeOrderError`, oppure usare `raise ExchangeOrderError(...) from e` per mantenere lo stack trace.
- Aggiornare `router.py` per leggere i dettagli (es. `e.args` o `e.response`) direttamente da `ExchangeOrderError` se quest'ultimo li incorpora.

**Implementazione:**
- ✅ Esteso `ExchangeOrderError` con `original_exception` e `original_details`
- ✅ Modificati tutti i punti di `raise ExchangeOrderError` in `exchange.py` per preservare dettagli originali
- ✅ Aggiornato `router.py` per estrarre `original_details` da `ExchangeOrderError`
- ✅ Sostituito controllo `isinstance(live_e, ccxt.BaseError)` con `isinstance(live_e, ExchangeOrderError)`

---

### TASK-909 — Isolamento chiamate AI sincrone per evitare blocco APScheduler (2026-06-30)

**Status:** ✅ Completato
**Priorità:** MEDIA

**Obiettivo:** Evitare che l'esecuzione di job AI ("supervisor_check_job") blocchi l'event loop e provochi ritardi a cascata ("missed jobs") negli altri scheduler.

**Contesto/Analisi:**
Il modulo APScheduler condivide lo stesso event loop principale. In `supervisor_scheduler.py`, la chiamata `run_once()` invoca il servizio AI in modo sincrono (`call_with_fallback`). Se questa richiesta di rete non è eseguita tramite un executor asincrono (es. `ThreadPoolExecutor` o `asyncio.to_thread`), congela l'event loop di FastAPI e di APScheduler per l'intera durata dell'elaborazione LLM (5-10 secondi). Al rilascio del loop, gli altri job accodati scattano in blocco in ritardo (misfire/missed).

**Proposta di Intervento:**
- Isolare l'invocazione alla libreria dell'LLM (dentro `supervisor_client.py` o `LLMModelService`) delegandola a un thread dedicato tramite `asyncio.to_thread(sync_llm_call)`.
- Verificare che tutte le chiamate di rete esterne nel modulo AI siano realmente non bloccanti o wrappate correttamente, permettendo al loop di continuare a emettere heartbeat e controllare la salute della sessione.

**Implementazione:**
- ✅ Modificato `supervisor_client.py` per usare `asyncio.to_thread()` con wrapper sincrono
- ✅ Il wrapper crea un event loop separato nel thread per eseguire la chiamata AI asincrona
- ✅ Questo evita che la chiamata AI blocchi l'event loop principale di APScheduler
- ✅ Aggiunto import `asyncio` per supportare la nuova implementazione

---

### TASK-906 — Trend Analysis: Prevenzione Falling Knife in Mean-Reversion (2026-06-30)

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

**Status:** Pending
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

---

### TASK-902 — Livello 3: Supervisor context-aware (2026-06-29)

**Status:** Pending
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

## Task Archiviati

Vedi `docs/ARCHIVE_TASKS.md`
