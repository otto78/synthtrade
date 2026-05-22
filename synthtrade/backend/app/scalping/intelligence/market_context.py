"""MarketContext — snapshot aggregato del contesto di mercato per un simbolo.

Combina tutti i dati dei collector + score in un unico oggetto
MarketIntelSnapshot pronto per essere:
  - Salvato su Supabase
  - Passato al Supervisor AI (context_builder)
  - Trasmesso al frontend via WebSocket
"""

from typing import Optional

from app.scalping.models.intelligence import (
    CVDData,
    FearGreedData,
    FundingRate,
    LongShortRatio,
    MarketIntelSnapshot,
    OpenInterest,
    SignalScore,
)
from app.scalping.intelligence.signal_score_engine import SignalScoreEngine


class MarketContext:
    """Contesto di mercato aggregato per un simbolo.

    Uso:
        context = MarketContext(symbol="BTCUSDT")
        snapshot = await context.build()
    """

    def __init__(
        self,
        symbol: str = "BTCUSDT",
        score_engine: Optional[SignalScoreEngine] = None,
    ):
        self.symbol = symbol
        self._engine = score_engine or SignalScoreEngine(symbol=symbol)

    async def build(self) -> MarketIntelSnapshot:
        """Costruisce uno snapshot completo del contesto di mercato.

        Returns:
            MarketIntelSnapshot con tutti i dati disponibili.
        """
        return await self._engine.get_snapshot()