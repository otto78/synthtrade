import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ── Login ─────────────────────────────────────────────────────────────

def test_login_correct_password_returns_token(monkeypatch):
    monkeypatch.setenv("APP_PASSWORD", "testpass")
    from app import config
    config.settings.APP_PASSWORD = "testpass"

    response = client.post("/auth/login", json={"password": "testpass"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password_returns_401(monkeypatch):
    from app import config
    config.settings.APP_PASSWORD = "testpass"

    response = client.post("/auth/login", json={"password": "wrongpass"})
    assert response.status_code == 401


def test_login_empty_password_returns_401():
    response = client.post("/auth/login", json={"password": ""})
    assert response.status_code == 401


# ── Protezione route ──────────────────────────────────────────────────

def test_protected_route_without_token_returns_401():
    response = client.get("/strategies")
    assert response.status_code == 401


def test_protected_route_with_invalid_token_returns_401():
    response = client.get("/strategies", headers={"Authorization": "Bearer invalidtoken"})
    assert response.status_code == 401


def test_protected_route_with_valid_token_returns_200(monkeypatch):
    from app import config
    config.settings.APP_PASSWORD = "testpass"

    login = client.post("/auth/login", json={"password": "testpass"})
    token = login.json()["access_token"]

    with patch("app.api.strategies.get_supabase") as mock_db:
        mock_db.return_value.table.return_value.select.return_value \
            .execute.return_value.data = []
        response = client.get("/strategies", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200


# ── Token scaduto ─────────────────────────────────────────────────────

def test_expired_token_returns_401():
    from app.core.auth_utils import create_access_token
    from datetime import timedelta
    token = create_access_token(expires_delta=timedelta(seconds=-1))

    response = client.get("/strategies", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
