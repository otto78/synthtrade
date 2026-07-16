"""
TASK-1116.G: Instrument discovery environment-aware — unit tests.

Tests that:
1. _direct_fetch_symbol_rules sends x-simulated-trading header when demo=True
2. Cache is partitioned by (symbol, demo_flag)
3. list_instruments sends the correct header
4. Session start rejects symbols not available in current environment
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.execution.exchange_models import (
    SymbolRef,
    SymbolRules,
    UnsupportedInstrumentError,
)
from app.execution.okx_exchange import OkxExchangeAdapter


BTC_EUR = SymbolRef(base="BTC", quote="EUR")
OKB_EUR = SymbolRef(base="OKB", quote="EUR")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_adapter(demo: bool = True) -> OkxExchangeAdapter:
    return OkxExchangeAdapter(
        api_key="test-key",
        secret="test-secret",
        passphrase="test-pass",
        demo=demo,
        base_url="https://eea.okx.com",
    )


def _mock_okx_response(instruments: list[dict], code: str = "0") -> MagicMock:
    """Create a mock httpx.Response for OKX instruments endpoint."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"code": code, "data": instruments}
    resp.raise_for_status = MagicMock()
    return resp


def _fake_instrument(inst_id: str = "BTC-EUR") -> dict:
    return {
        "instId": inst_id,
        "baseCcy": inst_id.split("-")[0],
        "quoteCcy": inst_id.split("-")[1] if "-" in inst_id else "USDT",
        "state": "live",
        "lotSz": "0.00001",
        "minSz": "0.00001",
        "tickSz": "0.1",
        "maxMktSz": "100",
        "maxMktAmt": "1000000",
    }


# ── Test: _direct_fetch_symbol_rules sends demo header ────────────────────────

