from typing import Optional, Literal
from pydantic import BaseModel, Field
from app.core.backtester import BacktestResult

class RankConfig(BaseModel):
    min_trades:   int   = 15
    min_sharpe:   float = 0.0
    max_drawdown: float = 40.0
    min_pnl:      float = 0.0
    w_pnl:        float = 0.40
    w_sharpe:     float = 0.30
    w_winrate:    float = 0.20
    w_drawdown:   float = 0.30
    risk_level:   Literal["low", "medium", "high"] = "medium"

    def __init__(self, **data):
        super().__init__(**data)
        if self.risk_level == "low":
            self.w_pnl = 0.10
            self.w_drawdown = 0.70
        elif self.risk_level == "high":
            self.w_pnl = 0.60
            self.w_drawdown = 0.10


class Ranker:
    def __init__(self, config: RankConfig = RankConfig()):
        self.cfg = config

    def compute_score(self, result: BacktestResult) -> Optional[float]:
        if (result.num_trades < self.cfg.min_trades or
                result.max_drawdown_pct > self.cfg.max_drawdown or
                result.sharpe < self.cfg.min_sharpe or
                result.pnl_pct < self.cfg.min_pnl):
            return None

        pnl_n  = min(result.pnl_pct / 20.0, 1.0)
        sha_n  = min(result.sharpe / 3.0, 1.0)
        wr_n   = result.win_rate
        dd_pen = result.max_drawdown_pct / 100.0

        score = (self.cfg.w_pnl * pnl_n + self.cfg.w_sharpe * sha_n +
                 self.cfg.w_winrate * wr_n - self.cfg.w_drawdown * dd_pen)
        return round(max(score, 0.0), 4)

def rank_strategies(strategies: list[dict]) -> list[dict]:
    return sorted(
        [s for s in strategies if s.get("score") is not None],
        key=lambda s: s["score"],
        reverse=True,
    )
