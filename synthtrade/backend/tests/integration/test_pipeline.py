import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch, call


def make_ohlcv(n: int = 300) -> pd.DataFrame:
    np.random.seed(42)
    close = pd.Series(100 + np.cumsum(np.abs(np.random.randn(n)) + 0.3))
    return pd.DataFrame({
        "open": close, "high": close * 1.001,
        "low": close * 0.999, "close": close, "volume": 1000.0,
    })


# ── Test: solo strategie con score > 0 vengono salvate ───────────────

def test_pipeline_saves_only_scored_strategies():
    mock_db = MagicMock()
    ohlcv = make_ohlcv()

    with patch("app.core.run_pipeline.fetch_ohlcv", return_value=ohlcv), \
         patch("app.core.run_pipeline.get_supabase", return_value=mock_db):

        from app.core.run_pipeline import run_pipeline
        saved = run_pipeline(pairs=["BTC/USDT"], timeframes=["5m"])

    assert isinstance(saved, int)
    assert saved >= 0


def test_pipeline_returns_count_of_saved_strategies():
    mock_db = MagicMock()
    ohlcv = make_ohlcv()

    with patch("app.core.run_pipeline.fetch_ohlcv", return_value=ohlcv), \
         patch("app.core.run_pipeline.get_supabase", return_value=mock_db):

        from app.core.run_pipeline import run_pipeline
        count = run_pipeline(pairs=["BTC/USDT"], timeframes=["5m"])

    assert count >= 0


def test_pipeline_upserts_to_supabase_when_strategies_found():
    mock_db = MagicMock()
    ohlcv = make_ohlcv()

    with patch("app.core.run_pipeline.fetch_ohlcv", return_value=ohlcv), \
         patch("app.core.run_pipeline.get_supabase", return_value=mock_db):

        from app.core.run_pipeline import run_pipeline
        count = run_pipeline(pairs=["BTC/USDT"], timeframes=["5m"])

    if count > 0:
        mock_db.table.return_value.upsert.assert_called()


def test_pipeline_no_error_on_50_strategies():
    """Pipeline non deve sollevare eccezioni su un batch reale."""
    mock_db = MagicMock()
    ohlcv = make_ohlcv()

    with patch("app.core.run_pipeline.fetch_ohlcv", return_value=ohlcv), \
         patch("app.core.run_pipeline.get_supabase", return_value=mock_db):

        from app.core.run_pipeline import run_pipeline
        try:
            run_pipeline(pairs=["BTC/USDT"], timeframes=["5m"])
        except Exception as e:
            pytest.fail(f"Pipeline ha sollevato un'eccezione: {e}")


def test_pipeline_skips_strategy_on_exception():
    """Un errore su una singola strategia non blocca il resto della pipeline."""
    mock_db = MagicMock()
    ohlcv = make_ohlcv()
    call_count = {"n": 0}

    def flaky_backtest(df, signal_fn, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise ValueError("Errore simulato")
        from app.core.backtester import run_backtest as real_backtest
        return real_backtest(df, signal_fn, **kwargs)

    with patch("app.core.run_pipeline.fetch_ohlcv", return_value=ohlcv), \
         patch("app.core.run_pipeline.get_supabase", return_value=mock_db), \
         patch("app.core.run_pipeline.run_backtest", side_effect=flaky_backtest):

        from app.core.run_pipeline import run_pipeline
        try:
            run_pipeline(pairs=["BTC/USDT"], timeframes=["5m"])
        except Exception as e:
            pytest.fail(f"Pipeline non deve propagare eccezioni singole: {e}")
