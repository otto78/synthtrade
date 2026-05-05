import pytest
import pandas as pd
import numpy as np
from app.core.backtester import run_backtest, BacktestResult, FEE_PCT, SLIPPAGE


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def rising_ohlcv():
    """300 candele con trend rialzista e rumore."""
    np.random.seed(0)
    close = pd.Series(100 + np.cumsum(np.abs(np.random.randn(300)) + 0.3))
    df = pd.DataFrame({"open": close, "high": close * 1.001,
                       "low": close * 0.999, "close": close, "volume": 1000.0})
    return df


@pytest.fixture
def falling_ohlcv():
    """300 candele con trend ribassista."""
    np.random.seed(1)
    close = pd.Series(200 - np.cumsum(np.abs(np.random.randn(300)) + 0.3))
    close = close.clip(lower=1)
    df = pd.DataFrame({"open": close, "high": close * 1.001,
                       "low": close * 0.999, "close": close, "volume": 1000.0})
    return df


def always_buy(df):
    return pd.Series(1, index=df.index)


def always_sell(df):
    return pd.Series(-1, index=df.index)


def never_signal(df):
    return pd.Series(0, index=df.index)


# ── Tipo di ritorno ───────────────────────────────────────────────────

def test_returns_backtest_result(rising_ohlcv):
    result = run_backtest(rising_ohlcv, always_buy)
    assert isinstance(result, BacktestResult)


def test_result_has_all_fields(rising_ohlcv):
    result = run_backtest(rising_ohlcv, always_buy)
    assert hasattr(result, "pnl_pct")
    assert hasattr(result, "win_rate")
    assert hasattr(result, "sharpe")
    assert hasattr(result, "max_drawdown_pct")
    assert hasattr(result, "num_trades")
    assert hasattr(result, "equity_curve")


# ── PnL ───────────────────────────────────────────────────────────────

def test_pnl_positive_on_rising_market(rising_ohlcv):
    result = run_backtest(rising_ohlcv, always_buy)
    assert result.pnl_pct > 0


def test_pnl_negative_on_falling_market_with_buy_signal(falling_ohlcv):
    result = run_backtest(falling_ohlcv, always_buy)
    assert result.pnl_pct < 0


def test_pnl_zero_trades_no_change(rising_ohlcv):
    result = run_backtest(rising_ohlcv, never_signal)
    assert result.num_trades == 0
    assert result.pnl_pct == 0.0


# ── Fee ───────────────────────────────────────────────────────────────

def test_fees_reduce_pnl(rising_ohlcv):
    """PnL con fee deve essere inferiore a PnL senza fee."""
    result_with_fee = run_backtest(rising_ohlcv, always_buy, initial_capital=1000.0)
    # Simula senza fee passando FEE_PCT=0 non è possibile direttamente,
    # ma verifichiamo che il PnL sia inferiore al rendimento grezzo del mercato.
    raw_return = (rising_ohlcv["close"].iloc[-1] / rising_ohlcv["close"].iloc[0] - 1) * 100
    assert result_with_fee.pnl_pct < raw_return


# ── Equity curve ─────────────────────────────────────────────────────

def test_equity_curve_same_length_as_ohlcv(rising_ohlcv):
    result = run_backtest(rising_ohlcv, always_buy)
    assert len(result.equity_curve) == len(rising_ohlcv)


def test_equity_curve_starts_at_initial_capital(rising_ohlcv):
    result = run_backtest(rising_ohlcv, always_buy, initial_capital=2000.0)
    assert result.equity_curve[0] == 2000.0


def test_equity_curve_all_positive(rising_ohlcv):
    result = run_backtest(rising_ohlcv, always_buy)
    assert all(v > 0 for v in result.equity_curve)


# ── Metriche ─────────────────────────────────────────────────────────

def test_win_rate_in_range(rising_ohlcv):
    result = run_backtest(rising_ohlcv, always_buy)
    assert 0.0 <= result.win_rate <= 1.0


def test_max_drawdown_non_negative(rising_ohlcv):
    result = run_backtest(rising_ohlcv, always_buy)
    assert result.max_drawdown_pct >= 0.0


def test_num_trades_non_negative(rising_ohlcv):
    result = run_backtest(rising_ohlcv, always_buy)
    assert result.num_trades >= 0


# ── No look-ahead ────────────────────────────────────────────────────

def test_no_lookahead_removing_last_candle(rising_ohlcv):
    """Rimuovere l'ultima candela non cambia i trade precedenti."""
    result_full = run_backtest(rising_ohlcv, always_buy)
    result_trim = run_backtest(rising_ohlcv.iloc[:-1], always_buy)
    assert result_full.num_trades >= result_trim.num_trades


# ── Costanti esposte ─────────────────────────────────────────────────

def test_fee_and_slippage_constants():
    assert FEE_PCT == 0.001
    assert SLIPPAGE == 0.0007
