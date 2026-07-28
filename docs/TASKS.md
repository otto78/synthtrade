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

### TASK-1236: Verificare se fee_tier_certified è persistito per-trade in DB — 🟡 Media ✅ COMPLETED

> **Risultato:** Gap confermato. Le colonne `entry_fee_rate`/`exit_fee_rate` non esistono su `scalping_trades`. Le colonne `entry_commission`/`exit_commission` esistono ma sono **NULL per tutti e 8 i trade** della sessione 4a42133e. A livello sessione, `fee_tier_certified=true` ma `fee_tier_raw=null`. Non è possibile distinguere retroattivamente quali trade avevano fee certificate e quali no. Gap di persistenza per-trade da aprire come TASK-1237.

---

### TASK-1237: Persistere entry_commission/exit_commission e fee_tier_certified per-trade — 🟡 Media

> **Origine:** TASK-1236 ha confermato che le colonne `entry_commission`/`exit_commission` su `scalping_trades` sono NULL per tutti gli 8 trade della sessione 4a42133e. Il flag `fee_tier_certified` è disponibile solo a livello sessione (`scalping_sessions`), non per-trade.
>
> **Obiettivo:** popolare `entry_commission` e `exit_commission` per ogni trade chiuso, e aggiungere un campo `fee_tier_certified` su `scalping_trades` per tracciare se le fee di quel trade erano certificate o fallback.
>
> **File da modificare:**
> - `scalping/candle_processor.py` — alla chiusura posizione, passare commissioni calcolate
> - `scalping/trade_executor.py` — `_close_position_and_record()` salvare commissioni
> - `scalping/rest/session.py` — INSERT/UPDATE trade includere campi fee
>
> **Verifica di completamento:** dopo una sessione demo con più trade, query su `scalping_trades` mostra `entry_commission`/`exit_commission` popolati e `fee_tier_certified` coerente col log `[NET_PRICING]`.

---

### Punto 4 (pesi signal score) — 🟡 Fermo

> **Stato:** Confermato nessuna azione da intraprendere ora — coerente con TASK-1159 bloccato. Resta in attesa di revisione pesi futura.