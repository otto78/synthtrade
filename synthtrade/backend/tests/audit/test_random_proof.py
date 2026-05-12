"""
TASK-FIX-011 — Verifica che il fix delle allucinazioni funzioni.

Questi test DEVONO PASSARE dopo il fix:
1. generate_for_request() produce score deterministici (stessi input → stessi output)
2. estimated_profit_pct è basato su backtest reale, non su random
3. score è nel range [0, 1] (da compute_score), non [70, 99] (da random.uniform)

Esecuzione:
    cd synthtrade/backend
    python -m pytest tests/audit/test_random_proof.py -v -s
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, AsyncMock
from app.core.strategy_generator import generate_for_request
from app.execution.schemas import StrategyRequest


@pytest.fixture
def base_request():
    """Richiesta base identica per entrambe le chiamate."""
    return StrategyRequest(
        budget_eur=100.0,
        duration_days=30,
        asset_class="crypto",
        risk_level="medium",
        max_strategies=5,
    )


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
async def test_same_request_produces_different_scores(base_request, mock_ohlcv):
    """
    DOPO IL FIX: Due chiamate identiche producono score IDENTICI.
    """
    with patch("app.core.strategy_generator.fetch_ohlcv", return_value=mock_ohlcv), \
         patch("app.core.strategy_generator.enrich_request_with_ai",
               new_callable=AsyncMock, return_value=base_request):
        results_1 = await generate_for_request(base_request)
        results_2 = await generate_for_request(base_request)

    assert results_1, "Nessuna strategia generata al primo run"
    assert results_2, "Nessuna strategia generata al secondo run"

    scores_1 = sorted([r.score for r in results_1])
    scores_2 = sorted([r.score for r in results_2])

    assert scores_1 == scores_2, (
        f"\n\n❌ Score ANCORA non deterministici dopo il fix!\n"
        f"   Call 1: {scores_1}\n"
        f"   Call 2: {scores_2}\n\n"
        f"   Il fix non ha rimosso completamente il random. "
        f"Verifica che generate_for_request() usi compute_score() e non random.uniform()."
    )
    print(f"✅ Score deterministici: {scores_1}")


@pytest.mark.asyncio
async def test_estimated_profit_is_not_random(base_request, mock_ohlcv):
    """
    DOPO IL FIX: I profitti stimati sono deterministici e basati su backtest.
    """
    with patch("app.core.strategy_generator.fetch_ohlcv", return_value=mock_ohlcv), \
         patch("app.core.strategy_generator.enrich_request_with_ai",
               new_callable=AsyncMock, return_value=base_request):
        results_1 = await generate_for_request(base_request)
        results_2 = await generate_for_request(base_request)

    profits_1 = sorted([r.estimated_profit_pct for r in results_1])
    profits_2 = sorted([r.estimated_profit_pct for r in results_2])

    assert profits_1 == profits_2, (
        f"\n\n❌ Profitti ANCORA non deterministici dopo il fix!\n"
        f"   Call 1: {profits_1}\n"
        f"   Call 2: {profits_2}\n\n"
        f"   Verifica che estimated_profit_pct = result.pnl_pct e non random.uniform()."
    )
    print(f"✅ Profitti deterministici: {profits_1}")


@pytest.mark.asyncio
async def test_score_is_in_correct_range(base_request, mock_ohlcv):
    """
    DOPO IL FIX: score è nel range [0, 1] (da compute_score), non [70, 99].
    """
    with patch("app.core.strategy_generator.fetch_ohlcv", return_value=mock_ohlcv), \
         patch("app.core.strategy_generator.enrich_request_with_ai",
               new_callable=AsyncMock, return_value=base_request):
        results = await generate_for_request(base_request)

    assert results, "Nessuna strategia generata"

    for r in results:
        in_correct_range = 0.0 <= r.score <= 1.0
        print(f"   Strategy {r.template}: score={r.score:.4f} (range corretto [0,1]: {in_correct_range})")
        assert in_correct_range, (
            f"❌ score={r.score} fuori dal range [0,1] — "
            f"deve venire da compute_score(), non da random.uniform()"
        )

    print(f"\n✅ Tutti gli score nel range corretto [0, 1]")


@pytest.mark.asyncio
async def test_backtest_fields_populated(base_request, mock_ohlcv):
    """
    DOPO IL FIX: backtest_pnl == estimated_profit_pct, backtest_trades > 0.
    """
    with patch("app.core.strategy_generator.fetch_ohlcv", return_value=mock_ohlcv), \
         patch("app.core.strategy_generator.enrich_request_with_ai",
               new_callable=AsyncMock, return_value=base_request):
        results = await generate_for_request(base_request)

    for r in results:
        assert r.backtest_trades > 0, (
            f"❌ backtest_trades=0 per {r.title} — backtest non eseguito"
        )
        assert r.estimated_profit_pct == r.backtest_pnl, (
            f"❌ estimated_profit_pct ({r.estimated_profit_pct}) != "
            f"backtest_pnl ({r.backtest_pnl})"
        )
        assert r.data_source.startswith("binance_"), (
            f"❌ data_source non Binance: {r.data_source}"
        )
        print(f"✅ {r.title}: trades={r.backtest_trades} "
              f"pnl={r.backtest_pnl:.2f}% "
              f"source={r.data_source}")