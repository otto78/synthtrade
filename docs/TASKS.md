# TASKS.md — SynthTrade Task Tracking

> **Aggiornato:** 2026-09-30 ~07:30 UTC. Task completati in `docs/ARCHIVE_TASKS.md`.
> **Stato suite:** 809 passed / 1 failed, lanciata **da `synthtrade/backend/`** (non dalla root). L'unico fallimento è `tests/unit/test_task_908.py::test_guard_does_not_affect_other_actions`, preesistente e non correlato.
> **In produzione:** TASK-1256 deployato 2026-09-25; TASK-1261 deployato 2026-09-29 ~14:00; TASK-1262 deployato 2026-09-29 15:44; TASK-1270 deployato 2026-09-30 ~07:25.
> **Handoff completo:** `docs/HANDOFF.md` — leggere prima di qualsiasi intervento.

---

## Fase 2 — Trading Logic Fix (In corso — obiettivo: bot profittevole)

> **Contesto generale Fase 2:** L'analisi statistica della sessione 11-25 agosto 2026 (48 trade, 14 giorni) ha rivelato che il bot aveva un win rate globale del ~25-30%, con expectancy negativa. Le cause principali:
> 1. Il regime detector classificava il 97% delle candele come "ranging" → attivava `rsi_bollinger` (mean-reversion) anche durante un rally BTC +27%.
> 2. L'override mean-reversion bypassava il filtro bearish dell'intelligence e apriva BUY contro-trend.
> 3. Il signal score aveva correlazione ≈0 con il PnL ma veniva usato come gate d'ingresso.
> 4. SL/TP asimmetrici richiedono win rate >38% per pareggio, ma il bot reale era al 25-30%.
>
> **TASK-1250 e TASK-1251 sono stati completati il 2026-08-25** e indirizzano le cause 1 e 2.
> **Analisi completa su 188 trade LIVE (luglio–settembre 2026):** vedere `docs/HANDOFF.md` §2.

---

### TASK-1261 — Supervisor: Fee Awareness, Memoria Cross-Sessione, Anti-Loop Pause ✅

**Stato:** ✅ Completato e deployato in LIVE 2026-09-29 ~14:00. Commit `77339b0` + `df9b67c` — push su `origin/main` completato il 2026-09-29 (erano rimasti locali fino al push di TASK-1262).

**Problemi risolti:**
1. **Stop&go stallo loop:** dopo restart, supervisor entrava in loop `no_action` perché vedeva 0 trade in sessione e applicava la regola "< 5 trade → no_action". Fix: se lo storico cross-sessione ha ≥ 20 trade, il gate viene bypasato e si usa la performance storica.
2. **Nessuna fee awareness:** il supervisor non sapeva che il breakeven WR reale è ~65% (non 38%). Fix: il contesto ora include `fee_info` con taker% e round-trip drag% calcolati a runtime da `_get_fee_rate()` / `_round_trip_fee_drag_pct()`.
3. **Anti-loop pause:** pattern `pause_trading` + `update_threshold` alternati sugli stessi dati. Fix: cooldown 30 min su `pause_trading` in `supervisor_scheduler.py` (campo `_last_pause_time`).
4. **History troppo corta:** solo ultime 10 decisioni, sparivano in minuti con 144 decisioni/giorno. Fix: estesa a 20 voci con `blocked_reason` visibile.
5. **System prompt hardcoded:** conteneva `BTC-EUR`, `OKX`, valori numerici storici BTC-EUR specifici. Fix: prompt generico con formula breakeven dinamica, riferimento al blocco `=== FEE REALI ===` nel contesto.

**Verifica post-deploy:** Prima decisione (14:00:30) il supervisor ha correttamente: applicato l'eccezione stop&go (186 trade ≥ 20), calcolato breakeven WR 65% dai dati runtime, concluso che `rsi_bollinger/ranging` WR 35.8% è strutturalmente perdente, emesso `no_action` perché non esiste alternativa migliore.

**File modificati:**
- `synthtrade/backend/app/ai/supervisor_context.py` — `fee_info` injection, `session_just_started`, history × 20
- `synthtrade/backend/app/scalping/supervisor/supervisor_client.py` — system prompt v3, `_format_context` fee block
- `synthtrade/backend/app/scalping/supervisor/supervisor_scheduler.py` — `_last_pause_time`, cooldown 30 min

---

### TASK-1262 — Fix Bias Strutturali nel Signal Scoring Engine

**Priorità:** 🔴 Alta — il bot non apre trade da 2026-09-29 08:22 (sessione `5c7e9329` → `a12483b5`)

**Analisi:** Vedere `docs/HANDOFF.md` §3 per la diagnosi completa con dati.

