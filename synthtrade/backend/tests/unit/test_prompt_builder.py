import pytest
from app.ai.prompt_builder import build_prompt, build_system_prompt
from app.ai.schemas import (
    EvalPromptInput, MarketContext, OhlcvSummary, StrategyContext
)
from datetime import datetime


def make_input() -> EvalPromptInput:
    summary = OhlcvSummary(
        symbol="BTC/USDT", timeframe="1h", candles=100,
        price_min=58000.0, price_max=63000.0, price_last=61000.0,
        volume_avg=1500.0, volatility_pct=1.8, trend_pct=5.2
    )
    market = MarketContext(symbol="BTC/USDT", timeframe="1h",
                           regime="trending", summary=summary,
                           generated_at=datetime.now(UTC))
    strategy = StrategyContext(
        strategy_id="s1", title="EMA Cross", template="trend_ema",
        params={"ema_fast": 9, "ema_slow": 21},
        pnl_pct=12.5, win_rate=0.62, sharpe=1.4,
        max_drawdown_pct=6.2, num_trades=28, score=0.75
    )
    return EvalPromptInput(market=market, strategy=strategy)


def test_build_prompt_includes_symbol():
    prompt = build_prompt(make_input())
    assert "BTC/USDT" in prompt


def test_build_prompt_includes_timeframe():
    prompt = build_prompt(make_input())
    assert "1h" in prompt


def test_build_prompt_includes_metrics():
    prompt = build_prompt(make_input())
    assert "12.5" in prompt   # pnl_pct
    assert "62%" in prompt    # win_rate formattato
    assert "1.4" in prompt    # sharpe


def test_build_prompt_includes_json_instructions():
    prompt = build_prompt(make_input())
    assert "score" in prompt
    assert "verdict" in prompt
    assert "reasoning" in prompt
    assert "PROMOTE" in prompt


def test_build_prompt_truncates_at_token_budget():
    prompt = build_prompt(make_input(), max_chars=200)
    assert len(prompt) <= 200


def test_build_system_prompt_contains_analyst_role():
    system = build_system_prompt()
    assert "quantitativ" in system.lower() or "analyst" in system.lower()
    assert "JSON" in system
