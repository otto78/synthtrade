import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.execution.schemas import StrategyRequest

from app.dependencies import get_current_user

client = TestClient(app)

@pytest.fixture
def auth_header():
    # Override dependency for all tests using this fixture
    app.dependency_overrides[get_current_user] = lambda: "test-user"
    yield {"Authorization": "Bearer test-token"}
    # Clean up after test
    app.dependency_overrides.clear()

def test_start_generation_unauthorized():
    """
    TASK-051: endpoint protetti da get_current_user
    """
    # Ensure no override exists
    app.dependency_overrides.clear()
    
    req_data = {
        "budget_eur": 100.0,
        "duration_days": 30,
        "asset_class": "crypto",
        "risk_level": "medium"
    }
    # No auth header
    response = client.post("/api/pipeline/generate", json=req_data)
    assert response.status_code == 401

def test_start_generation_success(auth_header):
    """
    TASK-048, TASK-049: POST success and returns generation_id
    """
    req_data = {
        "budget_eur": 100.0,
        "duration_days": 30,
        "asset_class": "crypto",
        "risk_level": "medium",
        "max_strategies": 5
    }
    response = client.post("/api/pipeline/generate", json=req_data, headers=auth_header)
    assert response.status_code == 202
    data = response.json()
    assert "generation_id" in data
    assert data["status"] == "pending"

def test_get_generation_status(auth_header):
    """
    TASK-050: GET status
    """
    # 1. Start generation
    req_data = {
        "budget_eur": 100.0,
        "duration_days": 30,
        "asset_class": "crypto",
        "risk_level": "medium"
    }
    resp_start = client.post("/api/pipeline/generate", json=req_data, headers=auth_header)
    gen_id = resp_start.json()["generation_id"]
    
    # 2. Get status
    resp_status = client.get(f"/api/pipeline/generate/{gen_id}/status", headers=auth_header)
    assert resp_status.status_code == 200
    status_data = resp_status.json()
    assert "status" in status_data
    assert status_data["status"] in ["pending", "running", "completed"]
