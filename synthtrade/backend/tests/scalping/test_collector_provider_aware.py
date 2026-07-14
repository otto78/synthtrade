"""Test provider-aware (TASK-1153) per funding_rate / open_interest / long_short_ratio.

Verifica che i 3 collector futures chiamino l'endpoint nativo OKX (via adapter)
quando EXCHANGE_PROVIDER=okx e NON Binance, e che per simboli senza perpetual
(es. OKB-EUR) non venga tentata alcuna chiamata di rete. Con provider binance
il comportamento legacy resta invariato (nessuna regressione).

I test usano FakeOkxAdapter (tests/integration/fake_okx_adapter.py) che espone
get_open_interest / get_funding_rate e traccia le chiamate.
"""
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.scalping.intelligence.collectors.funding_rate import FundingRateCollector
from app.scalping.intelligence.collectors.long_short_ratio import LongShortRatioCollector
from app.scalping.intelligence.collectors.open_interest import OpenInterestCollector
from app.scalping.intelligence.signal_score_engine import SignalScoreEngine
from app.scalping.models.intelligence import FundingRate, LongShortRatio, OpenInterest
from tests.integration.fake_okx_adapter import FakeOkxAdapter


@pytest.fixture
def okx_provider(monkeypatch):
    monkeypatch.setattr("app.config.settings.EXCHANGE_PROVIDER", "okx")
    yield


@pytest.fixture
def binance_provider(monkeypatch):
    monkeypatch.setattr("app.config.settings.EXCHANGE_PROVIDER", "binance")
    yield


def _binance_blocking_patch():
    """Patch httpx.AsyncClient.get per FAR FALLIRE se il path Binance venisse mai usato."""
    return patch(
        "httpx.AsyncClient.get",
        new=AsyncMock(side_effect=AssertionError("Binance call attempted — provider-aware path broken")),
    )


class TestProviderAwareOpenInterest:
    @pytest.mark.asyncio
    async def test_okx_btc_perpetual_uses_adapter_not_binance(self, okx_provider):
        adapter = FakeOkxAdapter()
        adapter.open_interest_value = 1_234_567.0
        collector = OpenInterestCollector(adapter=adapter)
        with _binance_blocking_patch():
            result = await collector.collect("BTC-EUR")
        assert isinstance(result, OpenInterest)
        assert result.asset == "BTC"
        assert result.value_usd == Decimal("1234567.0")
        assert "get_open_interest(BTC)" in adapter.calls

    @pytest.mark.asyncio
    async def test_okx_btc_perpetual_symbol_supported(self, okx_provider):
        collector = OpenInterestCollector(adapter=FakeOkxAdapter())
        assert collector.is_symbol_supported("BTC-EUR") is True
        assert collector.is_symbol_supported("ETH-EUR") is True

    @pytest.mark.asyncio
    async def test_okb_eur_returns_none_no_network_call(self, okx_provider):
        adapter = FakeOkxAdapter()
        collector = OpenInterestCollector(adapter=adapter)
        with _binance_blocking_patch():
            result = await collector.collect("OKB-EUR")
        assert result is None
        assert collector.is_symbol_supported("OKB-EUR") is False
        # OKB non ha perpetual -> nessuna chiamata adapter ne' rete
        assert not any(c.startswith("get_open_interest") for c in adapter.calls)

    @pytest.mark.asyncio
    async def test_fake_adapter_get_open_interest_mocked(self, okx_provider):
        adapter = FakeOkxAdapter()
        adapter.open_interest_value = 5.5e8
        collector = OpenInterestCollector(adapter=adapter)
        with _binance_blocking_patch():
            result = await collector.collect("BTC-EUR")
        assert isinstance(result, OpenInterest)
        assert result.value_usd == Decimal("550000000.0")
        assert "get_open_interest(BTC)" in adapter.calls

    @pytest.mark.asyncio
    async def test_binance_legacy_unchanged(self, binance_provider):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={
            "symbol": "BTCUSDT",
            "openInterest": "987654321.000",
            "time": 1700000000000,
        })
        mock_response.raise_for_status = MagicMock()
        collector = OpenInterestCollector()  # adapter=None
        with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_response)):
            result = await collector.collect("BTCUSDT")
        assert isinstance(result, OpenInterest)
        assert result.symbol == "BTCUSDT"
        assert result.value_usd == Decimal("987654321.000")

    @pytest.mark.asyncio
    async def test_binance_legacy_eur_still_skipped(self, binance_provider):
        collector = OpenInterestCollector()
        with _binance_blocking_patch():
            result = await collector.collect("BTC-EUR")
        assert result is None


