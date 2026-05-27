"""Deduplicator per Opportunity Monitor (TASK-810).

Evita duplicati cross-source usando hash del contenuto.
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import List, Set, Optional

from app.scalping.models.opportunity import PollerResult, Opportunity


logger = logging.getLogger(__name__)


class Deduplicator:
    """Rimuove opportunità duplicate tra diverse fonti."""

    def __init__(self):
        self._seen_hashes: Set[str] = set()
        self._max_cache_size: int = 10000

    def process(self, results: List[PollerResult]) -> List[PollerResult]:
        """Filtra i risultati per rimuovere duplicati."""
        unique = []
        for result in results:
            content_hash = self._compute_hash_result(result)
            if content_hash not in self._seen_hashes:
                self._seen_hashes.add(content_hash)
                unique.append(result)

        # Limita cache size
        if len(self._seen_hashes) > self._max_cache_size:
            self._seen_hashes = set(list(self._seen_hashes)[-self._max_cache_size // 2:])

        return unique

    def _compute_hash_result(self, result: PollerResult) -> str:
        """Calcola hash unico per un risultato poller."""
        content = f"{result.title}"
        return hashlib.md5(content.encode()).hexdigest()

    def is_duplicate(self, opportunity: Opportunity) -> bool:
        """Verifica se un'opportunità è già stata vista."""
        content = f"{opportunity.title}"
        content_hash = hashlib.md5(content.encode()).hexdigest()
        return content_hash in self._seen_hashes

    def mark_seen(self, opportunity: Opportunity) -> None:
        """Segna un'opportunità come vista."""
        content = f"{opportunity.title}"
        content_hash = hashlib.md5(content.encode()).hexdigest()
        self._seen_hashes.add(content_hash)