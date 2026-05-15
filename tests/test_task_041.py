import pytest
from app.core.ranker import Ranker, RankConfig
from app.core.backtester import BacktestResult

@pytest.fixture
def ranker():
    return Ranker()

def test_ranker_high_risk_prefers_pnl():
    ranker = Ranker(config=RankConfig(risk_level="high"))
    # Strategia 1: buon PnL, alto DD
    s1 = BacktestResult(pnl_pct=20.0, win_rate=0.5, sharpe=1.0, max_drawdown_pct=30.0, num_trades=20)
    # Strategia 2: basso PnL, basso DD
    s2 = BacktestResult(pnl_pct=5.0, win_rate=0.5, sharpe=1.0, max_drawdown_pct=5.0, num_trades=20)
    
    score1 = ranker.compute_score(s1)
    score2 = ranker.compute_score(s2)
    assert score1 > score2

def test_ranker_low_risk_prefers_safety():
    ranker = Ranker(config=RankConfig(risk_level="low"))
    # Strategia 1: buon PnL, alto DD
    s1 = BacktestResult(pnl_pct=20.0, win_rate=0.5, sharpe=1.0, max_drawdown_pct=30.0, num_trades=20)
    # Strategia 2: basso PnL, basso DD
    s2 = BacktestResult(pnl_pct=5.0, win_rate=0.5, sharpe=1.0, max_drawdown_pct=5.0, num_trades=20)
    
    score1 = ranker.compute_score(s1)
    score2 = ranker.compute_score(s2)
    assert score2 > score1
