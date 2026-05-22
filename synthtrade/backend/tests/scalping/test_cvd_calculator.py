"""Test per CVDCalculator (TASK-804)."""

from decimal import Decimal

import pytest

from app.scalping.intelligence.collectors.cvd_calculator import CVDCalculator


class TestCVDCalculator:
    def test_initial_cvd_zero(self):
        """CVD parte da zero."""
        calc = CVDCalculator()
        assert calc.cvd == Decimal("0")

    def test_buy_trade_increases_cvd(self):
        """Buy aggressivo (is_buyer_maker=False) aumenta CVD."""
        calc = CVDCalculator()
        calc.on_trade(price=50000, quantity=1.0, is_buyer_maker=False)
        assert calc.cvd == Decimal("1.0")

    def test_sell_trade_decreases_cvd(self):
        """Sell aggressivo (is_buyer_maker=True) diminuisce CVD."""
        calc = CVDCalculator()
        calc.on_trade(price=50000, quantity=1.0, is_buyer_maker=True)
        assert calc.cvd == Decimal("-1.0")

    def test_multiple_trades(self):
        """Multipli trades si accumulano correttamente."""
        calc = CVDCalculator()
        calc.on_trade(price=50000, quantity=0.5, is_buyer_maker=False)  # +0.5
        calc.on_trade(price=50100, quantity=0.3, is_buyer_maker=True)  # -0.3
        calc.on_trade(price=50200, quantity=0.2, is_buyer_maker=False)  # +0.2
        assert calc.cvd == Decimal("0.4")

    def test_snapshot_returns_data(self):
        """Snapshot ritorna CVDData con trend."""
        calc = CVDCalculator()
        calc.on_trade(price=50000, quantity=1.0, is_buyer_maker=False)
        snapshot = calc.snapshot("BTCUSDT")
        assert snapshot.symbol == "BTCUSDT"
        assert snapshot.cvd == Decimal("1.0")
        assert snapshot.trend is None  # under 2 prices

    def test_snapshot_with_trend_rising(self):
        """Trend 'rising' quando prezzo sale."""
        calc = CVDCalculator()
        calc.on_trade(price=50000, quantity=1.0, is_buyer_maker=False)
        calc.on_trade(price=50200, quantity=1.0, is_buyer_maker=False)
        snapshot = calc.snapshot("BTCUSDT")
        assert snapshot.trend == "rising"

    def test_snapshot_with_trend_falling(self):
        """Trend 'falling' quando prezzo scende."""
        calc = CVDCalculator()
        calc.on_trade(price=50200, quantity=1.0, is_buyer_maker=False)
        calc.on_trade(price=50000, quantity=1.0, is_buyer_maker=False)
        snapshot = calc.snapshot("BTCUSDT")
        assert snapshot.trend == "falling"

    def test_snapshot_with_trend_neutral(self):
        """Trend 'neutral' quando prezzo stabile."""
        calc = CVDCalculator()
        calc.on_trade(price=50000, quantity=1.0, is_buyer_maker=False)
        calc.on_trade(price=50001, quantity=1.0, is_buyer_maker=False)
        snapshot = calc.snapshot("BTCUSDT")
        assert snapshot.trend == "neutral"

    def test_reset_clears_cvd(self):
        """Reset azzera CVD."""
        calc = CVDCalculator()
        calc.on_trade(price=50000, quantity=1.0, is_buyer_maker=False)
        calc.reset()
        assert calc.cvd == Decimal("0")

    def test_cvd_to_score_positive(self):
        """CVD positivo -> score positivo."""
        score = CVDCalculator.cvd_to_score(Decimal("500"), Decimal("1000"))
        assert score > 0
        assert score <= 25.0

    def test_cvd_to_score_negative(self):
        """CVD negativo -> score negativo."""
        score = CVDCalculator.cvd_to_score(Decimal("-500"), Decimal("1000"))
        assert score < 0
        assert score >= -25.0

    def test_cvd_to_score_zero_baseline(self):
        """Baseline zero -> score zero."""
        score = CVDCalculator.cvd_to_score(Decimal("100"), Decimal("0"))
        assert score == 0.0

    def test_cvd_to_score_clamped(self):
        """Score non supera +/- 25."""
        score = CVDCalculator.cvd_to_score(Decimal("10000"), Decimal("1"))
        assert -25.0 <= score <= 25.0