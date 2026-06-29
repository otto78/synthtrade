# TASKS.md — SynthTrade Task Tracking

## Active Tasks

### TASK-892 — Decision Context Extractor (2026-06-29)

**Status:** Pending
**Priorità:** ALTA - prerequisito per TASK-894
**Stima:** 1h

**Obiettivo:** Creare un modulo condiviso per normalizzare l'estrazione del contesto decisionale, evitando duplicazione tra TASK-894 (scrittura DB) e SessionLogHandler (analisi log).

**File da creare:** `synthtrade/backend/app/core/decision_context.py`

**Task:**
1. Definire dataclass `DecisionContext` con tutti i campi richiesti da TASK-893
2. Implementare `extract_decision_context(**kwargs)` che normalizza e valida
3. Aggiungere test unitario per validare normalizzazione
4. Aggiornare TASK-894 per usare questo modulo

**Verifica:** Test unitario passa, TASK-894 usa il nuovo extractor.

---

### TASK-899 — Log Persistence Layer (2026-06-29)

**Status:** Pending
**Priorità:** MEDIA - prerequisito per integrazione download log
**Stima:** 2h

**Obiettivo:** Creare un layer di astrazione per la persistenza dei log, supportando sia DB che filesystem, e fornire parser riutilizzabili per i log legacy.

**File da creare:** `synthtrade/backend/app/core/log_persistence.py`

**Task:**
1. Creare classe `LogStorage` che astrae le operazioni di persistenza:
   - `persist_to_db(session_id, content)` - salva su scalping_sessions.log_content
   - `persist_to_file(content, path)` - salva su filesystem locale
   - `load_from_db(session_id)` -> LogContent - carica dal DB
   - `load_from_file(path)` -> LogContent - carica da filesystem
2. Creare classe `LogParser` per parsing dei log testuali:
   - `parse_lines_to_records(text)` - crea LogRecord sintetici da testo
   - `parse_to_structured_data(text)` - estrae dati strutturati per analisi
3. Integrazione con SessionLogHandler:
   - SessionLogHandler può usare LogStorage per il flush al DB
   - Router può usare LogParser per l'endpoint `/logs/analysis`
4. Aggiungere test unitari per LogStorage e LogParser

**Verifica:** Test unitari passano, SessionLogHandler può persistere su DB usando LogStorage, endpoint `/logs/analysis` usa LogParser.

---

### TASK-893 — Persistenza Log Decisionale: Fase 1 - Schema DB `session_signal_log` (2026-06-29)

**Status:** Pending

**Obiettivo:** Creare la tabella `session_signal_log` su Supabase per persistere ogni decisione del sistema con contesto completo.

**File:** `supabase/migrations/` (nuova migration)

**SQL Migration:**
```sql
CREATE TABLE session_signal_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES scalping_sessions(id),
    symbol TEXT NOT NULL,
    decided_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- snapshot del contesto al momento della decisione
    regime TEXT NOT NULL,
    strategy_type TEXT NOT NULL,
    tech_signal TEXT,                  -- BUY/SELL/HOLD/CLOSE
    tech_confidence NUMERIC(5,3),
    intel_score NUMERIC(6,2),
    intel_bias TEXT,                   -- bullish/bearish/neutral
    trend_direction TEXT,              -- converging/diverging/stable
    trend_value NUMERIC(6,2),

    -- esito della decisione
    decision_type TEXT NOT NULL CHECK (decision_type IN (
        'execute', 'block_conflict', 'mean_reversion_override',
        'hold_existing_position', 'rejected_other'
    )),
    decision_reason TEXT,              -- testo libero, es. "conflitto intelligence-tecnico"

    -- collegamento al trade, se la decisione ha portato a un trade (Fase 3)
    trade_id UUID REFERENCES scalping_trades(id),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_signal_log_session ON session_signal_log(session_id, decided_at);
CREATE INDEX idx_signal_log_strategy_regime ON session_signal_log(strategy_type, regime);
CREATE INDEX idx_signal_log_decision_type ON session_signal_log(decision_type);
```

**Task:**
1. Creare migration SQL con CREATE TABLE e tutti i campi definiti
2. Applicare migration su Supabase
3. Verifica: `SELECT * FROM session_signal_log LIMIT 1` ritorna header vuoto (tabella presente, no data)

---

### TASK-894 — Persistenza Log Decisionale: Fase 2 - Scrittura decisioni (5 punti) (2026-06-29)

