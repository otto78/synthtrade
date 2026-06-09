"""StochRSI + BB Squeeze Strategy — cattura breakout da volatilità imminente.

Stoch RSI è più reattivo del RSI classico (calcola RSI del RSI).
BB Squeeze rileva quando la larghezza delle Bollinger Bands è inferiore
alla media storica, indicando contrazione che precede un'espansione.

Segnale BUY: StochRSI < 0.20 (ipervenduto) + BB Squeeze attivo
Segnale SELL: StochRSI > 0.80 (ipercomprato) + BB Squeeze attivo

Adatta per regime volatile: cattura l'inizio di movimenti esplosivi.
"""

import logging
from typing import List, Optional

from app.scalping.models.market import Candle
from app.scalping.strategies.base import AbstractScalpingStrategy, _std_dev
from app.scalping.engine.signal_aggregator import TechnicalSignal

logger = logging.getLogger(__name__)

# Soglie StochRSI
STOCH_RSI_OVERSOLD = 0.20
STOCH_RSI_OVERBOUGHT = 0.80

# Periodi
RSI_PERIOD = 14
STOCH_PERIOD = 14
BB_PERIOD = 20
BB_STD_DEV = 2.0
BB_WIDTH_PERIOD = 20  # Media mobile per BB width


class StochRSIBBSqueezeStrategy(AbstractScalpingStrategy):
    """Strategia StochRSI + Bollinger Bands Squeeze per breakout trading.

    Rileva condizioni di ipercomprato/ipervenduto tramite StochRSI
    e le combina con la contrazione delle BB (squeeze) per anticipare
    movimenti esplosivi di prezzo.
    """

    @property
    def name(self) -> str:
        return "stoch_rsi_bb_squeeze"

    def evaluate(
        self,
        candles: List[Candle],
        indicators: Optional[dict] = None,
    ) -> TechnicalSignal:
        """Valuta StochRSI e BB Squeeze per segnale di breakout."""
        if len(candles) < max(BB_PERIOD + BB_WIDTH_PERIOD, RSI_PERIOD + STOCH_PERIOD + 1):
            return TechnicalSignal(type="NONE", confidence=0.0)

        closes = [float(c.close) for c in candles]

        # Calcola RSI
        rsi = self._compute_rsi(closes, RSI_PERIOD)

        # Calcola StochRSI: RSI normalizzato sugli ultimi STOCH_PERIOD valori
        stoch_rsi = self._compute_stoch_rsi(rsi, STOCH_PERIOD)

        # Calcola BB Width (larghezza normalizzata delle bande)
        bb_width, bb_width_history = self._compute_bb_width(closes, BB_PERIOD, BB_STD_DEV)

        # Calcola media storica BB Width per determinare squeeze
        bb_width_ma = sum(bb_width_history[-BB_WIDTH_PERIOD:]) / BB_WIDTH_PERIOD
        bb_squeeze = bb_width < bb_width_ma

        logger.debug(
            f"StochRSI eval: stoch_rsi={stoch_rsi:.3f} "
            f"bb_width={bb_width:.6f} bb_width_ma={bb_width_ma:.6f} "
            f"squeeze={bb_squeeze}"
        )

        # Segnale BUY: StochRSI ipervenduto + squeeze attivo
        if stoch_rsi < STOCH_RSI_OVERSOLD and bb_squeeze:
            return TechnicalSignal(
                type="BUY",
                confidence=0.75,
                source=self.name,
            )

        # Segnale SELL: StochRSI ipercomprato + squeeze attivo
        if stoch_rsi > STOCH_RSI_OVERBOUGHT and bb_squeeze:
            return TechnicalSignal(
                type="SELL",
                confidence=0.75,
                source=self.name,
            )

        return TechnicalSignal(type="NONE", confidence=0.0)

    def _compute_rsi(self, closes: List[float], period: int) -> List[float]:
        """Calcola lista RSI su tutte le chiusure."""
        from app.scalping.strategies.base import _calculate_rsi
        # Usa la funzione helper esistente
        return [_calculate_rsi(closes[: i + period + 1], period)
                for i in range(len(closes) - period)]

    def _compute_stoch_rsi(self, rsi_values: List[float], period: int) -> float:
        """Calcola StochRSI come (RSI - min_period) / (max_period - min_period)."""
        if len(rsi_values) < period + 1:
            return 0.5  # Neutro se dati insufficienti

        recent = rsi_values[-period:]
        rsi_min = min(recent)
        rsi_max = max(recent)

        if rsi_max == rsi_min:
            return 0.5  # Neutro se range piatto

        current_rsi = rsi_values[-1]
        stoch = (current_rsi - rsi_min) / (rsi_max - rsi_min)
        return max(0.0, min(1.0, stoch))

    def _compute_bb_width(self, closes: List[float], period: int, std_dev: float) -> tuple:
        """Calcola larghezza BB normalizzata e storico larghezze."""
        if len(closes) < period + 1:
            return 0.0, [0.0]

        width_history = []
        for i in range(period, len(closes)):
            window = closes[i - period: i]
            mean = sum(window) / period
            std = _std_dev(window)
            bb_upper = mean + std_dev * std
            bb_lower = mean - std_dev * std
            bb_mid = mean
            width = (bb_upper - bb_lower) / bb_mid if bb_mid > 0 else 0.0
            width_history.append(width)

        return width_history[-1], width_history