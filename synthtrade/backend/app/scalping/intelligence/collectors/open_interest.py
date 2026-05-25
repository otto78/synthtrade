"""OpenInterestCollector — recupera Open Interest da Binance Futures API.

Documentazione API:
  GET /fapi/v1/openInterest
  https://binance-docs.github.io/apidocs/futures/en/#open-interest

Open Interest crescente + prezzo laterale = breakout imminente
Open Interest decrescente = mercato in chiusura posizioni
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import httpx

from app.scalping.models.intelligence import OpenInterest

BINANCE_OI_URL = "https://fapi.binance.com/fapi/v1/openInterest"


class OpenInterestCollector:
    """Collettore Open Interest da Binance Futures."""

    def __init__(self, timeout_seconds: float = 10.0):
        self._timeout = timeout_seconds

    async def collect(self, symbol: str = "BTCUSDT") -> Optional[OpenInterest]:
        """Recupera l'Open Interest corrente per un simbolo.

        Args:
            symbol: Simbolo in formato Binance (es: BTCUSDT).

        Returns:
            OpenInterest se la chiamata ha successo, None altrimenti.
        """
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                params = {"symbol": symbol.upper()}
                response = await client.get(BINANCE_OI_URL, params=params)
                response.raise_for_status()

                data = await response.json()
                return OpenInterest(
                    symbol=symbol.upper(),
                    value_usd=Decimal(str(data.get("openInterest", "0"))),
                    asset=symbol.replace("USDT", ""),
                    timestamp=datetime.now(timezone.utc),
                )

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("OpenInterestCollector error for %s: %s", symbol, e)
            return None

    @staticmethod
    def oi_to_score(oi_value_usd: Decimal, baseline_usd: Decimal) -> float:
        """Converte OI in contributo score (-15 a +15).

        OI alto rispetto alla baseline = mercato esposto -> bias contrarian.
        """
        if baseline_usd == 0:
            return 0.0
        ratio = float(oi_value_usd) / float(baseline_usd)
        # ratio > 1.5 = OI molto alto -> bias short (-15)
        # ratio < 0.5 = OI basso -> bias long (+15)
        score = (1.0 - ratio) * 30
        return max(-15.0, min(15.0, score))