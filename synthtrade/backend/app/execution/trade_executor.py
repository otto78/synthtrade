from app.execution.schemas import OrderRequest, OrderResult
from app.execution.order_tracker import OrderTracker

class TradeExecutor:
    def __init__(self, exchange, order_tracker: OrderTracker):
        self.exchange = exchange
        self.order_tracker = order_tracker

    async def execute_order(self, request: OrderRequest) -> str:
        result: OrderResult = await self.exchange.place_order(request)
        if result.status == "FILLED":
            return self.order_tracker.open_position(request, result)
        raise Exception(f"Order not filled: {result.status}")

    async def close_position(self, position, exit_price: float, pnl_pct: float) -> None:
        await self.exchange.close_position(
            symbol=position.symbol,
            side=position.direction,
            quantity=position.quantity
        )
        self.order_tracker.close_position(position.trade_id, exit_price, pnl_pct)
