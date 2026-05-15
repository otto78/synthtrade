"""
Tests for TASK-038: MarketData Refactor (OhlcvRepository)
"""
import pytest
import pandas as pd
from unittest.mock import MagicMock
from app.db.repositories.ohlcv_repository import OhlcvRepository

@pytest.fixture
def mock_db():
    return MagicMock()

@pytest.fixture
def repo(mock_db):
    return OhlcvRepository(mock_db)

def test_get_cached_ohlcv(repo, mock_db):
    # Setup mock
    mock_data = [
        {"ts": "2026-05-15T00:00:00", "open": 60000, "high": 61000, "low": 59000, "close": 60500, "volume": 10},
    ]
    mock_db.table().select().eq().eq().order().execute.return_value.data = mock_data
    
    # Execute
    df = repo.get_cached("BTC/USDT", "1h")
    
    # Assert
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert df.iloc[0]["close"] == 60500
    mock_db.table.assert_called_with("ohlcv_cache")

def test_save_ohlcv(repo, mock_db):
    # Setup mock
    df = pd.DataFrame([{"ts": "2026-05-15T00:00:00", "open": 60000, "high": 61000, "low": 59000, "close": 60500, "volume": 10}])
    
    # Execute
    repo.save("BTC/USDT", "1h", df)
    
    # Assert
    mock_db.table.assert_called_with("ohlcv_cache")
    mock_db.table().upsert.assert_called_once()
