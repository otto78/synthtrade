"""
🔴 TASK-400: Test per CapitalAllocator
"""
import pytest
from app.execution.capital_allocator import CapitalAllocator, BudgetTooSmallError, InitialTradeRequest

allocator = CapitalAllocator()

def test_allocate_single_pair():
    """Strategia con pair="BTC/USDT" e budget=500 calcola 1 trade da 500 USDT."""
    strategy = {"pair": "BTC/USDT", "budget_eur": 500, "params": {}}
    trades = allocator.allocate(strategy, available_usdt=1000, holdings={"BTC": 0, "USDT": 1500})
    assert len(trades) == 1
    assert trades[0].symbol == "BTC/USDT"
    assert trades[0].usdt_amount == 500.0
    assert trades[0].side == "buy"

def test_allocate_with_existing_holdings_skips():
    """Se l'utente ha già BTC, il trade viene comunque aggiunto (poi il caller decide)."""
    strategy = {"pair": "BTC/USDT", "budget_eur": 500, "params": {}}
    trades = allocator.allocate(strategy, available_usdt=1000, holdings={"BTC": 0.5, "USDT": 500})
    assert len(trades) == 1  # Include sempre per semplicità

def test_allocate_multi_crypto():
    """Strategia con allocazione 60% BTC, 40% ETH → 2 trade con importi corretti."""
    strategy = {
        "pair": "", "budget_eur": 1000,
        "params": {"allocation": [{"symbol": "BTC/USDT", "pct": 60}, {"symbol": "ETH/USDT", "pct": 40}]}
    }
    trades = allocator.allocate(strategy, available_usdt=2000, holdings={"BTC": 0, "ETH": 0, "USDT": 2000})
    assert len(trades) == 2
    btc_trade = [t for t in trades if t.symbol == "BTC/USDT"][0]
    eth_trade = [t for t in trades if t.symbol == "ETH/USDT"][0]
    assert btc_trade.usdt_amount == 600.0
    assert eth_trade.usdt_amount == 400.0

def test_allocate_budget_too_small():
    """Budget sotto MIN_NOTIONAL → BudgetTooSmallError."""
    strategy = {
        "pair": "", "budget_eur": 5,
        "params": {"allocation": [{"symbol": "SOL/USDT", "pct": 100}]}
    }
    with pytest.raises(BudgetTooSmallError) as exc:
        allocator.allocate(strategy, available_usdt=5, holdings={"USDT": 5})
    assert exc.value.symbol == "SOL/USDT"

def test_allocate_fallback_to_pair():
    """Se params.allocation è assente, usa strategy['pair'] al 100%."""
    strategy = {"pair": "ETH/USDT", "budget_eur": 300, "params": {}}
    trades = allocator.allocate(strategy, available_usdt=500, holdings={"ETH": 0})
    assert len(trades) == 1
    assert trades[0].symbol == "ETH/USDT"
    assert trades[0].usdt_amount == 300.0

def test_allocate_empty_allocations_list():
    """params.allocation = [] → fallback a pair."""
    strategy = {"pair": "BTC/USDT", "budget_eur": 100, "params": {"allocation": []}}
    trades = allocator.allocate(strategy, available_usdt=200, holdings={"BTC": 0})
    assert len(trades) == 1
    assert trades[0].symbol == "BTC/USDT"

def test_allocate_zero_budget():
    """Budget = 0 → BudgetTooSmallError (sotto MIN_NOTIONAL)."""
    strategy = {"pair": "BTC/USDT", "budget_eur": 0, "params": {}}
    with pytest.raises(BudgetTooSmallError):
        allocator.allocate(strategy, available_usdt=0, holdings={"BTC": 0})
