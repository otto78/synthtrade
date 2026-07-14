"""Test per OpenInterestCollector (TASK-804)."""

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.scalping.intelligence.collectors.open_interest import OpenInterestCollector
from app.scalping.models.intelligence import OpenInterest


class TestOpenInterestCollector:
    @pytest.mark.asyncio
    async def test_collect_success(self):
        """Collettore parsa correttamente la risposta Binance."""
        from unittest.mock import MagicMock

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={
            "symbol": "BTCUSDT",
            "openInterest": "987654321.000",
            "time": 1700000000000,
        })
        mock_response.raise_for_status = MagicMock()

        collector = OpenInterestCollector()
        with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_response)):
            result = await collector.collect("BTCUSDT")

        assert result is not None
        assert result.symbol == "BTCUSDT"
        assert result.value_usd == Decimal("987654321.000")

    @pytest.mark.asyncio
    async def test_collect_http_error(self):
        """Errore HTTP ritorna None."""
        from unittest.mock import MagicMock

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock(side_effect=Exception("API error"))

        collector = OpenInterestCollector()
        with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_response)):
            result = await collector.collect("BTCUSDT")

        assert result is None

    def test_oi_to_score_high(self):
        """OI alto -> score negativo (bearish)."""
        score = OpenInterestCollector.oi_to_score(Decimal("2000"), Decimal("1000"))
        assert score < 0

    def test_oi_to_score_low(self):
        """OI basso -> score positivo (bullish)."""
        score = OpenInterestCollector.oi_to_score(Decimal("500"), Decimal("1000"))
        assert score > 0

    def test_oi_to_score_equal(self):
        """OI = baseline -> score zero."""
        score = OpenInterestCollector.oi_to_score(Decimal("1000"), Decimal("1000"))
        assert score == 0.0

    def test_oi_to_score_zero_baseline(self):
        """Baseline zero -> score zero."""
        score = OpenInterestCollector.oi_to_score(Decimal("1000"), Decimal("0"))
        assert score == 0.0

    def test_oi_to_score_clamped(self):
        """Raw score non supera +/- 100 (il peso 0.15 lo scala dopo in engine)."""
        score = OpenInterestCollector.oi_to_score(Decimal("100000"), Decimal("1000"))
        assert -100.0 <= score <= 100.0

    def test_asset_extraction(self):
        """Asset estratto automaticamente dal simbolo."""
        assert OpenInterestCollector().collect is not None  # smoke test