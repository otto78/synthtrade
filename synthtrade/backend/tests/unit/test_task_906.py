"""TASK-906 — Falling Knife Protection: blocca mean-reversion BUY durante crash."""

import pytest
from datetime import datetime, timezone

from app.scalping.engine.signal_aggregator import (
    SignalAggregator,
    ExecutionDecision,
    TechnicalSignal,
    FALLING_KNIFE_TREND_THRESHOLD,
)
from app.scalping.models.intelligence import SignalScore


def _make_score(
    total: float = -60.0,
    bias: str = "bearish",
    tradeable: bool = True,
    trend_5m: float | None = None,
    trend_direction: str | None = None,
) -> SignalScore:
    return SignalScore(
        total=total,
        bias=bias,
        tradeable=tradeable,
        signal_strength=abs(total),
        trend_5m=trend_5m,
        trend_direction=trend_direction,
        breakdown={
            "funding_rate": -5.0,
            "order_book_imbalance": -3.0,
            "open_interest": -2.0,
            "long_short_ratio": -4.0,
            "fear_greed": -3.0,
            "cvd": -1.0,
        },
    )


def _make_technical(
    type: str = "BUY",
    confidence: float = 0.8,
    source: str = "rsi_bollinger",
) -> TechnicalSignal:
    return TechnicalSignal(type=type, confidence=confidence, source=source)


@pytest.fixture
def aggregator():
    return SignalAggregator(min_confidence=0.3)


# ── Test 1: Falling knife blocca mean-reversion BUY ──

def test_falling_knife_blocks_mean_reversion_buy(aggregator):
    score = _make_score(trend_5m=-35.0, trend_direction="diverging")
    tech = _make_technical("BUY", source="rsi_bollinger")

    decision = aggregator.should_execute(tech, score, symbol="BTC-EUR")

    assert decision.execute is False
    assert "FALLING KNIFE" in decision.reason
    assert decision.is_mean_reversion_override is False


# ── Test 2: Falling knife NON blocca se trend è converging (score che recovery) ──

def test_falling_knife_allows_converging_trend(aggregator):
    score = _make_score(trend_5m=-35.0, trend_direction="converging")
    tech = _make_technical("BUY", source="rsi_bollinger")

    decision = aggregator.should_execute(tech, score, symbol="BTC-EUR")

    # converging = score si sta avvicinando a zero → non è crash
    assert decision.execute is True
    assert "FALLING KNIFE" not in (decision.reason or "")


# ── Test 3: Falling knife NON blocca se drop moderato (trend_5m > soglia) ──

def test_falling_knife_allows_mild_drop(aggregator):
    score = _make_score(trend_5m=-10.0, trend_direction="diverging")
    tech = _make_technical("BUY", source="rsi_bollinger")

    decision = aggregator.should_execute(tech, score, symbol="BTC-EUR")

    assert decision.execute is True
    assert "FALLING KNIFE" not in (decision.reason or "")


# ── Test 4: Falling knife NON blocca se trend_5m è None (storico insufficiente) ──

def test_falling_knife_allows_no_trend_data(aggregator):
    score = _make_score(trend_5m=None, trend_direction=None)
    tech = _make_technical("BUY", source="rsi_bollinger")

    decision = aggregator.should_execute(tech, score, symbol="BTC-EUR")

    assert decision.execute is True


# ── Test 5: Falling knife NON influenza segnali non mean-reversion ──

def test_falling_knife_does_not_block_regular_buy(aggregator):
    """Un BUY normale (non da strategia mean-reversion) non è filtrato dalla guard."""
    score = _make_score(total=30.0, bias="bullish", trend_5m=-35.0, trend_direction="diverging")
    tech = _make_technical("BUY", confidence=0.8, source="ema_cross")

    decision = aggregator.should_execute(tech, score, symbol="BTC-EUR")

    # BUY + bullish bias → dovrebbe passare (non è nel ramo bearish)
    assert decision.execute is True
    assert "FALLING KNIFE" not in (decision.reason or "")


# ── Test 6: Falling knife NON blocca mean-reversion SELL ──

def test_falling_knife_does_not_block_mean_reversion_sell(aggregator):
    """MEAN-REVERSION SELL con bias bullish non è un falling knife (è chiusura range)."""
    score = _make_score(total=30.0, bias="bullish", trend_5m=-35.0, trend_direction="diverging")
    tech = _make_technical("SELL", source="rsi_bollinger")

    decision = aggregator.should_execute(tech, score, symbol="BTC-EUR")

    assert decision.execute is True


# ── Test 7: Falling knife NON blocca CLOSE (sempre permesso) ──

def test_falling_knife_does_not_block_close(aggregator):
    score = _make_score(trend_5m=-50.0, trend_direction="diverging")
    tech = _make_technical("CLOSE")

    decision = aggregator.should_execute(tech, score, symbol="BTC-EUR")

    assert decision.execute is True


# ── Test 8: Falling knife con stoch_rsi_bb_squeeze (altra mean-reversion strategy) ──

def test_falling_knife_blocks_stoch_rsi_strategy(aggregator):
    score = _make_score(trend_5m=-25.0, trend_direction="diverging")
    tech = _make_technical("BUY", source="stoch_rsi_bb_squeeze")

    decision = aggregator.should_execute(tech, score, symbol="BTC-EUR")

    assert decision.execute is False
    assert "FALLING KNIFE" in decision.reason


# ── Test 9: Falling knife alla soglia esatta (edge case: -20.0 = NON blocca, threshold è escluso) ──

def test_falling_knife_at_threshold_boundary(aggregator):
    """trend_5m == -20.0 NON blocca (< -20.0, non <=)."""
    score = _make_score(trend_5m=-20.0, trend_direction="diverging")
    tech = _make_technical("BUY", source="rsi_bollinger")

    decision = aggregator.should_execute(tech, score, symbol="BTC-EUR")

    assert decision.execute is True  # -20.0 non è < -20.0


# ── Test 10: Falling knife con trend_5m molto negativo (crash estremo) ──

def test_falling_knife_extreme_crash(aggregator):
    score = _make_score(trend_5m=-80.0, trend_direction="diverging")
    tech = _make_technical("BUY", source="rsi_bollinger")

    decision = aggregator.should_execute(tech, score, symbol="BTC-EUR")

    assert decision.execute is False
    assert "FALLING KNIFE" in decision.reason
    assert "-80.0" in decision.reason


# ── Test 11: Falling knife con trend_direction "stable" NON blocca ──

def test_falling_knife_allows_stable_direction(aggregator):
    score = _make_score(trend_5m=-25.0, trend_direction="stable")
    tech = _make_technical("BUY", source="rsi_bollinger")

    decision = aggregator.should_execute(tech, score, symbol="BTC-EUR")

    # stable + trend_5m grande → non blocca (direction non è diverging)
    assert decision.execute is True


# ── Test 12: Costante FALLING_KNIFE_TREND_THRESHOLD esiste e ha valore corretto ──

def test_falling_knife_threshold_constant():
    assert FALLING_KNIFE_TREND_THRESHOLD == -20.0
