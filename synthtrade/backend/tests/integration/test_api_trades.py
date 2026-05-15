import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import get_current_user, get_db


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def mock_auth():
    app.dependency_overrides[get_current_user] = lambda: "user"
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_trades():
    return [
        {"id": "t1", "strategy_id": "s1", "pair": "BTC/USDT", "action": "BUY",
         "price": 60000.0, "quantity": 0.01, "status": "OPEN",
         "pnl_pct": 0.0, "executed_at": "2024-01-01T10:00:00Z"},
        {"id": "t2", "strategy_id": "s1", "pair": "ETH/USDT", "action": "SELL",
         "price": 3000.0, "quantity": 0.1, "status": "CLOSED",
         "pnl_pct": 2.5, "executed_at": "2024-01-01T09:00:00Z",
         "closed_at": "2024-01-01T11:00:00Z"},
    ]


def setup_mock_db(mock_db, data):
    exec_res = MagicMock()
    exec_res.data = data
    
    # Gestisce catene fluide con o senza .eq()
    mock_db.table.return_value.select.return_value.execute.return_value = exec_res
    mock_db.table.return_value.select.return_value.order.return_value.execute.return_value = exec_res
    mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = exec_res
    return mock_db


def test_get_trades_returns_list(client, mock_trades):
    mock_db = MagicMock()
    setup_mock_db(mock_db, mock_trades)
    app.dependency_overrides[get_db] = lambda: mock_db
    
    resp = client.get("/api/trades")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) == 2


def test_get_trades_filter_open(client, mock_trades):
    open_trades = [t for t in mock_trades if t["status"] == "OPEN"]
    mock_db = MagicMock()
    setup_mock_db(mock_db, open_trades)
    app.dependency_overrides[get_db] = lambda: mock_db
    
    resp = client.get("/api/trades?status=OPEN")
    assert resp.status_code == 200
    assert all(t["status"] == "OPEN" for t in resp.json())


def test_get_trades_required_fields(client, mock_trades):
    mock_db = MagicMock()
    setup_mock_db(mock_db, mock_trades)
    app.dependency_overrides[get_db] = lambda: mock_db
    
    resp = client.get("/api/trades")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) > 0
    trade = data[0]
    for field in ["id", "pair", "action", "price", "quantity", "status", "executed_at"]:
        assert field in trade


def test_get_trades_without_token_returns_401(client):
    app.dependency_overrides.clear()
    resp = client.get("/api/trades")
    assert resp.status_code == 401


def test_get_open_positions_endpoint(client, mock_trades):
    open_trades = [t for t in mock_trades if t["status"] == "OPEN"]
    mock_db = MagicMock()
    setup_mock_db(mock_db, open_trades)
    app.dependency_overrides[get_db] = lambda: mock_db
    
    resp = client.get("/api/trades/open")
    assert resp.status_code == 200
    assert all(t["status"] == "OPEN" for t in resp.json())
