import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, UTC
from app.ai.evaluator import Evaluator
from app.ai.schemas import EvalResult, ModelResponse, MarketContext, OhlcvSummary, StrategyContext, EvalPromptInput
from app.ai.eval_parser import EvalParseError
from app.ai.model_client import AllModelsUnavailableError


def make_strategy_row():
    return {
        "id": "s1", "title": "EMA Cross", "template": "trend_ema",
        "params": {"ema_fast": 9, "ema_slow": 21},
        "backtest": {"pnl_pct": 12.0, "win_rate": 0.6, "sharpe": 1.3,
                     "max_drawdown_pct": 5.0, "num_trades": 20},
        "score": 0.75, "pair": "BTC/USDT", "timeframe": "1h",
    }


def make_eval_result(verdict="PROMOTE"):
    return EvalResult(strategy_id="s1", score=0.8, verdict=verdict,
                      reasoning="Good", confidence=0.9, model_used="m",
                      evaluated_at=datetime.now(UTC))


@pytest.fixture
def evaluator():
    model_client = MagicMock()
    model_client.call_with_fallback = AsyncMock(return_value=ModelResponse(
        content='{"score":0.8,"verdict":"PROMOTE","reasoning":"Good metrics","confidence":0.9}',
        model="model-a", tokens_used=50
    ))
    cache = MagicMock()
    cache.get_cached_eval.return_value = None
    cache.save_eval = MagicMock()
    logger = MagicMock()

    return Evaluator(model_client=model_client, cache=cache, logger=logger)


@pytest.mark.asyncio
async def test_evaluate_strategy_calls_model(evaluator):
    import pandas as pd, numpy as np
    np.random.seed(0)
    close = pd.Series(100 + np.cumsum(np.random.randn(100) * 0.5 + 0.3))
    df = pd.DataFrame({"open": close, "high": close*1.002, "low": close*0.998,
                       "close": close, "volume": 1000.0})
    result = await evaluator.evaluate_strategy(make_strategy_row(), df)
    evaluator.model_client.call_with_fallback.assert_called_once()
    assert result is not None
    assert result.verdict == "PROMOTE"


@pytest.mark.asyncio
async def test_cache_hit_skips_model(evaluator):
    evaluator.cache.get_cached_eval.return_value = make_eval_result()
    result = await evaluator.evaluate_strategy(make_strategy_row(), MagicMock())
    evaluator.model_client.call_with_fallback.assert_not_called()
    assert result.verdict == "PROMOTE"


@pytest.mark.asyncio
async def test_saves_eval_after_success(evaluator):
    import pandas as pd, numpy as np
    np.random.seed(0)
    close = pd.Series(100 + np.cumsum(np.random.randn(100) * 0.5 + 0.3))
    df = pd.DataFrame({"open": close, "high": close*1.002, "low": close*0.998,
                       "close": close, "volume": 1000.0})
    await evaluator.evaluate_strategy(make_strategy_row(), df)
    evaluator.cache.save_eval.assert_called_once()


@pytest.mark.asyncio
async def test_eval_parse_error_returns_none(evaluator):
    evaluator.model_client.call_with_fallback = AsyncMock(
        return_value=ModelResponse(content="not json", model="m", tokens_used=0))
    import pandas as pd, numpy as np
    np.random.seed(0)
    close = pd.Series(100 + np.cumsum(np.random.randn(100) * 0.5))
    df = pd.DataFrame({"open": close, "high": close*1.002, "low": close*0.998,
                       "close": close, "volume": 1000.0})
    result = await evaluator.evaluate_strategy(make_strategy_row(), df)
    assert result is None
    evaluator.logger.error.assert_called()


@pytest.mark.asyncio
async def test_all_models_unavailable_returns_none(evaluator):
    evaluator.model_client.call_with_fallback = AsyncMock(
        side_effect=AllModelsUnavailableError("all down"))
    import pandas as pd, numpy as np
    np.random.seed(0)
    close = pd.Series(100 + np.cumsum(np.random.randn(100) * 0.5))
    df = pd.DataFrame({"open": close, "high": close*1.002, "low": close*0.998,
                       "close": close, "volume": 1000.0})
    result = await evaluator.evaluate_strategy(make_strategy_row(), df)
    assert result is None
    evaluator.logger.error.assert_called()


@pytest.mark.asyncio
async def test_evaluate_all_with_semaphore(evaluator):
    import pandas as pd, numpy as np
    np.random.seed(0)
    close = pd.Series(100 + np.cumsum(np.random.randn(100) * 0.5 + 0.3))
    df = pd.DataFrame({"open": close, "high": close*1.002, "low": close*0.998,
                       "close": close, "volume": 1000.0})
    strategies = [make_strategy_row() for _ in range(3)]
    results = await evaluator.evaluate_all(strategies, df, max_concurrent=2)
    assert len(results) == 3
