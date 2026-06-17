"""LongShortRatioCollector — recupera Long/Short Ratio da Binance Futures API.

Documentazione API:
  GET /futures/data/globalLongShortAccountRatio
  https://binance-docs.github.io/apidocs/futures/en/#long-short-ratio

> 70% long  -> mercato esposto a short squeeze (contrarian short bias)
> 70% short -> mercato esposto a long squeeze (contrarian long bias)
"""

import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional

import httpx

from app.scalping.models.intelligence import LongShortRatio

BINANCE_LS_URL = "https://fapi.binance.com/futures/data/globalLongShortAccountRatio"
logger = logging.getLogger(__name__)

# Mappa simboli spot → futures perpetual per collector
FUTURES_SYMBOL_MAP = {
    "BNBUSDC": "BNBUSDT",
    "BTCUSDC": "BTCUSDT",
    "ETHUSDC": "ETHUSDT",
}


class LongShortRatioCollector:
    """Collettore Long/Short Ratio da Binance Futures."""

    def __init__(self, timeout_seconds: float = 10.0, max_retries: int = 3):
        self._timeout = timeout_seconds
        self._max_retries = max_retries

    async def collect(self, symbol: str = "BTCUSDT", period: str = "5m") -> Optional[LongShortRatio]:
        """Recupera il Long/Short Ratio corrente per un simbolo.

        Args:
            symbol: Simbolo in formato Binance (es: BTCUSDT).
            period: Periodo ('5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d').

        Returns:
            LongShortRatio se la chiamata ha successo, None altrimenti.
        """
        # Mappa USDC → USDT per i futures perpetual
        futures_symbol = FUTURES_SYMBOL_MAP.get(symbol.upper(), symbol.upper())
        
        for attempt in range(self._max_retries):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    params = {
                        "symbol": futures_symbol,
                        "period": period,
                        "limit": 1,
                    }
                    response = await client.get(BINANCE_LS_URL, params=params)
                    response.raise_for_status()

                    data = response.json()
                    if not data:
                        return None

                    entry = data[0]
                    long_val = Decimal(str(entry.get("longAccount", "0")))
                    short_val = Decimal(str(entry.get("shortAccount", "0")))
                    
                    logger.debug("Raw LS data for %s: long=%s, short=%s", symbol, long_val, short_val)

                    return LongShortRatio(
                        symbol=symbol.upper(),
                        long_pct=long_val * 100,
                        short_pct=short_val * 100,
                        timestamp=datetime.fromtimestamp(entry.get("timestamp", 0) / 1000),
                    )

            except Exception as e:
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))  # Backoff
                    continue
                logger.warning("LongShortRatioCollector error for %s: %s", symbol, e)
                return None

    @staticmethod
    def ratio_to_score(long_pct: Decimal) -> float:
        """Converte il long % in contributo score (-100 a +100).

        > 70% long  -> mercato esposto -> bias short (score negativo)
        > 70% short -> mercato esposto -> bias long (score positivo)
        """
        long_val = float(long_pct)
        # Centro a 50%: (50 - long%) * 3.333
        # 80% long -> -100, 20% long -> +100
        score = (50.0 - long_val) * (100.0 / 30.0)
        return max(-100.0, min(100.0, score))