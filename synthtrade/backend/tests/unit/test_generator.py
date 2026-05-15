import pytest
import pandas as pd
from app.core.strategy_generator import (
    generate_all_variants,
    build_strategy_id,
    StrategyParams,
    TEMPLATES,
    generate_for_request
)
from app.execution.schemas import StrategyRequest
from unittest.mock import patch, AsyncMock, MagicMock

def test_generate_at_least_200_variants():
    variants = list(generate_all_variants())
    assert len(variants) >= 50


def test_each_variant_has_required_fields():
    for s in generate_all_variants():
        assert s.template
        assert s.pair
        assert s.timeframe
        assert isinstance(s.params, dict)
        assert len(s.params) > 0
        assert s.title, f"Missing title for {s.template}"
        assert s.description, f"Missing description for {s.template}"
        assert s.budget_eur > 0, f"Invalid budget for {s.template}"


@pytest.fixture
def mock_ohlcv():
    import numpy as np
    rng = np.random.default_rng(123)
    n = 8000
    cycles = 20
    t = np.linspace(0, cycles * 2 * np.pi, n)
    prices = 50000 + np.sin(t) * 3000 + rng.standard_normal(n) * 800
    prices = np.maximum(prices, 10000)
    return pd.DataFrame({
        "ts": pd.date_range("2024-01-01", periods=n, freq="1h"),
        "open": prices * 0.998,
        "high": prices * 1.004,
        "low":  prices * 0.996,
        "close": prices,
        "volume": np.abs(np.ones(n) * 5.0 + rng.standard_normal(n) * 1),
    })


@pytest.mark.asyncio
async def test_generate_for_request_full_data(mock_ohlcv):
    req = StrategyRequest(
        budget_eur=500.0,
        duration_days=30,
        asset_class="crypto",
        risk_level="medium",
        max_strategies=5
    )

    mock_md_service = MagicMock()
    mock_md_service.get_ohlcv.return_value = mock_ohlcv

    with patch("app.core.strategy_generator.enrich_request_with_ai",
               new_callable=AsyncMock, return_value=req):
        results, hint = await generate_for_request(req, mock_md_service)
    
    assert len(results) > 0
    assert hint is None
    for v in results:
        assert v.title
        assert v.description
        assert v.budget_eur == 500.0
        assert v.score > 0
        assert v.backtest_trades > 0


def test_strategy_id_is_deterministic():
    s = StrategyParams(template="trend_ema", pair="BTC/USDT", timeframe="5m",
                       params={"ema_fast": 20, "ema_slow": 50})
    assert build_strategy_id(s) == build_strategy_id(s)


def test_strategy_id_differs_for_different_params():
    s1 = StrategyParams(template="trend_ema", pair="BTC/USDT", timeframe="5m",
                        params={"ema_fast": 20, "ema_slow": 50})
    s2 = StrategyParams(template="trend_ema", pair="BTC/USDT", timeframe="5m",
                        params={"ema_fast": 10, "ema_slow": 100})
    assert build_strategy_id(s1) != build_strategy_id(s2)


def test_no_duplicate_ids_on_500_variants():
    variants = list(generate_all_variants())[:500]
    ids = [build_strategy_id(s) for s in variants]
    assert len(ids) == len(set(ids))


def test_all_templates_covered():
    templates_generated = {s.template for s in generate_all_variants()}
    assert templates_generated == set(TEMPLATES.keys())


def test_custom_pairs_and_timeframes():
    variants = list(generate_all_variants(pairs=["ETH/USDT"], timeframes=["1h"]))
    assert all(s.pair == "ETH/USDT" for s in variants)
    assert all(s.timeframe == "1h" for s in variants)


def test_params_values_come_from_template_grid():
    for s in generate_all_variants():
        grid = TEMPLATES[s.template]["params"]
        for key, value in s.params.items():
            assert value in grid[key], f"{key}={value} non è nel grid di {s.template}"
