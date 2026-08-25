# TASKS.md — SynthTrade Task Tracking

> **Aggiornato:** 2026-08-25. Task completati in `docs/ARCHIVE_TASKS.md`.

---

## Fase 2 — Trading Logic Fix (Priorità: trasformare il bot da perdente a profittevole)

### TASK-1250 — Filtro Macro Trend con Priorità sull'Override Mean-Reversion

**Problema:** Il regime detector classifica il 97% delle candele come "ranging" anche durante un rally sostenuto (+27% BTC). Questo attiva `rsi_bollinger` (mean-reversion) invece di `ema_cross` (trend-following). L'override mean-reversion bypassa il filtro bearish dell'intelligence e compra CONTRO il trend, con win rate misurato del 25%.

**Soluzione:** Aggiungere un filtro macro trend reale (EMA20/50 su timeframe 4h) che ha PRIORITÀ sull'override mean-reversion:
- Se BTC > EMA20/50 su 4h → non permettere override BUY-contro-bias bearish
- Se BTC > EMA20 su 4h → favorire ema_cross invece di rsi_bollinger nella strategy selector
- Il TASK-1242 "trend filter" blocca solo il caso "sotto EMA20" — serve anche il caso "sopra EMA20 → privilegia trend"

**File coinvolti:**
- `synthtrade/backend/app/scalping/engine/signal_aggregator.py:296-333` (override logic)
- `synthtrade/backend/app/scalping/engine/strategy_selector.py` (selezione strategia)
- `synthtrade/backend/app/scalping/candle_processor.py:621-634` (macro filter attuale)

**Criteri di accettazione:**
- [ ] Override mean-reversion bypassa il filtro bearish SOLO se BTC > EMA20 su 4h
- [ ] Strategy selector preferisce ema_cross quando BTC > EMA20 su 4h
- [ ] Log chiaro quando il filtro macro blocca un override
- [ ] Test: simulation con dati storici Aug 11-25 dimostra riduzione trade negativi

---

### TASK-1251 — Disabilitare o Vincolare Override Mean-Reversion su rsi_bollinger

**Problema:** L'override mean-reversion su rsi_bollinger ha win rate misurato del 25% su due campioni indipendenti (12 trade分析 + 48 trade sessione). Con SL 0.50%/TP 0.80%, l'expectancy è matematicamente negativa: `0.25×0.80 − 0.75×0.50 ≈ -0.17% per trade`.

**Soluzione:** Due opzioni (da valutare quale implementare):
1. **Disabilitare completamente** l'override su rsi_bollinger — il regime detector, se davvero rileva ranging genuino, userà rsi_bollinger senza la scappatoia dell'override
2. **Vincolare l'override** a condizioni specifiche che lo rendono selettivo:
   - Solo se bias è debolmente negativo (score tra -5 e -10), non forte (score < -15)
   - Solo se trend_5m è positivo o neutro (non diverging negativo)
   - Solo se regime confidence è bassa (< 0.6) — regime incerto = possibile ranging

**File coinvolti:**
- `synthtrade/backend/app/scalping/engine/signal_aggregator.py:296-333`
- `synthtrade/backend/app/scalping/engine/signal_aggregator.py:276-294` (bias conflict)

**Criteri di accettazione:**
- [ ] Override mean-reversion non viene più eseguito quando bias è forte bearish (score < -15)
- [ ] Log chiaro quando l'override viene bloccato vs consentito
- [ ] Test: su dati storici, override attivato solo in condizioni selezionate
- [ ] Win rate dell'override migliora rispetto al 25% misurato

---

### TASK-1252 — Ricalibrare Peso Signal Score nella Decisione

**Problema:** Il signal score ha correlazione storica con PnL ≈ 0.004 (nessuna). Tenerelo come gate di ingresso (soglia 6.0) sta bloccando/sbloccando trade sulla base di un numero che non predice nulla. Il TASK-1159 era bloccato per campione insufficiente — ora il campione c'è (48 trade, 14 giorni).

