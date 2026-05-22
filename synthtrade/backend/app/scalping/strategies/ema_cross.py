"""EMA Cross Strategy - filtro timing per trend following."""

from typing import List, Optional

from app.scalping.models.market import Candle
from app.scalping.strategies.base import AbstractScalpingStrategy
from app.scalping.engine.signal_aggregator import TechnicalSignal


class EMACrossStrategy(AbstractScalpingStrategy):
    """Strategia EMA 9/21 cross.

    Segnale BUY quando EMA9 incrocia sopra EMA21 (trend up).
    Segnale SELL quando EMA9 incrocia sotto EMA21 (trend down).
    Usato come filtro timing, non segnale primario.
    """

    @property
    def name(self) -> str:
        return "ema_cross"

    def evaluate(
        self,
        candles: List[Candle],
        indicators: Optional[dict] = None,
    ) -> TechnicalSignal:
        """Valuta incrocio EMA per generare segnale di timing."""
        if len(candles) < 21:
            return TechnicalSignal(type="NONE", confidence=0.0)

        ind = indicators or self.calculate_indicators(candles)

        ema_fast = ind.get("ema_fast", 0)
        ema_slow = ind.get("ema_slow", 0)
        ema_fast_prev = ind.get("ema_fast_prev", 0)
        ema_slow_prev = ind.get("ema_slow_prev", 0)

        # EMA 9/21 Bullish cross
        if ema_fast_prev <= ema_slow_prev and ema_fast > ema_slow:
            return TechnicalSignal(
                type="BUY",
                confidence=0.85,
                source=self.name,
            )

        # EMA 9/21 Bearish cross
        if ema_fast_prev >= ema_slow_prev and ema_fast < ema_slow:
            return TechnicalSignal(
                type="SELL",
                confidence=0.85,
                source=self.name,
            )

        return TechnicalSignal(type="NONE", confidence=0.0)