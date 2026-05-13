import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import get_current_user
from unittest.mock import AsyncMock, MagicMock

client = TestClient(app)

@pytest.fixture
def auth_header():
    app.dependency_overrides[get_current_user] = lambda: "test-user"
    yield {"Authorization": "Bearer test-token"}
    app.dependency_overrides.clear()

def test_get_exchange_status_success(auth_header, monkeypatch):
    """
    TASK-090: Verifica endpoint exchange status
    """
    mock_adapter = MagicMock()
    mock_adapter.get_balance = AsyncMock(return_value=1234.56)
    mock_adapter.close = AsyncMock()
    
    # Mocking BinanceExchangeAdapter class instantiation
    monkeypatch.setattr("app.api.exchange.BinanceExchangeAdapter", lambda **kwargs: mock_adapter)
    
    response = client.get("/api/exchange/status", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] in ["testnet", "live"]
    assert data["usdt_balance"] == 1234.56
