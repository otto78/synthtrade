"""MomentumBaseStrategy — strategia semplice prezzo vs EMA20.

Genera segnali piu' frequenti delle altre strategie:
- Prezzo > EMA20 + margine 0.1% → BUY (confidence 0.5)
- Prezzo < EMA20 - margine 0.1% → SELL (confidence 0.5)

Utile come fallback per far partire i trade in attesa
che condizioni ideali si presentino (v2.0 architecture).
"""

import logging
from typing import List, Optional

from app.scalping.strategies.base import AbstractScalpingStrategy
from app.scalping.models.market import Candle
from app.scalping.engine.signal_aggregator import TechnicalSignal

logger = logging.getLogger(__name__)


class MomentumBaseStrategy(AbstractScalpingStrategy):
    """Strategia momentum base: prezzo vs EMA20."""

    @property
    def name(self) -> str:
        return "momentum_base"

    def evaluate(
        self,
        candles: List[Candle],
        indicators: Optional[dict] = None,
    ) -> TechnicalSignal:
        if not candles:
            return TechnicalSignal(type="NONE", confidence=0.0, source=self.name)

        if indicators and "close" in indicators and "ema_fast" in indicators:
            close = indicators["close"]
            ema = indicators["ema_fast"]  # EMA9, reattiva
        else:
            closes = [float(c.close) for c in candles]
            if len(closes) < 2:
                return TechnicalSignal(type="NONE", confidence=0.0, source=self.name)
            close = closes[-1]
            # Calcola EMA9 semplice
            period = 9
            if len(closes) < period:
                return TechnicalSignal(type="NONE", confidence=0.0, source=self.name)
            multiplier = 2 / (period + 1)
            ema = sum(closes[:period]) / period
            for i in range(period, len(closes)):
                ema = closes[i] * multiplier + ema * (1 - multiplier)

        margin = close * 0.0001  # 0.01% margine (ultra-sensitive per più segnali in ranging)

        logger.debug(f"Momentum eval: close={close:.2f} ema={ema:.2f} margin={margin:.4f} diff={close-ema:.4f}")

        if close > ema + margin:
            return TechnicalSignal(
                type="BUY",
                confidence=0.7,  # Aumentato da 0.5 per passare combined confidence check
                source=self.name,
            )
        elif close < ema - margin:
            return TechnicalSignal(
                type="SELL",
                confidence=0.7,  # Aumentato da 0.5 per passare combined confidence check
                source=self.name,
            )

        logger.debug(f"Momentum signal NONE: price within margin band")
        return TechnicalSignal(type="NONE", confidence=0.0, source=self.name)
