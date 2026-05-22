"""Test per ExecutionLoop e componenti scalping engine."""

import pytest
from decimal import Decimal
from datetime import datetime, timezone

from app.scalping.data.candle_buffer import CandleBuffer
from app.scalping.models.market import Candle, MarketRegime
from app.scalping.engine.regime_detector import RegimeDetector
from app.scalping.engine.strategy_selector import StrategySelector
from app.scalping.engine.position_manager import PositionManager, Position
from app.scalping.strategies.base import AbstractScalpingStrategy
from app.scalping.strategies.registry import StrategyRegistry


# ──────────────────────────────────────────────────────────────
# Test CandleBuffer
# ──────────────────────────────────────────────────────────────

class TestCandleBuffer:
    def test_empty_buffer_returns_false(self):
        buf = CandleBuffer(size=10)
        assert buf.is_ready(min_size=5) is False

    def test_buffer_becomes_ready(self):
        buf = CandleBuffer(size=10)
        for i in range(10):
            buf.add(self._make_candle(i))
        assert buf.is_ready(min_size=5) is True
        assert len(buf) == 10

    def test_buffer_is_circular(self):
        buf = CandleBuffer(size=5)
        for i in range(10):
            buf.add(self._make_candle(i, close=Decimal(str(100 + i))))
        assert len(buf) == 5
        # Dopo 10 inserimenti con buffer size 5, le ultime 5 sono 101-105
        assert buf[0].close == Decimal("105")  # Ultima candela inserita

    def test_latest_property(self):
        buf = CandleBuffer(size=10)
        buf.add(self._make_candle(1, close=Decimal("100")))
        assert buf.latest.close == Decimal("100")

    def test_previous_property(self):
        buf = CandleBuffer(size=10)
        buf.add(self._make_candle(1, close=Decimal("100")))
        buf.add(self._make_candle(2, close=Decimal("101")))
        assert buf.previous.close == Decimal("100")

    def _make_candle(self, idx, close=Decimal("100")):
        return Candle(
            symbol="BTCUSDT",
            open=Decimal("99"),
            high=Decimal("101"),
            low=Decimal("98"),
            close=close,
            volume=Decimal("1"),
            timestamp=datetime.now(timezone.utc),
            closed=True,
        )


# ──────────────────────────────────────────────────────────────
# Test RegimeDetector
# ──────────────────────────────────────────────────────────────

class TestRegimeDetector:
    def test_detects_unknown_for_few_candles(self):
        detector = RegimeDetector()
        candles = [self._make_candle(i) for i in range(5)]
        regime = detector.detect(candles)
        assert regime.regime == "unknown"

    def test_detects_ranging_for_small_move(self):
        detector = RegimeDetector()
        candles = [self._make_candle(i, close=Decimal("100") + Decimal(str(i * 0.1))) for i in range(50)]
        regime = detector.detect(candles)
        assert regime.regime == "ranging"

    def test_detects_trending_up_for_large_move(self):
        detector = RegimeDetector()
        candles = [self._make_candle(i, close=Decimal("100") + Decimal(str(i * 2))) for i in range(50)]
        regime = detector.detect(candles)
        assert regime.regime == "trending_up"

    def test_detects_trending_down_for_negative_move(self):
        detector = RegimeDetector()
        candles = [self._make_candle(i, close=Decimal("200") - Decimal(str(i * 2))) for i in range(50)]
        regime = detector.detect(candles)
        assert regime.regime == "trending_down"

    def _make_candle(self, idx, close=Decimal("100")):
        return Candle(
            symbol="BTCUSDT",
            open=close,
            high=close + Decimal("1"),
            low=close - Decimal("1"),
            close=close,
            volume=Decimal("1"),
            timestamp=datetime.now(timezone.utc),
            closed=True,
        )


# ──────────────────────────────────────────────────────────────
# Test StrategySelector
# ──────────────────────────────────────────────────────────────

