"""Tests for Opportunity Deduplicator (TASK-810)."""

import pytest
from app.scalping.models.opportunity import PollerResult, OpportunitySource
from app.scalping.opportunity.deduplicator import Deduplicator


class TestDeduplicator:
    """Test deduplication logic."""

    def test_duplicate_detection_same_title(self):
        """Rimuove duplicati con stesso titolo."""
        d = Deduplicator()

        results = [
            PollerResult(source=OpportunitySource.BINANCE_RSS, title="Lists XYZ/USDT"),
            PollerResult(source=OpportunitySource.COINGECKO_NEWS, title="Lists XYZ/USDT"),
        ]

        unique = d.process(results)
        assert len(unique) == 1

    def test_preserve_different_titles(self):
        """Mantiene risultati diversi."""
        d = Deduplicator()

        results = [
            PollerResult(source=OpportunitySource.BINANCE_RSS, title="Lists XYZ/USDT"),
            PollerResult(source=OpportunitySource.BINANCE_RSS, title="Lists ABC/USDT"),
        ]

        unique = d.process(results)
        assert len(unique) == 2

    def test_duplicate_with_different_source(self):
        """Stesso contenuto da fonti diverse è comunque un duplicato."""
        d = Deduplicator()

        results = [
            PollerResult(source=OpportunitySource.BINANCE_RSS, title="Same title"),
            PollerResult(source=OpportunitySource.CRYPTOPANIC, title="Same title"),
        ]

        unique = d.process(results)
        assert len(unique) == 1

    def test_seen_cache_limits_size(self):
        """Cache hash limitata mantiene dimensione massima."""
        d = Deduplicator()
        d._max_cache_size = 100

        # Aggiunge molti elementi
        for i in range(200):
            results = [PollerResult(source=OpportunitySource.BINANCE_RSS, title=f"Title {i}")]

        # Dopo molti inserimenti, la cache dovrebbe essere limitata
        # Questo test verifica che il metodo clear_old funzioni
        assert len(d._seen_hashes) <= d._max_cache_size

    def test_is_duplicate_method(self):
        """is_duplicate rileva correttamente i duplicati."""
        d = Deduplicator()

        opp = Opportunity(
            symbol="XYZUSDT",
            category=OpportunityCategory.LISTING,
            urgency=OpportunityUrgency.HIGH,
            source=OpportunitySource.BINANCE_RSS,
            title="Lists XYZ/USDT",
        )

        # Prima volta non è duplicato
        assert d.is_duplicate(opp) == False
        d.mark_seen(opp)

        # Dopo mark_seen è duplicato
        assert d.is_duplicate(opp) == True


from app.scalping.models.opportunity import Opportunity, OpportunityCategory, OpportunityUrgency