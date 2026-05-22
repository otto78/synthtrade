import numpy as np
import pandas as pd

LOOKBACK_PERIODS = {
    "ema_slow": 200,
    "rsi": 21,
    "bb": 30,
}


def ema(series: pd.Series, period: int) -> pd.Series:
    result = series.ewm(span=period, adjust=False).mean()
    return result if isinstance(result, pd.Series) else result.iloc[:, 0]


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


def bollinger_bands(series: pd.Series, period: int = 20, std: float = 2.0) -> tuple[pd.Series, pd.Series, pd.Series]:
    mid = series.rolling(period).mean()
    sigma = series.rolling(period).std()
    return mid - std * sigma, mid, mid + std * sigma


def signal_ema_crossover(df: pd.DataFrame, fast: int, slow: int) -> pd.Series:
    close = df["close"]
    ema_f: pd.Series = ema(close, fast).shift(1)
    ema_s: pd.Series = ema(close, slow).shift(1)
    sig = pd.Series(0, index=df.index)
    sig[ema_f > ema_s] = 1
    sig[ema_f < ema_s] = -1
    return sig


def signal_rsi_reversion(df: pd.DataFrame, period: int, oversold: int, overbought: int) -> pd.Series:
    close = df["close"]
    r: pd.Series = rsi(close, period).shift(1)
    sig = pd.Series(0, index=df.index)
    sig[r < oversold] = 1
    sig[r > overbought] = -1
    return sig


def signal_breakout_bb(df: pd.DataFrame, period: int, std: float) -> pd.Series:
    close = df["close"]
    lower, _, upper = bollinger_bands(close, period, std)
    prev_close = close.shift(1)
    sig = pd.Series(0, index=df.index)
    sig[prev_close > upper.shift(1)] = 1
    sig[prev_close < lower.shift(1)] = -1
    return sig


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.Series:
    """Calcola il segnale MACD: 1 quando MACD > signal line, -1 quando < ."""
    ema_fast: pd.Series = ema(series, fast)
    ema_slow: pd.Series = ema(series, slow)
    macd_line: pd.Series = ema_fast - ema_slow
    signal_line: pd.Series = ema(macd_line, signal)
    sig = pd.Series(0, index=series.index)
    sig[macd_line > signal_line] = 1
    sig[macd_line < signal_line] = -1
    return sig.shift(1)


def signal_macd_crossover(df: pd.DataFrame, macd_fast: int, macd_slow: int, macd_signal: int) -> pd.Series:
    """Segnale basato sull'incrocio MACD."""
    close = df["close"]
    return macd(close, macd_fast, macd_slow, macd_signal)


def signal_ema_dual_crossover(df: pd.DataFrame, ema_short: int, ema_long: int) -> pd.Series:
    """EMA crossover generico per scalping e trend veloci."""
    close = df["close"]
    ema_f: pd.Series = ema(close, ema_short).shift(1)
    ema_s: pd.Series = ema(close, ema_long).shift(1)
    sig = pd.Series(0, index=df.index)
    sig[ema_f > ema_s] = 1
    sig[ema_f < ema_s] = -1
    return sig


# ── VWAP: Volume Weighted Average Price ─────────────────────────────────


def vwap(df: pd.DataFrame) -> pd.Series:
    """Calcola il VWAP cumulativo (Volume Weighted Average Price).

    VWAP = sum(close * volume) / sum(volume) per ogni riga cumulativamente.
    Il VWAP è un indicatore di prezzo medio ponderato per il volume,
    usato come filtro di timing nello scalping: sopra VWAP = trend rialzista,
    sotto VWAP = trend ribassista.

    Args:
        df: DataFrame con colonne 'close', 'volume' (e opzionalmente 'high', 'low').

    Returns:
        pd.Series con il VWAP per ogni riga.
    """
    close: pd.Series = df["close"]
    volume: pd.Series = df["volume"]
    cum_pv: pd.Series = (close * volume).cumsum()
    cum_vol: pd.Series = volume.cumsum()
    # Evita divisione per zero
    return cum_pv / cum_vol.replace(0, pd.NA)


# ── ADX: Average Directional Index ──────────────────────────────────────


def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """Calcola il True Range per ogni riga."""
    prev_close = close.shift(1)
    tr: pd.Series = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr


