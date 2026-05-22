"""🔴 RED + 🟢 GREEN: Test per broadcast scalping in ws.py (TASK-801)."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.api.ws import ConnectionManager


@pytest.fixture
def manager():
    return ConnectionManager()


@pytest.fixture
def mock_ws():
    ws = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


class TestBroadcastScalpingTick:
    """Test per broadcast_scalping_tick."""

    @pytest.mark.asyncio
    async def test_broadcast_scalping_tick_structure(self, manager, mock_ws):
        manager.active_connections = [mock_ws]
        await manager.broadcast_scalping_tick(
            symbol="BTC/USDT",
            price=65000.0,
            volume=100.5,
            timestamp="2026-05-22T12:00:00Z",
        )
        mock_ws.send_json.assert_called_once()
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["type"] == "scalping_tick"
        assert call_args["symbol"] == "BTC/USDT"
        assert call_args["price"] == 65000.0
        assert call_args["volume"] == 100.5
        assert call_args["timestamp"] == "2026-05-22T12:00:00Z"

    @pytest.mark.asyncio
    async def test_broadcast_scalping_tick_to_all(self, manager):
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        manager.active_connections = [ws1, ws2]
        await manager.broadcast_scalping_tick(
            symbol="ETH/USDT", price=3200.0, volume=50.0,
        )
        assert ws1.send_json.called
        assert ws2.send_json.called

    @pytest.mark.asyncio
    async def test_broadcast_scalping_tick_empty_connections(self, manager):
        """Non deve sollevare eccezioni se non ci sono connessioni."""
        await manager.broadcast_scalping_tick(
            symbol="BTC/USDT", price=65000.0, volume=100.0,
        )
        # Test passes if no exception

    @pytest.mark.asyncio
    async def test_broadcast_scalping_tick_removes_dead_connection(self, manager, mock_ws):
        """Se una connessione fallisce, deve essere rimossa."""
        dead_ws = AsyncMock()
        dead_ws.send_json = AsyncMock(side_effect=Exception("Connection lost"))
        manager.active_connections = [dead_ws, mock_ws]
        await manager.broadcast_scalping_tick(
            symbol="BTC/USDT", price=65000.0, volume=100.0,
        )
        assert dead_ws not in manager.active_connections
        assert mock_ws in manager.active_connections


class TestBroadcastIntelScore:
    """Test per broadcast_intel_score."""

    @pytest.mark.asyncio
    async def test_broadcast_intel_score_structure(self, manager, mock_ws):
        manager.active_connections = [mock_ws]
        await manager.broadcast_intel_score(
            symbol="BTC/USDT",
            total_score=72.5,
            bias="bullish",
            components={"funding_rate": 0.25, "cvd": 0.30},
        )
        mock_ws.send_json.assert_called_once()
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["type"] == "intel_score"
        assert call_args["symbol"] == "BTC/USDT"
        assert call_args["total_score"] == 72.5
        assert call_args["bias"] == "bullish"
        assert call_args["components"] == {"funding_rate": 0.25, "cvd": 0.30}

    @pytest.mark.asyncio
    async def test_broadcast_intel_score_default_timestamp(self, manager, mock_ws):
        """timestamp deve essere una stringa ISO."""
        manager.active_connections = [mock_ws]
        await manager.broadcast_intel_score(
            symbol="BTC/USDT", total_score=50.0, bias="neutral",
        )
        call_args = mock_ws.send_json.call_args[0][0]
        assert "timestamp" in call_args
        assert isinstance(call_args["timestamp"], str)

    @pytest.mark.asyncio
    async def test_broadcast_intel_score_empty_components(self, manager, mock_ws):
        """components può essere vuoto o omesso."""
        manager.active_connections = [mock_ws]
        await manager.broadcast_intel_score(
            symbol="BTC/USDT", total_score=30.0, bias="bearish",
        )
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["components"] == {}

    @pytest.mark.asyncio
    async def test_broadcast_intel_score_to_all(self, manager):
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        manager.active_connections = [ws1, ws2]
        await manager.broadcast_intel_score(
            symbol="ETH/USDT", total_score=80.0, bias="bullish",
        )
        assert ws1.send_json.called
        assert ws2.send_json.called