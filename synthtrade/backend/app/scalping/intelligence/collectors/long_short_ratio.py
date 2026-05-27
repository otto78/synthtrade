"""LongShortRatioCollector — recupera Long/Short Ratio da Binance Futures API.

Documentazione API:
  GET /futures/data/globalLongShortAccountRatio
  https://binance-docs.github.io/apidocs/futures/en/#long-short-ratio

> 70% long  -> mercato esposto a short squeeze (contrarian short bias)
> 70% short -> mercato esposto a long squeeze (contrarian long bias)
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

import httpx

from app.scalping.models.intelligence import LongShortRatio

BINANCE_LS_URL = "https://fapi.binance.com/futures/data/globalLongShortAccountRatio"


class LongShortRatioCollector:
    """Collettore Long/Short Ratio da Binance Futures."""

    def __init__(self, timeout_seconds: float = 10.0):
        self._timeout = timeout_seconds

    async def collect(self, symbol: str = "BTCUSDT", period: str = "5m") -> Optional[LongShortRatio]:
        """Recupera il Long/Short Ratio corrente per un simbolo.

        Args:
            symbol: Simbolo in formato Binance (es: BTCUSDT).
            period: Periodo ('5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d').

        Returns:
            LongShortRatio se la chiamata ha successo, None altrimenti.
        """
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                params = {
                    "symbol": symbol.upper(),
                    "period": period,
                    "limit": 1,
                }
                response = await client.get(BINANCE_LS_URL, params=params)
                response.raise_for_status()

                data = response.json()
                if not data:
                    return None

                entry = data[0]
                return LongShortRatio(
                    symbol=symbol.upper(),
                    long_pct=Decimal(str(entry.get("longAccount", "0"))),
                    short_pct=Decimal(str(entry.get("shortAccount", "0"))),
                    timestamp=datetime.fromtimestamp(entry.get("timestamp", 0) / 1000),
                )

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("LongShortRatioCollector error for %s: %s", symbol, e)
            return None

    @staticmethod
    def ratio_to_score(long_pct: Decimal) -> float:
        """Converte il long % in contributo score (-15 a +15).

        > 70% long  -> mercato esposto -> bias short (score negativo)
        > 70% short -> mercato esposto -> bias long (score positivo)
        """
        long_val = float(long_pct)
        # Centro a 50%: (50 - long%) * 0.5
        # 80% long -> -15, 20% long -> +15
        score = (50.0 - long_val) * 0.5
        return max(-15.0, min(15.0, score))