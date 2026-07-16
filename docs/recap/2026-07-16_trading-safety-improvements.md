# Recap Sessione 2026-07-16 — Trading Safety Improvements

> **Obiettivo:** mitigare le cause principali delle perdite nel trading live (100% BUY, 84% stop loss) attraverso protezioni specifiche, analisi dati e refinamenti del regime detection.

---

## Contesto

La sessione è partita dall'analisi dei dati DB: 184 trade chiusi, 19 con `trend_direction` non null. Il pattern emergente era chiaro:
- **100% dei trade era BUY** — nessun SELL nel dataset
- **84% stop loss** — il sistema entrava long in condizioni sfavorevoli
- **Regime sempre "unknown"** — la regime detection non era attiva o non classificava
- **Correlazione trend_value vs PnL = 0.004** — nessuna predittività

Tre problemi fondamentali sono stati identificati e risolti nella sessione.

---

## TASK-898 — Analisi Trend da Dati Persistiti

**Problema:** Non si aveva evidenza empirica su cosa stesse andando storto nel trading live.

**Soluzione:** Query SQL su `scalping_trades` JOIN `session_signal_log` per estrarre 19 trade con trend data. Creazione di `docs/trend_analysis_report.md` con:
- PnL per `trend_direction` (diverging/converging/stable)
- Distribuzione exit reason (84% stop_loss)
- Correlazione Pearson r=0.004 (nessuna)
- Dati grezzi dei 19 trade

**Outcome:** Confermato che il problema non è il trend_value in sé, ma il fatto che il sistema entrava long in modo indiscriminato. Le protezioni TASK-906 e TASK-908 mitighano questo problema.

**File:** `docs/trend_analysis_report.md`

---

## TASK-908 — Resume Guard: Bloccare Resume in Regime Bearish

**Problema:** Dopo uno stop loss, il sistema riprendeva a tradare (resume) anche in regime fortemente bearish (`trending_down` con confidence alta). Senza posizione aperta e senza la possibilità di fare short, il resume ricomprava in un mercato in caduta → un altro stop loss.

**Soluzione a 3 livelli:**

1. **Guard primaria** (`supervisor_scheduler.py:339-358`):
   - Legge `regime`, `regime_confidence`, `has_position` dal context
   - Se `regime == "trending_down"` AND `confidence >= 0.7` AND `has_position == false` → il `resume_trading` viene **bloccato**
   - Il supervisor riceve messaggio: "⚠️ Resume bloccato: regime bearish (trending_down, confidenza X%) senza posizione aperta."

2. **Defense-in-depth** (`parameter_updater.py:_resume()`):
   - Il metodo `_resume()` è reso **no-op** se il regime è bearish
   - Anche se la guard primaria venisse bypassata, il resume non applicherebbe parametri

3. **Contesto arricchito** (`supervisor_context.py`):
   - Aggiunto `short_enabled: False` al contesto
   - Il supervisor sa che non può fare short e quindi non propone resume in bearish

**File:**
- `synthtrade/backend/app/scalping/supervisor/supervisor_scheduler.py`
- `synthtrade/backend/app/scalping/supervisor/parameter_updater.py`
- `synthtrade/backend/app/ai/supervisor_context.py`
- `synthtrade/backend/tests/unit/test_task_908.py` (6 test)

---

## TASK-906 — Falling Knife Protection

**Problema:** `signal_aggregator.py` approvava mean-reversion BUY incondizionatamente quando `bias == "bearish"`. Durante un crash verticale, RSI+Bollinger segnalava BUY (oversold) ma il prezzo continuava a cadere → stop loss.

La logica era:
```
if bias == "bearish" and strategy in mean_reversion_strategies:
    # il mean-reversion BUY viene APPROVATO perché "bearish + oversold = opportunità"
```
Questo era corretto in mercato ranging, ma catastrofico in caduta libera.

**Soluzione:** Aggiunta guard `FALLING_KNIFE_TREND_THRESHOLD = -20.0` in `signal_aggregator.py`.

La guard blocca il mean-reversion BUY se:
- `trend_direction == "diverging"` (score si allontana da zero = crash)
- `trend_5m < -20.0` (drop di 20+ punti dello score in 5 minuti)

