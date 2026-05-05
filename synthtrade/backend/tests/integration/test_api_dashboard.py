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

def make_db(trades=None, active_strategy=None, equity_rows=None):
    mock = MagicMock()
    t = mock.table.return_value

    # trades per pnl_today
    t.select.return_value.gte.return_value.execute.return_value.data = trades or []

    # strategia attiva
    t.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = (
        [active_strategy] if active_strategy else []
    )

    # equity history (trades ordinati)
    t.select.return_value.order.return_value.execute.return_value.data = equity_rows or []

    return mock


# ── GET /dashboard ────────────────────────────────────────────────────

def test_dashboard_returns_required_fields(auth):
    with patch("app.api.dashboard.get_supabase", return_value=make_db()), \
         patch("app.api.dashboard.get_current_price", return_value=62000.0):
        r = client.get("/dashboard", headers=auth)
    assert r.status_code == 200
    data = r.json()
    for field in ("balance", "pnl_today", "active_strategy", "engine_status"):
        assert field in data


def test_dashboard_pnl_today_zero_when_no_trades(auth):
    with patch("app.api.dashboard.get_supabase", return_value=make_db(trades=[])), \
         patch("app.api.dashboard.get_current_price", return_value=62000.0):
        r = client.get("/dashboard", headers=auth)
    assert r.json()["pnl_today"] == 0.0


def test_dashboard_pnl_today_computed_from_trades(auth):
    trades = [
        {"pnl_pct": 0.05, "cost_eur": 100.0},
        {"pnl_pct": -0.02, "cost_eur": 50.0},
    ]
    with patch("app.api.dashboard.get_supabase", return_value=make_db(trades=trades)), \
         patch("app.api.dashboard.get_current_price", return_value=62000.0):
        r = client.get("/dashboard", headers=auth)
    expected = round(0.05 * 100.0 + (-0.02) * 50.0, 4)
    assert r.json()["pnl_today"] == expected


def test_dashboard_active_strategy_none_when_no_active(auth):
    with patch("app.api.dashboard.get_supabase", return_value=make_db()), \
         patch("app.api.dashboard.get_current_price", return_value=62000.0):
        r = client.get("/dashboard", headers=auth)
    assert r.json()["active_strategy"] is None


def test_dashboard_active_strategy_returned_when_present(auth):
    strategy = {"id": "trend_00001", "title": "EMA Trend", "score": 0.72, "status": "ACTIVE"}
    with patch("app.api.dashboard.get_supabase", return_value=make_db(active_strategy=strategy)), \
         patch("app.api.dashboard.get_current_price", return_value=62000.0):
        r = client.get("/dashboard", headers=auth)
    assert r.json()["active_strategy"]["id"] == "trend_00001"


def test_dashboard_engine_status_is_string(auth):
    with patch("app.api.dashboard.get_supabase", return_value=make_db()), \
         patch("app.api.dashboard.get_current_price", return_value=62000.0):
        r = client.get("/dashboard", headers=auth)
    assert isinstance(r.json()["engine_status"], str)


# ── GET /dashboard/equity-history ────────────────────────────────────

def test_equity_history_returns_list(auth):
    rows = [
        {"executed_at": "2024-01-01T10:00:00", "cost_eur": 100.0, "pnl_pct": 0.05},
        {"executed_at": "2024-01-01T11:00:00", "cost_eur": 100.0, "pnl_pct": 0.03},
    ]
    with patch("app.api.dashboard.get_supabase", return_value=make_db(equity_rows=rows)):
        r = client.get("/dashboard/equity-history", headers=auth)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_equity_history_items_have_ts_and_value(auth):
    rows = [{"executed_at": "2024-01-01T10:00:00", "cost_eur": 100.0, "pnl_pct": 0.05}]
    with patch("app.api.dashboard.get_supabase", return_value=make_db(equity_rows=rows)):
        r = client.get("/dashboard/equity-history", headers=auth)
    item = r.json()[0]
    assert "ts" in item
    assert "value" in item


def test_equity_history_empty_when_no_trades(auth):
    with patch("app.api.dashboard.get_supabase", return_value=make_db(equity_rows=[])):
        r = client.get("/dashboard/equity-history", headers=auth)
    assert r.json() == []


# ── Auth guard ────────────────────────────────────────────────────────

def test_dashboard_without_token_returns_401():
    r = client.get("/dashboard")
    assert r.status_code == 401
