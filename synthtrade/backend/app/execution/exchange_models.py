"""
TASK-1102: Exchange domain models and provider-neutral protocol.

Replaces Binance-specific names (OCO, LOT_SIZE, stepSize) with
SynthTrade domain concepts usable by any exchange adapter.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

from app.execution.exchange import ExchangeOrderError, ExchangeAuthError, ExchangeNetworkError  # noqa: F401 re-export


# ── Type aliases ──────────────────────────────────────────────────────────────

OrderSide = Literal["buy", "sell"]


# ── Errors ────────────────────────────────────────────────────────────────────

class ExitProtectionError(Exception):
    """Raised when exit bracket placement fails and emergency close is triggered."""


class UnsupportedInstrumentError(Exception):
    """Raised when a symbol is not available on the current exchange/mode."""


# ── Domain models ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SymbolRef:
    """Provider-neutral symbol representation."""
    base: str
    quote: str

    @property
    def compact(self) -> str:
        """Binance-style compact ID, e.g. BTCEUR."""
        return f"{self.base}{self.quote}"

    @property
    def ccxt(self) -> str:
        """CCXT slash format, e.g. BTC/EUR."""
        return f"{self.base}/{self.quote}"

    @property
    def okx(self) -> str:
        """OKX instrument ID format, e.g. BTC-EUR."""
        return f"{self.base}-{self.quote}"

    @classmethod
    def from_compact(cls, symbol: str, quote_assets: tuple[str, ...] = ("EUR", "USDC", "USDT", "BTC", "ETH")) -> "SymbolRef":
        """Parse compact symbol like BTCEUR into SymbolRef(base='BTC', quote='EUR')."""
        for q in quote_assets:
            if symbol.upper().endswith(q):
                return cls(base=symbol[: -len(q)].upper(), quote=q)
        raise ValueError(f"Cannot parse compact symbol: {symbol}")

    @classmethod
    def from_ccxt(cls, symbol: str) -> "SymbolRef":
        """Parse CCXT format BTC/EUR."""
        base, quote = symbol.split("/")
        return cls(base=base.upper(), quote=quote.upper())

    @classmethod
    def from_okx(cls, inst_id: str) -> "SymbolRef":
        """Parse OKX instId BTC-EUR."""
        base, quote = inst_id.split("-")
        return cls(base=base.upper(), quote=quote.upper())

    @classmethod
    def from_any(cls, symbol: str) -> "SymbolRef":
        """Parse any common symbol format into SymbolRef.

        Supports:
        - OKX format:  BTC-EUR
        - CCXT format: BTC/EUR
        - Compact:     BTCEUR
        """
        s = symbol.upper().strip()
        if "-" in s:
            base, quote = s.split("-", 1)
            return cls(base=base, quote=quote)
        if "/" in s:
            base, quote = s.split("/", 1)
            return cls(base=base, quote=quote)
        return cls.from_compact(s)

@dataclass
class SymbolRules:
    """Trading rules for a symbol (lot size, tick size, min size)."""
    symbol: SymbolRef
    lot_sz: float        # minimum quantity increment
    min_sz: float        # minimum order size
    tick_sz: float       # minimum price increment
    max_mkt_sz: float    # max market order size (base)
    max_mkt_amt: float   # max market order amount (quote)
    raw: dict[str, Any] = field(default_factory=dict)

    def round_qty(self, qty: float) -> float:
        """Floor qty to lot_sz precision."""
        if self.lot_sz <= 0:
            return qty
        steps = int(qty / self.lot_sz)
        return round(steps * self.lot_sz, 10)

    def round_price(self, price: float) -> float:
        """Round price to tick_sz precision."""
        if self.tick_sz <= 0:
            return price
        steps = round(price / self.tick_sz)
        return round(steps * self.tick_sz, 10)


@dataclass
class FeeTier:
    """Fee tier for a symbol on the current account."""
    maker: float
    taker: float
    certified: bool          # True = fetched from exchange, False = fallback
    source: str = "unknown"  # e.g. "okx_trade_fee", "binance_trade_fee", "fallback"
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class MarketOrderRequest:
    symbol: SymbolRef
    side: OrderSide
    quantity: float = 0.0     # base asset quantity (optional when quote_amount is used)
    quote_amount: float | None = None  # alternative: spend this quote amount
    margin_mode: str | None = None  # "cross" | "isolated" | None=cash (spot)


@dataclass
class ClosePositionRequest:
    symbol: SymbolRef
    side: OrderSide     # side of the POSITION (buy=long -> close with sell)
    quantity: float
    margin_mode: str | None = None  # "cross" | "isolated" | None=cash (spot)


@dataclass
class ExitBracketRequest:
    symbol: SymbolRef
    side: OrderSide     # side of the EXIT orders (opposite of entry)
    quantity: float
    tp_price: float
    sl_price: float
    entry_order_id: str | None = None
    fee_tier: FeeTier | None = None
    margin_mode: str | None = None  # "cross" | "isolated" | None=cash (spot)


@dataclass
class ShortAvailability:
    """TASK-1221: Short availability info for a symbol."""
    available: bool
    borrow_rate_apr: float | None = None
    max_loan_qty: float | None = None
    max_loan_ccy: str | None = None
    mgn_mode: str = "cross"


@dataclass
class MarginPosition:
    """TASK-1222.I: Margin position from OKX /positions?instType=MARGIN."""
    symbol: SymbolRef
    side: OrderSide          # "buy" (long) or "sell" (short)
    quantity: float
    entry_price: float
    mark_price: float
    unrealized_pnl: float
    margin_ratio: float      # mgnRatio from OKX
    pos_ccy: str             # raw posCcy from OKX
    lever: float = 1.0
    mgn_mode: str = "cross"
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class BorrowRecord:
    """TASK-1222.J: Borrow/repay record from OKX quick-margin-borrow-repay-history."""
    ccy: str
    borrow_amount: float
    margin_interest: float
    timestamp: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExchangeOrder:
    """Normalized order result from any exchange."""
    provider: str
    symbol: SymbolRef
    order_id: str
    side: OrderSide
    order_type: str
    status: str
    quantity: float
    filled: float
    average_price: float
    commission: float
    commission_asset: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExitBracketOrder:
    """Result of placing a TP/SL bracket."""
    provider: str
    symbol: SymbolRef
    bracket_id: str
    tp_order_id: str | None
    sl_order_id: str | None
    status: str
    raw: dict[str, Any] = field(default_factory=dict)


# ── Market data events (shared across providers) ─────────────────────────────

@dataclass
class CandleEvent:
    """Candle update from any exchange WS feed."""
    symbol: str
    interval: str
    open_time: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    is_closed: bool
    provider: str = "unknown"


@dataclass
class TradeEvent:
    """Individual trade from any exchange WS feed."""
    symbol: str
    trade_id: int
    price: float
    quantity: float
    is_buyer_maker: bool  # False = aggressive buy, True = aggressive sell
    timestamp: int
    provider: str = "unknown"


@dataclass
class ConnectionStatusEvent:
    symbol: str
    connected: bool
    error: str | None = None
    provider: str = "unknown"


# ── Market data WS protocol ───────────────────────────────────────────────────

@runtime_checkable
class MarketDataWSProtocol(Protocol):
    """Provider-neutral market data WebSocket client."""
    candle_queue: Any
    trade_queue: Any
    status_queue: Any

    async def start(self) -> None: ...
    async def stop(self) -> None: ...


# ── Exchange adapter protocol ─────────────────────────────────────────────────

@runtime_checkable
class ExchangeAdapterProtocol(Protocol):
    """
    TASK-1102: Provider-neutral exchange adapter interface.

    Replaces ExchangeProtocol (Binance-specific).
    BinanceExchangeAdapter and OkxExchangeAdapter both implement this.
    """
    provider: str       # "okx" | "binance"
    trading_mode: str   # "test" | "live"

    async def close(self) -> None: ...

    async def get_balance(self, asset: str) -> float: ...
    async def get_holdings(self) -> dict[str, float]: ...
    async def get_ticker_price(self, symbol: str) -> float: ...

    async def get_symbol_rules(self, symbol: SymbolRef) -> SymbolRules: ...
    async def get_trade_fee(self, symbol: SymbolRef) -> FeeTier: ...

    async def place_market_order(self, request: MarketOrderRequest) -> ExchangeOrder: ...
    async def close_position(self, request: ClosePositionRequest) -> ExchangeOrder: ...

    async def place_exit_bracket(self, request: ExitBracketRequest) -> ExitBracketOrder: ...
    async def get_open_exit_orders(self, symbol: SymbolRef) -> list[ExchangeOrder]: ...
    async def cancel_open_exit_orders(self, symbol: SymbolRef) -> None: ...
    async def get_algo_orders_history(self, symbol: str) -> list[dict[str, Any]]: ...
    # TASK-1186: fetch singolo ordine market per ordId — usato per recuperare avgPx reale post-fill
    async def get_order_by_id(self, symbol: SymbolRef, ord_id: str) -> dict[str, Any]: ...