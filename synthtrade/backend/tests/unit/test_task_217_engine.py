import pytest
from unittest.mock import MagicMock, AsyncMock
from app.execution.execution_engine import ExecutionEngine
from app.execution.schemas import Signal, PositionSnapshot
from app.execution.signal_resolver import DefaultSignalResolver

@pytest.mark.asyncio
async def test_execution_engine_process_signals_uses_resolver():
    # Mock dependencies
    risk_manager = MagicMock()
    order_tracker = MagicMock()
    exchange = AsyncMock()
    sl_service = MagicMock()
    
    # Setup resolver mock
    resolver = MagicMock()
    # Resolve should return only the first signal
    s1 = Signal(strategy_id="s1", symbol="BTC/USDT", direction="BUY", strength=0.8, price=50000)
    s2 = Signal(strategy_id="s1", symbol="ETH/USDT", direction="BUY", strength=0.4, price=3000)
    resolver.resolve.return_value = [s1]
    
    engine = ExecutionEngine(
        risk_manager=risk_manager,
        order_tracker=order_tracker,
        exchange=exchange,
        sl_service=sl_service,
        signal_resolver=resolver
    )
    
    # Mock order_tracker to return open positions
    order_tracker.get_open_positions.return_value = []
    
    # Mock risk_manager to approve
    risk_manager.validate_signal.return_value.approved = True
    risk_manager.validate_signal.return_value.position_size = 0.01
    risk_manager.validate_signal.return_value.stop_loss_price = 49000
    risk_manager.validate_signal.return_value.take_profit_price = 52000
    
    # Mock exchange place_order
    exchange.place_order.return_value.status = "FILLED"
    exchange.place_order.return_value.order_id = "oid123"
    
    # Execution
    await engine.process_signals([s1, s2], balance=1000, current_drawdown_pct=0)
    
    # Verification
    resolver.resolve.assert_called_once()
    # Should only process s1
    assert risk_manager.validate_signal.call_count == 1
    args, kwargs = risk_manager.validate_signal.call_args
    assert kwargs['signal'] == s1
