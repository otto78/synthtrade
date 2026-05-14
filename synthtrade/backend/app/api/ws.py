from fastapi import APIRouter, WebSocket
from app.core.auth_utils import verify_token
from app.execution.schemas import PositionSnapshot

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

    # TASK-414: Nuovi broadcast per trade e strategia
    async def broadcast_trade_opened(self, strategy_id: str, trade_id: str,
                                     symbol: str, direction: str, price: float,
                                     quantity: float):
        await self.broadcast({
            "type": "trade_opened",
            "strategy_id": strategy_id,
            "trade_id": trade_id,
            "symbol": symbol,
            "direction": direction,
            "price": price,
            "quantity": quantity,
        })

    async def broadcast_trade_closed(self, strategy_id: str, trade_id: str,
                                     pnl_pct: float, exit_price: float):
        await self.broadcast({
            "type": "trade_closed",
            "strategy_id": strategy_id,
            "trade_id": trade_id,
            "pnl_pct": round(pnl_pct, 4),
            "exit_price": exit_price,
        })

    async def broadcast_strategy_stopped(self, strategy_id: str,
                                         final_pnl_pct: float,
                                         final_value_usdt: float):
        await self.broadcast({
            "type": "strategy_stopped",
            "strategy_id": strategy_id,
            "final_pnl_pct": round(final_pnl_pct, 4),
            "final_value_usdt": round(final_value_usdt, 2),
        })

    async def broadcast_strategy_pnl_updated(self, strategy_id: str,
                                              current_pnl_pct: float,
                                              current_pnl_eur: float,
                                              current_value_usdt: float):
        await self.broadcast({
            "type": "strategy_pnl_updated",
            "strategy_id": strategy_id,
            "current_pnl_pct": round(current_pnl_pct, 4),
            "current_pnl_eur": round(current_pnl_eur, 2),
            "current_value_usdt": round(current_value_usdt, 2),
        })


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