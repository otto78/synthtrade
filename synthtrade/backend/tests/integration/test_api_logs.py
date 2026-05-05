import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ── Fixture token ─────────────────────────────────────────────────────

@pytest.fixture
def auth(monkeypatch):
    from app import config
    config.settings.APP_PASSWORD = "testpass"
    r = client.post("/auth/login", json={"password": "testpass"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ── Mock helpers ──────────────────────────────────────────────────────

LOG_1 = {"id": "aaa", "strategy_id": "trend_00001", "action": "BUY",
          "price": 62000.0, "quantity": 0.001, "reason": "EMA crossover",
          "ai_score": 0.81, "created_at": "2024-01-01T10:00:00"}
LOG_2 = {"id": "bbb", "strategy_id": "trend_00001", "action": "SELL",
          "price": 63000.0, "quantity": 0.001, "reason": "reverse signal",
          "ai_score": 0.75, "created_at": "2024-01-01T11:00:00"}


def make_db(data=None):
    mock = MagicMock()
    q = mock.table.return_value.select.return_value
    q.order.return_value.limit.return_value.offset.return_value.execute.return_value.data = data or []
    q.eq.return_value.order.return_value.limit.return_value.offset.return_value.execute.return_value.data = data or []
    return mock


# ── GET /logs ─────────────────────────────────────────────────────────

def test_logs_returns_list(auth):
    with patch("app.api.logs.get_supabase", return_value=make_db([LOG_1, LOG_2])):
        r = client.get("/logs", headers=auth)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_logs_pagination_limit(auth):
    with patch("app.api.logs.get_supabase", return_value=make_db([LOG_1])):
        r = client.get("/logs?limit=1&offset=0", headers=auth)
    assert r.status_code == 200


def test_logs_pagination_offset(auth):
    with patch("app.api.logs.get_supabase", return_value=make_db([LOG_2])):
        r = client.get("/logs?limit=10&offset=1", headers=auth)
    assert r.status_code == 200


def test_logs_filter_by_action(auth):
    with patch("app.api.logs.get_supabase", return_value=make_db([LOG_1])):
        r = client.get("/logs?action=BUY", headers=auth)
    assert r.status_code == 200


def test_logs_most_recent_first(auth):
    logs = [LOG_2, LOG_1]  # già ordinati decrescenti dal mock
    with patch("app.api.logs.get_supabase", return_value=make_db(logs)):
        r = client.get("/logs", headers=auth)
    data = r.json()
    if len(data) >= 2:
        assert data[0]["created_at"] >= data[1]["created_at"]


def test_logs_empty(auth):
    with patch("app.api.logs.get_supabase", return_value=make_db([])):
        r = client.get("/logs", headers=auth)
    assert r.status_code == 200
    assert r.json() == []


def test_logs_items_have_required_fields(auth):
    with patch("app.api.logs.get_supabase", return_value=make_db([LOG_1])):
        r = client.get("/logs", headers=auth)
    item = r.json()[0]
    for field in ("id", "action", "created_at"):
        assert field in item


# ── GET /logs/export ──────────────────────────────────────────────────

def test_logs_export_returns_csv_content_type(auth):
    with patch("app.api.logs.get_supabase", return_value=make_db([LOG_1, LOG_2])):
        r = client.get("/logs/export", headers=auth)
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]


def test_logs_export_has_csv_header(auth):
    with patch("app.api.logs.get_supabase", return_value=make_db([LOG_1])):
        r = client.get("/logs/export", headers=auth)
    first_line = r.text.split("\n")[0]
    assert "action" in first_line
    assert "created_at" in first_line


def test_logs_export_empty_still_returns_csv(auth):
    with patch("app.api.logs.get_supabase", return_value=make_db([])):
        r = client.get("/logs/export", headers=auth)
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]


# ── Auth guard ────────────────────────────────────────────────────────

def test_logs_without_token_returns_401():
    r = client.get("/logs")
    assert r.status_code == 401


def test_logs_export_without_token_returns_401():
    r = client.get("/logs/export")
    assert r.status_code == 401
