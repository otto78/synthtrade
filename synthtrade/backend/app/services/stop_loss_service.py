from typing import Literal

class StopLossService:
    def calculate_price(self, entry_price: float, direction: Literal["BUY", "SELL"], pct: float) -> float:
        if direction == "BUY":
            return entry_price * (1 - pct)
        return entry_price * (1 + pct)

    def is_hit(self, current_price: float, sl_price: float, direction: Literal["BUY", "SELL"]) -> bool:
        if direction == "BUY":
            return current_price <= sl_price
        return current_price >= sl_price
