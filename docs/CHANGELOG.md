no sempre una divresificazion# Changelog — SynthTrade

All notable changes to this project will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.2.9] — 2026-05-20

### Added
- **8 template strategici** (era 3): aggiunti `trend_ema_fast`, `mean_reversion_rsi_aggressive`, `breakout_bb_tight`, `momentum_macd`, `scalp_short_term`
- **Nuove funzioni indicatore**: `signal_macd_crossover`, `signal_ema_dual_crossover`, `macd()` in `indicators.py`
- **Registry esteso**: tutti gli 8 template registrati in `StrategyRegistry._load_defaults()`

### Changed
- **Filtri rilassati**: tolleranza durata 80% (era 50%), fallback su 3 template invece di 1 solo
- **Nomi descrittivi**: titolo usa template_data['title'] invece di template ID tecnico
- **Prompt AI**: `request_enricher.py` aggiornato con tutti gli 8 template
- **Fix `run_pipeline.py`**: titolo ora usa `strategy.title` (es. "Trend Following EMA (BTC/USDT)") invece di `f"{strategy.template} {strategy.pair} {strategy.timeframe}"` (es. "trend_ema BTC/USDT 1h")

## [1.2.8] — 2026-05-19

### Fixed
- **Dashboard falso saldo 1500€**: Risolto bug critico per cui la dashboard mostrava sempre 1500 EUR fittizi quando il fetch del saldo Binance era lento o restituiva 0. La causa era doppia:
  1. **Performance**: `get_total_balance_eur()` usava `fetch_ticker()` individuale per ciascuno dei 433 asset → 240 secondi, facendo scattare il timeout dashboard (8s). Ottimizzato con `fetch_tickers()` batch che recupera tutti i prezzi in una singola chiamata → 4.7 secondi.
  2. **Fallback hardcoded**: Rimosso il valore fittizio 1500.0 EUR che veniva iniettato quando saldo 0 o timeout. Ora mostra il saldo reale (anche se 0) con log warning.

## [1.2.4] — 2026-05-14

### Fixed
- **Binance Balance Conversion**: Risolto il bug nel calcolo del saldo totale in EUR su Testnet. Ora il sistema gestisce correttamente la coppia inversa `EUR/USDT` e converte accuratamente il saldo USDT in EUR per la dashboard.
- **Monitor API**: Aggiunto il campo `total_pnl_eur` alla risposta dell'API di monitoraggio, permettendo al frontend di mostrare il profitto reale della strategia attiva.
- **Frontend Error Handling**: Implementata la gestione degli errori durante l'attivazione della strategia nel frontend, con notifiche alert per l'utente in caso di fallimento (es. fondi insufficienti).

## [1.2.3] — 2026-05-14

### Added
- **Execution Phase A**: Completata l'attivazione operativa delle strategie.
- **CapitalAllocator**: Implementata logica di calcolo quote basata sul budget e allocazione percentuale.
- **Strategy Activation**: L'endpoint `/activate` ora esegue ordini MARKET reali (su Testnet), inizializza il capitale e trasmette eventi via WebSocket.
- **Strategy Stopping**: L'endpoint `/stop` ora chiude tutte le posizioni aperte, aggiorna lo stato a STOPPED e notifica il frontend.
- **Real-time Updates**: Implementato il broadcasting WebSocket per `trade_opened`, `trade_closed`, `strategy_stopped` e `strategy_pnl_updated`.
- **Live P&L Tracking**: Aggiunto endpoint `/active/pnl` e monitor job per il calcolo e la notifica in tempo reale delle performance delle strategie attive.
- **Advanced Trade Join**: Endpoint `/trades/active` che restituisce i trade aperti con i dettagli completi della strategia associata via resource embedding di Supabase.
- **Holdings Tracking**: Endpoint `/exchange/holdings` per monitorare i saldi reali dell'exchange.
- **ExecutionEngine**: Architettura singleton integrata nel ciclo di vita dell'applicazione con supporto al broadcasting real-time.

