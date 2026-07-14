"""OrderBookImbalanceCollector — ordine book imbalance da OKX public market data.

Endpoint (pubblico, nessuna autenticazione):
  GET https://eea.okx.com/api/v5/market/books?instId={instId}&sz={depth}

  imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth)
    > 0 -> piu liquidita' bid  -> pressione rialzista
    < 0 -> piu liquidita' ask  -> pressione ribassista
    Score: imbalance * 100, clampato a [-100, +100]

A differenza di funding_rate/open_interest/long_short_ratio, questo collector
funziona su QUALSIASI coppia spot OKX (incluso il simbolo operativo OKB-EUR)
perche' non dipende da un mercato futures perpetuo.
"""

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Optional

import httpx

from app.scalping.models.intelligence import OrderBookImbalance
from app.scalping.engine.okx_ws_client import _normalize_okx_symbol

logger = logging.getLogger(__name__)

# Base URL pubblica OKX (EEA). Stesso host usato da okx_balance.py e historical_loader.py.
OKX_BOOKS_URL = "https://eea.okx.com/api/v5/market/books"


class OrderBookImbalanceCollector:
    """Collettore Order Book Imbalance da OKX public market data."""

    def __init__(self, timeout_seconds: float = 10.0, max_retries: int = 3, depth: int = 20):
        self._timeout = timeout_seconds
        self._max_retries = max_retries
        self._depth = depth
        from app.scalping.intelligence.collectors.circuit_breaker import CollectorCircuitBreaker
        self._cb = CollectorCircuitBreaker("order_book_imbalance")

    def is_symbol_supported(self, symbol: str) -> bool:
        """Sempre True: l'order book esiste per ogni coppia spot OKX."""
        return True

    async def collect(self, symbol: str = "BTC-USDT") -> Optional[OrderBookImbalance]:
        if not self._cb.is_available():
            return None

        # Normalizza il simbolo nel formato instId OKX (es. OKBEUR -> OKB-EUR).
        # L'engine passa self.symbol gia' uppercase-senza-dash (es. "OKBEUR");
        # OKX richiede il dash per l'endpoint /market/books, altrimenti code!=0.
        inst_id = _normalize_okx_symbol(symbol)

        for attempt in range(self._max_retries):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    params = {"instId": inst_id, "sz": str(self._depth)}
                    response = await client.get(OKX_BOOKS_URL, params=params)
                    response.raise_for_status()

                    payload = response.json()
                    if payload.get("code") != "0" or not payload.get("data"):
                        logger.debug(
                            "OrderBookImbalanceCollector: empty/invalid book for %s code=%s",
                            symbol, payload.get("code"),
                        )
                        return None

                    book = payload["data"][0]
                    bids = book.get("bids") or []
                    asks = book.get("asks") or []

                    bid_depth = self._sum_depth(bids)
                    ask_depth = self._sum_depth(asks)

                    if bid_depth + ask_depth == 0:
                        logger.debug("OrderBookImbalanceCollector: empty book for %s", symbol)
                        return None

                    imbalance = float((bid_depth - ask_depth) / (bid_depth + ask_depth))
                    return OrderBookImbalance(
                        symbol=inst_id,
                        bid_depth=bid_depth,
                        ask_depth=ask_depth,
                        imbalance=imbalance,
                        timestamp=datetime.now(timezone.utc),
                    )

            except Exception as e:
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))  # Backoff
                    continue
                logger.warning("OrderBookImbalanceCollector error for %s: %s", symbol, e)
                self._cb.on_failure()
                return None

        return None

    @staticmethod
    def _sum_depth(levels: list) -> Decimal:
        """Somma le quantità (indice 1) dei livelli [price, size, ...]."""
        total = Decimal("0")
        for level in levels:
            try:
                total += Decimal(str(level[1]))
            except (IndexError, InvalidOperation, TypeError):
                continue
        return total

    @staticmethod
    def imbalance_to_score(imbalance: float) -> float:
        """Converte l'imbalance in contributo score (-100 a +100).

        imbalance > 0 (bid pesante) -> score positivo (bullish)
        imbalance < 0 (ask pesante) -> score negativo (bearish)
        """
        score = imbalance * 100.0
        return max(-100.0, min(100.0, score))
