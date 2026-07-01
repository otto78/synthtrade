"""Unit tests for Historical Context Builder."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from app.scalping.supervisor.historical_context import (
    build_historical_context,
    clear_historical_cache,
    _get_empty_context
)


@pytest.mark.asyncio
async def test_build_historical_context_empty_data():
    """Test with empty data from database."""
    with patch('app.scalping.supervisor.historical_context.get_supabase') as mock_supabase:
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.execute.return_value.data = []
        mock_supabase.return_value = mock_client
        
        result = await build_historical_context()
        
        assert result["total_historical_trades"] == 0
        assert result["historical_performance"] == {}
        assert result["best_combination"] is None
        assert result["worst_combination"] is None


@pytest.mark.asyncio
async def test_build_historical_context_with_data():
    """Test with realistic data from database."""
    mock_data = [
        {
            "strategy_type": "rsi_bollinger",
            "regime": "ranging",
            "n_trades": 30,
            "win_rate_pct": 43.3,
            "avg_pnl": -0.12
        },
        {
            "strategy_type": "ema_cross",
            "regime": "trending_down",
            "n_trades": 12,
            "win_rate_pct": 25.0,
            "avg_pnl": -0.45
        },
        {
            "strategy_type": "momentum_base",
            "regime": "unknown",
            "n_trades": 3,  # Insufficient data
            "win_rate_pct": 66.7,
            "avg_pnl": 0.15
        }
    ]
    
    with patch('app.scalping.supervisor.historical_context.get_supabase') as mock_supabase:
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.execute.return_value.data = mock_data
        mock_supabase.return_value = mock_client
        
        result = await build_historical_context()
        
        assert result["total_historical_trades"] == 42  # 30 + 12 (insufficient skipped)
        assert "rsi_bollinger/ranging" in result["historical_performance"]
        assert "ema_cross/trending_down" in result["historical_performance"]
        assert "momentum_base/unknown" in result["historical_performance"]
        
        # Check insufficient data flag
        assert result["historical_performance"]["momentum_base/unknown"]["insufficient_data"] is True
        
        # Check best/worst tracking
        assert result["best_combination"] == "rsi_bollinger/ranging"  # 43.3% win rate
        assert result["worst_combination"] == "ema_cross/trending_down"  # 25.0% win rate


@pytest.mark.asyncio
async def test_build_historical_context_cache():
    """Test that cache works correctly."""
    mock_data = [
        {
            "strategy_type": "rsi_bollinger",
            "regime": "ranging",
            "n_trades": 10,
            "win_rate_pct": 50.0,
            "avg_pnl": 0.0
        }
    ]
    
    with patch('app.scalping.supervisor.historical_context.get_supabase') as mock_supabase:
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.execute.return_value.data = mock_data
        mock_supabase.return_value = mock_client
        
        # First call - should query DB
        result1 = await build_historical_context()
        assert mock_client.table.called
        
        # Second call within TTL - should use cache
        mock_client.reset_mock()
        result2 = await build_historical_context()
        assert not mock_client.table.called  # Cache hit
        
        # Results should be identical
        assert result1 == result2


@pytest.mark.asyncio
async def test_clear_historical_cache():
    """Test cache clearing."""
    mock_data = [
        {
            "strategy_type": "rsi_bollinger",
            "regime": "ranging",
            "n_trades": 10,
            "win_rate_pct": 50.0,
            "avg_pnl": 0.0
        }
    ]
    
    with patch('app.scalping.supervisor.historical_context.get_supabase') as mock_supabase:
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.execute.return_value.data = mock_data
        mock_supabase.return_value = mock_client
        
        # First call
        await build_historical_context()
        assert mock_client.table.call_count == 1
        
        # Clear cache
        clear_historical_cache()
        
        # Second call - should query DB again
        await build_historical_context()
        assert mock_client.table.call_count == 2


def test_get_empty_context():
    """Test empty context structure."""
    result = _get_empty_context()
    
    assert result["total_historical_trades"] == 0
    assert result["historical_performance"] == {}
    assert result["best_combination"] is None
    assert result["worst_combination"] is None
    assert "data_freshness" in result