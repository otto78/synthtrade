# TASKS.md — SynthTrade Task Tracking

> **Aggiornato:** 2026-08-25. Task completati in `docs/ARCHIVE_TASKS.md`.

---

## Fase 2 — Trading Logic Fix (In corso — obiettivo: bot profittevole)

> **Contesto generale Fase 2:** L'analisi statistica della sessione 11-25 agosto 2026 (48 trade, 14 giorni) ha rivelato che il bot aveva un win rate globale del ~25-30%, con expectancy negativa. Le cause principali:
> 1. Il regime detector classificava il 97% delle candele come "ranging" → attivava `rsi_bollinger` (mean-reversion) anche durante un rally BTC +27%.
> 2. L'override mean-reversion bypassava il filtro bearish dell'intelligence e apriva BUY contro-trend.
> 3. Il signal score aveva correlazione ≈0 con il PnL ma veniva usato come gate d'ingresso.
> 4. SL/TP asimmetrici richiedono win rate >38% per pareggio, ma il bot reale era al 25-30%.
>
> **TASK-1250 e TASK-1251 sono stati completati il 2026-08-25** e indirizzano le cause 1 e 2.
> I TASK sotto (1252, 1253) restano da fare e richiedono dati post-fix per essere calibrati correttamente.

---

### TASK-1252 — Ricalibrare Peso Signal Score nella Decisione

**Priorità:** 🟡 Media — aspettare 1 settimana di dati live post-TASK-1250/1251 prima di cambiare

**Problema:** Il signal score (prodotto dall'intelligenza collettiva dei collector) ha correlazione storica con il PnL ≈ 0.004 — praticamente zero. Nonostante questo, viene usato come gate di ingresso con soglia 6.0: qualsiasi score sotto soglia blocca il trade, qualsiasi score sopra lo sblocca. In pratica si blocca o sblocca il trading sulla base di un numero che non predice nulla.

Il TASK-1159 era bloccato per campione insufficiente — ora il campione c'è (48 trade, 14 giorni, due set indipendenti). Il problema è confermato statisticamente.

**Perché aspettare:** Con TASK-1250/1251 appena attivati, il mix di trade cambierà (meno mean-reversion contro-trend, più ema_cross con trend). La correlazione score→PnL potrebbe cambiare. Calibrare sui dati vecchi (regime sbagliato) produrrebbe una soglia errata.

**Soluzione da implementare (tre opzioni, scegliere dopo revisione dati):**
1. **Ricalibrare la soglia** sui dati reali: se score non predice, abbassare la soglia o renderla dinamica per combinazione regime/strategia
2. **Ridurre peso score** nella combined confidence: da `score_norm * 0.3 + tech * 0.7` a `score_norm * 0.1 + tech * 0.9` — già il 70% è tecnico, riducendo ulteriormente si dà più peso al segnale direzionale
3. **Sostituire lo score** con indicatori che abbiano correlazione misurata (es. trend macro, regime confidence)

**File coinvolti:**
- `synthtrade/backend/app/scalping/engine/signal_aggregator.py:384-401` — combined confidence formula
- `synthtrade/backend/app/scalping/config_loader.py` — soglia `SCALPING_SIGNAL_STRENGTH_THRESHOLD` (modificabile via DB)
- `synthtrade/backend/app/scalping/supervisor/historical_context.py` — dati storici per ricalibrazione

**Criteri di accettazione:**
- [ ] Analisi correlazione score→PnL su dati post-TASK-1250/1251 (almeno 30 trade)
- [ ] Soglia o peso dello score calibrato sui dati reali
- [ ] Il sistema non blocca/sblocca trade basandosi su numeri non predittivi
- [ ] Confronto win rate PRIMA vs DOPO la ricalibrazione
- [ ] Log della soglia corrente nel context supervisor

---

### TASK-1253 — Rivedere Asimmetria SL/TP in Funzione del Win Rate Reale

**Priorità:** 🟡 Media — aspettare 1 settimana di dati live post-TASK-1250/1251 prima di cambiare

**Problema:** SL 0.50% / TP 0.80% richiede win rate > 38% per pareggio (ignorando fee). Con fee taker 0.10%+0.10%, il break-even reale sale a ~42%. Il win rate reale della combinazione regime/strategia osservata era ~25-30%.

Formula expectancy attuale:
`E = 0.28 × 0.80% − 0.72 × 0.50% = 0.224% − 0.360% = −0.136% per trade`

Ovvero con 50 trade/settimana si perdono circa 0.7% del capitale per settimana solo per l'asimmetria, anche se il sistema funzionasse perfettamente.

**Perché aspettare:** Il win rate del 25-30% includeva tutti i trade sbagliati dell'override mean-reversion (risolto da TASK-1250/1251). Il win rate post-fix potrebbe essere significativamente più alto, rendendo SL/TP attuali adeguati. Aggiustare ora significherebbe ottimizzare su dati corrotti.

**Soluzione da implementare (scegliere dopo revisione dati):**
1. **Allargare TP** (es. 0.80% → 1.20%): più reward per trade vincente, ma hold più lungo → più rischio inversione
2. **Stringere SL** (es. 0.50% → 0.35%): meno perdita per trade perdente, ma più facile da colpire su volatilità normale
3. **Bloccare combinazioni sotto soglia win rate**: se regime=ranging + strategia=rsi_bollinger + macro=bearish ha win rate storico < 38%, non aprire trade in quella combinazione — il regime selector decide

**File coinvolti:**
- `synthtrade/backend/app/scalping/config_loader.py` — `SCALPING_STOP_LOSS_PCT`, `SCALPING_TAKE_PROFIT_PCT` (modificabili via DB)
- `synthtrade/backend/app/scalping/engine/strategy_selector.py` — blocco combinazioni per win rate
- `synthtrade/backend/app/scalping/supervisor/historical_context.py` — win rate per combinazione regime/strategia

**Criteri di accettazione:**
- [ ] Analisi win rate per combinazione regime/strategia su dati post-TASK-1250/1251 (almeno 30 trade)
- [ ] SL/TP aggiustati in base al win rate reale misurato, oppure combinazioni bloccate
- [ ] Simulazione con nuovi parametri dimostra expectancy positiva
- [ ] Log del win rate per combinazione nel context supervisor

---

## Fase 1 — Log & Performance (Completata — vedi ARCHIVE_TASKS.md)

> TASK-1245 (Short-circuit SELL), TASK-1246 (Compact logging), TASK-1247 (Coalescing cicli), TASK-1250 (Macro trend filter), TASK-1251 (Override mean-reversion guard), TASK-1254 (Hold comparison supervisor) — tutti completati.
