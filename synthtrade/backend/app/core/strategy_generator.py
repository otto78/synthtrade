import random
from itertools import product
from dataclasses import dataclass
from typing import Generator, List, Optional
from app.execution.schemas import StrategyRequest
from app.ai.request_enricher import enrich_request_with_ai

TEMPLATES: dict[str, dict] = {
    "trend_ema": {
        "title": "Trend Following EMA",
        "description": "Segue il trend utilizzando incroci di medie mobili esponenziali.",
        "duration_days": 30,
        "risk_level": "medium",
        "params": {
            "ema_fast":    [10, 20],
            "ema_slow":    [50, 100],
            "stop_loss":   [0.02, 0.03],
            "take_profit": [0.05, 0.08],
        }
    },
    "mean_reversion_rsi": {
        "title": "Mean Reversion RSI",
        "description": "Sfrutta l'ipercomprato/ipervenduto per ritorni verso la media.",
        "duration_days": 15,
        "risk_level": "low",
        "params": {
            "rsi_period":     [14],
            "rsi_oversold":   [25, 30],
            "rsi_overbought": [70, 75],
            "stop_loss":      [0.02],
            "take_profit":    [0.04, 0.06],
        }
    },
    "breakout_bb": {
        "title": "Bollinger Breakout",
        "description": "Entra a mercato sulle rotture delle bande di Bollinger con alta volatilità.",
        "duration_days": 7,
        "risk_level": "high",
        "params": {
            "bb_period":   [20],
            "bb_std":      [2.0, 2.5],
            "stop_loss":   [0.03],
            "take_profit": [0.07, 0.10],
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
    title: Optional[str] = None
    description: Optional[str] = None
    ai_score: float = 0.0

    def __hash__(self):
        return hash((self.template, self.pair, self.timeframe, tuple(sorted(self.params.items())), self.budget_eur))


async def generate_for_request(req: StrategyRequest) -> List[StrategyParams]:
    """
    TASK-041: Generatore migliorato con varianti reali e descrizioni.
    """
    # Arricchimento con AI per estrarre simboli e template preferito
    req = await enrich_request_with_ai(req)
    
    filtered_templates = _filter_templates_by_constraints(req)
    
    pairs = req.symbols if req.symbols else ["BTC/USDT"]
    timeframes = ["1h", "4h"] # Varietà di timeframe
    
    all_variants = []
    for template_name in filtered_templates:
        template_data = TEMPLATES[template_name]
        param_grid = template_data["params"]
        keys = list(param_grid.keys())
        
        # Generiamo tutte le combinazioni possibili per questo template
        combos = list(product(*param_grid.values()))
        
        for pair, timeframe, combo in product(pairs, timeframes, combos):
            params_dict = dict(zip(keys, combo))
            
            # Calcolo di un punteggio AI simulato basato sulle preferenze utente
            score = 70.0 + random.uniform(0, 25.0)
            if req.free_text and template_name in req.free_text.lower():
                score += 5.0
            
            variant = StrategyParams(
                template=template_name,
                title=template_data["title"],
                description=template_data["description"],
                pair=pair,
                timeframe=timeframe,
                params=params_dict,
                budget_eur=req.budget_eur,
                ai_score=min(score, 99.0)
            )
            all_variants.append(variant)
                
    # Mischiamo e prendiamo solo le migliori N varianti per evitare duplicati visivi
    random.shuffle(all_variants)
    
    # Ritorna le varianti ordinate per punteggio AI
    return sorted(all_variants, key=lambda x: x.ai_score, reverse=True)[:req.max_strategies]


def _filter_templates_by_constraints(req: StrategyRequest) -> List[str]:
    valid_templates = []
    for name, data in TEMPLATES.items():
        # Durata ± 50% per essere più flessibili nella generazione
        dur = data.get("duration_days", 30)
        if not (req.duration_days * 0.5 <= dur <= req.duration_days * 1.5):
            continue
            
        # Rischio
        if req.risk_level == "low" and data.get("risk_level") == "high":
            continue
            
        valid_templates.append(name)
        
    # Se nessun template soddisfa i vincoli rigidi, restituiamo quello più vicino
    if not valid_templates:
        return [list(TEMPLATES.keys())[0]]
        
    return valid_templates