**Status:** Pending

**Obiettivo:** Scrivere su `session_signal_log` ogni decisione del sistema con contesto completo usando DecisionContextExtractor.

**Dipendenze:** TASK-892 (DecisionContextExtractor), TASK-893 (tabella deve esistere)

**File da modificare:** `backend/app/scalping/router.py`

**Task:**
1. Creare funzione helper `_log_signal_decision()` in `router.py` o in un nuovo modulo `signal_log_writer.py`
2. Usare `DecisionContextExtractor.extract_decision_context()` per normalizzare il contesto decisionale
3. Collegare la funzione ai 5 punti dove oggi viene loggato testualmente una decisione:
   - `PIPELINE: ... tradeable=True` seguito da `DECISION APPROVED` → `decision_type='execute'`
   - `BLOCK: conflitto intelligence-tecnico` → `decision_type='block_conflict'`
   - `MEAN-REVERSION BUY permesso ... nonostante bias=bearish` → `decision_type='mean_reversion_override'`
   - `HOLD: existing BUY position matches BUY signal` → `decision_type='hold_existing_position'`
   - altri `DECISION REJECTED` → `decision_type='rejected_other'`
4. Per ogni punto, passare i campi dal contesto disponibile all'extractor (regime, strategy, tech_signal, intel_score, intel_bias, trend_direction, trend_value)
5. Eseguire INSERT su `session_signal_log` con `decision_reason` testo libero quando appropriato
6. Política di errore: se l'INSERT su Supabase fallisce, NON deve bloccare il trading — loggare l'errore e continuare (stesso principio di "Balance check failed (non-blocking)")

**Verifica:** Dopo una sessione live di test, contare le righe in `session_signal_log` e confrontarle a mano con il numero di righe `PIPELINE:`/`BLOCK:`/`MEAN-REVERSION` nel log testuale della stessa sessione — devono corrispondere 1:1.

---

### TASK-895 — Persistenza Log Decisionale: Fase 3 - Collegamento `trade_id`/`signal_log_id` (2026-06-29)

**Status:** Pending

**Obiettivo:** Collegare ogni trade chiuso alla decisione di esecuzione corrispondente.

**Dipendenze:** TASK-893, TASK-894 (devono essere completate prima)

**File da modificare:** `supabase/migrations/` (nuova migration), `backend/app/scalping/router.py`

