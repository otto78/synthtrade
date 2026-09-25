import pytest
from unittest.mock import MagicMock, AsyncMock
from app.execution.exchange import BinanceExchangeAdapter


def _binance_markets():
    return {
        "BTC/USDT": {
            "id": "BTCUSDT",
            "symbol": "BTC/USDT",
            "base": "BTC",
            "quote": "USDT",
            "precision": {"amount": 3, "price": 2},
            "limits": {"amount": {"min": 0.001}, "cost": {"min": 5.0}},
            "info": {
                "filters": [
                    {"filterType": "LOT_SIZE", "stepSize": "0.001", "minQty": "0.001"},
                    {"filterType": "MIN_NOTIONAL", "minNotional": "5.0"},
                    {"filterType": "PRICE_FILTER", "tickSize": "0.01"},
                ]
            },
        }
    }

@pytest.mark.asyncio
async def test_binance_adapter_get_balance(monkeypatch):
    """
    TASK-073: get_balance() chiama l'endpoint corretto e restituisce il saldo USDT
    """
    mock_ccxt = AsyncMock()
    mock_ccxt.fetch_balance.return_value = {
        "free": {"USDT": 1000.50},
        "total": {"USDT": 1200.00}
    }
    
    adapter = BinanceExchangeAdapter(api_key="key", secret="secret", testnet=True, client=mock_ccxt)
    balance = await adapter.get_balance()
    
    assert balance == 1000.50
    mock_ccxt.fetch_balance.assert_called_once()

@pytest.mark.asyncio
async def test_binance_adapter_get_ticker_price(monkeypatch):
    """
    TASK-074: get_ticker_price(symbol) restituisce il prezzo corrente
    """
    mock_ccxt = AsyncMock()
    mock_ccxt.fetch_ticker.return_value = {"last": 65000.0}
    mock_ccxt.load_markets.return_value = _binance_markets()
    
    adapter = BinanceExchangeAdapter(api_key="key", secret="secret", testnet=True, client=mock_ccxt)
    price = await adapter.get_ticker_price("BTC/USDT")
    
    assert price == 65000.0
    mock_ccxt.fetch_ticker.assert_called_with("BTC/USDT")

@pytest.mark.asyncio
async def test_binance_adapter_place_market_order(monkeypatch):
    """
    TASK-075: place_market_order() chiama create_order con type=market
    """
    mock_ccxt = AsyncMock()
    mock_ccxt.create_order.return_value = {
        "id": "12345",
        "status": "closed",
        "price": 65000.0,
        "amount": 0.01
    }
    mock_ccxt.load_markets.return_value = _binance_markets()
    
    adapter = BinanceExchangeAdapter(api_key="key", secret="secret", testnet=True, client=mock_ccxt)
    result = await adapter.place_market_order("BTC/USDT", "buy", 0.01)
    
    # L'adapter restituisce il dict CCXT raw (chiave "id") + commission/commission_asset
    assert result["id"] == "12345"
    mock_ccxt.create_order.assert_called_with(
        symbol="BTCUSDT",  # l'adapter risolve l'id compatto dal market CCXT
        type="market",
        side="buy",
        amount=0.01
    )
