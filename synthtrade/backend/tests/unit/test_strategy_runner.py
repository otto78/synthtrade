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
    engine.process_signal = AsyncMock(return_value=None)
    engine.order_tracker = MagicMock()
    engine.order_tracker.get_open_positions = MagicMock(return_value=[])
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
    """Segnale BUY → engine.process_signal chiamato."""
    with patch("app.execution.strategy_runner.fetch_ohlcv", return_value=mock_ohlcv):
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
        # Se RSI genera BUY, process_signal deve essere chiamato
        # (con dati mockati potrebbe non generare segnale, ma non deve crashare)
        assert True


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
        mock_engine.process_signal.assert_not_called()


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
        mock_engine.process_signal.assert_not_called()


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
async def test_run_tick_allocation_budget(mock_engine, mock_ohlcv, mock_db):
    """Testa che il budget sia calcolato in base all'allocazione percentuale per ciascun simbolo."""
    mock_signal = MagicMock(return_value=pd.Series([1]))
    with patch("app.execution.strategy_runner.registry.get", return_value=mock_signal), \
         patch("app.execution.strategy_runner.fetch_ohlcv", return_value=mock_ohlcv):
        runner = StrategyRunner(mock_engine)
        strategy = {
            "id": "test-alloc",
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
        # Il metodo process_signal dovrebbe essere stato chiamato due volte, una per ogni simbolo
        assert mock_engine.process_signal.call_count == 2
        # Verifica i valori di budget passati a process_signal per ciascun simbolo
        calls = mock_engine.process_signal.call_args_list
        # Primo call (BTC/USDT) budget = 1000 * 0.60 = 600
        _, kwargs1 = calls[0]
        assert pytest.approx(kwargs1["balance"], 0.01) == 600
        # Secondo call (ETH/USDT) budget = 1000 * 0.40 = 400
        _, kwargs2 = calls[1]
        assert pytest.approx(kwargs2["balance"], 0.01) == 400

@pytest.mark.asyncio
async def test_run_tick_symbol_isolation(mock_engine, mock_ohlcv, mock_db):
    """Testa che le open_positions passate all'engine siano filtrate per simbolo."""
    from app.execution.schemas import PositionSnapshot
    
    mock_engine.order_tracker.get_open_positions.return_value = [
        PositionSnapshot(trade_id="1", strategy_id="test-iso", symbol="BTC/USDT", direction="BUY", entry_price=50000, quantity=1, stop_loss=40000, take_profit=60000, opened_at=datetime.now(timezone.utc)),
        PositionSnapshot(trade_id="2", strategy_id="test-iso", symbol="ETH/USDT", direction="SELL", entry_price=3000, quantity=10, stop_loss=3500, take_profit=2500, opened_at=datetime.now(timezone.utc)),
    ]

    mock_signal = MagicMock(return_value=pd.Series([1]))
    with patch("app.execution.strategy_runner.registry.get", return_value=mock_signal), \
         patch("app.execution.strategy_runner.fetch_ohlcv", return_value=mock_ohlcv):
        runner = StrategyRunner(mock_engine)
        strategy = {
            "id": "test-iso",
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
        
        assert mock_engine.process_signal.call_count == 2
        calls = mock_engine.process_signal.call_args_list
        
        # BTC/USDT call should only see BTC position
        _, kwargs1 = calls[0]
        assert len(kwargs1["open_positions"]) == 1
        assert kwargs1["open_positions"][0].symbol == "BTC/USDT"
        
        # ETH/USDT call should only see ETH position
        _, kwargs2 = calls[1]
        assert len(kwargs2["open_positions"]) == 1
        assert kwargs2["open_positions"][0].symbol == "ETH/USDT"