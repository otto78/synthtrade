import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, UTC, timedelta
from app.ai.cache import EvalCache
from app.ai.schemas import EvalResult


def make_eval(strategy_id="s1", verdict="PROMOTE"):
    return EvalResult(
        strategy_id=strategy_id, score=0.8, verdict=verdict,
        reasoning="Good", confidence=0.9, model_used="model-a",
        evaluated_at=datetime.now(UTC)
    )


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def cache(mock_db):
    with patch("app.ai.cache.get_supabase", return_value=mock_db):
        yield EvalCache(ttl_minutes=60)


def test_get_cached_eval_returns_result_if_fresh(cache, mock_db):
    fresh_ts = datetime.now(UTC).isoformat()
    mock_db.table.return_value.select.return_value.eq.return_value \
        .execute.return_value.data = [{
            "strategy_id": "s1", "score": 0.8, "verdict": "PROMOTE",
            "reasoning": "Good", "confidence": 0.9, "model_used": "model-a",
            "tokens_used": 10, "evaluated_at": fresh_ts
        }]
    result = cache.get_cached_eval("s1")
    assert result is not None
    assert result.verdict == "PROMOTE"


def test_get_cached_eval_returns_none_if_expired(cache, mock_db):
    old_ts = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
    mock_db.table.return_value.select.return_value.eq.return_value \
        .execute.return_value.data = [{
            "strategy_id": "s1", "score": 0.8, "verdict": "PROMOTE",
            "reasoning": "Good", "confidence": 0.9, "model_used": "model-a",
            "tokens_used": 10, "evaluated_at": old_ts
        }]
    result = cache.get_cached_eval("s1")
    assert result is None


def test_get_cached_eval_returns_none_if_absent(cache, mock_db):
    mock_db.table.return_value.select.return_value.eq.return_value \
        .execute.return_value.data = []
    result = cache.get_cached_eval("s1")
    assert result is None


def test_save_eval_upserts_to_supabase(cache, mock_db):
    eval_result = make_eval()
    cache.save_eval(eval_result)
    mock_db.table.return_value.upsert.assert_called_once()
    upserted = mock_db.table.return_value.upsert.call_args[0][0]
    assert upserted["strategy_id"] == "s1"
    assert upserted["verdict"] == "PROMOTE"
