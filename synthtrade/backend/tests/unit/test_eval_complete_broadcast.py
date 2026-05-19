import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.core.run_pipeline import run_pipeline

class FakeEvalResult:
    def __init__(self, strategy_id, verdict, score):
        self.strategy_id = strategy_id
        self.verdict = verdict
        self.score = score

@pytest.mark.asyncio
async def test_eval_complete_broadcast():
    # Mock MarketDataService
    md_service = MagicMock()
    md_service.get_ohlcv.return_value = []  # No OHLCV needed for this test

    # Fake evaluator returning one result
    fake_evaluator = MagicMock()
    fake_evaluator.evaluate_all.return_value = [FakeEvalResult('test-id', 'PROMOTE', 0.42)]

    # Patch evaluator builder and WS manager broadcast
    with patch('app.core.run_pipeline.build_evaluator', return_value=fake_evaluator):
        with patch('app.api.ws.manager.broadcast', new=AsyncMock()) as mock_broadcast:
            await run_pipeline(md_service, pairs=['BTC/USDT'], timeframes=['5m'], days=1, ai_eval=True)
            assert mock_broadcast.called, "WebSocket broadcast not called"
            call_msg = mock_broadcast.call_args[0][0]
            assert call_msg.get('type') == 'eval_complete'
            payload = call_msg.get('payload', {})
            assert payload.get('strategy_id') == 'test-id'
            assert payload.get('verdict') == 'PROMOTE'
            assert payload.get('score') == 0.42
