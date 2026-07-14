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

from app.config import settings
from app.scalping.models.intelligence import LongShortRatio

BINANCE_LS_URL = "https://fapi.binance.com/futures/data/globalLongShortAccountRatio"
logger = logging.getLogger(__name__)

# Mappa simboli spot → futures perpetual per collector
# EUR symbols non hanno equivalente su Binance Futures → None = graceful skip.
FUTURES_SYMBOL_MAP = {
    "BNBUSDC": "BNBUSDT",
    "BTCUSDC": "BTCUSDT",
    "ETHUSDC": "ETHUSDT",
    "BTCEUR": None,
    "BTC-EUR": None,
    "ETHEUR": None,
    "ETH-EUR": None,
    "SOLEUR": None,
    "SOL-EUR": None,
    "XRPEUR": None,
    "XRP-EUR": None,
    "OKBEUR": None,
    "OKB-EUR": None,
}


class LongShortRatioCollector:
    """Collettore Long/Short Ratio da Binance Futures.

    TASK-1153 / TASK-1158: OKX non ha un endpoint equivalente confermato per il
    long/short ratio. Con provider OKX, `is_symbol_supported` ritorna sempre
    False e `collect` ritorna None senza alcuna chiamata di rete (in attesa di
    TASK-1158). Con adapter=None il comportamento legacy Binance è invariato.
    """

    def __init__(self, timeout_seconds: float = 10.0, max_retries: int = 3, adapter: Optional[object] = None):
        self._timeout = timeout_seconds
        self._max_retries = max_retries
        self._adapter = adapter
        from app.scalping.intelligence.collectors.circuit_breaker import CollectorCircuitBreaker
        self._cb = CollectorCircuitBreaker("long_short_ratio")

    def is_symbol_supported(self, symbol: str) -> bool:
        """True se il simbolo può strutturalmente avere long/short ratio.

        OKX provider: nessun endpoint equivalente confermato (TASK-1158) ->
        sempre False, indipendentemente dal simbolo.
        Legacy Binance: usa la stessa FUTURES_SYMBOL_MAP del collect(). Se il
        simbolo non è nella mappa, ritorna True in modo conservativo.
        """
        if self._adapter is not None and settings.EXCHANGE_PROVIDER.lower() == "okx":
            return False
        sym_upper = symbol.upper()
        if sym_upper not in FUTURES_SYMBOL_MAP:
            return True
        return FUTURES_SYMBOL_MAP[sym_upper] is not None

    async def collect(self, symbol: str = "BTCUSDT", period: str = "5m") -> Optional[LongShortRatio]:
        if not self._cb.is_available():
            return None

        # OKX provider: nessun endpoint equivalente (TASK-1158) -> no rete
        if self._adapter is not None and settings.EXCHANGE_PROVIDER.lower() == "okx":
            logger.debug(
                "LongShortRatioCollector: skipping %s — no OKX equivalent endpoint "
                "(awaiting TASK-1158)",
                symbol,
            )
            return None

        # Mappa USDC → USDT per i futures perpetual
        futures_symbol = FUTURES_SYMBOL_MAP.get(symbol.upper(), symbol.upper())

        if futures_symbol is None:
            logger.debug(
                "LongShortRatioCollector: skipping %s — no Binance Futures equivalent (EUR pair)",
                symbol,
            )
            return None

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