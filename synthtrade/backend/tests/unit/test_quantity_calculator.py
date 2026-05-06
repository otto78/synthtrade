import pytest
from app.execution.quantity_calculator import calculate_quantity, BudgetTooSmallError

def test_calculate_quantity_basic():
    """
    TASK-085: calculate_quantity restituisce la quantità corretta
    """
    # 100 USDT budget, 50000 price -> 0.002 BTC
    # stepSize 0.0001
    filters = {"stepSize": 0.0001, "minQty": 0.0001, "minNotional": 10.0}
    qty = calculate_quantity(100.0, 50000.0, filters)
    assert qty == 0.002

def test_calculate_quantity_step_size():
    """
    TASK-085: rispetta stepSize (arrotondamento per difetto)
    """
    # 100 USDT / 60000 price = 0.001666...
    # stepSize 0.001 -> should be 0.001
    filters = {"stepSize": 0.001, "minQty": 0.0001, "minNotional": 10.0}
    qty = calculate_quantity(100.0, 60000.0, filters)
    assert qty == 0.001

def test_calculate_quantity_budget_limit():
    """
    TASK-086: quantità non supera mai il budget
    """
    budget = 100.0
    price = 60000.0
    filters = {"stepSize": 0.00001, "minQty": 0.0001, "minNotional": 10.0}
    qty = calculate_quantity(budget, price, filters)
    assert qty * price <= budget

def test_calculate_quantity_min_qty_error():
    """
    TASK-087: solleva BudgetTooSmallError se sotto minQty
    """
    filters = {"stepSize": 0.001, "minQty": 0.1, "minNotional": 10.0}
    # 10 USDT budget / 50000 price = 0.0002 BTC (under minQty 0.1)
    with pytest.raises(BudgetTooSmallError):
        calculate_quantity(10.0, 50000.0, filters)

def test_calculate_quantity_min_notional_error():
    """
    TASK-087: solleva BudgetTooSmallError se sotto minNotional
    """
    filters = {"stepSize": 0.00001, "minQty": 0.0001, "minNotional": 50.0}
    # 10 USDT budget (under minNotional 50.0)
    with pytest.raises(BudgetTooSmallError):
        calculate_quantity(10.0, 50000.0, filters)
