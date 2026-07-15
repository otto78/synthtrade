"""FearGreedCollector — usa alternative.me (gratuita, no API key).

Endpoint: GET https://api.alternative.me/fng/?limit=1
Risposta:
{
  "data": [{
    "value": "34",
    "value_classification": "Fear",
    "timestamp": "1718000000"
  }]
}

Aggiornamento: 1 volta ogni 24h (cacheare il valore intraday).
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta, timezone
from app.scalping.models.intelligence import FearGreedData

logger = logging.getLogger(__name__)

ALTERNATIVE_ME_URL = "https://api.alternative.me/fng/?limit=1"

# Cache intraday: il valore cambia al massimo 1 volta al giorno
_cached_value: int | None = None
_cached_at: datetime | None = None
_CACHE_TTL = timedelta(hours=4)  # rileggi ogni 4h per sicurezza


class FearGreedCollector:

    def __init__(self, timeout_seconds: float = 10.0, max_retries: int = 3):
        self._timeout = timeout_seconds
        self._max_retries = max_retries
        from app.scalping.intelligence.collectors.circuit_breaker import CollectorCircuitBreaker
        self._cb = CollectorCircuitBreaker("fear_greed")

    async def collect(self, limit: int = 1) -> FearGreedData | None:
        if not self._cb.is_available():
            return None
        global _cached_value, _cached_at

        # Usa cache se valida
        if _cached_value is not None and _cached_at is not None:
            if datetime.now(timezone.utc) - _cached_at < _CACHE_TTL:
                self._cb.on_success()
                return FearGreedData(
                    value=_cached_value,
                    label=self._classify(_cached_value),
                    timestamp=_cached_at,
                )

        for attempt in range(self._max_retries):
            try:
                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self._timeout)
                ) as session:
                    async with session.get(ALTERNATIVE_ME_URL) as resp:
                        if resp.status != 200:
                            logger.warning("FearGreed alternative.me: HTTP %d", resp.status)
                            return self._use_cache_or_none()
                        data = await resp.json()
                        value = int(data["data"][0]["value"])
                        _cached_value = value
                        _cached_at = datetime.now(timezone.utc)
                        logger.info("FearGreed aggiornato: %d (%s)", value, self._classify(value))
                        self._cb.on_success()
                        return FearGreedData(
                            value=value,
                            label=self._classify(value),
                            timestamp=_cached_at,
                        )
            except Exception as e:
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))  # Backoff
                    continue
                logger.warning("FearGreed alternative.me error: %s", e, exc_info=True)
                return self._use_cache_or_none()

    def _use_cache_or_none(self) -> FearGreedData | None:
        if _cached_value is not None:
            logger.info("FearGreed: uso cache (valore=%d)", _cached_value)
            return FearGreedData(
                value=_cached_value,
                label=self._classify(_cached_value),
                timestamp=_cached_at or datetime.now(timezone.utc),
            )
        logger.warning("FearGreed: nessun dato disponibile (né live né cache)")
        return None

    @staticmethod
    def _classify(value: int) -> str:
        if value <= 20:   return "Extreme Fear"
        if value <= 40:   return "Fear"
        if value <= 60:   return "Neutral"
        if value <= 80:   return "Greed"
        return "Extreme Greed"

    @staticmethod
    def value_to_score(value: int) -> float:
        """Converte Fear & Greed (0-100) in score (-100 a +100).
        
        Logica contrarian:
          < 20 (Extreme Fear)  → score positivo (opportunità long)
          > 80 (Extreme Greed) → score negativo (cautela)
          40-60 (Neutral)      → score vicino a 0
        """
        if value < 20:
            return (20 - value) * 5.0          # max +100 a value=0
        elif value > 80:
            return -(value - 80) * 5.0         # max -100 a value=100
        elif value < 40:
            return (40 - value) * 1.5          # +30 max a value=20
        elif value > 60:
            return -(value - 60) * 1.5         # -30 max a value=80
        return 0.0