### Fixed
- **Insufficient Funds**: Gestione errore 422 durante l'attivazione se il saldo USDT su Binance è inferiore al budget richiesto.
- **API Robustness**: Risolti bug di importazione e regressioni negli endpoint delle strategie.
- **Frontend Type Safety**: Aggiornati i modelli WebSocket per supportare i nuovi payload operativi.

## [1.2.1] — 2026-05-13

### Changed
- **Ranker**: Soglie più realistiche per crypto — min_trades=15 (era 8), max_drawdown=40% (era 22%), min_sharpe=0.0 (era 0.3), min_pnl=0% (era 2%)
- **Generator**: lookback=60gg (era 180), pairs default BTC/ETH/SOL/BNB (era solo BTC), timeframes 1h/4h (rimosso 15m)
- QUALITY_EMPTY_MESSAGE aggiornato con nuove soglie

### Fixed
- **Profitti irrealistici**: RSI 4h con 6 trades e Sharpe 27+ non passa più i filtri (min_trades=15)
- **Diagnosi completa**: Analisi su 8 asset (BTC, ETH, SOL, BNB, ADA, DOT, LINK, AVAX) con 180gg ha confermato che solo RSI 1h su altcoin è profittevole
- Test pipeline: 5 strategie generate con P&L medio +16.78%, drawdown 11.1%, trades 16 — realistico per crypto

---

## [0.9.0] — 2026-05-06

### Added
- **Backend**: Generatore di strategie potenziato con supporto a varianti reali (parametri, timeframe).
- **Backend**: Aggiunto calcolo dinamico `ai_score` per le strategie generate.
- **Frontend**: Nuova interfaccia "Rich Card" per i risultati della generazione.
- **Frontend**: Visualizzazione descrizioni, parametri e punteggi AI nelle card delle strategie.

### Fixed
- **Backend**: Corretto bug nell'endpoint `POST /strategies` per includere il campo `description`.
- **Frontend**: Risolti errori di console nell'approvazione delle strategie grazie a una migliore gestione dei tipi e degli ID.
- **Backend**: Risolto problema di duplicati visivi nella generazione strategie tramite shuffling e limiti di varianti.

---

## [0.7.0] — 2026-05-06

## [0.6.1] — 2026-05-06

### Added
- `app/execution/exchange.py`: Implementato `BinanceExchangeAdapter` con CCXT e `ExchangeProtocol`.
- `app/execution/quantity_calculator.py`: Calcolatore quantità con validazione `stepSize` e `minNotional`.
- `app/api/exchange.py`: Endpoint `GET /api/exchange/status`.
- `app/api/pipeline.py`: Endpoint `POST /api/pipeline/generate` e `GET /api/pipeline/generate/:id/status`.
- `app/ai/request_enricher.py`: Integrazione AI per estrazione simboli e template da testo libero.
- `app/execution/schemas.py`: Aggiunto modello `StrategyRequest`.

### Changed
- `app/core/strategy_generator.py`: Aggiornato per supportare `StrategyRequest` e filtri dinamici.

---

## [0.5.9] — 2026-05-05

### Added
- `tests/integration/test_ai_integration.py`: 5 scenari (happy path, fallback, cache hit, JSON malformato, all models down)
- `tests/integration/test_pipeline_ai.py`: 4 test pipeline con AI (evaluate_all, demote, errori non bloccanti, skip)

---

## [0.5.8] — 2026-05-05

### Added
- `core/run_pipeline.py`: aggiornato ad `async`, passo AI Evaluator su top-N strategie, DEMOTE → REJECTED
- `build_evaluator()` factory function

---

## [0.5.7] — 2026-05-05

### Added
- `api/eval.py`: `GET /api/strategies/:id/eval` (cache o 202), `POST /api/strategies/:id/eval/refresh` (BackgroundTasks) — 4 test

