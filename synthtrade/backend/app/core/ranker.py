from dataclasses import dataclass
from typing import Optional
from app.core.backtester import BacktestResult


@dataclass
class RankConfig:
    min_trades:   int   = 15    # 60gg × 1h = ~1440 candele → 15 trade minimo per significatività
    min_sharpe:   float = 0.0   # accetta Sharpe neutro (crypto volatile)
    max_drawdown: float = 40.0  # crypto è volatile, drawdown 30-40% è normale
    min_pnl:      float = 0.0   # accetta qualsiasi P&L positivo
    w_pnl:        float = 0.40
    w_sharpe:     float = 0.30
    w_winrate:    float = 0.20
    w_drawdown:   float = 0.30


def compute_score(result: BacktestResult, cfg: RankConfig = RankConfig()) -> Optional[float]:
    if (result.num_trades < cfg.min_trades or
            result.max_drawdown_pct > cfg.max_drawdown or
            result.sharpe < cfg.min_sharpe or
            result.pnl_pct < cfg.min_pnl):
        return None

    pnl_n  = min(result.pnl_pct / 20.0, 1.0)
    sha_n  = min(result.sharpe / 3.0, 1.0)
    wr_n   = result.win_rate
    dd_pen = result.max_drawdown_pct / 100.0

    score = (cfg.w_pnl * pnl_n + cfg.w_sharpe * sha_n +
             cfg.w_winrate * wr_n - cfg.w_drawdown * dd_pen)
    return round(max(score, 0.0), 4)


def rank_strategies(strategies: list[dict]) -> list[dict]:
    return sorted(
        [s for s in strategies if s.get("score") is not None],
        key=lambda s: s["score"],
        reverse=True,
    )
