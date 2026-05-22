"""🔴 RED + 🟢 GREEN: Test per controlli intraday in risk_manager.py (TASK-801)."""
import pytest
from app.execution.risk_manager import RiskManager, RiskConfig
from app.execution.schemas import PositionSnapshot
from datetime import datetime, timezone, timedelta


@pytest.fixture
def rm():
    return RiskManager(RiskConfig(
        max_concurrent_positions=2,
        max_exposure_per_symbol_pct=0.10,
        max_drawdown_pct=15.0,
        default_position_size_pct=0.05,
        default_stop_loss_pct=0.02,
        default_take_profit_pct=0.04,
    ))


def make_position(
    strategy_id="s1", symbol="BTC/USDT", direction="BUY",
    entry_price=60000.0, quantity=0.01, unrealized_pnl=0.0,
):
    return PositionSnapshot(
        trade_id=f"t_{strategy_id}",
        strategy_id=strategy_id,
        symbol=symbol,
        direction=direction,
        entry_price=entry_price,
        quantity=quantity,
        stop_loss=entry_price * 0.98,
        take_profit=entry_price * 1.04,
        opened_at=datetime.utcnow(),
        unrealized_pnl=unrealized_pnl,
    )


class TestCheckMaxDailyLoss:
    """Test per check_max_daily_loss."""

    def test_daily_loss_below_threshold(self, rm):
        """Con daily loss sotto la soglia, deve essere approvato."""
        result = rm.check_max_daily_loss(
            daily_pnl_pct=-2.0,
            max_daily_loss_pct=3.0,
        )
        assert result.approved is True
        assert result.reason == "OK"

    def test_daily_loss_at_threshold(self, rm):
        """Con daily loss esattamente al limite, deve essere approvato."""
        result = rm.check_max_daily_loss(
            daily_pnl_pct=-3.0,
            max_daily_loss_pct=3.0,
        )
        assert result.approved is True

    def test_daily_loss_exceeds_threshold(self, rm):
        """Con daily loss oltre la soglia, deve essere rifiutato."""
        result = rm.check_max_daily_loss(
            daily_pnl_pct=-5.0,
            max_daily_loss_pct=3.0,
        )
        assert result.approved is False
        assert "daily loss" in result.reason.lower() or "perdita" in result.reason.lower()

    def test_daily_loss_uses_default_threshold(self, rm):
        """Deve usare il default da config se non specificato."""
        result = rm.check_max_daily_loss(daily_pnl_pct=-20.0)
        assert result.approved is False

    def test_daily_loss_positive_not_blocked(self, rm):
        """Con daily loss negativo ma entro limiti, approvato."""
        result = rm.check_max_daily_loss(daily_pnl_pct=0.0)
        assert result.approved is True

    def test_daily_loss_returns_rest_of_fields(self, rm):
        """RiskCheckResult deve avere approved e reason popolati."""
        result = rm.check_max_daily_loss(daily_pnl_pct=-1.0)
        assert hasattr(result, "approved")
        assert hasattr(result, "reason")


class TestCheckMaxConsecutiveLosses:
    """Test per check_max_consecutive_losses."""

    def test_below_max_consecutive(self, rm):
        """Con perdite consecutive sotto la soglia, approvato."""
        result = rm.check_max_consecutive_losses(
            consecutive_losses=2,
            max_consecutive_losses=5,
        )
        assert result.approved is True
        assert result.reason == "OK"

    def test_at_max_consecutive(self, rm):
        """Con perdite consecutive al limite, approvato."""
        result = rm.check_max_consecutive_losses(
            consecutive_losses=5,
            max_consecutive_losses=5,
        )
        assert result.approved is True

    def test_exceeds_max_consecutive(self, rm):
        """Con perdite consecutive oltre il limite, rifiutato."""
        result = rm.check_max_consecutive_losses(
            consecutive_losses=6,
            max_consecutive_losses=5,
        )
        assert result.approved is False
        assert "perdite consecutive" in result.reason.lower() or "consecutive" in result.reason.lower()

    def test_uses_default_threshold(self, rm):
        """Deve usare il default da config se non specificato."""
        result = rm.check_max_consecutive_losses(consecutive_losses=20)
        assert result.approved is False

    def test_zero_consecutive_losses(self, rm):
        """Zero perdite consecutive deve essere sempre approvato."""
        result = rm.check_max_consecutive_losses(consecutive_losses=0)
        assert result.approved is True

    def test_one_consecutive_loss(self, rm):
        """Una singola perdita non deve bloccare."""
        result = rm.check_max_consecutive_losses(consecutive_losses=1)
        assert result.approved is True


class TestValidateSignalIntraday:
    """Test per validate_signal con i nuovi controlli intraday."""

    def test_validate_signal_with_intraday_checks_ok(self, rm):
        """Tutti i controlli passano."""
        from app.execution.schemas import Signal
        signal = Signal(
            strategy_id="s1", symbol="BTC/USDT",
            direction="BUY", strength=0.8, price=60000.0,
        )
        result = rm.validate_signal(
            signal=signal, balance=10000.0, open_positions=[],
            current_drawdown_pct=5.0,
            daily_pnl_pct=-1.0,
            consecutive_losses=1,
        )
        assert result.approved is True
        assert result.position_size > 0
        assert result.stop_loss_price > 0
        assert result.take_profit_price > 0

    def test_validate_signal_blocked_by_daily_loss(self, rm):
        """Bloccato se daily loss supera la soglia."""
        from app.execution.schemas import Signal
        signal = Signal(
            strategy_id="s1", symbol="BTC/USDT",
            direction="BUY", strength=0.8, price=60000.0,
        )
        result = rm.validate_signal(
            signal=signal, balance=10000.0, open_positions=[],
            current_drawdown_pct=5.0,
            daily_pnl_pct=-5.0,
            max_daily_loss_pct=3.0,
            consecutive_losses=0,
        )
        assert result.approved is False
        assert "daily loss" in result.reason.lower() or "perdita" in result.reason.lower()

    def test_validate_signal_blocked_by_consecutive_losses(self, rm):
        """Bloccato se consecutive losses supera la soglia."""
        from app.execution.schemas import Signal
        signal = Signal(
            strategy_id="s1", symbol="BTC/USDT",
            direction="BUY", strength=0.8, price=60000.0,
        )
        result = rm.validate_signal(
            signal=signal, balance=10000.0, open_positions=[],
            current_drawdown_pct=5.0,
            daily_pnl_pct=0.0,
            consecutive_losses=10,
        )
        assert result.approved is False
        assert "perdite consecutive" in result.reason.lower() or "consecutive" in result.reason.lower()

    def test_validate_signal_daily_loss_default(self, rm):
        """Deve funzionare anche senza parametri intraday (backward compatibile)."""
        from app.execution.schemas import Signal
        signal = Signal(
            strategy_id="s1", symbol="BTC/USDT",
            direction="BUY", strength=0.8, price=60000.0,
        )
        result = rm.validate_signal(
            signal=signal, balance=10000.0, open_positions=[],
            current_drawdown_pct=5.0,
        )
        # Senza parametri intraday, deve passare se drawdown ok
        assert result.approved is True