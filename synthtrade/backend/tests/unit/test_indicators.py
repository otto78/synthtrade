import pytest
import pandas as pd
import numpy as np
from app.core.indicators import (
    ema, rsi, bollinger_bands,
    signal_ema_crossover, signal_rsi_reversion, signal_breakout_bb,
    LOOKBACK_PERIODS,
)

# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def trending_up():
    """Serie con trend rialzista e rumore — 300 candele."""
    np.random.seed(0)
    close = pd.Series(100 + np.cumsum(np.abs(np.random.randn(300)) + 0.3))
    return pd.DataFrame({"close": close})


@pytest.fixture
def trending_down():
    np.random.seed(1)
    close = pd.Series(200 - np.cumsum(np.abs(np.random.randn(300)) + 0.3))
    return pd.DataFrame({"close": close})


@pytest.fixture
def flat():
    close = pd.Series(np.full(300, 150.0))
    return pd.DataFrame({"close": close})


@pytest.fixture
def oscillating():
    """Serie oscillante — utile per RSI e Bollinger."""
    np.random.seed(42)
    close = pd.Series(150 + np.cumsum(np.random.randn(300)))
    return pd.DataFrame({"close": close})


# ── EMA ───────────────────────────────────────────────────────────────

def test_ema_length(trending_up):
    result = ema(trending_up["close"], 20)
    assert len(result) == len(trending_up)


def test_ema_trending_up_last_values(trending_up):
    """Su serie crescente, EMA20 < EMA50 < close agli ultimi 3 indici."""
    e20 = ema(trending_up["close"], 20)
    e50 = ema(trending_up["close"], 50)
    for i in [-1, -2, -3]:
        assert e20.iloc[i] > e50.iloc[i], "EMA veloce deve essere sopra EMA lenta su trend up"
        assert e20.iloc[i] < trending_up["close"].iloc[i]


def test_ema_flat_converges(flat):
    """Su serie piatta, EMA converge al valore costante."""
    result = ema(flat["close"], 20)
    assert abs(result.iloc[-1] - 150.0) < 0.01


# ── RSI ───────────────────────────────────────────────────────────────

def test_rsi_range(oscillating):
    result = rsi(oscillating["close"], 14)
    valid = result.dropna()
    assert (valid >= 0).all() and (valid <= 100).all()


def test_rsi_trending_up_high(trending_up):
    """Su trend forte al rialzo, RSI deve essere > 50 alla fine."""
    result = rsi(trending_up["close"], 14)
    assert result.iloc[-1] > 50


def test_rsi_trending_down_low(trending_down):
    """Su trend forte al ribasso, RSI deve essere < 50 alla fine."""
    result = rsi(trending_down["close"], 14)
    assert result.iloc[-1] < 50


def test_rsi_length(oscillating):
    result = rsi(oscillating["close"], 14)
    assert len(result) == len(oscillating)


# ── Bollinger Bands ───────────────────────────────────────────────────

def test_bollinger_lower_lt_mid_lt_upper(oscillating):
    lower, mid, upper = bollinger_bands(oscillating["close"], 20, 2.0)
    valid = lower.dropna().index
    assert (lower[valid] < mid[valid]).all()
    assert (mid[valid] < upper[valid]).all()


def test_bollinger_length(oscillating):
    lower, mid, upper = bollinger_bands(oscillating["close"], 20, 2.0)
    assert len(lower) == len(mid) == len(upper) == len(oscillating)


def test_bollinger_mid_is_rolling_mean(oscillating):
    _, mid, _ = bollinger_bands(oscillating["close"], 20, 2.0)
    expected = oscillating["close"].rolling(20).mean()
    pd.testing.assert_series_equal(mid, expected)


# ── No look-ahead bias ────────────────────────────────────────────────

def test_signal_ema_no_lookahead(trending_up):
    """Rimuovere l'ultima candela non deve cambiare i segnali precedenti."""
    sig_full = signal_ema_crossover(trending_up, fast=10, slow=50)
    sig_trim = signal_ema_crossover(trending_up.iloc[:-1], fast=10, slow=50)
    pd.testing.assert_series_equal(
        sig_full.iloc[:-1].reset_index(drop=True),
        sig_trim.reset_index(drop=True),
    )


def test_signal_rsi_no_lookahead(oscillating):
    sig_full = signal_rsi_reversion(oscillating, period=14, oversold=30, overbought=70)
    sig_trim = signal_rsi_reversion(oscillating.iloc[:-1], period=14, oversold=30, overbought=70)
    pd.testing.assert_series_equal(
        sig_full.iloc[:-1].reset_index(drop=True),
        sig_trim.reset_index(drop=True),
    )


def test_signal_bb_no_lookahead(oscillating):
    sig_full = signal_breakout_bb(oscillating, period=20, std=2.0)
    sig_trim = signal_breakout_bb(oscillating.iloc[:-1], period=20, std=2.0)
    pd.testing.assert_series_equal(
        sig_full.iloc[:-1].reset_index(drop=True),
        sig_trim.reset_index(drop=True),
    )


# ── Signal values ─────────────────────────────────────────────────────

def test_signal_ema_values_in_set(trending_up):
    sig = signal_ema_crossover(trending_up, fast=10, slow=50)
    assert set(sig.unique()).issubset({-1, 0, 1})


def test_signal_rsi_values_in_set(oscillating):
    sig = signal_rsi_reversion(oscillating, period=14, oversold=30, overbought=70)
    assert set(sig.unique()).issubset({-1, 0, 1})


def test_signal_bb_values_in_set(oscillating):
    sig = signal_breakout_bb(oscillating, period=20, std=2.0)
    assert set(sig.unique()).issubset({-1, 0, 1})


# ── LOOKBACK_PERIODS ──────────────────────────────────────────────────

def test_lookback_periods_defined():
    assert isinstance(LOOKBACK_PERIODS, dict)
    assert "ema_slow" in LOOKBACK_PERIODS
    assert "rsi" in LOOKBACK_PERIODS
    assert "bb" in LOOKBACK_PERIODS
    assert all(v > 0 for v in LOOKBACK_PERIODS.values())
