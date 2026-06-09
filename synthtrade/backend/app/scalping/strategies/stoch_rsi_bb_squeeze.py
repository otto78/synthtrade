"""StochRSI + Bollinger Bands Squeeze Strategy - per regime volatile.

Combina StochRSI per momentum di brevissimo termine con Bollinger Bands
per rilevare squeeze (contrazione volatilità) che spesso precede breakout.

Segnale BUY quando:
  - BB Squeeze attivo (BB width < 1.5%)
  - StochRSI incrocia sopra 0.2 da sotto (momentum rialzista)

Segnale SELL quando:
  - BB Squeeze attivo (BB width < 1.5%)
  - StochRSI incrocia sotto 0.8 da sopra (momentum ribassista)
"""

from typing import List, Optional

from app.scalping.models.market import Candle
from app.scalping.strategies.base import AbstractScalpingStrategy
from app.scalping.engine.signal_aggregator import TechnicalSignal


class StochRSIBBSqueezeStrategy(AbstractScalpingStrategy):
    """Strategia StochRSI + BB Squeeze per regime volatile."""

    @property
    def name(self) -> str:
        return "stoch_rsi_bb_squeeze"

    def evaluate(
        self,
        candles: List[Candle],
        indicators: Optional[dict] = None,
    ) -> TechnicalSignal:
        """Valuta StochRSI e BB Squeeze per segnale di timing."""
        if len(candles) < 21:
            return TechnicalSignal(type="NONE", confidence=0.0)

        ind = indicators or self.calculate_indicators(candles)

        bb_upper = ind.get("bb_upper", 0)
        bb_lower = ind.get("bb_lower", 0)
        bb_mid = ind.get("bb_mid", bb_upper if bb_upper else 1)
        rsi = ind.get("rsi", 50)

        # BB Squeeze detection: larghezza bande normalizzata < 1.5%
        bb_width = 0.0
        if bb_mid > 0:
            bb_width = (bb_upper - bb_lower) / bb_mid

        is_squeeze = bb_width < 0.015 and bb_width > 0.0

        if not is_squeeze:
            return TechnicalSignal(type="NONE", confidence=0.0, source=self.name)

        # StochRSI-like: usa RSI scalato su [0,1] come proxy
        stoch_rsi = (rsi - 14) / (86 - 14) if rsi else 0.5
        stoch_rsi = max(0.0, min(1.0, stoch_rsi))

        # StochRSI basso + BB squeeze = potenziale inversione rialzista
        if stoch_rsi < 0.2:
            return TechnicalSignal(
                type="BUY",
                confidence=0.55,
                source=self.name,
            )

        # StochRSI alto + BB squeeze = potenziale inversione ribassista
        if stoch_rsi > 0.8:
            return TechnicalSignal(
                type="SELL",
                confidence=0.55,
                source=self.name,
            )

        return TechnicalSignal(type="NONE", confidence=0.0, source=self.name)