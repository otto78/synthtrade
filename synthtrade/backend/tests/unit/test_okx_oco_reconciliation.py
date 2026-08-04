"""Regression tests for the strict OKX OCO -> child order -> fill correlation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.execution.okx_exchange import OkxExchangeAdapter


def _response(payload):
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status = MagicMock()
    return response


@pytest.mark.asyncio
async def test_oco_history_fetches_only_its_child_order_fills():
    """A fill from another BTC-EUR trade cannot enter this reconciliation."""
    adapter = OkxExchangeAdapter("key", "secret", "passphrase", demo=True)
    client = MagicMock()
    client.get = AsyncMock(side_effect=[
        _response({
            "code": "0",
            "data": [{
                "algoId": "oco-123",
                "state": "effective",
                "instId": "BTC-EUR",
                "side": "sell",
                "actualSide": "sl",
                "ordId": "child-456",
                "ordIdList": [],
            }],
        }),
        _response({
            "code": "0",
            "data": [
                {"ordId": "child-456", "fillPx": "100", "fillSz": "0.1", "fillTime": "1000"},
                {"ordId": "child-456", "fillPx": "90", "fillSz": "0.2", "fillTime": "2000"},
                # This record would be unsafe if the adapter requested generic fills.
                {"ordId": "other-order", "fillPx": "50000", "fillSz": "1", "fillTime": "3000"},
            ],
        }),
    ])
    http_client_factory = MagicMock()
    http_client_factory.return_value.__aenter__ = AsyncMock(return_value=client)
    http_client_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    with patch("app.execution.okx_exchange.httpx.AsyncClient", http_client_factory):
        result = await adapter.get_algo_orders_history("BTC-EUR", bracket_id="oco-123")

    assert len(result) == 1
    assert result[0]["algoId"] == "oco-123"
    assert result[0]["ordId"] == "child-456"
    assert result[0]["ordType"] == "oco_sl"
    assert result[0]["fillTime"] == "2000"
    assert float(result[0]["avgPx"]) == pytest.approx((100 * 0.1 + 90 * 0.2) / 0.3)
    assert client.get.await_count == 2
    assert client.get.await_args_list[0].kwargs["params"]["algoId"] == "oco-123"
    assert client.get.await_args_list[1].kwargs["params"] == {
        "instType": "SPOT", "instId": "BTC-EUR", "ordId": "child-456"
    }
