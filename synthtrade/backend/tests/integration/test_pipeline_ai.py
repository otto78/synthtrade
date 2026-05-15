import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, UTC
from app.ai.schemas import EvalResult
from app.core.run_pipeline import run_pipeline
from app.services.market_data_service import MarketDataService


def make_ohlcv(n=100):
    np.random.seed(42)
    close = pd.Series(100 + np.cumsum(np.random.randn(n) * 0.5 + 0.3))
    return pd.DataFrame({"open": close, "high": close*1.002,
                         "low": close*0.998, "close": close, "volume": 1000.0})


def make_eval(strategy_id="s1", verdict="PROMOTE", score=0.8):
    return EvalResult(strategy_id=strategy_id, score=score, verdict=verdict,
                      reasoning="ok", confidence=0.9, model_used="m",
                      evaluated_at=datetime.now(UTC))


@pytest.fixture
def mock_md_service():
    service = MagicMock(spec=MarketDataService)
    service.get_ohlcv.return_value = make_ohlcv()
    return service


@pytest.mark.asyncio
async def test_pipeline_calls_evaluate_all(mock_md_service):
    mock_db = MagicMock()
    mock_db.table.return_value.upsert.return_value.execute.return_value.data = []
    mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value.data = []

    mock_evaluator = MagicMock()
    mock_evaluator.evaluate_all = AsyncMock(return_value=[make_eval()])

    with patch("app.core.run_pipeline.get_supabase", return_value=mock_db), \
         patch("app.core.run_pipeline.build_evaluator", return_value=mock_evaluator):
        # Patch Ranker per evitare ImportError o logic changes
        with patch("app.core.run_pipeline.Ranker") as mock_ranker_cls:
            mock_ranker = mock_ranker_cls.return_value
            mock_ranker.compute_score.return_value = 0.75
            await run_pipeline(mock_md_service, pairs=["BTC/USDT"], timeframes=["1h"], ai_eval=True)

    mock_evaluator.evaluate_all.assert_called_once()


@pytest.mark.asyncio
async def test_pipeline_demotes_strategy_on_demote_verdict(mock_md_service):
    mock_db = MagicMock()
    mock_db.table.return_value.upsert.return_value.execute.return_value.data = []
    mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value.data = []

    mock_evaluator = MagicMock()
    mock_evaluator.evaluate_all = AsyncMock(
        return_value=[make_eval(verdict="DEMOTE", score=0.2)])

    with patch("app.core.run_pipeline.get_supabase", return_value=mock_db), \
         patch("app.core.run_pipeline.build_evaluator", return_value=mock_evaluator):
        with patch("app.core.run_pipeline.Ranker") as mock_ranker_cls:
            mock_ranker = mock_ranker_cls.return_value
            mock_ranker.compute_score.return_value = 0.75
            await run_pipeline(mock_md_service, pairs=["BTC/USDT"], timeframes=["1h"], ai_eval=True)

    mock_db.table.return_value.update.assert_called()


@pytest.mark.asyncio
async def test_pipeline_ai_errors_do_not_block(mock_md_service):
    mock_db = MagicMock()
    mock_db.table.return_value.upsert.return_value.execute.return_value.data = []

    mock_evaluator = MagicMock()
    mock_evaluator.evaluate_all = AsyncMock(side_effect=Exception("AI down"))

    with patch("app.core.run_pipeline.get_supabase", return_value=mock_db), \
         patch("app.core.run_pipeline.build_evaluator", return_value=mock_evaluator):
        with patch("app.core.run_pipeline.Ranker") as mock_ranker_cls:
            mock_ranker = mock_ranker_cls.return_value
            mock_ranker.compute_score.return_value = 0.75
            try:
                await run_pipeline(mock_md_service, pairs=["BTC/USDT"], timeframes=["1h"], ai_eval=True)
            except Exception:
                pytest.fail("Pipeline non deve propagare errori AI")


@pytest.mark.asyncio
async def test_pipeline_without_ai_eval_skips_evaluator(mock_md_service):
    mock_db = MagicMock()
    mock_db.table.return_value.upsert.return_value.execute.return_value.data = []

    mock_evaluator = MagicMock()
    mock_evaluator.evaluate_all = AsyncMock()

    with patch("app.core.run_pipeline.get_supabase", return_value=mock_db), \
         patch("app.core.run_pipeline.build_evaluator", return_value=mock_evaluator):
        with patch("app.core.run_pipeline.Ranker") as mock_ranker_cls:
            mock_ranker = mock_ranker_cls.return_value
            mock_ranker.compute_score.return_value = 0.75
            await run_pipeline(mock_md_service, pairs=["BTC/USDT"], timeframes=["1h"], ai_eval=False)

    mock_evaluator.evaluate_all.assert_not_called()
