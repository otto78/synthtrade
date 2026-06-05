"""Test per SignalAggregator (TASK-804).

Verifica la logica ibrida:
  - Segnale bloccato se intelligence contraddice il tecnico
  - Segnale eseguito se allineato
  - Confidenza combinata
  - Soglia minima
"""

import pytest

from app.scalping.engine.signal_aggregator import (
    ExecutionDecision,
    SignalAggregator,
    TechnicalSignal,
)
from app.scalping.models.intelligence import SignalScore


def _make_score(
    total: float = 65.0,
    bias: str = "bullish",
    tradeable: bool = True,
    strength: float = 65.0,
) -> SignalScore:
    return SignalScore(
        total=total,
        bias=bias,
        tradeable=tradeable,
        signal_strength=strength,
        symbol="BTCUSDT",
    )


class TestSignalAggregator:
    def setup_method(self):
        self.aggregator = SignalAggregator(min_confidence=0.6)

    def test_blocks_buy_when_overleveraged(self):
        """Segnale BUY bloccato se score intelligence bearish."""
        score = _make_score(total=-45.0, bias="bearish", tradeable=True, strength=45.0)
        technical = TechnicalSignal(type="BUY", confidence=0.8)

        result = self.aggregator.should_execute(technical, score)

        assert result.execute is False
        assert result.reason is not None
        assert "conflitto" in result.reason.lower()

    def test_allows_buy_when_aligned(self):
        """Segnale BUY eseguito se intelligence bullish."""
        score = _make_score(total=65.0, bias="bullish", tradeable=True, strength=65.0)
        technical = TechnicalSignal(type="BUY", confidence=0.8)

        result = self.aggregator.should_execute(technical, score)

        assert result.execute is True
        assert result.confidence > 0.5

    def test_blocks_sell_when_bullish(self):
        """Segnale SELL bloccato se intelligence bullish."""
        score = _make_score(total=65.0, bias="bullish", tradeable=True, strength=65.0)
        technical = TechnicalSignal(type="SELL", confidence=0.8)

        result = self.aggregator.should_execute(technical, score)

        assert result.execute is False
        assert result.reason is not None
        assert "conflitto" in result.reason.lower()

    def test_allows_sell_when_bearish(self):
        """Segnale SELL eseguito se intelligence bearish."""
        score = _make_score(total=-65.0, bias="bearish", tradeable=True, strength=65.0)
        technical = TechnicalSignal(type="SELL", confidence=0.8)

        result = self.aggregator.should_execute(technical, score)

        assert result.execute is True
        assert result.confidence > 0.5

    def test_blocks_when_not_tradeable(self):
        """Score non tradeable blocca qualsiasi segnale."""
        score = _make_score(total=10.0, bias="neutral", tradeable=False, strength=10.0)
        technical = TechnicalSignal(type="BUY", confidence=0.8)

        result = self.aggregator.should_execute(technical, score)

        assert result.execute is False
        assert result.reason is not None
        assert "soglia" in result.reason.lower()

    def test_blocks_neutral(self):
        """Bias neutrale blocca il trade."""
        score = _make_score(total=5.0, bias="neutral", tradeable=True, strength=5.0)
        technical = TechnicalSignal(type="BUY", confidence=0.8)

        result = self.aggregator.should_execute(technical, score)

        assert result.execute is False
        assert result.reason is not None
        assert "neutrale" in result.reason.lower()

    def test_blocks_none_signal(self):
        """Segnale tecnico NONE non produce esecuzione."""
        score = _make_score(total=65.0, bias="bullish", tradeable=True, strength=65.0)
        technical = TechnicalSignal(type="NONE", confidence=0.0)

        result = self.aggregator.should_execute(technical, score)

        assert result.execute is False
        assert result.reason is not None
        assert "nessun segnale" in result.reason.lower()

    def test_low_combined_confidence(self):
        """Confidenza combinata sotto soglia blocca."""
        score = _make_score(total=30.0, bias="bullish", tradeable=True, strength=30.0)
        technical = TechnicalSignal(type="BUY", confidence=0.1)  # molto bassa

        result = self.aggregator.should_execute(technical, score)

        assert result.execute is False
        assert result.reason is not None
        assert "confidenza" in result.reason.lower()

    def test_allows_close_when_bearish(self):
        """CLOSE permesso in contesto bearish."""
        score = _make_score(total=-45.0, bias="bearish", tradeable=True, strength=45.0)
        technical = TechnicalSignal(type="CLOSE", confidence=0.9)

        result = self.aggregator.should_execute(technical, score)

        assert result.execute is True
        assert result.confidence > 0.5

    def test_confidence_is_combined(self):
        """Confidenza combinata riflette media di intelligence e tecnico."""
        score = _make_score(total=80.0, bias="bullish", tradeable=True, strength=80.0)
        technical = TechnicalSignal(type="BUY", confidence=0.9)

        result = self.aggregator.should_execute(technical, score)

        # signal_strength/100 = 0.8, technical = 0.9 -> media = 0.85
        assert result.confidence == pytest.approx(0.85, rel=0.01)