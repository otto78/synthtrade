"""TASK-1223: SELL signals are blocked by the long-only engine."""

from app.scalping.engine.signal_aggregator import SignalAggregator, TechnicalSignal
from app.scalping.models.intelligence import SignalScore


def _score(total: float, bias: str) -> SignalScore:
    return SignalScore(
        total=total,
        bias=bias,
        tradeable=True,
        signal_strength=abs(total),
        breakdown={
            "fear_greed": total / 32.5,
            "funding_rate": total / 43.3333333333,
            "cvd": total / 65,
            "long_short_ratio": total / 65,
            "sentiment": total / 32.5,
        },
        symbol="BTC-EUR",
    )


def test_sell_with_bearish_bias_is_blocked():
    result = SignalAggregator(min_confidence=0.3).should_execute(
        TechnicalSignal(type="SELL", confidence=0.8, source="ema_cross"),
        _score(-65.0, "bearish"),
        symbol="BTC-EUR",
    )

    assert result.execute is False
    assert result.reason == "SELL signals disabled"
    assert result.signal_type == "SELL"


def test_sell_with_bullish_bias_and_mean_reversion_is_blocked():
    result = SignalAggregator(min_confidence=0.3).should_execute(
        TechnicalSignal(type="SELL", confidence=0.8, source="rsi_bollinger"),
        _score(65.0, "bullish"),
        symbol="BTC-EUR",
    )

    assert result.execute is False
    assert result.reason == "SELL signals disabled"
    assert result.signal_type == "SELL"


def test_sell_with_bullish_bias_and_trend_source_is_blocked():
    result = SignalAggregator(min_confidence=0.3).should_execute(
        TechnicalSignal(type="SELL", confidence=0.8, source="ema_cross"),
        _score(65.0, "bullish"),
        symbol="BTC-EUR",
    )

    assert result.execute is False
    assert result.reason == "SELL signals disabled"
    assert result.signal_type == "SELL"