class TestProviderAwareFundingRate:
    @pytest.mark.asyncio
    async def test_okx_btc_uses_adapter_not_binance(self, okx_provider):
        adapter = FakeOkxAdapter()
        adapter.funding_rate_value = 0.0001
        collector = FundingRateCollector(adapter=adapter)
        with _binance_blocking_patch():
            result = await collector.collect("BTC-EUR")
        assert isinstance(result, FundingRate)
        assert result.rate == Decimal("0.0001")
        assert "get_funding_rate(BTC)" in adapter.calls

    @pytest.mark.asyncio
    async def test_okx_btc_perpetual_symbol_supported(self, okx_provider):
        collector = FundingRateCollector(adapter=FakeOkxAdapter())
        assert collector.is_symbol_supported("BTC-EUR") is True
        assert collector.is_symbol_supported("ETH-EUR") is True

    @pytest.mark.asyncio
    async def test_okb_eur_returns_none_no_network_call(self, okx_provider):
        adapter = FakeOkxAdapter()
        collector = FundingRateCollector(adapter=adapter)
        with _binance_blocking_patch():
            result = await collector.collect("OKB-EUR")
        assert result is None
        assert collector.is_symbol_supported("OKB-EUR") is False
        assert not any(c.startswith("get_funding_rate") for c in adapter.calls)

    @pytest.mark.asyncio
    async def test_binance_legacy_unchanged(self, binance_provider):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value=[{
            "symbol": "BTCUSDT",
            "fundingRate": "0.0001",
            "fundingTime": 1700000000000,
            "nextFundingTime": 1700003600000,
        }])
        mock_response.raise_for_status = MagicMock()
        collector = FundingRateCollector()
        with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_response)):
            result = await collector.collect("BTCUSDT")
        assert isinstance(result, FundingRate)
        assert result.rate == Decimal("0.0001")


class TestProviderAwareLongShortRatio:
    @pytest.mark.asyncio
    async def test_okx_always_unavailable_no_network_call(self, okx_provider):
        adapter = FakeOkxAdapter()
        collector = LongShortRatioCollector(adapter=adapter)
        with _binance_blocking_patch():
            result = await collector.collect("BTC-EUR")
        assert result is None
        assert collector.is_symbol_supported("BTC-EUR") is False
        assert not any(c.startswith("get_") for c in adapter.calls)

    @pytest.mark.asyncio
    async def test_binance_legacy_unchanged(self, binance_provider):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value=[{
            "symbol": "BTCUSDT",
            "longAccount": "0.60",
            "shortAccount": "0.40",
            "timestamp": 1700000000000,
        }])
        mock_response.raise_for_status = MagicMock()
        collector = LongShortRatioCollector()
        with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_response)):
            result = await collector.collect("BTCUSDT")
        assert isinstance(result, LongShortRatio)
        assert result.long_pct == Decimal("60.0")


class TestScoreReweightWhenUnavailable:
    def test_okb_eur_excludes_futures_collectors(self, okx_provider):
        engine = SignalScoreEngine(symbol="OKB-EUR", adapter=FakeOkxAdapter())
        total, excluded = engine.get_configurable_weight_total("OKB-EUR")
        assert set(excluded) == {"funding_rate", "open_interest", "long_short_ratio"}
        expected = (
            sum(engine.weights.values())
            - engine.weights["funding_rate"]
            - engine.weights["open_interest"]
            - engine.weights["long_short_ratio"]
        )
        assert total == pytest.approx(expected)

    def test_btc_eur_funding_and_oi_supported_long_short_not(self, okx_provider):
        engine = SignalScoreEngine(symbol="BTC-EUR", adapter=FakeOkxAdapter())
        total, excluded = engine.get_configurable_weight_total("BTC-EUR")
        # TASK-1153: BTC ha perpetual OKX -> funding_rate/open_interest attivi
        assert "funding_rate" not in excluded
        assert "open_interest" not in excluded
        # TASK-1158: nessun endpoint OKX equivalente per long/short -> strutturalmente assente
        assert "long_short_ratio" in excluded
