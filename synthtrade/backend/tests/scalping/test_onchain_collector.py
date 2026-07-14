"""Test TASK-1156 — OnChainCollector fallback Blockchair (proxy macro BTC/ETH).

Copre:
- simbolo non on-chain nativo (OKB-EUR) -> proxy BTC+ETH, source=blockchair_proxy:btc+eth
- simbolo nativo (BTC-USDT) -> fonte blockchair diretta, proxy=None
- estrazione variazione prezzo 24h come segnale macro (onchain_to_score)
- nessuna chiamata inutile quando il circuit breaker e' aperto
"""
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.scalping.intelligence.collectors.onchain import OnChainCollector
from app.scalping.models.intelligence import OnChainData


def _json_response(payload):
    m = MagicMock()
    m.status_code = 200
    m.json = MagicMock(return_value=payload)
    m.text = ""
    return m


BITCOIN_STATS = {
    "data": {
        "transactions_24h": 740000,
        "hashrate_24h": 968000000000000000000,
        "market_price_usd_change_24h_percentage": 2.0,
    }
}
ETHEREUM_STATS = {
    "data": {
        "transactions_24h": 3000000,
        "hashrate_24h": 0,
        "market_price_usd_change_24h_percentage": 4.0,
    }
}


class _FakeClient:
    """AsyncClient che risponde con le stats per chain richiesta."""

    def __init__(self, chain_payloads):
        self._chain_payloads = chain_payloads
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url, params=None, headers=None):
        self.calls.append(url)
        if "bitcoin" in url:
            return _json_response(self._chain_payloads["bitcoin"])
        if "ethereum" in url:
            return _json_response(self._chain_payloads["ethereum"])
        return _json_response({"data": {}})


def _collector():
    c = OnChainCollector(timeout_seconds=5.0)
    c._dune_key = ""  # nessuna Dune key: solo Blockchair
    return c


@pytest.mark.asyncio
async def test_proxy_for_non_native_symbol():
    c = _collector()
    with patch("httpx.AsyncClient", return_value=_FakeClient({"bitcoin": BITCOIN_STATS, "ethereum": ETHEREUM_STATS})):
        data = await c.collect("OKB-EUR")
    assert isinstance(data, OnChainData)
    assert data.proxy_symbol == "btc+eth"
    assert data.source == "blockchair_proxy:btc+eth"
    # transazioni aggregate BTC + ETH
    assert data.transaction_count == 740000 + 3000000
    # media variazione 24h (2.0 + 4.0) / 2
    assert data.price_change_24h_pct == pytest.approx(3.0)
    assert data.hash_rate == Decimal(str(BITCOIN_STATS["data"]["hashrate_24h"]))


@pytest.mark.asyncio
async def test_native_symbol_no_proxy():
    c = _collector()
    with patch("httpx.AsyncClient", return_value=_FakeClient({"bitcoin": BITCOIN_STATS, "ethereum": ETHEREUM_STATS})):
        data = await c.collect("BTC-USDT")
    assert data.proxy_symbol is None
    assert data.source == "blockchair"
    assert data.price_change_24h_pct == pytest.approx(2.0)
    assert data.transaction_count == 740000


@pytest.mark.asyncio
async def test_score_uses_price_change():
    data = OnChainData(
        symbol="OKB-EUR",
        price_change_24h_pct=10.0,
        proxy_symbol="btc+eth",
        source="blockchair_proxy:btc+eth",
        timestamp=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
    )
    # +10% macro -> +10 score (clip a +/-30)
    assert OnChainCollector.onchain_to_score(data) == pytest.approx(10.0)

    data_bear = OnChainData(
        symbol="OKB-EUR",
        price_change_24h_pct=-10.0,
        proxy_symbol="btc+eth",
        source="blockchair_proxy:btc+eth",
        timestamp=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
    )
    assert OnChainCollector.onchain_to_score(data_bear) == pytest.approx(-10.0)


@pytest.mark.asyncio
async def test_no_call_when_circuit_breaker_open():
    c = _collector()
    c._cb._state = "open"  # forza CB aperto
    with patch("httpx.AsyncClient", side_effect=AssertionError("non deve chiamare HTTP")) as mock:
        data = await c.collect("OKB-EUR")
    assert data is None
    mock.assert_not_called()
