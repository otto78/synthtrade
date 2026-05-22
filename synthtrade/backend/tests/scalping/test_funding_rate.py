"""Test per FundingRateCollector (TASK-804)."""

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.scalping.intelligence.collectors.funding_rate import (
    FundingRateCollector,
    BINANCE_FUNDING_RATE_URL,
)


class TestFundingRateCollector:
    @pytest.mark.asyncio
    async def test_collect_success(self):
        """Collettore parsa correttamente la risposta Binance."""
        from unittest.mock import MagicMock

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(return_value=[
            {
                "symbol": "BTCUSDT",
                "fundingRate": "0.0001",
                "fundingTime": 1700000000000,
                "nextFundingTime": 1700028000000,
            }
        ])
        mock_response.raise_for_status = MagicMock()

        collector = FundingRateCollector()
        with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_response)):
            result = await collector.collect("BTCUSDT")

        assert result is not None
        assert result.symbol == "BTCUSDT"
        assert result.rate == Decimal("0.0001")
        assert result.next_funding_time is not None

    @pytest.mark.asyncio
    async def test_collect_negative_rate(self):
        """Funding rate negativo correttamente parsato."""
        from unittest.mock import MagicMock

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(return_value=[
            {
                "symbol": "BTCUSDT",
                "fundingRate": "-0.0005",
                "fundingTime": 1700000000000,
            }
        ])
        mock_response.raise_for_status = MagicMock()

        collector = FundingRateCollector()
        with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_response)):
            result = await collector.collect("BTCUSDT")

        assert result is not None
        assert result.rate == Decimal("-0.0005")

    @pytest.mark.asyncio
    async def test_collect_empty_response(self):
        """Risposta vuota ritorna None."""
        from unittest.mock import MagicMock

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(return_value=[])
        mock_response.raise_for_status = MagicMock()

        collector = FundingRateCollector()
        with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_response)):
            result = await collector.collect("BTCUSDT")

        assert result is None

    @pytest.mark.asyncio
    async def test_collect_http_error(self):
        """Errore HTTP ritorna None senza sollevare eccezioni."""
        from unittest.mock import MagicMock

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock(
            side_effect=Exception("HTTP 429 Too Many Requests")
        )

        collector = FundingRateCollector()
        with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_response)):
            result = await collector.collect("BTCUSDT")

        assert result is None

    def test_interpret_rate_strong_short(self):
        """> 0.10% = strong_short."""
        assert FundingRateCollector.interpret_rate(Decimal("0.0015")) == "strong_short"

    def test_interpret_rate_short(self):
        """> 0.05% = short."""
        assert FundingRateCollector.interpret_rate(Decimal("0.0007")) == "short"

    def test_interpret_rate_neutral(self):
        """0.03% = neutral."""
        assert FundingRateCollector.interpret_rate(Decimal("0.0003")) == "neutral"

    def test_interpret_rate_long(self):
        """< -0.05% = long."""
        assert FundingRateCollector.interpret_rate(Decimal("-0.0007")) == "long"

    def test_interpret_rate_strong_long(self):
        """< -0.10% = strong_long."""
        assert FundingRateCollector.interpret_rate(Decimal("-0.0015")) == "strong_long"

    def test_rate_to_score_positive(self):
        """Funding rate positivo -> score negativo (bearish)."""
        score = FundingRateCollector.rate_to_score(Decimal("0.0001"))
        assert score < 0
        assert -25.0 <= score <= 0

    def test_rate_to_score_negative(self):
        """Funding rate negativo -> score positivo (bullish)."""
        score = FundingRateCollector.rate_to_score(Decimal("-0.0001"))
        assert score > 0
        assert 0 <= score <= 25.0

    def test_rate_to_score_zero(self):
        """Funding rate zero -> score zero."""
        score = FundingRateCollector.rate_to_score(Decimal("0"))
        assert score == 0.0

    def test_rate_to_score_clamped(self):
        """Score non supera +/- 25."""
        score = FundingRateCollector.rate_to_score(Decimal("0.002"))
        assert -25.0 <= score <= 25.0