**Task:**
1. Aggiungere colonna `signal_log_id UUID REFERENCES session_signal_log(id)` a `scalping_trades` (migration separata)
2. Popolare `signal_log_id` nel punto di apertura trade (subito dopo la scrittura del log decisionale in TASK-894, prima dell'ordine Binance)
3. Verificare su un trade reale chiuso che il join `session_signal_log.trade_id ↔ scalping_trades.id` (o l'inverso via `signal_log_id`) restituisca la riga corretta

**Decisione design da chiarire:** qual è la chiave di match tra la riga di log "execute" (scritta in TASK-894) e il trade chiuso? L'approccio preferito è aggiungere `signal_log_id` su `scalping_trades` e popolarlo subito dopo l'insert di TASK-894, prima di piazzare l'ordine — così il collegamento è per ID, non per timestamp o prezzo.

**Verifica:** Su almeno 3 trade chiusi reali, query di join che recupera regime/strategy/intel_score al momento dell'apertura insieme al PnL finale — confrontati a mano con quanto visibile nei log testuali dello stesso trade.

---

### TASK-896 — Persistenza Log Decisionale: Fase 4 - Qualità dati errore Binance (2026-06-29)

**Status:** Pending

**Obiettivo:** Loggare il body completo delle eccezioni Binance invece di messaggi troncati.

**Dipendenze:** TASK-893 (per il nuovo decision_type)

**File da modificare:** `backend/app/scalping/router.py`, `supabase/migrations/` (ALTER TABLE se necessario)

**Task:**
1. Modificare il logging dell'eccezione per includere il body completo (fix isolato, basso rischio, nessuna modifica a logica di trading)
2. Aggiungere `execution_error` come valore valido del CHECK constraint su `decision_type` (richiede `ALTER TABLE` se TASK-893 è già in produzione)
3. Collegare il punto di catch dell'eccezione alla scrittura `session_signal_log` con `decision_type='execution_error'`

**Codice da modificare:**
Nel blocco try/except attorno a `place_market_order`/`place_oco_order`:
```python
except ccxt.BaseError as e:
    logger.error(f"Live trade failed: {e}")  # invece di un messaggio troncato
    # opzionale: anche e.args se str(e) non basta a includere il body HTTP
```

**Verifica:** Riprodurre (o attendere) un nuovo fallimento `Live trade failed` e confermare che il log mostri il body reale (es. `insufficient balance`, `LOT_SIZE`, `MIN_NOTIONAL`) invece del messaggio troncato attuale.

---

### TASK-897 — Persistenza Log Decisionale: Fase 5 - Vista aggregata win rate (2026-06-29)

**Status:** Pending

**Obiettivo:** Creare una vista di sola lettura per win rate per (strategy, regime).

**Dipendenze:** TASK-893, TASK-894, TASK-895 (devono essere completate prima)

**File da modificare:** `supabase/migrations/` (nuova migration per la vista)

**SQL View:**
```sql
CREATE VIEW signal_outcome_by_strategy_regime AS
SELECT
    sl.strategy_type,
    sl.regime,
    COUNT(t.id) AS n_trades,
    COUNT(t.id) FILTER (WHERE t.pnl > 0) AS n_wins,
    ROUND(COUNT(t.id) FILTER (WHERE t.pnl > 0)::numeric / NULLIF(COUNT(t.id), 0) * 100, 1) AS win_rate_pct,
    ROUND(AVG(t.pnl), 4) AS avg_pnl,
    ROUND(SUM(t.pnl), 4) AS total_pnl
FROM session_signal_log sl
JOIN scalping_trades t ON t.signal_log_id = sl.id
WHERE sl.decision_type = 'execute'
GROUP BY sl.strategy_type, sl.regime;
```

**Nota:** Non parametrizzata su una finestra temporale fissa in questa fase — la decisione su finestra mobile (ultimi 14gg / ultimi N trade) è una scelta di design che riguarda come il Supervisor consumerà questo dato (Livello 2/3, fuori scope).

**Task:**
1. Creare la vista SQL
2. Verificarla contro il bilancio storico già calcolato a mano (18 sessioni, 70 trade, 34.3% win rate aggregato) — la somma di `n_trades` su tutte le righe della vista deve coincidere con 70, a meno di trade precedenti all'introduzione di TASK-893-895

**Verifica:** Query eseguita su Supabase, risultati confrontati a mano con almeno una sessione reale già nota (es. sessione con `rsi_bollinger`/`ranging` e `ema_cross`/`trending_up` o `trending_down` coerenti con quanto già analizzato).

---

### TASK-898 — Analisi Trend basata su dati persistiti (2026-06-29)

**Status:** Pending
**Priorità:** MEDIA — dipende da dati reali raccolti via TASK-894/895
**Stima:** 2h
**Dipendenze:** TASK-893, TASK-894, TASK-895 (completate) + almeno 20 trade reali chiusi con `trade_id` collegato correttamente in `session_signal_log`

**Obiettivo:** Analizzare l'outcome dei trade basandosi sul trend (converging/diverging/stable) utilizzando i dati persistiti in `session_signal_log`. Questa analisi chiude il punto pendente della sessione 22-23/06 sul Falling Knife Protection, dove il trend tracking non era ancora collegato al ramo mean-reversion e non si avevano dati per validare l'ipotesi.

#### Contesto

Il campo `trend_direction` indica dove sta andando lo score intelligence nel tempo:
- **converging** → lo score si sta avvicinando a 0
- **diverging** → lo score si sta allontanando da 0
- **stable** → lo score è piatto

**Nota importante:** `trend_direction` si riferisce al punteggio intelligence, non alla direzione del trade tecnico. Per analizzare ipotesi tipo "converging verso BUY/SELL" serve incrociare `trend_direction` con `tech_signal` o `intel_bias`.

#### Ipotesi da verificare

L'obiettivo è verificare se il `trend` al momento dell'apertura è predittivo dell'outcome:

| Trend (solo) | Ipotesi preliminare |
|--------------|---------------------|
| `converging` | Score si sta avvicinando a 0 — segnalare se questo correla con outcome positivi/negativi |
| `diverging` | Score si sta allontanando da 0 — segnalare se questo correla con outcome positivi/negativi |
| `stable` | Score piatto — baseline di confronto |

**Analisi aggiuntiva da fare incrociando con `tech_signal`:**
- `trend_direction` + `tech_signal='BUY'` vs `trend_direction` + `tech_signal='SELL'`
- `trend_direction` + `intel_bias` (bullish/bearish/neutral)

#### Fasi

##### Fase 1 — Verifica disponibilità dati

1. Verificare che `session_signal_log` contenga almeno 20 decisioni di tipo `execute` con `trade_id` collegato
2. Verificare che i campi `trend_direction` e `trend_value` siano popolati per almeno il 90% dei trade
3. Query di verifica:
```sql
SELECT COUNT(*) FROM session_signal_log
WHERE decision_type = 'execute' AND trade_id IS NOT NULL;

SELECT COUNT(*) FROM session_signal_log
WHERE decision_type = 'execute' AND trade_id IS NOT NULL
  AND trend_direction IS NOT NULL AND trend_value IS NOT NULL;
```

**Prerequisito critico:** Se TASK-895 è completato ma non ci sono ancora trade reali chiusi e collegati, questo task non può partire. Attendi almeno 20 trade chiusi con `trade_id` popolato.

##### Fase 2 — Analisi correlazione trend/outcome aggregata per regime/strategia

Script standalone per analizzare i dati dal DB:
```python
# scripts/analyze_trend_outcome_db.py
# Legge da session_signal_log e scalping_trades
# Calcola:
# - Win rate per trend_direction (converging/diverging/stable) aggregato
# - Win rate per (trend_direction, regime, strategy_type) — disaggregato
# - Win rate per (trend_direction, tech_signal) — incrocio con direzione tecnica
# - Win rate per (trend_direction, intel_bias) — incrocio con bias intelligence
# - Correlazione tra |trend_value| e pnl medio
```

Query SQL base per l'analisi aggregata:
```sql
SELECT
    sl.trend_direction,
    sl.regime,
    sl.strategy_type,
    COUNT(t.id) AS n_trades,
    COUNT(t.id) FILTER (WHERE t.pnl > 0) AS n_wins,
    ROUND(COUNT(t.id) FILTER (WHERE t.pnl > 0)::numeric / NULLIF(COUNT(t.id), 0) * 100, 1) AS win_rate_pct,
    ROUND(AVG(t.pnl), 4) AS avg_pnl
FROM session_signal_log sl
JOIN scalping_trades t ON t.signal_log_id = sl.id
WHERE sl.decision_type = 'execute'
  AND sl.trend_direction IS NOT NULL
GROUP BY sl.trend_direction, sl.regime, sl.strategy_type
ORDER BY sl.trend_direction, sl.regime, sl.strategy_type;
```

**Output atteso (esempio):**
```
Trend: converging, Regime: ranging, Strategy: rsi_bollinger → 8 trade, 6 win (75%)
Trend: converging, Regime: trending_up, Strategy: ema_cross → 4 trade, 2 win (50%)
Trend: diverging, Regime: ranging, Strategy: rsi_bollinger → 5 trade, 1 win (20%)
Trend: stable, Regime: trending_down, Strategy: ema_cross → 3 trade, 1 win (33%)
```

**Controllo numerosity:** Se una combinazione (trend, regime, strategy) ha meno di 5 trade, marcarla come "campione insufficiente" nel report — non trarre conclusioni da sotto-campioni.

##### Fase 3 — Report per Supervisor

Creare un report strutturato che il Supervisor può utilizzare nelle decisioni future:
- Statistiche aggregate per tipo di trend (converging/diverging/stable)
- Statistiche disaggregate per (trend, regime, strategy) con marker per campioni insufficienti
- Statistiche incrociando trend con tech_signal e intel_bias
- Osservazioni preliminari basate sui dati (non conclusioni definitive)
- Suggerimenti per il prompt del Supervisor (es. se diverging mostra win rate basso, suggerire al Supervisor di considerarlo come segnale di cautela)

**File da creare:** `docs/trend_analysis_report.md`

#### Metriche di successo

- Almeno 20 trade analizzati con metadati trend completi
- Report completo disponibile per consumo del Supervisor
- Osservazioni preliminari chiaramente marcate come "da validare su campione più ampio"

#### Rischi

- Campione troppo piccolo per conclusioni statistiche (n < 20 per combinazione)
- Il trend potrebbe essere rumoroso (calcolato su finestra mobile)
- Correlazione non implica causalità: il trend potrebbe essere proxy di altre variabili (regime, strategy)
- Conclusioni su campioni piccoli possono essere fuorvianti se concentrate in un solo regime/strategia

---

## Task Archiviati
