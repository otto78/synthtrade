from itertools import product
from dataclasses import dataclass
from typing import Generator, List
from app.execution.schemas import StrategyRequest
from app.ai.request_enricher import enrich_request_with_ai

TEMPLATES: dict[str, dict] = {
    "trend_ema": {
        "duration_days": 30,
        "risk_level": "medium",
        "params": {
            "ema_fast":    [10, 20, 30],
            "ema_slow":    [50, 100, 200],
            "stop_loss":   [0.02, 0.03, 0.05],
            "take_profit": [0.04, 0.06, 0.09],
        }
    },
    "mean_reversion_rsi": {
        "duration_days": 15,
        "risk_level": "low",
        "params": {
            "rsi_period":     [14, 21],
            "rsi_oversold":   [25, 30, 35],
            "rsi_overbought": [65, 70, 75],
            "stop_loss":      [0.02, 0.03],
            "take_profit":    [0.04, 0.06],
        }
    },
    "breakout_bb": {
        "duration_days": 7,
        "risk_level": "high",
        "params": {
            "bb_period":   [20, 30],
            "bb_std":      [2.0, 2.5],
            "stop_loss":   [0.02, 0.03],
            "take_profit": [0.05, 0.08],
        }
    },
}


@dataclass(frozen=True)
class StrategyParams:
    template: str
    pair: str
    timeframe: str
    params: dict
    budget_eur: float = 100.0

    def __hash__(self):
        return hash((self.template, self.pair, self.timeframe, tuple(sorted(self.params.items())), self.budget_eur))


async def generate_all_variants(
    pairs: list[str] = ["BTC/USDT"],
    timeframes: list[str] = ["5m", "15m"],
) -> Generator[StrategyParams, None, None]:
    for template_name, template_data in TEMPLATES.items():
        param_grid = template_data["params"]
        keys = list(param_grid.keys())
        for pair, timeframe, combo in product(pairs, timeframes, product(*param_grid.values())):
            yield StrategyParams(
                template=template_name,
                pair=pair,
                timeframe=timeframe,
                params=dict(zip(keys, combo)),
            )


async def generate_for_request(req: StrategyRequest) -> List[StrategyParams]:
    """
    TASK-041: Implement generate_for_request
    TASK-047: Aggiungere chiamata a enrich_request_with_ai()
    """
    # Arricchimento con AI se presente free_text
    req = await enrich_request_with_ai(req)
    
    filtered_templates = _filter_templates_by_constraints(req)
    
    pairs = req.symbols if req.symbols else ["BTC/USDT"]
    timeframes = ["1h"] # Default timeframe for now
    
    results = []
    for template_name in filtered_templates:
        template_data = TEMPLATES[template_name]
        param_grid = template_data["params"]
        keys = list(param_grid.keys())
        
        # Generiamo varianti per questo template
        for pair, timeframe, combo in product(pairs, timeframes, product(*param_grid.values())):
            results.append(StrategyParams(
                template=template_name,
                pair=pair,
                timeframe=timeframe,
                params=dict(zip(keys, combo)),
                budget_eur=req.budget_eur
            ))
            
            if len(results) >= req.max_strategies:
                return results
                
    return results


def _filter_templates_by_constraints(req: StrategyRequest) -> List[str]:
    """
    TASK-042: Refactor la selezione dei template
    """
    valid_templates = []
    
    for name, data in TEMPLATES.items():
        # Filter by duration (± 20%)
        dur = data.get("duration_days", 30)
        if not (req.duration_days * 0.8 <= dur <= req.duration_days * 1.2):
            continue
            
        # Filter by risk level
        if req.risk_level == "low" and data.get("risk_level") == "high":
            continue
            
        valid_templates.append(name)
        
    return valid_templates


import hashlib


def build_strategy_id(s: StrategyParams) -> str:
    key = f"{s.template}_{s.pair}_{s.timeframe}_{tuple(sorted(s.params.items()))}"
    digest = hashlib.md5(key.encode()).hexdigest()[:8]
    return f"{s.template[:4]}_{digest}"