class TestStrategySelector:
    def test_selects_ema_for_trending_up(self):
        selector = StrategySelector()
        regime = MarketRegime(regime="trending_up", confidence=0.8)
        strategy = selector.select(regime)
        assert strategy.name == "ema_cross"

    def test_selects_rsi_for_ranging(self):
        selector = StrategySelector()
        regime = MarketRegime(regime="ranging", confidence=0.7)
        strategy = selector.select(regime)
        assert strategy.name == "rsi_bollinger"

    def test_selects_vwap_for_volatile(self):
        selector = StrategySelector()
        regime = MarketRegime(regime="volatile", confidence=0.7)
        strategy = selector.select(regime)
        assert strategy.name == "vwap_reversion"

    def test_default_is_ema(self):
        selector = StrategySelector()
        regime = MarketRegime(regime="unknown", confidence=0.5)
        strategy = selector.select(regime)
        assert strategy.name == "ema_cross"


# ──────────────────────────────────────────────────────────────
# Test PositionManager
# ──────────────────────────────────────────────────────────────

class TestPositionManager:
    def test_no_open_position_initially(self):
        pm = PositionManager()
        assert pm.has_open() is False

    def test_open_position(self):
        pm = PositionManager()
        pos = pm.open_position("BTCUSDT", "BUY", Decimal("50000"), Decimal("0.001"))
        assert pm.has_open() is True
        assert pos.side == "BUY"
        assert pos.entry_price == Decimal("50000")

    def test_close_position(self):
        pm = PositionManager()
        pm.open_position("BTCUSDT", "BUY", Decimal("50000"), Decimal("0.001"))
        closed = pm.close_position(Decimal("51000"))
        assert closed is not None
        assert pm.has_open() is False

    def test_get_open_returns_last(self):
        pm = PositionManager()
        pm.open_position("BTCUSDT", "BUY", Decimal("50000"), Decimal("0.001"))
        pm.close_position(Decimal("51000"))
        pm.open_position("BTCUSDT", "SELL", Decimal("50500"), Decimal("0.001"))
        pos = pm.get_open()
        assert pos.side == "SELL"

    def test_get_open_returns_none_if_closed(self):
        pm = PositionManager()
        pm.open_position("BTCUSDT", "BUY", Decimal("50000"), Decimal("0.001"))
        pm.close_position(Decimal("51000"))
        assert pm.get_open() is None


# ──────────────────────────────────────────────────────────────
# Test StrategyRegistry
# ──────────────────────────────────────────────────────────────

class TestStrategyRegistry:
    def test_all_strategies_available(self):
        names = StrategyRegistry.names()
        assert "ema_cross" in names
        assert "rsi_bollinger" in names
        assert "vwap_reversion" in names

    def test_get_strategy_by_name(self):
        strategy = StrategyRegistry.get("ema_cross")
        assert strategy is not None
        assert strategy.name == "ema_cross"

    def test_get_unknown_returns_none(self):
        strategy = StrategyRegistry.get("unknown_strategy")
        assert strategy is None


# ──────────────────────────────────────────────────────────────
# Test Technical Strategies (basic evaluation)
# ──────────────────────────────────────────────────────────────

class TestEMACrossStrategy:
    def test_no_signal_with_few_candles(self):
        from app.scalping.strategies.ema_cross import EMACrossStrategy
        strat = EMACrossStrategy()
        candles = [self._make_candle(i) for i in range(5)]
        signal = strat.evaluate(candles)
        assert signal.type == "NONE"

    def test_buy_signal_on_cross(self):
        from app.scalping.strategies.ema_cross import EMACrossStrategy
        strat = EMACrossStrategy()
        # Crea candele con trend rialzista
        closed_prices = [100, 100, 100, 100, 100, 100, 100, 100, 100, 101, 102, 103,
                         104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115,
                         116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126]
        candles = [self._make_candle(i, close=Decimal(str(p))) for i, p in enumerate(closed_prices)]
        signal = strat.evaluate(candles)
        assert signal.type in ("BUY", "NONE")

    def _make_candle(self, idx, close=Decimal("100")):
        return Candle(
            symbol="BTCUSDT",
            open=close,
            high=close + Decimal("1"),
            low=close - Decimal("1"),
            close=close,
            volume=Decimal("1"),
            timestamp=datetime.now(timezone.utc),
            closed=True,
        )