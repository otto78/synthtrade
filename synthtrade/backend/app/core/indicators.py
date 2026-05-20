import pandas as pd

LOOKBACK_PERIODS = {
    "ema_slow": 200,
    "rsi": 21,
    "bb": 30,
}


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    # loss=0 significa nessuna perdita nel periodo → RSI=100
    result = pd.Series(index=series.index, dtype=float)
    no_loss = loss == 0
    result[no_loss] = 100.0
    has_loss = ~no_loss & loss.notna()
    rs = gain[has_loss] / loss[has_loss]
    result[has_loss] = 100 - (100 / (1 + rs))
    return result


def bollinger_bands(series: pd.Series, period: int = 20, std: float = 2.0):
    mid = series.rolling(period).mean()
    sigma = series.rolling(period).std()
    return mid - std * sigma, mid, mid + std * sigma


def signal_ema_crossover(df: pd.DataFrame, fast: int, slow: int) -> pd.Series:
    ema_f = ema(df["close"], fast).shift(1)
    ema_s = ema(df["close"], slow).shift(1)
    sig = pd.Series(0, index=df.index)
    sig[ema_f > ema_s] = 1
    sig[ema_f < ema_s] = -1
    return sig


def signal_rsi_reversion(df: pd.DataFrame, period: int, oversold: int, overbought: int) -> pd.Series:
    r = rsi(df["close"], period).shift(1)
    sig = pd.Series(0, index=df.index)
    sig[r < oversold] = 1
    sig[r > overbought] = -1
    return sig


def signal_breakout_bb(df: pd.DataFrame, period: int, std: float) -> pd.Series:
    lower, _, upper = bollinger_bands(df["close"], period, std)
    prev_close = df["close"].shift(1)
    sig = pd.Series(0, index=df.index)
    sig[prev_close > upper.shift(1)] = 1
    sig[prev_close < lower.shift(1)] = -1
    return sig


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.Series:
    """Calcola il segnale MACD: 1 quando MACD > signal line, -1 quando < ."""
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    sig = pd.Series(0, index=series.index)
    sig[macd_line > signal_line] = 1
    sig[macd_line < signal_line] = -1
    return sig.shift(1)


def signal_macd_crossover(df: pd.DataFrame, macd_fast: int, macd_slow: int, macd_signal: int) -> pd.Series:
    """Segnale basato sull'incrocio MACD."""
    return macd(df["close"], macd_fast, macd_slow, macd_signal)


def signal_ema_dual_crossover(df: pd.DataFrame, ema_short: int, ema_long: int) -> pd.Series:
    """EMA crossover generico per scalping e trend veloci."""
    ema_f = ema(df["close"], ema_short).shift(1)
    ema_s = ema(df["close"], ema_long).shift(1)
    sig = pd.Series(0, index=df.index)
    sig[ema_f > ema_s] = 1
    sig[ema_f < ema_s] = -1
    return sig
