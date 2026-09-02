# TASKS.md — SynthTrade Task Tracking

> **Aggiornato:** 2026-09-02. Task completati in `docs/ARCHIVE_TASKS.md`.

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

### TASK-1252 — Ricalibrare Peso Signal Score nella Decisione ✅ (Fase 1 completata)

**Stato:** Fix pipeline completato il 2026-09-02. Fase 2 (ricalibrazione soglia score) da fare dopo 30 trade.

**Fix applicato (Fase 1 — TASK-1252 fix):**
Diagnosi sessione B (25ago-1set, 7gg, 1 solo trade): il filtro TASK-1242 in `candle_processor.py` bloccava tutti i `mean_reversion_override` quando `btc_price < ema20_4h`. I 228 override approvati dall'aggregator non raggiungevano l'esecuzione. Fix: il filtro `btc < ema20_4h` è ora esente per `is_mean_reversion_override=True`. Il filtro `change_1h < -0.5%` rimane attivo per tutti. Commit `5228ac0`.

**Fase 2 — ancora da fare (dopo 30 trade live):**

**Problema:** Il signal score (prodotto dall'intelligenza collettiva dei collector) ha correlazione storica con il PnL ≈ 0.004 — praticamente zero. Nonostante questo, viene usato come gate di ingresso con soglia 6.0: qualsiasi score sotto soglia blocca il trade, qualsiasi score sopra lo sblocca. In pratica si blocca o sblocca il trading sulla base di un numero che non predice nulla.

Il TASK-1159 era bloccato per campione insufficiente — ora il campione c'è (48 trade, 14 giorni, due set indipendenti). Il problema è confermato statisticamente.

**Perché aspettare:** Con il fix TASK-1252 appena attivato, il mix di trade cambierà. La correlazione score→PnL potrebbe cambiare. Calibrare sui dati vecchi produrrebbe una soglia errata.

**Soluzione da implementare (tre opzioni, scegliere dopo revisione dati):**
1. **Ricalibrare la soglia** sui dati reali: se score non predice, abbassare la soglia o renderla dinamica per combinazione regime/strategia
2. **Ridurre peso score** nella combined confidence: da `score_norm * 0.3 + tech * 0.7` a `score_norm * 0.1 + tech * 0.9` — già il 70% è tecnico, riducendo ulteriormente si dà più peso al segnale direzionale
3. **Sostituire lo score** con indicatori che abbiano correlazione misurata (es. trend macro, regime confidence)

**File coinvolti:**
- `synthtrade/backend/app/scalping/engine/signal_aggregator.py:384-401` — combined confidence formula
- `synthtrade/backend/app/scalping/config_loader.py` — soglia `SCALPING_SIGNAL_STRENGTH_THRESHOLD` (modificabile via DB)
- `synthtrade/backend/app/scalping/supervisor/historical_context.py` — dati storici per ricalibrazione

**Criteri di accettazione:**
- [ ] Analisi correlazione score→PnL su dati post-TASK-1252 fix (almeno 30 trade)
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

### TASK-1256 — SL/TP e Trailing Per-Strategia (Architettura)

**Priorità:** 🔴 Alta — prerequisito per TASK-1257 e TASK-1258

**Problema:**
Attualmente esiste un **unico set globale** di SL/TP/trailing letto da `risk_config` in `_execution_state`. Questo si applica identico a tutte le strategie, indipendentemente dalla loro natura:

| Strategia | Natura | Hold tipico | Oscillazione BTC-EUR tipica | SL/TP ideale |
|-----------|--------|-------------|----------------------------|--------------|
| `rsi_bollinger` | Mean-reversion ranging | 20–90 min | ±0.2–0.5% | SL stretto, TP stretto |
| `ema_cross` | Trend-following | 2–8h | ±0.5–1.5% | SL più largo, TP largo |
| `vwap_reversion` | Mean-reversion intraday | 15–45 min | ±0.15–0.4% | SL strettissimo, TP stretto |

Usare TP=0.8%/SL=0.5% per `rsi_bollinger` significa aspettare un movimento lordo di ~1.0% in ranging — movimento raro che spesso non arriva entro l'oscillazione naturale del regime. La stessa coppia per `ema_cross` è invece troppo stretta: prende profit troppo presto mentre il trend continua.

Anche il **trailing stop** è configurato globalmente (`BE_TRIGGER=0.15%`, `STEP=0.15%`, `BUFFER=0.10%`). Con TP=0.55% (proposto per `rsi_bollinger`), il trigger scatterebbe al 27% del TP — troppo presto.

**Soluzione:**
Aggiungere nella `scalping_runtime_config` (DB) e nel `config_loader.py` la possibilità di definire SL/TP/trailing **per-strategia**, con fallback ai globali se non specificati.

**Pattern di lettura in `candle_processor.py`:**
```python
strategy_name = _execution_state.get('loop')._strategy.name  # es. "rsi_bollinger"
key_sl = f"STRATEGY_{strategy_name.upper()}_SL_PCT"
sl_pct = float(risk_cfg.get(key_sl, risk_cfg.get("stop_loss_pct", 0.5)))
key_tp = f"STRATEGY_{strategy_name.upper()}_TP_PCT"
tp_pct = float(risk_cfg.get(key_tp, risk_cfg.get("take_profit_pct", 0.8)))
```

Lo stesso pattern va esteso ai parametri trailing/break-even in `break_even.py`.

**File coinvolti:**
- `synthtrade/backend/app/scalping/candle_processor.py` — lettura SL/TP al momento del trade (L.825-827)
- `synthtrade/backend/app/scalping/break_even.py` — lettura break-even/trailing trigger (L.54-56, L.326-328)
- `synthtrade/backend/app/scalping/config_loader.py` — properties per-strategia con fallback
- `synthtrade/backend/app/scalping/rest/position.py` — position card legge SL/TP (L.73-74)
- `synthtrade/backend/app/scalping/router.py` — SL/TP per restore posizioni (L.148-149)

**Note implementative:**
- **Non modificare** il DB schema — i nuovi parametri vanno in `scalping_runtime_config` come chiavi aggiuntive (già supportate)
- Il supervisor AI può impostare i parametri per-strategia via `scalping_runtime_config` (nessuna modifica al supervisor necessaria)
- Test: verificare il fallback (no override → usa globale) e l'override (valore strategia usato se presente)

**Criteri di accettazione:**
- [ ] `candle_processor.py` legge SL/TP per-strategia con fallback al globale
- [ ] `break_even.py` legge trigger/step/buffer trailing per-strategia con fallback
- [ ] `config_loader.py` espone helper `sl_pct_for_strategy(name)` e `tp_pct_for_strategy(name)`
- [ ] La position card mostra i valori effettivi usati (per-strategia se configurati)
- [ ] Test fallback: globale usato se non c'è override per strategia
- [ ] Test override: valore strategia usato se chiave DB presente

---

### TASK-1257 — Calibrazione Valori SL/TP Per-Strategia (Dipende da TASK-1256 + 30 trade)

**Priorità:** 🟡 Media — dopo TASK-1256 e almeno 30 trade post-TASK-1252

**Problema:**
Una volta che TASK-1256 abilita i valori per-strategia, è necessario determinare i valori ottimali. I valori attuali (SL=0.5%, TP=0.8%) sono un compromesso globale non ottimale per nessuna strategia.

**Analisi base con fee reali OKX (taker=0.10% — verificato da DB):**

Round-trip fee drag = `1 - (1-0.001)² ≈ 0.20%`

| Strategia | SL netto proposto | TP netto proposto | WR breakeven | Razionale |
|-----------|------------------|------------------|--------------|-----------|
| `rsi_bollinger` | **0.35%** | **0.55%** | 38.9% | Ranging: oscillazioni tipiche BTC-EUR 0.2–0.5%; TP più raggiungibile |
| `ema_cross` | **0.60%** | **1.20%** | 33.3% | Trend: posizioni più lunghe; R:R 1:2 migliora expectancy |
| `vwap_reversion` | **0.25%** | **0.45%** | 35.7% | Trade brevi su dip VWAP, movimenti piccoli ma rapidi |

**Movimenti lordi equivalenti:**

| Strategia | SL lordo richiesto | TP lordo richiesto | Attuale SL lordo | Attuale TP lordo |
|-----------|-------------------|-------------------|-----------------|-----------------|
| `rsi_bollinger` | ~0.15% | ~0.75% | ~0.30% | ~1.00% |
| `ema_cross` | ~0.40% | ~1.40% | ~0.30% | ~1.00% |
| `vwap_reversion` | ~0.05% | ~0.65% | ~0.30% | ~1.00% |

> ⚠️ **SL lordo 0.15% per `rsi_bollinger` è molto stretto.** Su BTC-EUR in ranging, una normale oscillazione intracandle può colpire lo stop anche in direzione favorevole. Va misurato il tasso di "stop prematuro" sui dati reali prima di confermare il valore 0.35% netto.

**Metodo di calibrazione (da applicare sui 30+ trade post-TASK-1252):**
1. Estrarre dal DB: `entry_price`, `exit_price`, `close_reason`, `strategy_type`, `high_during_trade`, `low_during_trade` (o ricostruire da candle buffer)
2. Per ogni trade calcolare Max Favorable Excursion (MFE) e Max Adverse Excursion (MAE)
3. `TP_ottimale` ≈ 60° percentile del MFE per strategia → hit in 60% dei trade
4. `SL_ottimale` ≈ 25° percentile del MAE per strategia → falsa uscita solo nel 25% dei trade

**File coinvolti:**
- `synthtrade/backend/app/scalping/candle_processor.py` — usa i parametri per-strategia da TASK-1256
- `synthtrade/backend/app/scalping/config_loader.py` — aggiornamento defaults per-strategia
- DB `scalping_runtime_config` — chiavi `STRATEGY_RSI_BOLLINGER_SL_PCT`, `STRATEGY_EMA_CROSS_TP_PCT`, ecc.

**Criteri di accettazione:**
- [ ] Almeno 30 trade post-TASK-1252 con dati disponibili
- [ ] Analisi MFE/MAE per `rsi_bollinger` (strategia dominante attuale)
- [ ] Valori SL/TP scelti con WR breakeven ≤ WR osservato (expectancy ≥ 0)
- [ ] Simulazione: nuovi vs vecchi SL/TP sulle stesse entry → confronto PnL
- [ ] Monitoring 2 settimane post-cambio per conferma

---

### TASK-1258 — Calibrazione Trailing Stop Per-Strategia (Dipende da TASK-1256 + TASK-1257)

**Priorità:** 🟡 Media — dopo TASK-1256 e TASK-1257 completati

**Problema:**
I parametri trailing sono globali e assoluti. Con TP diversi per strategia, gli stessi valori assoluti producono comportamenti sproporzionati:

**Valori correnti:**
```
BREAK_EVEN_TRIGGER_NET_PCT   = 0.15%
BREAK_EVEN_LOCK_NET_PCT      = 0.05%
TRAILING_STEP_NET_PCT        = 0.15%
TRAILING_BUFFER_NET_PCT      = 0.10%
TRAILING_SAFETY_MARGIN_NET_PCT = 0.10%
```

**Problema con TP=0.55% (`rsi_bollinger` proposto):**
- BE trigger a +0.15% = **27% del TP** → troppo presto, rischio stop anticipato sul mean-reversion
- Solo 2 step possibili (0.15% + 0.30% = 0.45% < TP-SAFETY=0.45%) → trailing si esaurisce quasi subito
- Con TP breve, il trailing toglie quasi tutto il guadagno se il prezzo oscilla

**Problema con TP=1.20% (`ema_cross` proposto):**
- BE trigger a +0.15% = **12.5% del TP** → scatta troppo presto nel trend
- Step da 0.15% = solo 12.5% del range → passi troppo piccoli per un trend lungo
- Serve un trailing più "largo" per non essere stoppa prima che il trend si esaurisca naturalmente

**Parametri raccomandati per strategia (proporzionali al TP netto):**

Principio: `BE_TRIGGER ≈ 25% TP`, `STEP ≈ 20% TP`, `BUFFER ≈ 15% TP`, `SAFETY ≈ 12% TP`

| Parametro | Attuale | `rsi_bollinger` (TP=0.55%) | `ema_cross` (TP=1.20%) | `vwap_reversion` (TP=0.45%) |
|-----------|---------|---------------------------|------------------------|------------------------------|
| BE_TRIGGER | 0.15% | **0.14%** | **0.30%** | **0.11%** |
| LOCK_NET | 0.05% | **0.04%** | **0.08%** | **0.03%** |
| TRAILING_STEP | 0.15% | **0.11%** | **0.24%** | **0.09%** |
| TRAILING_BUFFER | 0.10% | **0.08%** | **0.18%** | **0.07%** |
| SAFETY_MARGIN | 0.10% | **0.07%** | **0.14%** | **0.05%** |

**Implementazione (approccio consigliato: valori assoluti per-strategia):**

Chiavi DB aggiuntive in `scalping_runtime_config`:
```
STRATEGY_RSI_BOLLINGER_BE_TRIGGER      = 0.14
STRATEGY_RSI_BOLLINGER_BE_LOCK         = 0.04
STRATEGY_RSI_BOLLINGER_TRAILING_STEP   = 0.11
STRATEGY_RSI_BOLLINGER_TRAILING_BUFFER = 0.08
STRATEGY_RSI_BOLLINGER_SAFETY_MARGIN   = 0.07
STRATEGY_EMA_CROSS_BE_TRIGGER          = 0.30
... ecc.
```

Il supervisor AI può aggiornare singoli parametri senza modifiche al codice.

**File coinvolti:**
- `synthtrade/backend/app/scalping/break_even.py` — lettura cfg con prefisso strategia + fallback (L.54-56, L.326-332)
- `synthtrade/backend/app/scalping/config_loader.py` — helper `trailing_params_for_strategy(name)`
- DB `scalping_runtime_config` — nuove chiavi `STRATEGY_*_BE_TRIGGER`, `STRATEGY_*_TRAILING_STEP`, ecc.

**Dipendenze:**
- TASK-1256 (infrastruttura per-strategia) — prerequisito
- TASK-1257 (TP/SL per-strategia determinati) — i trailing dipendono dal TP

**Criteri di accettazione:**
- [ ] `break_even.py` legge parametri trailing per-strategia con fallback al globale
- [ ] `config_loader.py` espone helper `trailing_params_for_strategy(name)` → dict
- [ ] Tabella proporzionale documentata e validata (come sopra)
- [ ] Simulazione: quanti trade si sarebbero chiusi anticipatamente (trailing hit < TP) con vecchi vs nuovi parametri
- [ ] `BREAK_EVEN_TRIGGER` ≈ 25% TP per ogni strategia (verificato)
- [ ] Il supervisor AI può aggiornare singoli parametri trailing via DB senza deploy

---

### TASK-1255 — Stop & Go: Auto-Restart Settimanale ✅


**Stato:** Completato il 2026-08-25

**Problema:** La sessione live accumula degradazione nel tempo (regime change, drift parametri, posizioni stale). Senza restart periodico, il bot continua con parametri obsoleti.

**Soluzione implementata:**
- **Backend:** `session_auto_restart.py` — job APScheduler ogni 15 min, verifica età sessione, stop+restart automatico dopo 7 giorni (aspetta chiusura posizioni aperte)
- **Frontend:** Checkbox "Stop & Go" nel pannello sessioni, countdown al prossimo restart, evento WS `session_auto_restarted` / `session_restart_pending`
- **DB:** Colonna `auto_restart_weekly` su `scalping_sessions`

**File coinvolti:**
- `synthtrade/backend/app/scalping/session_auto_restart.py` (nuovo)
- `synthtrade/backend/app/scalping/rest/session.py`
- `synthtrade/backend/app/scalping/_state.py`
- `synthtrade/backend/app/scheduler/jobs.py`
- `synthtrade/frontend/synthtrade-ui/src/app/scalping/models/session.model.ts`
- `synthtrade/frontend/synthtrade-ui/src/app/scalping/components/session-controls.component.ts`
- `synthtrade/frontend/synthtrade-ui/src/app/scalping/services/session-api.service.ts`
- `synthtrade/frontend/synthtrade-ui/src/app/scalping/services/scalping-ws.service.ts`
- `synthtrade/frontend/synthtrade-ui/src/app/scalping/components/scalping-dashboard.component.ts`

---

## Fase 1 — Log & Performance (Completata — vedi ARCHIVE_TASKS.md)

> TASK-1245 (Short-circuit SELL), TASK-1246 (Compact logging), TASK-1247 (Coalescing cicli), TASK-1250 (Macro trend filter), TASK-1251 (Override mean-reversion guard), TASK-1254 (Hold comparison supervisor), TASK-1255 (Stop & Go auto-restart) — tutti completati.
