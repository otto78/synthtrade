"""VWAP Reversion Strategy - mean reversion contro VWAP.

Logica corretta (TASK-1238):
  - BUY quando prezzo è SOTTO il VWAP (dip, opportunità di ritorno alla media)
  - NONE quando prezzo è SOPRA il VWAP (aspettare pullback; no short in EU)

Nota: la logica precedente era invertita (BUY sopra VWAP = momentum, non reversion).
"""

from typing import List, Optional

from app.scalping.models.market import Candle
from app.scalping.strategies.base import AbstractScalpingStrategy
from app.scalping.engine.signal_aggregator import TechnicalSignal


class VWAPReversionStrategy(AbstractScalpingStrategy):
    """Strategia VWAP Reversion (mean-reversion autentica).

    BUY quando il prezzo scende sotto il VWAP (ritorno alla media dal basso).
    NONE quando il prezzo è sopra il VWAP — lo short non è consentito (EU spot).

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

        # TASK-1238 + TASK-1240: logica corretta per mean-reversion long-only.
        # BUY quando il prezzo è SOTTO il VWAP (dip: il mercato si è allontanato
        # dalla media verso il basso, ci aspettiamo un ritorno alla media = rialzo).
        if distance < -0.002:  # 0.2% sotto VWAP
            return TechnicalSignal(
                type="BUY",
                confidence=0.7,
                source=self.name,
            )

        # Prezzo sopra VWAP: mercato già sopra la media.
        # In reversion autentica non si entra long qui (si venderebbe, ma no short EU).
        # → NONE: aspettare un pullback al VWAP prima di comprare.
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