> ⚠️ **Correzione 2026-09-29 (misurata su 68 snapshot reali di `/tmp/opencode/s2.log`).**
> La diagnosi iniziale sovrastimava i bias. Contributi medi effettivi dei collector
> con score disponibile: **Fear & Greed −2.700**, OBI −0.634, funding −0.524,
> **Long/Short Ratio +0.208**. Totale −3.554 su peso 0.95 → **score normalizzato −3.741**.
> L'LSR era a **~49%**, non 63%, e contribuiva **positivamente**: la tabella sotto
> riporta la versione originaria del task, non i dati verificati.

**Problema in sintesi (dati originari, non verificati):** Su 9 collector attivi (peso > 0), solo `order_book_imbalance` è dinamico per BTC-EUR. Tre bias permanenti abbassavano lo score di circa −4.3 punti:

| Causa | Contributo dichiarato | Contributo misurato | Natura |
|-------|----------------------|---------------------|--------|
| Long/Short Ratio (~63% long BTC) | −2.2 pt | **+0.208 pt** | Valore assoluto ~costante, ma non bearish |
| Fear & Greed (73 oggi) | −2.1 pt | **−2.700 pt** | Aggiornato 1×/giorno, drag costante |
| CVD (baseline 1000 hardcoded) | 0 pt (peso sprecato) | ~0 (+0.042) | Volume BTC-EUR << 1000 |

Il bias dominante è quindi **Fear & Greed**, non l'LSR. L'LSR resta da correggere
per un motivo diverso e valido: è una costante, quindi non contiene informazione.

Distribuzione reale (68 snapshot, soglia |score| ≥ 6.0): **bullish 0 (0.0%)**, bearish 11 (16.2%), neutro 57 (83.8%).

**Fix 1 — Long/Short Ratio: usare variazione rispetto alla media mobile recente**
- **Perché:** BTC ha strutturalmente 60-65% long → il valore assoluto non dice nulla di nuovo. Quello che conta è se oggi è *più* o *meno* long del recente storico.
- **Implementazione:** `LongShortRatioCollector` mantiene un buffer delle ultime `N` letture. Il metodo `ratio_to_score` riceve anche la media recente e produce un delta normalizzato: +100 se long% in forte calo (bullish), −100 se in forte crescita (bearish).
- **Parametro:** `_LSR_LOOKBACK = 12` letture. ⚠️ Il collector gira ogni `SCALPING_INTEL_UPDATE_INTERVAL_SEC=60` ma l'endpoint OKX ha `period=5m`: per coprire ~60 min servono 12 **letture distinte**, non 12 campioni. Senza dedupe lo storico si riempirebbe di duplicati e coprirebbe soltanto 12 minuti. Implementato `_record_reading()` con dedupe sui valori consecutivi identici.
- **Correzione implementativa:** `collect()` accoda la lettura **prima** che l'engine chieda la baseline, quindi `get_baseline()` esclude esplicitamente l'ultimo elemento. Senza questa esclusione il delta è smorzato di N/(N+1) e un cambio di regime resta invisibile. Warmup (`< 2` letture): contributo 0 e il peso dell'LSR è escluso dal denominatore di normalizzazione.

**Fix 2 — Fear & Greed: peso da 0.10 → 0.03**
- **Perché:** Pesa 10.5% normalizzato ma cambia 1×/giorno → contributo −2.1 punti fissi. Non è un segnale per-minuto. Ha senso come gate estremo (F&G < 20 o > 80) ma non come componente continua dello score.
- **Implementazione:** basta modificare `DEFAULT_WEIGHTS["fear_greed"]` da `0.10` a `0.03`. La logica `value_to_score` rimane invariata (i valori estremi < 20 / > 80 continuano a produrre score significativi anche con peso ridotto).

**Fix 3 — CVD: baseline dinamica proporzionale al volume osservato**
- **Perché:** Baseline hardcoded `Decimal("1000")` in due punti del codice. BTC-EUR su OKX spot ha volumi da 0.05–0.2 BTC per candela → CVD << 1000 → score sempre ~0–2%. Il 15.8% del peso non contribuisce mai.
- **Implementazione:** `CVDCalculator` espone `get_dynamic_baseline()` che restituisce la media del CVD assoluto massimale visto nelle ultime `M` finestre di reset. `signal_score_engine.py` chiama questo metodo invece di usare `Decimal("1000")`.
- **⚠️ Deviazione deliberata dal lower bound di 5.0 BTC specificato inizialmente.** Con un floor di 5.0 la baseline dinamica sarebbe stata comunque `max(5.0, ~0.2) = 5.0` su BTC-EUR, cioè 25× la scala reale: il rapporto CVD/baseline restava sotto 0.2 e il fix era **privo di effetto proprio nel caso che doveva risolvere**. Il lower bound è stato ridotto a `BASELINE_FLOOR = Decimal("0.01")`, un puro epsilon anti divisione-per-zero. Verificato da `test_dynamic_baseline_floor_does_not_dominate_real_scale`.
- **🐛 Bugfound in LIVE e corretto lo stesso giorno (commit `80f8862`).** Il floor epsilon da solo **non bastava**: `window_size` è 1000 trade ma la grace period ne richiede solo 100, quindi fra trade 100 e 1000 il CVD veniva valutato con una baseline inesistente, restituita come epsilon. `cvd_to_score` saturava a ±100 e il CVD contribute **un +15,0 costante** (peso 0.15 × 100) — il bias strutturale che il task voleva eliminare, invertito di segno. Confermato in LIVE: `cvd=OK(w=0.15,s=100.0)`.
  Correzione: `get_dynamic_baseline()` ritorna `None` finché nessuna finestra è chiusa, e l'engine esclude il CVD da score e normalizzazione in quel caso — stesso pattern già usato per l'LSR. Il log diagnostico dichiara ora `cvd=WARMUP` invece di un `s=0.0` fuorviante. Regressione coperta da `test_cvd_excluded_without_baseline`.
