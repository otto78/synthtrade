"""
TASK-1107: Exchange factory — provider-neutral adapter and WS client creation.

Reads EXCHANGE_PROVIDER from settings and returns the correct adapter/WS pair.
Supports: 'okx' | 'binance' (legacy).

Usage:
    from app.execution.exchange_factory import build_exchange_adapter, build_ws_client, build_order_stream

    adapter = build_exchange_adapter()
    ws_client = build_ws_client(symbols=["BTC-EUR"], demo=True)
    order_stream = build_order_stream()
"""
from __future__ import annotations

import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


def build_exchange_adapter() -> Any:
    """
    Build and return the correct exchange adapter based on EXCHANGE_PROVIDER.

    Returns an OkxExchangeAdapter or BinanceExchangeAdapter.
    Both implement ExchangeAdapterProtocol.
    """
    provider = settings.EXCHANGE_PROVIDER.lower()

    if provider == "okx":
        from app.execution.okx_exchange import OkxExchangeAdapter
        adapter = OkxExchangeAdapter(
            api_key=settings.exchange_api_key,
            secret=settings.exchange_secret_key,
            passphrase=settings.exchange_passphrase,
            demo=settings.exchange_demo,
            base_url=settings.OKX_BASE_URL,
        )
        logger.info(
            "[FACTORY] ExchangeAdapter: OKX | demo=%s | base_url=%s",
            settings.exchange_demo, settings.OKX_BASE_URL,
        )
        return adapter

    elif provider == "binance":
        from app.execution.exchange import BinanceExchangeAdapter
        is_testnet = settings.TRADING_MODE == "test"
        adapter = BinanceExchangeAdapter(
            api_key=settings.exchange_api_key,
            secret=settings.exchange_secret_key,
            testnet=is_testnet,
        )
        logger.info("[FACTORY] ExchangeAdapter: Binance | testnet=%s", is_testnet)
        return adapter

    else:
        raise ValueError(f"Unknown EXCHANGE_PROVIDER: {provider!r}. Must be 'okx' or 'binance'.")


def build_ws_client(symbols: list[str]) -> Any:
    """
    Build and return the correct market data WS client based on EXCHANGE_PROVIDER.

    For OKX: returns OkxWSClient (uses OKX instId format, e.g. BTC-EUR).
    For Binance: returns BinanceWSClient (uses compact format, e.g. btcusdt).

    Args:
        symbols: List of symbols in whatever format — will be normalized internally.
    """
    provider = settings.EXCHANGE_PROVIDER.lower()

    if provider == "okx":
        from app.scalping.engine.okx_ws_client import OkxWSClient
        # OkxWSClient accepts both BTC/EUR and BTC-EUR, normalizes to OKX instId
        is_demo = settings.exchange_demo
        client = OkxWSClient(symbols=symbols, demo=is_demo, eu=True)
        logger.info("[FACTORY] WSClient: OkxWSClient | symbols=%s | demo=%s", symbols, is_demo)
        return client

    elif provider == "binance":
        from app.scalping.engine.ws_client import BinanceWSClient
        is_testnet = settings.TRADING_MODE == "test"
        # BinanceWSClient expects lowercase compact format
        compact_symbols = [s.lower().replace("-", "").replace("/", "") for s in symbols]
        client = BinanceWSClient(symbols=compact_symbols, testnet=is_testnet)
        logger.info("[FACTORY] WSClient: BinanceWSClient | symbols=%s | testnet=%s", compact_symbols, is_testnet)
        return client

    else:
        raise ValueError(f"Unknown EXCHANGE_PROVIDER: {provider!r}.")


def build_order_stream() -> Any:
    """
    Build and return the correct order event stream based on EXCHANGE_PROVIDER.

    For OKX live: returns OkxOrderEventStream (subscribes to orders + algo-orders WS).
    For Binance live: returns UserDataStreamManager.
    For OKX demo: returns OkxOrderEventStream in demo mode.
    For paper mode: returns None (no real order stream needed).
    """
    provider = settings.EXCHANGE_PROVIDER.lower()
    is_live = settings.TRADING_MODE == "live"

    if provider == "okx":
        from app.execution.okx_order_event_stream import OkxOrderEventStream
        stream = OkxOrderEventStream(
            api_key=settings.exchange_api_key,
            secret=settings.exchange_secret_key,
            passphrase=settings.exchange_passphrase,
            demo=settings.exchange_demo,
            eu=True,
        )
        logger.info(
            "[FACTORY] OrderStream: OkxOrderEventStream | demo=%s", settings.exchange_demo
        )
        return stream

    elif provider == "binance":
        if not is_live:
            logger.info("[FACTORY] OrderStream: None (Binance paper/test mode)")
            return None
        from app.execution.user_data_stream import UserDataStreamManager
        stream = UserDataStreamManager(
            api_key=settings.BINANCE_API_KEY_LIVE or settings.BINANCE_API_KEY,
            secret=settings.BINANCE_SECRET_KEY_LIVE or settings.BINANCE_SECRET_KEY,
            testnet=False,
        )
        logger.info("[FACTORY] OrderStream: UserDataStreamManager (Binance live)")
        return stream

    else:
        raise ValueError(f"Unknown EXCHANGE_PROVIDER: {provider!r}.")


def normalize_symbol_for_provider(symbol: str) -> str:
    """
    Normalize a symbol string to the format expected by the current provider.

    OKX: BTC-EUR (OKX instId format)
    Binance: BTCEUR (compact uppercase)
    """
    provider = settings.EXCHANGE_PROVIDER.lower()
    # Remove any existing separators and split
    clean = symbol.upper().replace("-", "").replace("/", "")

    if provider == "okx":
        # Need to re-insert the hyphen — use common quote assets
        for q in ("EUR", "USDC", "USDT", "BTC", "ETH", "USD"):
            if clean.endswith(q):
                base = clean[: -len(q)]
                return f"{base}-{q}"
        return clean  # fallback: return as-is

    else:  # binance
        return clean.lower()


def get_symbol_for_ws(symbol: str) -> str:
    """Return symbol in the format expected by the WS client for the active provider."""
    return normalize_symbol_for_provider(symbol)
