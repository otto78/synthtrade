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
"""

from datetime import datetime, timezone
from typing import Optional

import httpx

from app.scalping.models.intelligence import FearGreedData

ALTERNATIVE_ME_URL = "https://api.alternative.me/fng/"
LABEL_MAP = {
    "Extreme Fear": "Extreme Fear",
    "Fear": "Fear",
    "Neutral": "Neutral",
    "Greed": "Greed",
    "Extreme Greed": "Extreme Greed",
}


class FearGreedCollector:
    """Collettore Fear & Greed Index da Alternative.me (API pubblica gratuita)."""

    def __init__(self, timeout_seconds: float = 10.0):
        self._timeout = timeout_seconds

    async def collect(self, limit: int = 1) -> Optional[FearGreedData]:
        """Recupera il Fear & Greed Index corrente.

        Args:
            limit: Numero di valori da recuperare (1 = solo l'ultimo).

        Returns:
            FearGreedData se la chiamata ha successo, None altrimenti.
        """
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                params = {"limit": limit, "format": "json"}
                response = await client.get(ALTERNATIVE_ME_URL, params=params)
                response.raise_for_status()

                data = response.json()
                entries = data.get("data", [])
                if not entries:
                    return None

                entry = entries[0]
                value = int(entry.get("value", 50))
                label = entry.get("value_classification", self.classify(value))

                return FearGreedData(
                    value=value,
                    label=label,
                    timestamp=datetime.now(timezone.utc),
                )

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("FearGreedCollector error: %s", e)
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


