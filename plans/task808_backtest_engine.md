# TASK-808 — Backtest Engine Implementation Plan

## Overview
Motore di backtest per validare le strategie scalping su dati storici prima del go-live.

## Files to Create

### 1. Models — `app/scalping/models/backtest.py`
- `BacktestConfig`: symbol, timeframe, start_date, end_date, initial_capital, use_intelligence, ...
- `SimulatedTrade`: entry/exit price, quantity, pnl, pnl_pct, signal_type, signal_score, ...
- `BacktestResult`: config, trades list, metrics dict, correlation data

### 2. HistoricalLoader — `app/scalping/backtest/historical_loader.py`
- `HistoricalLoader.load_ohlcv(symbol, interval, start, end)` → List[Candle]
- Usa Binance REST API pubblica (nessuna API key necessaria per OHLCV storico)
- Opzione caricamento da file CSV per test deterministici

### 3. BacktestEngine — `app/scalping/backtest/backtest_engine.py`
- `BacktestEngine.run(config, on_candle_callback, progress_callback)` → BacktestResult
- Itera candele, chiama ExecutionLoop.process_candle() su ogni candela
- Opzione `use_intelligence`: True = con SignalScoreEngine, False = solo segnale tecnico
- Callback di progresso per report intermedio

### 4. PerformanceCalculator — `app/scalping/backtest/performance_calculator.py`
- win_rate, total_pnl, max_drawdown, sharpe_ratio, profit_factor
- avg_win, avg_loss, consecutive_losses
- Correlazione signal_score → trade outcome
- Calcolo basato su lista di SimulatedTrade

### 5. ReportGenerator — `app/scalping/backtest/report_generator.py`
- `generate_report(result, config)` → dict JSON
- Confronto metriche with/without intelligence
- Riepilogo esecutivo

### 6. API Endpoints — `app/scalping/router.py` (da creare)
- `POST /scalping/backtest/run` — avvia backtest
- `GET /scalping/backtest/{id}/result` — recupera risultato

### 7. Tests — `tests/scalping/test_backtest_engine.py`
- 10+ test: config validazione, historical loader mock, engine run, metrics, correlation

## Architecture Pattern (segue pattern esistente)
- Models: Pydantic BaseModel con ConfigDict(frozen=True)
- Engine: classi con dependency injection (come ExecutionLoop)
- Test: pytest with @pytest.mark.asyncio, unittest.mock (AsyncMock)
- API: router FastAPI con dipendenze (come app.main)

## Verification
```bash
cd synthtrade/backend && python -m pytest tests/scalping/test_backtest_engine.py -v