"""CVDCalculator — Cumulative Volume Delta in tempo reale.

CVD calcola la pressione netta buy vs sell a partire dal trade stream di Binance.
Consuma i TradeEvent prodotti dal BinanceWSClient (TASK-803).

CVD crescente  = piu pressione buy  -> momentum rialzista
CVD calante    = piu pressione sell -> momentum ribassista
CVD divergente dal prezzo = forte segnale inversione imminente
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from app.scalping.models.intelligence import CVDData


class CVDCalculator:
    """Calcola il Cumulative Volume Delta da trades.

    Ad ogni trade:
      is_buyer_maker=False -> buy aggressivo (taker buy)  -> CVD += quantity
      is_buyer_maker=True  -> sell aggressivo (taker sell) -> CVD -= quantity

    Uso:
      calculator = CVDCalculator(window_size=100)
      calculator.on_trade(price=67650.50, quantity=0.001, is_buyer_maker=False)
      calculator.on_trade(price=67651.00, quantity=0.002, is_buyer_maker=True)
      snapshot = calculator.snapshot("BTCUSDT")
    """

    def __init__(self, window_size: int = 1000):
        self._cvd = Decimal("0")
        self._window_size = window_size
        self._trades_since_reset = 0
        self._last_delta = Decimal("0")
        self._last_prices: list[float] = []
        self._previous_cvd = Decimal("0")

    def on_trade(self, price: float, quantity: float, is_buyer_maker: bool) -> None:
        """Aggiorna CVD con un nuovo trade.

        Args:
            price: Prezzo del trade.
            quantity: Quantita' del trade.
            is_buyer_maker: True se il venditore e' aggressivo (sell), False se il compratore e' aggressivo (buy).
        """
        qty = Decimal(str(quantity))
        delta = -qty if is_buyer_maker else qty

        self._cvd += delta
        self._trades_since_reset += 1
        self._last_prices.append(price)

        # Reset periodico per evitare drift numerico
        if self._trades_since_reset >= self._window_size:
            self._previous_cvd = self._cvd
            self._cvd = Decimal("0")
            self._trades_since_reset = 0
            self._last_prices.clear()

    @property
    def cvd(self) -> Decimal:
        return self._cvd

    def snapshot(self, symbol: str = "BTCUSDT") -> CVDData:
        """Cattura lo stato corrente del CVD.

        Returns:
            CVDData con trend calcolato.
        """
        delta = self._cvd - self._previous_cvd if self._previous_cvd != 0 else Decimal("0")
        trend = self._compute_trend()
        return CVDData(
            symbol=symbol,
            cvd=self._cvd + self._previous_cvd,
            delta=delta,
            trend=trend,
            timestamp=datetime.now(timezone.utc),
        )

    def reset(self) -> None:
        """Resetta completamente il CVD."""
        self._cvd = Decimal("0")
        self._previous_cvd = Decimal("0")
        self._trades_since_reset = 0
        self._last_prices.clear()

    def _compute_trend(self) -> Optional[str]:
        """Calcola il trend basato sui prezzi recenti."""
        if len(self._last_prices) < 2:
            return None
        first = self._last_prices[0]
        last = self._last_prices[-1]
        if last > first * 1.001:  # +0.1%
            return "rising"
        elif last < first * 0.999:  # -0.1%
            return "falling"
        return "neutral"

    @staticmethod
    def cvd_to_score(cvd_value: Decimal, baseline: Decimal = Decimal("1000")) -> float:
        """Converte CVD in contributo score (-25 a +25).

        CVD positivo (pressione buy) -> score positivo (bullish)
        CVD negativo (pressione sell) -> score negativo (bearish)
        """
        if baseline == 0:
            return 0.0
        ratio = float(cvd_value) / float(baseline)
        score = ratio * 25  # CVD = baseline -> 25 punti
        return max(-25.0, min(25.0, score))