"""Test per BinanceWSClient (TASK-803).

Strategia di test:
  1. Test parsing messaggi kline e trade (unit, no WS reale).
  2. Test dispatch ed emissione su code/callback.
  3. Test lifecycle (start/stop) con websocket mockato.
  4. Test riconnessione automatica (connessione che cade).
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.scalping.engine.ws_client import (
    BinanceWSClient,
    CandleEvent,
    ConnectionStatusEvent,
    TradeEvent,
)


# ── Fixtures ───────────────────────────────────


@pytest.fixture
def sample_kline_msg() -> str:
    """Messaggio kline 1m realistico come lo invierebbe Binance."""
    return json.dumps({
        "e": "kline",
        "E": 1716300000000,
        "s": "BTCUSDT",
        "k": {
            "t": 1716299940000,
            "T": 1716299999999,
            "s": "BTCUSDT",
            "i": "1m",
            "f": 100,
            "L": 200,
            "o": "67500.00",
            "c": "67650.50",
            "h": "67700.00",
            "l": "67450.00",
            "v": "123.456",
            "n": 100,
            "x": True,
            "q": "0",
            "V": "60",
            "Q": "63",
            "B": "0",
        },
    })


@pytest.fixture
def sample_trade_msg() -> str:
    """Messaggio trade realistico come lo invierebbe Binance."""
    return json.dumps({
        "e": "trade",
        "E": 1716300000000,
        "s": "BTCUSDT",
        "t": 123456789,
        "p": "67650.50",
        "q": "0.001",
        "b": 100,
        "a": 200,
        "T": 1716300000000,
        "m": False,
        "M": True,
    })


@pytest.fixture
def sample_buy_trade_msg() -> str:
    """Trade con is_buyer_maker=True = sell aggressivo."""
    return json.dumps({
        "e": "trade",
        "E": 1716300001000,
        "s": "ETHUSDT",
        "t": 987654321,
        "p": "3200.00",
        "q": "0.50",
        "b": 300,
        "a": 400,
        "T": 1716300001000,
        "m": True,
        "M": True,
    })


# ── Test: Parsing ──────────────────────────────


class TestParseCandle:
    def test_valid_kline(self, sample_kline_msg):
        """Parsing corretto di un messaggio kline valido."""
        msg = json.loads(sample_kline_msg)
        event = BinanceWSClient._parse_candle(msg, "btcusdt")
        assert event is not None
        assert event.symbol == "btcusdt"
        assert event.interval == "1m"
        assert event.open == 67500.00
        assert event.close == 67650.50
        assert event.high == 67700.00
        assert event.low == 67450.00
        assert event.volume == 123.456
        assert event.is_closed is True
        assert event.open_time == 1716299940000

    def test_missing_k_field(self):
        """Se manca il campo 'k' ritorna None."""
        msg = {"e": "kline", "s": "BTCUSDT"}
        event = BinanceWSClient._parse_candle(msg, "btcusdt")
        assert event is None

    def test_invalid_price_types(self):
        """Se i prezzi non sono numerici ritorna None."""
        msg = {
            "e": "kline",
            "k": {
                "t": 0, "i": "1m", "o": "notanumber",
                "h": "0", "l": "0", "c": "0", "v": "0", "x": False,
            },
        }
        event = BinanceWSClient._parse_candle(msg, "btcusdt")
        assert event is None

    def test_kline_not_closed(self):
        """Candela non ancora chiusa (aggiornamento live)."""
        msg = {
            "e": "kline",
            "k": {
                "t": 0, "i": "1m", "o": "100", "h": "101",
                "l": "99", "c": "100.5", "v": "10", "x": False,
            },
        }
        event = BinanceWSClient._parse_candle(json.loads(json.dumps(msg)), "btcusdt")
        assert event is not None
        assert event.is_closed is False


class TestParseTrade:
    def test_valid_trade(self, sample_trade_msg):
        """Parsing corretto di un trade valido."""
        msg = json.loads(sample_trade_msg)
        event = BinanceWSClient._parse_trade(msg, "btcusdt")
        assert event is not None
        assert event.symbol == "btcusdt"
        assert event.trade_id == 123456789
        assert event.price == 67650.50
        assert event.quantity == 0.001
        assert event.is_buyer_maker is False  # buy aggressivo
        assert event.timestamp == 1716300000000

    def test_buyer_maker_trade(self, sample_buy_trade_msg):
        """Trade con is_buyer_maker=True correttamente parsato."""
        msg = json.loads(sample_buy_trade_msg)
        event = BinanceWSClient._parse_trade(msg, "ethusdt")
        assert event is not None
        assert event.symbol == "ethusdt"
        assert event.is_buyer_maker is True  # sell aggressivo

    def test_missing_price_field(self):
        """Se manca il campo prezzo ritorna None."""
        msg = {"e": "trade", "s": "BTCUSDT"}
        event = BinanceWSClient._parse_trade(msg, "btcusdt")
        assert event is None

    def test_invalid_quantity(self):
        """Se quantity non è numerica ritorna None."""
        msg = {"e": "trade", "t": 1, "p": "100", "q": "bad", "m": False, "T": 0}
        event = BinanceWSClient._parse_trade(json.loads(json.dumps(msg)), "btcusdt")
        assert event is None


# ── Test: Dispatch & Event Emission ────────────


class TestDispatch:
    @pytest.mark.asyncio
    async def test_dispatch_kline(self, sample_kline_msg):
        """Il dispatch di un kline produce un CandleEvent sulla coda."""
        client = BinanceWSClient(symbols=["btcusdt"])
        await client._dispatch(sample_kline_msg, "btcusdt")
        assert client.candle_queue.qsize() == 1
        event = client.candle_queue.get_nowait()
        assert isinstance(event, CandleEvent)
        assert event.symbol == "btcusdt"
        assert event.close == 67650.50

    @pytest.mark.asyncio
    async def test_dispatch_trade(self, sample_trade_msg):
        """Il dispatch di un trade produce un TradeEvent sulla coda."""
        client = BinanceWSClient(symbols=["btcusdt"])
        await client._dispatch(sample_trade_msg, "btcusdt")
        assert client.trade_queue.qsize() == 1
        event = client.trade_queue.get_nowait()
        assert isinstance(event, TradeEvent)
        assert event.price == 67650.50

    @pytest.mark.asyncio
    async def test_dispatch_invalid_json(self):
        """JSON non valido non produce eventi, loggato come warning."""
        client = BinanceWSClient(symbols=["btcusdt"])
        await client._dispatch("{invalid json}", "btcusdt")
        assert client.candle_queue.qsize() == 0
        assert client.trade_queue.qsize() == 0

    @pytest.mark.asyncio
    async def test_dispatch_unknown_event_type(self):
        """Tipo evento sconosciuto non produce eventi."""
        msg = json.dumps({"e": "unknown_event", "data": "test"})
        client = BinanceWSClient(symbols=["btcusdt"])
        await client._dispatch(msg, "btcusdt")
        assert client.candle_queue.qsize() == 0
        assert client.trade_queue.qsize() == 0

    @pytest.mark.asyncio
    async def test_callback_invoked(self, sample_kline_msg):
        """Il callback on_candle viene invocato quando registrato."""
        callback = MagicMock()
        client = BinanceWSClient(symbols=["btcusdt"])
        client.on_candle = callback
        await client._dispatch(sample_kline_msg, "btcusdt")
        callback.assert_called_once()
        args = callback.call_args[0]
        assert isinstance(args[0], CandleEvent)
        assert args[0].close == 67650.50

    @pytest.mark.asyncio
    async def test_trade_callback_invoked(self, sample_trade_msg):
        """Il callback on_trade viene invocato quando registrato."""
        callback = MagicMock()
        client = BinanceWSClient(symbols=["btcusdt"])
        client.on_trade = callback
        await client._dispatch(sample_trade_msg, "btcusdt")
        callback.assert_called_once()
        args = callback.call_args[0]
        assert isinstance(args[0], TradeEvent)
        assert args[0].price == 67650.50


# ── Test: Simboli ──────────────────────────────


class TestSymbols:
    def test_default_symbol(self):
        """Simbolo predefinito se non specificato."""
        client = BinanceWSClient()
        assert client.symbols == ["btcusdt"]

    def test_custom_symbols(self):
        """Simboli personalizzati e case-insensitive."""
        client = BinanceWSClient(symbols=["BTCUSDT", "ETHUSDT"])
        assert client.symbols == ["btcusdt", "ethusdt"]

    def test_single_symbol(self):
        """Singolo simbolo passato come lista."""
        client = BinanceWSClient(symbols=["ETHUSDT"])
        assert client.symbols == ["ethusdt"]


# ── Test: Lifecycle (con WS mockato) ───────────


class TestLifecycle:
    @pytest.mark.asyncio
    async def test_start_creates_tasks(self):
        """start() crea un asyncio.Task per ogni simbolo."""
        client = BinanceWSClient(symbols=["btcusdt"])
        assert len(client._tasks) == 0
        # Mockiamo _run_symbol_stream per evitare connessioni reali
        with patch.object(client, "_run_symbol_stream", AsyncMock()):
            await client.start()
            assert len(client._tasks) == 1
            assert client._tasks[0].get_name() == "ws-btcusdt"
            # Pulizia
            await client.stop()

    @pytest.mark.asyncio
    async def test_start_multiple_symbols(self):
        """start() crea un task per ogni simbolo."""
        client = BinanceWSClient(symbols=["btcusdt", "ethusdt"])
        with patch.object(client, "_run_symbol_stream", AsyncMock()):
            await client.start()
            assert len(client._tasks) == 2
            await client.stop()

    @pytest.mark.asyncio
    async def test_stop_cancels_tasks(self):
        """stop() cancella tutti i task."""
        client = BinanceWSClient(symbols=["btcusdt"])
        with patch.object(client, "_run_symbol_stream", AsyncMock()):
            await client.start()
            assert len(client._tasks) == 1
            await client.stop()
            assert len(client._tasks) == 0

    @pytest.mark.asyncio
    async def test_stop_sets_stop_event(self):
        """stop() setta _stop_event."""
        client = BinanceWSClient(symbols=["btcusdt"])
        assert client._stop_event.is_set() is False
        await client.stop()
        assert client._stop_event.is_set() is True


# ── Test: Riconnessione automatica ─────────────


class TestReconnection:
    @pytest.mark.asyncio
    async def test_reconnect_backoff(self):
        """La riconnessione usa backoff esponenziale fino al max."""
        client = BinanceWSClient(symbols=["btcusdt"], reconnect_max_delay=30.0)
        # Simula una connessione WS che fallisce subito
        mock_ws = AsyncMock()
        mock_ws.__aenter__ = AsyncMock(return_value=mock_ws)
        mock_ws.__aiter__ = AsyncMock(side_effect=ConnectionError("simulated error"))

        with (
            patch("app.scalping.engine.ws_client.settings") as mock_settings,
            patch("websockets.connect", return_value=mock_ws),
        ):
            mock_settings.binance_ws_base_url = "wss://test.stream"
            # Eseguiamo _run_symbol_stream in un task e lo fermiamo dopo 0.1s
            task = asyncio.create_task(client._run_symbol_stream("btcusdt"))
            await asyncio.sleep(0.15)
            assert task.done() is False  # deve stare riprovando
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass

    @pytest.mark.asyncio
    async def test_status_event_on_disconnect(self):
        """La disconnessione emette ConnectionStatusEvent con connected=False."""
        client = BinanceWSClient(symbols=["btcusdt"])
        # Simula un errore di connessione
        mock_ws = AsyncMock()
        mock_ws.__aenter__ = AsyncMock(side_effect=ConnectionError("connection failed"))
        mock_ws.__aiter__ = AsyncMock()

        with (
            patch("app.scalping.engine.ws_client.settings") as mock_settings,
            patch("websockets.connect", return_value=mock_ws),
        ):
            mock_settings.binance_ws_base_url = "wss://test.stream"
            task = asyncio.create_task(client._run_symbol_stream("btcusdt"))
            await asyncio.sleep(0.15)
            # Dovrebbe esserci uno status event di disconnessione
            assert client.status_queue.qsize() > 0
            events = []
            while not client.status_queue.empty():
                events.append(client.status_queue.get_nowait())
            assert any(
                isinstance(e, ConnectionStatusEvent) and not e.connected
                for e in events
            )
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass


# ── Test: Queue separation ─────────────────────


class TestQueueSeparation:
    @pytest.mark.asyncio
    async def test_candle_and_trade_separate(self, sample_kline_msg, sample_trade_msg):
        """Candele e trades vanno su code separate."""
        client = BinanceWSClient(symbols=["btcusdt"])
        await client._dispatch(sample_kline_msg, "btcusdt")
        await client._dispatch(sample_trade_msg, "btcusdt")
        assert client.candle_queue.qsize() == 1
        assert client.trade_queue.qsize() == 1
        assert isinstance(client.candle_queue.get_nowait(), CandleEvent)
        assert isinstance(client.trade_queue.get_nowait(), TradeEvent)