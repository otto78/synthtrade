"""Test per SignalScoreEngine (TASK-804)."""

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.scalping.intelligence.signal_score_engine import (
    DEFAULT_WEIGHTS,
    SignalScoreEngine,
)
from app.scalping.intelligence.collectors.cvd_calculator import CVDCalculator


class TestDefaultWeights:
    def test_weights_non_negative_and_complete(self):
        """Tutti i pesi attesi presenti e >= 0.

        NOTA: i pesi sono RELATIVI e normalizzati dall'engine (divide per il
        total_weight dei collector che hanno effettivamente risposto), quindi
        la somma NON deve essere 1.0. order_book_imbalance (TASK-1151) aggiunge
        0.15 come peso provvisorio, da ricalibrare in Fase 6.
        """
        expected_keys = {
            "funding_rate", "cvd", "open_interest", "long_short_ratio",
            "fear_greed", "onchain", "sentiment", "whale", "order_book_imbalance",
        }
        assert DEFAULT_WEIGHTS.keys() == expected_keys
        for name, w in DEFAULT_WEIGHTS.items():
            assert w >= 0.0, f"weight {name} must be >= 0"

    def test_order_book_imbalance_provisional_weight(self):
        """TASK-1151: order_book_imbalance ha peso provvisorio 0.15 (da ricalibrare Fase 6)."""
        assert DEFAULT_WEIGHTS["order_book_imbalance"] == 0.15


