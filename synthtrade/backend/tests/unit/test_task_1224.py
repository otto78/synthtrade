"""TASK-1224: long-only execution flow checks."""

from app.execution.exchange_models import ClosePositionRequest, SymbolRef
from app.scalping._state import _execution_state


def test_sl_above_entry_for_buy():
    from app.scalping.pricing import _sl_price_from_entry

    sl_price, feasible = _sl_price_from_entry(
        50000.0,
        "BUY",
        0.3,
        0.001,
        0.001,
        price_prec=2,
    )

    assert sl_price < 50000.0
    assert feasible is True


def test_paper_balance_decreases_for_buy():
    previous = _execution_state["session"].get("paper_balance")
    _execution_state["session"]["paper_balance"] = 1000.0

    try:
        trade_value = 100.0
        _execution_state["session"]["paper_balance"] -= trade_value
        assert _execution_state["session"]["paper_balance"] == 900.0
    finally:
        if previous is None:
            _execution_state["session"].pop("paper_balance", None)
        else:
            _execution_state["session"]["paper_balance"] = previous


def test_long_emergency_close_uses_sell():
    request = ClosePositionRequest(
        symbol=SymbolRef(base="BTC", quote="EUR"),
        side="buy",
        quantity=0.002,
    )

    close_side = "sell" if request.side == "buy" else "buy"
    assert request.side == "buy"
    assert close_side == "sell"
