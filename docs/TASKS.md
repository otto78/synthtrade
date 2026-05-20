# Active Tasks — SynthTrade

> **Fonte di verità:** questo file contiene il lavoro in corso e programmato.
> I task completati sono spostati in [ARCHIVE_TASKS.md](ARCHIVE_TASKS.md).
> Le idee generali e i piani a lungo termine sono in [BACKLOG.md](BACKLOG.md).

---

## 🚀 EPIC-SCALP-800 — Modulo Scalping v2.0 (Signal Intelligence)

> **Principio architetturale:** il modulo `app/scalping/` è un package autonomo montato
> sull'app FastAPI esistente senza modificare nessun file fuori da `main.py` e `config.py`.
> Ogni task include i test TDD da scrivere **prima** dell'implementazione (🔴 Red → 🟢 Green → 🔵 Refactor).
> I test del modulo scalping vivono in `tests/scalping/` per isolarli dalla suite esistente.

---

### TASK-800 — Scaffolding isolato e conftest per il modulo Scalping
**Status:** To Do
**Priorità:** Critica
**Dipende da:** nessuno (è il punto di partenza)
**Dettagli:**
Creare la struttura fisica del modulo e l'infrastruttura di test dedicata, garantendo che il modulo
sia completamente isolato dal codice esistente. Nessun file al di fuori di `main.py` e `config.py`
viene modificato in questo task.

**🔍 Verifica Duplicazioni (fare prima di implementare):**
- Aprire `app/config.py`: verificare se esiste già un sistema di sub-settings o se i settings
  sono tutti flat. Se esiste già un pattern (es. `class DatabaseSettings`), seguire lo stesso
  approccio invece di inventarne uno nuovo.
- Cercare `grep -r "APScheduler\|AsyncIOScheduler" app/` per capire come è configurato lo
  scheduler esistente e se esiste già un pattern di registrazione job da riutilizzare.
- Verificare se esiste già un `tests/conftest.py` con fixture globali che il `tests/scalping/conftest.py`
  potrebbe ereditare invece di ridefinire (es. fixture per il client Supabase mock).

**⚠️ Considerazioni di conflitto / ridondanza**
- **RiskManager duplicato:** il modulo generale possiede già `app/execution/risk_manager.py`. Prima di introdurre un nuovo RiskManager per lo scalping, verificare se è possibile estendere quello esistente con configurazioni specifiche (`SCALPING_MAX_DAILY_LOSS_PCT`, `SCALPING_MAX_CONSECUTIVE_LOSSES`).
- **Scheduler duplicato:** il progetto usa già `AsyncIOScheduler` in `app/scheduler/jobs.py`. Prima di registrare nuovi job scalping, controllare se esiste già un pattern di registrazione job da riutilizzare (es. `scheduler.add_job`).
- **OrderExecutor duplicato:** esiste `app/execution/trade_executor.py`. Se lo scalping richiede un executor separato, valutare l’estensione con flag `is_scalping` anziché creare una classe nuova.
- **Configurazione Settings:** aggiungere `ScalpingSettings` a `config.py` solo se non esiste già un sotto‑setting per moduli aggiuntivi.

**Piano di Attuazione:**
1. Creare le directory:
   ```
   app/scalping/__init__.py
   app/scalping/models/
   app/scalping/engine/
   app/scalping/intelligence/
   app/scalping/intelligence/collectors/
   app/scalping/opportunity/
   app/scalping/opportunity/pollers/
   app/scalping/supervisor/
   app/scalping/indicators/
   app/scalping/data/
   app/scalping/backtest/
   app/scalping/session/
   ```
2. Creare `tests/scalping/__init__.py` e `tests/scalping/conftest.py` con:
   - Fixture `mock_supabase_scalping` (patch del client Supabase per il modulo)
   - Fixture `sample_candles` — lista di 200 `Candle` con OHLCV realistici (BTC-like)
   - Fixture `sample_funding_snapshot` — `FundingRateSnapshot` con rate=0.0001
   - Fixture `sample_signal_score_bullish` — `SignalScore(total=+55, bias='bullish', tradeable=True)`
   - Fixture `sample_signal_score_bearish` — `SignalScore(total=-55, bias='bearish', tradeable=True)`
   - Fixture `sample_signal_score_neutral` — `SignalScore(total=+10, bias='neutral', tradeable=False)`
3. Creare `app/scalping/scalping_config.py` con classe `ScalpingSettings`:
   - `SCALPING_SYMBOL: str = "BTCUSDT"`
   - `SCALPING_TIMEFRAME: str = "1m"`
   - `SCALPING_LOOP_INTERVAL_MS: int = 1000`
   - `SCALPING_SIGNAL_SCORE_THRESHOLD: float = 30.0`
   - `SCALPING_MAX_DAILY_LOSS_PCT: float = 0.03`
   - `SCALPING_MAX_CONSECUTIVE_LOSSES: int = 5`
   - `SCALPING_SUPERVISOR_INTERVAL_MIN: int = 10`
   - `SCALPING_INTELLIGENCE_INTERVAL_SEC: int = 60`
   - `SCALPING_FUNDING_BEARISH_THRESHOLD: float = 0.001`
   - `SCALPING_FUNDING_BULLISH_THRESHOLD: float = -0.001`
   - `SCALPING_CVD_WINDOW_SIZE: int = 500`
   - Tutti i valori leggibili da `.env` con prefisso `SCALPING_`
4. Aggiungere a `config.py` (import unico): `from app.scalping.scalping_config import ScalpingSettings`
   e un campo `scalping: ScalpingSettings = ScalpingSettings()` in `Settings`.

**Test TDD da scrivere prima (`tests/scalping/test_scaffold.py`):**
- `test_scalping_config_defaults` — `ScalpingSettings()` istanzia senza errori e i valori di default
  corrispondono ai valori attesi (es. `SCALPING_MAX_DAILY_LOSS_PCT == 0.03`)
- `test_scalping_config_env_override` — override via env var `SCALPING_MAX_DAILY_LOSS_PCT=0.05`
  viene letto correttamente
- `test_scalping_module_importable` — `from app.scalping import __init__` non lancia eccezioni
- `test_existing_app_unaffected` — `GET /health` e `GET /strategies` rispondono `200` dopo
  l'aggiunta del modulo (verifica non-regression sull'app esistente)

---

### TASK-801 — Modelli Pydantic core del modulo Scalping
**Status:** To Do
**Priorità:** Alta
**Dipende da:** TASK-800
**Dettagli:**
Definire tutti i modelli di dati Pydantic usati dal modulo. I modelli sono il contratto interno
tra tutti i componenti: engine, intelligence, supervisor, frontend. Nessuna logica di business qui.

**🔍 Verifica Duplicazioni (fare prima di implementare):**
- Cercare `grep -r "class.*BaseModel" app/schemas/ app/core/` per vedere se modelli simili
  (es. `Signal`, `Trade`, `Position`) esistono già nell'app principale. Se esistono, valutare
  se estenderli o importarli direttamente invece di ridefinirli nel modulo scalping.
- Verificare se `app/schemas/trade.py` o simili hanno già un modello `Trade`/`TradeResult`
  compatibile: se sì, il modulo scalping può importarlo e aggiungere solo i campi specifici
  (es. `signal_score`, `funding_rate_at_entry`) tramite ereditarietà.
- Controllare se esistono già enum come `SignalType` o `MarketRegime` — in caso, riusarli
  con un alias invece di ridefinire valori identici in un namespace diverso.

**Piano di Attuazione:**
1. `app/scalping/models/market.py`:
   - `Candle(BaseModel)`: `open_time: datetime`, `open/high/low/close/volume: float`, `close_time: datetime`
   - `MarketRegime(str, Enum)`: `TRENDING_UP`, `TRENDING_DOWN`, `LATERAL`, `HIGH_VOLATILITY`, `LOW_VOLATILITY`
   - `OrderBook(BaseModel)`: `bids/asks: list[tuple[float, float]]`, `timestamp: datetime`

2. `app/scalping/models/signal.py`:
   - `SignalType(str, Enum)`: `BUY`, `SELL`, `HOLD`, `CLOSE`
   - `Signal(BaseModel)`: `type: SignalType`, `strategy_type: str`, `price: float`,
     `timestamp: datetime`, `confidence: float` (validato 0.0–1.0), `reason: str`

3. `app/scalping/models/position.py`:
   - `PositionSide(str, Enum)`: `LONG`, `SHORT`
   - `PositionStatus(str, Enum)`: `OPEN`, `CLOSED`, `CANCELLED`
   - `Position(BaseModel)`: `id: UUID`, `symbol: str`, `side: PositionSide`,
     `entry_price: float`, `quantity: float`, `stop_loss: float`, `take_profit: float`,
     `status: PositionStatus`, `opened_at: datetime`, `closed_at: datetime | None`,
     `exit_price: float | None`, `pnl: float | None`

4. `app/scalping/models/trade.py`:
   - `TradeResult(BaseModel)`: `position_id: UUID`, `pnl: float`, `pnl_pct: float`,
     `duration_seconds: int`, `exit_reason: str` (es. "TP_HIT", "SL_HIT", "MANUAL")

5. `app/scalping/models/strategy.py`:
   - `StrategyType(str, Enum)`: `EMA_CROSS`, `RSI_BOLLINGER`, `VWAP_REVERSION`
   - `StrategyParams(BaseModel)`: tutti i parametri (stop_loss_pct, take_profit_pct,
     position_size_pct, max_trades_per_day, min_volume_multiplier, ema_fast, ema_slow,
     rsi_period, rsi_oversold, rsi_overbought, bb_period, bb_std) con default dal piano
   - `ScalpingStrategy(BaseModel)`: `id: str`, `type: StrategyType`, `params: StrategyParams`,
     `is_active: bool`, `created_at: datetime`, `updated_at: datetime`

6. `app/scalping/models/intelligence.py`:
   - `FundingRateSnapshot(BaseModel)`: `symbol: str`, `rate: float`, `next_funding_time: int`,
     `timestamp: datetime`, `bias: str` (calcolato da rate: `bearish`/`bullish`/`neutral`)
   - `OpenInterestSnapshot(BaseModel)`: `symbol: str`, `oi_value: float`, `timestamp: datetime`
   - `LongShortRatioSnapshot(BaseModel)`: `symbol: str`, `long_pct: float`, `short_pct: float`,
     `timestamp: datetime`
   - `CVDSnapshot(BaseModel)`: `current: float`, `trend: str` (`rising`/`falling`/`neutral`),
     `divergence: bool`, `timestamp: datetime`
   - `FearGreedSnapshot(BaseModel)`: `value: int` (0–100), `classification: str`, `timestamp: datetime`
   - `MarketContext(BaseModel)`: aggregato di tutti i snapshot sopra + `signal_score: float | None`
   - `SignalScore(BaseModel)`: `total: float` (−100..+100), `breakdown: dict[str, float]`,
     `bias: str` (`bullish`/`bearish`/`neutral`), `tradeable: bool`, `primary_driver: str`

7. `app/scalping/models/opportunity.py`:
   - `OpportunitySource(str, Enum)`: `BINANCE_RSS`, `CRYPTOPANIC`, `COINGECKO`, `WHALE_ALERT`
   - `OpportunityCategory(str, Enum)`: `NEW_LISTING`, `LAUNCHPOOL`, `PROMOTION`,
     `DELISTING`, `MAINTENANCE`, `IRRELEVANT`
   - `OpportunityUrgency(str, Enum)`: `HIGH`, `MEDIUM`, `LOW`
   - `Opportunity(BaseModel)`: tutti i campi del piano incluso `content_hash: str`

8. `app/scalping/models/supervisor.py`:
   - `SupervisorAction(str, Enum)`: `UPDATE_PARAMS`, `CHANGE_STRATEGY`, `PAUSE_TRADING`,
     `RESUME_TRADING`, `NO_ACTION`
   - `SupervisorDecision(BaseModel)`: `action: SupervisorAction`, `reason: str`,
     `new_params: StrategyParams | None`, `new_strategy: StrategyType | None`,
     `confidence: float`, `market_bias: str`, `primary_signal: str`, `timestamp: datetime`

**Test TDD da scrivere prima (`tests/scalping/test_models.py`):**
- `test_candle_model_valid` — `Candle(open_time=..., open=50000, ...)` istanzia senza errori
- `test_signal_confidence_validation` — `Signal(confidence=1.5, ...)` lancia `ValidationError`
- `test_signal_score_range` — `SignalScore(total=150, ...)` lancia `ValidationError`
  (aggiungere `@field_validator` con clamp a −100..+100)
- `test_signal_score_tradeable_logic` — `total=10` → `tradeable=False` (sotto soglia 30)
- `test_funding_snapshot_bias_computed` — `rate=0.0015` → `bias='bearish'` (calcolato nel validator)
- `test_position_pnl_none_when_open` — posizione con `status=OPEN` ha `pnl=None`
- `test_opportunity_source_enum` — valore non valido lancia `ValidationError`
- `test_supervisor_decision_serialization` — `model_dump()` produce JSON serializzabile senza errori

---

