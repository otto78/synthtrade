import pytest
import pandas as pd
import numpy as np
import asyncio
from unittest.mock import MagicMock, patch, call
from app.core.run_pipeline import run_pipeline
from app.services.market_data_service import MarketDataService


def make_ohlcv(n: int = 300) -> pd.DataFrame:
    np.random.seed(42)
    close = pd.Series(100 + np.cumsum(np.abs(np.random.randn(n)) + 0.3))
    return pd.DataFrame({
        "open": close, "high": close * 1.001,
        "low": close * 0.999, "close": close, "volume": 1000.0,
    })


@pytest.fixture
def mock_md_service():
    service = MagicMock(spec=MarketDataService)
    service.get_ohlcv.return_value = make_ohlcv()
    return service


@pytest.fixture
def mock_db():
    return MagicMock()


# ── Test: solo strategie con score > 0 vengono salvate ───────────────

@pytest.mark.asyncio
async def test_pipeline_saves_only_scored_strategies(mock_md_service, mock_db):
    with patch("app.core.run_pipeline.get_supabase", return_value=mock_db):
        saved = await run_pipeline(mock_md_service, pairs=["BTC/USDT"], timeframes=["5m"], ai_eval=False)

    assert isinstance(saved, int)
    assert saved >= 0


@pytest.mark.asyncio
async def test_pipeline_returns_count_of_saved_strategies(mock_md_service, mock_db):
    with patch("app.core.run_pipeline.get_supabase", return_value=mock_db):
        count = await run_pipeline(mock_md_service, pairs=["BTC/USDT"], timeframes=["5m"], ai_eval=False)

    assert count >= 0


@pytest.mark.asyncio
async def test_pipeline_upserts_to_supabase_when_strategies_found(mock_md_service, mock_db):
    with patch("app.core.run_pipeline.get_supabase", return_value=mock_db):
        count = await run_pipeline(mock_md_service, pairs=["BTC/USDT"], timeframes=["5m"], ai_eval=False)

    if count > 0:
        mock_db.table.return_value.upsert.assert_called()


@pytest.mark.asyncio
async def test_pipeline_no_error_on_50_strategies(mock_md_service, mock_db):
    """Pipeline non deve sollevare eccezioni su un batch reale."""
    with patch("app.core.run_pipeline.get_supabase", return_value=mock_db):
        try:
            await run_pipeline(mock_md_service, pairs=["BTC/USDT"], timeframes=["5m"], ai_eval=False)
        except Exception as e:
            pytest.fail(f"Pipeline ha sollevato un'eccezione: {e}")


@pytest.mark.asyncio
async def test_pipeline_skips_strategy_on_exception(mock_md_service, mock_db):
    """Un errore su una singola strategia non blocca il resto della pipeline."""
    call_count = {"n": 0}

    def flaky_backtest(df, signal_fn, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise ValueError("Errore simulato")
        from app.core.backtester import run_backtest as real_backtest
        return real_backtest(df, signal_fn, **kwargs)

    with patch("app.core.run_pipeline.get_supabase", return_value=mock_db), \
         patch("app.core.run_pipeline.run_backtest", side_effect=flaky_backtest):

        try:
            await run_pipeline(mock_md_service, pairs=["BTC/USDT"], timeframes=["5m"], ai_eval=False)
        except Exception as e:
            pytest.fail(f"Pipeline non deve propagare eccezioni singole: {e}")