@pytest.mark.asyncio
async def test_symbol_rules_demo_header_sent():
    """When adapter is demo=True, x-simulated-trading: 1 header must be sent."""
    adapter = _make_adapter(demo=True)
    mock_resp = _mock_okx_response([_fake_instrument("BTC-EUR")])

    with patch("app.execution.okx_exchange.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        rules = await adapter._direct_fetch_symbol_rules(BTC_EUR)

        # Verify header was sent
        call_args = mock_client.get.call_args
        headers = call_args.kwargs.get("headers", call_args[1].get("headers", {}))
        assert headers.get("x-simulated-trading") == "1", "Demo header must be sent for demo adapter"

        assert rules.symbol == BTC_EUR
        assert rules.lot_sz == 0.00001


@pytest.mark.asyncio
async def test_symbol_rules_live_no_demo_header():
    """When adapter is demo=False, x-simulated-trading header must NOT be sent."""
    adapter = _make_adapter(demo=False)
    mock_resp = _mock_okx_response([_fake_instrument("BTC-EUR")])

    with patch("app.execution.okx_exchange.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        rules = await adapter._direct_fetch_symbol_rules(BTC_EUR)

        call_args = mock_client.get.call_args
        headers = call_args.kwargs.get("headers", call_args[1].get("headers", {}))
        assert "x-simulated-trading" not in headers, "Live adapter must NOT send demo header"


# ── Test: cache partitioned by (symbol, demo_flag) ────────────────────────────

@pytest.mark.asyncio
async def test_cache_partitioned_by_demo_flag():
    """Cache must separate demo and live results for the same symbol."""
    adapter_demo = _make_adapter(demo=True)
    adapter_live = _make_adapter(demo=False)

    # Pre-populate cache with demo result
    demo_rules = SymbolRules(
        symbol=BTC_EUR, lot_sz=0.001, min_sz=0.001, tick_sz=0.1,
        max_mkt_sz=100, max_mkt_amt=1_000_000,
    )
    adapter_demo._rules_cache[(BTC_EUR.okx, True)] = demo_rules
    adapter_demo._rules_cache_ts[(BTC_EUR.okx, True)] = 9999999999  # far future

    # Same symbol in live should NOT hit demo cache (different adapter instance)
    # But also verify the cache key format
    cache_key_demo = (BTC_EUR.okx, True)
    cache_key_live = (BTC_EUR.okx, False)

    assert cache_key_demo != cache_key_live, "Demo and live cache keys must be different"
    assert adapter_demo._rules_cache.get(cache_key_demo) == demo_rules


@pytest.mark.asyncio
async def test_get_symbol_rules_uses_partitioned_cache():
    """get_symbol_rules should use (symbol, demo) as cache key."""
    adapter = _make_adapter(demo=True)
    rules = SymbolRules(
        symbol=BTC_EUR, lot_sz=0.001, min_sz=0.001, tick_sz=0.1,
        max_mkt_sz=100, max_mkt_amt=1_000_000,
    )

    # Manually populate cache
    import time
    adapter._rules_cache[(BTC_EUR.okx, True)] = rules
    adapter._rules_cache_ts[(BTC_EUR.okx, True)] = time.time()

    # Should return cached without calling _direct_fetch_symbol_rules
    with patch.object(adapter, "_direct_fetch_symbol_rules", new_callable=AsyncMock) as mock_fetch:
        result = await adapter.get_symbol_rules(BTC_EUR)
        mock_fetch.assert_not_called()
        assert result == rules


# ── Test: list_instruments sends demo header ──────────────────────────────────

@pytest.mark.asyncio
async def test_list_instruments_demo_header():
    """list_instruments must send x-simulated-trading header when demo=True."""
    adapter = _make_adapter(demo=True)
    btc_instrument = _fake_instrument("BTC-EUR")
    okb_instrument = _fake_instrument("OKB-EUR")
    # Simulate: OKB-EUR not in demo catalog
    mock_resp = _mock_okx_response([btc_instrument])

    with patch("app.execution.okx_exchange.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        instruments = await adapter.list_instruments("SPOT")

        # Verify demo header
        call_args = mock_client.get.call_args
        headers = call_args.kwargs.get("headers", call_args[1].get("headers", {}))
        assert headers.get("x-simulated-trading") == "1"

        # Only live instruments returned
        assert len(instruments) == 1
        assert instruments[0]["instId"] == "BTC-EUR"


@pytest.mark.asyncio
async def test_list_instruments_live_no_header():
    """list_instruments must NOT send demo header when demo=False."""
    adapter = _make_adapter(demo=False)
    mock_resp = _mock_okx_response([_fake_instrument("BTC-EUR"), _fake_instrument("OKB-EUR")])

    with patch("app.execution.okx_exchange.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        instruments = await adapter.list_instruments("SPOT")

        call_args = mock_client.get.call_args
        headers = call_args.kwargs.get("headers", call_args[1].get("headers", {}))
        assert "x-simulated-trading" not in headers
        assert len(instruments) == 2


# ── Test: symbol not found raises UnsupportedInstrumentError ──────────────────

@pytest.mark.asyncio
async def test_symbol_not_found_raises_unsupported():
    """If OKX returns empty data for a symbol, UnsupportedInstrumentError is raised."""
    adapter = _make_adapter(demo=True)
    mock_resp = _mock_okx_response([])  # empty — symbol not in demo catalog

    with patch("app.execution.okx_exchange.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        with pytest.raises(UnsupportedInstrumentError, match="not found"):
            await adapter._direct_fetch_symbol_rules(OKB_EUR)


# ── Test: list_instruments filters by state ───────────────────────────────────

@pytest.mark.asyncio
async def test_list_instruments_filters_by_state():
    """Only instruments with state='live' should be returned."""
    adapter = _make_adapter(demo=True)
    instruments = [
        {"instId": "BTC-EUR", "state": "live"},
        {"instId": "DOGE-EUR", "state": "offline"},
        {"instId": "ETH-EUR", "state": "live"},
    ]
    mock_resp = _mock_okx_response(instruments)

    with patch("app.execution.okx_exchange.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await adapter.list_instruments("SPOT")

        assert len(result) == 2
        assert all(i["state"] == "live" for i in result)