### TASK-802 — Integrazione Indicatori Core e IndicatorProtocol
**Status:** To Do
**Priorità:** Media
**Dipende da:** TASK-801
**Dettagli:**
Definire il contratto `IndicatorProtocol` per garantire che tutti gli indicatori — sia quelli
esistenti in `app/core/indicators.py` sia i nuovi — siano intercambiabili.
I wrapper riutilizzano la logica già testata senza duplicarla.

**🔍 Verifica Duplicazioni (fare prima di implementare):**
- Aprire `app/core/indicators.py` e leggere le firme esatte di `ema()`, `rsi()`,
  `bollinger_bands()`: i wrapper devono adattarsi all'interfaccia reale, non a quella
  ipotizzata nel piano.
- Verificare se esiste già un `Protocol` o `ABC` per gli indicatori — se sì, estenderlo.
- Controllare se esiste già un concetto di "timing filter" o "signal filter" in
  `app/core/` o `app/execution/` che potrebbe essere riutilizzato.
- Verificare la firma di `signal_ema_crossover`, `signal_rsi_reversion` ecc. in
  `app/core/indicators.py`: se già restituiscono `pd.Series` con valori -1/0/1,
  i wrapper potrebbero essere inutili e basta importare direttamente.

**Piano di Attuazione:**
1. `app/scalping/indicators/__init__.py` (vuoto)
2. `app/scalping/indicators/protocol.py`:
   - `IndicatorProtocol(Protocol)`: metodo `calculate(candles: list[Candle]) -> pd.Series`
   - `TimingFilter(Protocol)`: metodo `is_ok(candles: list[Candle]) -> bool`
     con `reason: str` come proprietà del risultato
   - `TimingResult(NamedTuple)`: `ok: bool`, `reason: str`
3. `app/scalping/indicators/wrappers.py`:
   - `EMAWrapper(IndicatorProtocol)`: wrappa `app.core.indicators.ema()`,
     adatta l'input `list[Candle]` → `pd.Series` di close, restituisce `pd.Series`
   - `RSIWrapper(IndicatorProtocol)`: analogo per `rsi()`
   - `BollingerWrapper(IndicatorProtocol)`: restituisce `tuple[pd.Series, pd.Series, pd.Series]`
4. `app/scalping/indicators/timing_filters.py`:
   - `VolumeSpikeFilter(TimingFilter)`: `candle.volume > avg_volume * multiplier` → `TimingResult`
   - `BullishCandleFilter(TimingFilter)`: `close > open` → `TimingResult`
   - `RSIOversoldFilter(TimingFilter)`: `rsi < threshold` → `TimingResult`
   - `RSIOverboughtFilter(TimingFilter)`: `rsi > threshold` → `TimingResult`

**⚠️ Regola di non-regression:** i wrapper importano da `app.core.indicators` senza copiarne il codice.
Se `app/core/indicators.py` cambia firma, i test dei wrapper lo rilevano subito.

**Test TDD da scrivere prima (`tests/scalping/test_indicators_wrapper.py`):**
- `test_ema_wrapper_output_length` — output ha stessa lunghezza dell'input
- `test_ema_wrapper_no_lookahead` — rimuovere l'ultima candela non cambia i valori precedenti
- `test_rsi_wrapper_range` — tutti i valori sono in [0, 100]
- `test_bollinger_wrapper_ordering` — `lower < mid < upper` per ogni indice (escludendo NaN)
- `test_volume_spike_filter_true` — candela con volume 2x media → `ok=True`
- `test_volume_spike_filter_false` — candela con volume 0.5x media → `ok=False, reason` non vuoto
- `test_bullish_candle_filter` — `close > open` → `ok=True`; `close < open` → `ok=False`
- `test_rsi_oversold_filter` — rsi=28, threshold=30 → `ok=True`
- `test_existing_indicators_unchanged` — importare e chiamare `app.core.indicators.ema()` direttamente
  produce lo stesso risultato del wrapper (non-regression)

---

### TASK-803 — Implementazione VWAP e ADX
**Status:** To Do
**Priorità:** Alta
**Dipende da:** TASK-802
**Dettagli:**
Aggiungere VWAP e ADX come indicatori nativi del modulo scalping (non esistono in `app/core/indicators.py`).
Devono seguire `IndicatorProtocol` e avere reset/comportamento corretto per intraday.

**Piano di Attuazione:**
1. `app/scalping/indicators/vwap.py`:
   - `VWAPCalculator`: stato interno con `_cumulative_tp_vol` e `_cumulative_vol`
   - `calculate(candle: Candle) -> float`: aggiorna VWAP in tempo reale (stateful, un candle alla volta)
   - `reset()`: azzeramento per il reset giornaliero (da chiamare a mezzanotte UTC)
   - `calculate_series(candles: list[Candle]) -> pd.Series`: versione batch per backtest
   - Formula: `VWAP = Σ(TP × Volume) / Σ(Volume)`, dove `TP = (H+L+C)/3`
2. `app/scalping/indicators/adx.py`:
   - `adx(candles: list[Candle], period: int = 14) -> pd.Series`:
     implementazione completa DI+ DI- ADX
   - Restituisce serie con NaN per le prime `period*2` candele (warm-up necessario)
   - Espone anche `plus_di(candles, period)` e `minus_di(candles, period)` per il RegimeDetector

**Test TDD da scrivere prima (`tests/scalping/test_indicators_scalp.py`):**
- `test_vwap_first_candle` — con una sola candela, VWAP == typical price `(H+L+C)/3`
- `test_vwap_increasing_volume_weights_higher_price` — candela con volume doppio pesa il doppio
- `test_vwap_reset_clears_state` — dopo `reset()`, VWAP riparte da zero
- `test_vwap_series_matches_stateful` — `calculate_series(candles)` produce stesso risultato
  di `calculate()` candela per candela (consistenza stateful vs batch)
- `test_vwap_no_lookahead` — serie su N candele == serie su N+1 candele (primi N valori)
- `test_adx_range` — tutti i valori ADX non-NaN sono in [0, 100]
- `test_adx_warmup_nans` — prime `period*2` righe sono NaN
- `test_adx_strong_trend` — su serie con trend forte e lineare, ADX[-1] > 25
- `test_adx_weak_lateral` — su serie laterale (rumore bianco), ADX[-1] < 20
- `test_plus_di_minus_di_uptrend` — su uptrend sostenuto, `DI+ > DI-`

---

### TASK-804 — Migrazioni Supabase Schema v2.0
**Status:** To Do
**Priorità:** Alta
**Dipende da:** TASK-801
**Dettagli:**
Aggiornare il database per supportare il modulo scalping. Le migrazioni sono additive:
non modificano tabelle esistenti, aggiungono solo nuove tabelle.

**⚠️ Considerazioni di conflitto / ridondanza**
- **Schema esistente:** verificare le tabelle attuali in Supabase per evitare duplicati di colonne o tabelle con nomi simili (es. `sessions`, `trades`). Se esistono già tabelle con struttura simile, valutare l’estensione anziché crearne di nuove.
- **Chiavi esterne:** assicurarsi che le nuove FK non confliggano con constraint esistenti; controllare eventuali cascade delete già definiti.
- **Migrazioni precedenti:** eseguire `supabase db reset` in un ambiente di test per verificare che le migrazioni non rompano lo schema attuale.

**Piano di Attuazione:**
1. `supabase/migrations/20260601000001_scalping_sessions.sql`:
   ```sql
   CREATE TABLE scalping_sessions (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     mode TEXT NOT NULL CHECK (mode IN ('PAPER', 'LIVE', 'BACKTEST')),
     symbol TEXT NOT NULL,
     timeframe TEXT NOT NULL,
     status TEXT NOT NULL CHECK (status IN ('running', 'paused', 'stopped')),
     strategy_type TEXT NOT NULL,
     params JSONB NOT NULL,
     started_at TIMESTAMPTZ NOT NULL,
     stopped_at TIMESTAMPTZ,
     total_pnl NUMERIC(12,6) DEFAULT 0,
     trade_count INTEGER DEFAULT 0,
     win_count INTEGER DEFAULT 0,
     created_at TIMESTAMPTZ DEFAULT NOW()
   );
   ```
2. `supabase/migrations/20260601000002_scalping_trades.sql`:
   ```sql
   CREATE TABLE scalping_trades (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     session_id UUID REFERENCES scalping_sessions(id),
     symbol TEXT NOT NULL,
     side TEXT NOT NULL CHECK (side IN ('LONG', 'SHORT')),
     entry_price NUMERIC(12,6) NOT NULL,
     exit_price NUMERIC(12,6),
     quantity NUMERIC(12,8) NOT NULL,
     stop_loss NUMERIC(12,6) NOT NULL,
     take_profit NUMERIC(12,6) NOT NULL,
     pnl NUMERIC(12,6),
     pnl_pct NUMERIC(8,4),
     exit_reason TEXT,
     strategy_type TEXT NOT NULL,
     signal_score NUMERIC(6,2),
     funding_rate_at_entry NUMERIC(10,6),
     fear_greed_at_entry INTEGER,
     cvd_trend_at_entry TEXT,
     binance_order_id TEXT,
     entry_time TIMESTAMPTZ NOT NULL,
     exit_time TIMESTAMPTZ,
     status TEXT NOT NULL CHECK (status IN ('open', 'closed', 'cancelled'))
   );
   CREATE INDEX idx_scalping_trades_session ON scalping_trades(session_id);
   CREATE INDEX idx_scalping_trades_status ON scalping_trades(status);
   ```
3. `supabase/migrations/20260601000003_market_intel_snapshots.sql`:
   ```sql
   CREATE TABLE market_intel_snapshots (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     symbol TEXT NOT NULL,
     funding_rate NUMERIC(10,6),
     open_interest NUMERIC(20,2),
     long_pct NUMERIC(5,2),
     short_pct NUMERIC(5,2),
     cvd_current NUMERIC(20,6),
     cvd_trend TEXT,
     fear_greed_value INTEGER,
     fear_greed_label TEXT,
     signal_score NUMERIC(6,2),
     signal_bias TEXT,
     recorded_at TIMESTAMPTZ DEFAULT NOW()
   );
   CREATE INDEX idx_intel_symbol_time ON market_intel_snapshots(symbol, recorded_at DESC);
   ```
4. `supabase/migrations/20260601000004_opportunities.sql`:
   ```sql
   CREATE TABLE opportunities (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     source TEXT NOT NULL,
     category TEXT NOT NULL,
     urgency TEXT NOT NULL CHECK (urgency IN ('high', 'medium', 'low')),
     scalping_opportunity BOOLEAN DEFAULT FALSE,
     title TEXT NOT NULL,
     action TEXT,
     symbol TEXT,
     expected_volatility TEXT,
     time_sensitive BOOLEAN DEFAULT FALSE,
     url TEXT,
     raw_content TEXT,
     content_hash TEXT UNIQUE NOT NULL,
     classified_by_ai BOOLEAN DEFAULT FALSE,
     user_action TEXT CHECK (user_action IN ('watched', 'ignored', 'acted')),
     detected_at TIMESTAMPTZ DEFAULT NOW()
   );
   CREATE INDEX idx_opp_urgency_time ON opportunities(urgency, detected_at DESC);
   CREATE INDEX idx_opp_symbol ON opportunities(symbol) WHERE symbol IS NOT NULL;
   ```
5. `supabase/migrations/20260601000005_supervisor_log.sql`:
   ```sql
   CREATE TABLE supervisor_decisions (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     session_id UUID REFERENCES scalping_sessions(id),
     action TEXT NOT NULL,
     reason TEXT NOT NULL,
     confidence NUMERIC(4,3),
     market_bias TEXT,
     primary_signal TEXT,
     previous_params JSONB,
     new_params JSONB,
     previous_strategy TEXT,
     new_strategy TEXT,
     decided_at TIMESTAMPTZ DEFAULT NOW()
   );
   ```
6. Verificare con `supabase db reset` in locale che tutte le migration esistenti + le nuove si applicano senza errori.

**Test TDD da scrivere prima (`tests/scalping/test_migrations.py`):**
- `test_scalping_sessions_table_exists` — query `SELECT 1 FROM scalping_sessions LIMIT 1` non lancia errori
- `test_scalping_trades_fk_constraint` — insert con `session_id` non esistente → errore FK
- `test_opportunities_hash_unique` — insert di due opportunity con stesso `content_hash` → errore UNIQUE
- `test_market_intel_snapshot_insert` — insert + select restituisce la riga corretta
- `test_existing_tables_unmodified` — le tabelle `strategies`, `trades`, `operation_logs`, `ohlcv_cache`
  hanno le stesse colonne di prima della migrazione (non-regression schema)

---

### TASK-805 — `FundingRateCollector` (Binance Futures API)
**Status:** To Do
**Priorità:** Alta
**Dipende da:** TASK-801, TASK-804
**Dettagli:**
Raccogliere il Funding Rate corrente. Il bias contrarian è fondamentale: FR alto significa
mercato overleveraged long → il SignalScoreEngine deve pesarlo come bearish.

