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


class TestTask1251StrongBearishGuard:
    """TASK-1251: verifica blocco override mean-reversion con bias bearish forte.

    Il blocco si attiva quando market_score.total < -15.0 (default soglia).
    Il test usa min_confidence=0.4 per non intralciare con la soglia di confidenza.
    """

    def setup_method(self):
        self.aggregator = SignalAggregator(min_confidence=0.4)

    def test_blocks_mean_reversion_buy_when_strong_bearish(self):
        """TASK-1251: rsi_bollinger BUY bloccato quando bias bearish forte (score < -15)."""
        # Score bearish forte: -20 < -15 → deve bloccare
        score = _make_score(total=-20.0, bias="bearish", tradeable=True, strength=20.0)
        technical = TechnicalSignal(type="BUY", confidence=0.85, source="rsi_bollinger")

        result = self.aggregator.should_execute(technical, score, symbol="BTCEUR")

        assert result.execute is False
        assert result.is_mean_reversion_override is False
        assert result.reason is not None
        assert "1251" in result.reason or "strong" in result.reason.lower() or "soglia" in result.reason.lower()

    def test_allows_mean_reversion_buy_when_weakly_bearish(self):
        """TASK-1251: rsi_bollinger BUY permesso quando bias bearish debole (-5 > score > -15)."""
        # Score bearish debole: -10 > -15 → override ancora consentito
        score = _make_score(total=-10.0, bias="bearish", tradeable=True, strength=10.0)
        technical = TechnicalSignal(type="BUY", confidence=0.85, source="rsi_bollinger")

        result = self.aggregator.should_execute(technical, score, symbol="BTCEUR")

        assert result.execute is True
        assert result.is_mean_reversion_override is True

    def test_blocks_at_threshold_boundary(self):
        """TASK-1251: score esattamente al limite (-15.0) non supera il blocco (< è strict)."""
        # score == -15.0 → NON è < -15.0, quindi l'override è permesso
        score_at_limit = _make_score(total=-15.0, bias="bearish", tradeable=True, strength=15.0)
        technical = TechnicalSignal(type="BUY", confidence=0.85, source="rsi_bollinger")
        result_at = self.aggregator.should_execute(technical, score_at_limit, symbol="BTCEUR")
        assert result_at.execute is True  # -15.0 == -15.0 non è < -15.0

        # score == -15.1 → è < -15.0, bloccato
        score_over = _make_score(total=-15.1, bias="bearish", tradeable=True, strength=15.1)
        result_over = self.aggregator.should_execute(technical, score_over, symbol="BTCEUR")
        assert result_over.execute is False

    def test_non_mean_reversion_buy_still_blocked_by_bias(self):
        """TASK-1251: BUY da ema_cross con bias bearish viene bloccato dal filtro normale."""
        score = _make_score(total=-20.0, bias="bearish", tradeable=True, strength=20.0)
        technical = TechnicalSignal(type="BUY", confidence=0.85, source="ema_cross")

        result = self.aggregator.should_execute(technical, score, symbol="BTCEUR")

        assert result.execute is False
        assert result.is_mean_reversion_override is False
        assert "conflitto" in result.reason.lower()