def _directional_movement(
    high: pd.Series, low: pd.Series,
    period: int = 14,
) -> tuple[pd.Series, pd.Series]:
    """Calcola +DM e -DM smoothed."""
    prev_high = high.shift(1)
    prev_low = low.shift(1)
    up_move: pd.Series = high - prev_high
    down_move: pd.Series = prev_low - low

    plus_dm = pd.Series(0.0, index=high.index)
    minus_dm = pd.Series(0.0, index=high.index)

    # +DM quando up > down e up > 0
    up_gt_down = up_move > down_move
    up_gt_zero = up_move > 0
    plus_dm[up_gt_down & up_gt_zero] = up_move[up_gt_down & up_gt_zero]

    # -DM quando down > up e down > 0
    down_gt_up = down_move > up_move
    down_gt_zero = down_move > 0
    minus_dm[down_gt_up & down_gt_zero] = down_move[down_gt_up & down_gt_zero]

    # Smoothing con Wilder's method (EMA-like)
    # Prima media semplice, poi smoothing
    plus_dm_smooth: pd.Series = plus_dm.rolling(period).mean()
    minus_dm_smooth: pd.Series = minus_dm.rolling(period).mean()

    # Wilder smoothing
    alpha = 1 / period
    for i in range(period, len(plus_dm_smooth)):
        plus_dm_smooth.iloc[i] = (
            plus_dm_smooth.iloc[i - 1]
            + alpha * (plus_dm.iloc[i] - plus_dm_smooth.iloc[i - 1])
        )
        minus_dm_smooth.iloc[i] = (
            minus_dm_smooth.iloc[i - 1]
            + alpha * (minus_dm.iloc[i] - minus_dm_smooth.iloc[i - 1])
        )

    return plus_dm_smooth, minus_dm_smooth


def adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calcola l'Average Directional Index (ADX) per la forza del trend.

    ADX valuta la forza del trend indipendentemente dalla direzione.
    Valori > 25 indicano trend forte, < 20 mercato ranging.

    Args:
        df: DataFrame con colonne 'high', 'low', 'close'.
        period: Periodo di lookback (default 14).

    Returns:
        pd.Series con ADX (range 0-100).
    """
    high: pd.Series = df["high"]
    low: pd.Series = df["low"]
    close: pd.Series = df["close"]

    # True Range smoothing (ATR-like)
    tr: pd.Series = _true_range(high, low, close)
    atr: pd.Series = tr.rolling(period).mean()

    # +DI e -DI
    plus_dm, minus_dm = _directional_movement(high, low, period)

    # +DI e -DI normalizzati su ATR
    plus_di: pd.Series = 100 * plus_dm / atr.replace(0, pd.NA)
    minus_di: pd.Series = 100 * minus_dm / atr.replace(0, pd.NA)

    # DX = |+DI - -DI| / (+DI + -DI) * 100
    di_diff: pd.Series = (plus_di - minus_di).abs()
    di_sum: pd.Series = (plus_di + minus_di).replace(0, pd.NA)
    dx: pd.Series = 100 * di_diff / di_sum

    # ADX = media mobile di DX
    adx_series: pd.Series = dx.rolling(period).mean()

    return adx_series


# ── Regime Detection ────────────────────────────────────────────────────


def detect_trend(df: pd.DataFrame, period: int = 20) -> str:
    """Rileva il trend di mercato usando la pendenza della regressione lineare.

    Usa la pendenza di una regressione lineare sui prezzi di chiusura
    per determinare se il mercato è uptrend, downtrend o ranging.

    Args:
        df: DataFrame con colonna 'close'.
        period: Periodo di lookback per la regressione.

    Returns:
        'uptrend', 'downtrend', 'ranging', o 'insufficient_data'.
    """
    if len(df) < period:
        return "insufficient_data"

    closes = df["close"].iloc[-period:].to_numpy()
    x = np.arange(len(closes))

    # Regressione lineare via polyfit
    coeffs: np.ndarray = np.polyfit(x, closes, 1)
    slope: float = float(coeffs[0])

    # Pendenza normalizzata come % del prezzo medio
    slope_pct: float = slope / float(np.mean(closes)) * 100

    if slope_pct > 0.05:
        return "uptrend"
    elif slope_pct < -0.05:
        return "downtrend"
    else:
        return "ranging"


def detect_volatility(df: pd.DataFrame, period: int = 20) -> float:
    """Calcola la volatilità come ATR normalizzato sul prezzo.

    ATR (Average True Range) diviso per il prezzo medio,
    normalizzato come percentuale.

    Args:
        df: DataFrame con colonne 'high', 'low', 'close'.
        period: Periodo di lookback (default 20).

    Returns:
        Volatilità normalizzata (float, 0+).
    """
    if len(df) < 2:
        return 0.0

    high: pd.Series = df["high"]
    low: pd.Series = df["low"]
    close: pd.Series = df["close"]

    tr: pd.Series = _true_range(high, low, close)
    atr: pd.Series = tr.rolling(period).mean()
    avg_price: pd.Series = close.rolling(period).mean()

    # Volatilità normalizzata come ATR% / prezzo
    vol: pd.Series = (atr / avg_price.replace(0, pd.NA)).dropna()
    if len(vol) == 0:
        return 0.0

    return float(vol.iloc[-1]) * 100