- **Interazione da conoscere:** la grace period usa `_trades_since_reset`, che si azzera a ogni finestra. Quindi il CVD è escluso per i primi 100 trade **di ogni** finestra da 1000, cioè ~10% del tempo. Voluto: un CVD parziale confrontato con la media delle finestre chiuse è rumore.
- **Nota:** il default `cvd_to_score(..., baseline=Decimal("1000"))` è mantenuto solo per compatibilità con i chiamanti esistenti; l'engine passa sempre la baseline dinamica.

**File coinvolti:**
- `synthtrade/backend/app/scalping/intelligence/collectors/long_short_ratio.py`
- `synthtrade/backend/app/scalping/intelligence/signal_score_engine.py`
- `synthtrade/backend/app/scalping/intelligence/collectors/cvd_calculator.py`

**Test aggiornati/aggiunti** (le path in `tests/unit/` indicate originariamente non esistono; i test reali sono in `tests/scalping/`):
- `tests/scalping/test_long_short_ratio.py` — delta, baseline, esclusione corrente, dedupe, `maxlen`
- `tests/scalping/test_cvd_calculator.py` — baseline dinamica, floor, storico bounded, scala reale vs hardcoded
- `tests/scalping/test_signal_score_engine.py` — peso F&G 0.03

**Impatto misurato (ricalcolo riga per riga sui 68 snapshot reali, solo Fix 2 ricostruibile dal log):**

| Metrica | Prima | Dopo Fix 2 | Delta |
|---------|-------|-----------|-------|
| Score normalizzato medio | −3.741 | −1.891 | **+1.850** |
| Score massimo osservato | +2.17 | +4.49 | +2.32 |
| Snapshot bullish (> +6) | 0 (0.0%) | **0 (0.0%)** | 0 |
| Snapshot bearish (< −6) | 11 (16.2%) | 4 (5.9%) | −11.3 pp |
| Snapshot neutro | 57 (83.8%) | 64 (94.1%) | +10.3 pp |

Fix 1 e Fix 3 non sono ricostruibili dallo storico (servono le letture LSR e le finestre CVD, non presenti nelle righe di log). Qualitativamente Fix 1 sostituisce un contributo costante (+0.208) con uno a media ~0, e Fix 3 rende il 15% del peso effettivamente utilizzabile.

