"""TASK-908 — Resume guard: blocca resume in regime bearish senza short."""

import asyncio
import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.scalping.models.supervisor import SupervisorDecision


def _make_decision(action: str = "resume_trading", confidence: float = 0.9) -> SupervisorDecision:
    return SupervisorDecision(
        action=action,
        reason="test",
        confidence=confidence,
        market_bias="bearish",
    )


def _make_scheduler(
    regime: str = "trending_down",
    regime_confidence: float = 0.85,
    has_position: bool = False,
):
    """Crea un SupervisorScheduler con mock per testare la guard."""
    from app.scalping.supervisor.supervisor_scheduler import SupervisorScheduler

    loop_mock = MagicMock()
    loop_mock.regime = SimpleNamespace(regime=regime, confidence=regime_confidence)
    loop_mock._position_manager = MagicMock()
    loop_mock._position_manager.has_open.return_value = has_position
    loop_mock.strategy = SimpleNamespace(name="rsi_bollinger")
    loop_mock.session_id = "test-session-id"

    sched = SupervisorScheduler.__new__(SupervisorScheduler)
    sched._symbol = "BTC-EUR"
    sched._interval = 600
    sched._client = MagicMock()
    sched._updater = MagicMock()
    sched._updater.apply = AsyncMock()
    sched._score_engine = MagicMock()
    sched._score_engine.get_snapshot = AsyncMock(return_value=None)
    sched._score_engine.compute = AsyncMock(return_value=None)
    sched._loop = loop_mock
    sched._running = True
    sched._last_strategy_change = 0.0
    sched._last_param_update = 0.0
    sched._last_threshold_change = 0.0
    sched._current_strategy = "rsi_bollinger"
    sched._daily_ai_calls = 0
    sched._last_reset_day = ""

    sched._save_decision_to_memory = AsyncMock()
    sched._auto_adjust_threshold = AsyncMock()

    return sched


_ROUTER_STATE_PATCH = "app.scalping.router._execution_state"


# ── Test 1: blocca resume quando trending_down, alta confidence, nessuna posizione ──

@pytest.mark.asyncio
async def test_blocks_resume_when_trending_down_and_no_position():
    sched = _make_scheduler(regime="trending_down", regime_confidence=0.85, has_position=False)
    decision = _make_decision("resume_trading")
    sched._client.decide = AsyncMock(return_value=decision)

    fake_state = {"session": {"status": "paused"}, "trade_history": []}
    with patch(_ROUTER_STATE_PATCH, fake_state):
        result = await sched._tick()

    assert result is not None
    sched._updater.apply.assert_not_called()
    sched._save_decision_to_memory.assert_called_once()
    # Verify was_applied=False was passed
    call_args = sched._save_decision_to_memory.call_args
    assert call_args.kwargs.get("was_applied") is False


# ── Test 2: allow resume quando regime NON è bearish ──

@pytest.mark.asyncio
async def test_allows_resume_when_regime_not_bearish():
    sched = _make_scheduler(regime="ranging", regime_confidence=0.85, has_position=False)
    decision = _make_decision("resume_trading")
    sched._client.decide = AsyncMock(return_value=decision)

    fake_state = {"session": {"status": "paused"}, "trade_history": []}
    with patch(_ROUTER_STATE_PATCH, fake_state):
        result = await sched._tick()

    assert result is not None
    sched._updater.apply.assert_called_once_with(decision)


# ── Test 3: allow resume quando c'è una posizione aperta ──

@pytest.mark.asyncio
async def test_allows_resume_when_position_open():
    sched = _make_scheduler(regime="trending_down", regime_confidence=0.85, has_position=True)
    decision = _make_decision("resume_trading")
    sched._client.decide = AsyncMock(return_value=decision)

    fake_state = {"session": {"status": "paused"}, "trade_history": []}
    with patch(_ROUTER_STATE_PATCH, fake_state):
        result = await sched._tick()

    assert result is not None
    sched._updater.apply.assert_called_once_with(decision)


# ── Test 4: allow resume quando confidence bassa ──

@pytest.mark.asyncio
async def test_allows_resume_when_confidence_low():
    sched = _make_scheduler(regime="trending_down", regime_confidence=0.5, has_position=False)
    decision = _make_decision("resume_trading")
    sched._client.decide = AsyncMock(return_value=decision)

    fake_state = {"session": {"status": "paused"}, "trade_history": []}
    with patch(_ROUTER_STATE_PATCH, fake_state):
        result = await sched._tick()

    assert result is not None
    sched._updater.apply.assert_called_once_with(decision)


# ── Test 5: la guard non influenza altre azioni ──

@pytest.mark.asyncio
async def test_guard_does_not_affect_other_actions():
    sched = _make_scheduler(regime="trending_down", regime_confidence=0.85, has_position=False)
    decision = _make_decision("pause_trading")
    sched._client.decide = AsyncMock(return_value=decision)

    fake_state = {"session": {"status": "running"}, "trade_history": []}
    with patch(_ROUTER_STATE_PATCH, fake_state):
        result = await sched._tick()

    assert result is not None
    sched._updater.apply.assert_called_once_with(decision)


# ── Test 6: defense-in-depth _resume() no-op se già running ──

@pytest.mark.asyncio
async def test_resume_noop_when_already_running():
    from app.scalping.supervisor.parameter_updater import ParameterUpdater

    updater = ParameterUpdater()

    fake_state = {"session": {"status": "running"}}
    with patch(_ROUTER_STATE_PATCH, fake_state):
        await updater._resume()

    # If _resume was a no-op, the session status should still be "running" (not changed)
    assert fake_state["session"]["status"] == "running"
