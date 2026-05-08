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
    estimated_profit_pct: float = 0.0
    estimated_profit_eur: float = 0.0
    created_at: Optional[str] = None
    expires_at: Optional[str] = None
    custom_name: Optional[str] = None

    def __hash__(self):
        return hash((self.template, self.pair, self.timeframe, tuple(sorted(self.params.items())), self.budget_eur))

    def __post_init__(self):
        # Garantisce budget non nullo
        if self.budget_eur is None or self.budget_eur <= 0:
            object.__setattr__(self, 'budget_eur', 100.0)
        # Garantisce titolo e descrizione
        if not self.title and self.template in TEMPLATES:
            object.__setattr__(self, 'title', f"{TEMPLATES[self.template]['title']} ({self.pair})")
        if not self.description and self.template in TEMPLATES:
            object.__setattr__(self, 'description', TEMPLATES[self.template]['description'])


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
            
            # Stima profitto (simulata basata sul template e rischio)
            base_profit_map = {"low": 3.0, "medium": 8.0, "high": 15.0}
            base_profit = base_profit_map.get(template_data.get("risk_level", "medium"), 5.0)
            est_profit_pct = float(base_profit + random.uniform(-2.0, 5.0))
            
            # Usiamo il budget della richiesta, assicurandoci che non sia 0
            budget = float(req.budget_eur) if req.budget_eur > 0 else 100.0
            est_profit_eur = float((budget * est_profit_pct) / 100.0)
            
            # Nome personalizzato: se l'utente lo fornisce, usalo; altrimenti generane uno automatico
            if req.custom_name:
                final_custom_name = req.custom_name
            else:
                auto_names = {
                    "trend_ema": ["Il Seguace", "L'Ondaiolo", "Trendy", "Mr EMA", "La Scia"],
                    "mean_reversion_rsi": ["Il Rimbalzista", "Mr RSI", "Elastico", "L'Armonico", "Controcorrente"],
                    "breakout_bb": ["Lo Squartatore", "Boomer", "La Fiamma", "Rompiballe", "Il Valicano"],
                }
                base_name = random.choice(auto_names.get(template_name, ["Il Geniale"]))
                final_custom_name = f"{base_name} su {pair.split('/')[0]}"

            variant = StrategyParams(
                template=template_name,
                title=f"{template_data['title']} ({pair})", 
                description=template_data["description"],
                pair=pair,
                timeframe=timeframe,
                params=params_dict,
                budget_eur=budget,
                ai_score=float(min(score, 99.0)),
                estimated_profit_pct=est_profit_pct,
                estimated_profit_eur=est_profit_eur,
                custom_name=final_custom_name
            )
            all_variants.append(variant)
                
    # Mischiamo e prendiamo solo le migliori N varianti per evitare duplicati visivi
    random.shuffle(all_variants)
    
    # Ritorna le varianti ordinate per punteggio AI
    results = sorted(all_variants, key=lambda x: x.ai_score, reverse=True)[:req.max_strategies]
    
    # TASK-321: Calcolo data di scadenza (7 giorni da ora)
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    expiry = now + timedelta(days=7)
    now_str = now.isoformat()
    expiry_str = expiry.isoformat()

    # Assicuriamoci che ogni risultato abbia titolo, descrizione e timestamp validi
    for r in results:
        if not r.title:
            r.title = f"{TEMPLATES[r.template]['title']} ({r.pair})"
        if not r.description:
            r.description = TEMPLATES[r.template]['description']
        
        # Impostazione timestamp (uso di object.__setattr__ perché la classe è frozen)
        object.__setattr__(r, 'created_at', now_str)
        object.__setattr__(r, 'expires_at', expiry_str)
            
    return results


def generate_all_variants(
    pairs: list[str] = ["BTC/USDT"],
    timeframes: list[str] = ["5m", "15m"],
) -> Generator[StrategyParams, None, None]:
    """Prodotto cartesiano: tipicamente 200–800 strategie candidate."""
    for template_name, template_data in TEMPLATES.items():
        param_grid = template_data["params"]
        keys = list(param_grid.keys())
        for pair, timeframe, combo in product(pairs, timeframes, product(*param_grid.values())):
            yield StrategyParams(
                template=template_name,
                pair=pair,
                timeframe=timeframe,
                params=dict(zip(keys, combo)),
                title=f"{template_data['title']} ({pair})",
                description=template_data["description"]
            )


def build_strategy_id(s: StrategyParams) -> str:
    """Genera un ID deterministico basato sui parametri."""
    import hashlib
    import json
    payload = f"{s.template}:{s.pair}:{s.timeframe}:{json.dumps(s.params, sort_keys=True)}"
    return hashlib.md5(payload.encode()).hexdigest()[:10]


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
