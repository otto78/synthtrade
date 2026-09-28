"""
Tests for OkxExchangeAdapter (TASK-1103/1104) and OkxWSClient (TASK-1105).

All tests use fake/mock clients — no network calls.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.execution.exchange_models import (
    ClosePositionRequest,
    ExitBracketRequest,
    ExitProtectionError,
    FeeTier,
    MarketOrderRequest,
    SymbolRef,
    SymbolRules,
    CandleEvent,
    TradeEvent,
)
from app.execution.okx_exchange import OkxExchangeAdapter
from app.scalping.engine.okx_ws_client import OkxWSClient


# ── Fixtures ──────────────────────────────────────────────────────────────────

BTC_EUR = SymbolRef(base="BTC", quote="EUR")



# ── SymbolRef ─────────────────────────────────────────────────────────────────

def test_symbol_ref_formats():
    ref = SymbolRef.from_ccxt("BTC/EUR")
    assert ref.compact == "BTCEUR"
    assert ref.okx == "BTC-EUR"
    assert ref.ccxt == "BTC/EUR"


def test_symbol_ref_from_okx():
    ref = SymbolRef.from_okx("ETH-EUR")
    assert ref.base == "ETH"
    assert ref.quote == "EUR"


def test_symbol_ref_from_compact():
    ref = SymbolRef.from_compact("BTCEUR")
    assert ref.base == "BTC"
    assert ref.quote == "EUR"


# ── SymbolRules ───────────────────────────────────────────────────────────────

def test_round_qty():
    rules = SymbolRules(BTC_EUR, lot_sz=0.001, min_sz=0.001, tick_sz=0.01,
                        max_mkt_sz=100, max_mkt_amt=1_000_000)
    assert rules.round_qty(0.0056789) == pytest.approx(0.005)


def test_round_price():
    rules = SymbolRules(BTC_EUR, lot_sz=0.001, min_sz=0.001, tick_sz=0.1,
                        max_mkt_sz=100, max_mkt_amt=1_000_000)
# ── OkxWSClient parsers ───────────────────────────────────────────────────────

def test_parse_candle_closed():
    row = ["1720000000000", "90000", "91000", "89000", "90500", "1.5",
           "135000", "135000", "1"]
    event = OkxWSClient._parse_candle(row, "BTC-EUR")  # type: ignore[attr-defined]
    assert isinstance(event, CandleEvent)
    assert event.is_closed is True
    assert event.open == 90000.0
    assert event.close == 90500.0
    assert event.provider == "okx"


def test_parse_candle_live():
    row = ["1720000000000", "90000", "91000", "89000", "90500", "1.5",
           "135000", "135000", "0"]
    event = OkxWSClient._parse_candle(row, "BTC-EUR")  # type: ignore[attr-defined]
    assert event is not None
    assert event.is_closed is False


def test_parse_trade_buy_side():
    """OKX side=buy -> taker is buyer -> is_buyer_maker=False."""
    row = {"instId": "BTC-EUR", "tradeId": "123", "px": "90000", "sz": "0.001",
           "side": "buy", "ts": "1720000000000"}
    event = OkxWSClient._parse_trade(row, "BTC-EUR")  # type: ignore[attr-defined]
    assert event is not None
    assert event.is_buyer_maker is False
    assert event.provider == "okx"


def test_parse_trade_sell_side():
    """OKX side=sell -> taker is seller -> is_buyer_maker=True."""
    row = {"instId": "BTC-EUR", "tradeId": "124", "px": "90000", "sz": "0.001",
           "side": "sell", "ts": "1720000000000"}
    event = OkxWSClient._parse_trade(row, "BTC-EUR")  # type: ignore[attr-defined]
    assert event is not None
    assert event.is_buyer_maker is True


def test_parse_candle_invalid_row():
    event = OkxWSClient._parse_candle([], "BTC-EUR")  # type: ignore[attr-defined]
    assert event is None


def test_parse_trade_invalid_row():
    event = OkxWSClient._parse_trade({}, "BTC-EUR")  # type: ignore[attr-defined]
    # price=0, qty=0 — still parses but with zeros
    assert event is not None
    assert event.price == 0.0


# ── OkxWSClient dispatch ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_okx_ws_client_dispatch_candle():
    client = OkxWSClient(symbols=["BTC-EUR"], demo=True)
    msg = {
        "arg": {"channel": "candle1m", "instId": "BTC-EUR"},
        "data": [["1720000000000", "90000", "91000", "89000", "90500", "1.5",
                  "135000", "135000", "1"]],
    }
    await client._dispatch(json.dumps(msg))  # type: ignore[attr-defined]
    assert not client.candle_queue.empty()  # type: ignore[union-attr]
    event = client.candle_queue.get_nowait()  # type: ignore[union-attr]
    assert event.is_closed is True


@pytest.mark.asyncio
async def test_okx_ws_client_dispatch_trade():
    client = OkxWSClient(symbols=["BTC-EUR"], demo=True)
    msg = {
        "arg": {"channel": "trades", "instId": "BTC-EUR"},
        "data": [{"instId": "BTC-EUR", "tradeId": "1", "px": "90000",
                  "sz": "0.001", "side": "buy", "ts": "1720000000000"}],
    }
    await client._dispatch(json.dumps(msg))  # type: ignore[attr-defined]
    assert not client.trade_queue.empty()  # type: ignore[union-attr]
    event = client.trade_queue.get_nowait()  # type: ignore[union-attr]
    assert event.is_buyer_maker is False


@pytest.mark.asyncio
async def test_okx_ws_client_ignores_pong():
    client = OkxWSClient(symbols=["BTC-EUR"], demo=True)
    await client._dispatch("pong")  # type: ignore[attr-defined]
    assert client.candle_queue.empty()  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_okx_ws_client_symbol_normalization():
    """BTC/EUR and BTC-EUR should both be normalized to BTC-EUR."""
    client = OkxWSClient(symbols=["BTC/EUR", "ETH-EUR"])
    assert "BTC-EUR" in client.symbols
    assert "ETH-EUR" in client.symbols


# ── exchange_factory ──────────────────────────────────────────────────────────

def test_get_adapter_okx(monkeypatch):
    monkeypatch.setattr("app.config.settings.EXCHANGE_PROVIDER", "okx")
    monkeypatch.setattr("app.config.settings.TRADING_MODE", "test")
    monkeypatch.setattr("app.config.settings.OKX_API_KEY", "k")
    monkeypatch.setattr("app.config.settings.OKX_SECRET_KEY", "s")
    monkeypatch.setattr("app.config.settings.OKX_PASSPHRASE", "p")
    monkeypatch.setattr("app.config.settings.OKX_BASE_URL", "https://eea.okx.com")

    from app.core.exchange_factory import get_adapter
    adapter = get_adapter()
    assert adapter.provider == "okx"


def test_get_market_ws_client_okx(monkeypatch):
    monkeypatch.setattr("app.config.settings.EXCHANGE_PROVIDER", "okx")
    monkeypatch.setattr("app.config.settings.TRADING_MODE", "test")

    from app.core.exchange_factory import get_market_ws_client
    ws = get_market_ws_client(["BTC-EUR"])
    assert isinstance(ws, OkxWSClient)
    assert "BTC-EUR" in ws.symbols


def test_get_market_ws_client_binance(monkeypatch):
    monkeypatch.setattr("app.config.settings.EXCHANGE_PROVIDER", "binance")
    monkeypatch.setattr("app.config.settings.TRADING_MODE", "test")
    monkeypatch.setattr("app.config.settings.BINANCE_API_KEY", "k")
    monkeypatch.setattr("app.config.settings.BINANCE_SECRET_KEY", "s")

    from app.core.exchange_factory import get_market_ws_client
    from app.scalping.engine.ws_client import BinanceWSClient
    ws = get_market_ws_client(["BTCEUR"])
    assert isinstance(ws, BinanceWSClient)


# ── OkxOrderEventStream normalizers ──────────────────────────────────────────

from app.execution.okx_order_event_stream import OkxOrderEventStream


def test_normalize_order_filled():
    item = {
        "instId": "BTC-EUR", "side": "sell", "ordId": "ord123",
        "state": "filled", "avgPx": "90500.5",
        "fee": "-0.18", "feeCcy": "EUR",
    }
    result = OkxOrderEventStream._normalize_order(item)  # type: ignore[attr-defined]
    assert result is not None
    assert result["status"] == "filled"
    assert result["fill_price"] == 90500.5
    assert result["commission"] == pytest.approx(0.18)
    assert result["commission_asset"] == "EUR"
    assert result["side"] == "SELL"
    assert result["leg"] == "market"
    assert result["provider"] == "okx"


def test_normalize_order_cancelled_maps_to_expired():
    item = {
        "instId": "BTC-EUR", "side": "buy", "ordId": "ord124",
        "state": "cancelled", "avgPx": "0", "fee": "0", "feeCcy": "EUR",
    }
    result = OkxOrderEventStream._normalize_order(item)  # type: ignore[attr-defined]
    assert result is not None
    assert result["status"] == "expired"


def test_normalize_order_live_state_ignored():
    item = {"instId": "BTC-EUR", "side": "sell", "ordId": "ord125", "state": "live"}
    result = OkxOrderEventStream._normalize_order(item)  # type: ignore[attr-defined]
    assert result is None


def test_normalize_algo_order_effective():
    item = {
        "instId": "BTC-EUR", "side": "sell", "algoId": "algo99",
        "ordId": "ord200", "state": "effective",
        "avgPx": "92000.0", "fee": "-0.32", "feeCcy": "EUR",
        "ordType": "oco_tp",
    }
    result = OkxOrderEventStream._normalize_algo_order(item)  # type: ignore[attr-defined]
    assert result is not None
    assert result["status"] == "filled"
    assert result["bracket_id"] == "algo99"
    assert result["order_list_id"] == "algo99"
    assert result["leg"] == "take_profit"
    assert result["fill_price"] == 92000.0


def test_normalize_algo_order_sl():
    item = {
        "instId": "BTC-EUR", "side": "sell", "algoId": "algo100",
        "ordId": "ord201", "state": "effective",
        "avgPx": "88000.0", "fee": "-0.31", "feeCcy": "EUR",
        "ordType": "oco_sl",
    }
    result = OkxOrderEventStream._normalize_algo_order(item)  # type: ignore[attr-defined]
    assert result
    assert result["leg"] == "stop_loss"


def test_normalize_algo_order_actual_side_tp():
    """actualSide field takes priority over trigger prices."""
    item = {
        "instId": "BTC-EUR", "side": "sell", "algoId": "algo103",
        "ordId": "ord210", "state": "effective",
        "avgPx": "93000.0", "fee": "-0.33", "feeCcy": "EUR",
        "actualSide": "tp", "tpTriggerPx": "95000", "slTriggerPx": "85000",
    }
    result = OkxOrderEventStream._normalize_algo_order(item)  # type: ignore[attr-defined]
    assert result is not None
    assert result["leg"] == "take_profit"
    assert result["fill_price"] == 93000.0


def test_normalize_algo_order_actual_side_sl():
    """actualSide="sl" overrides tpTriggerPx being non-zero."""
    item = {
        "instId": "BTC-EUR", "side": "sell", "algoId": "algo104",
        "ordId": "ord211", "state": "effective",
        "avgPx": "87000.0", "fee": "-0.31", "feeCcy": "EUR",
        "actualSide": "sl", "tpTriggerPx": "95000", "slTriggerPx": "85000",
    }
    result = OkxOrderEventStream._normalize_algo_order(item)  # type: ignore[attr-defined]
    assert result is not None
    assert result["leg"] == "stop_loss"


def test_normalize_algo_order_preserves_okx_fill_time():
    item = {
        "instId": "BTC-EUR", "side": "sell", "algoId": "algo-fill-time",
        "ordId": "ord-fill-time", "state": "effective", "avgPx": "87000.0",
        "actualSide": "sl", "fillTime": "1785835084000",
    }
    result = OkxOrderEventStream._normalize_algo_order(item)  # type: ignore[attr-defined]
    assert result is not None
    assert result["fill_time"] == "2026-08-04T09:18:04+00:00"


def test_normalize_algo_order_oco_fill_closer_to_tp():
    """OCO without actualSide: fill closer to TP → take_profit."""
    item = {
        "instId": "BTC-EUR", "side": "sell", "algoId": "algo105",
        "ordId": "ord212", "state": "effective",
        "avgPx": "94500.0", "fee": "-0.30", "feeCcy": "EUR",
        "tpTriggerPx": "95000", "slTriggerPx": "85000",
    }
    result = OkxOrderEventStream._normalize_algo_order(item)  # type: ignore[attr-defined]
    assert result is not None
    assert result["leg"] == "take_profit"


def test_normalize_algo_order_oco_fill_closer_to_sl():
    """OCO without actualSide: fill closer to SL → stop_loss."""
    item = {
        "instId": "BTC-EUR", "side": "sell", "algoId": "algo106",
        "ordId": "ord213", "state": "effective",
        "avgPx": "86000.0", "fee": "-0.30", "feeCcy": "EUR",
        "tpTriggerPx": "95000", "slTriggerPx": "85000",
    }
    result = OkxOrderEventStream._normalize_algo_order(item)  # type: ignore[attr-defined]
    assert result is not None
    assert result["leg"] == "stop_loss"


def test_normalize_algo_order_real_world_bracket_sl():
    """
    Real-world: bracket 3745204575738245120 — OKX returned actualSide="sl"
    but tpTriggerPx was non-zero (OCO). Without actualSide, old code would
    mislabel as take_profit. With actualSide, it correctly returns stop_loss.
    """
    item = {
        "instId": "BTC-EUR", "side": "sell", "algoId": "3745204575738245120",
        "ordId": "3746657746278064128", "state": "effective",
        "avgPx": "0", "fee": "-0.00000353", "feeCcy": "BTC",
        "actualSide": "sl", "tpTriggerPx": "57815.6", "slTriggerPx": "56335.3",
    }
    result = OkxOrderEventStream._normalize_algo_order(item)  # type: ignore[attr-defined]
    assert result is not None
    assert result["leg"] == "stop_loss"
    assert result["bracket_id"] == "3745204575738245120"


def test_normalize_algo_order_canceled():
    item = {
        "instId": "BTC-EUR", "side": "sell", "algoId": "algo101",
        "state": "canceled", "avgPx": "0", "fee": "0", "feeCcy": "EUR",
        "ordType": "oco",
    }
    result = OkxOrderEventStream._normalize_algo_order(item)  # type: ignore[attr-defined]
    assert result
    assert result["status"] == "expired"


def test_normalize_algo_order_live_ignored():
    item = {"instId": "BTC-EUR", "algoId": "algo102", "state": "live"}
    result = OkxOrderEventStream._normalize_algo_order(item)  # type: ignore[attr-defined]
    assert result is None


@pytest.mark.asyncio
async def test_order_event_stream_dispatch_order():
    stream = OkxOrderEventStream("k", "s", "p", demo=True)
    received: list[dict] = []

    async def handler(event: dict) -> None:
        received.append(event)

    stream._on_order_update = handler  # type: ignore[attr-defined]

    msg = {
        "arg": {"channel": "orders"},
        "data": [{
            "instId": "BTC-EUR", "side": "sell", "ordId": "ord300",
            "state": "filled", "avgPx": "91000", "fee": "-0.2", "feeCcy": "EUR",
        }],
    }
    await stream._dispatch(json.dumps(msg))  # type: ignore[attr-defined]
    assert len(received) == 1
    assert received[0]["order_id"] == "ord300"


@pytest.mark.asyncio
async def test_order_event_stream_dispatch_algo():
    stream = OkxOrderEventStream("k", "s", "p", demo=True)
    received: list[dict] = []

    async def handler(event: dict) -> None:
        received.append(event)

    stream._on_order_update = handler  # type: ignore[attr-defined]

    msg = {
        "arg": {"channel": "algo-orders"},
        "data": [{
            "instId": "BTC-EUR", "side": "sell", "algoId": "algo200",
            "ordId": "ord400", "state": "effective",
            "avgPx": "92000", "fee": "-0.3", "feeCcy": "EUR", "ordType": "oco_tp",
        }],
    }
    await stream._dispatch(json.dumps(msg))  # type: ignore[attr-defined]
    assert len(received) == 1
    assert received[0]["bracket_id"] == "algo200"
    assert received[0]["leg"] == "take_profit"


def test_get_order_event_stream_okx(monkeypatch):
    monkeypatch.setattr("app.config.settings.EXCHANGE_PROVIDER", "okx")
    monkeypatch.setattr("app.config.settings.TRADING_MODE", "test")
    monkeypatch.setattr("app.config.settings.OKX_API_KEY", "k")
    monkeypatch.setattr("app.config.settings.OKX_SECRET_KEY", "s")
    monkeypatch.setattr("app.config.settings.OKX_PASSPHRASE", "p")

    from app.core.exchange_factory import get_order_event_stream
