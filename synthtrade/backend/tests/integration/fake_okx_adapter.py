"""
TASK-1111: Fake OKX adapter and order stream for integration tests.

Implements ExchangeAdapterProtocol and the order stream interface
without any network calls. Designed to be injected into _execution_state
to test the full scalping flow (entry → bracket → fill → close) in isolation.

Usage in tests:
    adapter = FakeOkxAdapter()
    order_stream = FakeOrderStream()
    # inject into router state and trigger scenarios
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from app.execution.exchange_models import (
    ClosePositionRequest,
    ExchangeOrder,
    ExitBracketOrder,
    ExitBracketRequest,
    ExitProtectionError,
    FeeTier,
    MarketOrderRequest,
    SymbolRef,
    SymbolRules,
)


# ── Constants ─────────────────────────────────────────────────────────────────

BTC_EUR = SymbolRef(base="BTC", quote="EUR")

FAKE_RULES = SymbolRules(
    symbol=BTC_EUR,
    lot_sz=0.00001,
    min_sz=0.00001,
    tick_sz=0.1,
    max_mkt_sz=100.0,
    max_mkt_amt=1_000_000.0,
)

FAKE_FEE = FeeTier(
    maker=-0.002,   # -0.2% rebate (OKX-style)
    taker=-0.0035,  # -0.35% rebate
    certified=True,
    source="fake_okx",
)


# ── Fake adapter ──────────────────────────────────────────────────────────────

@dataclass
class FakeOkxAdapter:
    """
    Fake OKX exchange adapter implementing ExchangeAdapterProtocol.

    Tracks all calls so tests can assert what was invoked.
    Configurable failure modes: bracket_fails, close_fails.
    """

    provider: str = "okx"
    trading_mode: str = "test"

    # Balances
    balances: dict[str, float] = field(default_factory=lambda: {"EUR": 1000.0, "BTC": 0.0})
    holdings_data: dict[str, float] = field(default_factory=lambda: {"EUR": 1000.0})

    # Config for simulated market price
    last_price: float = 43700.0

    # Failure flags
    bracket_fails: bool = False
    close_fails: bool = False
    market_order_fails: bool = False

    # Open bracket tracking
    open_brackets: dict[str, dict] = field(default_factory=dict)

    # Call log
    calls: list[str] = field(default_factory=list)
    placed_orders: list[ExchangeOrder] = field(default_factory=list)
    placed_brackets: list[ExitBracketOrder] = field(default_factory=list)
    cancelled_orders: list[SymbolRef] = field(default_factory=list)
    closed_positions: list[ClosePositionRequest] = field(default_factory=list)

    # Auto-increment order id counter
    _order_counter: int = field(default=1, repr=False)

    def _next_id(self) -> str:
        oid = f"fake-order-{self._order_counter:04d}"
        self._order_counter += 1
        return oid

    # ── Protocol methods ─────────────────────────────────────────────────────

    async def close(self) -> None:
        self.calls.append("close")

    async def get_balance(self, asset: str = "EUR") -> float:
        self.calls.append(f"get_balance({asset})")
        return self.balances.get(asset, 0.0)

    async def get_holdings(self) -> dict[str, float]:
        self.calls.append("get_holdings")
        return dict(self.holdings_data)

    async def get_ticker_price(self, symbol: str) -> float:
        self.calls.append(f"get_ticker_price({symbol})")
        return self.last_price

    async def get_symbol_rules(self, symbol: SymbolRef) -> SymbolRules:
        self.calls.append(f"get_symbol_rules({symbol.okx})")
        return FAKE_RULES

    async def get_trade_fee(self, symbol: SymbolRef) -> FeeTier:
        self.calls.append(f"get_trade_fee({symbol.okx})")
        return FAKE_FEE

    async def place_market_order(self, request: MarketOrderRequest) -> ExchangeOrder:
        self.calls.append(f"place_market_order({request.side},{request.symbol.okx})")
        if self.market_order_fails:
            from app.execution.exchange_models import ExchangeOrderError  # type: ignore[attr-defined]
            raise Exception("FakeOkxAdapter: market_order_fails=True")

        oid = self._next_id()
        qty = request.quantity or (request.quote_amount or 10.0) / self.last_price
        qty = round(qty, 8)

        # Update balances
        if request.side == "buy":
            self.balances["EUR"] = max(0.0, self.balances.get("EUR", 0.0) - self.last_price * qty)
            self.balances["BTC"] = self.balances.get("BTC", 0.0) + qty
            self.holdings_data["BTC"] = self.holdings_data.get("BTC", 0.0) + qty
        else:
            self.balances["BTC"] = max(0.0, self.balances.get("BTC", 0.0) - qty)
            self.holdings_data["BTC"] = max(0.0, self.holdings_data.get("BTC", 0.0) - qty)
            self.balances["EUR"] = self.balances.get("EUR", 0.0) + self.last_price * qty

        order = ExchangeOrder(
            provider="okx",
            symbol=request.symbol,
            order_id=oid,
            side=request.side,
            order_type="market",
            status="closed",
            quantity=qty,
            filled=qty,
            average_price=self.last_price,
            commission=0.0,
            commission_asset="EUR",
            raw={"fake": True},
        )
        self.placed_orders.append(order)
        return order

    async def close_position(self, request: ClosePositionRequest) -> ExchangeOrder:
        self.calls.append(f"close_position({request.side},{request.symbol.okx})")
        if self.close_fails:
            raise Exception("FakeOkxAdapter: close_fails=True")
        self.closed_positions.append(request)
        return await self.place_market_order(
            MarketOrderRequest(
                symbol=request.symbol,
                side="sell" if request.side.upper() == "BUY" else "buy",
                quantity=request.quantity,
            )
        )

    async def place_exit_bracket(self, request: ExitBracketRequest) -> ExitBracketOrder:
        self.calls.append(
            f"place_exit_bracket({request.symbol.okx},tp={request.tp_price},sl={request.sl_price})"
        )
        if self.bracket_fails:
            # Trigger emergency close path
            raise Exception("FakeOkxAdapter: bracket_fails=True")

        algo_id = f"algo-{self._next_id()}"
        bracket = ExitBracketOrder(
            provider="okx",
            symbol=request.symbol,
            bracket_id=algo_id,
            tp_order_id=f"tp-{algo_id}",
            sl_order_id=f"sl-{algo_id}",
            status="placed",
            raw={"fake": True},
        )
        self.open_brackets[algo_id] = {
            "tp_price": request.tp_price,
            "sl_price": request.sl_price,
            "qty": request.quantity,
            "symbol": request.symbol,
        }
        self.placed_brackets.append(bracket)
        return bracket

    async def get_open_exit_orders(self, symbol: SymbolRef) -> list[ExchangeOrder]:
        self.calls.append(f"get_open_exit_orders({symbol.okx})")
        return [
            ExchangeOrder(
                provider="okx",
                symbol=symbol,
                order_id=bid,
                side="sell",
                order_type="oco",
                status="open",
                quantity=info["qty"],
                filled=0.0,
                average_price=0.0,
                commission=0.0,
                commission_asset="EUR",
                raw=info,
            )
            for bid, info in self.open_brackets.items()
            if info["symbol"] == symbol
        ]

    async def cancel_open_exit_orders(self, symbol: SymbolRef) -> None:
        self.calls.append(f"cancel_open_exit_orders({symbol.okx})")
        # Remove brackets for this symbol
        to_remove = [
            bid for bid, info in self.open_brackets.items()
            if info["symbol"] == symbol
        ]
        for bid in to_remove:
            del self.open_brackets[bid]
        self.cancelled_orders.append(symbol)

    # ── Intelligence collector adapters (TASK-1153) ─────────────────────────────
    # Read-only perpetual data consumed by OpenInterestCollector / FundingRateCollector
    # when EXCHANGE_PROVIDER=okx. Configurable so tests can assert OKX-native calls.

    async def get_open_interest(self, base_asset: str) -> Optional[float]:
        self.calls.append(f"get_open_interest({base_asset})")
        return getattr(self, "open_interest_value", None)

    async def get_funding_rate(self, base_asset: str) -> Optional[float]:
        self.calls.append(f"get_funding_rate({base_asset})")
        return getattr(self, "funding_rate_value", None)

    async def get_long_short_ratio(self, base_asset: str, period: str = "5m") -> Optional[float]:
        self.calls.append(f"get_long_short_ratio({base_asset})")
        return getattr(self, "long_short_ratio_value", None)

    # ── Test helpers ─────────────────────────────────────────────────────────

    def reset_calls(self) -> None:
        self.calls.clear()
        self.placed_orders.clear()
        self.placed_brackets.clear()
        self.cancelled_orders.clear()
        self.closed_positions.clear()

    def simulate_tp_fill(self, bracket: ExitBracketOrder) -> dict:
        """Generate a fake TP fill event compatible with _on_order_update."""
        info = self.open_brackets.get(bracket.bracket_id, {})
        return {
            "provider": "okx",
            "symbol": bracket.symbol.okx,
            "side": "SELL",
            "order_id": bracket.tp_order_id,
            "bracket_id": bracket.bracket_id,
            "order_list_id": bracket.bracket_id,
            "status": "filled",
            "fill_price": info.get("tp_price", self.last_price * 1.005),
            "commission": 0.0,
            "commission_asset": "EUR",
            "leg": "take_profit",
        }

    def simulate_sl_fill(self, bracket: ExitBracketOrder) -> dict:
        """Generate a fake SL fill event compatible with _on_order_update."""
        info = self.open_brackets.get(bracket.bracket_id, {})
        return {
            "provider": "okx",
            "symbol": bracket.symbol.okx,
            "side": "SELL",
            "order_id": bracket.sl_order_id,
            "bracket_id": bracket.bracket_id,
            "order_list_id": bracket.bracket_id,
            "status": "filled",
            "fill_price": info.get("sl_price", self.last_price * 0.997),
            "commission": 0.0,
            "commission_asset": "EUR",
            "leg": "stop_loss",
        }


# ── Fake order stream ─────────────────────────────────────────────────────────

class FakeOrderStream:
    """
    Fake OKX order event stream.

    Stores the callbacks registered via start() so tests can trigger
    fill events manually with fire_fill(event_dict).
    """

    def __init__(self) -> None:
        self._on_order_update: Optional[Callable] = None
        self._on_reconnect_sync: Optional[Callable] = None
        self.started: bool = False
        self.stopped: bool = False
        self.fired_events: list[dict] = []

    async def start(
        self,
        on_order_update: Callable,
        on_reconnect_sync: Optional[Callable] = None,
    ) -> None:
        self._on_order_update = on_order_update
        self._on_reconnect_sync = on_reconnect_sync
        self.started = True

    async def stop(self) -> None:
        self.stopped = True

    async def fire_fill(self, event: dict) -> None:
        """Trigger a fill event as if it came from OKX WebSocket."""
        self.fired_events.append(event)
        if self._on_order_update:
            await self._on_order_update(event)

    async def fire_reconnect(self) -> None:
        """Simulate a WS reconnect sync callback."""
        if self._on_reconnect_sync:
            await self._on_reconnect_sync()
