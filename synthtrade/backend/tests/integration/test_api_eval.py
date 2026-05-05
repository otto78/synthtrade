import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from datetime import datetime, UTC
from app.main import app
from app.core.auth_utils import create_access_token
from app.ai.schemas import EvalResult


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"Authorization": f"Bearer {create_access_token()}"}


def make_eval(verdict="PROMOTE"):
    return EvalResult(
        strategy_id="s1", score=0.8, verdict=verdict,
        reasoning="Good metrics", confidence=0.9,
        model_used="model-a", tokens_used=50,
        evaluated_at=datetime.now(UTC)
    )


def test_get_eval_returns_cache_if_present(client, auth_headers):
    with patch("app.api.eval.EvalCache") as MockCache:
        MockCache.return_value.get_cached_eval.return_value = make_eval()
        resp = client.get("/api/strategies/s1/eval", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["verdict"] == "PROMOTE"


def test_get_eval_returns_202_if_not_cached(client, auth_headers):
    with patch("app.api.eval.EvalCache") as MockCache:
        MockCache.return_value.get_cached_eval.return_value = None
        resp = client.get("/api/strategies/s1/eval", headers=auth_headers)
    assert resp.status_code == 202


def test_post_eval_refresh_accepted(client, auth_headers):
    with patch("app.api.eval.EvalCache"), \
         patch("app.api.eval.build_evaluator"):
        resp = client.post("/api/strategies/s1/eval/refresh", headers=auth_headers)
    assert resp.status_code in (200, 202)


def test_eval_endpoints_require_auth(client):
    assert client.get("/api/strategies/s1/eval").status_code == 401
    assert client.post("/api/strategies/s1/eval/refresh").status_code == 401
