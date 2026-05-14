"""
backend/tests/integration/test_capital_allocator.py
-------------------------------------------
Test di integrazione per la logica di allocazione del capitale.
Verifica il calcolo delle quote in USDT per l'acquisto iniziale.
"""

import pytest
from app.execution.capital_allocator import CapitalAllocator

def test_allocate_single_asset():
    allocator = CapitalAllocator()
    strategy = {
        "id": "strat_1",
        "pair": "BTC/USDT",
        "budget_eur": 500.0,
        "params": {}
    }
    available_usdt = 1000.0
    holdings = {"USDT": 1000.0}
    
    trades = allocator.allocate(strategy, available_usdt, holdings)
    
    assert len(trades) == 1
    assert trades[0].symbol == "BTC/USDT"
    assert trades[0].usdt_amount == 500.0
    assert trades[0].pct == 100.0
    assert trades[0].side == "buy"

def test_allocate_multi_asset():
    allocator = CapitalAllocator()
    strategy = {
        "id": "strat_multi",
        "params": {
            "allocation": [
                {"symbol": "BTC/USDT", "pct": 60},
                {"symbol": "ETH/USDT", "pct": 40}
            ]
        },
        "budget_eur": 1000.0
    }
    available_usdt = 2000.0
    holdings = {"USDT": 2000.0}
    
    trades = allocator.allocate(strategy, available_usdt, holdings)
    
    assert len(trades) == 2
    btc_trade = next(t for t in trades if t.symbol == "BTC/USDT")
    eth_trade = next(t for t in trades if t.symbol == "ETH/USDT")
    
    assert btc_trade.usdt_amount == 600.0
    assert eth_trade.usdt_amount == 400.0

def test_allocate_insufficient_budget():
    from app.execution.capital_allocator import BudgetTooSmallError
    allocator = CapitalAllocator()
    # Budget molto piccolo che va sotto il MIN_NOTIONAL (10 USDT)
    strategy = {
        "id": "strat_small",
        "pair": "BTC/USDT",
        "budget_eur": 5.0,
        "params": {}
    }
    
    with pytest.raises(BudgetTooSmallError):
        allocator.allocate(strategy, 100.0, {"USDT": 100.0})
