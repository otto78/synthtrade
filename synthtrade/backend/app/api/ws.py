from fastapi import APIRouter, WebSocket
from app.core.auth_utils import verify_token

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active_connections.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active_connections:
            self.active_connections.remove(ws)

    async def broadcast(self, message: dict):
        for ws in list(self.active_connections):
            await ws.send_json(message)

    async def broadcast_price(self, pair: str, price: float):
        await self.broadcast({"type": "price", "pair": pair, "price": price})

    async def broadcast_engine_status(self, status: str):
        await self.broadcast({"type": "engine_status", "status": status})


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket, token: str | None = None):
    if not token or not verify_token(token):
        await ws.accept()
        await ws.send_json({"type": "error", "code": 1008, "detail": "Unauthorized"})
        await ws.close(code=1008)
        return

    await manager.connect(ws)
    try:
        await ws.send_json({"type": "ping"})
        while True:
            await ws.receive_text()
    except Exception:
        manager.disconnect(ws)
