import pytest
import asyncio
import time
from app.core.strategy_generator import generate_for_request
from app.execution.schemas import StrategyRequest
from unittest.mock import MagicMock, AsyncMock

@pytest.mark.asyncio
async def test_generate_for_request_performance():
    # Setup mock data per simulare una generazione massiva
    req = StrategyRequest(budget_eur=100.0, duration_days=30, asset_class="crypto", risk_level="medium")
    
    mock_md = MagicMock()
    # Simula un ritorno veloce
    mock_md.get_ohlcv.return_value = MagicMock()
    mock_md.get_ohlcv.return_value.empty = False
    
    start_time = time.time()
    await generate_for_request(req, mock_md)
    end_time = time.time()
    
    duration = end_time - start_time
    # Un tempo ragionevole per generazione massiva deve essere < 0.5s
    assert duration < 0.5
