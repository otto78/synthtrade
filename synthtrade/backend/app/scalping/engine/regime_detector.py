"""RegimeDetector - identifica il regime di mercato con isteresi.

TASK-903: Aggiunta isteresi di K candele per evitare flickering.
Il regime committed cambia SOLO se lo stesso candidato si osserva
per K candele consecutive. Se il candidato cambia prima di K → reset.

L'implementazione predefinita (detect()) usa logica interna semplice.
Il metodo detect_with_core() riutilizza detect_trend() e detect_volatility()
da app/core/indicators.py per un'analisi più sofisticata.
"""

from typing import List, Optional

from app.scalping.models.market import Candle, MarketRegime

# TASK-903: numero di candele consecutive richieste per confermare un cambio regime
REGIME_HYSTERESIS_K = 3


class RegimeDetector:
    """Detects market regime from price action with hysteresis.

    Uses indicators to classify market as:
    - trending_up: Strong uptrend
    - trending_down: Strong downtrend
    - ranging: Sideways market
    - volatile: High volatility, no clear direction

    TASK-903: Regime changes only after K consecutive candles with the same
    candidate regime. Prevents flickering at threshold boundaries.
    """

    def __init__(self, k: int = REGIME_HYSTERESIS_K):
        self._k = k
        self._committed_regime: Optional[str] = None
        self._committed_confidence: float = 0.0
        self._pending_regime: Optional[str] = None
        self._pending_count: int = 0

    @property
    def pending_regime(self) -> Optional[str]:
        """Regime candidato attualmente in fase di conferma (per debug)."""
        return self._pending_regime

    @property
    def pending_count(self) -> int:
        """Numero di candele consecutive con lo stesso candidato."""
        return self._pending_count

    @property
    def committed_regime(self) -> Optional[str]:
        """Ultimo regime confermato (committed)."""
        return self._committed_regime

    def _detect_candidate(
        self,
        candles: List[Candle],
        indicators: Optional[dict] = None,
    ) -> MarketRegime:
        """Rileva il regime candidato (raw, senza isteresi)."""
        if len(candles) < 20:
            if len(candles) >= 5:
                return MarketRegime(regime="ranging", confidence=0.3)
            return MarketRegime(regime="unknown", confidence=0.0)

        ind = indicators or {}

        highs = [float(c.high) for c in candles[-20:]]
        lows = [float(c.low) for c in candles[-20:]]
        closes = [float(c.close) for c in candles[-20:]]

        price_change = (closes[-1] - closes[0]) / closes[0] if closes[0] > 0 else 0

        atr = sum(highs[i] - lows[i] for i in range(-14, 0)) / 14
        volatility_ratio = atr / closes[-1] if closes[-1] > 0 else 0

        if volatility_ratio > 0.01:
            regime = "volatile"
            confidence = 0.7
        elif price_change > 0.003:
            regime = "trending_up"
            confidence = 0.85
        elif price_change < -0.003:
            regime = "trending_down"
            confidence = 0.85
        else:
            regime = "ranging"
            confidence = 0.6

        return MarketRegime(regime=regime, confidence=confidence)

    def detect(
        self,
        candles: List[Candle],
        indicators: Optional[dict] = None,
    ) -> MarketRegime:
        """Detect market regime con isteresi.

        Il regime committed cambia solo se lo stesso candidato viene
        rilevato per K candele consecutive.
        """
        candidate = self._detect_candidate(candles, indicators)
        candidate_regime = candidate.regime

        # Prima chiamata → commit immediato
        if self._committed_regime is None:
            self._committed_regime = candidate_regime
            self._committed_confidence = candidate.confidence
            self._pending_regime = None
            self._pending_count = 0
            return candidate

        # Candidato uguale al committed → reset pending (tutto stabile)
        if candidate_regime == self._committed_regime:
            self._pending_regime = None
            self._pending_count = 0
            return MarketRegime(
                regime=self._committed_regime,
                confidence=self._committed_confidence,
            )

        # Candidato uguale al pending → incrementa counter
        if candidate_regime == self._pending_regime:
            self._pending_count += 1
        else:
            # Nuovo candidato → reset counter
            self._pending_regime = candidate_regime
            self._pending_count = 1

        # Contatore raggiunto K → commit
        if self._pending_count >= self._k:
            self._committed_regime = candidate_regime
            self._committed_confidence = candidate.confidence
            self._pending_regime = None
            self._pending_count = 0
            return MarketRegime(
                regime=candidate_regime,
                confidence=candidate.confidence,
            )

        # Non ancora confermato → restituisci il committed
        return MarketRegime(
            regime=self._committed_regime,
            confidence=self._committed_confidence,
        )

    def detect_with_core(
        self,
        candles: List[Candle],
    ) -> MarketRegime:
        """Detect regime usando app/core/indicators.py.

        Metodo aggiuntivo che riutilizza detect_trend() e detect_volatility()
        dal core. Non sostituisce detect() per retrocompatibilità.
        Nota: questo metodo NON usa l'isteresi (stateless come prima).
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

        if vol_pct > 2.0:
            return MarketRegime(regime="volatile", confidence=0.7)

        mapped_regime = regime_map.get(trend, "ranging")
        confidence = 0.85 if mapped_regime in ("trending_up", "trending_down") else 0.6

        return MarketRegime(regime=mapped_regime, confidence=confidence)