---

## [0.5.6] — 2026-05-05

### Added
- `ai/evaluator.py`: `evaluate_strategy()` (context+prompt+model+parse+cache), `evaluate_all()` con `asyncio.Semaphore` — 7 test

---

## [0.5.5] — 2026-05-05

### Added
- `ai/cache.py`: `EvalCache` con TTL, `get_cached_eval()`, `save_eval()` upsert Supabase — 4 test

---

## [0.5.4] — 2026-05-05

### Added
- `ai/eval_parser.py`: `parse_eval_result()`, estrazione JSON da markdown, clamp score, `EvalParseError` — 8 test

---

## [0.5.3] — 2026-05-05

### Added
- `ai/model_client.py`: cascade OpenRouter, retry backoff esponenziale 429/503, `ModelTimeoutError`, `AllModelsUnavailableError` — 7 test

---

## [0.5.2] — 2026-05-05

### Added
- `ai/prompt_builder.py`: `build_prompt()` con metriche e istruzioni JSON, `build_system_prompt()`, truncate — 6 test

---

## [0.5.1] — 2026-05-05

### Added
- `ai/context_builder.py`: `build_ohlcv_summary()`, `detect_market_regime()` (trending/volatile/ranging), `build_market_context()` — 7 test

---

## [0.5.0] — 2026-05-05

### Added
- `ai/schemas.py`: `OhlcvSummary`, `MarketContext`, `StrategyContext`, `EvalPromptInput`, `EvalResult`, `ModelResponse`
- `config.py`: `AI_API_KEY`, `AI_API_BASE_URL`, `AI_CASCADE_MODELS`, `AI_FALLBACK_MODEL`, `AI_MAX_TOKENS`, `AI_TEMPERATURE`, `AI_TIMEOUT_SECONDS`, `AI_MAX_RETRIES`, `AI_BACKOFF_BASE`, `AI_EVAL_CACHE_TTL_MINUTES`, `PIPELINE_AI_EVAL_TOP_N`, `MAX_CONCURRENT_EVALS`

---

## [0.4.6] — 2026-05-05

### Added
- `tests/integration/test_execution_integration.py`: 4 scenari (pipeline completa, stop loss, risk reject, drawdown)
- `api/trades.py`: `GET /api/trades` (con filtro status), `GET /api/trades/open` — 5 test
- Registrato `trades.router` in `main.py`

---

## [0.4.5] — 2026-05-05

### Added
- `scheduler/jobs.py`: `run_pipeline_job`, `monitor_positions_job`, `heartbeat_job` con `AsyncIOScheduler` — 4 test
- `GET /api/scheduler/status`: lista job attivi e stato scheduler
- Scheduler registrato nel lifespan di `main.py`

---

## [0.4.4] — 2026-05-05

### Added
- `execution/execution_engine.py`: `process_signal`, `check_exit_conditions`, `close_position_if_needed`, gestione eccezioni exchange — 11 test

---

## [0.4.3] — 2026-05-05

### Added
- `execution/signal_resolver.py`: `SignalResolverProtocol` + `DefaultSignalResolver` (threshold filter, best-per-symbol, open position filter) — 5 test

---

## [0.4.2] — 2026-05-05

### Added
- `execution/order_tracker.py`: `open_position`, `close_position`, `get_open_positions`, `update_unrealized_pnl` — 7 test

---

## [0.4.1] — 2026-05-05

### Added
- `execution/risk_manager.py`: `RiskConfig` dataclass, `calculate_position_size`, `check_max_positions`, `check_drawdown`, `calculate_stop_loss_price`, `calculate_take_profit_price`, `validate_signal` — 13 test

---

## [0.4.0] — 2026-05-05

