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
        """Valuta lo stato EMA per generare segnale di trend.
        
        Ritorna BUY se EMA veloce > EMA lenta (trend rialzista persistente).
        Ritorna SELL se EMA veloce < EMA lenta (trend ribassista persistente).
        """
        if len(candles) < 21:
            return TechnicalSignal(type="NONE", confidence=0.0)

        ind = indicators or self.calculate_indicators(candles)

        ema_fast = ind.get("ema_fast", 0)
        ema_slow = ind.get("ema_slow", 0)

        # Stato Trend Rialzista
        if ema_fast > ema_slow:
            return TechnicalSignal(
                type="BUY",
                confidence=0.75, # Confidenza leggermente ridotta perche' segnale di stato
                source=self.name,
            )

        # Stato Trend Ribassista
        if ema_fast < ema_slow:
            return TechnicalSignal(
                type="SELL",
                confidence=0.75,
                source=self.name,
            )

        return TechnicalSignal(type="NONE", confidence=0.0)