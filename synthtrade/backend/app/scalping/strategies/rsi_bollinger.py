"""RSI + Bollinger Bands Strategy - filtro timing per mean reversion.

Soglie calibrate per mercato ranging a bassa volatilità:
- RSI oversold 38 (era 30) — cattura mean-reversion anche su range stretti
- RSI overbought 62 (era 70) — simmetrico
- BB tolleranza 1.5% (era 1%) — più spazio in volumi laterali
- Confidence 0.6 (era 0.7) — leggermente ridotta per evitare falsi positivi
"""

from typing import List, Optional

from app.scalping.models.market import Candle
from app.scalping.strategies.base import AbstractScalpingStrategy
from app.scalping.engine.signal_aggregator import TechnicalSignal


class RSIBollingerStrategy(AbstractScalpingStrategy):
    """Strategia RSI + Bollinger Bands per mean reversion in ranging.

    Segnale BUY quando RSI < 38 (ipervenduto) e prezzo vicino BB bassa.
    Segnale SELL quando RSI > 62 (ipercomprato) e prezzo vicino BB alta.
    
    Soglie calibrate per mercato ranging a bassa volatilità come BNBUSDC
    nel range 597-602 (0.5% di movimento) dove RSI 30/70 non viene mai toccato.
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

        # Oversold: RSI sotto soglia e prezzo vicino BB bassa
        if rsi < 38 and close <= bb_lower * 1.015:
            return TechnicalSignal(
                type="BUY",
                confidence=0.6,
                source=self.name,
            )

        # Overbought: RSI sopra soglia e prezzo vicino BB alta
        if rsi > 62 and close >= bb_upper * 0.985:
            return TechnicalSignal(
                type="SELL",
                confidence=0.6,
                source=self.name,
            )

        return TechnicalSignal(type="NONE", confidence=0.0)