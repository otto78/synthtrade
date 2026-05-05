import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, UTC
from app.execution.execution_engine import ExecutionEngine
from app.execution.schemas import Signal, OrderResult, RiskCheckResult, PositionSnapshot


def make_signal(symbol="BTC/USDT", strategy_id="s1"):
    return Signal(strategy_id=strategy_id, symbol=symbol, direction="BUY",
                  strength=0.8, price=60000.0, timestamp=datetime.now(UTC))


def make_position(trade_id="t1", symbol="BTC/USDT"):
    return PositionSnapshot(
        trade_id=trade_id, strategy_id="s1", symbol=symbol,
        direction="BUY", entry_price=58000.0, quantity=0.01,
        stop_loss=56840.0, take_profit=62400.0, opened_at=datetime.now(UTC)
    )


@pytest.fixture
def engine():
    risk_manager = MagicMock()
    order_tracker = MagicMock()
    exchange = MagicMock()
    logger = MagicMock()

    risk_manager.validate_signal.return_value = RiskCheckResult(
        approved=True, reason="OK", position_size=0.01,
        stop_loss_price=58800.0, take_profit_price=62400.0
    )
    exchange.place_order = AsyncMock(return_value=OrderResult(
        order_id="o1", status="FILLED", symbol="BTC/USDT",
        direction="BUY", quantity=0.01, price=60000.0
    ))
    exchange.close_order = AsyncMock(return_value=OrderResult(
        order_id="o2", status="FILLED", symbol="BTC/USDT",
        direction="SELL", quantity=0.01, price=62000.0
    ))
    order_tracker.open_position.return_value = "trade-1"
    order_tracker.get_open_positions.return_value = []

    return ExecutionEngine(
        risk_manager=risk_manager,
        order_tracker=order_tracker,
        exchange=exchange,
        logger=logger,
    )


@pytest.mark.asyncio
async def test_process_signal_calls_risk_manager(engine):
    signal = make_signal()
    await engine.process_signal(signal, balance=10000.0, open_positions=[],
                                current_drawdown_pct=5.0)
    engine.risk_manager.validate_signal.assert_called_once()


@pytest.mark.asyncio
async def test_process_signal_rejected_no_order(engine):
    engine.risk_manager.validate_signal.return_value = RiskCheckResult(
        approved=False, reason="drawdown troppo alto"
    )
    signal = make_signal()
    await engine.process_signal(signal, balance=10000.0, open_positions=[],
                                current_drawdown_pct=20.0)
    engine.exchange.place_order.assert_not_called()


@pytest.mark.asyncio
async def test_process_signal_approved_builds_order_request(engine):
    signal = make_signal()
    await engine.process_signal(signal, balance=10000.0, open_positions=[],
                                current_drawdown_pct=5.0)
    call_args = engine.exchange.place_order.call_args[0][0]
    assert call_args.symbol == "BTC/USDT"
    assert call_args.stop_loss == 58800.0
    assert call_args.take_profit == 62400.0


@pytest.mark.asyncio
async def test_process_signal_filled_opens_position(engine):
    signal = make_signal()
    await engine.process_signal(signal, balance=10000.0, open_positions=[],
                                current_drawdown_pct=5.0)
    engine.order_tracker.open_position.assert_called_once()


@pytest.mark.asyncio
async def test_process_signal_rejected_order_no_position(engine):
    engine.exchange.place_order.return_value = AsyncMock(return_value=None)
    engine.exchange.place_order = AsyncMock(return_value=OrderResult(
        order_id="o1", status="REJECTED", symbol="BTC/USDT",
        direction="BUY", quantity=0.01, price=60000.0
    ))
    signal = make_signal()
    await engine.process_signal(signal, balance=10000.0, open_positions=[],
                                current_drawdown_pct=5.0)
    engine.order_tracker.open_position.assert_not_called()


def test_check_exit_conditions_sl_hit(engine):
    pos = make_position()
    pos.stop_loss = 58000.0
    assert engine.check_exit_conditions(pos, current_price=57000.0) is True


def test_check_exit_conditions_tp_hit(engine):
    pos = make_position()
    pos.take_profit = 62000.0
    assert engine.check_exit_conditions(pos, current_price=63000.0) is True


def test_check_exit_conditions_no_exit(engine):
    pos = make_position()
    pos.stop_loss = 58000.0
    pos.take_profit = 62000.0
    assert engine.check_exit_conditions(pos, current_price=60000.0) is False


@pytest.mark.asyncio
async def test_close_position_if_needed_closes_on_sl(engine):
    pos = make_position()
    pos.stop_loss = 58000.0
    pos.take_profit = 62000.0
    await engine.close_position_if_needed(pos, current_price=57000.0)
    engine.exchange.close_order.assert_called_once()
    engine.order_tracker.close_position.assert_called_once()


@pytest.mark.asyncio
async def test_close_position_if_needed_no_close(engine):
    pos = make_position()
    pos.stop_loss = 58000.0
    pos.take_profit = 62000.0
    await engine.close_position_if_needed(pos, current_price=60000.0)
    engine.exchange.close_order.assert_not_called()


@pytest.mark.asyncio
async def test_exchange_exception_caught(engine):
    engine.exchange.place_order.side_effect = Exception("exchange down")
    signal = make_signal()
    # Non deve sollevare eccezione
    await engine.process_signal(signal, balance=10000.0, open_positions=[],
                                current_drawdown_pct=5.0)
    engine.logger.error.assert_called()
