from dataclasses import dataclass
from typing import Literal
from app.execution.schemas import RiskCheckResult, PositionSnapshot


@dataclass
class RiskConfig:
    max_concurrent_positions: int = 1
    max_exposure_per_symbol_pct: float = 0.10
    max_drawdown_pct: float = 15.0
    default_position_size_pct: float = 0.05
    default_stop_loss_pct: float = 0.02
    default_take_profit_pct: float = 0.04

    @classmethod
    def from_settings(cls, settings):
        """Crea RiskConfig dai Settings dell'app."""
        return cls(
            max_concurrent_positions=settings.MAX_CONCURRENT_POSITIONS,
            max_exposure_per_symbol_pct=settings.MAX_EXPOSURE_PER_SYMBOL_PCT,
            max_drawdown_pct=settings.MAX_DRAWDOWN_PCT,
            default_position_size_pct=settings.DEFAULT_POSITION_SIZE_PCT,
            default_stop_loss_pct=settings.DEFAULT_STOP_LOSS_PCT,
            default_take_profit_pct=settings.DEFAULT_TAKE_PROFIT_PCT,
        )


class RiskManager:
    def __init__(self, config: RiskConfig | None = None):
        self.config = config or RiskConfig()

    def calculate_position_size(self, balance: float, price: float,
                                existing_exposure_eur: float = 0.0) -> float:
        target_eur = balance * self.config.default_position_size_pct
        max_eur = balance * self.config.max_exposure_per_symbol_pct - existing_exposure_eur
        eur = min(target_eur, max(max_eur, 0.0))
        return eur / price if price > 0 else 0.0

    def check_max_positions(self, open_positions: list[PositionSnapshot]) -> RiskCheckResult:
        if len(open_positions) >= self.config.max_concurrent_positions:
            return RiskCheckResult(approved=False,
                                   reason=f"Raggiunto il limite di {self.config.max_concurrent_positions} posizioni aperte")
        return RiskCheckResult(approved=True, reason="OK")

    def check_drawdown(self, current_drawdown_pct: float) -> RiskCheckResult:
        if current_drawdown_pct > self.config.max_drawdown_pct:
            return RiskCheckResult(approved=False,
                                   reason=f"Drawdown {current_drawdown_pct:.1f}% supera il limite {self.config.max_drawdown_pct:.1f}%")
        return RiskCheckResult(approved=True, reason="OK")

    def check_max_daily_loss(self, daily_pnl_pct: float,
                             max_daily_loss_pct: float | None = None) -> RiskCheckResult:
        """
        TASK-801: Controllo intraday — perdita massima giornaliera.

        Blocca il trading se la perdita del giorno supera la soglia configurata.
        """
        threshold = max_daily_loss_pct if max_daily_loss_pct is not None else self.config.max_drawdown_pct
        if daily_pnl_pct < -threshold:
            return RiskCheckResult(
                approved=False,
                reason=f"Perdita giornaliera {daily_pnl_pct:.1f}% supera la soglia {threshold:.1f}%"
            )
        return RiskCheckResult(approved=True, reason="OK")

    def check_max_consecutive_losses(self, consecutive_losses: int,
                                     max_consecutive_losses: int | None = None) -> RiskCheckResult:
        """
        TASK-801: Controllo intraday — perdite consecutive massime.

        Blocca il trading se il numero di perdite consecutive supera la soglia configurata.
        """
        threshold = max_consecutive_losses if max_consecutive_losses is not None else self.config.max_concurrent_positions
        if consecutive_losses > threshold:
            return RiskCheckResult(
                approved=False,
                reason=f"{consecutive_losses} perdite consecutive superano la soglia {threshold}"
            )
        return RiskCheckResult(approved=True, reason="OK")

    def calculate_stop_loss_price(self, entry_price: float,
                                  direction: Literal["BUY", "SELL"]) -> float:
        pct = self.config.default_stop_loss_pct
        return entry_price * (1 - pct) if direction == "BUY" else entry_price * (1 + pct)

    def calculate_take_profit_price(self, entry_price: float,
                                    direction: Literal["BUY", "SELL"]) -> float:
        pct = self.config.default_take_profit_pct
        return entry_price * (1 + pct) if direction == "BUY" else entry_price * (1 - pct)

    def validate_signal(self, signal, balance: float,
                        open_positions: list[PositionSnapshot],
                        current_drawdown_pct: float,
                        daily_pnl_pct: float | None = None,
                        consecutive_losses: int | None = None,
                        max_daily_loss_pct: float | None = None,
                        max_consecutive_losses: int | None = None) -> RiskCheckResult:
        drawdown_check = self.check_drawdown(current_drawdown_pct)
        if not drawdown_check.approved:
            return drawdown_check

        positions_check = self.check_max_positions(open_positions)
        if not positions_check.approved:
            return positions_check

        # TASK-801: Controlli intraday
        if daily_pnl_pct is not None:
            daily_check = self.check_max_daily_loss(daily_pnl_pct, max_daily_loss_pct)
            if not daily_check.approved:
                return daily_check

        if consecutive_losses is not None:
            consec_check = self.check_max_consecutive_losses(consecutive_losses, max_consecutive_losses)
            if not consec_check.approved:
                return consec_check

        size = self.calculate_position_size(balance, signal.price)
        sl = self.calculate_stop_loss_price(signal.price, signal.direction)
        tp = self.calculate_take_profit_price(signal.price, signal.direction)

        return RiskCheckResult(approved=True, reason="OK",
                               position_size=size, stop_loss_price=sl,
                               take_profit_price=tp)