**Soluzione:** Tre opzioni (da valutare):
1. **Ricalibrare la soglia** basandosi sui dati reali: se lo score non predice, abbassare la soglia o renderla dinamica in base al win rate storico per combinazione regime/strategia
2. **Ridurre il peso dello score** nella combinazione finale: `score_norm * 0.3 + tech_confidence * 0.7` → ridurre a `score_norm * 0.1 + tech_confidence * 0.9` o simile
3. **Sostituire lo score** con un indicatore che abbia correlazione misurata con il PnL (es. trend macro, regime confidence)

**File coinvolti:**
- `synthtrade/backend/app/scalping/engine/signal_aggregator.py:384-401` (combined confidence)
- `synthtrade/backend/app/scalping/config_loader.py` (soglia configurabile)
- `synthtrade/backend/app/scalping/supervisor/historical_context.py` (dati storici)

**Criteri di accettazione:**
- [ ] La soglia o il peso dello score è calibrato sui dati reali della sessione
- [ ] Il sistema non blocca/sblocca trade basandosi su numeri non predittivi
- [ ] Test: confronto win rate PRIMA vs DOPO la ricalibrazione
- [ ] Log della soglia corrente nel context del supervisor

---

### TASK-1253 — Rivedere Asimmetria SL/TP in Funzione del Win Rate Reale

**Problema:** SL 0.50% / TP 0.80% richiede win rate > 38% per pareggio (ignorando fee). Il win rate reale della combinazione regime/strategia attuale è ~25-30%. L'asimmetria è sfavorevole.

**Soluzione:** Tre opzioni (da valutare):
1. **Allargare il TP** (es. da 0.80% a 1.20%) per aumentare il reward per trade vincente
2. **Stringere meno lo SL** (es. da 0.50% a 0.35%) per ridurre la perdita per trade perdente
3. **Smettere di fare trade** in combinazioni regime/strategia con win rate < 38% — il regime detector dovrebbe bloccare le combinazioni non profittevoli

**File coinvolti:**
- `synthtrade/backend/app/scalping/config_loader.py` (SL/TP configurabili via DB)
- `synthtrade/backend/app/scalping/engine/strategy_selector.py` (blocco combinazioni)
- `synthtrade/backend/app/scalping/supervisor/historical_context.py` (dati per decisione)

**Criteri di accettazione:**
- [ ] SL/TP aggiustati in base al win rate reale misurato
- [ ] Oppure: regime selector blocca combinazioni con win rate < 38%
- [ ] Test: simulazione con nuovi parametri dimostra expectancy positiva
- [ ] Log del win rate per combinazione regime/strategia nel context supervisor

---

### TASK-1254 — Aggiungere Confronto vs Hold al Context Supervisor (Completato)

**Problema:** Il supervisor AI non vede il confronto tra la performance del bot e un semplice buy-and-hold. Questo gli impedisce di prendere decisioni informate su quando mettere in pausa o cambiare strategia.

**Soluzione:** Aggiungere `hold_return_pct` e `vs_hold_gap` al context del supervisor AI, calcolati dal rapporto prezzo corrente BTC / prezzo iniziale sessione.

**Stato:** ✅ Completato in commit `b9a512b` (Fase 1)

**File coinvolti:**
- `synthtrade/backend/app/ai/supervisor_context.py`
- `synthtrade/backend/app/scalping/supervisor/supervisor_client.py`
- `synthtrade/backend/app/scalping/supervisor/supervisor_scheduler.py`

---

## Fase 1 — Log & Performance (Completata)

### TASK-1245 — Short-Circuit SELL Signals ✅
### TASK-1246 — Compact Logging ✅
### TASK-1247 — Coalescing Cicli Identici ✅

---

## Precedenti (da verificare stato)

### Punto 4 (pesi signal score) — 🟡 Fermo

> **Stato:** Confermato nessuna azione da intraprendere ora — coerente con TASK-1159 bloccato. Resta in attesa di revisione pesi futura. **ORA SBLOCCATO** dai dati della sessione 11-25 agosto (48 trade, 14 giorni).
