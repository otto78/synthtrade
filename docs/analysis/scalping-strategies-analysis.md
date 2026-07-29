# Analisi Completa Strategie Scalping — SynthTrade

> **Data:** 2026-07-29
> **Scopo:** Documento di riferimento per analisi, modifica, aggiunta/rimozione strategie e trigger.
> **Attenzione:** Le strategie DB (`strategies` table) sono **template di generazione** per backtest — **non** le strategie runtime usate dall airing scalping. Le strategie runtime sono le 5 classi in `app/scalping/strategies/`.

---

## Indice

1. [Architettura: Due sistemi separati](#1-architettura-due-sistemi-separati)
2. [Strategie Runtime Scalping (5 classi)](#2-strategie-runtime-scalping-5-classi)
3. [Regime Detection & Strategy Selection](#3-regime-detection--strategy-selection)
4. [Intelligence Layer — Signal Score Engine](#4-intelligence-layer--signal-score-engine)
5. [Signal Aggregation & Execution Gating](#5-signal-aggregation--execution-gating)
6. [Supervisor AI](#6-supervisor-ai)
7. [Template Strategie Pipeline (8 template)](#7-template-strategie-pipeline-8-template)
8. [Configurazione Corrente — DB e .env](#8-configurazione-corrente--db-e-env)
9. [Mappa dei Punti di Modifica](#9-mappa-dei-punti-di-modifica)

---

## 1. Architettura: Due sistemi separati

Esistono **due sistemi di strategia completamente distinti**:

### A. Scalping Runtime Strategies — USO ATTIVO (real-time)

- **File:** `synthtrade/backend/app/scalping/strategies/`
- **Ruolo:** Decidono il timing di entrata su ogni candela 1m
- **5 classi concrete**, registrate in `registry.py`
- **Eseguite** da `ExecutionLoop.process_candle()` ogni minuto
- **Mapping regime → strategia** via `StrategySelector` (sezione 3)
- **Possono essere sostituite in tempo reale** dal Supervisor AI

### B. Pipeline Template Strategies — GENERAZIONE OFF-LINE

- **File:** `synthtrade/backend/app/core/strategy_generator.py`
- **Ruolo:** Generare strategie via backtest storico per investimenti manuali
- **8 template** con parametri predefiniti
- **Non usate** dall airing scalping real-time
- **Salvate** nella tabella `strategies` del DB

> ⚠️ **IMPORTANTE:** Modificare i template in `strategy_generator.py` o la tabella `strategies` **NON** ha effetto sul trading live. Le strategie live sono le 5 classi in `scalping/strategies/`.

---

## 2. Strategie Runtime Scalping (5 classi)

### 2.1 EMACrossStrategy — `ema_cross.py`

| Proprietà | Valore |
|-----------|--------|
| **File** | `synthtrade/backend/app/scalping/strategies/ema_cross.py` |
| **Regime** | `trending_up`, `trending_down` |
| **Logica** | EMA 9 cross EMA 21 + pendenza minima EMA21 > 0.03% (`MIN_SLOPE = 0.0003`) |
| **Confidenza** | 0.75 (BUY); 0.75 (SELL) |
| ** Parametri modificabili** | `MIN_SLOPE` (line 13), periodi EMA (line 17-18 hardcoded: 9, 21) |
| **Limiti** | Solo LONG operation (SELL → NONE per engine long-only) |

**Trigger attivazione (BUY):**
```
ema9 > ema21 AND ema21_slope > 0.0003 → BUY con confidence 0.75
```

**Trigger attivazione (SELL):**
```
ema9 < ema21 AND ema21_slope < -0.0003 → SELL con confidence 0.75
```
(bloccato da engine long-only)

### 2.2 RSIBollingerStrategy — `rsi_bollinger.py`

| Proprietà | Valore |
|-----------|--------|
| **File** | `synthtrade/backend/app/scalping/strategies/rsi_bollinger.py` |
| **Regime** | `ranging` |
| **Logica** | Mean reversion: RSI + Bollinger Bands, soglie dinamiche su ATR% |
| **Confidenza** | 0.35–0.70 (dinamica per volatilità) |
| **Parametri modificabili** | Soglie ATR% (line 83-103), periodi RSI/BB (line 110-111 hardcoded: 14, 20) |

**Soglie dinamiche per ATR%:**

| ATR% | RSI Oversold | RSI Overbought | BB Tolerance | Confidence |
|------|-------------|---------------|-------------|-----------|
| < 0.4% | 48 | 52 | 1.008 (0.8%) | 0.35 |
| 0.4–0.6% | 43 | 57 | 1.012 (1.2%) | 0.50 |
| 0.6–1.0% | 38 | 62 | 1.015 (1.5%) | 0.60 |
| > 1.0% | 33 | 67 | 1.020 (2.0%) | 0.70 |

**Trigger attivazione (BUY mean-reversion):**
```
rsi < oversold_threshold AND price < bb_lower * bb_tolerance → BUY
```
Questa strategia è eleggibile per **mean-reversion override** (sez. 5 punto 7) — bypassa il bias conflict se lo score intelligence è forte e il trend non è caduta-coltello.

### 2.3 StochRSIBBSqueezeStrategy — `stoch_rsi_bb_squeeze.py`

| Proprietà | Valore |
|-----------|--------|
| **File** | `synthtrade/backend/app/scalping/strategies/stoch_rsi_bb_squeeze.py` |
| **Regime** | `volatile` |
| **Logica** | BB Squeeze + StochRSI proxy: entra quando la volatilità si comprime e poi espande |
| **Confidenza** | 0.55 |
| **Parametri modificabili** | `bb_width < 0.015` (1.5%) soglia squeeze (line 48), StochRSI soglie 0.2/0.8 (line 49) |

**Trigger attivazione (BUY):**
```
bb_width < 0.015 AND (close - bb_lower) / (bb_upper - bb_lower) < 0.2 → BUY
```
(StochRSI è proxy via posizione prezzo nelle bande)

### 2.4 MomentumBaseStrategy — `momentum_base.py`

| Proprietà | Valore |
|-----------|--------|
| **File** | `synthtrade/backend/app/scalping/strategies/momentum_base.py` |
| **Regime** | `unknown` (fallback) |
| **Logica** | Price > EMA9 con margine 0.01% — high-frequency fallback |
| **Confidenza** | 0.70 |
| **Parametri modificabili** | `margin = close * 0.0001` (0.01%) (line 53), periodo EMA 9 (line 55) |

**Trigger attivazione (BUY):**
```
close > ema9 + margin → BUY
close < ema9 - margin → SELL (bloccato)
```

### 2.5 VWAPReversionStrategy — `vwap_reversion.py`

| Proprietà | Valore |
|-----------|--------|
| **File** | `synthtrade/backend/app/scalping/strategies/vwap_reversion.py` |
| **Regime** | Non collegato (non nel mapping default, ma registrato) |
| **Logica** | Prezzo sotto VWAP > 0.2% → BUY; sopra VWAP > 0.2% → SELL |
| **Confidenza** | 0.70 |
| **Parametri modificabili** | `distance_threshold = 0.002` (0.2%) (line 38), VWAP window = 20 (line 63) |

**Trigger attivazione (BUY):**
```
(vwap - close) / vwap > 0.002 → BUY
(close - vwap) / vwap > 0.002 → SELL (bloccato)
```

---

## 3. Regime Detection & Strategy Selection

### RegimeDetector — `regime_detector.py`

Classifica il mercato ogni candela 1m in 4 regimi + hysteresis.

**Parametri硬codati (line 80-93):**
```
REGIME_HYSTERESIS_K = 3    # candele consecutive per conferma cambio regime
volatile:  volatility_ratio > 0.01    (1% di range ATR/close)
trending_up:  price_change_1h > 0.003 (0.3%)
trending_down: price_change_1h < -0.003 (-0.3%)
ranging:  tutto il resto
```

### StrategySelector — `strategy_selector.py`

**Mapping fisso (line 20-28 di `config_loader.py`):** Non overridabile da DB.

```
trending_up    → ema_cross
trending_down  → ema_cross
ranging        → rsi_bollinger
volatile       → stoch_rsi_bb_squeeze
unknown        → momentum_base
```

**Strategie consentite per regime (per Supervisor AI):**
```
ranging:        [rsi_bollinger, momentum_base, stoch_rsi_bb_squeeze]
volatile:       [stoch_rsi_bb_squeeze, momentum_base]
trending_up:    [ema_cross]
trending_down:  [ema_cross]
unknown:        [momentum_base]
```

**Punto di modifica:** `config_loader.py:20-35`. Si può aggiungere un nuovo regime o cambiare mapping.

---

## 4. Intelligence Layer — Signal Score Engine

### SignalScoreEngine — `signal_score_engine.py`

**Pesi correnti (DEFAULT_WEIGHTS, line 64-75) — calibrati su dati reali BTC-EUR (2026-07-15):**

| Collettore | Peso | Ruolo |
|-----------|------|-------|
| `order_book_imbalance` | **0.30** | Unico segnale reattivo — reagisce a squilibri reali del book |
| `funding_rate` | **0.15** | Bias macro — ridotto dopo calibrazione |
| `cvd` | **0.15** | Pressione buy/sell cumulativa — ridotto provisionalmente |
| `long_short_ratio` | **0.10** | Ridondante con funding_rate |
| `fear_greed` | **0.10** | Contesto, non trigger |
| `whale` | **0.05** | Contributo non verificabile |
| `open_interest` | **0.05** | Osservato come puro rumore |
| `onchain` | **0.05** | Proxy macro stabile |
| `sentiment` | **0.00** | Variabilità zero osservata — cablato OFF |
| `spread` | **0.00** | Cablato OFF |

**Score aggregation formula (solo 8 collettori attivi):**
```
score = Σ(weight_i * score_i) / Σ(active_weight_i)
clamped to [-100, +100]
```

**Soglie di tradeability:**
- `coverage < 50%` → score neutrale, non tradeabile (line 561)
- `|score| >= threshold` (DB: `SCALPING_SIGNAL_STRENGTH_THRESHOLD` = **6.0**) → bias bullish/bearish
- Trend 5m score: velocity in punti/minuto, direzione `converging`/`diverging`/`stable`

**Punto di modifica:** `signal_score_engine.py:64-75` per pesi, soglia in `.env`/DB `scalping_runtime_config`.

---

## 5. Signal Aggregation & Execution Gating

### SignalAggregator — `signal_aggregator.py`

Fonde il punteggio intelligence con il segnale tecnico della strategia per decidere se eseguire.

**Pipeline decisionale (per ogni candela 1m):**

```
1. TechnicalSignal.type == NONE? → skip
2. CLOSE signal? → sempre permesso
3. SELL signal? → bloccato (long-only engine)
4. Pochi collector attivi (<4)? → bypassa intelligence se score forte, blocca se score debole
5. |score| < 5.0 (neutrale)? → blocca
6. |score| < SCALPING_SIGNAL_STRENGTH_THRESHOLD (6.0)? → blocca
7. Bias conflict (BUY su bearish score)? → blocca, ECCETTO mean-reversion override
   per strategie ["rsi_bollinger", "stoch_rsi_bb_squeeze"]
8. Falling knife protection (trend_5m < -20.0)? → blocca mean-reversion BUY
9. TA pattern bearish + volume anomaly? → blocca BUY
   TA pattern bullish + volume anomaly? → boost confidence +0.2
10. Combined confidence = score_norm * 0.3 + technical.confidence * 0.7
    Deve essere >= SCALPING_MIN_CONFIDENCE (0.25)
```

**Parametri soglia:**
| Parametro | Valore DB | Note |
|-----------|-----------|------|
| `SCALPING_SIGNAL_STRENGTH_THRESHOLD` | 6.0 | Minimo |score| per tradeability |
| `SCALPING_MIN_CONFIDENCE` | 0.25 | Minimo combined confidence |
| `SCALPING_MIN_COLLECTORS` | 4 | Minimo collettori attivi |
| `FALLING_KNIFE_TREND_THRESHOLD` | -20.0 | Hardcoded (signal_aggregator.py:20) |
| Pesi combinati | 0.3 intel + 0.7 tech | Hardcoded (signal_aggregator.py:389) |

**Punti di modifica:**
- Soglia falling knife: `signal_aggregator.py:20`
- Pesi combinati: `signal_aggregator.py:388-389`
- Strategie mean-reversion eligibili: `signal_aggregator.py:16`
- Mean-reversion override: `signal_aggregator.py:270-340`

---

## 6. Supervisor AI

### `supervisor/supervisor_scheduler.py` + `supervisor_client.py`

Il Supervisor è un agente AI (via OpenRouter) che può:
1. **Cambiare strategia runtime** — selezionare una diversa strategia di timing
2. **Modificare parametri** — signal threshold, regime thresholds
3. **Mettere in pausa/riprendere** la sessione

**Parametri di controllo:**
| Parametro | Valore | Descrizione |
|-----------|--------|-------------|
| `SCALPING_SUPERVISOR_INTERVAL_SEC` | 600 (10 min) | Frequenza check AI |
| `SCALPING_STRATEGY_COOLDOWN_SEC` | 1200 (20 min) | Minimo tempo tra cambi strategia |
| `SCALPING_PARAM_UPDATE_COOLDOWN_SEC` | 600 (10 min) | Minimo tempo tra update params |
| `SCALPING_SUPERVISOR_MIN_TRADES_BEFORE_CHANGE` | 5 | Trade minimi prima di cambiare strategia |
| `SCALPING_SUPERVISOR_MAX_REPEAT_DECISIONS` | 3 | Max stessa decisione consecutiva |
| `SCALPING_SUPERVISOR_MAX_DAILY_CALLS` | 100 | Budget giornaliero API AI |
| Soglia segnale bounds | [5.0, 30.0] | Clamp per modifiche supervisor |

**Vincoli di azione:** Il supervisor può solo selezionare strategie dalla lista `allowed_strategies` per il regime corrente.

---

## 7. Template Strategie Pipeline (8 template)

> **File:** `strategy_generator.py:67-167`. Usati per backtest/generazione — NON per trading live.

| Template | Durata | Rischio | Parametri |
|----------|--------|---------|-----------|
| `trend_ema` | 30gg | medio | ema_fast[10,20,50], ema_slow[100,200], sl[2-3%], tp[5-12%] |
| `trend_ema_fast` | 14gg | alto | ema_fast[5,10], ema_slow[20,30], sl[1.5-2.5%], tp[3-5%] |
| `mean_reversion_rsi` | 15gg | basso | rsi_period[14], oversold[25,30], overbought[70,75], sl[2%], tp[4-6%] |
| `mean_reversion_rsi_aggressive` | 10gg | alto | rsi_period[7,14], oversold[20,25], overbought[75,80], sl[2.5%], tp[6-10%] |
| `breakout_bb` | 7gg | alto | bb_period[20], bb_std[2.0,2.5], sl[3%], tp[7-10%] |
| `breakout_bb_tight` | 5gg | alto | bb_period[14,20], bb_std[1.5,2.0], sl[2-3%], tp[5-8%] |
| `momentum_macd` | 21gg | medio | macd_fast[12], slow[26], signal[9], sl[2-3%], tp[4-7%] |
| `scalp_short_term` | 3gg | alto | ema_short[5,8], ema_long[13,21], sl[1-1.5%], tp[2-3%] |

**Filtri qualità backtest (line 24-28):** min 15 trade, Sharpe ≥ 0, drawdown < 40%, P&L > 0%
**Default pairs (line 218):** BTC/USDT, ETH/USDT, SOL/USDT, BNB/USDT
**Timeframes (line 220):** 1h, 4h
**Lookback (line 223):** 60 giorni

---

## 8. Configurazione Corrente — DB e .env

### 8.1 Sessione attiva (da DB `scalping_sessions`)

| Campo | Valore |
|-------|--------|
| Strategia attiva | `momentum_base` |
| Symbol | BTC-EUR |
| Timeframe | 1m |
| Modalità | LIVE |
| Trade value | 20.00 EUR |
| Stato | running |

### 8.2 Risk Config (da DB `scalping_risk_config`)

| Parametro | Valore |
|-----------|--------|
| `stop_loss_pct` | 0.50% (netto) |
| `take_profit_pct` | 0.80% (netto) |
| `max_daily_loss` | 2 USD |
| `max_drawdown` | 10% |
| `leverage` | 10x |
| `session_max_loss_pct` | 10% |

### 8.3 Runtime Config (da DB `scalping_runtime_config`)

| Parametro | Valore | Note |
|-----------|--------|------|
| `SCALPING_TRADE_VALUE` | 10.0 USDC | Ma sessione usa trade_value 20.0 EUR |
| `SCALPING_MAX_DAILY_LOSS` | 50.0 | Sovrascritto da risk_config (2 USD) |
| `SCALPING_MAX_DRAWDOWN_PCT` | 10.0 | |
| `SCALPING_STOP_LOSS_PCT` | 0.5 | Netto (dopo fees) |
| `SCALPING_TAKE_PROFIT_PCT` | 0.8 | Netto (dopo fees) |
| `SCALPING_SIGNAL_STRENGTH_THRESHOLD` | 6.0 | Score minimo per trade |
| `SCALPING_MIN_CONFIDENCE` | 0.25 | |
| `SCALPING_MIN_COLLECTORS` | 4 | |
| `SCALPING_STRATEGY_COOLDOWN_SEC` | 1200 | 20 min |
| `SCALPING_PARAM_UPDATE_COOLDOWN_SEC` | 600 | 10 min |
| `SCALPING_SUPERVISOR_INTERVAL_SEC` | 600 | 10 min |
| `SCALPING_REGIME_TREND_THRESHOLD_PCT` | 3.0 | |
| `SCALPING_REGIME_VOLATILE_THRESHOLD` | 0.02 | |
| `SCALPING_TA_VOLUME_ANOMALY_MULTIPLIER` | 2.0 | |

### 8.4 Weight Intelligence (da `signal_score_engine.py:64-75`)

| Collettore | Peso |
|-----------|------|
| order_book_imbalance | 0.30 |
| funding_rate | 0.15 |
| cvd | 0.15 |
| long_short_ratio | 0.10 |
| fear_greed | 0.10 |
| whale | 0.05 |
| open_interest | 0.05 |
| onchain | 0.05 |
| sentiment | 0.00 (OFF) |
| spread | 0.00 (OFF) |

---

## 9. Mappa dei Punti di Modifica

### Per modificare strategie di timing esistenti:

| Cosa modificare | File | Linee |
|----------------|------|-------|
| Soglia EMA slope | `scalping/strategies/ema_cross.py` | 13 |
| Soglie ATR%/RSI dinamiche | `scalping/strategies/rsi_bollinger.py` | 83-103 |
| Soglia BB Squeeze | `scalping/strategies/stoch_rsi_bb_squeeze.py` | 48 |
| Soglia StochRSI proxy | `scalping/strategies/stoch_rsi_bb_squeeze.py` | 49 |
| Margine momentum | `scalping/strategies/momentum_base.py` | 53 |
| Soglia VWAP distance | `scalping/strategies/vwap_reversion.py` | 38 |
| VWAP window | `scalping/strategies/vwap_reversion.py` | 63 |

### Per aggiungere/rimuovere strategie runtime:

| Cosa modificare | File | Linee |
|----------------|------|-------|
| Nuova classe strategia | `scalping/strategies/<nome>.py` | Nuovo file |
| Registrare nel registry | `scalping/strategies/registry.py` | 16-35 |
| Mappare a un regime | `scalping/config_loader.py` | 20-35 |
| Abilitare mean-reversion override | `scalping/engine/signal_aggregator.py` | 16 |

### Per modificare l'intelligence layer:

| Cosa modificare | File | Linee |
|----------------|------|-------|
| Pesi collettori | `scalping/intelligence/signal_score_engine.py` | 64-75 |
| Soglia coverage | `scalping/intelligence/signal_score_engine.py` | 561 |
| Cache TTL | `scalping/intelligence/signal_score_engine.py` | 272 |
| Nuovo collettore | `scalping/intelligence/collectors/<nome>.py` | Nuovo file |
| Circuit breaker soglia | `scalping/intelligence/collectors/circuit_breaker.py` | 14-15 |

### Per modificare la pipeline decisionale:

| Cosa modificare | File | Linee |
|----------------|------|-------|
| Pesi confidenza combinata (intel vs tech) | `scalping/engine/signal_aggregator.py` | 388-389 |
| Soglia falling knife | `scalping/engine/signal_aggregator.py` | 20 |
| Min confidence | `scalping/engine/signal_aggregator.py` | 389 (via constant vs env) |
| Regime hysteresis K | `scalping/engine/regime_detector.py` | 20 |
| Soglie regime (trend%, volatility%) | `scalping/engine/regime_detector.py` | 80-93 |

### Per modificare parametri da DB/Config:

| Cosa modificare | Dove |
|----------------|------|
| SL/TP netti % | `.env` + `scalping_risk_config` DB table |
| Signal threshold | `.env` + `scalping_runtime_config` DB table |
| Min confidence | `.env` + `scalping_runtime_config` DB table |
| Min collectors | `.env` + `scalping_runtime_config` DB table |
| Trade value | Session config (via UI/API) |
| Regime thresholds | `.env` + `scalping_runtime_config` DB table |
| Supervisor cooldowns | `.env` + `scalping_runtime_config` DB table |

### Per modificare il Supervisor AI:

| Cosa modificare | File | Linee |
|----------------|------|-------|
| System prompt | `scalping/supervisor/supervisor_client.py` | 70-200 |
| Cooldowns | `scalping/supervisor/supervisor_scheduler.py` | 28-40 |
| Bounds threshold | `scalping/supervisor/parameter_updater.py` | 117-125 |
| Budget chiamate | `.env` (`SCALPING_SUPERVISOR_MAX_DAILY_CALLS`) | — |

### Per modificare i template di generazione pipeline (non live):

| Cosa modificare | File | Linee |
|----------------|------|-------|
| Template params | `core/strategy_generator.py` | 67-167 |
| Signal map | `core/strategy_generator.py` | 52-65 |
| Quality filters | `core/strategy_generator.py` | 24-28 |
| Default pairs/timeframes | `core/strategy_generator.py` | 218-223 |
| AI evaluation | `core/run_pipeline.py` | 125-165 |