**Piano di Attuazione:**
1. `app/scalping/intelligence/collectors/funding_rate.py`:
   - `FundingRateCollector`:
     - `BASE_URL = "https://fapi.binance.com"`
     - `async fetch(symbol: str = "BTCUSDT") -> FundingRateSnapshot`
     - Chiamata a `GET /fapi/v1/fundingRate?symbol={symbol}&limit=1` via `aiohttp.ClientSession`
     - Calcola `bias` nel costruttore del snapshot:
       `rate > SCALPING_FUNDING_BEARISH_THRESHOLD` → `'bearish'`,
       `rate < SCALPING_FUNDING_BULLISH_THRESHOLD` → `'bullish'`, else `'neutral'`
     - Gestione errori: `aiohttp.ClientError` → lancia `CollectorError` con messaggio descrittivo
     - Timeout configurabile (default 10s)
   - `CollectorError(Exception)`: eccezione base per tutti i collector

**Test TDD da scrivere prima (`tests/scalping/test_funding_rate_collector.py`):**
- `test_fetch_returns_snapshot` — mock `aiohttp` con risposta JSON valida Binance →
  `FundingRateSnapshot` con `rate=0.0001`, `symbol="BTCUSDT"`, `bias='neutral'`
- `test_fetch_bearish_bias` — `rate=0.0015` → `bias='bearish'`
- `test_fetch_bullish_bias` — `rate=-0.0015` → `bias='bullish'`
- `test_fetch_network_error` — mock `aiohttp.ClientError` → lancia `CollectorError`
- `test_fetch_timeout` — mock `asyncio.TimeoutError` → lancia `CollectorError`
- `test_fetch_invalid_json` — risposta malformata → lancia `CollectorError`
- `test_fetch_uses_correct_endpoint` — verifica che l'URL chiamato contenga `fapi.binance.com`
  e il parametro `symbol` corretto (assert su `mock_session.get.call_args`)

---

### TASK-806 — `BinanceWsClient` (Raw WebSocket Streaming)
**Status:** To Do
**Priorità:** Critica
**Dipende da:** TASK-801, TASK-836
**Dettagli:**
Client WebSocket verso Binance per ricevere il trade stream in tempo reale.
È il cuore dell'infrastruttura real-time: il CVDCalculator e il TickProcessor dipendono da esso.
La logica di heartbeat/reconnect è definita in TASK-836 ed implementata qui.

**Piano di Attuazione:**
1. `app/scalping/engine/ws_client.py`:
   - `BinanceTradeEvent(BaseModel)`: `symbol: str`, `price: float`, `quantity: float`,
     `is_buyer_maker: bool`, `trade_time: int`
   - `BinanceCandleEvent(BaseModel)`: `symbol: str`, `interval: str`, `candle: Candle`,
     `is_closed: bool`
   - `WsEventType(str, Enum)`: `TRADE`, `KLINE`, `ERROR`, `RECONNECT`
   - `BinanceWsClient`:
     - `__init__(symbol: str, on_trade: Callable, on_kline: Callable, settings: ScalpingSettings)`
     - `async connect()`: apre connessione a
       `wss://stream.binance.com:9443/stream?streams={symbol}@trade/{symbol}@kline_1m`
     - Loop interno: riceve messaggi, fa parsing, chiama il callback appropriato
     - `async disconnect()`: chiude la connessione gracefully
     - `is_connected: bool` (property)
     - Heartbeat e reconnect: implementati seguendo le specifiche di TASK-836

**Test TDD da scrivere prima (`tests/scalping/test_ws_client.py`):**
- `test_ws_client_parses_trade_event` — mock WebSocket che invia un messaggio trade JSON →
  il callback `on_trade` viene chiamato con `BinanceTradeEvent` corretto
- `test_ws_client_parses_kline_event` — mock kline chiusa → callback `on_kline` con `is_closed=True`
- `test_ws_client_ignores_unclosed_kline` — kline aperta → callback `on_kline` non chiamato
  (oppure chiamato con `is_closed=False`, a seconda della scelta implementativa — documentare)
- `test_ws_client_is_connected_false_before_connect` — `is_connected == False` prima di `connect()`
- `test_ws_client_is_connected_true_after_connect` — `is_connected == True` dopo `connect()` (mock)
- `test_ws_client_is_connected_false_after_disconnect` — `is_connected == False` dopo `disconnect()`
- `test_ws_client_invalid_message_does_not_crash` — JSON malformato → nessuna eccezione propagata,
  errore loggato

---

### TASK-836 — WebSocket Heartbeat & Reconnect (dipendenza di TASK-806)
**Status:** To Do
**Priorità:** Critica
**Dipende da:** TASK-806 (implementazione contestuale)
**Dettagli:**
Specificare e implementare la strategia di resilienza del WS client. Va implementato
contestualmente a TASK-806 perché è parte della stessa classe.

**Piano di Attuazione:**
1. Nel `BinanceWsClient` (vedi TASK-806):
   - Ping/pong ogni 30s: inviare `PING` frame e attendere `PONG` entro 10s
   - Se nessun `PONG` entro 10s → considera connessione persa, avvia reconnect
   - Riconnessione con **exponential backoff**: 1s, 2s, 4s, 8s, 16s, cap a 60s
   - Contatore `reconnect_attempts: int` (reset a 0 dopo connessione stabile > 60s)
   - Loggare ogni tentativo: `logger.warning(f"WS reconnect attempt {n}, backoff={delay}s")`
   - Dopo 10 tentativi falliti → loggare `logger.error` e notificare via callback `on_error`
2. `app/scalping/engine/ws_client.py` espone `reconnect_count: int` (property) per i test

**Test TDD da scrivere prima (`tests/scalping/test_ws_reconnect.py`):**
- `test_reconnect_on_connection_drop` — mock WebSocket che lancia `ConnectionClosed` →
  il client tenta la riconnessione (verifica che `connect()` venga chiamato di nuovo)
- `test_reconnect_backoff_sequence` — mock che fallisce 3 volte → i delay sono 1, 2, 4 secondi
  (mock `asyncio.sleep` e verifica i valori)
- `test_reconnect_count_increments` — dopo 2 reconnect, `reconnect_count == 2`
- `test_reconnect_count_resets_after_stable` — dopo connessione stabile per >60s,
  `reconnect_count == 0`
- `test_ping_pong_sent_periodically` — mock WS → verifica che ping venga inviato entro 35s
- `test_no_pong_triggers_reconnect` — ping inviato ma nessun pong per 10s → reconnect avviato

---

### TASK-833 — `CVDCalculator` (Cumulative Volume Delta)
**Status:** To Do
**Priorità:** Alta
**Dipende da:** TASK-806 (riceve eventi trade via callback)
**Dettagli:**
Calcola il CVD accumulando il delta buy/sell da ogni trade event. Il CVD è il segnale
di pressione reale del mercato — più affidabile del solo volume totale.

**Piano di Attuazione:**
1. `app/scalping/intelligence/cvd_calculator.py`:
   - `CVDPoint(NamedTuple)`: `cvd: float`, `timestamp: int`
   - `CVDCalculator`:
     - `__init__(window_size: int = 500)`: buffer circolare `deque(maxlen=window_size)`
     - `on_trade(event: BinanceTradeEvent) -> None`:
       - `delta = event.quantity if not event.is_buyer_maker else -event.quantity`
       - `self._cvd += delta`
       - Aggiunge `CVDPoint` al buffer
     - `get_snapshot() -> CVDSnapshot`:
       - `trend`: confronta media CVD ultime 50 entry vs ultime 10 entry
         → `'rising'` se recente > storico recente, `'falling'` se < , `'neutral'` altrimenti
       - `divergence: bool` — placeholder `False` (implementazione completa in TASK-811)
     - `reset() -> None`: azzera `_cvd` e svuota buffer (per reset sessione)
     - `current_cvd: float` (property)
     - `history: list[CVDPoint]` (property, restituisce copia del buffer)

**Test TDD da scrivere prima (`tests/scalping/test_cvd_calculator.py`):**
- `test_cvd_taker_buy_positive` — trade con `is_buyer_maker=False` → CVD aumenta di `quantity`
- `test_cvd_taker_sell_negative` — trade con `is_buyer_maker=True` → CVD diminuisce di `quantity`
- `test_cvd_accumulates` — sequenza di 5 trade → CVD è la somma algebrica corretta
- `test_cvd_buffer_size_limited` — dopo `window_size + 100` trade, buffer ha esattamente
  `window_size` elementi
- `test_cvd_snapshot_trend_rising` — iniettare 100 buy pesanti → `trend == 'rising'`
- `test_cvd_snapshot_trend_falling` — iniettare 100 sell pesanti → `trend == 'falling'`
- `test_cvd_reset` — dopo `reset()`, `current_cvd == 0.0` e `len(history) == 0`
- `test_cvd_snapshot_is_copy` — modificare il risultato di `history` non modifica lo stato interno

---

### TASK-807 — Collectors `OpenInterest` e `LongShortRatio`
**Status:** To Do
**Priorità:** Media
**Dipende da:** TASK-805 (stesso pattern collector, condivide `CollectorError`)
**Dettagli:**
Raccogliere dati sull'esposizione del mercato per identificare potenziali squeeze e inversioni.

**Piano di Attuazione:**
1. `app/scalping/intelligence/collectors/open_interest.py`:
   - `OpenInterestCollector`:
     - `async fetch(symbol: str) -> OpenInterestSnapshot`
     - Endpoint: `GET https://fapi.binance.com/fapi/v1/openInterest?symbol={symbol}`
     - Parsing di `openInterest` (float) e `time` (timestamp)
2. `app/scalping/intelligence/collectors/long_short_ratio.py`:
   - `LongShortRatioCollector`:
     - `async fetch(symbol: str, period: str = "5m") -> LongShortRatioSnapshot`
     - Endpoint: `GET https://fapi.binance.com/futures/data/globalLongShortAccountRatio`
     - Parametri: `symbol`, `period`, `limit=1`
     - Parsing di `longAccount` e `shortAccount` (float)

**Test TDD da scrivere prima (`tests/scalping/test_collectors_oi_ls.py`):**
- `test_oi_collector_returns_snapshot` — mock HTTP → `OpenInterestSnapshot` con valori corretti
- `test_oi_collector_network_error` — mock errore → lancia `CollectorError`
- `test_ls_collector_returns_snapshot` — mock HTTP → `long_pct + short_pct == 100.0` (±0.01)
- `test_ls_collector_network_error` — lancia `CollectorError`
- `test_ls_ratio_sum_validation` — se la risposta API ha valori che non sommano a ~1.0,
  il collector logga warning ma non crasha (graceful degradation)

---

### TASK-808 — Collectors `FearGreed` e `Sentiment` (CryptoPanic)
**Status:** To Do
**Priorità:** Media
**Dipende da:** TASK-805 (stesso pattern)
**Dettagli:**
Integrare fonti esterne di sentiment per il contesto macro. Il Fear & Greed si aggiorna
una volta al giorno — da cacheare in memoria per non fare chiamate inutili.

**Piano di Attuazione:**
1. `app/scalping/intelligence/collectors/fear_greed.py`:
   - `FearGreedCollector`:
     - `API_URL = "https://api.alternative.me/fng/"`
     - `async fetch() -> FearGreedSnapshot`
     - **Cache in memoria**: se l'ultimo fetch è stato < 1h fa, restituisce il valore cachato
     - `_last_fetched: datetime | None` e `_cached: FearGreedSnapshot | None`
2. `app/scalping/intelligence/collectors/sentiment.py`:
   - `CryptoPanicCollector`:
     - `BASE_URL = "https://cryptopanic.com/api/v1/posts/"`
     - `async fetch(currencies: list[str] = ["BTC"]) -> list[dict]`
     - Filtra per `filter=important` e `public=true`
     - Richiede `settings.CRYPTOPANIC_TOKEN` (opzionale: se non configurato, restituisce lista vuota
       con log warning invece di crashare)
     - Restituisce lista grezza di news (titolo, url, source, published_at, sentiment_score)
   - Aggiungere `CRYPTOPANIC_TOKEN: str = ""` a `ScalpingSettings`

**Test TDD da scrivere prima (`tests/scalping/test_collectors_sentiment.py`):**
- `test_fear_greed_returns_snapshot` — mock HTTP → `FearGreedSnapshot` con `value=45`,
  `classification='Neutral'`
- `test_fear_greed_cache_prevents_second_call` — due `fetch()` consecutivi entro 1h →
  HTTP chiamato una sola volta (verifica `mock_session.get.call_count == 1`)
- `test_fear_greed_cache_expired_after_1h` — cache di 2h fa → HTTP chiamato di nuovo
- `test_cryptopanic_no_token_returns_empty` — `CRYPTOPANIC_TOKEN=""` → lista vuota, nessuna eccezione
- `test_cryptopanic_returns_list` — mock HTTP con 3 news → lista di 3 dizionari
- `test_cryptopanic_network_error` — lancia `CollectorError`

---

