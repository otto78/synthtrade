import logging
from app.execution.schemas import (
    Signal, OrderRequest, OrderResult, RiskCheckResult, PositionSnapshot
)
from app.execution.risk_manager import RiskManager
from app.execution.order_tracker import OrderTracker
from app.services.stop_loss_service import StopLossService
from app.execution.signal_resolver import SignalResolverProtocol, DefaultSignalResolver

class ExecutionEngine:
    def __init__(self, risk_manager: RiskManager, order_tracker: OrderTracker,
                 exchange, sl_service: StopLossService, logger=None, 
                 signal_resolver: SignalResolverProtocol = None):
        self.risk_manager = risk_manager
        self.order_tracker = order_tracker
        self.exchange = exchange
        self.sl_service = sl_service
        self.logger = logger or logging.getLogger(__name__)
        self.signal_resolver = signal_resolver or DefaultSignalResolver()

    async def _broadcast_trade_opened(self, strategy_id: str, trade_id: str,
                                      symbol: str, direction: str, price: float,
                                      quantity: float):
        try:
            from app.api.ws import manager
            await manager.broadcast_trade_opened(
                strategy_id=strategy_id,
                trade_id=trade_id,
                symbol=symbol,
                direction=direction,
                price=price,
                quantity=quantity
            )
        except Exception as e:
            self.logger.warning(f"Failed to broadcast trade_opened: {e}")

    async def _broadcast_trade_closed(self, strategy_id: str, trade_id: str,
                                      pnl_pct: float, exit_price: float):
        try:
            from app.api.ws import manager
            await manager.broadcast_trade_closed(
                strategy_id=strategy_id,
                trade_id=trade_id,
                pnl_pct=pnl_pct,
                exit_price=exit_price
            )
        except Exception as e:
            self.logger.warning(f"Failed to broadcast trade_closed: {e}")

    async def process_signals(self, signals: list[Signal], balance: float,
                              current_drawdown_pct: float) -> None:
        """
        TASK-217: Processa una lista di segnali risolvendoli tramite il resolver.
        """
        if not signals:
            return

        # Recupera tutte le posizioni aperte per il contesto di risoluzione
        open_positions = self.order_tracker.get_open_positions()
        
        # Risoluzione segnali (filtro/priorità)
        resolved_signals = self.signal_resolver.resolve(signals, open_positions)
        
        for signal in resolved_signals:
            # Filtra le posizioni per il simbolo specifico per il risk manager
            symbol_positions = [p for p in open_positions if p.symbol == signal.symbol]
            await self.process_signal(
                signal=signal,
                balance=balance,
                open_positions=symbol_positions,
                current_drawdown_pct=current_drawdown_pct
            )

    async def process_signal(self, signal: Signal, balance: float,
                             open_positions: list[PositionSnapshot],
                             current_drawdown_pct: float) -> None:
        check: RiskCheckResult = self.risk_manager.validate_signal(
            signal=signal, balance=balance,
            open_positions=open_positions,
            current_drawdown_pct=current_drawdown_pct,
        )

        if not check.approved:
            self.logger.info(f"Signal rejected: {check.reason}")
            return

        request = OrderRequest(
            strategy_id=signal.strategy_id,
            symbol=signal.symbol,
            direction=signal.direction,
            quantity=check.position_size,
            price=signal.price,
            stop_loss=check.stop_loss_price,
            take_profit=check.take_profit_price,
        )

        try:
            result: OrderResult = await self.exchange.place_order(request)
        except Exception as e:
            self.logger.error(f"Exchange error on place_order: {e}")
            return

        if result.status == "FILLED":
            trade_id = self.order_tracker.open_position(request, result)
            self.logger.info(f"Position opened: {result.order_id}")
            # TASK-414: Broadcast real-time
            await self._broadcast_trade_opened(
                strategy_id=signal.strategy_id,
                trade_id=trade_id,
                symbol=signal.symbol,
                direction=signal.direction,
                price=result.price or signal.price,
                quantity=result.quantity or check.position_size
            )
        else:
            self.logger.warning(f"Order not filled: {result.status} — {result.message}")

    def check_exit_conditions(self, position: PositionSnapshot,
                              current_price: float) -> bool:
        sl_hit = self.sl_service.is_hit(current_price, position.stop_loss, position.direction)
        if position.direction == "BUY":
            return sl_hit or current_price >= position.take_profit
        return sl_hit or current_price <= position.take_profit

    async def close_position_if_needed(self, position: PositionSnapshot,
                                       current_price: float) -> None:
        if not self.check_exit_conditions(position, current_price):
            return
        try:
            result: OrderResult = await self.exchange.close_order(position)
            pnl_pct = ((current_price - position.entry_price) / position.entry_price * 100
                       if position.direction == "BUY"
                       else (position.entry_price - current_price) / position.entry_price * 100)
            self.order_tracker.close_position(position.trade_id, current_price, pnl_pct)
            self.logger.info(f"Position closed: {position.trade_id} pnl={pnl_pct:.2f}%")
            # TASK-414: Broadcast real-time
            await self._broadcast_trade_closed(
                strategy_id=position.strategy_id,
                trade_id=position.trade_id,
                pnl_pct=pnl_pct,
                exit_price=current_price
            )
        except Exception as e:
            self.logger.error(f"Exchange error on close_order: {e}")
