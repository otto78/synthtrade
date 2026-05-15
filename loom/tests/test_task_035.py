"""
Tests for TASK-035: StrategyRepository Refactor
"""
import pytest
from unittest.mock import MagicMock
from app.db.repositories.strategy_repository import StrategyRepository
from app.models.strategy import Strategy

@pytest.fixture
def mock_db():
    return MagicMock()

@pytest.fixture
def repo(mock_db):
    return StrategyRepository(mock_db)

def test_get_strategy_by_id(repo, mock_db):
    # Setup mock
    mock_data = {
        "id": "test-id",
        "title": "Test Strategy",
        "status": "ACTIVE",
        "pair": "BTC/USDT",
        "timeframe": "1h",
        "template": "RSI_Default",
        "params": {"rsi_period": 14}
    }
    mock_db.table().select().eq().single().execute.return_value.data = mock_data
    
    # Execute
    strategy = repo.get_by_id("test-id")
    
    # Assert
    assert isinstance(strategy, Strategy)
    assert strategy.id == "test-id"
    assert strategy.status == "ACTIVE"

def test_list_active_strategies(repo, mock_db):
    # Setup mock
    mock_data = [
        {"id": "s1", "status": "ACTIVE", "pair": "BTC/USDT", "timeframe": "1h", "template": "T1", "params": {}},
        {"id": "s2", "status": "ACTIVE", "pair": "ETH/USDT", "timeframe": "4h", "template": "T2", "params": {}},
    ]
    mock_db.table().select().eq().execute.return_value.data = mock_data
    
    # Execute
    strategies = repo.get_active()
    
    # Assert
    assert len(strategies) == 2
    assert all(isinstance(s, Strategy) for s in strategies)
    assert strategies[0].id == "s1"
    assert strategies[1].id == "s2"

def test_update_status(repo, mock_db):
    # Execute
    repo.update_status("test-id", "EXPIRED")
    
    # Assert
    mock_db.table.assert_called_with("strategies")
    mock_db.table().update.assert_called_with({"status": "EXPIRED"})
    mock_db.table().update().eq.assert_called_with("id", "test-id")

from app.db.repositories.trade_repository import TradeRepository
from app.models.trade import Trade

@pytest.fixture
def trade_repo(mock_db):
    return TradeRepository(mock_db)

def test_get_open_trades_by_strategy(trade_repo, mock_db):
    # Setup mock
    mock_data = [
        {"id": "t1", "strategy_id": "s1", "pair": "BTC/USDT", "action": "BUY", "status": "OPEN", "price": 50000.0, "quantity": 0.01},
    ]
    mock_db.table().select().eq().eq().execute.return_value.data = mock_data
    
    # Execute
    trades = trade_repo.get_open_by_strategy("s1")
    
    # Assert
    assert len(trades) == 1
    assert isinstance(trades[0], Trade)
    assert trades[0].id == "t1"

def test_insert_trade(trade_repo, mock_db):
    # Setup mock
    mock_data = [{"id": "new-t", "strategy_id": "s1", "pair": "BTC/USDT", "action": "BUY", "status": "OPEN", "price": 50000.0, "quantity": 0.01}]
    mock_db.table().insert().execute.return_value.data = mock_data
    
    # Execute
    trade = trade_repo.insert({"strategy_id": "s1", "pair": "BTC/USDT", "action": "BUY", "status": "OPEN", "price": 50000.0, "quantity": 0.01})
    
    # Assert
    assert isinstance(trade, Trade)
    assert trade.id == "new-t"
