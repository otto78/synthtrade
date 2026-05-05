import pytest
from app.execution.risk_manager import RiskManager, RiskConfig
from app.execution.schemas import Signal, PositionSnapshot
from datetime import datetime


def make_signal(symbol="BTC/USDT", strength=0.8, price=60000.0, direction="BUY"):
    return Signal(strategy_id="s1", symbol=symbol, direction=direction,
                  strength=strength, price=price)


def make_position(symbol="BTC/USDT", strategy_id="s1"):
    return PositionSnapshot(
        trade_id="t1", strategy_id=strategy_id, symbol=symbol,
        direction="BUY", entry_price=58000.0, quantity=0.1,
        stop_loss=56840.0, take_profit=60320.0, opened_at=datetime.utcnow()
    )


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


def test_calculate_position_size(rm):
    size = rm.calculate_position_size(balance=10000.0, price=60000.0)
    # 5% di 10000 = 500 EUR → 500/60000 ≈ 0.00833
    assert abs(size - 500 / 60000) < 1e-6


def test_position_size_capped_by_exposure(rm):
    # max_exposure 10% di 10000 = 1000 EUR → 1000/60000
    size = rm.calculate_position_size(balance=10000.0, price=60000.0,
                                      existing_exposure_eur=0.0)
    assert size * 60000 <= 10000 * 0.10


def test_check_max_positions_approved(rm):
    result = rm.check_max_positions(open_positions=[make_position()])
    assert result.approved is True


def test_check_max_positions_rejected(rm):
    positions = [make_position(strategy_id="s1"), make_position(strategy_id="s2")]
    result = rm.check_max_positions(open_positions=positions)
    assert result.approved is False
    assert "limite" in result.reason.lower()


def test_check_drawdown_approved(rm):
    result = rm.check_drawdown(current_drawdown_pct=10.0)
    assert result.approved is True


def test_check_drawdown_rejected(rm):
    result = rm.check_drawdown(current_drawdown_pct=20.0)
    assert result.approved is False
    assert "drawdown" in result.reason.lower()


def test_calculate_stop_loss_long(rm):
    sl = rm.calculate_stop_loss_price(entry_price=60000.0, direction="BUY")
    assert abs(sl - 60000.0 * (1 - 0.02)) < 0.01


def test_calculate_stop_loss_short(rm):
    sl = rm.calculate_stop_loss_price(entry_price=60000.0, direction="SELL")
    assert abs(sl - 60000.0 * (1 + 0.02)) < 0.01


def test_calculate_take_profit_long(rm):
    tp = rm.calculate_take_profit_price(entry_price=60000.0, direction="BUY")
    assert abs(tp - 60000.0 * (1 + 0.04)) < 0.01


def test_calculate_take_profit_short(rm):
    tp = rm.calculate_take_profit_price(entry_price=60000.0, direction="SELL")
    assert abs(tp - 60000.0 * (1 - 0.04)) < 0.01


def test_validate_signal_approved(rm):
    signal = make_signal()
    result = rm.validate_signal(
        signal=signal, balance=10000.0, open_positions=[],
        current_drawdown_pct=5.0
    )
    assert result.approved is True
    assert result.position_size > 0
    assert result.stop_loss_price > 0
    assert result.take_profit_price > 0


def test_validate_signal_rejected_drawdown(rm):
    signal = make_signal()
    result = rm.validate_signal(
        signal=signal, balance=10000.0, open_positions=[],
        current_drawdown_pct=20.0
    )
    assert result.approved is False
    assert "drawdown" in result.reason.lower()


def test_validate_signal_rejected_max_positions(rm):
    signal = make_signal()
    positions = [make_position(strategy_id="s1"), make_position(strategy_id="s2")]
    result = rm.validate_signal(
        signal=signal, balance=10000.0, open_positions=positions,
        current_drawdown_pct=5.0
    )
    assert result.approved is False
