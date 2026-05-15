from datetime import datetime, UTC
from typing import Literal
from app.db.repositories.trade_repository import TradeRepository
from app.execution.schemas import OrderRequest, OrderResult, PositionSnapshot


class OrderTracker:
    def __init__(self, repo: TradeRepository):
        self.repo = repo

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
        new_trade = self.repo.insert(data)
        return new_trade.id

    def close_position(self, trade_id: str, exit_price: float, pnl_pct: float) -> None:
        self.repo.update(trade_id, {
            "status": "CLOSED",
            "exit_price": exit_price,
            "pnl_pct": pnl_pct,
            "closed_at": datetime.now(UTC).isoformat(),
        })

    def get_open_positions(self, symbol: str | None = None, strategy_id: str | None = None) -> list[PositionSnapshot]:
        """
        Retrieves open positions, optionally filtered by symbol or strategy.
        """
        trades = self.repo.get_open_positions(symbol=symbol, strategy_id=strategy_id)
        return [self._row_to_snapshot(t) for t in trades]

    def get_realized_pnl(self, strategy_id: str) -> float:
        """
        Calculates the total realized PnL in USDT for a strategy by summing
        up (entry_value * pnl_pct) for all its CLOSED trades.
        """
        trades = self.repo.get_closed_trades_by_strategy(strategy_id)
        total_realized = 0.0
        for trade in trades:
            entry_value = trade.price * trade.quantity
            pnl_pct = trade.pnl_pct or 0.0
            total_realized += entry_value * (pnl_pct / 100.0)
        return total_realized

    def update_unrealized_pnl(self, entry_price: float, current_price: float,
                               quantity: float,
                               direction: Literal["BUY", "SELL"]) -> float:
        if direction == "BUY":
            return (current_price - entry_price) * quantity
        return (entry_price - current_price) * quantity

    def _row_to_snapshot(self, trade) -> PositionSnapshot:
        return PositionSnapshot(
            trade_id=trade.id,
            strategy_id=trade.strategy_id,
            symbol=trade.pair,
            direction=trade.action,
            entry_price=trade.price,
            quantity=trade.quantity,
            stop_loss=trade.model_dump().get("stop_loss", 0.0),
            take_profit=trade.model_dump().get("take_profit", 0.0),
            opened_at=trade.executed_at,
        )
