import pytest
from app.execution.schemas import StrategyRequest
from app.core.strategy_generator import generate_for_request, TEMPLATES

@pytest.mark.asyncio
async def test_generate_for_request_duration_filter():
    """
    TASK-035: generate_for_request(req: StrategyRequest) restituisce solo strategie con duration_days compatibile (± 20%)
    """
    # trend_ema has 30 days. request 30 days should include it.
    req = StrategyRequest(
        budget_eur=100.0,
        duration_days=30,
        asset_class="crypto",
        risk_level="medium"
    )
    strategies = await generate_for_request(req)
    templates_found = {s.template for s in strategies}
    assert "trend_ema" in templates_found
    
    # request 7 days should include breakout_bb (7 days) but not trend_ema (30 days)
    req_short = StrategyRequest(
        budget_eur=100.0,
        duration_days=7,
        asset_class="crypto",
        risk_level="medium"
    )
    strategies_short = await generate_for_request(req_short)
    templates_found_short = {s.template for s in strategies_short}
    assert "breakout_bb" in templates_found_short
    assert "trend_ema" not in templates_found_short

@pytest.mark.asyncio
async def test_generate_for_request_symbols_filter():
    """
    TASK-036: se req.symbols è specificato, le strategie generate usano solo quei simboli
    """
    symbols = ["ETH/USDT", "SOL/USDT"]
    req = StrategyRequest(
        budget_eur=100.0,
        duration_days=30,
        asset_class="crypto",
        risk_level="medium",
        symbols=symbols
    )
    strategies = await generate_for_request(req)
    for s in strategies:
        assert s.pair in symbols

@pytest.mark.asyncio
async def test_generate_for_request_risk_level_low():
    """
    TASK-037: risk_level = "low" esclude strategie con rischio alto
    """
    # breakout_bb is high risk in our TEMPLATES mock
    req = StrategyRequest(
        budget_eur=100.0,
        duration_days=7, # matches breakout_bb duration
        asset_class="crypto",
        risk_level="low"
    )
    strategies = await generate_for_request(req)
    templates_found = {s.template for s in strategies}
    assert "breakout_bb" not in templates_found

@pytest.mark.asyncio
async def test_generate_for_request_risk_level_high():
    """
    TASK-038: risk_level = "high" consente tutti i template
    """
    req = StrategyRequest(
        budget_eur=100.0,
        duration_days=7,
        asset_class="crypto",
        risk_level="high"
    )
    strategies = await generate_for_request(req)
    templates_found = {s.template for s in strategies}
    assert "breakout_bb" in templates_found

@pytest.mark.asyncio
async def test_generate_for_request_budget_propagation():
    """
    TASK-039: budget_eur viene propagato come budget_eur nei parametri della strategia generata
    """
    budget = 500.0
    req = StrategyRequest(
        budget_eur=budget,
        duration_days=30,
        asset_class="crypto",
        risk_level="medium"
    )
    strategies = await generate_for_request(req)
    for s in strategies:
        assert s.budget_eur == budget

@pytest.mark.asyncio
async def test_generate_for_request_max_strategies_limit():
    """
    TASK-040: max_strategies limita il numero di strategie restituite
    """
    max_s = 3
    req = StrategyRequest(
        budget_eur=100.0,
        duration_days=30,
        asset_class="crypto",
        risk_level="medium",
        max_strategies=max_s
    )
    strategies = await generate_for_request(req)
    assert len(strategies) <= max_s
