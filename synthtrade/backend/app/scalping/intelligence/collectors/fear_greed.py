"""FearGreedCollector — recupera Fear & Greed Index da Alternative.me API.

Documentazione API:
  https://api.alternative.me/fng/
  https://alternative.me/crypto/fear-and-greed-index/

Valori:
  0-24  = Extreme Fear
  25-44 = Fear
  45-54 = Neutral
  55-74 = Greed
  75-100 = Extreme Greed

NOTA: Il valore viene cachato per 5 minuti (l'indice si aggiorna ogni ora).
      In caso di errore, viene usato il valore in cache se disponibile.
      Sono previsti fino a 2 retry con 2s di backoff.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.scalping.models.intelligence import FearGreedData

logger = logging.getLogger(__name__)

ALTERNATIVE_ME_URL = "https://api.alternative.me/fng/"
_CACHE_TTL_SECONDS = 300  # 5 minuti


class FearGreedCollector:
    """Collettore Fear & Greed Index da Alternative.me (API pubblica gratuita).

    Implementa caching (5 min) e retry (2×, 2s backoff) per gestire
    l'instabilità dell'endpoint pubblico.
    """

    def __init__(self, timeout_seconds: float = 10.0):
        self._timeout = timeout_seconds
        self._cached_value: Optional[FearGreedData] = None
        self._cached_at: float = 0.0

    async def collect(self, limit: int = 1) -> Optional[FearGreedData]:
        """Recupera il Fear & Greed Index corrente.

        Usa la cache se il dato ha meno di 5 minuti.
        Fa fino a 2 retry in caso di errore.
        Se fallisce ma ha un valore cachato (anche scaduto), lo ritorna comunque.

        Returns:
            FearGreedData se disponibile, None solo se mai ricevuto un dato.
        """
        # Controlla cache valida
        now = time.monotonic()
        if self._cached_value is not None and (now - self._cached_at) < _CACHE_TTL_SECONDS:
            logger.debug("FearGreed: cache hit (age=%.0fs)", now - self._cached_at)
            return self._cached_value

        # Fetch con retry
        last_error = None
        for attempt in range(3):  # 1 tentativo + 2 retry
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    params = {"limit": limit, "format": "json"}
                    response = await client.get(ALTERNATIVE_ME_URL, params=params)
                    response.raise_for_status()

                    data = response.json()
                    entries = data.get("data", [])
                    if not entries:
                        break

                    entry = entries[0]
                    value = int(entry.get("value", 50))
                    label = entry.get("value_classification", self.classify(value))

                    result = FearGreedData(
                        value=value,
                        label=label,
                        timestamp=datetime.now(timezone.utc),
                    )
                    # Aggiorna cache
                    self._cached_value = result
                    self._cached_at = now
                    logger.debug("FearGreed: fetched value=%d label=%s", value, label)
                    return result

            except asyncio.CancelledError:
                raise
            except Exception as e:
                last_error = e
                if attempt < 2:
                    logger.debug("FearGreed attempt %d failed: %s — retrying in 2s", attempt + 1, e)
                    await asyncio.sleep(2)

        # Tutti i tentativi falliti
        if self._cached_value is not None:
            logger.warning(
                "FearGreedCollector: fetch failed (%s) — usando valore cachato (age=%.0fs, value=%d)",
                last_error, now - self._cached_at, self._cached_value.value
            )
            return self._cached_value

        logger.warning("FearGreedCollector: fetch failed e nessuna cache disponibile: %s", last_error)
        return None

    @staticmethod
    def classify(value: int) -> str:
        """Classifica un valore numerico in label Fear & Greed."""
        if value <= 24:
            return "Extreme Fear"
        elif value <= 44:
            return "Fear"
        elif value <= 54:
            return "Neutral"
        elif value <= 74:
            return "Greed"
        return "Extreme Greed"

    @staticmethod
    def fng_to_score(value: int) -> float:
        """Converte Fear & Greed in contributo score (-10 a +10).

        Estremi (Fear < 20 o Greed > 80) = potenziale inversione -> bias contrarian.
        """
        if value >= 80:  # Extreme Greed -> mercato euforico -> short bias
            return -10.0
        elif value >= 65:  # Greed -> leggero short bias
            return -3.0
        elif value >= 45:  # Neutral
            return 0.0
        elif value >= 25:  # Fear -> leggero long bias
            return 3.0
        else:  # Extreme Fear -> long bias
            return 10.0
