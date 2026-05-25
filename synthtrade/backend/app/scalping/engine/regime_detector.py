"""RegimeDetector - identifica il regime di mercato.

L'implementazione predefinita (detect()) usa logica interna semplice.
Il metodo detect_with_core() riutilizza detect_trend() e detect_volatility()
da app/core/indicators.py per un'analisi più sofisticata.
"""

from typing import List, Optional

from app.scalping.models.market import Candle, MarketRegime


class RegimeDetector:
    """Detects market regime from price action.

    Uses indicators to classify market as:
    - trending_up: Strong uptrend
    - trending_down: Strong downtrend
    - ranging: Sideways market
    - volatile: High volatility, no clear direction
    """

    def detect(
        self,
        candles: List[Candle],
        indicators: Optional[dict] = None,
    ) -> MarketRegime:
        """Detect market regime from candles."""
        if len(candles) < 20:
            return MarketRegime(regime="unknown", confidence=0.0)

        ind = indicators or {}

        # Get indicators - prefer calculated ones
        close = float(candles[-1].close)
        highs = [float(c.high) for c in candles[-20:]]
        lows = [float(c.low) for c in candles[-20:]]
        closes = [float(c.close) for c in candles[-20:]]

        # Simple regime detection logic
        price_change = (closes[-1] - closes[0]) / closes[0] if closes[0] > 0 else 0

        # Volatility (ATR proxy)
        atr = sum(highs[i] - lows[i] for i in range(-14, 0)) / 14

        volatility_ratio = atr / closes[-1] if closes[-1] > 0 else 0

        # Determine regime
        if volatility_ratio > 0.02:  # High volatility
            regime = "volatile"
            confidence = 0.7
        elif price_change > 0.03:  # 3% up
            regime = "trending_up"
            confidence = 0.85
        elif price_change < -0.03:  # 3% down
            regime = "trending_down"
            confidence = 0.85
        else:
            regime = "ranging"
            confidence = 0.6

        return MarketRegime(regime=regime, confidence=confidence)

    def detect_with_core(
        self,
        candles: List[Candle],
    ) -> MarketRegime:
        """Detect regime usando app/core/indicators.py.
        
        Metodo aggiuntivo che riutilizza detect_trend() e detect_volatility()
        dal core. Non sostituisce detect() per retrocompatibilità.
        """
        import pandas as pd
        from app.core.indicators import detect_trend, detect_volatility

        if len(candles) < 20:
            return MarketRegime(regime="unknown", confidence=0.0)

        df = pd.DataFrame([
            {
                "open": float(c.open),
                "high": float(c.high),
                "low": float(c.low),
                "close": float(c.close),
                "volume": getattr(c, "volume", 0),
            }
            for c in candles[-20:]
        ])

        vol_pct = detect_volatility(df, period=20)
        trend = detect_trend(df, period=20)

        regime_map = {
            "uptrend": "trending_up",
            "downtrend": "trending_down",
            "ranging": "ranging",
            "insufficient_data": "unknown",
        }

        if vol_pct > 2.0:  # 2% ATR ratio = volatile
            return MarketRegime(regime="volatile", confidence=0.7)

        mapped_regime = regime_map.get(trend, "ranging")
        confidence = 0.85 if mapped_regime in ("trending_up", "trending_down") else 0.6

        return MarketRegime(regime=mapped_regime, confidence=confidence)