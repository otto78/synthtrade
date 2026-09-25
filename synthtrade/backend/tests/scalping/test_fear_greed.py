"""Test per FearGreedCollector (TASK-804)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.scalping.intelligence.collectors import fear_greed
from app.scalping.intelligence.collectors.fear_greed import FearGreedCollector


def _make_session(status: int, payload=None):
    response = MagicMock()
    response.status = status
    response.json = AsyncMock(return_value=payload)

    response_context = MagicMock()
    response_context.__aenter__ = AsyncMock(return_value=response)
    response_context.__aexit__ = AsyncMock(return_value=None)

    session = MagicMock()
    session.get = MagicMock(return_value=response_context)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    return session, response


@pytest.fixture(autouse=True)
def isolate_collector(monkeypatch):
    fear_greed._cached_value = None
    fear_greed._cached_at = None
    monkeypatch.setattr(
        fear_greed.aiohttp,
        "ClientSession",
        MagicMock(side_effect=AssertionError("network access is not allowed")),
    )
    yield
    fear_greed._cached_value = None
    fear_greed._cached_at = None


class TestFearGreedCollector:
    @pytest.mark.asyncio
    async def test_collect_success(self):
        session, response = _make_session(
            200,
            {
                "data": [
                    {"value": "25", "value_classification": "Fear", "timestamp": "1700000000"},
                ]
            },
        )
        collector = FearGreedCollector(max_retries=1)

        with patch.object(
            fear_greed.aiohttp,
            "ClientSession",
            return_value=session,
        ):
            result = await collector.collect()

        assert result is not None
        assert result.value == 25
        assert result.label == "Fear"
        response.json.assert_awaited_once_with()

    @pytest.mark.asyncio
    async def test_collect_extreme_greed(self):
        session, _ = _make_session(
            200,
            {
                "data": [
                    {
                        "value": "85",
                        "value_classification": "Extreme Greed",
                        "timestamp": "1700000000",
                    },
                ]
            },
        )
        collector = FearGreedCollector(max_retries=1)

        with patch.object(
            fear_greed.aiohttp,
            "ClientSession",
            return_value=session,
        ):
            result = await collector.collect()

        assert result is not None
        assert result.value == 85
        assert result.label == "Extreme Greed"

    @pytest.mark.asyncio
    async def test_collect_empty_response(self):
        session, response = _make_session(200, {"data": []})
        collector = FearGreedCollector(max_retries=1)

        with patch.object(
            fear_greed.aiohttp,
            "ClientSession",
            return_value=session,
        ):
            result = await collector.collect()

        assert result is None
        response.json.assert_awaited_once_with()

    @pytest.mark.asyncio
    async def test_collect_http_error(self):
        session, response = _make_session(503, None)
        collector = FearGreedCollector(max_retries=1)

        with patch.object(
            fear_greed.aiohttp,
            "ClientSession",
            return_value=session,
        ):
            result = await collector.collect()

        assert result is None
        response.json.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_collect_uses_mocked_aiohttp_client(self):
        session, _ = _make_session(
            200,
            {
                "data": [
                    {"value": "50", "value_classification": "Neutral", "timestamp": "1700000000"},
                ]
            },
        )
        collector = FearGreedCollector(timeout_seconds=3.0, max_retries=1)

        with patch.object(
            fear_greed.aiohttp,
            "ClientSession",
            return_value=session,
        ) as client_session:
            result = await collector.collect()

        assert result is not None
        client_session.assert_called_once()
        assert client_session.call_args.kwargs["timeout"].total == 3.0
        session.get.assert_called_once_with(fear_greed.ALTERNATIVE_ME_URL)

    def test_classify_extreme_fear(self):
        assert FearGreedCollector._classify(0) == "Extreme Fear"
        assert FearGreedCollector._classify(10) == "Extreme Fear"
        assert FearGreedCollector._classify(20) == "Extreme Fear"

    def test_classify_fear(self):
        assert FearGreedCollector._classify(21) == "Fear"
        assert FearGreedCollector._classify(40) == "Fear"

    def test_classify_neutral(self):
        assert FearGreedCollector._classify(41) == "Neutral"
        assert FearGreedCollector._classify(60) == "Neutral"

    def test_classify_greed(self):
        assert FearGreedCollector._classify(61) == "Greed"
        assert FearGreedCollector._classify(80) == "Greed"

    def test_classify_extreme_greed(self):
        assert FearGreedCollector._classify(81) == "Extreme Greed"
        assert FearGreedCollector._classify(100) == "Extreme Greed"

    def test_value_to_score_extreme_greed(self):
        assert FearGreedCollector.value_to_score(85) == -25.0

    def test_value_to_score_greed(self):
        assert FearGreedCollector.value_to_score(70) == -15.0

    def test_value_to_score_neutral(self):
        assert FearGreedCollector.value_to_score(50) == 0.0

    def test_value_to_score_fear(self):
        assert FearGreedCollector.value_to_score(35) == 7.5

    def test_value_to_score_extreme_fear(self):
        assert FearGreedCollector.value_to_score(15) == 25.0
