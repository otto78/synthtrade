"""Opportunity Scheduler (TASK-810).

Polling periodico ogni 5 minuti.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional

from app.scalping.opportunity.pollers.base import BasePoller
from app.scalping.opportunity.pollers.binance_rss import BinanceRSSPoller
from app.scalping.opportunity.pollers.coingecko import CoinGeckoPoller
from app.scalping.opportunity.pollers.whale_alert import WhaleAlertPoller
from app.scalping.opportunity.pollers.news import NewsPoller
from app.scalping.opportunity.deduplicator import Deduplicator
from app.scalping.opportunity.classifier import OpportunityClassifier
from app.scalping.opportunity.router import OpportunityRouter
from app.scalping.models.opportunity import PollerResult


logger = logging.getLogger(__name__)


class OpportunityScheduler:
    """Scheduler per polling ogni 5 minuti."""

    DEFAULT_INTERVAL = 300  # 5 minuti

    def __init__(
        self,
        deduplicator: Optional[Deduplicator] = None,
        classifier: Optional[OpportunityClassifier] = None,
        router: Optional[OpportunityRouter] = None,
    ):
        self.pollers: List[BasePoller] = []
        self.deduplicator = deduplicator or Deduplicator()
        self.classifier = classifier or OpportunityClassifier()
        self.router = router or OpportunityRouter()
        self._running = False
        self._task: Optional[asyncio.Task] = None

        # Initialize default pollers
        self._setup_default_pollers()

    def _setup_default_pollers(self):
        """Inizializza i poller di default."""
        self.pollers = [
            BinanceRSSPoller(),
            CoinGeckoPoller(),
            WhaleAlertPoller(),
            NewsPoller(),
        ]

    async def run_once(self) -> List[PollerResult]:
        """Esegue un'unica iterazione: fetch -> deduplicate -> classify -> route."""
        all_results: List[PollerResult] = []

        # Fetch from all pollers
        for poller in self.pollers:
            results = await poller.run_once()
            all_results.extend(results)

        logger.info(f"OpportunityScheduler: {len(all_results)} raw results")

        # Deduplicate
        unique_results = self.deduplicator.process(all_results)
        logger.info(f"OpportunityScheduler: {len(unique_results)} unique results")

        # Classify
        opportunities = await self.classifier.classify_batch(unique_results)

        # Route
        for opp in opportunities:
            self.router.route(opp)

        return unique_results

    async def start(self, interval: Optional[int] = None):
        """Avvia il polling periodico."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop(interval), name="opportunity-scheduler")
        logger.info(f"OpportunityScheduler started (interval: {interval or self.DEFAULT_INTERVAL}s)")

    async def _run_loop(self, interval: Optional[int] = None):
        """Loop di polling."""
        while self._running:
            try:
                await self.run_once()
            except Exception as e:
                logger.error(f"OpportunityScheduler loop error: {e}")

            await asyncio.sleep(interval or self.DEFAULT_INTERVAL)

    async def stop(self):
        """Ferma il polling."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        logger.info("OpportunityScheduler stopped")

    def get_pollers(self) -> List[BasePoller]:
        """Recupera i poller registrati."""
        return self.pollers

    def add_poller(self, poller: BasePoller):
        """Aggiunge un poller personalizzato."""
        self.pollers.append(poller)