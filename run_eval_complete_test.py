import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.run_pipeline import run_pipeline

async def main():
    # Mock MarketDataService with dummy get_ohlcv
    md_service = MagicMock()
    md_service.get_ohlcv.return_value = []  # empty ohlcv list (won't be used because no backtest)

    # Prepare a fake evaluator that returns a single eval result
    class FakeEvalResult:
        def __init__(self, strategy_id, verdict, score):
            self.strategy_id = strategy_id
            self.verdict = verdict
            self.score = score

    fake_evaluator = MagicMock()
    fake_evaluator.evaluate_all.return_value = [FakeEvalResult('test-id', 'PROMOTE', 0.42)]

    # Patch the evaluator builder to return our fake evaluator
    with patch('app.core.run_pipeline.build_evaluator', return_value=fake_evaluator):
        # Patch the WS manager broadcast to capture calls
        with patch('app.api.ws.manager.broadcast', new=AsyncMock()) as mock_broadcast:
            # Run pipeline with ai_eval enabled; it will hit the broadcast path
            await run_pipeline(md_service, pairs=['BTC/USDT'], timeframes=['5m'], days=1, ai_eval=True)
            # Verify broadcast was called at least once with the expected type
            assert mock_broadcast.called, "WebSocket broadcast not called"
            call_args = mock_broadcast.call_args[0][0]
            assert call_args.get('type') == 'eval_complete', f"Unexpected message type: {call_args.get('type')}"
            payload = call_args.get('payload', {})
            assert payload.get('strategy_id') == 'test-id'
            assert payload.get('verdict') == 'PROMOTE'
            assert payload.get('score') == 0.42
            print('Test passed')

if __name__ == '__main__':
    asyncio.run(main())