class TestTask1250MacroTrendGuard:
    """TASK-1250: verifica blocco override mean-reversion con macro context BTC > EMA20 4h.

    Quando BTC > EMA20 4h, anche un override con bias debole (score > -15) deve essere bloccato.
    Il test usa score=-10 (bias debole, non bloccato da TASK-1251) e aggiunge il macro context.
    """

    def setup_method(self):
        self.aggregator = SignalAggregator(min_confidence=0.4)
        # score debole bearish: supera TASK-1251 (score > -15), ma deve essere bloccato da TASK-1250
        self.score = _make_score(total=-10.0, bias="bearish", tradeable=True, strength=10.0)
        self.technical = TechnicalSignal(type="BUY", confidence=0.85, source="rsi_bollinger")

    def test_blocks_mean_reversion_when_btc_above_ema20(self):
        """TASK-1250: macro guard blocca override quando BTC > EMA20 4h."""
        macro = {"btc_price_at_entry": 60000.0, "btc_ema20_4h": 58000.0}

        result = self.aggregator.should_execute(
            self.technical, self.score, symbol="BTCEUR", macro_context=macro
        )

        assert result.execute is False
        assert result.is_mean_reversion_override is False
        assert "1250" in result.reason or "macro" in result.reason.lower()

    def test_allows_mean_reversion_when_btc_below_ema20(self):
        """TASK-1250: macro guard NON blocca quando BTC < EMA20 4h (downtrend macro)."""
        macro = {"btc_price_at_entry": 55000.0, "btc_ema20_4h": 58000.0}

        result = self.aggregator.should_execute(
            self.technical, self.score, symbol="BTCEUR", macro_context=macro
        )

        assert result.execute is True
        assert result.is_mean_reversion_override is True

    def test_allows_when_no_macro_context(self):
        """TASK-1250: senza macro context, il comportamento è invariato (backward compat)."""
        result = self.aggregator.should_execute(
            self.technical, self.score, symbol="BTCEUR", macro_context=None
        )
        # Score -10 debole + no macro → override permesso (TASK-1251 non blocca)
        assert result.execute is True
        assert result.is_mean_reversion_override is True

    def test_allows_when_ema20_is_zero(self):
        """TASK-1250: ema20_4h=0 (dato non disponibile) → guard disattivato."""
        macro = {"btc_price_at_entry": 60000.0, "btc_ema20_4h": 0.0}

        result = self.aggregator.should_execute(
            self.technical, self.score, symbol="BTCEUR", macro_context=macro
        )
        assert result.execute is True


class TestTask1250StrategySelector:
    """TASK-1250: verifica override ranging -> ema_cross in StrategySelector."""

    def setup_method(self):
        from app.scalping.engine.strategy_selector import StrategySelector
        from app.scalping.models.market import MarketRegime
        self.selector = StrategySelector(regime_strategy_map={
            "ranging": "rsi_bollinger",
            "trending_up": "ema_cross",
            "trending_down": "rsi_bollinger",
            "volatile": "vwap_reversion",
            "unknown": "vwap_reversion",
        })
        self.MarketRegime = MarketRegime

    def test_overrides_ranging_to_ema_cross_when_btc_above_ema20(self):
        """TASK-1250: ranging regime con BTC sopra EMA20 4h → ema_cross."""
        regime = self.MarketRegime(regime="ranging", confidence=0.6)
        macro = {"btc_price_at_entry": 60000.0, "btc_ema20_4h": 58000.0}

        name = self.selector.get_name_for_regime(regime, macro_context=macro)

        assert name == "ema_cross"

    def test_no_override_when_btc_below_ema20(self):
        """TASK-1250: ranging regime con BTC sotto EMA20 4h → rsi_bollinger (invariato)."""
        regime = self.MarketRegime(regime="ranging", confidence=0.6)
        macro = {"btc_price_at_entry": 55000.0, "btc_ema20_4h": 58000.0}

        name = self.selector.get_name_for_regime(regime, macro_context=macro)

        assert name == "rsi_bollinger"

    def test_no_override_for_trending_up(self):
        """TASK-1250: trending_up NON viene toccato (già correttamente -> ema_cross)."""
        regime = self.MarketRegime(regime="trending_up", confidence=0.85)
        macro = {"btc_price_at_entry": 60000.0, "btc_ema20_4h": 58000.0}

        name = self.selector.get_name_for_regime(regime, macro_context=macro)

        assert name == "ema_cross"

    def test_no_override_when_no_macro(self):
        """TASK-1250: senza macro context → comportamento invariato."""
        regime = self.MarketRegime(regime="ranging", confidence=0.6)

        name = self.selector.get_name_for_regime(regime, macro_context=None)


        assert name == "rsi_bollinger"


