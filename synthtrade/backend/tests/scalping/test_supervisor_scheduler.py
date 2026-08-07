"""Test per SupervisorScheduler e ParameterUpdater (TASK-806)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.scalping.supervisor.supervisor_scheduler import SupervisorScheduler
from app.scalping.supervisor.parameter_updater import ParameterUpdater
from app.scalping.supervisor.supervisor_client import SupervisorClient
from app.scalping.models.supervisor import SupervisorDecision


class TestParameterUpdater:
    def test_initial_state(self):
        updater = ParameterUpdater()
        assert updater._loop is None

    def test_set_execution_loop(self):
        updater = ParameterUpdater()
        mock_loop = MagicMock()
        updater.set_execution_loop(mock_loop)
        assert updater._loop is mock_loop

    @pytest.mark.asyncio
    async def test_apply_no_action_does_nothing(self):
        updater = ParameterUpdater()
        decision = SupervisorDecision(
            action="no_action",
            reason="test",
            confidence=0.5,
        )
        await updater.apply(decision)  # Should not raise

    @pytest.mark.asyncio
    async def test_apply_update_params(self):
        updater = ParameterUpdater()
        decision = SupervisorDecision(
            action="update_params",
            reason="testing",
            confidence=0.8,
            new_params={"atr_multiplier": 2.0},
        )
        await updater.apply(decision)

    @pytest.mark.asyncio
    async def test_apply_change_strategy(self):
        updater = ParameterUpdater()
        decision = SupervisorDecision(
            action="change_strategy",
            reason="regime shift",
            confidence=0.9,
            new_strategy="rsi_bollinger",
        )
        await updater.apply(decision)

    @pytest.mark.asyncio
    async def test_apply_pause_trading(self):
        updater = ParameterUpdater()
        decision = SupervisorDecision(
            action="pause_trading",
            reason="high volatility",
            confidence=0.95,
        )
        await updater.apply(decision)

    @pytest.mark.asyncio
    async def test_apply_resume_trading(self):
        updater = ParameterUpdater()
        decision = SupervisorDecision(
            action="resume_trading",
            reason="conditions improved",
            confidence=0.85,
        )
        await updater.apply(decision)


class TestSupervisorScheduler:
    def test_initial_state(self):
        mock_client = MagicMock()
        mock_updater = MagicMock()
        mock_engine = MagicMock()
        scheduler = SupervisorScheduler(
            symbol="BTCUSDT",
            interval_seconds=60,
            client=mock_client,
            updater=mock_updater,
            score_engine=mock_engine,
        )
        assert scheduler._symbol == "BTCUSDT"
        assert scheduler._interval == 60
        assert scheduler._running is False

    def test_set_execution_loop(self):
        mock_client = MagicMock()
        mock_updater = MagicMock()
        mock_engine = MagicMock()
        scheduler = SupervisorScheduler(
            client=mock_client,
            updater=mock_updater,
            score_engine=mock_engine,
        )
        mock_loop = MagicMock()
        scheduler.set_execution_loop(mock_loop)
        assert scheduler._loop is mock_loop

    @pytest.mark.asyncio
    async def test_start_creates_task(self):
        mock_client = MagicMock()
        mock_updater = MagicMock()
        mock_engine = MagicMock()
        scheduler = SupervisorScheduler(
            symbol="ETHUSDT",
            client=mock_client,
            updater=mock_updater,
            score_engine=mock_engine,
        )
        scheduler.start()
        assert scheduler._running is True
        assert scheduler._task is not None
        scheduler.stop()  # Clean up

    @pytest.mark.asyncio
    async def test_stop_cancels_task(self):
        mock_client = MagicMock()
        mock_updater = MagicMock()
        mock_engine = MagicMock()
        scheduler = SupervisorScheduler(
            symbol="ETHUSDT",
            client=mock_client,
            updater=mock_updater,
            score_engine=mock_engine,
        )
        scheduler.start()
        scheduler.stop()
        assert scheduler._running is False

    @pytest.mark.asyncio
    async def test_tick_calls_components(self):
        from app.scalping.models.intelligence import MarketIntelSnapshot, SignalScore

        mock_client = MagicMock()
        mock_client.decide = AsyncMock(return_value=SupervisorDecision(
            action="no_action",
            reason="test",
            confidence=0.5,
        ))

        mock_updater = MagicMock()
        mock_updater.apply = AsyncMock()

        mock_engine = MagicMock()
        mock_engine.get_snapshot = AsyncMock(return_value=MarketIntelSnapshot(
            symbol="BTCUSDT",
            signal_score=SignalScore(total=0, bias="neutral", tradeable=False),
        ))
        mock_engine.compute = AsyncMock(return_value=SignalScore(total=0, bias="neutral", tradeable=False))

        scheduler = SupervisorScheduler(
            symbol="BTCUSDT",
            client=mock_client,
            updater=mock_updater,
            score_engine=mock_engine,
        )
        scheduler._running = True

        # Run single tick
        await scheduler._tick()

        mock_client.decide.assert_called_once()
        mock_updater.apply.assert_called_once()

    @pytest.mark.asyncio
    async def test_tick_resume_with_new_strategy_applies_change(self, mock_supabase):
        """resume_trading con new_strategy valida per il regime → applica anche il cambio strategia."""
        from app.scalping.models.intelligence import MarketIntelSnapshot, SignalScore

        mock_client = MagicMock()
        mock_client.decide = AsyncMock(return_value=SupervisorDecision(
            action="resume_trading",
            reason="regime ok, riprendere con strategia diversa",
            confidence=0.75,
            new_strategy="rsi_bollinger",
        ))

        mock_updater = MagicMock()
        mock_updater.apply = AsyncMock()

        mock_engine = MagicMock()
        mock_engine.get_snapshot = AsyncMock(return_value=MarketIntelSnapshot(
            symbol="BTCUSDT",
            signal_score=SignalScore(total=0, bias="neutral", tradeable=False),
        ))
        mock_engine.compute = AsyncMock(return_value=SignalScore(total=0, bias="neutral", tradeable=False))

        mock_loop = MagicMock()
        mock_loop.regime.regime = "ranging"
        mock_loop.regime.confidence = 0.8
        mock_loop.strategy.name = "rsi_bollinger"
        mock_loop.session_id = "s1"

        scheduler = SupervisorScheduler(
            symbol="BTCUSDT",
            client=mock_client,
            updater=mock_updater,
            score_engine=mock_engine,
        )
        scheduler._running = True
        scheduler.set_execution_loop(mock_loop)

        await scheduler._tick()

        # apply chiamato 2 volte: prima il resume, poi il change_strategy
        assert mock_updater.apply.call_count == 2
        calls = mock_updater.apply.call_args_list
        assert calls[0].args[0].action == "resume_trading"
        assert calls[1].args[0].action == "change_strategy"
        assert calls[1].args[0].new_strategy == "rsi_bollinger"
        assert scheduler._current_strategy == "rsi_bollinger"

    @pytest.mark.asyncio
    async def test_tick_resume_with_strategy_not_allowed_keeps_strategy(self, mock_supabase):
        """resume_trading con strategia NON consentita nel regime → resume sì, cambio strategia no."""
        from app.scalping.models.intelligence import MarketIntelSnapshot, SignalScore

        mock_client = MagicMock()
        mock_client.decide = AsyncMock(return_value=SupervisorDecision(
            action="resume_trading",
            reason="resume senza cambio valido",
            confidence=0.75,
            new_strategy="momentum_base",
        ))

        mock_updater = MagicMock()
        mock_updater.apply = AsyncMock()

        mock_engine = MagicMock()
        mock_engine.get_snapshot = AsyncMock(return_value=MarketIntelSnapshot(
            symbol="BTCUSDT",
            signal_score=SignalScore(total=0, bias="neutral", tradeable=False),
        ))
        mock_engine.compute = AsyncMock(return_value=SignalScore(total=0, bias="neutral", tradeable=False))

        mock_loop = MagicMock()
        mock_loop.regime.regime = "ranging"
        mock_loop.regime.confidence = 0.8
        mock_loop.strategy.name = "rsi_bollinger"
        mock_loop.session_id = "s1"

        scheduler = SupervisorScheduler(
            symbol="BTCUSDT",
            client=mock_client,
            updater=mock_updater,
            score_engine=mock_engine,
        )
        scheduler._running = True
        scheduler.set_execution_loop(mock_loop)

        await scheduler._tick()

        # apply chiamato 1 volta: solo resume, strategia invariata
        assert mock_updater.apply.call_count == 1
        assert mock_updater.apply.call_args.args[0].action == "resume_trading"
        assert scheduler._current_strategy == "rsi_bollinger"
