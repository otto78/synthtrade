"""Test per FearGreedCollector (TASK-804)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.scalping.intelligence.collectors.fear_greed import FearGreedCollector


class TestFearGreedCollector:
    @pytest.mark.asyncio
    async def test_collect_success(self):
        """Collettore parsa correttamente la risposta Alternative.me."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(return_value={
            "data": [
                {"value": "25", "value_classification": "Fear", "timestamp": "1700000000"},
            ]
        })
        mock_response.raise_for_status = MagicMock()

        collector = FearGreedCollector()
        with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_response)):
            result = await collector.collect()

        assert result is not None
        assert result.value == 25
        assert result.label == "Fear"

    @pytest.mark.asyncio
    async def test_collect_extreme_greed(self):
        """Valore Extreme Greed parsato correttamente."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(return_value={
            "data": [
                {"value": "85", "value_classification": "Extreme Greed", "timestamp": "1700000000"},
            ]
        })
        mock_response.raise_for_status = MagicMock()

        collector = FearGreedCollector()
        with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_response)):
            result = await collector.collect()

        assert result is not None
        assert result.value == 85
        assert result.label == "Extreme Greed"

    @pytest.mark.asyncio
    async def test_collect_empty_response(self):
        """Risposta vuota ritorna None."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(return_value={"data": []})
        mock_response.raise_for_status = MagicMock()

        collector = FearGreedCollector()
        with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_response)):
            result = await collector.collect()

        assert result is None

    @pytest.mark.asyncio
    async def test_collect_http_error(self):
        """Errore HTTP ritorna None."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock(side_effect=Exception("API error"))

        collector = FearGreedCollector()
        with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_response)):
            result = await collector.collect()

        assert result is None

    def test_classify_extreme_fear(self):
        """0-24 = Extreme Fear."""
        assert FearGreedCollector.classify(10) == "Extreme Fear"
        assert FearGreedCollector.classify(0) == "Extreme Fear"
        assert FearGreedCollector.classify(24) == "Extreme Fear"

    def test_classify_fear(self):
        """25-44 = Fear."""
        assert FearGreedCollector.classify(25) == "Fear"
        assert FearGreedCollector.classify(44) == "Fear"

    def test_classify_neutral(self):
        """45-54 = Neutral."""
        assert FearGreedCollector.classify(45) == "Neutral"
        assert FearGreedCollector.classify(54) == "Neutral"

    def test_classify_greed(self):
        """55-74 = Greed."""
        assert FearGreedCollector.classify(55) == "Greed"
        assert FearGreedCollector.classify(74) == "Greed"

    def test_classify_extreme_greed(self):
        """75-100 = Extreme Greed."""
        assert FearGreedCollector.classify(75) == "Extreme Greed"
        assert FearGreedCollector.classify(100) == "Extreme Greed"

    def test_fng_to_score_extreme_greed(self):
        """Extreme Greed (>80) -> -10.0 short bias."""
        assert FearGreedCollector.fng_to_score(85) == -10.0

    def test_fng_to_score_greed(self):
        """Greed (65-79) -> -3.0."""
        assert FearGreedCollector.fng_to_score(70) == -3.0

    def test_fng_to_score_neutral(self):
        """Neutral (45-64) -> 0.0."""
        assert FearGreedCollector.fng_to_score(50) == 0.0

    def test_fng_to_score_fear(self):
        """Fear (25-44) -> +3.0."""
        assert FearGreedCollector.fng_to_score(35) == 3.0

    def test_fng_to_score_extreme_fear(self):
        """Extreme Fear (<25) -> +10.0 long bias."""
        assert FearGreedCollector.fng_to_score(15) == 10.0