class TestSignalScoreEngine:
    @pytest.mark.asyncio
    async def test_compute_all_collectors_fail(self):
        """Se tutti i collector falliscono, score neutrale e non tradeable."""
        engine = SignalScoreEngine(symbol="BTCUSDT", threshold=30.0)

        # Mock tutti i collector per fallire
        engine._funding_rate.collect = AsyncMock(return_value=None)
        engine._open_interest.collect = AsyncMock(return_value=None)
        engine._long_short.collect = AsyncMock(return_value=None)
        engine._fear_greed.collect = AsyncMock(return_value=None)
        engine._sentiment.collect = AsyncMock(return_value=None)
        engine._whale.collect = AsyncMock(return_value=None)
        engine._onchain.collect = AsyncMock(return_value=None)
        engine._order_book_imbalance.collect = AsyncMock(return_value=None)

        score = await engine.compute()

        assert score.total == 0.0
        assert score.bias == "neutral"
        assert score.tradeable is False
        assert len(score.breakdown) == 0

    @pytest.mark.asyncio
    async def test_compute_bullish_scenario(self):
        """Scenario rialzista: funding rate negativo + CVD positivo."""
        from datetime import datetime, timezone
        from app.scalping.models.intelligence import FundingRate, OpenInterest, LongShortRatio, FearGreedData

        engine = SignalScoreEngine(symbol="BTCUSDT", threshold=30.0)

        # Mock funding rate negativo (bullish)
        engine._funding_rate.collect = AsyncMock(return_value=FundingRate(
            rate=Decimal("-0.0005"), symbol="BTCUSDT", timestamp=datetime.now(timezone.utc)
        ))

        # Mock OI stabile
        engine._open_interest.collect = AsyncMock(return_value=OpenInterest(
            value_usd=Decimal("1000000000"), symbol="BTCUSDT", timestamp=datetime.now(timezone.utc)
        ))

        # Mock L/S con piu short (bullish)
        engine._long_short.collect = AsyncMock(return_value=LongShortRatio(
            long_pct=Decimal("35"), short_pct=Decimal("65"),
            symbol="BTCUSDT", timestamp=datetime.now(timezone.utc)
        ))

        # Mock Fear & Greed (paura = long bias)
        engine._fear_greed.collect = AsyncMock(return_value=FearGreedData(
            value=20, label="Extreme Fear", timestamp=datetime.now(timezone.utc)
        ))

        # Mock remaining collectors to None
        engine._sentiment.collect = AsyncMock(return_value=None)
        engine._whale.collect = AsyncMock(return_value=None)
        engine._onchain.collect = AsyncMock(return_value=None)
        engine._order_book_imbalance.collect = AsyncMock(return_value=None)

        score = await engine.compute()

        assert score.total > 0  # Score positivo = bullish
        assert score.bias == "bullish"
        assert len(score.breakdown) > 0

    @pytest.mark.asyncio
    async def test_compute_bearish_scenario(self):
        """Scenario ribassista: funding rate alto positivo + L/S long-heavy."""
        from datetime import datetime, timezone
        from app.scalping.models.intelligence import FundingRate, OpenInterest, LongShortRatio, FearGreedData

        engine = SignalScoreEngine(symbol="BTCUSDT", threshold=30.0)

        # Mock funding rate positivo alto (bearish)
        engine._funding_rate.collect = AsyncMock(return_value=FundingRate(
            rate=Decimal("0.001"), symbol="BTCUSDT", timestamp=datetime.now(timezone.utc)
        ))

        # Mock OI molto alto (bearish)
        engine._open_interest.collect = AsyncMock(return_value=OpenInterest(
            value_usd=Decimal("2000000000"), symbol="BTCUSDT", timestamp=datetime.now(timezone.utc)
        ))

        # Mock L/S con > 70% long (bearish)
        engine._long_short.collect = AsyncMock(return_value=LongShortRatio(
            long_pct=Decimal("80"), short_pct=Decimal("20"),
            symbol="BTCUSDT", timestamp=datetime.now(timezone.utc)
        ))

        # Mock Fear & Greed (euforia = short bias)
        engine._fear_greed.collect = AsyncMock(return_value=FearGreedData(
            value=85, label="Extreme Greed", timestamp=datetime.now(timezone.utc)
        ))

        # Mock remaining collectors to None
        engine._sentiment.collect = AsyncMock(return_value=None)
        engine._whale.collect = AsyncMock(return_value=None)
        engine._onchain.collect = AsyncMock(return_value=None)
        engine._order_book_imbalance.collect = AsyncMock(return_value=None)

        score = await engine.compute()

        assert score.total < 0  # Score negativo = bearish
        assert score.bias == "bearish"
        assert len(score.breakdown) > 0

    @pytest.mark.asyncio
    async def test_compute_with_cvd(self):
        """CVDCalculator collegato contribuisce allo score."""
        from datetime import datetime, timezone

        engine = SignalScoreEngine(symbol="BTCUSDT", threshold=30.0)

        # Crea CVDCalculator con abbastanza trades da superare il grace period (100)
        cvd = CVDCalculator()
        for _ in range(101):
            cvd.on_trade(price=50000, quantity=1000, is_buyer_maker=False)  # buy pressure

        engine._set_cvd_calculator(cvd)

        # Mock altri collector a None (solo CVD attivo)
        engine._funding_rate.collect = AsyncMock(return_value=None)
        engine._open_interest.collect = AsyncMock(return_value=None)
        engine._long_short.collect = AsyncMock(return_value=None)
        engine._fear_greed.collect = AsyncMock(return_value=None)
        engine._sentiment.collect = AsyncMock(return_value=None)
        engine._whale.collect = AsyncMock(return_value=None)
        engine._onchain.collect = AsyncMock(return_value=None)
        engine._order_book_imbalance.collect = AsyncMock(return_value=None)

        score = await engine.compute()

        assert "cvd" in score.breakdown
        assert score.breakdown["cvd"] > 0  # CVD positivo = bullish

    @pytest.mark.asyncio
    async def test_get_snapshot_structure(self):
        """Verifica che get_snapshot restituisca un MarketIntelSnapshot completo."""
        from datetime import datetime, timezone
        from app.scalping.models.intelligence import MarketIntelSnapshot, FundingRate

        engine = SignalScoreEngine(symbol="BTCUSDT", threshold=30.0)
        
        # Mock collectors per ritornare qualcosa di semplice
        engine._funding_rate.collect = AsyncMock(return_value=FundingRate(
            rate=Decimal("0"), symbol="BTCUSDT", timestamp=datetime.now(timezone.utc)
        ))
        engine._open_interest.collect = AsyncMock(return_value=None)
        engine._long_short.collect = AsyncMock(return_value=None)
        engine._fear_greed.collect = AsyncMock(return_value=None)
        engine._sentiment.collect = AsyncMock(return_value=None)
        engine._whale.collect = AsyncMock(return_value=None)
        engine._onchain.collect = AsyncMock(return_value=None)
        engine._order_book_imbalance.collect = AsyncMock(return_value=None)

        snapshot = await engine.get_snapshot()
        
        assert isinstance(snapshot, MarketIntelSnapshot)
        assert snapshot.symbol == "BTCUSDT"
        assert snapshot.funding_rate is not None
        assert snapshot.signal_score is not None
        assert snapshot.sentiment is None # Come da mock

    @pytest.mark.asyncio
    async def test_get_snapshot_cache_hit(self):
        """Seconda chiamata senza force_refresh usa la cache (no refetch collector)."""
        from datetime import datetime, timezone
        from app.scalping.models.intelligence import FundingRate

        engine = SignalScoreEngine(symbol="BTCUSDT", threshold=30.0)
        engine._funding_rate.collect = AsyncMock(return_value=FundingRate(
            rate=Decimal("0"), symbol="BTCUSDT", timestamp=datetime.now(timezone.utc)
        ))
        engine._open_interest.collect = AsyncMock(return_value=None)
        engine._long_short.collect = AsyncMock(return_value=None)
        engine._fear_greed.collect = AsyncMock(return_value=None)
        engine._sentiment.collect = AsyncMock(return_value=None)
        engine._whale.collect = AsyncMock(return_value=None)
        engine._onchain.collect = AsyncMock(return_value=None)
        engine._order_book_imbalance.collect = AsyncMock(return_value=None)

        first = await engine.get_snapshot(force_refresh=True)
        second = await engine.get_snapshot()

        assert first is second
        engine._funding_rate.collect.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_snapshot_force_refresh_bypasses_cache(self):
        """force_refresh=True invalida la cache e richiama i collector."""
        from datetime import datetime, timezone
        from app.scalping.models.intelligence import FundingRate

        engine = SignalScoreEngine(symbol="BTCUSDT", threshold=30.0)
        engine._funding_rate.collect = AsyncMock(return_value=FundingRate(
            rate=Decimal("0"), symbol="BTCUSDT", timestamp=datetime.now(timezone.utc)
        ))
        engine._open_interest.collect = AsyncMock(return_value=None)
        engine._long_short.collect = AsyncMock(return_value=None)
        engine._fear_greed.collect = AsyncMock(return_value=None)
        engine._sentiment.collect = AsyncMock(return_value=None)
        engine._whale.collect = AsyncMock(return_value=None)
        engine._onchain.collect = AsyncMock(return_value=None)
        engine._order_book_imbalance.collect = AsyncMock(return_value=None)

        await engine.get_snapshot(force_refresh=True)
        await engine.get_snapshot(force_refresh=True)

        assert engine._funding_rate.collect.call_count == 2