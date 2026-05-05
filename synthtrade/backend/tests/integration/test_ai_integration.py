import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, UTC
from app.ai.evaluator import Evaluator
from app.ai.model_client import ModelClient, AllModelsUnavailableError
from app.ai.cache import EvalCache
from app.ai.schemas import ModelResponse, EvalResult


def make_ohlcv(n=100):
    np.random.seed(42)
    close = pd.Series(100 + np.cumsum(np.random.randn(n) * 0.5 + 0.3))
    return pd.DataFrame({"open": close, "high": close*1.002,
                         "low": close*0.998, "close": close, "volume": 1000.0})


def make_strategy():
    return {
        "id": "s1", "title": "EMA Cross", "template": "trend_ema",
        "params": {"ema_fast": 9, "ema_slow": 21},
        "backtest": {"pnl_pct": 15.0, "win_rate": 0.65, "sharpe": 1.6,
                     "max_drawdown_pct": 4.0, "num_trades": 30},
        "score": 0.82, "pair": "BTC/USDT", "timeframe": "1h",
    }


def build_evaluator_with_mock(response_content: str, cache_result=None):
    model_client = MagicMock(spec=ModelClient)
    model_client.call_with_fallback = AsyncMock(return_value=ModelResponse(
        content=response_content, model="model-a", tokens_used=50))
    cache = MagicMock(spec=EvalCache)
    cache.get_cached_eval.return_value = cache_result
    cache.save_eval = MagicMock()
    return Evaluator(model_client=model_client, cache=cache)


@pytest.mark.asyncio
async def test_happy_path_good_metrics_promote():
    evaluator = build_evaluator_with_mock(
        '{"score":0.82,"verdict":"PROMOTE","reasoning":"Strong metrics","confidence":0.9}')
    result = await evaluator.evaluate_strategy(make_strategy(), make_ohlcv())
    assert result is not None
    assert result.verdict == "PROMOTE"
    assert result.score >= 0.7


@pytest.mark.asyncio
async def test_fallback_model_used_on_primary_timeout():
    model_client = MagicMock(spec=ModelClient)
    model_client.call_with_fallback = AsyncMock(return_value=ModelResponse(
        content='{"score":0.6,"verdict":"HOLD","reasoning":"Fallback ok","confidence":0.7}',
        model="model-fallback", tokens_used=30))
    cache = MagicMock(spec=EvalCache)
    cache.get_cached_eval.return_value = None
    cache.save_eval = MagicMock()
    evaluator = Evaluator(model_client=model_client, cache=cache)

    result = await evaluator.evaluate_strategy(make_strategy(), make_ohlcv())
    assert result.model_used == "model-fallback"


@pytest.mark.asyncio
async def test_cache_hit_does_not_call_model():
    cached = EvalResult(strategy_id="s1", score=0.8, verdict="PROMOTE",
                        reasoning="cached", confidence=0.9, model_used="m",
                        evaluated_at=datetime.now(UTC))
    evaluator = build_evaluator_with_mock("irrelevant", cache_result=cached)
    result = await evaluator.evaluate_strategy(make_strategy(), make_ohlcv())
    evaluator.model_client.call_with_fallback.assert_not_called()
    assert result.verdict == "PROMOTE"


@pytest.mark.asyncio
async def test_malformed_json_logs_error_pipeline_continues():
    evaluator = build_evaluator_with_mock("this is not json at all")
    evaluator.logger = MagicMock()
    result = await evaluator.evaluate_strategy(make_strategy(), make_ohlcv())
    assert result is None
    evaluator.logger.error.assert_called()


@pytest.mark.asyncio
async def test_all_models_down_pipeline_completes():
    model_client = MagicMock(spec=ModelClient)
    model_client.call_with_fallback = AsyncMock(
        side_effect=AllModelsUnavailableError("all down"))
    cache = MagicMock(spec=EvalCache)
    cache.get_cached_eval.return_value = None
    evaluator = Evaluator(model_client=model_client, cache=cache, logger=MagicMock())

    result = await evaluator.evaluate_strategy(make_strategy(), make_ohlcv())
    assert result is None
    # Pipeline non deve crashare
