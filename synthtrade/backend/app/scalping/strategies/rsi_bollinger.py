"""RSI + Bollinger Bands Strategy - filtro timing per mean reversion."""

from typing import List, Optional

from app.scalping.models.market import Candle
from app.scalping.strategies.base import AbstractScalpingStrategy
from app.scalping.engine.signal_aggregator import TechnicalSignal


class RSIBollingerStrategy(AbstractScalpingStrategy):
    """Strategia RSI + Bollinger Bands per mean reversion.

    Segnale BUY quando RSI < 30 (ipervenduto) e prezzo tocca BB bassa.
    Segnale SELL quando RSI > 70 (ipersubito) e prezzo tocca BB alta.
    """

    @property
    def name(self) -> str:
        return "rsi_bollinger"

    def evaluate(
        self,
        candles: List[Candle],
        indicators: Optional[dict] = None,
    ) -> TechnicalSignal:
        """Valuta RSI e BB per segnale di timing."""
        if len(candles) < 20:
            return TechnicalSignal(type="NONE", confidence=0.0)

        ind = indicators or self.calculate_indicators(candles)

        rsi = ind.get("rsi", 50)
        close = ind.get("close", 0)
        bb_lower = ind.get("bb_lower", 0)
        bb_upper = ind.get("bb_upper", 0)

        # Oversold: RSI < 30 e prezzo vicino BB bassa
        if rsi < 30 and close <= bb_lower * 1.01:
            return TechnicalSignal(
                type="BUY",
                confidence=0.8,
                source=self.name,
            )

        # Overbought: RSI > 70 e prezzo vicino BB alta
        if rsi > 70 and close >= bb_upper * 0.99:
            return TechnicalSignal(
                type="SELL",
                confidence=0.8,
                source=self.name,
            )

        return TechnicalSignal(type="NONE", confidence=0.0)