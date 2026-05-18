import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, UTC
from app.execution.schemas import Signal, OrderResult, RiskCheckResult, PositionSnapshot
from app.execution.risk_manager import RiskManager, RiskConfig
from app.execution.order_tracker import OrderTracker
from app.execution.execution_engine import ExecutionEngine


def make_signal(symbol="BTC/USDT", strategy_id="s1", strength=0.8, price=60000.0):
    return Signal(strategy_id=strategy_id, symbol=symbol, direction="BUY",
                  strength=strength, price=price, timestamp=datetime.now(UTC))


def make_position(trade_id="t1", entry=58000.0, sl=56840.0, tp=62320.0):
    return PositionSnapshot(
        trade_id=trade_id, strategy_id="s1", symbol="BTC/USDT",
        direction="BUY", entry_price=entry, quantity=0.01,
        stop_loss=sl, take_profit=tp, opened_at=datetime.now(UTC)
    )


def build_engine(order_result_status="FILLED", open_positions=None):
    config = RiskConfig(max_concurrent_positions=2, max_drawdown_pct=15.0,
                        default_position_size_pct=0.05, default_stop_loss_pct=0.02,
                        default_take_profit_pct=0.04, max_exposure_per_symbol_pct=0.10)
    risk_manager = RiskManager(config)

    order_tracker = MagicMock(spec=OrderTracker)
    order_tracker.open_position.return_value = "trade-1"
    order_tracker.get_open_positions.return_value = open_positions or []

    exchange = MagicMock()
    exchange.place_order = AsyncMock(return_value=OrderResult(
        order_id="o1", status=order_result_status,
        symbol="BTC/USDT", direction="BUY", quantity=0.01, price=60000.0
    ))
    exchange.close_order = AsyncMock(return_value=OrderResult(
        order_id="o2", status="FILLED",
        symbol="BTC/USDT", direction="SELL", quantity=0.01, price=62000.0
    ))

    engine = ExecutionEngine(
        risk_manager=risk_manager,
        order_tracker=order_tracker,
        exchange=exchange,
        sl_service=MagicMock(),
        logger=MagicMock(),
    )
    return engine


@pytest.mark.asyncio
async def test_full_pipeline_signal_to_open_trade():
    """Signal approvato → ordine FILLED → posizione aperta su Supabase."""
    engine = build_engine(order_result_status="FILLED")
    signal = make_signal()

    await engine.process_signal(signal, balance=10000.0, open_positions=[],
                                current_drawdown_pct=5.0)

    engine.exchange.place_order.assert_called_once()
    engine.order_tracker.open_position.assert_called_once()
    call_req = engine.exchange.place_order.call_args[0][0]
    assert call_req.symbol == "BTC/USDT"
    assert call_req.stop_loss < signal.price
    assert call_req.take_profit > signal.price


@pytest.mark.asyncio
async def test_stop_loss_scenario():
    """Posizione aperta → prezzo scende sotto SL → posizione chiusa."""
    position = make_position(entry=60000.0, sl=58800.0, tp=62400.0)
    engine = build_engine(open_positions=[position])

    # Prezzo sotto SL
    await engine.close_position_if_needed(position, current_price=58000.0)

    engine.exchange.close_order.assert_called_once_with(position)
    engine.order_tracker.close_position.assert_called_once()
    args = engine.order_tracker.close_position.call_args[0]
    assert args[0] == "t1"
    assert args[1] == 58000.0


@pytest.mark.asyncio
async def test_risk_reject_max_positions():
    """Portfolio al limite → nessun ordine → log con reason."""
    positions = [make_position("t1"), make_position("t2")]
    config = RiskConfig(max_concurrent_positions=2)
    engine = build_engine(open_positions=positions)
    engine.risk_manager = RiskManager(config)

    signal = make_signal()
    await engine.process_signal(signal, balance=10000.0,
                                open_positions=positions, current_drawdown_pct=5.0)

    engine.exchange.place_order.assert_not_called()
    engine.logger.info.assert_called()
    log_msg = engine.logger.info.call_args[0][0]
    assert "rejected" in log_msg.lower() or "limite" in log_msg.lower()


@pytest.mark.asyncio
async def test_drawdown_scenario_all_signals_rejected():
    """Drawdown oltre soglia → tutti i signal rigettati."""
    engine = build_engine()
    signals = [
        make_signal(strategy_id="s1", symbol="BTC/USDT"),
        make_signal(strategy_id="s2", symbol="ETH/USDT"),
    ]

    for signal in signals:
        await engine.process_signal(signal, balance=10000.0,
                                    open_positions=[], current_drawdown_pct=20.0)

    engine.exchange.place_order.assert_not_called()
