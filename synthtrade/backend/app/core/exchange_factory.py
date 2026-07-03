"""
ExchangeFactory — Provider-neutral exchange adapter factory.

Returns OkxExchangeAdapter or BinanceExchangeAdapter based on EXCHANGE_PROVIDER.
Binance singleton (ccxt.binance) preserved for legacy callers via get_exchange().

TASK-1103/1107: Updated to support OKX as primary provider.
"""

import logging
import ccxt
from app.config import settings

logger = logging.getLogger(__name__)

# ── Legacy Binance singleton (kept for backward compat) ───────────────────────

_exchange: ccxt.binance | None = None
_current_mode: str | None = None


def _build_binance() -> ccxt.binance:
    api_key = settings.binance_api_key
    secret_key = settings.binance_secret_key

    if not api_key or not secret_key:
        logger.warning("Binance API key o secret non configurate")

    exchange = ccxt.binance({
        "apiKey": api_key,
        "secret": secret_key,
        "enableRateLimit": True,
    })

    if settings.TRADING_MODE == "test":
        exchange.set_sandbox_mode(True)
        logger.info("ExchangeFactory: Binance TESTNET creata")
    else:
        logger.info("ExchangeFactory: Binance LIVE creata")

    return exchange


def get_exchange() -> ccxt.binance:
    """Legacy Binance singleton — use get_adapter() for new code."""
    global _exchange, _current_mode

    if _exchange is None or _current_mode != settings.TRADING_MODE:
        _exchange = _build_binance()
        _current_mode = settings.TRADING_MODE

    return _exchange


def reconnect(mode: str | None = None) -> ccxt.binance:
    """Force Binance reconnect (legacy)."""
    global _exchange, _current_mode

    logger.info("ExchangeFactory: riconnessione forzata (mode=%s)", mode or settings.TRADING_MODE)
    _exchange = _build_binance()
    _current_mode = settings.TRADING_MODE
    return _exchange


def reset() -> None:
    """Reset singleton (useful in tests)."""
    global _exchange, _current_mode
    _exchange = None
    _current_mode = None


# ── Provider-neutral adapter factory ─────────────────────────────────────────

def get_adapter():
    """
    Return the exchange adapter for the configured provider.

    Returns OkxExchangeAdapter if EXCHANGE_PROVIDER=okx,
    BinanceExchangeAdapter otherwise.

    This is the preferred entry point for new code.
    """
    provider = settings.EXCHANGE_PROVIDER.lower()

    if provider == "okx":
        from app.execution.okx_exchange import OkxExchangeAdapter
        adapter = OkxExchangeAdapter.from_settings()
        logger.info(
            "ExchangeFactory: OkxExchangeAdapter created (demo=%s, mode=%s)",
            settings.exchange_demo,
            settings.TRADING_MODE,
        )
        return adapter

    # Binance fallback
    from app.execution.exchange import BinanceExchangeAdapter
    adapter = BinanceExchangeAdapter(
        api_key=settings.binance_api_key,
        secret_key=settings.binance_secret_key,
        testnet=(settings.TRADING_MODE == "test"),
    )
    logger.info(
        "ExchangeFactory: BinanceExchangeAdapter created (testnet=%s)",
        settings.TRADING_MODE == "test",
    )
    return adapter


def get_market_ws_client(symbols: list[str]):
    """
    Return the market data WS client for the configured provider.

    Returns OkxWSClient if EXCHANGE_PROVIDER=okx,
    BinanceWSClient otherwise.
    """
    provider = settings.EXCHANGE_PROVIDER.lower()

    if provider == "okx":
        from app.scalping.engine.okx_ws_client import OkxWSClient
        demo = settings.exchange_demo
        return OkxWSClient(symbols=symbols, demo=demo, eu=True)

    from app.scalping.engine.ws_client import BinanceWSClient
    return BinanceWSClient(
        symbols=[s.lower().replace("/", "").replace("-", "") for s in symbols],
        testnet=(settings.TRADING_MODE == "test"),
    )

def get_order_event_stream():
    """
    Return the order event stream for the configured provider.

    Returns OkxOrderEventStream if EXCHANGE_PROVIDER=okx,
    UserDataStreamManager otherwise.
    """
    provider = settings.EXCHANGE_PROVIDER.lower()

    if provider == "okx":
        from app.execution.okx_order_event_stream import OkxOrderEventStream
        return OkxOrderEventStream.from_settings()

    from app.execution.user_data_stream import UserDataStreamManager
    return UserDataStreamManager(
        api_key=settings.binance_api_key,
        api_secret=settings.binance_secret_key,
        testnet=(settings.TRADING_MODE == "test"),
    )
