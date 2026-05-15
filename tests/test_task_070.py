import pytest
from unittest.mock import AsyncMock, MagicMock
from app.execution.trade_executor import TradeExecutor
from app.execution.schemas import OrderRequest, OrderResult

@pytest.fixture
def mock_exchange():
    return AsyncMock()

@pytest.fixture
def mock_tracker():
    return MagicMock()

@pytest.fixture
def executor(mock_exchange, mock_tracker):
    return TradeExecutor(mock_exchange, mock_tracker)

@pytest.mark.asyncio
async def test_execute_order_success(executor, mock_exchange, mock_tracker):
    req = OrderRequest(strategy_id="s1", symbol="BTC/USDT", direction="BUY", quantity=0.01, price=60000.0, stop_loss=58000.0, take_profit=62000.0)
    mock_exchange.place_order.return_value = OrderResult(order_id="o1", status="FILLED", symbol="BTC/USDT", direction="BUY", quantity=0.01, price=60000.0)
    mock_tracker.open_position.return_value = "trade-1"
    
    trade_id = await executor.execute_order(req)
    
    assert trade_id == "trade-1"
    mock_exchange.place_order.assert_called_once()
    mock_tracker.open_position.assert_called_once()

@pytest.mark.asyncio
async def test_execute_order_fail(executor, mock_exchange):
    req = OrderRequest(strategy_id="s1", symbol="BTC/USDT", direction="BUY", quantity=0.01, price=60000.0, stop_loss=58000.0, take_profit=62000.0)
    mock_exchange.place_order.side_effect = Exception("Exchange down")
    
    with pytest.raises(Exception):
        await executor.execute_order(req)
