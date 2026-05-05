import pytest
from app.core.strategy_generator import (
    generate_all_variants,
    build_strategy_id,
    StrategyParams,
    TEMPLATES,
)


def test_generate_at_least_200_variants():
    variants = list(generate_all_variants())
    assert len(variants) >= 200


def test_each_variant_has_required_fields():
    for s in generate_all_variants():
        assert s.template
        assert s.pair
        assert s.timeframe
        assert isinstance(s.params, dict)
        assert len(s.params) > 0


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
        grid = TEMPLATES[s.template]
        for key, value in s.params.items():
            assert value in grid[key], f"{key}={value} non è nel grid di {s.template}"
