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

### TASK-1235: Investigare perché fee_tier_certified diventa False dal secondo trade in poi — 🔴 Alta ✅ COMPLETED

> **Risultato:** Root cause identificata in `main.py` (session restore). Durante il restore della sessione al restart del server, `get_trade_fee()` viene chiamata e il risultato salvato in `_execution_state["fee_tier"]`, ma `_execution_state["fee_tier_certified"]` non veniva mai settato. Il flag restava a `False` (default del `.get()`).
>
> **Flusso anomalo:** session start normale → `certified=True` (session.py:205). Server restart → main.py restore → `fee_tier` salvato (come FeeTier object, non dict!) ma `fee_tier_certified` mai assegnato → default `False`. Tutti i trade successivi leggono `False`.
>
> **Fix applicato:**
> 1. `main.py:399-406` e `416-425`: aggiunto `_execution_state["fee_tier_certified"] = fee_tier.certified` + conversione FeeTier→dict in entrambi i path di restore (con e senza posizione aperta). Anche nel path di eccezione: `fee_tier_certified = False`.
> 2. `candle_processor.py:513-525`: aggiunto WARNING log quando `certified=False` al momento del trade, con messaggio esplicito che punta a `TASK-1235` per debugging futuro.

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