> 🔴 **Il task NON sblocca da solo l'apertura di BUY.** Dopo i fix il bias si riduce quasi a zero (−1.89) ma **nessuno dei 68 snapshot supera +6.0**: il segnale bullish resta a 0. Il constraint residuo non è più il bias dei collector ma l'ampiezza del segnale. L'unico collector realmente dinamico è l'OBI (peso 0.30, range misurato −45.1..+16.6): per sfondare +6 serve che OBI si accenda da solo, evento raro (≈1% delle candele secondo l'handoff). Ricalibrare la soglia 6.0 o rivedere i pesi è **TASK-1252 fase 2**, fuori scope qui.

**Criteri di accettazione:**
- [x] Bias strutturale da L/S Ratio neutralizzato: contributo LSR ora un delta rispetto alla media mobile, media ~0 invece di una costante
- [x] Peso F&G ridotto a 0.03: contributo misurato −2.700 → −0.810 (−69%)
- [x] CVD baseline dinamica: scala reale 0.2 BTC gestita correttamente, floor non più dominante
- [x] Suite test: **804 passed, 1 failed** (HEAD baseline: 791 passed, 1 failed — lo stesso fallimento preesistente `tests/unit/test_task_908.py::test_guard_does_not_affect_other_actions`, fuori scope, introdotto da TASK-1261). Nessuna regressione.
- [x] Deploy VPS + verifica distribuzione score — deploy eseguito 15:44:23 UTC, pesi e coverage verificati nei log LIVE
- [ ] Bot apre almeno 1 trade nelle prime 4h post-deploy — **attendibile solo se il regime lo consente; vedi nota sopra**

**Stato:** ✅ **COMPLETATO, COMMITTATO E IN LIVE** — commit `4ff3073` (push su `origin/main` 2026-09-29). Deploy avvenuto alle 15:44:23 UTC, pochi secondi prima dell'avvio del container (15:44:27): i tre file di TASK-1262 erano già in `/app`, quindi il processo in esecuzione gira il codice nuovo. Confermato nei log LIVE:

```
[ScoreEngine] COLLECTORS: btc-eur | ... fear_greed=OK(w=0.03,s=-19.5) ...
[ScoreEngine] COVERAGE: btc-eur total=0.88 responded=0.58
```

`w=0.03` (era 0.10) e `total=0.88` (era 0.95) verificano il Fix 2 attivo. `long_short_ratio=OK(w=0.10,s=0.0)` con score a zero è il comportamento atteso durante il warmup: senza baseline il collector è escluso dal punteggio e contribuisce 0. Dopo ~12 letture distinte (≈60 min, dato `period=5m` dell'endpoint) inizierà a produrre delta reali.

> **Nota su HANDOFF §3:** la sezione riporta l'LSR a 63% con contributo −2.2 pt e un totale di −5.0. Entrambi i valori sono contraddetti dai log reali (49% e +0.208, totale −3.741). Se HANDOFF viene usato come riferimento, leggerlo con questa correzione.

---

### TASK-1270 — Fill OCO non riconosciuto in tempo reale: posizione bloccata fino al riavvio ✅

**Stato:** ✅ **COMPLETATO, COMMITTATO E IN LIVE** — commit `5a30950` (push 2026-09-30 ~07:25). Deploy e restart container verificati. **Fix in attesa di conferma LIVE** (vedi "Verifica su campo" sotto).

**Priorità:** 🔴 Alta — durante l'incidente la posizione è rimasta aperta ~14h bloccando ogni nuovo ingresso.

**Problema (incidente LIVE 2026-09-29):**
Un BUY BTC-EUR aperto alle 16:48 (`73350.3`, qty `0.00027266`, OCO `3966069478195580928`) è stato chiuso dallo stop loss su OKX alle **16:53:57** a `73268.1`. La posizione però è rimasta **aperta su app e DB** per ~14 ore, con l'OKX completamente flat (nessun ordine, nessun algo order). Risolto solo al riavvio del container del 2026-09-30 06:47 (`Recovered verified OCO fill`, `reason=stop_loss`, `pnl=-0.06`).

**Root cause — non era un listener caduto.** L'UDS era connesso e l'evento era arrivato regolarmente. La catena:

1. `trade_executor.py` riceve l'evento OCO ~1s dopo l'esecuzione, ma **senza prezzo**. Il codice lo documenta già: `orders-algo-history` può riportare l'OCO `effective` prima che il prezzo del fill figlio sia esposto.
2. Il delegate delega quindi a `_reconcile_position_with_exchange`, che leggeva correttamente `balance=0` (posizione chiusa) ma interrogava `orders-algo-history` **una sola volta**.
3. La history di OKX è *eventually consistent*: la lookup emessa subito dopo il trigger non trovava ancora il leg con `state="effective"`.
4. La funzione loggava `retaining local trade for retry` e restituiva `None` — ma **quel retry non esisteva mai**. L'unico retry era in `_on_uds_reconnect_sync()`, mai scattato perché l'UDS non si era disconnesso.

Risultato: la posizione restava aperta e bloccava l'apertura di nuovi trade finché un riavvio non riconciliava.

**Fix implementato** (`reconciliation.py`):
- Estratto `_await_verified_bracket_fill()`: esegue il **polling** con la stessa tolleranza già misurata in TASK-1175 (OKX propaga in 1-5s), applicata ora anche al path normale "balance dice chiusa" e non solo al ramo di errore del balance check.
- Il ramo di errore del balance check è stato riallineato allo stesso helper, eliminando il codice duplicato.
- Se il fill non diventa visibile dopo il polling, il log passa da `WARNING` a `ERROR` con messaggio esplicito: la posizione **bloccherà nuovi ingressi** fino a un riavvio. Visibile all'operatore invece che silenziosamente trattenuto.
- Costanti di modulo `FILL_VISIBILITY_ATTEMPTS` / `FILL_VISIBILITY_DELAY` risolte a call time (non come default di parametro), così restano l'unica fonte di verità ed overridabili nei test.

> **Nessuna periodicità aggiunta.** Il retry è **event-driven**: scatta solo quando un fill è già avvenuto. Non è un reconcile periodico, che resta un fallback non implementato (vedi TASK-1271).

**Test aggiunti** (`tests/unit/test_reconcile_position.py`):
- `test_scenario_F_retries_until_algo_fill_propagates` — riproduce l'incidente LIVE: le prime 2 lookup non trovano il fill, la 3ª lo recupera (`73268.1`, `reason=stop_loss`).
- `test_scenario_G_never_closes_on_unverified_fill` — la sicurezza di TASK-1184 resta prioritaria: se il fill non è mai verificato, il trade **non** viene chiuso con un prezzo sintetico, nemmeno dopo i retry.

**Criteri di accettazione:**
- [x] Root cause identificata con evidenza da log/DB/OKX reali, non da assunzioni
- [x] Retry sul path normale "balance chiusa + fill non ancora visibile"
- [x] Nessuna chiusura sintetica su fill non verificato (TASK-1184 preservata)
- [x] Codice duplicato unificato in un solo helper
- [x] Suite: **809 passed, 1 failed** — l'unico fallimento è `tests/unit/test_task_908.py::test_guard_does_not_affect_other_actions`, **preesistente e non correlato**
- [x] Commit `5a30950` pushato e deployato; reconcile mostra le 3 query a ~0.66s di distanza nei log
- [ ] **Verifica su campo:** nessuno stop/take-profit è scattato dopo il deploy. La conferma LIVE arriverà alla prossima chiusura del trade `e90d8f77` (entry `73111.5`). Finché non succede, il fix è "corretto e testato", non ancora "verificato in LIVE".

**File coinvolti:**
- `synthtrade/backend/app/scalping/reconciliation.py` — helper di polling, costanti, log `ERROR`, deduplicazione
- `synthtrade/backend/tests/unit/test_reconcile_position.py` — scenari F e G

---

### TASK-1271 — Fallback: reconcile periodico delle posizioni aperte ⏸️

**Stato:** ⏸️ **SOSPESA — in attesa di dati.** Non implementata. **Non è un bug noto**, è una rete di sicurezza opzionale per un caso non ancora osservato.

**Priorità:** 🟡 Bassa — aprire **solo se** il problema si ripresenta.

**Perché è sospesa e non fatta subito:** TASK-1270 ha risolto la causa (lookup singola su history eventually consistent) con un polling event-driven. Il residuo è un caso che **non è mai stato osservato**: se il fill di un OCO non diventa visibile nemmeno dopo il polling di ~3s, la posizione resta aperta e blocca gli ingressi. Finché quel caso non si verifica, un reconcile periodico aggiungerebbe un job ricorrente che gira per sempre per una teoria — e l'utente ha indicato esplicitamente che il sistema deve funzionare **sempre** in tempo reale, non essere salvato da polling di fondo.

**Cosa fare se il problema si ripresenta:**
Il sintomo è un `ERROR` nei log con il testo `no verified OCO fill ... WILL block new entries`, oppure una posizione aperta su DB mentre il balance su OKX è a zero. Il percorso di recupero immediato resta il riavvio del container, che riconcilia dallo startup.

**Implementazione proposta (solo se necessaria):**
1. Job in `app/scheduler/` che chiama `_reconcile_position_with_exchange` per le posizioni `open` su DB ogni N minuti.
2. Il job deve essere **solo reattivo**: nessuna azione se il balance dice ancora posizione aperta (nessun costo, nessun rischio).
3. Idempotente: se non c'è fill verificato, non fare nulla e non chiudere mai sinteticamente.
4. Attenzione a non duplicare il percorso di startup: `main.py` e `pipeline.py` (sotto `if restore_mode:`) già riconciliano all'avvio. Il job periodico è un caso diverso — trade che invecchiano *a runtime*.

**Criteri di accettazione (se attivata):**
- [ ] Trigger: almeno 1 occorrenza reale del caso "fill non visibile dopo polling"
- [ ] Il job non chiude mai un trade senza fill verificato
- [ ] Il job non produce scritture su DB quando non serve
- [ ] Frequenza scelta in base a un tasso di fill anomali misurato, non arbitrario
- [ ] Il boot loop di `synthtrade` non ne risente

**File coinvolti (se attivata):**
- `synthtrade/backend/app/scheduler/` — nuovo job
- `synthtrade/backend/app/main.py` — registrazione scheduler

---

### TASK-1272 — Falso pausa di sessione: saldo basso per capitale impegnato ✅

**Stato:** ✅ **COMPLETATA e deployata** (commit `13ab09f`).

**Causa:** `spot_reconciliation_job()` in `app/scheduler/scalping_jobs.py` confrontava
`session["live_balance"]` con `trade_value` senza considerare la posizione aperta.
`live_balance` è `cashBal` di OKX (available + frozen), quindi **include il capitale
impegnato nella posizione**: con 21.9 EUR e trade da 20 EUR, ogni posizione aperta
riportava il saldo a 1.87 EUR e la sessione veniva pausa. Tre errori in uno:
confronto sbagliato, `pause_reason=SPOT_BALANCE_ZERO` falso, e messaggio all'utente
"i tuoi fondi sono in Simple Earn" quando quei fondi erano nella nostra posizione.

**Fix:**
- saldo basso **con posizione aperta** → log INFO con il notional impegnato, stato invariato
- saldo basso **senza posizione** → pausa legittima con `SPOT_BALANCE_INSUFFICIENT` e
  messaggio che dice esplicitamente che non c'è posizione aperta
- ripresa automatica invariata quando il saldo torna sufficiente

**Test:** 5 regressioni in `TestSpotReconciliation`. Verificato che catturino il bug:
**3 falliscono col codice precedente** e passano col fix. Suite `814 passed, 1 failed`
(`test_task_908` preesistente).

**Nota:** questo bug era l'unico motivo per cui il bot non stava bleeding. Corretto
il check, la sessione è ripartita e ha ripreso a operare. La pausa **non** è un
meccanismo di sicurezza utilizzabile per fermare il bleeding.

---

### TASK-1273 — Random-entry test: gli entry valgono più di un orario casuale? ✅

**Stato:** ✅ **COMPLETATA — esito negativo.** Report: `docs/RANDOM_ENTRY_TEST.md`.
Script: `scripts/random_entry_test.py`.

**Domanda:** il 90% degli trade entra con override mean-reversion e nessuno ha score
`>+6`. L'entry logic aggiunge qualcosa, o è rumore?

**Metodo:** simulatore che riusa le funzioni di pricing e la ladder break-even/trailing
di produzione (niente logica riscritta), validato contro i trade realmente realizzati
prima di confrontarli con gli entry casuali. Test eseguito due volte, una per bracket,
perché la scelta del bracket non possa influenzare la conclusione.

**Validazione:** simulato −0.2140% vs realizzato −0.2353%, p=0.595, 80% dei motivi
d'uscita concordanti. Il simulatore riproduce la realtà.

**Esito (8000 entry casuali, bracket globale usato dall'84% dei trade reali):**

| | media/trade | win rate |
|---|---|---|
| entry del bot | −0.2140% | 40.9% |
| entry casuali | −0.1729% | 46.3% |

**Differenza −0.0410% per trade · CI95 [−0.0944%, +0.0148%] · p=0.130 → indistinguibile,
con stima puntuale negativa.** Stesso esito sul bracket override (−0.0185%, p=0.242).

**Dati collaterali:**
- il TP viene centrato **3% delle volte** qualunque sia l'entry (bot 2.2%, casuali 3.0%);
  la ladder break-even/trailing intercetta quasi tutto prima
- i trade del bot vanno più spesso a stop pieno (59.1% vs 53.7%)
- win rate del bot **inferiore** al caso

**Conseguenza:** l'entry logic non ha edge misurabile. Cfr. anche TASK-1274.

**Correzione:** una versione precedente di questa task riportava che l'override SL/TP
per-strategia "non è applicato nell'84% dei trade". Era un errore di metodo: il campione
mescolava l'era pre-override (in cui l'override non esisteva e il TP globale è corretto
per definizione) con l'era post-override. **L'override funziona 13/13** nella sua era.
Nessun bug.

---

### TASK-1274 — Break-even e trailing: bloccano le perdite o il win rate? ✅

**Stato:** ✅ **COMPLETATA — l'ipotesi era invertita.** Report: `docs/RANDOM_ENTRY_TEST.md`
Parte 2. Controfattuali 2×2 in `scripts/random_entry_test.py`.

**Ipotesi da verificare:** che i due blocchi di sicurezza abbassino la percentuale di
vittoria per ridurre le perdite.

**Metodo:** l'override per-strategia è online dal 2026-09-25 15:16 UTC (TASK-1256), quindi
il confronto è stato rifatto **sui soli 182 trade dell'era a bracket fisso**, dove SL e TP
erano uguali per tutti. Simulatore validato (p=0.530, 144/180 motivi concordanti).
Quattro varianti: full, solo break-even, solo trailing, nessuno.

**Risposta: no, su entrambi i punti.**

1. **Non riducono il win rate — lo raddoppiano.** 21.1% → 41.7% (bot), 22.2% → 46.3%
   (casuali).
2. **Non riducono le perdite, mai.** La media dei perdenti è **−0.5000% in tutte e quattro
   le varianti**, perché i due blocchi spostano lo SL solo verso l'alto: un trade che non
   raggiunge +0.15% netto perde esattamente lo SL iniziale. **Il lato perdenti è
   strutturalmente congelato.**
3. **Quello che riducono è la vincita media**: +0.80% → +0.20%, e il TP centrato crolla
   dal 21.1% al 2.2%.
4. **Lo scambio è favorevole**: +0.0385%/trade rispetto a "nessuno" (braccio casuale
   n=7498, CI95 [+0.0240, +0.0540], p<0.001). Vanno tenuti.
5. **Il lock di break-even aggiunge zero**: solo trailing − full = +0.0001%, p=0.996.
   Il trailing da solo fa tutto il lavoro.

**Conseguenze operative:**
- Il vero collo di bottiglia è il **TP a +0.80% netto centrato il 2–3% delle volte** e il
  **lato perdenti fermo allo SL iniziale**. L'unica leva reale sulle perdite è avvicinare
  lo SL iniziale.
- L'override per-strategia lo fa (SL netto 0.50 → 0.30, perdita per perdente −0.40%), ma
  ha un **effetto collaterale**: per armare il break-even servono +0.35% lordo, quindi con
  SL a −0.30% quasi tutta la protezione non si attiva più. Le varianti si appiattiscono
  (scarto 0.007% contro 0.039% col bracket globale).
- Nei 13 trade reali post-override: **10 su 13 sono `stop_loss` puro**, P&L −0.1769%
  per trade (meglio del −0.2333% precedente, ma n troppo piccolo per concludere).

**Criteri di accettazione:**
- [x] Controfattuali 2×2 su break-even e trailing
- [x] Solo sull'era a bracket fisso, confrontabile
- [x] Simulatore validato prima del confronto
- [x] Confronto appaiato per la significatività
- [x] Config attuale (post-override) simulata a parte

**File coinvolti:**
- `scripts/random_entry_test.py`
- `docs/RANDOM_ENTRY_TEST.md`

---

### TASK-1252 — Ricalibrare Peso Signal Score nella Decisione ✅ (Fase 1 completata)

**Stato:** 🔶 Fase 1 completata il 2026-09-02. **Fase 2 (ricalibrazione soglia score) ora prioritaria e sbloccata dall'evidenza di TASK-1262:** su 68 snapshot reali il bias dei collector è stato corretto (score medio −3.741 → −1.891) ma **nessuno dei 68 snapshot ha superato la soglia +6.0**: il segnale bullish resta a 0.0%. Il constraint non è più il bias dei collector ma l'ampiezza del segnale e la soglia che lo filtra. Prima di ricalibrare va però chiarito *cosa* misurare, dato che la correlazione score→PnL misurata è ≈ 0.004.

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

**Stato:** ⏸️ **APERTA — in attesa di dati.** Bloccata sul campione: servono ≥30 trade dopo TASK-1250/1251 per misurare il win rate reale per combinazione regime/strategia. Ottimizzare ora significherebbe calibrare su dati corrotti dal vecchio override mean-reversion. Nota: l'attuale SL 0.30% / TP 0.55% (non più 0.50%/0.80% — verificato sulla posizione LIVE) richiede win rate > 35.29% per pareggio (SL/(SL+TP)), contro i 38.46% della combinazione precedente. La soglia di break-even si è quindi abbassata di 3.2 pp con TASK-1256: va comunque rimisurata sui dati reali, non considerata risolta.

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
- [x] `candle_processor.py` legge SL/TP per-strategia con fallback al globale (`_per_strategy_sl_tp_pct`)
- [ ] `break_even.py` legge trigger/step/buffer trailing per-strategia con fallback — **partial**: il cap del trailing segue il TP per-strategia via `_effective_tp_net_pct`; chiavi dedicate `STRATEGY_*_BE_TRIGGER/STEP/BUFFER` non implementate (nessun consumatore finché `TRAILING_ENABLED=False` di default)
- [x] `config_loader.py` espone helper per-strategia con fallback — implementedi: `strategy_sl_pct_override(name)` / `strategy_tp_pct_override(name)` (restituiscono `None` se assente; il fallback al globale è nel chiamante)
- [x] La position card mostra i valori effettivi usati (per-strategia se configurati) — `rest/position.py`, `router.py`, `trade_processor.py` derivano le % dai prezzi OCO reali
- [x] Test fallback: globale usato se non c'è override per strategia — `tests/unit/test_task_1256_per_strategy_sl_tp.py`
- [x] Test override: valore strategia usato se chiave DB presente — idem (13 test, tutti verdi)

**Stato:** ✅ **COMPLETATO e IN LIVE** (commit `87a8f03`; deploy VPS + verifica 2026-09-29). Prerequisito per TASK-1257/1258 sbloccato, ma la calibrazione resta gated su ≥30 trade post-deploy.

**Nota di deployment (2026-09-29):** i valori in LIVE per `rsi_bollinger` sono **SL 0.30 / TP 0.55 netti**. Al momento
della verifica la strategia in esecuzione era `ema_cross` per override macro TASK-1250, quindi usava i
globali 0.50/0.80: i valori dedicati della bollinger erano presenti ma non attivi. **Prima di giudicare
l'effetto dei valori per-strategia, controllare sempre la strategia attiva nei log.**

---

### TASK-1257 — Calibrazione Valori SL/TP Per-Strategia (Dipende da TASK-1256 + 30 trade)

**Priorità:** 🟡 Media — dopo TASK-1256 e almeno 30 trade post-TASK-1252

**Problema:**
Una volta che TASK-1256 abilita i valori per-strategia, è necessario determinare i valori ottimali. I valori attuali (SL=0.5%, TP=0.8%) sono un compromesso globale non ottimale per nessuna strategia.

**Analisi base con fee reali OKX (taker=0.10% — verificato da DB):**

Round-trip fee drag = `1 - (1-0.001)² ≈ 0.20%`

| Strategia | SL netto proposto | TP netto proposto | WR breakeven | Razionale |
|-----------|------------------|------------------|--------------|-----------|
| `rsi_bollinger` | **0.30%** | **0.55%** | 35.3% | Ranging: oscillazioni tipiche BTC-EUR 0.2–0.5%; TP più raggiungibile. SL 0.30 in LIVE dal 2026-09-25 |
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
- [ ] Almeno 30 trade post-deploy 1.7.0 (dal 2026-09-25, verifica VPS 2026-09-29)
- [ ] Analisi MFE/MAE per `rsi_bollinger` (strategia dominante attuale)
- [ ] Valori SL/TP scelti con WR breakeven ≤ WR osservato (expectancy ≥ 0)
- [ ] Simulazione: nuovi vs vecchi SL/TP sulle stesse entry → confronto PnL
- [ ] Monitoring 2 settimane post-cambio per conferma

**Stato:** ⏸️ APERTA — in raccolta dati.  L'infrastruttura è in LIVE e le percentuali restituite dalla position
card ora corrispondono ai valori effettivamente usati, quindi la verifica non richiede più ricostruzioni manuali.
Prima di estrarre i dati, **filtrare per `strategy_type`**: mescolare `ema_cross` e `rsi_bollinger` produrrebbe
una distribuzione MFE/MAE meaningless, perché usano SL/TP diversi.

**Dimensionamento da tenere presente:** SL 0.30% netto ≈ **−0.10% di movimento prezzo**, perché le fee
(0.20% round-trip) consumano circa due terzi dello stop. Su un trade da 20 € lo stop scatta a ~2 cent.

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
- [ ] Simmetria BE/trailing verificata con i valori in LIVE: BE trigger 0.15% = **27%** del TP 0.55 (target ~25%, quindi già in linea), ma `LOCK 0.05%` = 9% del TP contro un 7% atteso
- [ ] Simulazione: quanti trade si sarebbero chiusi anticipatamente (trailing hit < TP) con vecchi vs nuovi parametri
- [ ] `BREAK_EVEN_TRIGGER` ≈ 25% TP per ogni strategia (verificato)
- [ ] Il supervisor AI può aggiornare singoli parametri trailing via DB senza deploy

**Stato:** ⏸️ APERTA — la lacuna concreta oggi in LIVE. 

Il punto scoperto il 2026-09-29: gli step del trailing **non sono proporzionali al TP**, sono valori
fissi in `break_even.py` (`STEP 0.15`, `BUFFER 0.10`, `SAFETY 0.10`), identici per tutte le strategie e
overridabili solo via DB. A essere dinamico è solo **quanti step** stanno sotto il tetto `TP - SAFETY`:

| Strategia | TP netto | Tetto (TP − SAFETY) | Step effettivi |
|---|---|---|---|
| `rsi_bollinger` | 0.55 | 0.45 | **1** (0.30) |
| `ema_cross` | 0.80 | 0.70 | **3** (0.30 / 0.45 / 0.60) |

Conseguenza: con TP 0.55 la scala fissa viene troncata a un solo livello, quindi **aumentare il TP da
0.45 a 0.55 non produce più step**. È la ragione per cui la tabella proporzionale qui sopra è ancora
necessaria, e va applicata agli step e non solo al cap (che TASK-1256 ha già reso dinamico).

**Da non toccare:** il break-even è corretto e fee-aware (trigger +0.15% netto, stop sicurezza +0.05%
netto via `_exit_price_ratio`). L'obiettivo è "non perdere", non guadagnare: su un trade da 20 € uno
stop a +0,05% vale 1 cent ed è corretto che ci sia. Le chiavi `STRATEGY_*_BE_TRIGGER/STEP/BUFFER` hanno
un ulteriore ostruzione: nessun consumatore finché `TRAILING_ENABLED=False` di default.

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
