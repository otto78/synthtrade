from itertools import product
from dataclasses import dataclass
from typing import Generator

TEMPLATES: dict[str, dict] = {
    "trend_ema": {
        "ema_fast":    [10, 20, 30],
        "ema_slow":    [50, 100, 200],
        "stop_loss":   [0.02, 0.03, 0.05],
        "take_profit": [0.04, 0.06, 0.09],
    },
    "mean_reversion_rsi": {
        "rsi_period":     [14, 21],
        "rsi_oversold":   [25, 30, 35],
        "rsi_overbought": [65, 70, 75],
        "stop_loss":      [0.02, 0.03],
        "take_profit":    [0.04, 0.06],
    },
    "breakout_bb": {
        "bb_period":   [20, 30],
        "bb_std":      [2.0, 2.5],
        "stop_loss":   [0.02, 0.03],
        "take_profit": [0.05, 0.08],
    },
}


@dataclass(frozen=True)
class StrategyParams:
    template: str
    pair: str
    timeframe: str
    params: dict

    def __hash__(self):
        return hash((self.template, self.pair, self.timeframe, tuple(sorted(self.params.items()))))


def generate_all_variants(
    pairs: list[str] = ["BTC/USDT"],
    timeframes: list[str] = ["5m", "15m"],
) -> Generator[StrategyParams, None, None]:
    for template_name, param_grid in TEMPLATES.items():
        keys = list(param_grid.keys())
        for pair, timeframe, combo in product(pairs, timeframes, product(*param_grid.values())):
            yield StrategyParams(
                template=template_name,
                pair=pair,
                timeframe=timeframe,
                params=dict(zip(keys, combo)),
            )


import hashlib


def build_strategy_id(s: StrategyParams) -> str:
    key = f"{s.template}_{s.pair}_{s.timeframe}_{tuple(sorted(s.params.items()))}"
    digest = hashlib.md5(key.encode()).hexdigest()[:8]
    return f"{s.template[:4]}_{digest}"
