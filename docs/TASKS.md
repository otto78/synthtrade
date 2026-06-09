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