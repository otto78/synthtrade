from datetime import datetime, UTC
from typing import Literal
from app.db.supabase_client import get_supabase
from app.execution.schemas import OrderRequest, OrderResult, PositionSnapshot


class OrderTracker:
    def __init__(self):
        self.db = get_supabase()

    def open_position(self, request: OrderRequest, result: OrderResult) -> str:
        data = {
            "strategy_id": request.strategy_id,
            "pair": request.symbol,
            "action": request.direction,
            "price": result.price,
            "quantity": result.quantity,
            "stop_loss": request.stop_loss,
            "take_profit": request.take_profit,
            "status": "OPEN",
            "paper": request.paper,
            "executed_at": datetime.now(UTC).isoformat(),
        }
        res = self.db.table("trades").insert(data).execute()
        return res.data[0]["id"]

    def close_position(self, trade_id: str, exit_price: float, pnl_pct: float) -> None:
        self.db.table("trades").update({
            "status": "CLOSED",
            "exit_price": exit_price,
            "pnl_pct": pnl_pct,
            "closed_at": datetime.now(UTC).isoformat(),
        }).eq("id", trade_id).execute()

    def get_open_positions(self, symbol: str | None = None) -> list[PositionSnapshot]:
        query = self.db.table("trades").select("*").eq("status", "OPEN")
        if symbol:
            query = self.db.table("trades").select("*").eq("status", "OPEN")
            res = query.execute()
            rows = [r for r in res.data if r.get("pair") == symbol]
        else:
            res = query.execute()
            rows = res.data

        return [self._row_to_snapshot(r) for r in rows]

    def update_unrealized_pnl(self, entry_price: float, current_price: float,
                               quantity: float,
                               direction: Literal["BUY", "SELL"]) -> float:
        if direction == "BUY":
            return (current_price - entry_price) * quantity
        return (entry_price - current_price) * quantity

    def _row_to_snapshot(self, row: dict) -> PositionSnapshot:
        return PositionSnapshot(
            trade_id=row["id"],
            strategy_id=row["strategy_id"],
            symbol=row["pair"],
            direction=row["action"],
            entry_price=row["price"],
            quantity=row["quantity"],
            stop_loss=row.get("stop_loss", 0.0),
            take_profit=row.get("take_profit", 0.0),
            opened_at=datetime.fromisoformat(row["executed_at"]),
        )
