"""Test per LongShortRatioCollector (TASK-804)."""

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.scalping.intelligence.collectors.long_short_ratio import (
    LongShortRatioCollector,
)


class TestLongShortRatioCollector:
    @pytest.mark.asyncio
    async def test_collect_success(self):
        """Collettore parsa correttamente la risposta Binance."""
        from unittest.mock import MagicMock

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(return_value=[
            {
                "symbol": "BTCUSDT",
                "longAccount": "65.5",
                "shortAccount": "34.5",
                "timestamp": 1700000000000,
            }
        ])
        mock_response.raise_for_status = MagicMock()

        collector = LongShortRatioCollector()
        with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_response)):
            result = await collector.collect("BTCUSDT")

        assert result is not None
        assert result.long_pct == Decimal("65.5")
        assert result.short_pct == Decimal("34.5")
        assert result.ratio == pytest.approx(1.8985, rel=1e-3)

    @pytest.mark.asyncio
    async def test_collect_empty_response(self):
        """Risposta vuota ritorna None."""
        from unittest.mock import MagicMock

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(return_value=[])
        mock_response.raise_for_status = MagicMock()

        collector = LongShortRatioCollector()
        with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_response)):
            result = await collector.collect("BTCUSDT")

        assert result is None

    @pytest.mark.asyncio
    async def test_collect_http_error(self):
        """Errore HTTP ritorna None."""
        from unittest.mock import MagicMock

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock(side_effect=Exception("API error"))

        collector = LongShortRatioCollector()
        with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_response)):
            result = await collector.collect("BTCUSDT")

        assert result is None

    def test_ratio_to_score_more_long(self):
        """Più long -> score negativo (bearish)."""
        score = LongShortRatioCollector.ratio_to_score(Decimal("75"))
        assert score < 0

    def test_ratio_to_score_more_short(self):
        """Più short -> score positivo (bullish)."""
        score = LongShortRatioCollector.ratio_to_score(Decimal("25"))
        assert score > 0

    def test_ratio_to_score_equal(self):
        """50-50 -> score zero."""
        score = LongShortRatioCollector.ratio_to_score(Decimal("50"))
        assert score == 0.0

    def test_ratio_to_score_clamped(self):
        """Score non supera +/- 15."""
        score = LongShortRatioCollector.ratio_to_score(Decimal("100"))
        assert -15.0 <= score <= 15.0
        score = LongShortRatioCollector.ratio_to_score(Decimal("0"))
        assert -15.0 <= score <= 15.0