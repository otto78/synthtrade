import pytest
from datetime import datetime, UTC
from app.execution.signal_resolver import DefaultSignalResolver
from app.execution.schemas import Signal, PositionSnapshot


def make_signal(strategy_id="s1", symbol="BTC/USDT", strength=0.8, direction="BUY"):
    return Signal(strategy_id=strategy_id, symbol=symbol, direction=direction,
                  strength=strength, price=60000.0, timestamp=datetime.now(UTC))


def make_position(strategy_id="s1", symbol="BTC/USDT"):
    return PositionSnapshot(
        trade_id="t1", strategy_id=strategy_id, symbol=symbol,
        direction="BUY", entry_price=58000.0, quantity=0.01,
        stop_loss=56840.0, take_profit=60320.0, opened_at=datetime.now(UTC)
    )


@pytest.fixture
def resolver():
    return DefaultSignalResolver(strength_threshold=0.6)


def test_filters_below_threshold(resolver):
    signals = [make_signal(strength=0.5), make_signal(strategy_id="s2", strength=0.9)]
    result = resolver.resolve(signals, open_positions=[])
    assert len(result) == 1
    assert result[0].strategy_id == "s2"


def test_keeps_strongest_per_symbol(resolver):
    signals = [
        make_signal(strategy_id="s1", symbol="BTC/USDT", strength=0.7),
        make_signal(strategy_id="s2", symbol="BTC/USDT", strength=0.9),
    ]
    result = resolver.resolve(signals, open_positions=[])
    assert len(result) == 1
    assert result[0].strategy_id == "s2"


def test_filters_symbol_already_in_position(resolver):
    signals = [make_signal(strategy_id="s1", symbol="BTC/USDT", strength=0.9)]
    positions = [make_position(strategy_id="s2", symbol="BTC/USDT")]
    result = resolver.resolve(signals, open_positions=positions)
    assert result == []


def test_returns_empty_if_no_signals_pass(resolver):
    signals = [make_signal(strength=0.3)]
    result = resolver.resolve(signals, open_positions=[])
    assert result == []


def test_multiple_symbols_resolved(resolver):
    signals = [
        make_signal(strategy_id="s1", symbol="BTC/USDT", strength=0.8),
        make_signal(strategy_id="s2", symbol="ETH/USDT", strength=0.7),
    ]
    result = resolver.resolve(signals, open_positions=[])
    assert len(result) == 2
