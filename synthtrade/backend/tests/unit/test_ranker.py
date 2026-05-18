from app.core.ranker import Ranker, rank_strategies, RankConfig
from app.core.backtester import BacktestResult


def compute_score(result: BacktestResult, config: RankConfig = None) -> float | None:
    ranker = Ranker(config) if config else Ranker()
    return ranker.compute_score(result)



# ── Fixtures ──────────────────────────────────────────────────────────

def make_result(**kwargs) -> BacktestResult:
    defaults = dict(
        pnl_pct=10.0,
        win_rate=0.6,
        sharpe=1.5,
        max_drawdown_pct=8.0,
        num_trades=50,
        equity_curve=[],
    )
    defaults.update(kwargs)
    return BacktestResult(**defaults)


def make_strategy(score: float | None, **kwargs) -> dict:
    return {"id": "test", "score": score, **kwargs}


# ── Filtri hard — devono restituire None ─────────────────────────────

def test_score_none_if_too_few_trades():
    result = make_result(num_trades=10)
    assert compute_score(result) is None


def test_score_none_if_drawdown_too_high():
    # max_drawdown = 40.0, set result 50.0 > 40.0
    result = make_result(max_drawdown_pct=50.0)
    assert compute_score(result) is None

def test_score_none_if_sharpe_too_low():
    # min_sharpe = 0.0, set result -0.5 < 0.0
    result = make_result(sharpe=-0.5)
    assert compute_score(result) is None

def test_score_none_if_pnl_too_low():
    # min_pnl = 0.0, set result -1.0 < 0.0
    result = make_result(pnl_pct=-1.0)
    assert compute_score(result) is None



# ── Strategia valida ──────────────────────────────────────────────────

def test_score_in_range_for_valid_result():
    result = make_result()
    score = compute_score(result)
    assert score is not None
    assert 0.0 <= score <= 1.0


def test_score_is_rounded_to_4_decimals():
    result = make_result()
    score = compute_score(result)
    assert score == round(score, 4)


def test_higher_pnl_gives_higher_score():
    low = compute_score(make_result(pnl_pct=3.0))
    high = compute_score(make_result(pnl_pct=15.0))
    assert high > low


def test_higher_sharpe_gives_higher_score():
    low = compute_score(make_result(sharpe=0.6))
    high = compute_score(make_result(sharpe=2.5))
    assert high > low


def test_higher_drawdown_gives_lower_score():
    low_dd = compute_score(make_result(max_drawdown_pct=3.0))
    high_dd = compute_score(make_result(max_drawdown_pct=12.0))
    assert low_dd > high_dd


# ── rank_strategies ───────────────────────────────────────────────────

def test_rank_strategies_sorted_descending():
    strategies = [
        make_strategy(0.3),
        make_strategy(0.8),
        make_strategy(0.5),
    ]
    ranked = rank_strategies(strategies)
    scores = [s["score"] for s in ranked]
    assert scores == sorted(scores, reverse=True)


def test_rank_strategies_excludes_none_scores():
    strategies = [
        make_strategy(0.5),
        make_strategy(None),
        make_strategy(0.7),
    ]
    ranked = rank_strategies(strategies)
    assert all(s["score"] is not None for s in ranked)
    assert len(ranked) == 2


def test_rank_strategies_empty_input():
    assert rank_strategies([]) == []


def test_rank_strategies_all_none():
    strategies = [make_strategy(None), make_strategy(None)]
    assert rank_strategies(strategies) == []


# ── RankConfig custom ─────────────────────────────────────────────────

def test_custom_config_changes_threshold():
    strict = RankConfig(min_trades=100)
    result = make_result(num_trades=50)
    assert compute_score(result, strict) is None


def test_custom_config_relaxed_passes():
    relaxed = RankConfig(min_trades=10, min_sharpe=0.1, min_pnl=0.5, max_drawdown=50.0)
    result = make_result(num_trades=15, sharpe=0.2, pnl_pct=1.0, max_drawdown_pct=20.0)
    assert compute_score(result, relaxed) is not None
