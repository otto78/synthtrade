# TASKS.md — SynthTrade Task Tracking

> **Aggiornato:** 2026-07-28. Task completati in `docs/ARCHIVE_TASKS.md`.

---

### TASK-1231: Cleanup — Rimuovere conteggio SELL dal Session Summary — ✅ COMPLETED

> **Problema:** Il blocco SESSION ANALYSIS SUMMARY mostrava `Segnali: ... BUY=1 SELL=0` e `Trades: 8 eseguiti | BUY=8 SELL=0`. Dato che SELL è permanentemente disabilitato (long-only engine), la colonna era morta e aggiungeva solo rumore.
>
> **Fix:** Rimosso il breakdown BUY/SELL dalla visualizzazione in `_format_analysis_section()` in `session_log_handler.py`. I conteggi interni sono mantenuti nell'analysis JSON per il download e l'endpoint strutturato.
>
> **File modificato:** `synthtrade/backend/app/core/session_log_handler.py`
>
> **Commit:** TBD

---

### TASK-1232: Query storica — Win rate mean-reversion override segmentato per intensità bias — 🔴 Alta

> **Dipendenze:** TASK-1233 (verifica integrità dati prima di fidarsi dell'aggregato)
>
> **Obiettivo:** confermare o confutare con dati reali multi-sessione il pattern osservato nella sessione 4a42133e: bias fortemente bearish → override mean-reversion BUY → stop loss.
>
> **Query:** join `session_signal_log` (`decision_type='mean_reversion_override'`) con `scalping_trades` via `signal_log_id`, bucket per `intel_score` (es. [-10,-15), [-15,-20), [-20,-30)), calcolo win rate e avg PnL per bucket. Stesso pattern già usato in `trend_analysis_report.md` (16/07).
>
> **Output atteso:** documento tipo `docs/recap/YYYY-MM-DD_mean-reversion-override-analysis.md` con la tabella bucket→win_rate→avg_pnl e una conclusione esplicita: il pattern regge o no coi dati disponibili? Se il campione è ancora troppo piccolo (probabile, vista la bassa frequenza di trade attuale), dirlo chiaramente invece di trarre conclusioni premature.
>
> **Non fare in questo task:** nessuna modifica a `signal_aggregator.py` o alla soglia dell'override — questo è solo il task di raccolta evidenza.

---

### TASK-1233: Verifica integrità signal_log_id per i trade della sessione 4a42133e — 🔴 Alta

> **Bloccante per:** TASK-1232
>
> **Contesto:** nella sessione analizzata sono stati osservati 18 fallimenti di scrittura su `session_signal_log` (12× getaddrinfo failed tra 12:36-13:00, 6× Server disconnected tra 17:17-23:19). Verificando riga per riga, nessuno di questi fallimenti coincide temporalmente con le 8 aperture trade via override — cadono tutti su decisioni `hold_existing_position`/`rejected_other`. Ma il writer logga solo gli errori, mai un successo esplicito, quindi non è verificabile dai soli log applicativi.
>
> **Query:**
> ```sql
> SELECT t.id, t.entry_time, t.signal_log_id, sl.decision_type, sl.intel_score
> FROM scalping_trades t
> LEFT JOIN session_signal_log sl ON sl.id = t.signal_log_id
> WHERE t.session_id = '4a42133e-cf22-4824-96ce-c37fc0406245'
> ORDER BY t.entry_time;
> ```
>
> **Verifica di completamento:** tutti gli 8 trade devono avere `signal_log_id` non-NULL collegato a una riga con `decision_type='mean_reversion_override'`. Se anche un solo trade ha `signal_log_id` NULL, documentarlo come gap noto prima di usare l'aggregato in TASK-1232 — non escluderlo silenziosamente dalla query futura senza annotarlo.

---

### TASK-1234: Signal log writer — Aggiungere conferma di successo esplicita — 🟡 Media

> **Problema:** `_log_signal_decision()`/`log_signal_decision()` in `app/core/signal_log_writer.py` logga solo gli errori (18 righe ERROR viste in una sola sessione). Non c'è modo di distinguere dai log "scrittura riuscita silenziosamente" da "scrittura mai tentata" senza query DB.
>
> **Fix:** aggiungere un log INFO con il `signal_log_id` restituito dall'insert per i soli `decision_type='mean_reversion_override'` (più critici da tracciare). Esempio: `[SIGNAL_LOG] Scritto signal_log_id=<uuid> decision_type=mean_reversion_override`.
>
> **Test:** verificare che il log di conferma appaia per un insert riuscito e non appaia se l'insert fallisce (deve restare ERROR-only in quel caso, nessun doppio log).
>
> **Beneficio diretto:** le prossime sessioni permetteranno di rispondere alla domanda "quanti override sono stati davvero persistiti" leggendo solo il log, senza dover aprire Supabase.

---

### TASK-1235: Investigare perché fee_tier_certified diventa False dal secondo trade in poi — 🔴 Alta

> **Evidenza:** negli 8 log `[NET_PRICING]` della sessione 4a42133e, solo il primo trade (10:35) ha `certified=True`; tutti i successivi 7 (14:33 → 21:46) hanno `certified=False`, con fallback a fee 0.001/0.001 nonostante lo stesso adapter OKX e nessun restart di sessione visibile nei log applicativi.
>
> **Ipotesi da verificare (non assumere quale sia corretta):**
> - Il fee tier viene certificato una sola volta all'avvio sessione e poi non più ri-tentato — un problema successivo (es. race condition, stato non persistito correttamente tra chiusura/riapertura trade) resetta il flag a False invece di mantenere il valore già certificato.
> - Ogni apertura trade richiama `get_trade_fee()`/`_direct_fetch_trade_fee()` da capo, e dal secondo trade in poi la chiamata fallisce silenziosamente (rate limit OKX, errore rete) cadendo sul fallback — coerente col pattern già visto altre volte nel progetto (es. TASK-1116.E).
>
> **File da controllare:** `candle_processor.py` (punto dove viene costruito `[NET_PRICING]` e dove `certified` viene letto/impostato), `okx_exchange.py` (`get_trade_fee`).
>
> **Fix minimo richiesto prima di chiudere il task:** quando `certified=False`, loggare esplicitamente il motivo (es. `fee tier fallback: <eccezione>` o `fee tier not refreshed since session start`) — oggi si vede solo il risultato (False), mai la causa. Senza questo, la prossima sessione con lo stesso sintomo richiederà di nuovo scavo manuale nei log grezzi.
>
> **Verifica di completamento:** su una sessione demo/paper con più trade consecutivi, il log deve mostrare per ogni trade `certified=True` (se la fee è davvero certificabile ad ogni apertura) oppure un motivo esplicito del fallback.

---

### TASK-1236: Verificare se fee_tier_certified è persistito per-trade in DB — 🟡 Media

> **Dipendenze:** nessuna (query read-only), utile eseguirlo insieme a TASK-1233
>
> **Obiettivo:** dallo schema noto (TASK-1108/1114), `fee_tier_certified`/`fee_tier_raw` sembrano vivere su `scalping_sessions`, mentre `entry_fee_rate`/`exit_fee_rate` dovrebbero vivere su `scalping_trades`. Nella sessione analizzata il flag certified cambia dentro la stessa sessione (True poi False) — se il campo DB è solo a livello sessione, quell'informazione va persa: non si potrà più distinguere a posteriori quale degli 8 trade aveva fee certificate e quale no.
>
> **Query:**
> ```sql
> SELECT id, entry_time, entry_fee_rate, exit_fee_rate
> FROM scalping_trades
> WHERE session_id = '4a42133e-cf22-4824-96ce-c37fc0406245'
> ORDER BY entry_time;
>
> SELECT fee_tier_certified, fee_tier_raw FROM scalping_sessions
> WHERE id = '4a42133e-cf22-4824-96ce-c37fc0406245';
> ```
>
> **Verifica di completamento:** se `entry_fee_rate`/`exit_fee_rate` sono popolati per-trade con valori diversi tra i trade (coerente coi log: trade 1 con fee certificate, gli altri col fallback 0.001), il gap è già chiuso — basta documentarlo. Se invece i valori sono NULL o identici per tutti gli 8 trade nonostante il log mostri certified diverso, è un gap reale da aprire come task di fix separato (non in questo task, che resta di sola verifica).

---

### Punto 4 (pesi signal score) — 🟡 Fermo

> **Stato:** Confermato nessuna azione da intraprendere ora — coerente con TASK-1159 bloccato. Resta in attesa di revisione pesi futura.