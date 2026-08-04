# Handoff Protocol — SynthTrade

## Ultimo Handoff

### Da: Codex → prossima sessione

**Data:** 2026-08-04

**Contesto:** TASK-1244 — correzione definitiva della riconciliazione delle chiusure OCO OKX mentre l'app era offline.

### Riparazione storico già chiuso
- `scripts/repair_okx_trade_history.py` non modifica nulla per default. Eseguire il dry-run con `--session-id <uuid> --report C:\tmp\okx-repair.json`, verificare le righe `update_verified`, quindi applicare con `--apply --report ... --confirm APPLY_OKX_REPAIR`.
- Il job non usa matching per simbolo/lato e scarta i casi senza catena `algoId → ordId → fill`. Non eseguire gli script storici `fix_db.py`/`list_db.py`: sono stati rimossi perché non sicuri.

### ✅ Diagnosi e fix
- Il codice precedente chiamava `get_algo_orders_history()`, ma l'adapter interrogava prima `/api/v5/trade/fills` per l'intero simbolo e ritornava subito. Il reconcile, se l'`algoId` non compariva in quel fill, sceglieva la prima vendita `side=sell`: non era una correlazione con l'OCO e poteva usare il trade di un'altra sessione.
- `OkxExchangeAdapter.get_algo_orders_history(symbol, bracket_id)` ora legge `orders-algo-history` per lo specifico `algoId` salvato nel DB, estrae il child `ordId` e richiede i fill soltanto per quell'ordine. Restituisce prezzo medio ponderato, `actualSide` (TP/SL) e `fillTime` reale.
- `reconciliation.py` accetta una chiusura solo con match esatto `algoId`. Rimossi fallback ``exit side`` e ``entry_price``; se l'API non ha ancora propagato il fill, la posizione locale non viene chiusa/corrotta e il retry successivo resta sicuro.

### 🧪 Verifica eseguita
- `.venv\\Scripts\\python.exe -m pytest synthtrade/backend/tests/unit/test_reconcile_position.py synthtrade/backend/tests/unit/test_okx_oco_reconciliation.py -q`
- Risultato: **7 passed**. `ruff` non è installato nel virtualenv.

### 📌 Test manuale raccomandato
1. Aprire un trade live con OCO, annotare `exchange_bracket_id` nella riga `scalping_trades`.
2. Fermare il backend, lasciare scattare SL o TP su OKX, riavviare.
3. Verificare che `exit_price`/`exit_time` coincidano con il fill del child `ordId` dell'OCO e che la riga diventi `closed`; sia dashboard sia pagina Log leggono la stessa riga DB.
4. In caso di ritardo API, verificare il warning ``no verified fill exists``: non deve comparire una chiusura a entry price.

---

### Da: Antigravity → prossima sessione

**Data:** 2026-08-03 09:45

**Contesto:** Fix bug timestamp riconciliazione exit_time OKX post-riavvio weekend e fix formattazione data/ora trade log sessioni frontend.

---

### ✅ Fix 1 — Timestamp riconciliazione exit_time (`okx_exchange.py`)
- **Problema:** Post-riavvio del weekend, i trade riconciliati mostravano come `exit_time` l'orario di esecuzione della riconciliazione (`datetime.now()`) invece del reale timestamp di fill su OKX.
- **Root Cause:** OKX `/api/v5/trade/fills` utilizza la chiave `ts` per il timestamp dei fill e non `fillTime`. L'adapter `okx_exchange.py` (L.745) eseguiva `fill.get("fillTime")` che ritornava sempre `None`.
- **Fix:** Modificato in `fill.get("fillTime") or fill.get("ts")`. Ora `exit_time` viene estratto correttamente dal fill OKX.

---

### ✅ Fix 2 — Formattazione data/ora trade log sessioni (`logs.page.ts`)
- **Problema:** La tabella dei trade nel dettaglio sessione mostrava solo l'ora (`HH:mm`) per `entry_time`, rendendo ambigua la data dei trade.
- **Fix:** In `logs.page.ts` (L.184), aggiornato il pipe di formattazione a `dd/MM/yy HH:mm` e rinominata l'intestazione da `Ora` a `Data/Ora`, allineandola allo Storico Trade.

---

### ⚠️ Punto Aperto Residuo
- **`position_manager.py` (Live close path):** Il percorso di chiusura in-memory/live imposta ancora `closed_at = datetime.now()` al momento della ricezione/gestione dell'evento di chiusura anziché adottare il timestamp esatto dal payload dell'exchange/WS. Resta da gestire in un task separato.

---

### Precedente Handoff

### Da: Antigravity → prossima sessione

**Data:** 2026-07-28 09:30

**Contesto:** Analisi completa log sessione 4a42133e (10.847 righe) — 5 nuovi task creati per approfondimento e fix.

---

### ✅ Recap mancante — Risolto

Il blocco SESSION ANALYSIS SUMMARY ora è presente in testa al dump e popolato correttamente. La fix applicata:
- Rimuovere conteggio SELL dal summary (long-only engine)

**Verificato:** Decisioni=891 totali, Segnali=1, Trades=8, Intelligence min=-26.2 max=18.9 avg=-4.3

### ✅ Punto 1 aggiornato — Task TASK-1231 creato

Cleanup: rimuovere scomposizione BUY/SELL dal Session Summary.

---

### 🔴 TASK-1232: Query storica win rate mean-reversion override

Join `session_signal_log` → `scalping_trades` via `signal_log_id`, bucket per `intel_score`, calcolo win rate e avg PnL per bucket. Documento in `docs/recap/`.

**Bloccante:** TASK-1233 (verifica integrità signal_log_id)

### 🔴 TASK-1233: Verifica integrità signal_log_id sessione 4a42133e

