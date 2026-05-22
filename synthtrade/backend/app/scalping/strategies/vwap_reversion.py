"""VWAP Reversion Strategy - filtro timing per mean reversion contro VWAP."""

from typing import List, Optional

from app.scalping.models.market import Candle
from app.scalping.strategies.base import AbstractScalpingStrategy
from app.scalping.engine.signal_aggregator import TechnicalSignal


class VWAPReversionStrategy(AbstractScalpingStrategy):
    """Strategia VWAP Reversion.

    Segnale BUY quando prezzo > VWAP (trend up).
    Segnale SELL quando prezzo < VWAP (trend down).
    Come filtro timing, non segnale primario.
    """

    @property
    def name(self) -> str:
        return "vwap_reversion"

    def evaluate(
        self,
        candles: List[Candle],
        indicators: Optional[dict] = None,
    ) -> TechnicalSignal:
        """Valuta posizione rispetto a VWAP."""
        if len(candles) < 5:
            return TechnicalSignal(type="NONE", confidence=0.0)

        vwap = self._calculate_vwap(candles)
        close = float(candles[-1].close)

        # Calcola distanza percentuale dal VWAP
        distance = (close - vwap) / vwap if vwap > 0 else 0

        # Price above VWAP (bullish bias)
        if distance > 0.002:  # 0.2% sopra VWAP
            return TechnicalSignal(
                type="BUY",
                confidence=0.7,
                source=self.name,
            )

        # Price below VWAP (bearish bias)
        if distance < -0.002:  # 0.2% sotto VWAP
            return TechnicalSignal(
                type="SELL",
                confidence=0.7,
                source=self.name,
            )

        return TechnicalSignal(type="NONE", confidence=0.0)

    def _calculate_vwap(self, candles: List[Candle]) -> float:
        """Calcola VWAP delle ultime candele."""
        if not candles:
            return 0.0

        total_volume = 0.0
        total_price_volume = 0.0

        for c in candles[-20:]:  # VWAP delle ultime 20 candele
            typical_price = float((c.high + c.low + c.close) / 3)
            volume = float(c.volume)
            total_price_volume += typical_price * volume
            total_volume += volume

        return total_price_volume / total_volume if total_volume > 0 else 0.0