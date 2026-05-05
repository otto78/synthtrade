import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.core.auth_utils import create_access_token


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    token = create_access_token()
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_trades():
    return [
        {"id": "t1", "strategy_id": "s1", "pair": "BTC/USDT", "action": "BUY",
         "price": 60000.0, "quantity": 0.01, "status": "OPEN",
         "stop_loss": 58800.0, "take_profit": 62400.0, "pnl_pct": None,
         "paper": True, "executed_at": "2024-01-01T10:00:00Z", "closed_at": None},
        {"id": "t2", "strategy_id": "s1", "pair": "ETH/USDT", "action": "SELL",
         "price": 3000.0, "quantity": 0.1, "status": "CLOSED",
         "stop_loss": 3060.0, "take_profit": 2880.0, "pnl_pct": 2.5,
         "paper": True, "executed_at": "2024-01-01T09:00:00Z",
         "closed_at": "2024-01-01T11:00:00Z"},
    ]


def test_get_trades_returns_list(client, auth_headers, mock_trades):
    with patch("app.api.trades.get_supabase") as mock_db:
        mock_db.return_value.table.return_value.select.return_value \
            .order.return_value.execute.return_value.data = mock_trades
        resp = client.get("/api/trades", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) == 2


def test_get_trades_filter_open(client, auth_headers, mock_trades):
    open_trades = [t for t in mock_trades if t["status"] == "OPEN"]
    with patch("app.api.trades.get_supabase") as mock_db:
        mock_db.return_value.table.return_value.select.return_value \
            .eq.return_value.order.return_value.execute.return_value.data = open_trades
        resp = client.get("/api/trades?status=OPEN", headers=auth_headers)
    assert resp.status_code == 200
    assert all(t["status"] == "OPEN" for t in resp.json())


def test_get_trades_required_fields(client, auth_headers, mock_trades):
    with patch("app.api.trades.get_supabase") as mock_db:
        mock_db.return_value.table.return_value.select.return_value \
            .order.return_value.execute.return_value.data = mock_trades
        resp = client.get("/api/trades", headers=auth_headers)
    trade = resp.json()[0]
    for field in ["id", "pair", "action", "price", "quantity", "status", "executed_at"]:
        assert field in trade


def test_get_trades_without_token_returns_401(client):
    resp = client.get("/api/trades")
    assert resp.status_code == 401


def test_get_open_positions_endpoint(client, auth_headers, mock_trades):
    open_trades = [t for t in mock_trades if t["status"] == "OPEN"]
    with patch("app.api.trades.get_supabase") as mock_db:
        mock_db.return_value.table.return_value.select.return_value \
            .eq.return_value.order.return_value.execute.return_value.data = open_trades
        resp = client.get("/api/trades/open", headers=auth_headers)
    assert resp.status_code == 200
    assert all(t["status"] == "OPEN" for t in resp.json())
