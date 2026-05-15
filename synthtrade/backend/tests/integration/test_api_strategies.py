import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_db_fixture():
    # Salviamo gli override originali
    original_overrides = app.dependency_overrides.copy()
    
    def get_mock_db():
        # Questo verrà configurato dai singoli test
        return getattr(pytest, "_current_mock_db", MagicMock())
    
    from app.dependencies import get_db
    app.dependency_overrides[get_db] = get_mock_db
    yield
    # Ripristiniamo gli override originali
    app.dependency_overrides = original_overrides


@pytest.fixture
def token(monkeypatch):
    from app import config
    config.settings.APP_PASSWORD = "testpass"
    r = client.post("/api/auth/login", json={"password": "testpass"})
    return r.json()["access_token"]


@pytest.fixture
def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ── Dati mock ─────────────────────────────────────────────────────────

STRATEGY_SUMMARY = {
    "id": "trend_00001", "title": "EMA Trend BTC 5m",
    "pair": "BTC/USDT", "timeframe": "5m", "params": {}, "budget_eur": 500.0,
    "score": 0.72, "status": "PENDING",
    "ai_score": 0.81, "ai_risk": "LOW",
}

STRATEGY_DETAIL = {
    **STRATEGY_SUMMARY,
    "template": "trend_ema",
    "equity_curve": [1000.0, 1010.0, 1020.0],
    "ai_note": "Strategia solida su trend rialzista",
    "backtest": {"pnl_pct": 8.2, "sharpe": 1.4, "win_rate": 0.6, "max_drawdown_pct": 5.1, "num_trades": 42},
}


def mock_db_list(data):
    mock = MagicMock()
    # Mocking chain for get_all and filter
    mock.table.return_value.select.return_value.execute.return_value.data = data
    mock.table.return_value.select.return_value.eq.return_value.execute.return_value.data = data
    return mock


def mock_db_detail(data):
    mock = MagicMock()
    # Mocking chain for get_by_id
    mock.table.return_value.select.return_value.eq.return_value.execute.return_value.data = data
    return mock


def mock_db_update(select_data, updated_status):
    mock = MagicMock()
    # get_by_id call
    mock.table.return_value.select.return_value.eq.return_value.execute.return_value.data = select_data
    # update call
    mock.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        {**select_data[0], "status": updated_status}
    ] if select_data else []
    return mock


# ── GET /strategies ───────────────────────────────────────────────────

def test_list_strategies_returns_list(auth):
    pytest._current_mock_db = mock_db_list([STRATEGY_SUMMARY])
    r = client.get("/api/strategies", headers=auth)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_list_strategies_contains_required_fields(auth):
    pytest._current_mock_db = mock_db_list([STRATEGY_SUMMARY])
    r = client.get("/api/strategies", headers=auth)
    item = r.json()[0]
    for field in ("id", "title", "score", "status"):
        assert field in item


def test_list_strategies_filter_by_status(auth):
    pending = {**STRATEGY_SUMMARY, "status": "PENDING"}
    pytest._current_mock_db = mock_db_list([pending])
    r = client.get("/api/strategies?strategy_status=PENDING", headers=auth)
    assert r.status_code == 200
    assert all(s["status"] == "PENDING" for s in r.json())


def test_list_strategies_empty(auth):
    pytest._current_mock_db = mock_db_list([])
    r = client.get("/api/strategies", headers=auth)
    assert r.status_code == 200
    assert r.json() == []


# ── GET /strategies/{id} ──────────────────────────────────────────────

def test_get_strategy_returns_detail(auth):
    pytest._current_mock_db = mock_db_detail([STRATEGY_DETAIL])
    r = client.get("/api/strategies/trend_00001", headers=auth)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == "trend_00001"
    assert "equity_curve" in data
    assert "params" in data
    assert "ai_note" in data


def test_get_strategy_not_found_returns_404(auth):
    pytest._current_mock_db = mock_db_detail([])
    r = client.get("/api/strategies/nonexistent", headers=auth)
    assert r.status_code == 404


# ── POST /strategies/{id}/approve ────────────────────────────────────

def test_approve_pending_strategy(auth):
    pending = {**STRATEGY_SUMMARY, "status": "PENDING"}
    pytest._current_mock_db = mock_db_update([pending], "APPROVED")
    r = client.post("/api/strategies/trend_00001/approve", headers=auth)
    assert r.status_code == 200
    assert r.json()["status"] == "APPROVED"


def test_approve_non_pending_returns_409(auth):
    active = {**STRATEGY_SUMMARY, "status": "ACTIVE"}
    pytest._current_mock_db = mock_db_update([active], "APPROVED")
    r = client.post("/api/strategies/trend_00001/approve", headers=auth)
    assert r.status_code == 409


def test_approve_nonexistent_returns_404(auth):
    pytest._current_mock_db = mock_db_update([], "APPROVED")
    r = client.post("/api/strategies/nonexistent/approve", headers=auth)
    assert r.status_code == 404


# ── POST /strategies/{id}/reject ─────────────────────────────────────

def test_reject_strategy(auth):
    pending = {**STRATEGY_SUMMARY, "status": "PENDING"}
    pytest._current_mock_db = mock_db_update([pending], "REJECTED")
    r = client.post("/api/strategies/trend_00001/reject", headers=auth)
    assert r.status_code == 200
    assert r.json()["status"] == "REJECTED"


def test_reject_nonexistent_returns_404(auth):
    pytest._current_mock_db = mock_db_update([], "REJECTED")
    r = client.post("/api/strategies/nonexistent/reject", headers=auth)
    assert r.status_code == 404


# ── Auth guard ────────────────────────────────────────────────────────

def test_strategies_without_token_returns_401():
    r = client.get("/api/strategies")
    assert r.status_code == 401
