import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import pandas as pd

from app.core.run_pipeline import run_pipeline
from app.core.strategy_generator import StrategyParams

class FakeEvalResult:
    def __init__(self, strategy_id, verdict, score):
        self.strategy_id = strategy_id
        self.verdict = verdict
        self.score = score

@pytest.mark.asyncio
async def test_eval_complete_broadcast():
    # Mock MarketDataService with a valid close price series
    md_service = MagicMock()
    prices = [100.0 + i * 0.5 for i in range(80)]
    md_service.get_ohlcv.return_value = pd.DataFrame({"close": prices})

    # Fake evaluator returning one result
    fake_evaluator = MagicMock()
    fake_evaluator.evaluate_all = AsyncMock(return_value=[FakeEvalResult('test-id', 'PROMOTE', 0.42)])

    # Minimal strategy variant that will be backtested
    strategy = StrategyParams(
        template='trend_ema',
        pair='BTC/USDT',
        timeframe='5m',
        params={'ema_fast': 5, 'ema_slow': 12, 'stop_loss': 0.02, 'take_profit': 0.05},
    )

    # Patch strategy generation and registry lookup to keep the test focused
    with patch('app.core.run_pipeline.generate_all_variants', return_value=[strategy]):
        with patch('app.core.run_pipeline.registry.get', return_value=lambda df, p: pd.Series([1, -1] * 40, index=df.index)):
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
