"""FundingRateCollector — recupera funding rate da Binance Futures API.

Documentazione API:
  GET /fapi/v1/fundingRate
  https://binance-docs.github.io/apidocs/futures/en/#get-funding-rate-history

Funding Rate positivo  -> i long pagano gli short (overleveraged long) -> bias SHORT
Funding Rate negativo  -> gli short pagano i long (overleveraged short) -> bias LONG
"""

import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional

import httpx

from app.scalping.models.intelligence import FundingRate

logger = logging.getLogger(__name__)

BINANCE_FUNDING_RATE_URL = "https://fapi.binance.com/fapi/v1/fundingRate"

# Mappa simboli spot → futures perpetual per collector
# I dati di funding rate esistono SOLO su USDT perpetual futures.
# USDC spot è equivalente come sottostante (BNB), quindi usiamo USDT come proxy.
FUTURES_SYMBOL_MAP = {
    "BNBUSDC": "BNBUSDT",
    "BTCUSDC": "BTCUSDT",
    "ETHUSDC": "ETHUSDT",
}


class FundingRateCollector:
    """Collettore funding rate da Binance Futures.

    Soglie:
      > +0.10% = fortemente overleveraged long (contrarian short)
      > +0.05% = moderatamente rialzista
        ~0%    = equilibrio
      < -0.05% = moderatamente ribassista
      < -0.10% = fortemente overleveraged short (contrarian long)
    """

    def __init__(self, timeout_seconds: float = 10.0, max_retries: int = 3):
        self._timeout = timeout_seconds
        self._max_retries = max_retries

    async def collect(self, symbol: str = "BTCUSDT") -> Optional[FundingRate]:
        """Recupera il funding rate corrente per un simbolo.

        Args:
            symbol: Simbolo in formato Binance (es: BTCUSDT).

        Returns:
            FundingRate se la chiamata ha successo, None altrimenti.
        """
        # Mappa USDC → USDT per i futures perpetual
        futures_symbol = FUTURES_SYMBOL_MAP.get(symbol.upper(), symbol.upper())
        
        for attempt in range(self._max_retries):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    params = {"symbol": futures_symbol, "limit": 1}
                    response = await client.get(BINANCE_FUNDING_RATE_URL, params=params)
                    response.raise_for_status()

                    data = response.json()
                    if not data:
                        return None

                    entry = data[0]
                    return FundingRate(
                        symbol=symbol.upper(),
                        rate=Decimal(str(entry.get("fundingRate", "0"))),
                        timestamp=datetime.fromtimestamp(entry.get("fundingTime", 0) / 1000),
                        next_funding_time=(
                            datetime.fromtimestamp(entry["nextFundingTime"] / 1000)
                            if "nextFundingTime" in entry
                            else None
                        ),
                    )

            except Exception as e:
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))  # Backoff
                    continue
                logger.warning("FundingRateCollector error for %s: %s", symbol, e)
                return None

    @staticmethod
    def interpret_rate(rate: Decimal) -> str:
        """Interpreta il funding rate come bias di mercato.

        Returns:
            'strong_short', 'short', 'neutral', 'long', 'strong_long'
        """
        rate_pct = float(rate) * 100  # Converti in percentuale
        if rate_pct > 0.10:
            return "strong_short"
        elif rate_pct > 0.05:
            return "short"
        elif rate_pct < -0.10:
            return "strong_long"
        elif rate_pct < -0.05:
            return "long"
        return "neutral"

    @staticmethod
    def rate_to_score(rate: Decimal) -> float:
        """Converte il funding rate in un contributo score (-100 a +100).

        Funding rate positivo (long pagano) -> score negativo (bearish)
        Funding rate negativo (short pagano) -> score positivo (bullish)
        """
        rate_pct = float(rate) * 100
        # Mappa: +0.20% -> -100, +0.10% -> -50, 0% -> 0, -0.10% -> +50, -0.20% -> +100
        score = -rate_pct * 500  # 0.10% * 500 = 50
        return max(-100.0, min(100.0, score))