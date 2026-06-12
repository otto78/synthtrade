"""PositionManager - gestisce posizioni aperte."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class PositionStatus(str, Enum):
    """Status della posizione."""
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


@dataclass
class Position:
    """Rappresenta una posizione aperta."""
    symbol: str
    side: str  # 'BUY' or 'SELL'
    entry_price: Decimal
    quantity: Decimal
    entry_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    status: PositionStatus = PositionStatus.OPEN
    order_id: Optional[str] = None
    oco_id: Optional[str] = None
    sl_id: Optional[str] = None
    tp_id: Optional[str] = None
    # FIX-2026-06-12: Campi per User Data Stream (match ordini Binance)
    oco_order_list_id: Optional[str] = None  # orderListId dell'OCO
    sl_order_id: Optional[str] = None        # orderId dello STOP_LOSS (da orderReports)
    tp_order_id: Optional[str] = None        # orderId del LIMIT_MAKER (da orderReports)


class PositionManager:
    """Gestisce le posizioni aperte per lo scalping."""

    def __init__(self):
        self._positions: List[Position] = []

    def has_open(self) -> bool:
        """Verifica se c'e' una posizione aperta."""
        return any(p.status == PositionStatus.OPEN for p in self._positions)

    def get_open(self) -> Optional[Position]:
        """Restituisce l'eventuale posizione aperta."""
        for p in reversed(self._positions):
            if p.status == PositionStatus.OPEN:
                return p
        return None

    def open_position(
        self,
        symbol: str,
        side: str,
        entry_price: Decimal,
        quantity: Decimal,
        order_id: Optional[str] = None,
    ) -> Position:
        """Apre una nuova posizione."""
        position = Position(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            quantity=quantity,
            order_id=order_id,
        )
        self._positions.append(position)
        return position

    def close_position(
        self,
        exit_price: Decimal,
        order_id: Optional[str] = None,
    ) -> Optional[Position]:
        """Chiude l'eventuale posizione aperta."""
        pos = self.get_open()
        if pos:
            pos.status = PositionStatus.CLOSED
            return pos
        return None

    def set_stop_loss(self, sl: Decimal) -> None:
        """Imposta stop loss sulla posizione aperta."""
        pos = self.get_open()
        if pos:
            pos.stop_loss = sl

    def set_take_profit(self, tp: Decimal) -> None:
        """Imposta take profit sulla posizione aperta."""
        pos = self.get_open()
        if pos:
            pos.take_profit = tp

    def force_close_all(self, exit_price: Decimal) -> int:
        """Chiude forzatamente TUTTE le posizioni aperte.
        
        Args:
            exit_price: Prezzo di chiusura per tutte le posizioni aperte.
            
        Returns:
            int: Numero di posizioni chiuse.
        """
        closed_count = 0
        for pos in self._positions:
            if pos.status == PositionStatus.OPEN:
                pos.status = PositionStatus.CLOSED
                closed_count += 1
        if closed_count > 0:
            logger.info(f"Force closed {closed_count} position(s) @ {exit_price}")
        return closed_count

    def get_all(self) -> List[Position]:
        """Restituisce tutte le posizioni."""
        return self._positions.copy()
