import pytest
import json
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ── Fixture token ─────────────────────────────────────────────────────

@pytest.fixture
def token(monkeypatch):
    from app import config
    config.settings.APP_PASSWORD = "testpass"
    r = client.post("/auth/login", json={"password": "testpass"})
    return r.json()["access_token"]


# ── Connessione senza token → chiude con 1008 ─────────────────────────

def test_ws_no_token_closes_with_1008():
    with client.websocket_connect("/ws") as ws:
        data = ws.receive_json()
        assert data["code"] == 1008


# ── Connessione con token invalido → chiude con 1008 ─────────────────

def test_ws_invalid_token_closes_with_1008():
    with client.websocket_connect("/ws?token=invalidtoken") as ws:
        data = ws.receive_json()
        assert data["code"] == 1008


# ── Connessione valida → riceve ping entro la connessione ─────────────

def test_ws_valid_token_receives_ping(token):
    with client.websocket_connect(f"/ws?token={token}") as ws:
        data = ws.receive_json()
        assert data["type"] == "ping"


# ── Broadcast prezzo ──────────────────────────────────────────────────

def test_ws_broadcast_price(token):
    from app.api.ws import manager

    with client.websocket_connect(f"/ws?token={token}") as ws:
        ws.receive_json()  # consuma il ping iniziale

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            manager.broadcast({"type": "price", "pair": "BTC/USDT", "price": 62000.0})
        )
        data = ws.receive_json()

    assert data["type"] == "price"
    assert data["pair"] == "BTC/USDT"
    assert data["price"] == 62000.0


# ── ConnectionManager ─────────────────────────────────────────────────

def test_connection_manager_connect_disconnect():
    from app.api.ws import ConnectionManager
    from unittest.mock import AsyncMock, MagicMock

    manager = ConnectionManager()
    mock_ws = MagicMock()
    mock_ws.accept = AsyncMock()
    mock_ws.send_json = AsyncMock()

    import asyncio
    asyncio.get_event_loop().run_until_complete(manager.connect(mock_ws))
    assert mock_ws in manager.active_connections

    manager.disconnect(mock_ws)
    assert mock_ws not in manager.active_connections


def test_connection_manager_broadcast_sends_to_all():
    from app.api.ws import ConnectionManager
    from unittest.mock import AsyncMock, MagicMock

    manager = ConnectionManager()
    ws1, ws2 = MagicMock(), MagicMock()
    ws1.accept = AsyncMock()
    ws2.accept = AsyncMock()
    ws1.send_json = AsyncMock()
    ws2.send_json = AsyncMock()

    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(manager.connect(ws1))
    loop.run_until_complete(manager.connect(ws2))
    loop.run_until_complete(manager.broadcast({"type": "ping"}))

    ws1.send_json.assert_called_once_with({"type": "ping"})
    ws2.send_json.assert_called_once_with({"type": "ping"})
