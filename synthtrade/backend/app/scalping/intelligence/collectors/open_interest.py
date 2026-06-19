"""OpenInterestCollector — recupera Open Interest da Binance Futures API.

Documentazione API:
  GET /fapi/v1/openInterest
  https://binance-docs.github.io/apidocs/futures/en/#open-interest

Open Interest crescente + prezzo laterale = breakout imminente
Open Interest decrescente = mercato in chiusura posizioni

NOTA: La baseline è calcolata dinamicamente come media mobile degli ultimi N fetch,
così lo score è sensibile ai cambiamenti REALI di OI invece di un valore fisso arbitrario.
"""

import asyncio
import logging
from collections import deque
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import httpx

from app.scalping.models.intelligence import OpenInterest

logger = logging.getLogger(__name__)

BINANCE_OI_URL = "https://fapi.binance.com/fapi/v1/openInterest"

# Quanti campioni tenere per la baseline rolling
_ROLLING_WINDOW = 5

# Mappa simboli spot → futures perpetual per collector
# I dati OI esistono SOLO su USDT perpetual futures.
# USDC spot è equivalente come sottostante, quindi usiamo USDT come proxy.
FUTURES_SYMBOL_MAP = {
    "BNBUSDC": "BNBUSDT",
    "BTCUSDC": "BTCUSDT",
    "ETHUSDC": "ETHUSDT",
}


class OpenInterestCollector:
    """Collettore Open Interest da Binance Futures con baseline dinamica."""

    def __init__(self, timeout_seconds: float = 10.0, max_retries: int = 3):
        self._timeout = timeout_seconds
        self._max_retries = max_retries
        self._history: dict[str, deque] = {}
        from app.scalping.intelligence.collectors.circuit_breaker import CollectorCircuitBreaker
        self._cb = CollectorCircuitBreaker("open_interest")

    async def collect(self, symbol: str = "BTCUSDT") -> Optional[OpenInterest]:
        if not self._cb.is_available():
            return None
        futures_symbol = FUTURES_SYMBOL_MAP.get(symbol.upper(), symbol.upper())
        
        for attempt in range(self._max_retries):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    params = {"symbol": futures_symbol}
                    response = await client.get(BINANCE_OI_URL, params=params)
                    response.raise_for_status()

                    data = response.json()
                    oi_value = Decimal(str(data.get("openInterest", "0")))

                    # Aggiorna history per baseline rolling
                    sym_key = symbol.upper()
                    if sym_key not in self._history:
                        self._history[sym_key] = deque(maxlen=_ROLLING_WINDOW)
                    self._history[sym_key].append(float(oi_value))

                    baseline = Decimal(str(sum(self._history[sym_key]) / len(self._history[sym_key])))

                    logger.debug(
                        "OpenInterest for %s: value=%.0f baseline=%.0f (samples=%d)",
                        symbol, float(oi_value), float(baseline), len(self._history[sym_key])
                    )

                    return OpenInterest(
                        symbol=symbol.upper(),
                        value_usd=oi_value,
                        asset=symbol.replace("USDT", "").replace("USDC", ""),
                        timestamp=datetime.now(timezone.utc),
                    )

            except Exception as e:
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))  # Backoff
                    continue
                logger.warning("OpenInterestCollector error for %s: %s", symbol, e)
                return None

    def get_baseline(self, symbol: str) -> Decimal:
        """Restituisce la baseline rolling per un simbolo."""
        sym_key = symbol.upper()
        history = self._history.get(sym_key)
        if not history:
            return Decimal("0")
        return Decimal(str(sum(history) / len(history)))

    @staticmethod
    def oi_to_score(oi_value_usd: Decimal, baseline_usd: Decimal) -> float:
        """Converte OI in contributo score (-100 a +100).

        OI alto rispetto alla baseline = mercato esposto = bias contrarian.
        Con baseline dinamica questo score varia realmente invece di essere costante.
        """
        if baseline_usd == 0:
            return 0.0
        ratio = float(oi_value_usd) / float(baseline_usd)
        # ratio > 1.5 = OI molto alto -> bias short (-100)
        # ratio < 0.5 = OI basso -> bias long (+100)
        score = (1.0 - ratio) * 200
        return max(-100.0, min(100.0, score))