### Added
- `execution/schemas.py`: `Signal`, `OrderRequest`, `OrderResult`, `RiskCheckResult`, `PositionSnapshot`
- `config.py`: `MAX_CONCURRENT_POSITIONS`, `MAX_EXPOSURE_PER_SYMBOL_PCT`, `MAX_DRAWDOWN_PCT`, `DEFAULT_POSITION_SIZE_PCT`, `DEFAULT_STOP_LOSS_PCT`, `DEFAULT_TAKE_PROFIT_PCT`, `SCHEDULER_PIPELINE_INTERVAL_MIN`

---

## [0.3.8] — 2025-01-17

### Added
- `pages/login/login.page.ts`: ReactiveForm, spinner, error 401, redirect `/dashboard` — 7 test
- `pages/dashboard/dashboard.page.ts`: 4 StatCard, WS `stats_update`, skeleton loading — 4 test
- `pages/strategies/strategies.page.ts`: lista, filtro tab ALL/ACTIVE/PENDING, approve, confirm+reject, empty state — 5 test
- `pages/active-trade/active-trade.page.ts`: WS `price_update`, P&L classi positive/negative, empty state — 5 test
- `pages/logs/logs.page.ts`: filtro level, paginazione offset 50, WS `new_log` prepend — 5 test

---

## [0.3.7] — 2025-01-17

### Added
- `app.routes.ts`: lazy loading con `loadComponent`, `AppShellComponent` come layout wrapper, `authGuard`/`noAuthGuard`, redirect `**` → `dashboard` — 6 test
- Placeholder page components per tutte le 5 route

---

## [0.3.6] — 2025-01-17

### Added
- `layout/sidebar/sidebar.component.ts`: 4 nav items, toggle collapsed con `signal()`, classe `sidebar--collapsed` — 4 test
- `layout/topbar/topbar.component.ts`: username da `AuthService.currentUser$`, bottone logout — 2 test
- `layout/app-shell/app-shell.component.ts`: shell flex Sidebar + Topbar + `<router-outlet>`

---

## [0.3.5] — 2025-01-17

### Added
- `shared/components/stat-card/`: label, value, delta opzionale, skeleton loading — 4 test
- `shared/components/badge-status/`: classi CSS `badge--active/pending/rejected` via `computed()` — 6 test
- `shared/components/price-ticker/`: flash-up/flash-down su cambio prezzo, rimozione classe su `animationend` — 4 test
- `shared/components/confirm-dialog/`: output `confirmed`/`cancelled`, listener `Escape` via `@HostListener` — 5 test
- `shared/components/empty-state/`: componente semplice
- `shared/pipes/relative-time.pipe.ts`: `pure: false`, formatta in s/m/h/d ago — 5 test
- `shared/pipes/format-number.pipe.ts`: suffissi K/M — 5 test
- `shared/pipes/signed-number.pipe.ts`: prefisso `+` per positivi — 4 test

---

## [0.2.4] — 2025-01-16

### Added
- `api/ws.py`: WebSocket /ws con auth via query param, ping iniziale, broadcast per tipo (price, engine_status)
- `ConnectionManager`: connect/disconnect/broadcast
- `tests/integration/test_ws.py`: 6 test (auth, ping, broadcast, manager unit)

---

## [0.2.3] — 2025-01-16

### Added
- `api/logs.py`: GET /logs (paginato, filtri action/strategy_id) + GET /logs/export (CSV)
- `tests/integration/test_api_logs.py`: 12 test

---

## [0.2.2] — 2025-01-16

### Added
- `api/dashboard.py`: GET /dashboard (balance, pnl_today, active_strategy, engine_status)
- `api/dashboard.py`: GET /dashboard/equity-history (lista ts+value ordinata)
- `tests/integration/test_api_dashboard.py`: 10 test

### Fixed
- `build_strategy_id` ora usa `hashlib.md5` invece di `hash()` — ID stabili indipendentemente dal seed Python

---

## [0.2.1] — 2025-01-16

### Added
- `api/strategies.py`: GET list/detail, POST approve/reject con mock Supabase
- `tests/integration/test_api_strategies.py`: 12 test (list, filter, detail, approve, reject, 404, 409, auth)

