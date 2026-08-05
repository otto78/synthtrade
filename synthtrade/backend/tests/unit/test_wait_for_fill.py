"""Tests for candle_processor._wait_for_fill (OKX async fill polling).

Verifica che il polling attenda il fill reale del market order prima che il
bracket venga piazzato (fix sCode 51008). Nessuna chiamata di rete.
"""
from __future__ import annotations

import asyncio
import time

from app.scalping.candle_processor import _wait_for_fill
from app.execution.exchange_models import SymbolRef


class _FakeExchange:
    """Fake adapter con get_order_by_id che riproduce il fill asincrono OKX."""

    def __init__(self, sequence):
        self.sequence = list(sequence)
        self.calls = 0

    async def get_order_by_id(self, symbol, ord_id):
        self.calls += 1
        return self.sequence[min(self.calls - 1, len(self.sequence) - 1)]


class _NoPollExchange:
    """Adapter senza get_order_by_id (es. Binance legacy) — polling saltato."""


async def test_returns_real_fill_on_first_poll():
    exchange = _FakeExchange([{"state": "filled", "accFillSz": "0.00035957", "avgPx": "55630.2"}])
    price, qty = await _wait_for_fill(exchange, SymbolRef.from_okx("BTC-EUR"), "ord1", 55620.1, 0.00035958)
    assert price == 55630.2
    assert qty == 0.00035957
    assert exchange.calls == 1


async def test_waits_until_filled():
    exchange = _FakeExchange([
        {"state": "live", "accFillSz": "0", "avgPx": ""},
        {"state": "live", "accFillSz": "0", "avgPx": ""},
        {"state": "filled", "accFillSz": "0.0003595", "avgPx": "55632.5"},
    ])
    price, qty = await _wait_for_fill(exchange, SymbolRef.from_okx("BTC-EUR"), "ord1", 55620.1, 0.00035958)
    assert price == 55632.5
    assert qty == 0.0003595
    assert exchange.calls == 3


async def test_keeps_fallback_price_when_avg_px_missing():
    exchange = _FakeExchange([{"state": "filled", "accFillSz": "0.00035957", "avgPx": ""}])
    price, qty = await _wait_for_fill(exchange, SymbolRef.from_okx("BTC-EUR"), "ord1", 55620.1, 0.00035958)
    assert price == 55620.1
    assert qty == 0.00035957


async def test_returns_fallback_after_timeout():
    exchange = _FakeExchange([{"state": "live", "accFillSz": "0", "avgPx": ""}])
    price, qty = await _wait_for_fill(
        exchange, SymbolRef.from_okx("BTC-EUR"), "ord1", 55620.1, 0.00035958,
        max_attempts=3, sleep_sec=0.01,
    )
    assert price == 55620.1
    assert qty == 0.00035958
    assert exchange.calls == 3


async def test_survives_poll_errors_and_keeps_polling():
    exchange = _FakeExchange([{"state": "filled", "accFillSz": "0.0001", "avgPx": "50000.0"}])

    async def flaky_get_order_by_id(symbol, ord_id):
        exchange.calls += 1
        if exchange.calls == 1:
            raise OSError("getaddrinfo failed")
        return exchange.sequence[0]

    exchange.get_order_by_id = flaky_get_order_by_id
    price, qty = await _wait_for_fill(exchange, SymbolRef.from_okx("BTC-EUR"), "ord1", 55620.1, 0.00035958)
    assert price == 50000.0
    assert qty == 0.0001


async def test_skips_polling_without_order_id():
    exchange = _FakeExchange([{"state": "filled", "accFillSz": "0.1", "avgPx": "50000.0"}])
    price, qty = await _wait_for_fill(exchange, SymbolRef.from_okx("BTC-EUR"), "", 55620.1, 0.00035958)
    assert (price, qty) == (55620.1, 0.00035958)
    assert exchange.calls == 0


async def test_skips_polling_when_adapter_has_no_get_order_by_id():
    exchange = _NoPollExchange()
    price, qty = await _wait_for_fill(exchange, SymbolRef.from_okx("BTC-EUR"), "ord1", 55620.1, 0.00035958)
    assert (price, qty) == (55620.1, 0.00035958)


async def test_polling_is_async_not_blocking():
    exchange = _FakeExchange([{"state": "filled", "accFillSz": "0.0001", "avgPx": "50000.0"}])
    started = time.monotonic()

    async def slow_get_order_by_id(symbol, ord_id):
        await asyncio.sleep(0.02)
        return exchange.sequence[0]

    exchange.get_order_by_id = slow_get_order_by_id
    await _wait_for_fill(exchange, SymbolRef.from_okx("BTC-EUR"), "ord1", 55620.1, 0.00035958)
    assert time.monotonic() - started >= 0.01
