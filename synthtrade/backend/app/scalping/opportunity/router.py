"""Opportunity Router (TASK-810).

Smista opportunità per categoria e urgenza.
"""

import logging
from typing import List, Optional, Dict

from app.scalping.models.opportunity import Opportunity, OpportunityCategory, OpportunityUrgency


logger = logging.getLogger(__name__)


class OpportunityRouter:
    """Smista opportunità per categoria e urgenza."""

    def __init__(self):
        self._opportunities: List[Opportunity] = []
        self._watchlist: List[str] = []  # Symbols to watch

    def route(self, opportunity: Opportunity) -> Dict:
        """Smista un'opportunità e restituisce routing info."""
        # Aggiungi alla lista
        self._opportunities.append(opportunity)

        routing_info = {
            "opportunity": opportunity,
            "should_notify": False,
            "should_watchlist": False,
            "action": None,
        }

        # HIGH urgency con simbolo -> notifica immediata
        if opportunity.urgency == OpportunityUrgency.HIGH and opportunity.symbol:
            routing_info["should_notify"] = True
            routing_info["action"] = "notify_frontend"

            if opportunity.category == OpportunityCategory.LISTING:
                routing_info["should_watchlist"] = True
                if opportunity.symbol not in self._watchlist:
                    self._watchlist.append(opportunity.symbol)

        # WHALE con simbolo -> aggiungi a watchlist se non c'è già
        if opportunity.category == OpportunityCategory.WHALE and opportunity.symbol:
            if opportunity.symbol not in self._watchlist:
                self._watchlist.append(opportunity.symbol)
                routing_info["action"] = "add_to_watchlist"

        return routing_info

    def route_batch(self, opportunities: List[Opportunity]) -> List[Dict]:
        """Smista più opportunità."""
        return [self.route(opp) for opp in opportunities]

    def get_opportunities(
        self,
        urgency: Optional[OpportunityUrgency] = None,
        category: Optional[OpportunityCategory] = None,
        limit: int = 50,
    ) -> List[Opportunity]:
        """Recupera opportunità con filtri."""
        result = self._opportunities

        if urgency:
            result = [o for o in result if o.urgency == urgency]
        if category:
            result = [o for o in result if o.category == category]

        # Sort by creation date (newest first)
        result = sorted(result, key=lambda o: o.created_at, reverse=True)

        return result[:limit]

    def get_watchlist(self) -> List[str]:
        """Recupera la watchlist simboli."""
        return self._watchlist.copy()

    def mark_watched(self, opportunity_id: str) -> bool:
        """Segna un'opportunità come watched."""
        for opp in self._opportunities:
            if opp.id == opportunity_id:
                opp.is_watched = True
                return True
        return False

    def mark_ignored(self, opportunity_id: str) -> bool:
        """Segna un'opportunità come ignorata."""
        for opp in self._opportunities:
            if opp.id == opportunity_id:
                opp.is_ignored = True
                return True
        return False

    def clear_old(self, max_age_days: int = 7) -> int:
        """Rimuove opportunità più vecchie di max_age_days."""
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
        original_count = len(self._opportunities)
        self._opportunities = [
            o for o in self._opportunities
            if o.created_at >= cutoff
        ]
        removed = original_count - len(self._opportunities)
        return removed