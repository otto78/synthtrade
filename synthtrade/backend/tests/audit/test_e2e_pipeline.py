"""
TASK-FIX-008 — Test E2E: pipeline completa utente → backtest → DB

Verifica che generate_for_request() usi backtest reale su dati OHLCV
e produca risultati deterministici (stessi dati → stessi risultati).

Esecuzione:
    cd synthtrade/backend
    python -m pytest tests/audit/test_e2e_pipeline.py -v -s
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, AsyncMock
from app.core.strategy_generator import generate_for_request
from app.execution.schemas import StrategyRequest


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
async def test_generate_for_request_uses_backtest(mock_ohlcv):
    """
    E2E: generate_for_request() deve:
    1. Chiamare fetch_ohlcv() (dati storici)
    2. Chiamare run_backtest() via compute_score
    3. Avere score deterministici (non random)
    4. Avere backtest_pnl popolato con valore reale
    """
    req = StrategyRequest(
        budget_eur=100.0,
        duration_days=30,
        asset_class="crypto",
        risk_level="medium",
        max_strategies=3,
    )

    with patch("app.core.strategy_generator.fetch_ohlcv", return_value=mock_ohlcv), \
         patch("app.core.strategy_generator.enrich_request_with_ai",
               new_callable=AsyncMock, return_value=req):
        results_1, _ = await generate_for_request(req)
        results_2, _ = await generate_for_request(req)

    assert results_1, "Nessuna strategia generata al primo run"
    assert results_2, "Nessuna strategia generata al secondo run"

    # Deterministico: stessi input → stessi output
    scores_1 = [r.score for r in results_1]
    scores_2 = [r.score for r in results_2]
    assert scores_1 == scores_2, (
        f"Score non deterministici:\nCall 1: {scores_1}\nCall 2: {scores_2}"
    )

    profits_1 = [r.estimated_profit_pct for r in results_1]
    profits_2 = [r.estimated_profit_pct for r in results_2]
    assert profits_1 == profits_2, (
        f"Profitti non deterministici:\nCall 1: {profits_1}\nCall 2: {profits_2}"
    )

    # Backtest eseguito: campi popolati
    for s in results_1:
        assert s.backtest_trades > 0, (
            f"backtest_trades deve essere > 0, got {s.backtest_trades}"
        )
        assert s.estimated_profit_pct == s.backtest_pnl, (
            f"estimated_profit_pct ({s.estimated_profit_pct}) != "
            f"backtest_pnl ({s.backtest_pnl})"
        )
        assert s.data_source.startswith("binance_"), (
            f"data_source deve indicare fonte Binance, got {s.data_source}"
        )
        assert 0.0 < s.score <= 1.0, (
            f"score fuori range [0,1]: {s.score}"
        )
        assert s.backtest_sharpe >= 0.0, f"sharpe deve essere >= 0: {s.backtest_sharpe}"
        print(f"  ✅ {s.title}: score={s.score:.4f} pnl={s.backtest_pnl:.2f}% "
              f"sharpe={s.backtest_sharpe:.3f} trades={s.backtest_trades}")


@pytest.mark.asyncio
async def test_pipeline_rejects_low_quality_strategies(mock_ohlcv):
    """
    E2E: Le strategie che non superano le soglie del ranker devono essere
    escluse (score=None) e non mostrate all'utente.
    """
    req = StrategyRequest(
        budget_eur=100.0,
        duration_days=30,
        asset_class="crypto",
        risk_level="medium",
        max_strategies=10,
    )

    with patch("app.core.strategy_generator.fetch_ohlcv", return_value=mock_ohlcv), \
         patch("app.core.strategy_generator.enrich_request_with_ai",
               new_callable=AsyncMock, return_value=req):
        results, _ = await generate_for_request(req)

    # Tutte le strategie restituite devono avere score > 0
    assert len(results) <= 10, f"max_strategies=10, got {len(results)}"
    for s in results:
        assert s.score > 0, f"Strategia con score nullo non filtrata: {s.title}"
        assert s.backtest_trades > 0, (
            f"Strategia senza trades non filtrata: {s.title}"
        )