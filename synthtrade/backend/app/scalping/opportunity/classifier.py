"""Opportunity Classifier (TASK-810).

Classifica opportunità usando AI (ModelClient).
"""

import logging
from typing import Optional, List

from app.scalping.models.opportunity import (
    PollerResult, Opportunity, OpportunityCategory, OpportunityUrgency, OpportunitySource
)
from app.ai.model_client import ModelClient


logger = logging.getLogger(__name__)


class OpportunityClassifier:
    """Classifica opportunità usando Claude API."""

    def __init__(self, model_client: Optional[ModelClient] = None):
        self.model_client = model_client

    CLASSIFIER_PROMPT = """You are a crypto trading opportunity classifier. Analyze the following news/trending item and classify it.

Respond with JSON containing:
- category: one of [listing, launchpool, news, whale, airdrop, staking, delisting, other]
- urgency: one of [HIGH, MEDIUM, LOW]
- is_tradeable: boolean
- confidence_score: 0-100

Focus on whether this represents a tradable opportunity for a scalping bot.
- listing/launchpool/airdrop/staking: HIGH urgency if new token, tradeable
- whale: HIGH if large transfer to/from exchange, tradeable
- news: MEDIUM if general market news, LOW if irrelevant
- delisting: HIGH urgency, not tradeable (avoid)

Item to classify:
Title: {title}
Description: {description}
Source: {source}
"""

    async def classify(self, result: PollerResult) -> Opportunity:
        """Classifica un risultato poller in un'opportunità."""
        # Default classification based on keywords if no AI
        if not self.model_client:
            return self._classify_fallback(result)

        try:
            prompt = self.CLASSIFIER_PROMPT.format(
                title=result.title,
                description=result.description or "N/A",
                source=result.source.value,
            )

            response = await self.model_client.call_with_fallback(
                system="You are a crypto trading opportunity classifier. Respond only with valid JSON.",
                user=prompt,
            )

            # Parse response - expect JSON
            import json
            data = json.loads(response.content)

            return Opportunity(
                symbol=result.symbol,
                category=OpportunityCategory(data.get("category", "other")),
                urgency=OpportunityUrgency(data.get("urgency", "LOW")),
                source=result.source,
                title=result.title,
                description=result.description,
                url=result.url,
                published_at=result.published_at,
                is_tradeable=data.get("is_tradeable", False),
                confidence_score=data.get("confidence_score"),
                ai_reasoning=response.content,
            )

        except Exception as e:
            logger.warning(f"Classifier AI failed: {e}, using fallback")
            return self._classify_fallback(result)

    def _classify_fallback(self, result: PollerResult) -> Opportunity:
        """Classificazione heuristica senza AI."""
        title_lower = result.title.lower()
        desc_lower = (result.description or "").lower()
        combined = f"{title_lower} {desc_lower}"

        # Determine category from keywords
        if "list" in combined or "trading pair" in combined:
            category = OpportunityCategory.LISTING
        elif "launchpool" in combined or "savings" in combined:
            category = OpportunityCategory.LAUNCHPOOL
        elif "airdrop" in combined:
            category = OpportunityCategory.AIRDROP
        elif "staking" in combined:
            category = OpportunityCategory.STAKING
        elif "delist" in combined:
            category = OpportunityCategory.DELISTING
        elif result.source == OpportunitySource.WHALE_ALERT:
            category = OpportunityCategory.WHALE
        else:
            category = OpportunityCategory.NEWS

        # Determine urgency
        urgency = OpportunityUrgency.LOW
        if category in (OpportunityCategory.LISTING, OpportunityCategory.LAUNCHPOOL, OpportunityCategory.AIRDROP):
            urgency = OpportunityUrgency.HIGH
        elif category == OpportunityCategory.WHALE:
            urgency = OpportunityUrgency.MEDIUM
        elif category == OpportunityCategory.NEWS:
            # Check for keywords that indicate high impact
            if any(kw in combined for kw in ["breaking", "major", "significant", "regulatory", "etf", "approval"]):
                urgency = OpportunityUrgency.HIGH

        # Tradeable for certain categories
        is_tradeable = category in (OpportunityCategory.LISTING, OpportunityCategory.LAUNCHPOOL)

        return Opportunity(
            symbol=result.symbol,
            category=category,
            urgency=urgency,
            source=result.source,
            title=result.title,
            description=result.description,
            url=result.url,
            published_at=result.published_at,
            is_tradeable=is_tradeable,
            confidence_score=50.0 if is_tradeable else 30.0,
        )

    async def classify_batch(self, results: List[PollerResult]) -> List[Opportunity]:
        """Classifica più risultati."""
        opportunities = []
        for result in results:
            opp = await self.classify(result)
            opportunities.append(opp)
        return opportunities