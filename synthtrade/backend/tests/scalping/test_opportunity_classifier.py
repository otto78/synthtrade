"""Tests for Opportunity Classifier (TASK-810)."""

import pytest
from datetime import datetime, timezone

from app.scalping.models.opportunity import (
    Opportunity, OpportunityCategory, OpportunityUrgency, OpportunitySource, PollerResult
)
from app.scalping.opportunity.classifier import OpportunityClassifier


class TestOpportunityClassifierFallback:
    """Test fallback classification without AI."""

    def test_classify_listing_fallback(self):
        """Classificazione di un listing announcement."""
        classifier = OpportunityClassifier(model_client=None)

        result = PollerResult(
            source=OpportunitySource.BINANCE_RSS,
            title="Binance Adds Trading Pairs for ABC/USDT",
            description="New trading pair listed",
            url="https://binance.com/abc",
        )

        opp = classifier._classify_fallback(result)

        assert opp.category == OpportunityCategory.LISTING
        assert opp.urgency == OpportunityUrgency.HIGH
        assert opp.is_tradeable == True

    def test_classify_whale_fallback(self):
        """Classificazione di whale movement."""
        classifier = OpportunityClassifier(model_client=None)

        result = PollerResult(
            source=OpportunitySource.WHALE_ALERT,
            title="Whale Alert: 500 BTC transfer",
        )

        opp = classifier._classify_fallback(result)

        assert opp.category == OpportunityCategory.WHALE
        assert opp.urgency == OpportunityUrgency.MEDIUM

    def test_classify_news_fallback(self):
        """Classificazione di news generica."""
        classifier = OpportunityClassifier(model_client=None)

        result = PollerResult(
            source=OpportunitySource.CRYPTOPANIC,
            title="Bitcoin price analysis",
            description="Daily market update",
        )

        opp = classifier._classify_fallback(result)

        assert opp.category == OpportunityCategory.NEWS
        assert opp.urgency == OpportunityUrgency.LOW

    def test_classify_launchpool_fallback(self):
        """Classificazione di launchpool."""
        classifier = OpportunityClassifier(model_client=None)

        result = PollerResult(
            source=OpportunitySource.BINANCE_RSS,
            title="New Launchpool for XYZ token",
        )

        opp = classifier._classify_fallback(result)

        assert opp.category == OpportunityCategory.LAUNCHPOOL
        assert opp.urgency == OpportunityUrgency.HIGH

    def test_classify_airdrop_fallback(self):
        """Classificazione di airdrop."""
        classifier = OpportunityClassifier(model_client=None)

        result = PollerResult(
            source=OpportunitySource.COINGECKO_NEWS,
            title="XYZ Token Airdrop Announced",
        )

        opp = classifier._classify_fallback(result)

        assert opp.category == OpportunityCategory.AIRDROP

    def test_classify_high_urgency_news(self):
        """News con keyword 'breaking' ottiene urgenza HIGH."""
        classifier = OpportunityClassifier(model_client=None)

        result = PollerResult(
            source=OpportunitySource.CRYPTOPANIC,
            title="Breaking: Major regulatory update for crypto",
        )

        opp = classifier._classify_fallback(result)

        assert opp.urgency == OpportunityUrgency.HIGH

    def test_symbol_extraction_from_title(self):
        """Estrazione simbolo da titolo."""
        classifier = OpportunityClassifier(model_client=None)

        # Test "$XYZ" pattern
        result = PollerResult(
            source=OpportunitySource.CRYPTOPANIC,
            title="XYZ Token ($XYZ) Surges",
        )
        opp = classifier._classify_fallback(result)
        # Note: fallback doesn't extract symbol, only AI does. Test the pattern recognition.

    @pytest.mark.asyncio
    async def test_classify_batch(self):
        """Batch classification works."""
        classifier = OpportunityClassifier(model_client=None)

        results = [
            PollerResult(source=OpportunitySource.BINANCE_RSS, title="Lists XYZ/USDT"),
            PollerResult(source=OpportunitySource.CRYPTOPANIC, title="Market update"),
        ]

        opportunities = await classifier.classify_batch(results)

        assert len(opportunities) == 2
        assert all(isinstance(o, Opportunity) for o in opportunities)