class TestTask1252MeanReversionNotBlockedByEMA20:
    """TASK-1252: verifica che mean_reversion_override non sia bloccato dal check btc < ema20_4h.

    Contesto: nella sessione B (25ago-1set) il signal_aggregator restituiva
    execute=True + is_mean_reversion_override=True per score ≈ -7.8 (bias bearish debole).
    Ma il candle_processor bloccava poi il trade perché BTC < EMA20 4h.
    Il fix di TASK-1252 esonera is_mean_reversion_override dal filtro btc < ema20_4h.

    Questo test verifica che il segnale prodotto dall'aggregator abbia il flag corretto
    nelle condizioni della sessione B, così il candle_processor può applicare la logica giusta.
    """

    def setup_method(self):
        self.aggregator = SignalAggregator(min_confidence=0.4)

    def test_produces_mr_override_when_btc_below_ema20(self):
        """Sessione B scenario: BTC sotto EMA20 4h, score bearish debole → is_mean_reversion_override=True.

        signal_aggregator deve produrre execute=True+is_mean_reversion_override=True.
        Il candle_processor (TASK-1252 fix) deve poi permettere l'esecuzione perché è MR.
        """
        # Condizioni esatte della sessione B: score ≈ -7.8, bias bearish, BTC sotto EMA20
        score = _make_score(total=-7.8, bias="bearish", tradeable=True, strength=7.8)
        technical = TechnicalSignal(type="BUY", confidence=0.85, source="rsi_bollinger")
        # macro: BTC sotto EMA20 → condizione che bloccava nella sessione B
        macro = {"btc_price_at_entry": 67000.0, "btc_ema20_4h": 69000.0}

        result = self.aggregator.should_execute(
            technical, score, symbol="BTC-EUR", macro_context=macro
        )

        assert result.execute is True, f"Expected execute=True, got reason: {result.reason}"
        assert result.is_mean_reversion_override is True
        # Il blocco TASK-1250 è in signal_aggregator solo per BTC > EMA20 (not <), quindi non deve intervenire
        assert "1250" not in (result.reason or "").upper() or "non bloccato" in (result.reason or "").lower()

    def test_mr_override_still_blocked_by_strong_bearish_guard(self):
        """TASK-1252 non tocca TASK-1251: score forte bearish (< -15) deve ancora bloccare."""
        score = _make_score(total=-20.0, bias="bearish", tradeable=True, strength=20.0)
        technical = TechnicalSignal(type="BUY", confidence=0.85, source="rsi_bollinger")
        macro = {"btc_price_at_entry": 67000.0, "btc_ema20_4h": 69000.0}

        result = self.aggregator.should_execute(
            technical, score, symbol="BTC-EUR", macro_context=macro
        )

        assert result.execute is False
        assert result.is_mean_reversion_override is False

    def test_mr_override_not_blocked_when_btc_slightly_below_ema20(self):
        """Scenario tipico sessione B: btc_price leggermente sotto ema20 → override deve passare."""
        score = _make_score(total=-6.9, bias="bearish", tradeable=True, strength=6.9)
        technical = TechnicalSignal(type="BUY", confidence=0.80, source="rsi_bollinger")
        macro = {"btc_price_at_entry": 68000.0, "btc_ema20_4h": 68500.0}

        result = self.aggregator.should_execute(
            technical, score, symbol="BTC-EUR", macro_context=macro
        )

        assert result.execute is True
        assert result.is_mean_reversion_override is True

    def test_directional_buy_still_blocked_btc_below_ema20_in_aggregator(self):
        """ema_cross BUY con BTC sopra EMA20 4h non è toccato da TASK-1252 (rimane in candle_processor)."""
        # In signal_aggregator, ema_cross con bias bearish viene bloccato per "conflitto"
        # (non per il macro filter, quello è nel candle_processor).
        score = _make_score(total=-10.0, bias="bearish", tradeable=True, strength=10.0)
        technical = TechnicalSignal(type="BUY", confidence=0.85, source="ema_cross")

        result = self.aggregator.should_execute(technical, score, symbol="BTC-EUR")

        assert result.execute is False
        assert result.is_mean_reversion_override is False
        assert "conflitto" in result.reason.lower()
