"""EMA Cross Strategy - filtro timing per trend following."""

import logging
from typing import List, Optional

from app.scalping.models.market import Candle
from app.scalping.strategies.base import AbstractScalpingStrategy
from app.scalping.engine.signal_aggregator import TechnicalSignal

logger = logging.getLogger(__name__)

# Pendenza minima EMA21 per considerare il trend valido (0.03%)
MIN_SLOPE = 0.0003


class EMACrossStrategy(AbstractScalpingStrategy):
    """Strategia EMA 9/21 cross con slope filter.

    Segnale BUY quando EMA9 > EMA21 e la pendenza EMA21 >= 0.03% (trend up valido).
    Segnale SELL quando EMA9 < EMA21 e la pendenza EMA21 <= -0.03% (trend down valido).
    Usato come filtro timing, non segnale primario.

    Lo slope filter elimina i falsi segnali in ranging market dove le EMA
    si intrecciano continuamente senza un trend definito.
    """

    # TASK-1249: parametri modificabili dal supervisor via update_params.
    # I default coincidono con i valori hardcoded storici → nessun cambio
    # di comportamento a parità di config.
    DEFAULT_PARAMS: dict = {
        "fast_period": 9,        # periodo EMA veloce
        "slow_period": 21,       # periodo EMA lenta
        "min_slope": MIN_SLOPE,  # pendenza minima EMA21 (0.03%)
    }

    @property
    def name(self) -> str:
        return "ema_cross"

    def evaluate(
        self,
        candles: List[Candle],
        indicators: Optional[dict] = None,
    ) -> TechnicalSignal:
        """Valuta lo stato EMA per generare segnale di trend.
        
        Applica slope filter per evitare falsi segnali in ranging.
        Ritorna BUY/SELL solo se la pendenza EMA21 è significativa.
        """
        if len(candles) < 21:
            return TechnicalSignal(type="NONE", confidence=0.0)

        ind = indicators or self.calculate_indicators(candles)

        # TASK-1249: parametri letti da self._params (modificabili dal supervisor).
        p = self._params
        min_slope = p.get("min_slope", MIN_SLOPE)

        ema_fast = ind.get("ema_fast", 0)
        ema_slow = ind.get("ema_slow", 0)
        ema_slow_prev = ind.get("ema_slow_prev", 0)

        # Slope filter: pendenza EMA21 normalizzata
        slope = 0.0
        if ema_slow_prev > 0:
            slope = (ema_slow - ema_slow_prev) / ema_slow_prev

        logger.debug(f"EMA cross: fast={ema_fast:.2f} slow={ema_slow:.2f} slope={slope:.6f}")

        # Stato Trend Rialzista (solo se pendenza positiva sufficiente)
        if ema_fast > ema_slow and slope >= min_slope:
            return TechnicalSignal(
                type="BUY",
                confidence=0.75,
                source=self.name,
            )

        # Stato Trend Ribassista (solo se pendenza negativa sufficiente)
        if ema_fast < ema_slow and slope <= -min_slope:
            return TechnicalSignal(
                type="SELL",
                confidence=0.75,
                source=self.name,
            )

        return TechnicalSignal(type="NONE", confidence=0.0)