### TASK-809 — `SignalScoreEngine` (Weighted Aggregation)
**Status:** To Do
**Priorità:** Critica
**Dipende da:** TASK-805, TASK-807, TASK-808, TASK-833
**Dettagli:**
Il cuore del Signal Intelligence layer: aggrega tutti i segnali in un unico score da −100 a +100.
I pesi devono essere configurabili (l'AI Supervisor potrà aggiornarli in TASK-823).

**Piano di Attuazione:**
1. `app/scalping/intelligence/signal_score_engine.py`:
   - `SignalWeights(BaseModel)`:
     - `funding_rate: float = 0.25`
     - `cvd: float = 0.25`
     - `open_interest: float = 0.15`
     - `long_short_ratio: float = 0.15`
     - `fear_greed: float = 0.10`
     - `onchain: float = 0.10`
     - Validator: somma pesi == 1.0 (±0.001)
   - `SignalScoreEngine`:
     - `__init__(weights: SignalWeights = SignalWeights())`
     - `calculate(context: MarketContext) -> SignalScore`:
       - Funding Rate: `rate > 0.001` → score negativo (fino a −100 lineare); viceversa positivo
       - CVD: mappa `trend` → score: `rising=+50`, `falling=-50`, `neutral=0`
         (con scaling sul volume relativo se disponibile)
       - Long/Short: `long_pct > 70` → negativo (contrarian); `long_pct < 30` → positivo
       - Fear & Greed: estremi (`>80` o `<20`) → contrarian score
       - Open Interest: usato come amplificatore del bias (non come segnale diretto)
         — se OI cresce + price laterale → `tradeable = False` (breakout imminente, non scalping)
       - Score finale pesato: `total = Σ(score_i × weight_i)`
       - `bias`: `'bullish'` se `total > 20`, `'bearish'` se `total < -20`, else `'neutral'`
       - `tradeable`: `abs(total) >= settings.SCALPING_SIGNAL_SCORE_THRESHOLD`
       - `primary_driver`: chiave del componente con contributo assoluto maggiore
     - `update_weights(new_weights: SignalWeights) -> None` — per il ParameterUpdater
   - `_score_funding_rate(rate: float, thresholds: tuple) -> float` — funzione pura privata
   - `_score_cvd(snapshot: CVDSnapshot) -> float` — funzione pura privata
   - `_score_long_short(snapshot: LongShortRatioSnapshot) -> float` — funzione pura privata
   - `_score_fear_greed(snapshot: FearGreedSnapshot) -> float` — funzione pura privata

**Test TDD da scrivere prima (`tests/scalping/test_signal_score_engine.py`):**
- `test_all_neutral_signals_score_zero` — tutti i segnali al valore neutro → `total ≈ 0`
- `test_overleveraged_long_bearish` — `funding_rate=0.002, long_pct=75, fear_greed=82` →
  `total < -30, bias='bearish', tradeable=True`
- `test_all_bullish_signals` — funding negativo + CVD rising + long_pct=25 + fear_greed=15 →
  `total > 30, bias='bullish', tradeable=True`
- `test_conflicting_signals_neutral` — metà bullish metà bearish → `tradeable=False`
- `test_score_clamped_to_range` — anche con segnali estremi, `total ∈ [-100, 100]`
- `test_weights_must_sum_to_one` — `SignalWeights(funding_rate=0.5, cvd=0.5, ...)` con somma ≠ 1 →
  `ValidationError`
- `test_update_weights_takes_effect` — cambiare pesi → score cambia per stesso `MarketContext`
- `test_primary_driver_identified` — il campo `primary_driver` corrisponde al componente
  con `abs(score_i × weight_i)` massimo
- `test_oi_growing_lateral_not_tradeable` — OI in crescita + trend laterale → `tradeable=False`
  indipendentemente dal total score

---

### TASK-810 — `IntelligenceScheduler` e DB Snapshots
**Status:** To Do
**Priorità:** Media
**Dipende da:** TASK-805, TASK-807, TASK-808, TASK-809, TASK-804
**Dettagli:**
Automatizzare la raccolta dati e il salvataggio su Supabase. Lo scheduler non deve
interferire con APScheduler dell'app esistente: usa un'istanza separata con prefisso job `scalping_`.

**Piano di Attuazione:**
1. `app/scalping/intelligence/intelligence_scheduler.py`:
   - `IntelligenceScheduler`:
     - Usa `AsyncIOScheduler` da APScheduler (istanza propria, non condivisa con `app/scheduler/`)
     - `start(symbol: str)`: registra i job con id prefissati `scalping_intel_*`
     - Job `scalping_intel_funding` ogni `SCALPING_INTELLIGENCE_INTERVAL_SEC` secondi:
       chiama `FundingRateCollector.fetch()` → aggiorna `self._last_funding`
     - Job `scalping_intel_oi` ogni 5 minuti
     - Job `scalping_intel_ls` ogni 5 minuti
     - Job `scalping_intel_feargreed` ogni 60 minuti
     - Job `scalping_intel_snapshot` ogni `SCALPING_INTELLIGENCE_INTERVAL_SEC` secondi:
       chiama `SignalScoreEngine.calculate()` → salva su `market_intel_snapshots` via Supabase
     - `stop()`: spegne lo scheduler
     - `get_current_context() -> MarketContext`: restituisce l'ultimo context assemblato
     - `_last_error: dict[str, Exception]`: traccia l'ultimo errore per job (per TASK-835)
   - Se un collector fallisce (eccezione), loggare e usare l'ultimo valore valido
     (non crashare lo scheduler)

**Test TDD da scrivere prima (`tests/scalping/test_intelligence_scheduler.py`):**
- `test_scheduler_starts_and_stops` — `start()` + `stop()` senza errori; `scheduler.running` cambia stato
- `test_scheduler_jobs_have_scalping_prefix` — tutti i job id iniziano con `scalping_intel_`
- `test_scheduler_does_not_conflict_with_main_scheduler` — lo scheduler del modulo scalping
  è un'istanza diversa dall'`AsyncIOScheduler` di `app/scheduler/` (verifica `id(scheduler) !=`)
- `test_collector_error_does_not_stop_scheduler` — mock collector che lancia `CollectorError` →
  scheduler continua a girare, errore registrato in `_last_error`
- `test_get_current_context_returns_last_valid` — dopo un tick riuscito, `get_current_context()`
  restituisce `MarketContext` non None
- `test_snapshot_saved_to_supabase` — mock Supabase → dopo un tick, `table.insert` chiamato
  con i dati corretti

---

### TASK-811 — `RegimeDetector` con ADX + ATR + BB Width
**Status:** To Do
**Priorità:** Media
**Dipende da:** TASK-803, TASK-802
**Dettagli:**
Identificare il regime di mercato corrente. Questo determina quale strategia tecnica
viene attivata come filtro di timing.

**Piano di Attuazione:**
1. `app/scalping/engine/regime_detector.py`:
   - `RegimeDetector`:
     - `__init__(settings: ScalpingSettings)`
     - Aggiungere a `ScalpingSettings`:
       - `REGIME_ADX_TREND_THRESHOLD: float = 25.0`
       - `REGIME_ADX_LATERAL_THRESHOLD: float = 20.0`
       - `REGIME_ATR_VOLATILITY_MULTIPLIER: float = 2.0`
       - `REGIME_BB_WIDTH_COMPRESSION_RATIO: float = 0.8`
     - `detect(candles: list[Candle]) -> MarketRegime`:
       1. Calcola ADX, ATR, BB width dalla lista candele
       2. Se `ATR > ATR_avg_20 * REGIME_ATR_VOLATILITY_MULTIPLIER` → `HIGH_VOLATILITY`
       3. Elif `ADX > REGIME_ADX_TREND_THRESHOLD`:
          - Se `EMA_fast > EMA_slow` → `TRENDING_UP`
          - Else → `TRENDING_DOWN`
       4. Elif `ADX < REGIME_ADX_LATERAL_THRESHOLD` e `BB_width < BB_width_avg * 0.8` → `LOW_VOLATILITY`
       5. Else → `LATERAL`
     - Richiede almeno 50 candele (warm-up ADX); se meno → restituisce `LATERAL` con log warning
   - `StrategySelector`:
     - `select(regime: MarketRegime) -> StrategyType`:
       - `TRENDING_UP/DOWN` → `EMA_CROSS`
       - `LATERAL` → `RSI_BOLLINGER`
       - `HIGH_VOLATILITY` → `VWAP_REVERSION` (più sicura)
       - `LOW_VOLATILITY` → `RSI_BOLLINGER`

**Test TDD da scrivere prima (`tests/scalping/test_regime_detector.py`):**
- `test_detect_trending_up` — candles con uptrend forte (ADX > 25, EMA fast > slow) → `TRENDING_UP`
- `test_detect_trending_down` — downtrend → `TRENDING_DOWN`
- `test_detect_lateral` — ADX < 20 + BB width compresso → `LATERAL` o `LOW_VOLATILITY`
- `test_detect_high_volatility` — ATR doppio della media → `HIGH_VOLATILITY`
- `test_warmup_too_few_candles` — < 50 candele → `LATERAL` (senza crash)
- `test_strategy_selector_trending_up` — `TRENDING_UP` → `EMA_CROSS`
- `test_strategy_selector_high_volatility` — `HIGH_VOLATILITY` → `VWAP_REVERSION`
- `test_detector_thresholds_configurable` — abbassare `REGIME_ADX_TREND_THRESHOLD` a 15 →
  stesso dataset classifica come TRENDING che prima era LATERAL

---

### TASK-812 — `SignalAggregator` (Intel Bias + Technical Timing)
**Status:** To Do
**Priorità:** Alta
**Dipende da:** TASK-809, TASK-802, TASK-811
**Dettagli:**
Il gate finale prima dell'esecuzione: un ordine viene passato a `OrderExecutor` solo se
intelligence e timing tecnico concordano. Include tutti i test di scenario (ex TASK-813).

**Piano di Attuazione:**
1. `app/scalping/engine/signal_aggregator.py`:
   - `ExecutionDecision(BaseModel)`:
     - `execute: bool`
     - `reason: str`
     - `confidence: float` (0.0 se `execute=False`)
     - `final_signal: SignalType | None`
   - `SignalAggregator` (funzione pura, no stato):
     - `should_execute(technical_signal: Signal, market_score: SignalScore) -> ExecutionDecision`:
       - **Gate 1** — score tradeable: se `not market_score.tradeable` → `execute=False`,
         `reason=f"Score intelligenza insufficiente ({market_score.total:.1f})"`
       - **Gate 2** — allineamento direzione:
         - `score.bias == 'bullish'` e `signal.type == BUY` → allineati
         - `score.bias == 'bearish'` e `signal.type == SELL/CLOSE` → allineati
         - `score.bias == 'neutral'` → blocca sempre con `reason="Bias neutro, attendere segnale chiaro"`
         - In conflitto → `execute=False`,
           `reason=f"Conflitto: tecnico={signal.type.value} vs intel={score.bias}"`
       - **Gate 3** — confidence minima: `signal.confidence < 0.5` → blocca
       - Se tutti i gate passano → `execute=True`, `confidence=market_score.total/100`
     - Deve essere **funzione pura**: stessi input → stesso output, nessuno stato interno
   - Tutti i blocchi vengono loggati (il chiamante passa il logger o usa il logger del modulo)

**Test TDD da scrivere prima (`tests/scalping/test_signal_aggregator.py`):**
- `test_allows_buy_when_bullish_aligned` — score bullish + BUY tecnico → `execute=True`
- `test_allows_sell_when_bearish_aligned` — score bearish + SELL tecnico → `execute=True`
- `test_blocks_buy_when_bearish_score` — score bearish + BUY tecnico → `execute=False`,
  reason contiene "Conflitto"
- `test_blocks_sell_when_bullish_score` — score bullish + SELL tecnico → `execute=False`
- `test_blocks_when_score_not_tradeable` — `tradeable=False` → `execute=False`,
  reason contiene "insufficiente"
- `test_blocks_neutral_bias` — `bias='neutral'` → `execute=False` sempre
- `test_blocks_low_confidence_technical` — `signal.confidence=0.3` → `execute=False`
- `test_confidence_proportional_to_score` — `score.total=80` → `confidence=0.8`
- `test_overleveraged_long_blocks_buy` — scenario end-to-end:
  `funding=0.002, long_pct=75, fear_greed=82` → SignalScoreEngine produce bearish →
  SignalAggregator blocca BUY tecnico (test di integrazione tra i due componenti)
- `test_is_pure_function` — stessi argomenti chiamati 100 volte → stesso risultato

---

### TASK-813 — (Incorporato in TASK-812)
> ~~**TASK-813 — Unit Test per Signal Alignment Logic**~~
> I test di allineamento sono stati integrati direttamente in TASK-812 per evitare
> frammentazione. Il task è rimosso dalla lista attiva.

---

### TASK-814 — `RiskManager` Scalping (Daily Loss Hard Stop)
**Status:** To Do
**Priorità:** Alta
**Dipende da:** TASK-801, TASK-804
**Dettagli:**
Risk manager specifico per scalping — separato da `app/core/risk_manager.py` per evitare
di modificare codice esistente. Condivide il pattern ma ha regole diverse (velocità, intraday).

**Piano di Attuazione:**
1. `app/scalping/engine/risk_manager.py` (nuovo file, NON modificare `app/core/risk_manager.py`):
   - `ScalpingRiskConfig(BaseModel)`:
     - `max_daily_loss_pct: float` (default da `ScalpingSettings`)
     - `max_consecutive_losses: int`
     - `max_position_size_pct: float = 0.05`
     - `max_trades_per_day: int = 20`
   - `RiskCheckResult(BaseModel)`: `allowed: bool`, `reason: str`
   - `ScalpingRiskManager`:
     - `__init__(config: ScalpingRiskConfig)`
     - Stato interno: `daily_pnl: float`, `consecutive_losses: int`,
       `trades_today: int`, `_session_date: date`
     - `check_pre_trade(capital: float) -> RiskCheckResult`:
       - Daily loss check: `daily_pnl < -(capital * max_daily_loss_pct)` → `allowed=False`
       - Consecutive losses: `consecutive_losses >= max_consecutive_losses` → `allowed=False`
       - Max trades: `trades_today >= max_trades_per_day` → `allowed=False`
     - `on_trade_opened() -> None`: `trades_today += 1`
     - `on_trade_closed(pnl: float) -> None`:
       - `daily_pnl += pnl`
       - Se `pnl < 0`: `consecutive_losses += 1`; else: `consecutive_losses = 0`
     - `reset_daily() -> None`: azzeramento per nuovo giorno (chiamato dallo scheduler)
     - `_check_date_reset() -> None`: auto-reset se `_session_date != date.today()`

**Test TDD da scrivere prima (`tests/scalping/test_scalping_risk_manager.py`):**
- `test_allows_trade_when_within_limits` — tutti i limiti rispettati → `allowed=True`
- `test_blocks_on_daily_loss_exceeded` — `daily_pnl = -(capital * 0.04)`, soglia 3% →
  `allowed=False`, reason contiene "daily loss"
- `test_blocks_on_consecutive_losses` — 5 perdite consecutive, soglia 5 → `allowed=False`
- `test_resets_consecutive_on_win` — 4 perdite + 1 vincita → `consecutive_losses == 0`
- `test_blocks_on_max_trades` — 20 trade aperti, soglia 20 → `allowed=False`
- `test_daily_reset_clears_state` — dopo `reset_daily()`, tutti i contatori a zero
- `test_auto_reset_on_new_day` — `_session_date` ieri → `check_pre_trade()` fa auto-reset
- `test_does_not_modify_existing_risk_manager` — import di `app.core.risk_manager` funziona
  ancora senza errori (non-regression)

---

### TASK-815 — `OrderExecutor` Scalping (Binance Testnet + OCO)
**Status:** To Do
**Priorità:** Alta
**Dipende da:** TASK-814, TASK-801
**Dettagli:**
Esecutore ordini specifico per scalping con supporto OCO (One-Cancels-the-Other) per
impostare SL e TP lato server Binance. Usa `BinanceExchangeAdapter` già esistente
oppure wrappa CCXT con configurazione Futures/Spot dedicata.

**Piano di Attuazione:**
1. `app/scalping/engine/order_executor.py`:
   - `ScalpingOrderExecutor`:
     - `__init__(exchange_adapter, paper_mode: bool = True)`
     - `async open_long(symbol: str, quantity: float, stop_loss: float, take_profit: float) -> Position`:
       - In paper mode: non chiama il vero exchange, crea `Position` con prezzi simulati
       - In live mode: chiama OCO order API Binance
         `POST /api/v3/order/oco` con `stopPrice=stop_loss, price=take_profit, side=SELL`
         poi un order market BUY separato per l'entrata
       - Ritorna `Position` con `status=OPEN`
     - `async close_position(position: Position, current_price: float, reason: str) -> TradeResult`:
       - In paper mode: calcola PnL simulato
       - In live mode: cancella OCO pending + market order opposto
       - Ritorna `TradeResult`
     - `async get_open_orders(symbol: str) -> list[dict]`
   - Gestione errori Binance specifici: `MIN_NOTIONAL` (size troppo piccola),
     `INSUFFICIENT_BALANCE`, errori di rate limit → wrappati in `OrderExecutorError`

**Test TDD da scrivere prima (`tests/scalping/test_order_executor.py`):**
- `test_open_long_paper_mode` — `paper_mode=True` → exchange non chiamato,
  `Position` restituita con `status=OPEN`, `entry_price` == prezzo simulato
- `test_close_position_paper_pnl_long` — long entry 50000, exit 51000, qty 0.001 →
  `pnl == 1.0` (USD), `pnl_pct ≈ 0.02`
- `test_close_position_paper_pnl_loss` — exit < entry → `pnl < 0`
- `test_open_long_live_calls_exchange` — mock exchange → `create_order` chiamato
- `test_executor_wraps_exchange_error` — exchange lancia eccezione → `OrderExecutorError`
- `test_paper_mode_does_not_call_real_exchange` — nessuna chiamata HTTP reale in paper mode

---

### TASK-816 — `ScalpingEngine` Loop & Concurrency
**Status:** To Do
**Priorità:** Critica
**Dipende da:** TASK-811, TASK-812, TASK-814, TASK-815, TASK-806
**Dettagli:**
Il loop principale del Layer 1. Delega tutta la business logic al `TickProcessor` (TASK-834).
Gestisce solo il ciclo, lo stato (Started/Paused/Stopped) e la concorrenza.

**Piano di Attuazione:**
1. `app/scalping/engine/loop.py`:
   - `EngineState(str, Enum)`: `IDLE`, `RUNNING`, `PAUSED`, `STOPPED`
   - `ScalpingEngine`:
     - `__init__(tick_processor, ws_client, settings: ScalpingSettings)`
     - `state: EngineState` (property, thread-safe con `asyncio.Lock`)
     - `async start(symbol: str, mode: str) -> None`:
       - Valida `mode ∈ {'PAPER', 'LIVE', 'BACKTEST'}`
       - Avvia `BinanceWsClient.connect()`
       - Setta `state = RUNNING`
       - Avvia loop interno
     - `async pause() -> None`: setta `state = PAUSED` (il loop continua ma salta il tick)
     - `async resume() -> None`: setta `state = RUNNING`
     - `async stop() -> None`: setta `state = STOPPED`, disconnette WS, chiude posizioni aperte
     - `_loop()`: coroutine interna che chiama `tick_processor.process_tick()` ogni
       `SCALPING_LOOP_INTERVAL_MS` ms; in stato `PAUSED` salta il processing ma non esce
   - Singleton gestito tramite dependency injection in FastAPI (non globale)

**Test TDD da scrivere prima (`tests/scalping/test_scalping_engine.py`):**
- `test_initial_state_is_idle` — motore appena creato → `state == IDLE`
- `test_start_sets_running` — `await engine.start(...)` → `state == RUNNING`
- `test_pause_sets_paused` — `start()` poi `pause()` → `state == PAUSED`
- `test_resume_sets_running` — `pause()` poi `resume()` → `state == RUNNING`
- `test_stop_sets_stopped` — `stop()` → `state == STOPPED`
- `test_tick_not_called_when_paused` — mock `tick_processor` → in stato PAUSED,
  `process_tick()` non viene chiamato
- `test_stop_disconnects_ws` — mock `ws_client` → `disconnect()` chiamato su `stop()`
- `test_invalid_mode_raises` — `start(mode="INVALID")` → `ValueError`
- `test_engine_state_is_thread_safe` — `pause()` e `resume()` chiamati concorrentemente
  non portano a stato inconsistente

---

### TASK-834 — `TickProcessor` (Business Logic per tick)
**Status:** To Do
**Priorità:** Alta
**Dipende da:** TASK-811, TASK-812, TASK-814, TASK-815, TASK-810
**Dettagli:**
Tutta la logica di business eseguita ad ogni tick. Il `ScalpingEngine` non conosce
questa logica — chiama solo `process_tick()`.

**Piano di Attuazione:**
1. `app/scalping/engine/tick_processor.py`:
   - `TickProcessor`:
     - `__init__(candle_buffer, regime_detector, strategy_selector, strategy_map,
                 signal_aggregator, risk_manager, order_executor,
                 intelligence_scheduler, position_manager, ws_broadcaster, settings)`
     - `async process_tick(candle: Candle) -> TickResult | None`:
       1. Aggiunge candle al buffer; se buffer non pronto (< warm-up) → `return None`
       2. `regime = regime_detector.detect(buffer.get())`
       3. `strategy_type = strategy_selector.select(regime)`
       4. `strategy = strategy_map[strategy_type]`
       5. `technical_signal = strategy.evaluate(buffer.get(), indicators)`
       6. `market_context = intelligence_scheduler.get_current_context()`
       7. `market_score = signal_score_engine.calculate(market_context)`
       8. `decision = signal_aggregator.should_execute(technical_signal, market_score)`
       9. Se `not decision.execute` → log + broadcast `SIGNAL_BLOCKED` event → return
       10. `risk_result = risk_manager.check_pre_trade(capital)`
       11. Se `not risk_result.allowed` → log + broadcast `RISK_BLOCK` event → return
       12. Se `technical_signal.type == BUY` e nessuna posizione aperta:
           - `position = await order_executor.open_long(...)`
           - `risk_manager.on_trade_opened()`
       13. Se `technical_signal.type in (SELL, CLOSE)` e posizione aperta:
           - `trade = await order_executor.close_position(...)`
           - `risk_manager.on_trade_closed(trade.pnl)`
           - Salva trade su Supabase
       14. Broadcast evento WS al frontend
     - `TickResult(BaseModel)`: `action_taken: str`, `signal: Signal`, `decision: ExecutionDecision`
   - `CandleBuffer`:
     - `add(candle: Candle)`, `get() -> list[Candle]`, `is_ready(min_size: int) -> bool`
     - Dimensione configurabile (default 200)

**Test TDD da scrivere prima (`tests/scalping/test_tick_processor.py`):**
- `test_tick_returns_none_when_buffer_not_ready` — buffer con 10 candele, min=50 → `None`
- `test_tick_no_trade_when_aggregator_blocks` — mock aggregator che blocca →
  `order_executor.open_long` non chiamato
- `test_tick_no_trade_when_risk_blocks` — mock risk che blocca → nessun ordine
- `test_tick_opens_position_on_aligned_buy` — mock aggregator `execute=True` + BUY tecnico →
  `order_executor.open_long` chiamato una volta
- `test_tick_closes_position_on_sell` — posizione aperta + CLOSE tecnico →
  `order_executor.close_position` chiamato
- `test_tick_does_not_double_open` — posizione già aperta + altro BUY → nessun secondo open
- `test_tick_broadcasts_ws_event` — mock `ws_broadcaster` → `broadcast` chiamato ad ogni tick
- `test_tick_saves_trade_on_close` — mock Supabase → insert chiamato dopo chiusura posizione

---

### TASK-817 — Router FastAPI `/scalping/*` e WebSocket Events
**Status:** To Do
**Priorità:** Media
**Dipende da:** TASK-816, TASK-834, TASK-804
**Dettagli:**
Esporre le API REST e WebSocket del modulo scalping. Il router viene montato in `main.py`
con `app.include_router(scalping_router, prefix="/scalping")` senza modificare nessun altro router.

**Piano di Attuazione:**
1. `app/scalping/router.py`:
   - `scalping_router = APIRouter(prefix="/scalping", tags=["scalping"])`
   - Endpoint sessione:
     - `POST /session/start` → avvia `ScalpingEngine.start()`, risponde `202` con `session_id`
     - `POST /session/stop` → `ScalpingEngine.stop()`
     - `POST /session/pause` → `ScalpingEngine.pause()`
     - `POST /session/resume` → `ScalpingEngine.resume()`
     - `GET /session/status` → `EngineState` corrente + session info
   - Endpoint intelligence:
     - `GET /intelligence/snapshot` → `IntelligenceScheduler.get_current_context()`
     - `GET /intelligence/signal-score` → `SignalScore` corrente
   - Endpoint trade:
     - `GET /trades` → lista trade sessione corrente da Supabase (paginato)
     - `GET /trades/open` → posizione aperta corrente (se esiste)
   - Endpoint supervisor:
     - `GET /supervisor/log` → ultime N decisioni da `supervisor_decisions`
   - WebSocket:
     - `WS /ws/scalping` → stream eventi: `candle`, `signal`, `signal_blocked`,
       `risk_block`, `position_opened`, `position_closed`, `supervisor_decision`,
       `intel_update`
2. `ScalpingWsBroadcaster`:
   - `broadcast_candle(candle: Candle)`, `broadcast_signal(signal: Signal)`,
     `broadcast_position(position: Position)`, `broadcast_intel(score: SignalScore)`, ecc.
   - Usa il `ConnectionManager` esistente (se esiste) o ne crea uno nuovo per il namespace scalping
3. In `main.py`: aggiungere `from app.scalping.router import scalping_router`
   e `app.include_router(scalping_router)` (unica modifica a file esistente)

**Test TDD da scrivere prima (`tests/scalping/test_router.py`):**
- `test_post_session_start_returns_202` — mock engine → risposta `202` con body `{session_id}`
- `test_post_session_stop` — `200` con stato updated
- `test_get_session_status_idle` — engine non avviato → `{"state": "IDLE"}`
- `test_get_intelligence_snapshot` — mock scheduler → risposta con `MarketContext` serializzato
- `test_get_trades_empty` — nessun trade in sessione → lista vuota
- `test_get_trades_open_no_position` — nessuna posizione → `404` o body `null`
- `test_existing_routes_unaffected` — `GET /strategies`, `GET /dashboard`, `GET /logs`
  rispondono ancora `200` dopo il mount del router scalping (non-regression critica)
- `test_scalping_router_prefix` — tutti gli endpoint scalping iniziano con `/scalping/`

---

### TASK-835 — Scheduler Health-Check
**Status:** To Do
**Priorità:** Media
**Dipende da:** TASK-810, TASK-817
**Dettagli:**
Monitorare la salute degli scheduler (Intelligence e Supervisor) e esporre metriche.

**Piano di Attuazione:**
1. `app/scalping/intelligence/intelligence_scheduler.py` — aggiungere:
   - `execution_metrics: dict[str, SchedulerJobMetric]` dove:
     - `SchedulerJobMetric(BaseModel)`: `job_id: str`, `last_run: datetime | None`,
       `last_duration_ms: float | None`, `last_error: str | None`, `run_count: int`,
       `error_count: int`
   - Decoratore `@track_metrics(job_id)` applicato a ogni job function
   - `get_health() -> dict[str, SchedulerJobMetric]`: restituisce lo stato di tutti i job
2. `GET /scalping/scheduler/health` nell'endpoint router (TASK-817):
   - Restituisce `execution_metrics` + `scheduler.running: bool`
   - Se un job ha `error_count > 5 negli ultimi 10 run` → `status: "degraded"`
3. Auto-restart: se un job va in errore 3 volte consecutive, `reschedule()` con backoff 2x

**Test TDD da scrivere prima (`tests/scalping/test_scheduler_health.py`):**
- `test_metrics_initialized_empty` — prima di qualunque run, `run_count == 0` per ogni job
- `test_metrics_updated_after_run` — dopo un'esecuzione, `run_count == 1`, `last_run` non None
- `test_error_count_increments` — job che lancia eccezione → `error_count == 1`
- `test_health_endpoint_returns_all_jobs` — `GET /scalping/scheduler/health` include tutti i job
- `test_health_degraded_on_repeated_errors` — 6 errori consecutivi → `status: "degraded"`

---

### TASK-818 — Pollers `BinanceRSSPoller` e `WhaleAlertPoller`
**Status:** To Do
**Priorità:** Media
**Dipende da:** TASK-801
**Dettagli:**
Raccogliere news e annunci per il feed opportunità.

**Piano di Attuazione:**
1. `app/scalping/opportunity/pollers/binance_rss.py`:
   - `RawAnnouncement(BaseModel)`: `source: str`, `title: str`, `summary: str`,
     `url: str`, `published_at: datetime`
   - `BinanceRSSPoller`:
     - `RSS_URL = "https://www.binance.com/en/support/announcement/rss"`
     - `async poll() -> list[RawAnnouncement]`
     - Usa `feedparser` (aggiungere a requirements)
     - Timeout 15s; se errore → lancia `PollerError` (subclasse di `CollectorError`)
2. `app/scalping/opportunity/pollers/whale_alert.py`:
   - `WhaleAlertPoller`:
     - `BASE_URL = "https://api.whale-alert.io/v1/transactions"`
     - `async poll(min_value_usd: float = 1_000_000) -> list[RawAnnouncement]`
     - Richiede `WHALE_ALERT_API_KEY` (opzionale: se vuoto → lista vuota con log)
   - Aggiungere `WHALE_ALERT_API_KEY: str = ""` a `ScalpingSettings`

**Test TDD da scrivere prima (`tests/scalping/test_opportunity_pollers.py`):**
- `test_rss_poller_parses_feed` — mock HTTP con RSS XML valido → lista di `RawAnnouncement`
- `test_rss_poller_network_error` — lancia `PollerError`
- `test_rss_poller_empty_feed` — feed senza entry → lista vuota (no crash)
- `test_whale_no_api_key_returns_empty` — `WHALE_ALERT_API_KEY=""` → lista vuota
- `test_whale_poller_returns_announcements` — mock HTTP → lista con almeno 1 elemento

---

### TASK-819 — AI `OpportunityClassifier` (Claude API)
**Status:** To Do
**Priorità:** Media
**Dipende da:** TASK-818, TASK-801
**Dettagli:**
Usare Claude (via Anthropic API diretta) per classificare le news.
Riusa il pattern dell'AI Evaluator esistente per le chiamate API.

**Piano di Attuazione:**
1. `app/scalping/opportunity/classifier.py`:
   - `CLASSIFIER_SYSTEM_PROMPT` — dal piano (classifica in category, urgency, scalping_opportunity, ecc.)
   - `OpportunityClassifier`:
     - `async classify(announcement: RawAnnouncement) -> Opportunity`:
       - Chiama `POST https://api.anthropic.com/v1/messages` con il testo dell'annuncio
       - Model: `claude-sonnet-4-20250514`
       - Parsa risposta JSON; se parsing fallisce → `category=IRRELEVANT, urgency=LOW`
         (graceful degradation, non crash)
       - Calcola `content_hash = hashlib.sha256(announcement.title + announcement.url).hexdigest()[:16]`
   - `OpportunityClassifierError(Exception)`

**Test TDD da scrivere prima (`tests/scalping/test_opportunity_classifier.py`):**
- `test_classify_new_listing` — mock Anthropic con risposta JSON `{category: "new_listing", urgency: "high"}` →
  `Opportunity` con campi corretti
- `test_classify_invalid_json_fallback` — risposta non-JSON → `category=IRRELEVANT` (no crash)
- `test_content_hash_computed` — `content_hash` non è None e ha lunghezza 16
- `test_classifier_api_error_fallback` — HTTP 500 → `category=IRRELEVANT` (no crash)
- `test_classify_uses_correct_model` — verifica che il body della richiesta contenga
  `"model": "claude-sonnet-4-20250514"`

---

### TASK-820 — `OpportunityRouter`, `Deduplicator` e `OpportunityScheduler`
**Status:** To Do
**Priorità:** Media
**Dipende da:** TASK-818, TASK-819, TASK-804
**Dettagli:**
Orchestrare il pipeline opportunità: poll → deduplica → classifica → smista → salva.

**Piano di Attuazione:**
1. `app/scalping/opportunity/deduplicator.py`:
   - `Deduplicator`:
     - Set in memoria `_seen_hashes: set[str]` caricato da Supabase all'avvio
     - `is_duplicate(hash: str) -> bool`
     - `mark_seen(hash: str) -> None`
2. `app/scalping/opportunity/opportunity_router.py`:
   - `OpportunityRouter`:
     - `route(opportunity: Opportunity) -> None`:
       - Se `urgency == HIGH` e `scalping_opportunity == True` → broadcast WS immediato
       - Salva sempre su Supabase `opportunities`
     - `get_recent(limit: int = 20, urgency_filter: str | None = None) -> list[Opportunity]`
3. `app/scalping/opportunity/opportunity_scheduler.py`:
   - `OpportunityScheduler`:
     - Job ogni 5 minuti: chiama tutti i poller → filtra duplicati → classifica → route
     - Istanza APScheduler separata con job id `scalping_opp_*`

**Test TDD da scrivere prima (`tests/scalping/test_opportunity_pipeline.py`):**
- `test_deduplicator_blocks_duplicate` — stesso hash due volte → secondo `is_duplicate == True`
- `test_deduplicator_allows_new` — hash mai visto → `is_duplicate == False`
- `test_router_broadcasts_high_urgency` — mock broadcaster → `urgency=HIGH` + `scalping_opportunity=True`
  → broadcast chiamato
- `test_router_saves_to_supabase` — mock Supabase → insert chiamato per ogni opportunity
- `test_scheduler_jobs_have_prefix` — tutti i job id iniziano con `scalping_opp_`
- `test_full_pipeline_deduplication` — stessa news inviata due volte → insert su Supabase chiamato 1 sola volta

---

### TASK-821 — `ContextBuilder` v2.0 (Intel Snapshots per Supervisor)
**Status:** To Do
**Priorità:** Alta
**Dipende da:** TASK-810, TASK-804, TASK-809
**Dettagli:**
Arricchire il contesto inviato al Supervisor AI con i dati di intelligence reali.

**Piano di Attuazione:**
1. `app/scalping/supervisor/context_builder.py`:
   - `SupervisorContext(BaseModel)`:
     - Tutti i campi del piano + nuovi:
     - `signal_score: float | None` — score corrente
     - `funding_rate: float | None`
     - `funding_bias: str | None`
     - `cvd_trend: str | None`
     - `long_pct: float | None`
     - `fear_greed_value: int | None`
     - `recent_opportunities: list[str]` — titoli delle ultime 3 opportunità HIGH
   - `ContextBuilder`:
     - `async build(session_id: str) -> SupervisorContext`:
       - Query Supabase per `scalping_trades` della sessione
       - Legge `intelligence_scheduler.get_current_context()`
       - Assembla `SupervisorContext`

**Test TDD da scrivere prima (`tests/scalping/test_context_builder.py`):**
- `test_build_includes_intelligence_data` — mock scheduler con context → `SupervisorContext`
  ha `signal_score != None` e `funding_rate != None`
- `test_build_calculates_win_rate` — 3 vincite, 2 perdite → `win_rate == 0.6`
- `test_build_handles_no_trades` — sessione senza trade → `win_rate == 0.0`, no crash
- `test_build_includes_recent_opportunities` — 3 opportunity HIGH nel DB → lista di 3 titoli

---

### TASK-822 — `ClaudeClient` Supervisor (Real-data Reasoning)
**Status:** To Do
**Priorità:** Alta
**Dipende da:** TASK-821
**Dettagli:**
Il Supervisor AI usa Claude con il system prompt v2.0 che include la gerarchia dei segnali
di intelligence. Il reasoning deve citare i dati reali (funding, CVD, ecc.).

**Piano di Attuazione:**
1. `app/scalping/supervisor/claude_client.py`:
   - `SUPERVISOR_SYSTEM_PROMPT` — v2.0 dal piano (include gerarchia segnali e campo `primary_signal`)
   - `SupervisorClaudeClient`:
     - `async analyze(context: SupervisorContext) -> SupervisorDecision`
     - Model: `claude-sonnet-4-20250514`, `max_tokens=1000`, `temperature=0.1`
     - Chiama `POST https://api.anthropic.com/v1/messages`
     - Parsa JSON → `SupervisorDecision`
     - Se parsing fallisce → `SupervisorDecision(action=NO_ACTION, reason="Parse error", confidence=0.0, ...)`
     - Salva decisione su `supervisor_decisions` Supabase
2. `app/scalping/supervisor/decision_parser.py`:
   - `parse_supervisor_decision(raw_json: str) -> SupervisorDecision`
   - Strip markdown fence `json` se presente
   - Validazione con Pydantic; campo `action` deve essere in enum validi

**Test TDD da scrivere prima (`tests/scalping/test_supervisor_claude.py`):**
- `test_analyze_returns_decision` — mock Anthropic con JSON valido → `SupervisorDecision`
  con campi corretti
- `test_analyze_invalid_json_fallback` — risposta non-JSON → `action=NO_ACTION` (no crash)
- `test_decision_parser_strips_markdown` — input con ` ```json ... ``` ` → parsato correttamente
- `test_decision_parser_invalid_action` — `action="INVALID"` nel JSON → `ValidationError` o fallback
- `test_supervisor_uses_intelligence_data` — verifica che il prompt costruito contenga
  i valori di `funding_rate` e `signal_score` dal `SupervisorContext`
- `test_decision_saved_to_supabase` — mock Supabase → insert chiamato su `supervisor_decisions`

---

### TASK-823 — `ParameterUpdater` e `SupervisorScheduler`
**Status:** To Do
**Priorità:** Media
**Dipende da:** TASK-822, TASK-816
**Dettagli:**
Applicare le decisioni del Supervisor AI al loop di esecuzione in modo hot (senza riavvio).

**Piano di Attuazione:**
1. `app/scalping/supervisor/parameter_updater.py`:
   - `ParameterUpdater`:
     - `async apply(decision: SupervisorDecision, engine: ScalpingEngine) -> None`:
       - `UPDATE_PARAMS`: aggiorna `strategy.params` nel `TickProcessor` via setter thread-safe
       - `CHANGE_STRATEGY`: cambia `strategy_selector.current_override` (se non None, bypassa regime)
       - `PAUSE_TRADING`: chiama `engine.pause()`
       - `RESUME_TRADING`: chiama `engine.resume()`
       - `NO_ACTION`: solo log
       - Broadcast WS evento `supervisor_decision` al frontend
2. `app/scalping/supervisor/supervisor_scheduler.py`:
   - `SupervisorScheduler`:
     - Job `scalping_supervisor_analyze` ogni `SCALPING_SUPERVISOR_INTERVAL_MIN` minuti
     - Chiama `ContextBuilder.build()` → `ClaudeClient.analyze()` → `ParameterUpdater.apply()`
     - Traccia metriche (stesso pattern di TASK-835)

**Test TDD da scrivere prima (`tests/scalping/test_parameter_updater.py`):**
- `test_update_params_applies_new_stop_loss` — decision con `new_params.stop_loss_pct=0.008` →
  dopo apply, `engine.tick_processor.strategy.params.stop_loss_pct == 0.008`
- `test_change_strategy_overrides_selector` — decision con `new_strategy=RSI_BOLLINGER` →
  prossimo tick usa RSI_BOLLINGER indipendentemente dal regime
- `test_pause_calls_engine_pause` — mock engine → `engine.pause()` chiamato
- `test_no_action_does_not_modify_engine` — `NO_ACTION` → nessun metodo del engine chiamato
- `test_apply_broadcasts_ws_event` — mock broadcaster → evento `supervisor_decision` emesso

---

### TASK-824 — Scaffolding Modulo Angular Scalping e WS Service
**Status:** To Do
**Priorità:** Alta
**Dipende da:** TASK-817
**Dettagli:**
Setup frontend del modulo scalping con lazy loading. Il modulo è completamente separato
dall'app Angular esistente — usa routing lazy per non impattare il bundle iniziale.

**Piano di Attuazione:**
1. Creare `src/app/scalping/scalping.module.ts` (NgModule con lazy loading)
2. Creare `src/app/scalping/scalping-routing.module.ts` con route `/scalping`
3. Aggiungere route lazy a `app-routing.module.ts`:
   ```typescript
   { path: 'scalping', loadChildren: () => import('./scalping/scalping.module').then(m => m.ScalpingModule) }
   ```
4. Creare tutti i modelli TypeScript in `src/app/scalping/models/`:
   - `intelligence.model.ts`: `FundingRateSnapshot`, `CVDSnapshot`, `SignalScore`, `MarketContext`
   - `opportunity.model.ts`: `Opportunity`, `OpportunityUrgency`
   - `session.model.ts`: `ScalpingSession`, `EngineState`
   - `signal.model.ts`: `Signal`, `SignalType`, `ExecutionDecision`
5. `src/app/scalping/services/scalping-ws.service.ts`:
   - `ScalpingWsService`:
     - `connect(token: string): void` — apre WS a `ws://localhost:8008/scalping/ws/scalping`
     - `disconnect(): void`
     - `candle$: Observable<CandleEvent>`, `signal$: Observable<SignalEvent>`,
       `position$: Observable<PositionEvent>`, `intelUpdate$: Observable<SignalScore>`,
       `supervisorDecision$: Observable<SupervisorDecisionEvent>`,
       `riskBlock$: Observable<RiskBlockEvent>`
     - Auto-reconnect con `retryWhen` + `delay(3000)`
   - Endpoint API: `scalping-api.service.ts` con metodi per tutti gli endpoint del router
6. Aggiungere link "Scalping" nella sidebar esistente — unica modifica a componente esistente

**Test TDD da scrivere prima (`src/app/scalping/services/scalping-ws.service.spec.ts`):**
- `test_connect_opens_websocket` — `connect()` chiama `webSocket()` con URL corretto
- `test_candle_observable_emits_on_message` — mock WS emette `{type:'candle', payload:{...}}` →
  `candle$` emette il payload
- `test_signal_observable_emits_on_message` — analogo per `signal`
- `test_reconnect_on_error` — mock WS che lancia error → subscribe riceve evento dopo reconnect
- `test_disconnect_closes_connection` — `disconnect()` → WS chiuso

**Test Angular app esistente (`src/app/app-routing.module.spec.ts`):**
- `test_scalping_route_is_lazy` — la route `/scalping` usa `loadChildren` (non `component`)
- `test_existing_routes_unchanged` — `/dashboard`, `/strategies`, `/active`, `/logs`
  esistono ancora e puntano ai componenti corretti

---

### TASK-825 — Componenti `MarketIntelPanel` e `SignalScorecard`
**Status:** To Do
**Priorità:** Alta
**Dipende da:** TASK-824
**Dettagli:**
Visualizzare i dati di intelligence in tempo reale. Sono i componenti più informativi del dashboard scalping.

**Piano di Attuazione:**
1. `src/app/scalping/components/market-intel-panel/`:
   - Input: `@Input() context: MarketContext | null`
   - Mostra: Funding Rate con colore (rosso se bearish, verde se bullish),
     OI value, Long/Short gauge (progress bar da 0 a 100, soglie colorate),
     CVD trend con icona (↑ rising, ↓ falling, → neutral), Fear & Greed meter
   - Aggiornamento: subscribe a `ScalpingWsService.intelUpdate$`
   - Loading skeleton quando `context == null`
2. `src/app/scalping/components/signal-scorecard/`:
   - Input: `@Input() score: SignalScore | null`
   - Visualizza score totale (grande, centrato), colore: `--color-buy` se > 20,
     `--color-sell` se < −20, `--text-secondary` se neutro
   - Breakdown con barra orizzontale per ogni componente (funding, cvd, ls, fg)
   - Badge `BULLISH` / `BEARISH` / `NEUTRAL` e `TRADEABLE` / `WAITING`
   - Animazione flash quando score cambia significativamente (> 10 punti)

**Test TDD da scrivere prima:**
- `market-intel-panel.component.spec.ts`:
  - `test_shows_loading_skeleton_when_context_null` — `context=null` → `.skeleton` visibile
  - `test_shows_funding_rate_value` — `context.fundingRate.rate=0.0015` → testo "0.15%" visibile
  - `test_funding_rate_color_bearish` — `rate > 0` → elemento ha classe `bearish`
  - `test_funding_rate_color_bullish` — `rate < 0` → classe `bullish`
  - `test_cvd_trend_icon_rising` — `cvdTrend='rising'` → "↑" presente nel DOM
- `signal-scorecard.component.spec.ts`:
  - `test_shows_total_score` — `score.total=55` → "55" visibile
  - `test_buy_color_when_bullish` — `total > 20` → elemento ha `color: var(--color-buy)`
  - `test_sell_color_when_bearish` — `total < -20` → `var(--color-sell)`
  - `test_tradeable_badge` — `tradeable=true` → badge "TRADEABLE" visibile
  - `test_waiting_badge` — `tradeable=false` → badge "WAITING" visibile
  - `test_breakdown_bars_rendered` — per ogni chiave in `score.breakdown` → una barra presente

---

### TASK-826 — `OpportunityFeedComponent` con Urgency Badges
**Status:** To Do
**Priorità:** Media
**Dipende da:** TASK-824, TASK-820
**Dettagli:**
Feed real-time opportunità classificate dall'AI con badge colorati per urgenza.

**Piano di Attuazione:**
1. `src/app/scalping/components/opportunity-feed/`:
   - Subscribe a `ScalpingWsService` per nuove opportunità (evento `opportunity_new`)
   - HTTP initial load: `GET /scalping/intelligence/opportunities`
   - Lista scrollabile con max 50 item (CDK VirtualScroll)
   - Per ogni item: badge urgency (🔴 HIGH / 🟡 MEDIUM / 🔵 LOW), source icon,
     titolo, action consigliata, simbolo se presente, timestamp relativo
   - Bottoni inline: [Monitora] (aggiunge a watchlist) / [Ignora] (chiama `POST /opportunities/{id}/ignore`)
   - Filtro per urgency (dropdown: ALL / HIGH / MEDIUM / LOW)
   - Nuovi item → animazione slide-in dall'alto

**Test TDD da scrivere prima (`opportunity-feed.component.spec.ts`):**
- `test_renders_empty_state` — nessuna opportunity → testo "Nessuna opportunità rilevata"
- `test_renders_opportunity_list` — 3 opportunity mock → 3 card nel DOM
- `test_high_urgency_badge_color` — urgency=HIGH → badge con classe `urgency-high`
- `test_filter_shows_only_high` — filtro HIGH selezionato → solo item HIGH visibili
- `test_ignore_calls_api` — click [Ignora] → `OpportunityApiService.ignore(id)` chiamato
- `test_new_ws_event_prepends_item` — WS emette nuova opportunity → appare in cima alla lista

---

### TASK-827 — Live Chart con Signal Overlay
**Status:** To Do
**Priorità:** Alta
**Dipende da:** TASK-824
**Dettagli:**
Grafico candlestick in tempo reale con overlay dei segnali di trading. Usa `lightweight-charts`
già in uso nell'app (no nuove dipendenze da installare).

**Piano di Attuazione:**
1. `src/app/scalping/components/live-chart/`:
   - Crea chart in `ngAfterViewInit` con tema dark (colori da `--bg-surface`, `--color-buy`, ecc.)
   - Subscribe a `ScalpingWsService.candle$` → `candleSeries.update()`
   - Subscribe a `ScalpingWsService.signal$` → aggiunge marker:
     - BUY: triangolo verde ▲ sotto la candela
     - SELL/CLOSE: triangolo rosso ▼ sopra la candela
     - SIGNAL_BLOCKED: marcatore grigio ○ (segnale bloccato, per trasparenza)
   - Header: pair, timeframe, regime badge, strategia attiva
   - `ngOnDestroy`: rimuove chart e cancella subscription

**Test TDD da scrivere prima (`live-chart.component.spec.ts`):**
- `test_chart_created_on_init` — spy su `createChart` → chiamato in `ngAfterViewInit`
- `test_candle_update_called_on_ws_event` — mock WS emette candle → `candleSeries.update` chiamato
- `test_buy_marker_added_on_buy_signal` — WS emette BUY signal → `setMarkers` chiamato con
  marker di tipo triangolo
- `test_chart_destroyed_on_destroy` — `ngOnDestroy` → `chart.remove()` chiamato
- `test_regime_badge_visible` — `currentRegime='TRENDING_UP'` → badge con testo "TRENDING UP" nel DOM

---

### TASK-828 — `SessionControlsComponent` e `PerformancePanelComponent`
**Status:** To Do
**Priorità:** Media
**Dipende da:** TASK-824
**Dettagli:**
Pannello di controllo sessione (START/PAUSE/STOP) e metriche performance real-time.

**Piano di Attuazione:**
1. `src/app/scalping/components/session-controls/`:
   - Selector modalità: PAPER (default) / LIVE (richiede conferma modal)
   - Selector pair: BTCUSDT, ETHUSDT, BNBUSDT
   - Stato sessione: `EngineState` da `GET /scalping/session/status` + WS `status_changed`
   - Bottoni: START (verde, solo se IDLE/STOPPED), PAUSE (giallo, solo se RUNNING),
     RESUME (verde, solo se PAUSED), STOP (rosso, con confirm modal, solo se RUNNING/PAUSED)
   - Timer sessione: tempo trascorso dall'avvio (formato `HH:mm:ss`)
2. `src/app/scalping/components/performance-panel/`:
   - KPI: Total PnL (EUR + %), Win Rate, # Trade oggi, Consecutive Losses
   - Aggiornamento da WS `position_closed` → ricalcola KPI localmente
   - Indicatore visivo: drawdown gauge (barra rossa che cresce verso il limite daily loss)

**Test TDD da scrivere prima:**
- `session-controls.component.spec.ts`:
  - `test_start_button_visible_when_idle` — `state=IDLE` → bottone START visibile e abilitato
  - `test_pause_button_visible_when_running` — `state=RUNNING` → bottone PAUSE visibile
  - `test_stop_shows_confirm_modal` — click STOP → modal di conferma appare prima della chiamata API
  - `test_live_mode_shows_warning` — selezionare LIVE → warning "Real funds at risk" visibile
  - `test_start_calls_api` — click START → `ScalpingApiService.startSession()` chiamato
- `performance-panel.component.spec.ts`:
  - `test_shows_zero_state` — nessun trade → PnL=€0.00, WinRate=0%, Trades=0
  - `test_pnl_updates_on_trade_closed` — WS emette `position_closed` con pnl=5.0 → PnL aggiornato
  - `test_win_rate_calculation` — 3 win + 2 loss → "60.0%" visibile
  - `test_drawdown_gauge_fills_on_loss` — daily pnl = −1.5% su soglia 3% → gauge al 50%

---

### TASK-829 — Backtest Engine con supporto Intelligence Layer
**Status:** To Do
**Priorità:** Alta
**Dipende da:** TASK-811, TASK-812, TASK-809
**Dettagli:**
Validare su dati storici che il Signal Intelligence layer migliori i risultati rispetto alle
sole strategie tecniche. Usa il `BacktestEngine` esistente come base.

**Piano di Attuazione:**
1. `app/scalping/backtest/historical_loader.py`:
   - `HistoricalLoader`:
     - `async load_ohlcv(symbol: str, interval: str, days: int) -> list[Candle]`
     - Usa `market_data.fetch_ohlcv()` esistente (no duplicazione)
     - `async load_funding_rate_history(symbol: str, days: int) -> list[FundingRateSnapshot]`
       (endpoint: `GET /fapi/v1/fundingRate?limit=1000`)
2. `app/scalping/backtest/backtest_engine.py` (nuovo, non modifica `app/core/backtester.py`):
   - `ScalpingBacktestEngine`:
     - `run(candles: list[Candle], funding_history: list[FundingRateSnapshot],
           strategy_type: StrategyType, params: StrategyParams,
           use_intelligence: bool = True) -> BacktestReport`
     - In modalità `use_intelligence=True`: per ogni candela, calcola `SignalScore` dal
       `FundingRateSnapshot` corrispondente (approssimazione temporale) → applica `SignalAggregator`
     - In modalità `use_intelligence=False`: esegue solo la strategia tecnica
   - `BacktestReport(BaseModel)`: `pnl_pct`, `win_rate`, `sharpe`, `max_drawdown_pct`,
     `num_trades`, `equity_curve: list[float]`, `signals_blocked_by_intel: int`,
     `use_intelligence: bool`
3. `app/scalping/backtest/performance_calculator.py`:
   - Riusa formule di `app/core/backtester.py` senza duplicare (import diretto)
4. Endpoint: `POST /scalping/backtest/run` nel router

**Test TDD da scrivere prima (`tests/scalping/test_backtest_engine.py`):**
- `test_backtest_without_intel_runs` — `use_intelligence=False` su 100 candele → report senza crash
- `test_backtest_with_intel_blocks_some_trades` — `use_intelligence=True` →
  `signals_blocked_by_intel > 0` (almeno qualche segnale bloccato da intelligence)
- `test_backtest_equity_curve_length` — `len(equity_curve) == len(candles)`
- `test_intel_reduces_trade_count` — `use_intelligence=True` ha `num_trades <= use_intelligence=False`
  (per stesso dataset, l'intelligence può solo ridurre i trade)
- `test_historical_loader_uses_existing_market_data` — verifica che `load_ohlcv` chiami
  `market_data.fetch_ohlcv` (non reimplementi da zero — non-regression)

---

### TASK-830 — Analisi Comparativa Backtest e Report
**Status:** To Do
**Priorità:** Media
**Dipende da:** TASK-829
**Dettagli:**
Generare report comparativi automatici per validare il valore aggiunto del Signal Intelligence layer.

**Piano di Attuazione:**
1. `app/scalping/backtest/report_generator.py`:
   - `ComparisonReport(BaseModel)`:
     - `strategy_only: BacktestReport` — backtest senza intelligence
     - `with_intelligence: BacktestReport` — backtest con intelligence
     - `delta_pnl_pct: float`, `delta_win_rate: float`, `delta_max_drawdown: float`
     - `intel_value_positive: bool` — True se intelligence migliora il PnL
     - `signals_filtered_pct: float` — percentuale di segnali bloccati dall'intelligence
   - `generate_comparison(symbol: str, days: int, strategy: StrategyType,
                          params: StrategyParams) -> ComparisonReport`
2. Endpoint: `GET /scalping/backtest/{id}/result` → `ComparisonReport`
3. Frontend (componente semplice): tabella con due colonne "Solo Strategia" vs "Con Intelligence",
   riga per ogni metrica, delta colorato (verde se miglioramento, rosso se peggioramento)

**Test TDD da scrivere prima (`tests/scalping/test_comparison_report.py`):**
- `test_delta_pnl_calculated` — `strategy_only.pnl=5.0, with_intel.pnl=7.0` → `delta_pnl_pct=2.0`
- `test_intel_value_positive` — intelligence migliora PnL → `intel_value_positive=True`
- `test_signals_filtered_pct` — 10 trade senza intel, 7 con intel → `signals_filtered_pct ≈ 30%`

---

### TASK-831 — E2E Tests Playwright — Workflow Scalping
**Status:** To Do
**Priorità:** Alta
**Dipende da:** Tutti i task frontend (TASK-824–828), TASK-817
**Dettagli:**
Testare l'intero flusso dalla dashboard scalping al database, inclusa la non-regression
del workflow esistente (strategie, dashboard, logs).

**Piano di Attuazione:**
1. `e2e/scalping-session.spec.ts`:
   - Setup: backend running in PAPER mode, frontend running
   - `test_navigate_to_scalping_dashboard` — `GET /scalping` → pagina caricata, SessionControls visibili
   - `test_start_paper_session` — click START → stato cambia in RUNNING, timer inizia
   - `test_pause_resume_session` — PAUSE → PAUSED, RESUME → RUNNING
   - `test_stop_session_requires_confirm` — STOP → modal appare → Annulla → stato RUNNING
   - `test_stop_session_confirmed` — STOP → Conferma → stato STOPPED
2. `e2e/scalping-intel.spec.ts`:
   - `test_market_intel_panel_loads` — panel visibile con dati o loading skeleton
   - `test_signal_scorecard_updates` — attendere aggiornamento WS → scorecard cambia valore
3. `e2e/scalping-regression.spec.ts` — **CRITICO: non-regression**:
   - `test_existing_dashboard_unaffected` — `GET /dashboard` → carica senza errori
   - `test_existing_strategies_unaffected` — `GET /strategies` → lista strategie visibile
   - `test_existing_logs_unaffected` — `GET /logs` → log visibili con filtri funzionanti
   - `test_existing_active_trade_unaffected` — `GET /active-trade` → pagina carica

---

### TASK-837 — API Keys & Secrets Validation
**Status:** To Do
**Priorità:** Alta
**Dipende da:** TASK-800 (config)
**Dettagli:**
Script di pre-flight check che verifica presenza e validità delle API key prima del deploy.
Non è parte del modulo runtime — è un tool di deployment.

**Piano di Attuazione:**
1. `app/scalping/scripts/validate_secrets.py`:
   - Check `BINANCE_API_KEY` e `BINANCE_API_SECRET`:
     - Chiama `GET /api/v3/account` (Testnet) e verifica risposta `200`
     - Se fallisce → stampa istruzioni per generare la key su testnet.binance.vision
   - Check `ANTHROPIC_API_KEY`:
     - Chiama `POST /v1/messages` con `max_tokens=1` e verifica risposta `200` (no `401`)
   - Check `CRYPTOPANIC_TOKEN` (opzionale):
     - Se configurato, verifica `GET /api/v1/posts/?auth_token=...&public=true` → `200`
   - Check `WHALE_ALERT_API_KEY` (opzionale): analogo
   - Output: tabella con stato per ogni key (✅ OK / ⚠️ Missing / ❌ Invalid)
   - Exit code `0` se tutte le required key sono valide; `1` altrimenti
2. Aggiungere step in `docker-compose.prod.yml` o GitHub Actions: eseguire lo script
   prima del deploy

**Test TDD da scrivere prima (`tests/scalping/test_validate_secrets.py`):**
- `test_binance_key_valid` — mock HTTP 200 → output include "✅ BINANCE"
- `test_binance_key_invalid` — mock HTTP 401 → output include "❌ BINANCE", exit code 1
- `test_anthropic_key_missing` — `ANTHROPIC_API_KEY=""` → output include "⚠️ ANTHROPIC"
- `test_optional_keys_not_required` — `CRYPTOPANIC_TOKEN=""` → script non fallisce (exit 0)

---

### TASK-832 — Code Review Finale e Deploy Paper Trading
**Status:** To Do
**Priorità:** Media
**Dipende da:** Tutti i task precedenti
**Dettagli:**
Verifica finale prima di avviare la prima sessione di paper trading reale.

**Piano di Attuazione:**
1. **Security audit:**
   - Verificare che nessuna API key sia loggata (grep `logger.*API_KEY` nel codice)
   - Verificare che `PAPER_TRADING=True` sia il default in `ScalpingSettings`
   - Verificare che `LIVE` mode richieda conferma esplicita (`SCALPING_ALLOW_LIVE_MODE: bool = False`)
   - Verificare che il SL sia sempre inviato a Binance server-side (non solo locale)
2. **Test coverage check:**
   - Eseguire `pytest tests/scalping/ --cov=app/scalping --cov-report=term-missing`
   - Verificare coverage ≥ 80% su tutti i moduli critici (engine, intelligence, supervisor)
3. **Non-regression finale:**
   - Eseguire la suite esistente completa: `pytest tests/` (escludendo `tests/scalping/`)
   - Zero nuovi failure accettabili
4. **Deploy su server di test:**
   - Avviare con `PAPER_TRADING=True`, `BINANCE_TESTNET=True`
   - Monitorare log per 30 minuti durante sessione attiva
   - Verificare: trade loggati su Supabase, intelligence aggiornata, supervisor che analizza
5. **Analisi prima sessione paper:**
   - Generare `ComparisonReport` dopo 4h di sessione
   - Verificare che `signals_blocked_by_intel > 0` (intelligence funziona)

**Checklist pre-deploy:**
- [ ] `pytest tests/scalping/` — 100% pass
- [ ] `pytest tests/` (suite esistente) — 0 regressioni
- [ ] Coverage ≥ 80% modulo scalping
- [ ] `validate_secrets.py` — exit 0
- [ ] `PAPER_TRADING=True` in `.env` server
- [ ] Nessuna API key in log
- [ ] SL/TP impostati server-side verificati manualmente su testnet

---

### TASK-838 — E2E Playwright Regression — Suite completa
**Status:** To Do
**Priorità:** Alta
**Dipende da:** TASK-831
**Dettagli:**
Consolidamento di tutti i test E2E in una suite regressione completa da eseguire prima
di ogni deploy. Estende i test esistenti (TASK-176, TASK-177, TASK-178) con il workflow scalping.

**Piano di Attuazione:**
1. `e2e/regression.spec.ts` — suite aggregata:
   - Import degli spec esistenti: `auth.spec`, `strategies.spec`, `logs.spec`
   - Import del nuovo `scalping-session.spec`
   - Configurazione Playwright `fullyParallel: false` (i test scalping sono stateful)
2. Script `package.json`: `"test:e2e:regression": "playwright test e2e/regression.spec.ts"`
3. GitHub Actions: aggiungere step che esegue `test:e2e:regression` su PR verso `main`
4. I test E2E scalping richiedono backend con `PAPER_TRADING=True` e Intelligence Scheduler attivo

**Criteri di successo:**
- Tutti i 27 test E2E esistenti passano ancora
- Almeno 5 nuovi test E2E scalping passano
- Tempo totale suite < 5 minuti

---

---

## 📋 Riepilogo Dipendenze e Ordine di Esecuzione

```
TASK-800 (Scaffolding)
  └─→ TASK-801 (Modelli)
        ├─→ TASK-802 (IndicatorProtocol)
        │     └─→ TASK-803 (VWAP + ADX)
        │           └─→ TASK-811 (RegimeDetector)
        │                 └─→ TASK-812 (SignalAggregator)
        ├─→ TASK-804 (DB Migrations)
        ├─→ TASK-805 (FundingRate)
        │     ├─→ TASK-807 (OI + LongShort)
        │     └─→ TASK-808 (FearGreed + Sentiment)
        └─→ TASK-806 (WsClient) + TASK-836 (Reconnect)
              └─→ TASK-833 (CVDCalculator)

TASK-805 + 807 + 808 + 833 (tutti i collector)
  └─→ TASK-809 (SignalScoreEngine)
        └─→ TASK-810 (IntelligenceScheduler)
              ├─→ TASK-811 (RegimeDetector) ─→ TASK-812 (SignalAggregator)
              │     └─→ TASK-814 (RiskManager)
              │           └─→ TASK-815 (OrderExecutor)
              │                 └─→ TASK-834 (TickProcessor)
              │                       └─→ TASK-816 (ScalpingEngine Loop)
              │                             └─→ TASK-817 (Router + WS Events)
              └─→ TASK-821 (ContextBuilder)
                    └─→ TASK-822 (ClaudeClient Supervisor)
                          └─→ TASK-823 (ParameterUpdater)

TASK-818 (Pollers) + TASK-819 (Classifier) + TASK-820 (Router+Dedup)
  (paralleli, dipendono solo da TASK-801 + TASK-804)

TASK-824 (Angular Scaffolding)
  ├─→ TASK-825 (Intel Panel + Scorecard)
  ├─→ TASK-826 (Opportunity Feed)
  ├─→ TASK-827 (Live Chart)
  └─→ TASK-828 (Session Controls + Performance)

TASK-811 + TASK-812 + TASK-809 ─→ TASK-829 (Backtest) ─→ TASK-830 (Report)

TASK-835 (Scheduler Health) — dopo TASK-810
TASK-837 (Secrets Validation) — dopo TASK-800

TASK-831 (E2E Scalping) — dopo tutti i frontend
TASK-832 (Code Review + Deploy) — ultimo
TASK-838 (E2E Regression) — dopo TASK-831
```

---

## ⚠️ Regole Globali di Non-Regressione

> Queste regole si applicano a **ogni** task dell'epica e devono essere verificate
> prima di ogni PR/merge.

1. **Nessuna modifica a file esistenti** tranne: `main.py` (solo `include_router`),
   `config.py` (solo aggiunta `ScalpingSettings`), `app-routing.module.ts` (solo lazy route),
   `sidebar.component.ts/html` (solo aggiunta link).

2. **Test di non-regression obbligatori per ogni PR:**
   ```bash
   pytest tests/ -k "not scalping" --tb=short   # suite esistente: 0 failure
   pytest tests/scalping/ --tb=short             # suite scalping: 100% pass
   ```

3. **Import del modulo scalping non ciclici:** nessun file in `app/scalping/` importa da
   `app/api/`, `app/core/execution_engine.py`, o altri moduli di business logic esistenti.
   Può importare solo da: `app/core/indicators.py`, `app/core/market_data.py`,
   `app/db/supabase_client.py`, `app/config.py`.

4. **APScheduler:** il modulo scalping usa **istanze separate** di `AsyncIOScheduler`
   (mai il riferimento globale di `app/scheduler/`). Verifica: `grep -r "from app.scheduler"
   app/scalping/` deve restituire vuoto.

5. **Port conflicts:** il WS server scalping usa il namespace `/scalping/ws/` per non
   collidere con il WS esistente su `/ws`.
