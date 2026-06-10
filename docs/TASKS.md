# TASKS.md — SynthTrade Task Tracking

## Active Tasks

### TASK-814 — Live Mode Bug Fixes (2026-06-05 → 2026-06-09) ✅

**Status:** Complete ✅

Fix issues identified from live session logs:
- [x] **Issue 1-8**: All fixed — WS handshake, RSS/CoinGecko/Whale pollers, OCO balance settlement, logging visibility, session restore pipeline, minNotional, OCO post-fee balance
- [x] Update docs and commit

---

### TASK-815 — SignalScoreEngine: soglia dinamica e pesi calibrati (2026-06-09) ✅

**Status:** Complete ✅
**Commit:** `123976e`
**File:** `signal_score_engine.py`

**Modifiche:**
- Pesi ridistribuiti (funding_rate 0.20, cvd 0.20, OI 0.15, L/S 0.15, F&G 0.15, whale 0.10, sentiment 0.05, onchain 0.0)
- Normalizzazione USDC→USDT per collector futures
- Soglia scalata: `effective_threshold = threshold * coverage`

---

### TASK-816 — RSI Bollinger: soglie calibrate per mercato ranging (2026-06-09) ✅

**Status:** Complete ✅
**Commit:** `123976e`
**File:** `rsi_bollinger.py`

**Modifiche:**
- RSI_OVERSOLD: 30 → 38
- RSI_OVERBOUGHT: 70 → 62
- BB tolleranza: 1.01 → 1.015
- Confidence: 0.7 → 0.6

---

### TASK-817 — SignalAggregator: bypass mean-reversion per ranging (2026-06-09) ✅

**Status:** Complete ✅
**Commit:** `123976e`
**File:** `signal_aggregator.py`

**Modifiche:**
- `MEAN_REVERSION_STRATEGIES = ("rsi_bollinger", "stoch_rsi_bb_squeeze")`
- Permette SELL da mean-reversion in ranging quando bias intelligence è bullish
- Permette BUY da mean-reversion in ranging quando bias intelligence è bearish

---

### TASK-818 — StrategySelector: mapping regimi corretto (2026-06-09) ✅

**Status:** Complete ✅
**Commit:** `123976e`
**File:** `strategy_selector.py`

**Modifiche:**
- `ranging` → `rsi_bollinger`
- `volatile` → `stoch_rsi_bb_squeeze`
- `trending_up/down` → `ema_cross`
- `unknown` → `momentum_base`

---

### TASK-819 — Supervisor: cooldown e regime validation (2026-06-09) ✅

**Status:** Complete ✅
**Commit:** `123976e`
**File:** `supervisor_scheduler.py`, `supervisor_client.py`

**Modifiche:**
- Cooldown cambio strategia: 20 minuti
- Cooldown aggiornamento parametri: 10 minuti
- Regime validation: blocca strategie non compatibili col regime corrente
- Se strategia proposta non ammessa, resetta cooldown per prossimo tick valido
- `REGIME_ALLOWED_STRATEGIES` mapping completo nel prompt AI

---

### TASK-820 — EMA Cross: rimuovere slope filter + registrazione nuove strategie (2026-06-09) ✅

**Status:** Complete ✅
**Commit:** `123976e`
**File:** `ema_cross.py`, `stoch_rsi_bb_squeeze.py`, `registry.py`

**Modifiche:**
- `ema_cross.py`: Rimosso MIN_SLOPE e logica pendenza — segnale BUY se EMA9 > EMA21, SELL se EMA9 < EMA21
- `stoch_rsi_bb_squeeze.py`: Creata strategia StochRSI + BB Squeeze per regime volatile
- `registry.py`: Registrata `stoch_rsi_bb_squeeze`

---

### TASK-821 — Frontend: default BNBUSDC e rimozione initial load (2026-06-09) ✅

**Status:** Complete ✅

**Modifiche:**
- Default symbol: BTCUSDT → BNBUSDC in tutti i componenti scalping
- Default strategia: scalping_v2 → momentum_base
- Dropdown strategie: aggiunto `stoch_rsi_bb_squeeze`, rimosso `scalping_v2`, nomi normalizzati
  (`RSI + Bollinger` invece di `RSI con Bollinger`, `StochRSI BB Squeeze` invece di `Stoch RSI con BB Squeeze`)
- Rimosso initial load da TradeLog e PerformancePanel (attendono sessione attiva)
- `strategy-panel.component.ts`: fallback `STRATEGY_DEFAULTS['momentum_base']` invece di `scalping_v2`

**File modificati:**
- `session-controls.component.ts`
- `live-chart.component.ts`
- `market-intel-panel.component.ts`
- `session-api.service.ts`
- `trade-log.component.ts`
- `performance-panel.component.ts`
- `strategy-panel.component.ts`

---

### TASK-823 — Fix persistenza sessione scalping: saldo, trade history, posizione aperta (2026-06-10) ✅

**Status:** Complete ✅

**Bug 1 — Saldo 10,000 falso dopo restart:**
- `_restore_scalping_session()` ora inizializza `BinanceExchangeAdapter` e fa `fetch_balance()` da Binance per sessioni live
- Usa `_normalize_binance_total_balance()` e `_select_preferred_quote_balance()` per trovare il saldo corretto

**Bug 2 — Lista trade vuota dopo restart:**
- Step 5: carica fino a 200 trade dalla tabella `scalping_trades` via `session_id`
- Popola `_execution_state["trade_history"]` in memoria

**Bug 3 — Performance vuota dopo restart:**
- Stessa causa del Bug 2 — dipende da `trade_history` popolato

**Bug 4 — Trade persi al restart (posizione aperta non persistita):**
- Nuova funzione `_save_open_position_to_db()`: salva posizione aperta su DB con `status='open'` subito dopo `pm.open_position()`
- Nuova funzione `_update_closed_position_in_db()`: UPDATE della stessa riga alla chiusura (anziché INSERT)
- La funzione `_close_position_and_record()` ora usa `_update_closed_position_in_db()` invece di INSERTare ex-novo
- Step 7: carica eventuale posizione con `status='open'` da DB e la ripristina in `PositionManager`
- `_restore_scalping_session()` resa async per supportare le chiamate CCXT

**Migration 010:** Aggiunta colonna `trade_value FLOAT` a `scalping_sessions`

**File modificati:**
- `synthtrade/backend/app/main.py` — `_restore_scalping_session()` async, Steps 5-8
- `synthtrade/backend/app/scalping/router.py` — funzioni helper persistenza

---

### TASK-822 — Config panel: rimuovere sub-tab "Strategy" e aggiungere titolo "Session" con ID (2026-06-09)

**Priorità:** Bassa

**Problema:** Nel pannello di configurazione principale è presente una sub-scheda "Strategy" che mostra la strategia selezionata inizialmente ma non si aggiorna quando la strategia corrente cambia (es. dopo una decisione del supervisor AI). Esiste già una sezione più completa e aggiornata nel pannello Strategy dedicato.

**Soluzione:**
1. Rimuovere la sub-scheda "Strategy" dal pannello di configurazione principale
2. Aggiungere un titolo principale "Session" al pannello di configurazione
3. Mostrare l'ID della sessione in testo più piccolo sotto il titolo
4. Mantenere visibili le impostazioni di configurazione del trade già esistenti nel sistema

**Modifiche:**
- Rimuovere sub-tab "Strategy" dal componente del pannello configurazione sessione
- Aggiungere header con titolo "Session" + session ID
- Lasciare al loro posto le impostazioni esistenti (symbol, strategy selector, trade value)

**Rischio:** Basso — rimozione UI senza impatto su logica backend.