---

## [0.2.0] — 2025-01-16

### Added
- `app/core/auth_utils.py`: `create_access_token`, `verify_token` via python-jose
- `app/dependencies.py`: `get_current_user` con HTTPBearer (auto_error=False → 401)
- `app/api/auth.py`: `POST /auth/login` con password da env
- `app/api/strategies.py`: stub protetto con approve/reject
- `tests/integration/test_api_auth.py`: 7 test (login, token scaduto, route protette)

---

## [0.1.6] — 2025-01-16

### Added
- `app/core/run_pipeline.py`: pipeline batch completa (genera → backtest → rank → upsert Supabase)
- Cache OHLCV in-memory per evitare fetch ripetuti nella stessa pipeline run
- Gestione eccezioni per strategia: errori singoli non bloccano la pipeline
- `tests/integration/test_pipeline.py`: 5 test integration

---

## [0.1.5] — 2025-01-16

### Added
- `app/core/market_data.py`: fetch OHLCV Binance con cache Supabase, fetch solo delta mancante
- `get_current_price()` per prezzo live
- `tests/unit/test_market_data.py`: 7 test con mock Supabase e Binance

---

## [0.1.4] — 2025-01-16

### Added
- `app/core/ranker.py`: filtri hard (min_trades, max_drawdown, min_sharpe, min_pnl) + score composito
- `RankConfig` dataclass con pesi configurabili
- `tests/unit/test_ranker.py`: 15 test (filtri, score range, ordinamento, config custom)

---

## [0.1.3] — 2025-01-16

### Added
- `app/core/backtester.py`: simulazione OHLCV con fee 0.1% e slippage 0.07%
- Chiusura automatica posizione aperta a fine serie
- `tests/unit/test_backtester.py`: 14 test (PnL, fee, equity_curve, no look-ahead)

### Fixed
- PnL calcolato correttamente anche su posizioni mai chiuse da segnale esplicito

---

## [0.1.2] — 2025-01-16

### Added
- `app/core/strategy_generator.py`: prodotto cartesiano parametri, 3 template (trend_ema, mean_reversion_rsi, breakout_bb)
- `StrategyParams` dataclass frozen con hash per ID deterministico
- `build_strategy_id()`: ID univoco da hash parametri
- `tests/unit/test_generator.py`: 8 test (>200 varianti, no duplicati, ID deterministico)

---

## [0.1.1] — 2025-01-15

### Added
- `app/core/indicators.py`: EMA, RSI (con gestione loss=0), Bollinger Bands
- Signal functions: `signal_ema_crossover`, `signal_rsi_reversion`, `signal_breakout_bb` (no look-ahead)
- `LOOKBACK_PERIODS` costante per warm-up minimo
- `tests/unit/test_indicators.py`: 17 test tutti verdi

---

## [0.1.0] — 2025-01-15

### Added
- Struttura monorepo `synthtrade/` (backend, supabase)
- `.gitignore`, `README.md`, `docker-compose.yml`
- FastAPI app con `GET /health` → `{"status": "ok"}`
- `config.py` con `Settings` via pydantic-settings
- `supabase_client.py` singleton con `lru_cache`
- `pytest.ini` (asyncio_mode=auto) + `conftest.py` (fixture `client`, `mock_supabase`)
- 4 migration SQL: strategies, trades, operation_logs, ohlcv_cache
- `seed.sql` con 3 strategie PENDING di esempio
- `Dockerfile` multi-stage + `docker-compose.yml`
- `requirements.txt` con tutte le dipendenze
- `docs/` con TASKS.md, STORY.md, CHANGELOG.md, BACKLOG.md, HANDOFF.md

---

<!-- Versioning guide:
  MAJOR (1.0.0) — breaking changes
  MINOR (0.1.0) — new features, backward compatible
  PATCH (0.0.1) — bug fixes
-->
