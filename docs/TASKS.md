# TASKS.md — SynthTrade Task Tracking

> **Aggiornato:** 2026-08-03. Task completati in `docs/ARCHIVE_TASKS.md`.

---

## 🔴 FASE 1 — Bug Critici e Pulizia (EV Fix)

> **Contesto**: analisi di 5 sessioni live (24/07–03/08/2026) ha dimostrato EV = -0.236%/trade.
> Causa: 2 bug di codice critici + 2 problemi strutturali che rendono il sistema incapace
> di operare profittevolmente. Queste task DEVONO essere completate prima di qualsiasi
> altra espansione (multi-session, nuove strategie, ecc.).
> Riferimento: `analisi_sessioni.md` nell'artifact directory di questa sessione.

---

### TASK-1238 — Fix VWAP Reversion: logica BUY/SELL invertita ✅ Completato

> **Priorità**: CRITICA — la strategia vwap_reversion genera segnali opposti a quelli attesi
> **File**: `synthtrade/backend/app/scalping/strategies/vwap_reversion.py`
>
> **Problema**: La strategia emette BUY quando `prezzo > VWAP + 0.2%` (breakout/momentum)
> invece di emettere BUY quando `prezzo < VWAP - 0.2%` (reversion al dip, comportamento
> corretto per una strategia mean-reversion). La logica è esattamente invertita.
> In un mercato in trend rialzista, la logica attuale entra già dopo un movimento fatto;
> in un mercato laterale/ribassista entra contro il movimento, amplificando le perdite.
>
> **Fix**: Invertire le condizioni BUY/SELL nella strategia.
> **Nota**: i segnali SELL vengono già bloccati dall'aggregator, ma vanno rimossi dal codice
> per pulizia (vedi TASK-1240).
> **Acceptance**: unit test che verifica che BUY venga emesso con price < VWAP e non viceversa.

---

### TASK-1239 — Fix btc_change_24h_pct: campo OKX "chg" inesistente ✅ Completato

> **Priorità**: CRITICA — il supervisor e il regime detector ricevono sempre 0% di variazione
> 24h, rendendo il contesto macro cieco per tutte le decisioni di sessione.
> **File**: `synthtrade/backend/app/execution/okx_exchange.py` (~L.430-480)
>
> **Problema**: L'API OKX `/api/v5/market/ticker` non restituisce un campo `"chg"`.
> Il codice fa `ticker.get("chg") or 0.0` che produce sempre 0.
> I campi reali che OKX restituisce sono `"last"` e `"open24h"`.
>
> **Fix**:
> ```python
> last = float(ticker.get("last") or 0)
> open24h = float(ticker.get("open24h") or 0)
> change_24h_pct = ((last - open24h) / open24h * 100) if open24h > 0 else 0.0
> ```
> **Acceptance**: valore non-zero e coerente con il mercato al momento dell'esecuzione.

---

### TASK-1240 — Rimuovere generazione segnali SELL dalle strategie ✅ Completato

> **Priorità**: ALTA — i segnali SELL vengono già bloccati nell'aggregator, ma le strategie
> li generano ancora internamente causando rumore computazionale e potenziali distorsioni
> nelle metriche del supervisor (che vede segnali che poi non esegue).
> **File**:
>   - `synthtrade/backend/app/scalping/strategies/momentum_base.py`
>   - `synthtrade/backend/app/scalping/strategies/vwap_reversion.py`
>
> **Problema**: In Europa non è consentito lo short selling in spot. I segnali SELL/SHORT
> sono permanentemente disabilitati nell'aggregator (`signal_aggregator.py` log:
> "SELL signals are permanently disabled"). Tuttavia le strategie continuano a generarli,
> sprecando cicli e inquinando le metriche del supervisor AI.
>
> **Fix**: In entrambe le strategie, sostituire i blocchi `if price < threshold: signal = SELL`
> con un segnale `WAIT` o semplicemente `return None`. Mantenere solo la logica BUY.
> **Acceptance**: le strategie non emettono mai `TechnicalSignal(type="SELL")`.

---

### TASK-1241 — Persistere signal_score e intelligence fields nel DB ✅ Completato

