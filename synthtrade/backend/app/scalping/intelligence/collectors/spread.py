"""SpreadCollector — spread bid/ask relativo da OKX public ticker.

Endpoint (pubblico, nessuna autenticazione):
  GET https://eea.okx.com/api/v5/market/ticker?instId={instId}

  spread_pct = (ask - bid) / mid_price * 100
    > 0 -> costo di attraversamento del book

NON è direzionale (non bullish/bearish): è un flag di affidabilità/cautela.
Lo spread viene normalizzato rispetto a una media mobile degli ultimi N
campioni: uno spread 3x la media recente è anomalo (bassa liquidità / rischio
di slippage), non un valore assoluto arbitrario.

NOTA: il wiring nel weighted score è INTENZIONALMENTE DISATTIVATO (vedi
TASK-1152 nel piano). Il collector calcola e logga, ma non influenza ancora
le decisioni di trading finché non si decide gate-vs-peso in signal_aggregator.
"""

import asyncio
import logging
from collections import deque
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Optional

import httpx

from app.scalping.models.intelligence import SpreadSnapshot
from app.scalping.engine.okx_ws_client import _normalize_okx_symbol

logger = logging.getLogger(__name__)

# Base URL pubblica OKX (EEA). Stesso host usato da okx_balance.py e historical_loader.py.
OKX_TICKER_URL = "https://eea.okx.com/api/v5/market/ticker"

# Soglia di anomalia: spread >= ANOMALY_RATIO * media mobile recente.
ANOMALY_RATIO = 3.0
WINDOW_SIZE = 20


class SpreadCollector:
    """Collettore spread bid/ask relativo da OKX public ticker."""

    def __init__(
        self,
        timeout_seconds: float = 10.0,
        max_retries: int = 3,
        window_size: int = WINDOW_SIZE,
        anomaly_ratio: float = ANOMALY_RATIO,
    ):
        self._timeout = timeout_seconds
        self._max_retries = max_retries
        self._window_size = window_size
        self._anomaly_ratio = anomaly_ratio
        self._window: deque = deque(maxlen=window_size)
        from app.scalping.intelligence.collectors.circuit_breaker import CollectorCircuitBreaker
        self._cb = CollectorCircuitBreaker("spread")

    def is_symbol_supported(self, symbol: str) -> bool:
        """Sempre True: il ticker esiste per ogni coppia spot OKX."""
        return True

    async def collect(self, symbol: str = "BTC-USDT") -> Optional[SpreadSnapshot]:
        if not self._cb.is_available():
            return None

        # Normalizza il simbolo nel formato instId OKX (es. OKBEUR -> OKB-EUR).
        # L'engine passa self.symbol gia' uppercase-senza-dash (es. "OKBEUR");
        # OKX richiede il dash per l'endpoint /market/ticker, altrimenti code!=0.
        inst_id = _normalize_okx_symbol(symbol)

        for attempt in range(self._max_retries):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    params = {"instId": inst_id}
                    response = await client.get(OKX_TICKER_URL, params=params)
                    response.raise_for_status()

                    payload = response.json()
                    if payload.get("code") != "0" or not payload.get("data"):
                        logger.debug(
                            "SpreadCollector: empty/invalid ticker for %s code=%s",
                            symbol, payload.get("code"),
                        )
                        return None

                    ticker = payload["data"][0]
                    bid = self._to_decimal(ticker.get("bidPx"))
                    ask = self._to_decimal(ticker.get("askPx"))

                    if bid is None or ask is None or bid <= 0 or ask <= 0:
                        logger.debug("SpreadCollector: invalid bid/ask for %s", symbol)
                        return None

                    mid = (bid + ask) / Decimal("2")
                    if mid <= 0:
                        return None

                    spread_abs = ask - bid
                    spread_pct = float(spread_abs / mid * Decimal("100"))

                    rolling_avg = self._record(spread_pct)
                    ratio = (spread_pct / rolling_avg) if rolling_avg > 0 else 1.0
                    is_anomalous = ratio >= self._anomaly_ratio and self.sample_count >= 2

                    logger.debug(
                        "[COLLECTORS] spread symbol=%s spread_pct=%.4f "
                        "rolling_avg=%.4f ratio=%.2f anomalous=%s (wiring OFF)",
                        inst_id, spread_pct, rolling_avg, ratio, is_anomalous,
                    )

                    return SpreadSnapshot(
                        symbol=inst_id,
                        bid=bid,
                        ask=ask,
                        mid_price=mid,
                        spread_abs=spread_abs,
                        spread_pct=spread_pct,
                        rolling_avg_pct=rolling_avg,
                        ratio_vs_avg=ratio,
                        is_anomalous=is_anomalous,
                        sample_count=self.sample_count,
                        timestamp=datetime.now(timezone.utc),
                    )

            except Exception as e:
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))  # Backoff
                    continue
                logger.warning("SpreadCollector error for %s: %s", symbol, e)
                self._cb.on_failure()
                return None

        return None

    @property
    def sample_count(self) -> int:
        return len(self._window)

    def _record(self, spread_pct: float) -> float:
        """Aggiunge un campione alla finestra mobile e ritorna la media corrente.

        La media è calcolata SU TUTTI i campioni presenti (incluso quello
        appena aggiunto), così il primo campione ha rolling_avg == se stesso.
        """
        self._window.append(spread_pct)
        if not self._window:
            return spread_pct
        return sum(self._window) / len(self._window)

    @staticmethod
    def _to_decimal(value) -> Optional[Decimal]:
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return None
