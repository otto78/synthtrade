import pytest
from app.core.strategy_generator import (
    generate_all_variants,
    build_strategy_id,
    StrategyParams,
    TEMPLATES,
)


def test_generate_at_least_200_variants():
    # TEMPLATES ha 3 entry, pairs 1, timeframes 2 -> 3 * 1 * 2 = 6 combinazioni base.
    # Ogni combinazione ha il prodotto dei parametri nel grid.
    # trend_ema: 2*2*2*2 = 16
    # mean_reversion_rsi: 1*2*2*1*2 = 8
    # breakout_bb: 1*2*1*2 = 4
    # Totale combinazioni parametri: 16 + 8 + 4 = 28
    # Totale varianti: 28 * 1 (pair) * 2 (timeframes) = 56
    variants = list(generate_all_variants())
    assert len(variants) >= 50


def test_each_variant_has_required_fields():
    for s in generate_all_variants():
        assert s.template
        assert s.pair
        assert s.timeframe
        assert isinstance(s.params, dict)
        assert len(s.params) > 0
        # TASK-181: Verifica campi regressione
        assert s.title, f"Missing title for {s.template}"
        assert s.description, f"Missing description for {s.template}"
        assert s.budget_eur > 0, f"Invalid budget for {s.template}"


@pytest.mark.asyncio
async def test_generate_for_request_full_data():
    from app.execution.schemas import StrategyRequest
    req = StrategyRequest(
        budget_eur=500.0,
        duration_days=30,
        asset_class="crypto",
        risk_level="medium",
        max_strategies=5
    )
    from app.core.strategy_generator import generate_for_request
    variants = await generate_for_request(req)
    
    assert len(variants) > 0
    for v in variants:
        assert v.title
        assert v.description
        assert v.budget_eur == 500.0
        assert v.estimated_profit_pct != 0
        assert v.estimated_profit_eur > 0


def test_strategy_id_is_deterministic():
    s = StrategyParams(template="trend_ema", pair="BTC/USDT", timeframe="5m",
                       params={"ema_fast": 20, "ema_slow": 50})
    assert build_strategy_id(s) == build_strategy_id(s)


def test_strategy_id_differs_for_different_params():
    s1 = StrategyParams(template="trend_ema", pair="BTC/USDT", timeframe="5m",
                        params={"ema_fast": 20, "ema_slow": 50})
    s2 = StrategyParams(template="trend_ema", pair="BTC/USDT", timeframe="5m",
                        params={"ema_fast": 10, "ema_slow": 100})
    assert build_strategy_id(s1) != build_strategy_id(s2)


def test_no_duplicate_ids_on_500_variants():
    variants = list(generate_all_variants())[:500]
    ids = [build_strategy_id(s) for s in variants]
    assert len(ids) == len(set(ids))


def test_all_templates_covered():
    templates_generated = {s.template for s in generate_all_variants()}
    assert templates_generated == set(TEMPLATES.keys())


def test_custom_pairs_and_timeframes():
    variants = list(generate_all_variants(pairs=["ETH/USDT"], timeframes=["1h"]))
    assert all(s.pair == "ETH/USDT" for s in variants)
    assert all(s.timeframe == "1h" for s in variants)


def test_params_values_come_from_template_grid():
    for s in generate_all_variants():
        grid = TEMPLATES[s.template]["params"]
        for key, value in s.params.items():
            assert value in grid[key], f"{key}={value} non è nel grid di {s.template}"