**Logica dettagliata:**
- `trend_5m`: variazione dello score negli ultimi 5 minuti (es: -35.0 = score dropato 35 punti)
- `trend_direction`: `"diverging"` = score si allontana da zero (crash), `"converging"` = score si avvicina a zero (recovery)
- Guard attiva **SOLO** per mean-reversion BUY (`rsi_bollinger`, `stoch_rsi_bb_squeeze`)
- **Non influenza:** CLOSE, SELL, BUY normali, mean-reversion SELL

**Impatto stimato:** Avrebbe bloccato almeno 7 dei 9 trade "diverging" con trend_value negativo dal dataset TASK-898.

**File:**
- `synthtrade/backend/app/scalping/engine/signal_aggregator.py`
- `synthtrade/backend/tests/unit/test_task_906.py` (12 test)

---

## TASK-903 — RegimeDetector: Isteresi K Candele

**Problema:** `RegimeDetector` era completamente **stateless** — nessun `__init__`, zero attributi. Ogni chiamata a `detect()` produceva un regime da zero basato sulle ultime 20 candele. Le soglie (volatility_ratio > 0.01, price_change > 0.003) causavano flickering quando il prezzo oscillava vicino ai boundary.

L'`ExecutionLoop` (riga 162-175) sovrascrive `_current_regime` ad ogni tick senza smoothing. Il regime poteva passare da `ranging` a `trending_up` a `volatile` in 3 tick consecutivi, causando:
- Cambio continuo di strategia (ranging → ema_cross → stoch_rsi_bb)
- Segnali contraddittori al supervisor
- Instabilità decisionale

**Soluzione:** Aggiunta isteresi K=3 in `regime_detector.py`.

**Come funziona:**
1. `_detect_candidate()` estrae la logica raw (invariata) → restituisce il candidato
2. `detect()` applica l'isteresi:
   - **Prima chiamata** → commit immediato del candidato
   - **Candidato uguale al committed** → tutto stabile, reset pending
   - **Nuovo candidato** → inizia conteggio (`_pending_count = 1`)
   - **Stesso candidato per K candele** → commit del nuovo regime
   - **Candidato cambia prima di K** → reset counter
3. Finché il regime non viene committato, `detect()` restituisce il regime **committed** precedente

**API pubblica:**
- `pending_regime`: candidato attualmente in fase di conferma (per debug)
- `pending_count`: numero di candele consecutive con lo stesso candidato
- `committed_regime`: ultimo regime confermato

**Retrocompatibilità:** `detect_with_core()` resta stateless come prima.

**File:**
- `synthtrade/backend/app/scalping/engine/regime_detector.py`
- `synthtrade/backend/tests/unit/test_task_903.py` (15 test)

---

## Health Check Fix (non task)

**Problema:** Il health check in `scalping_jobs.py:224` considerava `status == "paused"` come errore. Ma `paused` è uno stato intenzionale (pausa manuale), non un errore.

**Fix:** `status == "running"` → `status in ("running", "paused")`

**File:** `synthtrade/backend/app/scheduler/scalping_jobs.py`

---

## Riepilogo Test

| Task | Test | File |
|------|------|------|
| TASK-908 | 6 | `test_task_908.py` |
| TASK-906 | 12 | `test_task_906.py` |
| TASK-903 | 15 | `test_task_903.py` |
| **Totale** | **33** | |

---

## Commits

| Commit | Task | Messaggio |
|--------|------|-----------|
| `95179b9` | Health check | `fix: health check accepts paused status` |
| `4426959` | TASK-1171 | `fix: intel snapshot skips non-session symbols` |
| `d8ac27f` | TASK-1116.G | `feat: instrument discovery environment-aware` |
| `c8b41d5` | TASK-908 | `feat: TASK-908 resume guard — block resume in bearish regime without position` |
| `cc17fce` | TASK-906 | `feat: TASK-906 falling knife protection — block mean-reversion BUY during crash` |
| `782bd1a` | TASK-898 | `docs: TASK-898 trend analysis report — 19 trades analyzed` |
| `75b61ee` | TASK-903 | `feat: TASK-903 regime hysteresis K=3 — prevent flickering` |

---

## Task Rimasti Aperti

| Task | Priorità | Note |
|------|----------|------|
| TASK-1166 | 🟡 Media | Refactor router.py (~4200 righe → moduli <500 righe) |

---

## Prossimi Passi

1. **TASK-1166** — Refactor router.py (2-3 giorni)
2. **Raccogliere dati** — servono ≥100 trade con trend data per analisi statistica significativa
3. **Monitorare in live** — verificare che TASK-906 e TASK-908 riducano le perdite dopo 50+ trade
