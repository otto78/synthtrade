import pandas as pd
import numpy as np
from app.ai.schemas import MarketContext, OhlcvSummary
from app.config import settings


def build_ohlcv_summary(df: pd.DataFrame, symbol: str, timeframe: str,
                         min_candles: int = 20) -> OhlcvSummary:
    if df.empty:
        raise ValueError("DataFrame candles vuoto")
    if len(df) < min_candles:
        raise ValueError(f"Candles insufficienti: {len(df)} < minimo {min_candles}")

    close = df["close"]
    atr = (df["high"] - df["low"]).mean() if "high" in df.columns else close.std()
    trend_pct = (close.iloc[-1] - close.iloc[0]) / close.iloc[0] * 100

    return OhlcvSummary(
        symbol=symbol,
        timeframe=timeframe,
        candles=len(df),
        price_min=float(close.min()),
        price_max=float(close.max()),
        price_last=float(close.iloc[-1]),
        volume_avg=float(df["volume"].mean()) if "volume" in df.columns else 0.0,
        volatility_pct=float(atr / close.mean() * 100),
        trend_pct=float(trend_pct),
    )


def detect_market_regime(df: pd.DataFrame, 
                        volatile_threshold: float = settings.MARKET_REGIME_VOLATILE_THRESHOLD,
                        trending_threshold: float = settings.MARKET_REGIME_TRENDING_THRESHOLD) -> str:
    close = df["close"]
    atr = (df["high"] - df["low"]).mean() if "high" in df.columns else close.std()
    atr_ratio = atr / close.mean()

    if atr_ratio > volatile_threshold:
        # Controlla se c'è anche trend
        x = np.arange(len(close))
        slope, _ = np.polyfit(x, close.values, 1)
        r2 = np.corrcoef(x, close.values)[0, 1] ** 2
        if r2 > trending_threshold:
            return "trending"
        return "volatile"

    # Bassa volatilità — controlla trend
    x = np.arange(len(close))
    r2 = np.corrcoef(x, close.values)[0, 1] ** 2
    if r2 > trending_threshold:
        return "trending"
    return "ranging"


def build_market_context(df: pd.DataFrame, symbol: str, timeframe: str) -> MarketContext:
    summary = build_ohlcv_summary(df, symbol, timeframe)
    regime = detect_market_regime(df)
    return MarketContext(symbol=symbol, timeframe=timeframe,
                         regime=regime, summary=summary)
