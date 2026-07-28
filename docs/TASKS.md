# TASKS.md — SynthTrade Task Tracking

> **Aggiornato:** 2026-07-28. Task completati in `docs/ARCHIVE_TASKS.md`.

---

### TASK-1232: Query storica — Win rate mean-reversion override segmentato per intensità bias — 🔴 Alta ✅ COMPLETED

> **Risultato:** 12 trade mean-reversion override BUY analizzati su 4 sessioni. Win rate globale 25% (3/11 chiusi). Zona potenzialmente ottimale [-15,-20] con 50% win rate (2 trade). Campione ancora troppo piccolo per conclusions definitive. Report: `docs/recap/2026-07-28_mean-reversion-override-analysis.md`.

---

### TASK-1233: Verifica integrità signal_log_id per i trade della sessione 4a42133e — 🔴 Alta ✅ COMPLETED

> **Risultato:** Tutti e 8 trade hanno `signal_log_id` non-NULL collegato a una riga in `session_signal_log`. 7/8 con `decision_type='mean_reversion_override'`, 1/8 (trade 13:42) con `decision_type='execute'` (segnale pipeline regolare, score +15.0 — bias opposto ai 7 override). Nessun gap di scrittura.

---

### TASK-1234: Signal log writer — Aggiungere conferma di successo esplicita — 🟡 Media ✅ COMPLETED

> **Risultato:** Aggiunto log INFO in `log_signal_decision()` per `decision_type='mean_reversion_override'` con format `[SIGNAL_LOG] Scritto signal_log_id=<uuid> decision_type=mean_reversion_override session=<id>`. Log non appare su errori (ERROR-only). 3 nuovi test: INFO presente su successo, assente su altri decision_type, assente su errore. 15/15 test passanti.

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