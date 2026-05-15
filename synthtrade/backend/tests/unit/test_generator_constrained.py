import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, AsyncMock, MagicMock
from app.execution.schemas import StrategyRequest
from app.core.strategy_generator import generate_for_request, normalize_trading_pair, TEMPLATES


def test_normalize_trading_pair_formats_ccxt():
    """HALU-BE-01: chip BTCUSDT → BTC/USDT."""
    assert normalize_trading_pair("BTCUSDT") == "BTC/USDT"
    assert normalize_trading_pair("ethusdt") == "ETH/USDT"
    assert normalize_trading_pair("BTC/USDT") == "BTC/USDT"


@pytest.fixture
def mock_ohlcv():
    """OHLCV sintetica con 20 cicli bull/bear per generare 30+ EMA crossover."""
    rng = np.random.default_rng(123)
    n = 8000
    cycles = 20
    t = np.linspace(0, cycles * 2 * np.pi, n)
    prices = 50000 + np.sin(t) * 3000 + rng.standard_normal(n) * 800
    prices = np.maximum(prices, 10000)
    return pd.DataFrame({
        "open": prices * 0.998,
        "high": prices * 1.004,
        "low":  prices * 0.996,
        "close": prices,
        "volume": np.abs(np.ones(n) * 5.0 + rng.standard_normal(n) * 1),
    }, index=pd.date_range("2024-01-01", periods=n, freq="1h"))


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_ohlcv")
async def test_generate_for_request_duration_filter(mock_ohlcv):
    """
    TASK-035: generate_for_request(req: StrategyRequest) restituisce solo strategie con duration_days compatibile (± 20%)
    """
    mock_md_service = MagicMock()
    mock_md_service.get_ohlcv.return_value = mock_ohlcv

    with patch("app.core.strategy_generator.enrich_request_with_ai",
               new_callable=AsyncMock, side_effect=lambda x: x):
        # trend_ema has 30 days. request 30 days should include it.
        req = StrategyRequest(
            budget_eur=100.0,
            duration_days=30,
            asset_class="crypto",
            risk_level="medium"
        )
        strategies, _ = await generate_for_request(req, mock_md_service)
        templates_found = {s.template for s in strategies}
        assert "trend_ema" in templates_found

        # request 7 days should include breakout_bb (7 days) but not trend_ema (30 days)
        req_short = StrategyRequest(
            budget_eur=100.0,
            duration_days=7,
            asset_class="crypto",
            risk_level="medium"
        )
        strategies_short, _ = await generate_for_request(req_short, mock_md_service)
        templates_found_short = {s.template for s in strategies_short}
        assert "breakout_bb" in templates_found_short
        assert "trend_ema" not in templates_found_short


@pytest.mark.asyncio
async def test_generate_for_request_symbols_filter(mock_ohlcv):
    """
    TASK-036: se req.symbols è specificato, le strategie generate usano solo quei simboli
    """
    mock_md_service = MagicMock()
    mock_md_service.get_ohlcv.return_value = mock_ohlcv

    with patch("app.core.strategy_generator.enrich_request_with_ai",
               new_callable=AsyncMock, side_effect=lambda x: x):
        symbols = ["ETH/USDT", "SOL/USDT"]
        req = StrategyRequest(
            budget_eur=100.0,
            duration_days=30,
            asset_class="crypto",
            risk_level="medium",
            symbols=symbols
        )
        strategies, _ = await generate_for_request(req, mock_md_service)
        for s in strategies:
            assert s.pair in symbols


@pytest.mark.asyncio
async def test_generate_for_request_risk_level_low(mock_ohlcv):
    """
    TASK-037: risk_level = "low" esclude strategie con rischio alto
    """
    mock_md_service = MagicMock()
    mock_md_service.get_ohlcv.return_value = mock_ohlcv

    with patch("app.core.strategy_generator.enrich_request_with_ai",
               new_callable=AsyncMock, side_effect=lambda x: x):
        req = StrategyRequest(
            budget_eur=100.0,
            duration_days=7,
            asset_class="crypto",
            risk_level="low"
        )
        strategies, _ = await generate_for_request(req, mock_md_service)
        templates_found = {s.template for s in strategies}
        assert "breakout_bb" not in templates_found


@pytest.mark.asyncio
async def test_generate_for_request_risk_level_high(mock_ohlcv):
    """
    TASK-038: risk_level = "high" consente tutti i template
    """
    mock_md_service = MagicMock()
    mock_md_service.get_ohlcv.return_value = mock_ohlcv

    with patch("app.core.strategy_generator.enrich_request_with_ai",
               new_callable=AsyncMock, side_effect=lambda x: x):
        req = StrategyRequest(
            budget_eur=100.0,
            duration_days=7,
            asset_class="crypto",
            risk_level="high"
        )
        strategies, _ = await generate_for_request(req, mock_md_service)
        templates_found = {s.template for s in strategies}
        assert "breakout_bb" in templates_found


@pytest.mark.asyncio
async def test_generate_for_request_budget_propagation(mock_ohlcv):
    """
    TASK-039: budget_eur viene propagato come budget_eur nei parametri della strategia generata
    """
    mock_md_service = MagicMock()
    mock_md_service.get_ohlcv.return_value = mock_ohlcv

    with patch("app.core.strategy_generator.enrich_request_with_ai",
               new_callable=AsyncMock, side_effect=lambda x: x):
        budget = 500.0
        req = StrategyRequest(
            budget_eur=budget,
            duration_days=30,
            asset_class="crypto",
            risk_level="medium"
        )
        strategies, _ = await generate_for_request(req, mock_md_service)
        for s in strategies:
            assert s.budget_eur == budget


@pytest.mark.asyncio
async def test_generate_for_request_max_strategies_limit(mock_ohlcv):
    """
    TASK-040: max_strategies limita il numero di strategie restituite
    """
    mock_md_service = MagicMock()
    mock_md_service.get_ohlcv.return_value = mock_ohlcv

    with patch("app.core.strategy_generator.enrich_request_with_ai",
               new_callable=AsyncMock, side_effect=lambda x: x):
        max_s = 3
        req = StrategyRequest(
            budget_eur=100.0,
            duration_days=30,
            asset_class="crypto",
            risk_level="medium",
            max_strategies=max_s
        )
        strategies, _ = await generate_for_request(req, mock_md_service)
        assert len(strategies) <= max_s