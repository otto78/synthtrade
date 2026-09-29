"""CVDCalculator — Cumulative Volume Delta in tempo reale.

CVD calcola la pressione netta buy vs sell a partire dal trade stream di Binance.
Consuma i TradeEvent prodotti dal BinanceWSClient (TASK-803).

CVD crescente  = piu pressione buy  -> momentum rialzista
CVD calante    = piu pressione sell -> momentum ribassista
CVD divergente dal prezzo = forte segnale inversione imminente
"""

import collections
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from app.scalping.models.intelligence import CVDData

# TASK-1262: lower bound della baseline dinamica.
# Il task specificava 5.0 BTC, ma la stessa analisi riporta volumi di 0.05-0.2 BTC
# per finestra su BTC-EUR: un floor di 5.0 e' 25-100x il valore reale e riporterebbe
# il rapporto cvd/baseline sotto 0.2, azzerando di fatto il fix. Qui si usa solo un
# epsilon anti divisione-per-zero, lasciando la scala reale ai dati osservati.
BASELINE_FLOOR = Decimal("0.01")


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
        # TASK-1262: storico CVD massimi per baseline dinamica
        self._historical_max_abs = collections.deque(maxlen=20)

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
            # TASK-1262: memorizza l'escursione massima prima del reset
            self._historical_max_abs.append(abs(self._cvd))
            self._previous_cvd = self._cvd
            self._cvd = Decimal("0")
            self._trades_since_reset = 0
            self._last_prices.clear()

    @property
    def cvd(self) -> Decimal:
        return self._cvd

    def has_baseline(self) -> bool:
        """True se esiste almeno una finestra completa su cui basare la scala."""
        return bool(self._historical_max_abs)

    def get_dynamic_baseline(self) -> Optional[Decimal]:
        """Baseline dinamica: media delle escursioni per finestra gia' chiuse.

        TASK-1262: la baseline hardcoded a 1000 era nonsensicala su BTC-EUR su OKX
        spot, dove una finestra vale 0.05-0.2 BTC: il rapporto restava sotto 0.2 e
        lo score non superava mai i +-2 punti, sprecando il 15% del peso.

        Ritorna None finche' nessuna finestra e' stata chiusa: senza una finestra
        completa non esiste una scala di riferimento, e usare il lower bound
        epsilon farebbe saturare cvd_to_score a +-100, producendo un contributo
        costante di 15 punti invece di un segnale. Il chiamante (SignalScoreEngine)
        esclude il collector da score e normalizzazione in quel caso, come gia'
        fa per Long/Short Ratio.

        Il lower bound (BASELINE_FLOOR) resta un epsilon anti divisione-per-zero
        applicato solo quando esiste gia' una scala osservata.
        """
        if not self._historical_max_abs:
            return None
        total = sum(self._historical_max_abs, Decimal("0"))
        avg_max = total / Decimal(str(len(self._historical_max_abs)))
        return max(BASELINE_FLOOR, avg_max)

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
        """Converte CVD in contributo score (-100 a +100).

        CVD positivo (pressione buy) -> score positivo (bullish)
        CVD negativo (pressione sell) -> score negativo (bearish)

        TASK-1262: il default resta 1000 per compatibilita' con i chiamanti che
        passano la baseline esplicitamente. SignalScoreEngine usa
        get_dynamic_baseline() perche' il valore reale di BTC-EUR e' 2-3 ordini
        di grandezza inferiore.
        """
        if baseline == 0:
            return 0.0
        ratio = float(cvd_value) / float(baseline)
        score = ratio * 100  # CVD = baseline -> 100 punti
        return max(-100.0, min(100.0, score))