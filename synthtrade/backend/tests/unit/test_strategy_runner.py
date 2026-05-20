"""
🔴 TASK-407: Test per StrategyRunner
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from app.execution.strategy_runner import StrategyRunner, _extract_symbols, _signal_to_direction


@pytest.fixture
def mock_ohlcv():
    """Fixture: 100 candele simulate."""
    np.random.seed(42)
    prices = 50000 + np.cumsum(np.random.randn(100) * 100)
    return pd.DataFrame({
        "open": prices * 0.999, "high": prices * 1.002,
        "low": prices * 0.998, "close": prices,
        "volume": np.ones(100) * 10,
    }, index=pd.date_range("2026-01-01", periods=100, freq="1h"))


@pytest.fixture
def mock_engine():
    """Mock ExecutionEngine."""
    engine = MagicMock()
    engine.process_signals = AsyncMock(return_value=None)
    engine.order_tracker = MagicMock()
    engine.order_tracker.get_open_positions = MagicMock(return_value=[])
    engine.order_tracker.get_realized_pnl = MagicMock(return_value=0.0)
    engine.order_tracker.update_unrealized_pnl = MagicMock(return_value=0.0)
    engine.exchange = MagicMock()
    engine.exchange.get_ticker_price = AsyncMock(return_value=100.0)
    return engine


@pytest.fixture
def mock_db(mocker):
    """Mock Supabase DB."""
    mock = MagicMock()
    mocker.patch("app.execution.strategy_runner.get_supabase", return_value=mock)
    return mock


def test_extract_symbols_single():
    """Estrae il pair singolo."""
    s = {"pair": "BTC/USDT", "params": {}}
    assert _extract_symbols(s) == ["BTC/USDT"]


def test_extract_symbols_multi():
    """Estrae simboli multipli da params.allocation."""
    s = {"params": {"allocation": [{"symbol": "BTC/USDT"}, {"symbol": "ETH/USDT"}]}}
    assert _extract_symbols(s) == ["BTC/USDT", "ETH/USDT"]


def test_extract_symbols_empty():
    """Se non c'è pair né allocation → fallback a BTC/USDT."""
    s = {"params": {}}
    assert _extract_symbols(s) == ["BTC/USDT"]


def test_signal_to_direction():
    assert _signal_to_direction(1) == "BUY"
    assert _signal_to_direction(-1) == "SELL"
    assert _signal_to_direction(0) is None


@pytest.mark.asyncio
async def test_run_tick_buy_signal(mock_engine, mock_ohlcv, mock_db):
    """Segnale BUY → engine.process_signals chiamato."""
    mock_signal = MagicMock(return_value=pd.Series([1]))
    with patch("app.execution.strategy_runner.registry.get", return_value=mock_signal), \
         patch("app.execution.strategy_runner.fetch_ohlcv", return_value=mock_ohlcv):
        runner = StrategyRunner(mock_engine)
        strategy = {
            "id": "test-123",
            "template": "mean_reversion_rsi",
            "pair": "BTC/USDT",
            "timeframe": "1h",
            "params": {"rsi_period": 14, "rsi_oversold": 25, "rsi_overbought": 70},
            "budget_eur": 1000,
        }
        await runner.run_tick(strategy)
        # process_signals deve essere chiamato con i segnali raccolti
        assert mock_engine.process_signals.call_count == 1


@pytest.mark.asyncio
async def test_run_tick_no_crash(mock_engine, mock_ohlcv, mock_db):
    """Il tick non deve mai crashare, indipendentemente dal segnale."""
    with patch("app.execution.strategy_runner.fetch_ohlcv", return_value=mock_ohlcv):
        runner = StrategyRunner(mock_engine)
        strategy = {
            "id": "test-456",
            "template": "trend_ema",
            "pair": "BTC/USDT",
            "timeframe": "1h",
            "params": {"ema_fast": 10, "ema_slow": 50},
            "budget_eur": 1000,
        }
        await runner.run_tick(strategy)
        # Con i dati mockati, EMA genera segnale. Il test verifica solo che non crasha.
        assert True


@pytest.mark.asyncio
async def test_run_tick_unknown_template(mock_engine, mock_ohlcv, mock_db):
    """Template sconosciuto → skip silenzioso."""
    with patch("app.execution.strategy_runner.fetch_ohlcv", return_value=mock_ohlcv):
        runner = StrategyRunner(mock_engine)
        strategy = {
            "id": "test-789",
            "template": "unknown_template",
            "pair": "BTC/USDT",
            "timeframe": "1h",
            "params": {},
            "budget_eur": 1000,
        }
        await runner.run_tick(strategy)
        mock_engine.process_signals.assert_not_called()


@pytest.mark.asyncio
async def test_run_tick_ohlcv_error(mock_engine, mock_db):
    """Errore fetch OHLCV → skip con log."""
    with patch("app.execution.strategy_runner.fetch_ohlcv", side_effect=Exception("API error")):
        runner = StrategyRunner(mock_engine)
        strategy = {
            "id": "test-err",
            "template": "mean_reversion_rsi",
            "pair": "BTC/USDT",
            "timeframe": "1h",
            "params": {"rsi_period": 14, "rsi_oversold": 25, "rsi_overbought": 70},
            "budget_eur": 1000,
        }
        await runner.run_tick(strategy)
        # Non deve propagare eccezioni
        mock_engine.process_signals.assert_not_called()


@pytest.mark.asyncio
async def test_run_tick_updates_last_tick_at(mock_engine, mock_ohlcv, mock_db):
    """Verifica aggiornamento last_tick_at su DB."""
    with patch("app.execution.strategy_runner.fetch_ohlcv", return_value=mock_ohlcv):
        runner = StrategyRunner(mock_engine)
        strategy = {
            "id": "test-tick",
            "template": "mean_reversion_rsi",
            "pair": "BTC/USDT",
            "timeframe": "1h",
            "params": {"rsi_period": 14, "rsi_oversold": 25, "rsi_overbought": 70},
            "budget_eur": 1000,
        }
        await runner.run_tick(strategy)
        # Verifica che update su DB sia stato chiamato
        mock_db.table.assert_called_with("strategies")

@pytest.mark.asyncio
async def test_run_tick_accumulates_signals(mock_engine, mock_ohlcv, mock_db):
    """Testa che StrategyRunner accumuli segnali da più simboli e li passi in un unico call."""
    mock_signal = MagicMock(return_value=pd.Series([1]))
    with patch("app.execution.strategy_runner.registry.get", return_value=mock_signal), \
         patch("app.execution.strategy_runner.fetch_ohlcv", return_value=mock_ohlcv):
        runner = StrategyRunner(mock_engine)
        strategy = {
            "id": "test-accum",
            "template": "mean_reversion_rsi",
            "timeframe": "1h",
            "params": {
                "rsi_period": 14,
                "rsi_oversold": 25,
                "rsi_overbought": 70,
                "allocation": [
                    {"symbol": "BTC/USDT", "pct": 60},
                    {"symbol": "ETH/USDT", "pct": 40},
                ],
            },
            "budget_eur": 1000,
        }
        await runner.run_tick(strategy)
        # process_signals deve essere chiamato UNA VOLTA con DUE segnali
        assert mock_engine.process_signals.call_count == 1
        args, kwargs = mock_engine.process_signals.call_args
        assert len(kwargs["signals"]) == 2
        symbols = [s.symbol for s in kwargs["signals"]]
        assert "BTC/USDT" in symbols
        assert "ETH/USDT" in symbols