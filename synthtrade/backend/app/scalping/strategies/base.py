"""Abstract Scalping Strategy - base class for timing filters."""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import List, Optional

from app.scalping.models.market import Candle
from app.scalping.engine.signal_aggregator import TechnicalSignal


class AbstractScalpingStrategy(ABC):
    """Strategia di scalping base.

    Le strategie implementano i segnali tecnici che fungono da filtri
    di timing (v2.0 architecture).
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Nome della strategia."""
        pass

    def update_params(self, params: dict) -> None:
        """Aggiorna parametri della strategia (usato dal supervisor).

        Le sottoclassi possono fare override per personalizzare l'aggiornamento.
        Default: memorizza come dizionario self._params.
        """
        self._params = params

    @abstractmethod
    def evaluate(
        self,
        candles: List[Candle],
        indicators: Optional[dict] = None,
    ) -> TechnicalSignal:
        """Valuta la strategia e restituisce un segnale tecnico.

        Args:
            candles: Lista di candele (ultime N candele).
            indicators: Indicatori pre-calcolati (opzionale).

        Returns:
            TechnicalSignal con type='BUY', 'SELL', 'CLOSE', o 'NONE'.
        """
        pass

    @staticmethod
    def calculate_indicators(candles: List[Candle]) -> dict:
        """Calcola indicatori di base dalle candele.

        Usa le funzioni esistenti in app/core/indicators.py quando disponibili.
        Qui forniamo un fallback minimo.
        """
        if len(candles) < 2:
            return {}

        closes = [float(c.close) for c in candles]
        highs = [float(c.high) for c in candles]
        lows = [float(c.low) for c in candles]

        # EMA semplice (fallback - preferibilmente usare app/core/indicators.py)
        ema_fast = _calculate_ema(closes, 9)
        ema_slow = _calculate_ema(closes, 21)

        # RSI semplice
        rsi = _calculate_rsi(closes, 14) if len(closes) >= 15 else 50.0

        # Bollinger Bands
        bb_middle = sum(closes[-20:]) / 20
        bb_std = (_std_dev(closes[-20:]) if len(closes) >= 20 else 0.01)
        bb_upper = bb_middle + 2 * bb_std
        bb_lower = bb_middle - 2 * bb_std

        return {
            "ema_fast": ema_fast[-1] if ema_fast else 0,
            "ema_slow": ema_slow[-1] if ema_slow else 0,
            "ema_fast_prev": ema_fast[-2] if len(ema_fast) > 1 else 0,
            "ema_slow_prev": ema_slow[-2] if len(ema_slow) > 1 else 0,
            "rsi": rsi,
            "bb_upper": bb_upper,
            "bb_lower": bb_lower,
            "bb_middle": bb_middle,
            "close": closes[-1],
        }


def _calculate_ema(values: List[float], period: int) -> List[float]:
    """Calcola EMA."""
    if len(values) < period:
        return []

    multiplier = 2 / (period + 1)
    ema = [sum(values[:period]) / period]

    for i in range(period, len(values)):
        ema.append(values[i] * multiplier + ema[-1] * (1 - multiplier))

    return ema


def _calculate_rsi(values: List[float], period: int = 14) -> float:
    """Calcola RSI."""
    if len(values) < period + 1:
        return 50.0

    gains = []
    losses = []

    for i in range(1, min(period + 1, len(values))):
        diff = values[-i] - values[-(i + 1)]
        if diff > 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(-diff)

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _std_dev(values: List[float]) -> float:
    """Deviazione standard."""
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    return (sum((x - mean) ** 2 for x in values) / len(values)) ** 0.5