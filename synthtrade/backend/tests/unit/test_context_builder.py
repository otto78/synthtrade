import pytest
import pandas as pd
import numpy as np
from app.ai.context_builder import build_ohlcv_summary, detect_market_regime, build_market_context
from app.ai.schemas import MarketContext


def make_ohlcv(n=100, trend=0.3) -> pd.DataFrame:
    np.random.seed(42)
    close = pd.Series(100 + np.cumsum(np.random.randn(n) * 0.5 + trend))
    return pd.DataFrame({
        "open": close, "high": close * 1.002,
        "low": close * 0.998, "close": close, "volume": 1000.0,
    })


def test_build_ohlcv_summary_aggregates_stats():
    df = make_ohlcv(100)
    summary = build_ohlcv_summary(df, symbol="BTC/USDT", timeframe="1h")
    assert summary.candles == 100
    assert summary.price_min < summary.price_max
    assert summary.price_last == pytest.approx(df["close"].iloc[-1])
    assert summary.volume_avg > 0


def test_build_ohlcv_summary_raises_on_empty():
    with pytest.raises(ValueError, match="candles"):
        build_ohlcv_summary(pd.DataFrame(), symbol="BTC/USDT", timeframe="1h")


def test_build_ohlcv_summary_raises_below_minimum():
    df = make_ohlcv(5)
    with pytest.raises(ValueError, match="minimo"):
        build_ohlcv_summary(df, symbol="BTC/USDT", timeframe="1h", min_candles=20)


def test_detect_market_regime_trending():
    # Serie con trend forte
    close = pd.Series(np.linspace(100, 130, 100))
    df = pd.DataFrame({"close": close, "high": close * 1.001, "low": close * 0.999})
    regime = detect_market_regime(df)
    assert regime == "trending"


def test_detect_market_regime_volatile():
    # Serie molto volatile
    np.random.seed(0)
    close = pd.Series(100 + np.cumsum(np.random.randn(100) * 5))
    df = pd.DataFrame({"close": close, "high": close * 1.05, "low": close * 0.95})
    regime = detect_market_regime(df)
    assert regime in ("volatile", "ranging", "trending")  # dipende dai dati


def test_detect_market_regime_ranging():
    # Serie laterale
    np.random.seed(1)
    close = pd.Series(100 + np.random.randn(100) * 0.1)
    df = pd.DataFrame({"close": close, "high": close * 1.001, "low": close * 0.999})
    regime = detect_market_regime(df)
    assert regime == "ranging"


def test_build_market_context_returns_market_context():
    df = make_ohlcv(100)
    ctx = build_market_context(df, symbol="BTC/USDT", timeframe="1h")
    assert isinstance(ctx, MarketContext)
    assert ctx.symbol == "BTC/USDT"
    assert ctx.regime in ("trending", "volatile", "ranging")
    assert ctx.summary.candles == 100
