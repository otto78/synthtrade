"""Test suite componenti core scalping (TASK-868)."""
import time
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.scalping.session_load_guard import SessionLoadGuard
from app.scalping.engine.position_manager import PositionManager, PositionStatus
from app.scalping.engine.signal_aggregator import SignalAggregator, TechnicalSignal
from app.scalping.models.intelligence import SignalScore


# ── SessionLoadGuard ──────────────────────────────────────────────────────────

def test_guard_starts_idle():
    g = SessionLoadGuard()
    assert g._state == "idle"
    assert not g.is_ready()


def test_guard_idle_to_ready():
    g = SessionLoadGuard()
    g.start_loading()
    for phase in SessionLoadGuard.REQUIRED_PHASES:
        g.complete_phase(phase)
    assert g.is_ready()


def test_guard_reset():
    g = SessionLoadGuard()
    g.start_loading()
    g.complete_phase("db_phase")
    g.reset()
    assert g._state == "idle"
    assert not g.is_ready()


def test_guard_fail_blocks():
    g = SessionLoadGuard()
    g.start_loading()
    g.fail("error")
    assert not g.is_ready()


# ── PositionManager ───────────────────────────────────────────────────────────

def test_position_open_close_cycle():
    pm = PositionManager()
    assert not pm.has_open()
    pos = pm.open_position("BNBUSDC", "BUY", Decimal("620"), Decimal("0.016"))
    assert pm.has_open()
    closed = pm.close_position(Decimal("625"))
    assert closed is pos
    assert pos.status == PositionStatus.CLOSED
    assert pos.exit_price == Decimal("625")   # TASK-867
    assert pos.closed_at is not None           # TASK-867
    assert not pm.has_open()


def test_close_when_no_position():
    assert PositionManager().close_position(Decimal("100")) is None


# ── SignalAggregator ──────────────────────────────────────────────────────────

def _score(total, bias, tradeable=True):
    return SignalScore(
        total=total, bias=bias, tradeable=tradeable,
        breakdown={"funding_rate": total, "cvd": total, "open_interest": total, "long_short_ratio": total},
        signal_strength=abs(total), symbol="BNBUSDC",
        computed_at=datetime.now(timezone.utc),
    )


def test_close_signal_always_allowed():
    agg = SignalAggregator(min_confidence=0.3)
    d = agg.should_execute(TechnicalSignal("CLOSE", 0.8), _score(0, "neutral", False))
    assert d.execute is True


def test_none_signal_blocked():
    d = SignalAggregator().should_execute(TechnicalSignal("NONE", 0.9), _score(20, "bullish"))
    assert d.execute is False


def test_neutral_bias_blocks():
    d = SignalAggregator(min_confidence=0.3).should_execute(
        TechnicalSignal("BUY", 0.9), _score(3, "neutral", False), symbol="BNBUSDC"
    )
    assert d.execute is False


def test_bias_mismatch_blocks():
    d = SignalAggregator(min_confidence=0.3).should_execute(
        TechnicalSignal("BUY", 0.9, source="ema_cross"), _score(20, "bearish"), symbol="BNBUSDC"
    )
    assert d.execute is False


def test_aligned_signal_executes():
    d = SignalAggregator(min_confidence=0.3).should_execute(
        TechnicalSignal("BUY", 0.8, source="ema_cross"), _score(20, "bullish"), symbol="BNBUSDC"
    )
    assert d.execute is True


# ── CircuitBreaker ────────────────────────────────────────────────────────────

def test_cb_opens_after_3_failures():
    from app.scalping.intelligence.collectors.circuit_breaker import CollectorCircuitBreaker
    cb = CollectorCircuitBreaker("test")
    assert cb.is_available()
    for _ in range(3):
        cb.on_failure()
    assert not cb.is_available()


def test_cb_recovers_after_reset_period():
    from app.scalping.intelligence.collectors.circuit_breaker import CollectorCircuitBreaker
    cb = CollectorCircuitBreaker("test")
    cb.RESET_AFTER_SEC = 0
    for _ in range(3):
        cb.on_failure()
    cb._opened_at = time.monotonic() - 1
    assert cb.is_available()  # half_open
    cb.on_success()
    assert cb._state == "closed"
