import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, UTC
from app.execution.order_tracker import OrderTracker
from app.execution.schemas import OrderRequest, OrderResult


def make_order_request(symbol="BTC/USDT", strategy_id="s1"):
    return OrderRequest(
        strategy_id=strategy_id, symbol=symbol, direction="BUY",
        quantity=0.01, price=60000.0, stop_loss=58800.0, take_profit=62400.0
    )


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.table.return_value.insert.return_value.execute.return_value.data = [{"id": "trade-1"}]
    db.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{"id": "trade-1"}]
    db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "trade-1", "strategy_id": "s1", "pair": "BTC/USDT", "action": "BUY",
         "price": 60000.0, "quantity": 0.01, "stop_loss": 58800.0, "take_profit": 62400.0,
         "status": "OPEN", "executed_at": datetime.now(UTC).isoformat()}
    ]
    return db


@pytest.fixture
def tracker(mock_db):
    with patch("app.execution.order_tracker.get_supabase", return_value=mock_db):
        yield OrderTracker()


def test_open_position_inserts_to_supabase(tracker, mock_db):
    result = OrderResult(order_id="o1", status="FILLED", symbol="BTC/USDT",
                         direction="BUY", quantity=0.01, price=60000.0)
    req = make_order_request()
    trade_id = tracker.open_position(req, result)
    assert trade_id == "trade-1"
    mock_db.table.assert_called_with("trades")


def test_open_position_status_open(tracker, mock_db):
    result = OrderResult(order_id="o1", status="FILLED", symbol="BTC/USDT",
                         direction="BUY", quantity=0.01, price=60000.0)
    tracker.open_position(make_order_request(), result)
    insert_call = mock_db.table.return_value.insert.call_args[0][0]
    assert insert_call["status"] == "OPEN"


def test_close_position_updates_supabase(tracker, mock_db):
    tracker.close_position(trade_id="trade-1", exit_price=62000.0, pnl_pct=3.3)
    mock_db.table.return_value.update.assert_called_once()
    update_data = mock_db.table.return_value.update.call_args[0][0]
    assert update_data["status"] == "CLOSED"
    assert update_data["exit_price"] == 62000.0
    assert "closed_at" in update_data


def test_get_open_positions_returns_open_only(tracker, mock_db):
    positions = tracker.get_open_positions()
    assert len(positions) == 1
    assert positions[0].symbol == "BTC/USDT"


def test_get_open_positions_filter_by_symbol(tracker, mock_db):
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    positions = tracker.get_open_positions(symbol="ETH/USDT")
    assert positions == []


def test_update_unrealized_pnl_long(tracker):
    pnl = tracker.update_unrealized_pnl(entry_price=60000.0, current_price=63000.0,
                                         quantity=0.01, direction="BUY")
    assert abs(pnl - (63000 - 60000) * 0.01) < 0.01


def test_update_unrealized_pnl_short(tracker):
    pnl = tracker.update_unrealized_pnl(entry_price=60000.0, current_price=57000.0,
                                         quantity=0.01, direction="SELL")
    assert abs(pnl - (60000 - 57000) * 0.01) < 0.01
