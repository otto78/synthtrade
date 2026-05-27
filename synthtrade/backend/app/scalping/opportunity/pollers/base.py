"""Base poller class."""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Optional

from app.scalping.models.opportunity import PollerResult, OpportunitySource


logger = logging.getLogger(__name__)


class BasePoller(ABC):
    """Classe base per tutti i poller."""

    def __init__(self, source: OpportunitySource):
        self.source = source
        self._last_run: Optional[datetime] = None
        self._last_hash: Optional[str] = None

    @abstractmethod
    async def fetch(self) -> List[PollerResult]:
        """Recupera nuovi contenuti dalla fonte."""
        pass

    @abstractmethod
    def get_default_interval(self) -> int:
        """Restituisce l'intervallo di polling in secondi."""
        pass

    async def run_once(self) -> List["PollerResult"]:
        """Esegue un'unica iterazione del poller."""
        try:
            results = await self.fetch()
            self._last_run = datetime.now(timezone.utc)
            logger.info(f"{self.source.value}: {len(results)} items fetched")
            return results
        except Exception as e:
            logger.error(f"{self.source.value} poller error: {e}")
            return []

    def should_run(self, interval_seconds: int) -> bool:
        """Verifica se è il momento di eseguire il polling."""
        if self._last_run is None:
            return True
        elapsed = (datetime.now(timezone.utc) - self._last_run).total_seconds()
        return elapsed >= interval_seconds