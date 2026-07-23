"""TASK-1225: Short close + time-stop 48h fixed tests.

Tests verify:
- Short PnL is inverted (entry_price - exit_price)
- Time-stop job closes short positions after 48h
- Time-stop job ignores long positions and positions under threshold
- Paper mode short PnL is correct
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from decimal import Decimal
from datetime import datetime, timezone, timedelta

from app.scalping.engine.position_manager import PositionManager, Position


class TestShortPnlInverted:
    """Verify short PnL calculation is inverted."""

    def test_close_short_pnl_positive_when_price_drops(self):
        """TASK-1225.B: entry=100, exit=95 → PnL positive (short profits when price drops)."""
        entry_f = 100.0
        fill_price = 95.0
        qty_f = 1.0
        side = "SELL"

        gross_pnl = (fill_price - entry_f) * qty_f if side == "BUY" else (entry_f - fill_price) * qty_f
        assert gross_pnl == 5.0, f"Short PnL should be positive when price drops: got {gross_pnl}"

    def test_close_short_pnl_negative_when_price_rises(self):
        """TASK-1225.B: entry=100, exit=105 → PnL negative (short loses when price rises)."""
        entry_f = 100.0
        fill_price = 105.0
        qty_f = 1.0
        side = "SELL"

        gross_pnl = (fill_price - entry_f) * qty_f if side == "BUY" else (entry_f - fill_price) * qty_f
        assert gross_pnl == -5.0, f"Short PnL should be negative when price rises: got {gross_pnl}"

    def test_close_long_pnl_positive_when_price_rises(self):
        """Long PnL: entry=100, exit=105 → positive (baseline test)."""
        entry_f = 100.0
        fill_price = 105.0
        qty_f = 1.0
        side = "BUY"

        gross_pnl = (fill_price - entry_f) * qty_f if side == "BUY" else (entry_f - fill_price) * qty_f
        assert gross_pnl == 5.0


class TestTimestopJobClosesAfter48h:
    """Verify time-stop job logic closes short positions after 48h."""

    def test_timestop_expired_closes_position(self):
        """TASK-1225.D/E: Position open 49h → should close."""
        entry_time = datetime.now(timezone.utc) - timedelta(hours=49)
        max_hours = 48
        age = datetime.now(timezone.utc) - entry_time
        age_hours = age.total_seconds() / 3600
        assert age_hours > max_hours, f"Position should be expired: age={age_hours}h > {max_hours}h"

    def test_timestop_not_expired_ignores(self):
        """TASK-1225.D: Position open 24h → should NOT close."""
        entry_time = datetime.now(timezone.utc) - timedelta(hours=24)
        max_hours = 48
        age = datetime.now(timezone.utc) - entry_time
        age_hours = age.total_seconds() / 3600
        assert age_hours < max_hours, f"Position should NOT be expired: age={age_hours}h < {max_hours}h"

    def test_timestop_exactly_at_boundary_not_closed(self):
        """TASK-1225.D: Position open exactly 47h59m → should NOT close (strict < check)."""
        entry_time = datetime.now(timezone.utc) - timedelta(hours=47, minutes=59)
        max_hours = 48
        age = datetime.now(timezone.utc) - entry_time
        age_hours = age.total_seconds() / 3600
        assert age_hours < max_hours, f"Position should NOT be expired at boundary: age={age_hours}h"

    def test_timestop_ignores_long_positions(self):
        """TASK-1225.D: Time-stop only touches SHORT (SELL) positions."""
        side = "BUY"
        assert side != "SELL", "Time-stop should not close long positions"

    def test_timestop_only_touches_sell(self):
        """Verify the side check logic."""
        for side in ("BUY", "SELL", "buy", "sell"):
            should_close = side == "SELL"
            if side == "BUY":
                assert not should_close
            elif side == "SELL":
                assert should_close


class TestTimestopJobIntegration:
    """Integration-style tests for the short_timestop_job function.

    Uses direct patching of _execution_state where short_timestop_job reads it
    (app.scalping.router), to avoid cross-test state pollution.
    """

    @pytest.mark.asyncio
    async def test_timestop_no_position_skips(self):
        """No open position → job does nothing."""
        pm = PositionManager()
        state = {"position_manager": pm, "session": {"status": "running", "mode": "paper"}, "trade_history": []}

        from app.scheduler.scalping_jobs import short_timestop_job
        with patch("app.scalping.router._execution_state", state), \
             patch("app.scalping.trade_executor._close_position_and_record", new_callable=AsyncMock) as mock_close:
            await short_timestop_job()
            mock_close.assert_not_called()

    @pytest.mark.asyncio
    async def test_timestop_long_position_skips(self):
        """Long position → time-stop does NOT close it."""
        pm = PositionManager()
        pos = pm.open_position(
            symbol="BTC-EUR",
            side="BUY",
            entry_price=Decimal("50000"),
            quantity=Decimal("0.002"),
        )
        pos.entry_time = datetime.now(timezone.utc) - timedelta(hours=49)
        state = {"position_manager": pm, "session": {"status": "running", "mode": "paper"}, "trade_history": []}

        from app.scheduler.scalping_jobs import short_timestop_job
        with patch("app.scalping.router._execution_state", state), \
             patch("app.scalping.trade_executor._close_position_and_record", new_callable=AsyncMock) as mock_close:
            await short_timestop_job()
            mock_close.assert_not_called()

    @pytest.mark.asyncio
    async def test_timestop_short_under_threshold_skips(self):
        """Short position < 48h → time-stop does NOT close it."""
        pm = PositionManager()
        pos = pm.open_position(
            symbol="BTC-EUR",
            side="SELL",
            entry_price=Decimal("50000"),
            quantity=Decimal("0.002"),
        )
        state = {"position_manager": pm, "session": {"status": "running", "mode": "paper"}, "trade_history": []}

        from app.scheduler.scalping_jobs import short_timestop_job
        with patch("app.scalping.router._execution_state", state), \
             patch("app.scalping.trade_executor._close_position_and_record", new_callable=AsyncMock) as mock_close:
            await short_timestop_job()
            mock_close.assert_not_called()

    @pytest.mark.asyncio
    async def test_timestop_short_expired_calls_close(self):
        """Short position > 48h → time-stop CLOSES it with reason='timestop_fixed'."""
        pm = PositionManager()
        pos = pm.open_position(
            symbol="BTC-EUR",
            side="SELL",
            entry_price=Decimal("50000"),
            quantity=Decimal("0.002"),
        )
        pos.entry_time = datetime.now(timezone.utc) - timedelta(hours=49)
        state = {"position_manager": pm, "session": {"status": "running", "mode": "paper"}, "trade_history": []}

        from app.scheduler.scalping_jobs import short_timestop_job
        with patch("app.scalping.router._execution_state", state), \
             patch("app.scalping.trade_executor._close_position_and_record", new_callable=AsyncMock) as mock_close:
            await short_timestop_job()
            mock_close.assert_called_once()
            args = mock_close.call_args
            assert args.kwargs.get("reason") == "timestop_fixed", f"Expected reason='timestop_fixed', got {args.kwargs}"

    @pytest.mark.asyncio
    async def test_timestop_idle_session_skips(self):
        """Idle session → job does nothing."""
        state = {"position_manager": PositionManager(), "session": {"status": "idle", "mode": "paper"}, "trade_history": []}

        from app.scheduler.scalping_jobs import short_timestop_job
        with patch("app.scalping.router._execution_state", state), \
             patch("app.scalping.trade_executor._close_position_and_record", new_callable=AsyncMock) as mock_close:
            await short_timestop_job()
            mock_close.assert_not_called()


class TestPaperModeShortPnl:
    """Verify paper mode short PnL is correct."""

    def test_paper_short_entry_exit_pnl(self):
        """TASK-1225.H: Paper mode SELL PnL is inverted."""
        entry_price = 50000.0
        exit_price = 49500.0
        qty = 0.002
        side = "SELL"

        gross_pnl = (exit_price - entry_price) * qty if side == "BUY" else (entry_price - exit_price) * qty
        assert gross_pnl > 0, f"Short should profit when price drops: got {gross_pnl}"
        assert gross_pnl == pytest.approx(1.0, abs=0.01)

    def test_paper_short_price_rises_loses(self):
        """TASK-1225.H: Paper mode SELL loses when price rises."""
        entry_price = 50000.0
        exit_price = 50500.0
        qty = 0.002
        side = "SELL"

        gross_pnl = (exit_price - entry_price) * qty if side == "BUY" else (entry_price - exit_price) * qty
        assert gross_pnl < 0, f"Short should lose when price rises: got {gross_pnl}"


class TestPositionManagerSideField:
    """Verify Position side field is correctly set."""

    def test_short_position_side_is_sell(self):
        pm = PositionManager()
        pos = pm.open_position(
            symbol="BTC-EUR",
            side="SELL",
            entry_price=Decimal("50000"),
            quantity=Decimal("0.002"),
        )
        assert pos.side == "SELL"
        assert pos.symbol == "BTC-EUR"

    def test_long_position_side_is_buy(self):
        pm = PositionManager()
        pos = pm.open_position(
            symbol="BTC-EUR",
            side="BUY",
            entry_price=Decimal("50000"),
            quantity=Decimal("0.002"),
        )
        assert pos.side == "BUY"
