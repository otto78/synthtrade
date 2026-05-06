import pytest
from unittest.mock import MagicMock, AsyncMock
from app.execution.exchange import BinanceExchangeAdapter

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
    
    adapter = BinanceExchangeAdapter(api_key="key", secret="secret", testnet=True, client=mock_ccxt)
    result = await adapter.place_market_order("BTC/USDT", "BUY", 0.01)
    
    assert result["order_id"] == "12345"
    mock_ccxt.create_order.assert_called_with(
        symbol="BTC/USDT",
        type="market",
        side="buy",
        amount=0.01
    )
