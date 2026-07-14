"""Test per SignalAggregator (TASK-804).

Verifica la logica ibrida:
  - Segnale bloccato se intelligence contraddice il tecnico
  - Segnale eseguito se allineato
  - Confidenza combinata
  - Soglia minima
"""

import pytest
from typing import Dict, Optional

from app.scalping.engine.signal_aggregator import (
    ExecutionDecision,
    SignalAggregator,
    TechnicalSignal,
)
from app.scalping.models.intelligence import SignalScore


_5_COLLECTORS: Dict[str, float] = {
    "fear_greed": 1.0,
    "funding_rate": 1.0,
    "cvd": 1.0,
    "long_short_ratio": 1.0,
    "sentiment": 1.0,
}


def _make_score(
    total: float = 65.0,
    bias: str = "bullish",
    tradeable: bool = True,
    strength: float = 65.0,
    breakdown: Optional[Dict[str, float]] = None,
) -> SignalScore:
    return SignalScore(
        total=total,
        bias=bias,
        tradeable=tradeable,
        signal_strength=strength,
        breakdown=breakdown or _5_COLLECTORS,
        symbol="BTCUSDT",
    )


class TestSignalAggregator:
    def setup_method(self):
        self.aggregator = SignalAggregator(min_confidence=0.6)

    def test_bypass_when_few_collectors(self):
        """Bypass intelligence se <= 3 collector hanno risposto (mancanza dati)."""
        score = _make_score(
            total=1.0, bias="neutral", tradeable=False, strength=5.0,
            breakdown={"fear_greed": 1.0, "sentiment": 0.5},  # solo 2 collector
        )
        technical = TechnicalSignal(type="BUY", confidence=0.8)

        result = self.aggregator.should_execute(technical, score)

        # bypass attivato, execute=True se confidence sufficiente
        assert result.execute is True
        assert result.reason is not None
        assert "fallback" in result.reason

    def test_blocks_when_4plus_collectors_neutral(self):
        """Con 4+ collector e score < 5.0, blocca per intelligenza neutrale."""
        score = _make_score(
            total=1.2, bias="neutral", tradeable=False, strength=5.0,
        )
        technical = TechnicalSignal(type="BUY", confidence=0.8)

        result = self.aggregator.should_execute(technical, score)

        assert result.execute is False
        assert result.reason is not None
        assert "neutrale" in result.reason.lower()

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
        assert "threshold" in result.reason.lower()

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

        # upstream weighting: 70% tecnico / 30% intelligence
        # signal_strength/100 = 0.8, technical = 0.9 -> 0.8*0.3 + 0.9*0.7 = 0.87
        assert result.confidence == pytest.approx(0.87, rel=0.01)