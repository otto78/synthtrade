"""Test per CVDCalculator (TASK-804)."""

from decimal import Decimal

import pytest

from app.scalping.intelligence.collectors.cvd_calculator import (
    BASELINE_FLOOR,
    CVDCalculator,
)


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
        assert score == 50.0

    def test_cvd_to_score_negative(self):
        """CVD negativo -> score negativo."""
        score = CVDCalculator.cvd_to_score(Decimal("-500"), Decimal("1000"))
        assert score == -50.0

    def test_cvd_to_score_zero_baseline(self):
        """Baseline zero -> score zero."""
        score = CVDCalculator.cvd_to_score(Decimal("100"), Decimal("0"))
        assert score == 0.0

    def test_cvd_to_score_clamped(self):
        """Score non supera +/- 100."""
        score = CVDCalculator.cvd_to_score(Decimal("10000"), Decimal("1"))
        assert score == 100.0

    # ── TASK-1262: baseline dinamica ──

    def test_dynamic_baseline_warmup_uses_floor(self):
        """Prima della prima finestra chiusa si usa il lower bound epsilon.

        Una baseline derivata da una sola finestra parziale amplificherebbe il
        rumore a score pieni.
        """
        calc = CVDCalculator()
        assert calc.get_dynamic_baseline() == BASELINE_FLOOR

    def test_dynamic_baseline_from_closed_windows(self):
        """La baseline e' la media delle escursioni delle finestre chiuse."""
        calc = CVDCalculator(window_size=4)
        for qty in (2.0, 2.0, 2.0, 2.0):  # finestra 1: +8
            calc.on_trade(price=50000, quantity=qty, is_buyer_maker=False)
        assert calc._trades_since_reset == 0
        for qty in (1.0, 1.0, 1.0, 1.0):  # finestra 2: -4
            calc.on_trade(price=50000, quantity=qty, is_buyer_maker=True)
        # finestre: |8| e |-4| -> media 6.0
        assert calc.get_dynamic_baseline() == Decimal("6.0")

    def test_dynamic_baseline_ignores_sign(self):
        """Escursioni negative e positive contano con lo stesso peso."""
        calc = CVDCalculator(window_size=2)
        for _ in range(2):
            calc.on_trade(price=1, quantity=10.0, is_buyer_maker=False)  # finestra +20
        for _ in range(2):
            calc.on_trade(price=1, quantity=10.0, is_buyer_maker=True)   # finestra -20
        assert calc.get_dynamic_baseline() == Decimal("20.0")

    def test_dynamic_baseline_respects_floor(self):
        """Su volumi sub-floor la baseline non scende sotto l'epsilon."""
        calc = CVDCalculator(window_size=2)
        for _ in range(2):
            calc.on_trade(price=1, quantity=0.001, is_buyer_maker=False)
        assert calc.get_dynamic_baseline() == BASELINE_FLOOR

    def test_dynamic_baseline_changes_score_scale_vs_hardcoded(self):
        """Il caso reale BTC-EUR: baseline 1000 sprecava il 15% del peso.

        Escursioni da 0.2 BTC per finestra: con la baseline hardcoded lo score
        sarebbe 0.02 punti, con quella dinamica il segnale torna su scala utile.
        """
        calc = CVDCalculator(window_size=2)
        for _ in range(2):
            calc.on_trade(price=1, quantity=0.2, is_buyer_maker=False)  # finestra +0.4
        baseline = calc.get_dynamic_baseline()
        assert baseline == Decimal("0.4")

        hardcoded = CVDCalculator.cvd_to_score(Decimal("0.4"), Decimal("1000"))
        dynamic = CVDCalculator.cvd_to_score(Decimal("0.4"), baseline)
        assert abs(hardcoded) < 1.0
        assert dynamic == 100.0

    def test_dynamic_baseline_floor_does_not_dominate_real_scale(self):
        """Il floor non deve essere piu' grande della scala reale osservata.

        TASK-1262 specificava un lower bound di 5.0 BTC, ma le finestre di BTC-EUR
        valgono 0.05-0.2 BTC: con quel floor il rapporto restava sotto 0.2 e il
        fix era privo di effetto proprio dove serviva.
        """
        calc = CVDCalculator(window_size=2)
        for _ in range(2):
            calc.on_trade(price=1, quantity=0.1, is_buyer_maker=False)  # finestra +0.2
        baseline = calc.get_dynamic_baseline()
        assert baseline == Decimal("0.2")
        assert baseline < BASELINE_FLOOR * 100

    def test_dynamic_baseline_history_is_bounded(self):
        """Lo storico delle finestre non cresce indefinitamente."""
        calc = CVDCalculator(window_size=1)
        for _ in range(50):
            calc.on_trade(price=1, quantity=1.0, is_buyer_maker=False)
        assert len(calc._historical_max_abs) == 20