Query LEFT JOIN tra `scalping_trades` e `session_signal_log`. Documentare se trade con signal_log_id NULL.

### 🟡 TASK-1234: Signal log writer — aggiungere conferma successo esplicita

Aggiungere log INFO con signal_log_id su insert riusciti per override mean-reversion. Oggi solo ERROR loggato.

### 🔴 TASK-1235: fee_tier_certified False dal 2° trade in poi

Solo trade 1/8 ha certified=True. Verificare `candle_processor.py` e `okx_exchange.py`. Fix minimo: loggare motivo del fallback.

### 🟡 TASK-1236: Verificare fee_tier_certified persistito per-trade in DB

Query `scalping_trades.entry_fee_rate/exit_fee_rate` vs `scalping_sessions.fee_tier_certified`.

---

### 📋 Task ancora Pending

| Task | Descrizione | Priorità |
|------|-------------|----------|
| TASK-1230 | Session Max Loss + Drawdown Fix | 🔴 ALTA |
| TASK-1231 | Cleanup: rimuovere SELL dal Session Summary | 🟢 BASSA |
| TASK-1232 | Query storica win rate mean-reversion override | 🔴 ALTA (dipende da 1233) |
| TASK-1233 | Verifica integrità signal_log_id sessione 4a42133e | 🔴 ALTA |
| TASK-1234 | Signal log writer: aggiungere conferma successo | 🟡 MEDIA |
| TASK-1235 | fee_tier_certified False dal 2° trade | 🔴 ALTA |
| TASK-1236 | Verificare fee_tier_certified per-trade in DB | 🟡 MEDIA |

### 📊 Scoperte chiave dalla sessione 4a42133e

1. **Mean-reversion override → trade:** 29 override, solo 8 con trade reale. 18 fallimenti scrittura DB (hold), 0 coincidenti con entry.
2. **Fee tier certified:** Solo trade 1/8 ha certified=True. Tutti gli altri fallback a 0.001/0.001.
3. **Supervisor auto-decay:** Dalle 00:26:38, session in paused — override continuano senza esecuzione (~15 "fantasma").

---

### Precedente Handoff

**Data:** 2026-07-24 11:40

**Contesto:** Risoluzione errore 51155 OKX e pulizia finale epica short.

---

### ✅ Risoluzione Errore 51155 (OKX Compliance)

**Problema:** Nonostante il codice fosse tornato allo Spot puro (`tdMode="cash"`), le operazioni su OKX fallivano con `51155 Local compliance restrictions`.
**Causa:** L'errore scattava perché la sessione era avviata sulla coppia **`BTC-USD`** (valuta fiat americana), che è bloccata dalle policy MiCA per gli account retail in EU, indipendentemente dalla modalità di margin.
**Soluzione:** L'utente ha cambiato il balance e ha avviato la sessione su `BTC-EUR`, e gli ordini BUY a mercato con relativi bracket exit (OCO) sono partiti perfettamente.

### ✅ Cleanup default symbol

**Fix applicati:**
- Modificati i default del frontend in `session-api.service.ts` e `market-intel-panel.component.ts` da `OKBEUR` a `BTC-EUR` per evitare che l'app parta sulla chart sbagliata all'avvio.

**Prossimi passi:**
- Focus su strategie Long-only (mean reversion, ecc).
- Nessun residuo short rimasto nel codice.

---

### Precedente Handoff

### Da: Antigravity → prossima sessione

**Data:** 2026-07-17 14:30

**Contesto:** TASK-1166 Refactoring `router.py` — Fasi 1-4 completate.

---

### ✅ TASK-1166 Completato: `router.py` da 4310→180 righe (95.8% riduzione)

**Problema:** `router.py` era un monolite ingestibile da oltre 4300 righe.
**Soluzione completa (4 fasi):**
- **Fase 1:** Estratti `_state.py` (50 righe), `pricing.py` (149), `reconciliation.py` (162), `db_ops.py` (169).
- **Fase 2:** Estratti `trade_executor.py` (451), `session_lifecycle.py` (59).
- **Fase 3:** Estratti `broadcast.py` (38), `pipeline.py` (224), `market_processors.py` (1006).
- **Fase 4:** Estratti REST endpoints in `rest/`:
  - `rest/market_data.py` (245): exchange-info, instruments, sessions, trade-history, candles, `_snapshot_to_dict`
  - `rest/backtest.py` (75): run, result, list endpoints
  - `rest/session.py` (968): control_session, get_session, logs, position, config, risk, performance, health
  - `rest/intel_opportunity.py` (243): intelligence, opportunities, debug, supervisor endpoints
- `router.py` (180 righe) ora è un thin shell che include 4 sub-router + re-export backward-compat + WS endpoint.
- Tutti i test passano: 12/12 OKX integration, 6/6 reconcile, 27/27 unit.
- Pre-existing bugs fixati: `session_lifecycle.py` import path, `market_processors.py` loose code syntax.

### 📋 Task ancora Pending

| Task | Descrizione | Priorità |
|------|-------------|----------|
| TASK-1166.Cleanup | Eliminare eventuali test o commenti obsoleti, aggiornare TASKS.md | BASSA |

### 🔍 Verifica manuale da fare al prossimo avvio

- Testare start sessione live per verificare che `_on_order_update` funzioni correttamente da `trade_executor.py`.
- Verificare che il WebSocket endpoint inizia correttamente (lo WS è ancora in `router.py`).
- Controllare che tutti gli import backward-compat in `router.py` funzionano con main.py, config_api.py, scalping_jobs.py, user_data_stream.py, supervisor_scheduler.py, parameter_updater.py.

---

(Il resto del file HANDOFF.md precedente è preservato ma troncato per chiarezza — vedi versione completa su disco)