> **Priorità**: ALTA — senza questi dati non è possibile analizzare la correlazione tra
> qualità del segnale e outcome del trade, né implementare filtri basati su score minimo.
> **File**: `synthtrade/backend/app/scalping/db_ops.py` (funzione `_save_open_position_to_db`)
>
> **Problema**: I seguenti campi esistono nella tabella `scalping_trades` ma sono sempre NULL
> perché non vengono passati al momento del salvataggio del trade:
>   - `signal_score` (punteggio composito dell'intelligence layer, range -100/+100)
>   - `funding_rate_at_entry` (funding rate OKX al momento dell'ingresso)
>   - `fear_greed_at_entry` (indice Fear&Greed al momento dell'ingresso)
>   - `cvd_trend_at_entry` (trend CVD: "bullish"/"bearish"/"neutral")
>   - `regime_classified` (regime classificato dal regime_detector: trending_up/down/ranging)
>
> **Fix**: Aggiungere questi campi al dict `supervisor_context` che viene passato a
> `_save_open_position_to_db`, e includerli nella `insert_data` nel DB.
> Verificare che i valori siano disponibili nel router al momento dell'apertura trade.
> **Acceptance**: dopo un trade live, questi campi sono non-NULL nel DB.

---

## 🟠 FASE 2 — Trend Filter (dopo completamento Fase 1)

> **Contesto**: Fase 2 può iniziare solo dopo che la Fase 1 è validata con ≥10 trade live.
> Il filtro trend è la modifica con il maggiore impatto atteso sul win rate (+15-20%).

---

### TASK-1242 — Trend Filter: bloccare BUY quando BTC sotto EMA20 4h 🟡 Todo

> **Priorità**: ALTA (Fase 2)
> **File**: `synthtrade/backend/app/scalping/engine/signal_aggregator.py`
>          oppure `engine/regime_detector.py`
>
> **Problema**: Il sistema entra long indipendentemente dalla direzione del trend di medio
> termine. Nel periodo 27/07-03/08, BTC è sceso da 57.600€ a 53.000€ e il sistema ha
> continuato ad aprire long durante tutta la discesa, totalizzando 19 perdite su 24 trade.
>
> **Fix**: Prima di autorizzare ogni segnale BUY, verificare:
>   1. BTC price > EMA20 calcolata sulle ultime 20 candele 4h
>   2. btc_change_1h_pct > -0.5% (non comprare in forte discesa oraria)
> Se una delle condizioni non è soddisfatta → segnale WAIT (non BUY).
>
> **Dati necessari**: candlestick 4h già disponibili (verificare nel signal engine).
> **Acceptance**: nessun BUY viene autorizzato quando BTC è sotto EMA20 4h.

---

## 🟡 FASE 3 — Revisione TP/SL (dopo validazione Fase 2)

> **Contesto**: Da avviare dopo almeno 20 trade con Fase 1+2 attive e EV stimato positivo.

---

### TASK-1243 — Revisione struttura TP/SL: ridurre impatto fee su SL stretto 🟡 Todo

> **Priorità**: MEDIA (Fase 3)
> **File**: `scalping_risk_config` (tabella DB) + eventuale codice di default
>
> **Problema**: Con SL=0.30% e fee round-trip 0.18%, le commissioni erodono il 60% dello SL.
> Il R:R teorico 3.33:1 collassa a 1.57:1 reale, rendendo il break-even matematicamente
> al 38.8% win rate (attualmente siamo al 20.8%).
>
> **Opzioni da valutare (in ordine di preferenza)**:
>   A. Allargare SL a 0.50%, TP a 1.50% — stessa ratio teorica, fee meno impattanti (36%)
>   B. Trailing SL: sposta SL a break-even dopo +0.30% gain
>   C. Abbassare TP a 0.60% per aumentare frequenza di vincita (da validare con backtest)
>
> **Acceptance**: almeno 20 trade live con nuova configurazione e EV stimato > 0.

---



### BUG-2026-08-03 — Fix reconcile exit_time timestamp OKX + frontend date display ✅ Completato

> **Stato:** Completato il 03/08/2026.
> - **Backend `okx_exchange.py` L.745**: OKX `/api/v5/trade/fills` usa `ts` (non `fillTime`) come timestamp. L'adapter mappava `fill.get("fillTime")` (sempre `None`), causando il fallback di `exit_time` a `datetime.now()` (reconcile time) invece della data/ora reale del fill OKX post-riavvio weekend. Risolto con `fill.get("fillTime") or fill.get("ts")`.
> - **Frontend `logs.page.ts` L.184**: La tabella trade nella vista sessioni mostrava solo `HH:mm` invece di `dd/MM/yy HH:mm` per `entry_time`. Rinominata anche l'intestazione da `Ora` a `Data/Ora` per coerenza con il tab Storico Trade.

---

### TASK-1166 — Consolidamento a 3 Strategie Runtime ✅ Completato

> **Stato:** Tutte le fasi completate il 30/07/2026.
> - **Fase 1**: 6 chiavi `REGIME_STRATEGY_*` / `REGIME_ALLOWED_*` inserite in `scalping_runtime_config` (DB override)
> - **Fase 2**: Default hardcoded aggiornati in `config_loader.py`, `strategy_selector.py`, `supervisor_scheduler.py`
> - **Fase 3**: Dropdown frontend ridotto a 3 opzioni (EMA Cross, RSI+Bollinger, VWAP Reversion), default `vwap_reversion`
> - **Fase 4**: `docs/plans/okx-sl-tp-recalibration-task.md` marcato come superato (fee reale 0,20% round-trip)
> - **Prossimo**: Fase 4.1/4.2 (osservazione post-cambio) — dopo 15-20 trade con nuovo mapping

---

### Punto 4 (pesi signal score) — 🟡 Fermo

> **Stato:** Confermato nessuna azione da intraprendere ora — coerente con TASK-1159 bloccato. Resta in attesa di revisione pesi futura.
