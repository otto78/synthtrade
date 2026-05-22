"""Binance live WebSocket client per il feed dati scalping.

Si connette agli stream kline (1m) e trade di Binance,
emettendo eventi asincroni consumabili da TickProcessor, CVDCalculator e
dal broadcast verso il frontend via app/api/ws.py.

Utilizza settings.binance_ws_base_url per selezionare automaticamente
Testnet (wss://testnet.binance.vision/ws) o Live (wss://stream.binance.com:9443/ws).
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

from app.config import settings

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Data Classes Eventi
# ──────────────────────────────────────────────


@dataclass
class CandleEvent:
    """Evento generato alla chiusura/aggiornamento di una candela 1m."""
    symbol: str
    interval: str
    open_time: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    is_closed: bool  # True = candela completata, False = aggiornamento live


@dataclass
class TradeEvent:
    """Evento generato ad ogni trade eseguito (utile per CVD)."""
    symbol: str
    trade_id: int
    price: float
    quantity: float
    is_buyer_maker: bool  # False = buy aggressivo, True = sell aggressivo
    timestamp: int


@dataclass
class ConnectionStatusEvent:
    """Evento generato quando lo stato della connessione cambia."""
    symbol: str
    connected: bool
    error: Optional[str] = None


# ──────────────────────────────────────────────
# BinanceWSClient
# ──────────────────────────────────────────────


class BinanceWSClient:
    """Client WebSocket asincrono per stream Binance.

    Si connette agli stream kline_1m e trade per ogni simbolo.
    Emette eventi su code asyncio separatamente per candele e trades.

    Usage:
        client = BinanceWSClient(symbols=["btcusdt", "ethusdt"])
        await client.start()

        # Consumare eventi in un altro task:
        while True:
            candle = await client.candle_queue.get()
            # processa candela

        # Oppure registrare callback:
        client.on_candle(my_candle_handler)
    """

    def __init__(
        self,
        symbols: Optional[list[str]] = None,
        reconnect_max_delay: float = 30.0,
    ):
        self.symbols = [s.lower() for s in (symbols or ["btcusdt"])]
        self._reconnect_max_delay = reconnect_max_delay

        # Code asincrone per consumatori esterni
        self.candle_queue: asyncio.Queue[CandleEvent] = asyncio.Queue()
        self.trade_queue: asyncio.Queue[TradeEvent] = asyncio.Queue()
        self.status_queue: asyncio.Queue[ConnectionStatusEvent] = asyncio.Queue()

        # Callback opzionali (invocati OLTRE alle code)
        self._on_candle: Optional[Callable[[CandleEvent], None]] = None
        self._on_trade: Optional[Callable[[TradeEvent], None]] = None
        self._on_status: Optional[Callable[[ConnectionStatusEvent], None]] = None

        # Stato interno
        self._tasks: list[asyncio.Task] = []
        self._stop_event = asyncio.Event()

    # ── Callback registration ─────────────────

    @property
    def on_candle(self) -> Optional[Callable[[CandleEvent], None]]:
        return self._on_candle

    @on_candle.setter
    def on_candle(self, cb: Optional[Callable[[CandleEvent], None]]) -> None:
        self._on_candle = cb

    @property
    def on_trade(self) -> Optional[Callable[[TradeEvent], None]]:
        return self._on_trade

    @on_trade.setter
    def on_trade(self, cb: Optional[Callable[[TradeEvent], None]]) -> None:
        self._on_trade = cb

    @property
    def on_status(self) -> Optional[Callable[[ConnectionStatusEvent], None]]:
        return self._on_status

    @on_status.setter
    def on_status(self, cb: Optional[Callable[[ConnectionStatusEvent], None]]) -> None:
        self._on_status = cb

    # ── Lifecycle ─────────────────────────────

    async def start(self) -> None:
        """Avvia un task per ogni simbolo (ciascuno con kline + trade stream)."""
        self._stop_event.clear()
        for symbol in self.symbols:
            task = asyncio.create_task(
                self._run_symbol_stream(symbol),
                name=f"ws-{symbol}",
            )
            self._tasks.append(task)
        logger.info(
            "BinanceWSClient avviato per %d simboli: %s",
            len(self.symbols),
            ", ".join(self.symbols),
        )

    async def stop(self) -> None:
        """Ferma tutti i task di connessione."""
        self._stop_event.set()
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        logger.info("BinanceWSClient fermato.")

    # ── Stream per singolo simbolo ────────────

    async def _run_symbol_stream(self, symbol: str) -> None:
        """Mantiene la connessione WS per un simbolo con auto-riconnessione."""
        import websockets

        streams = [f"{symbol}@kline_1m", f"{symbol}@trade"]
        url = f"{settings.binance_ws_base_url}/{'/'.join(streams)}"

        delay = 1.0
        while not self._stop_event.is_set():
            try:
                self._emit_status(ConnectionStatusEvent(symbol, connected=True))
                async with websockets.connect(url, ping_interval=20) as ws:
                    logger.info("WS connesso: %s", url)
                    delay = 1.0  # reset backoff
                    async for raw in ws:
                        if self._stop_event.is_set():
                            break
                        # websockets può restituire bytes; decodifichiamo se necessario
                        text = raw.decode() if isinstance(raw, bytes) else raw
                        await self._dispatch(text, symbol)
            except asyncio.CancelledError:
                logger.debug("WS %s cancellato.", symbol)
                break
            except Exception as exc:
                logger.warning(
                    "WS %s disconnesso (%s). Reconnect in %.1fs...",
                    symbol, exc, delay,
                )
                self._emit_status(
                    ConnectionStatusEvent(symbol, connected=False, error=str(exc)),
                )
                if self._stop_event.is_set():
                    break
                await asyncio.sleep(delay)
                delay = min(delay * 2, self._reconnect_max_delay)

    # ── Dispatch messaggi ─────────────────────

    async def _dispatch(self, raw: str, symbol: str) -> None:
        """Parsa e smista un messaggio JSON grezzo da Binance."""
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("WS %s: messaggio JSON non valido: %s", symbol, raw[:100])
            return

        event_type = msg.get("e")  # 'kline' | 'trade'
        if event_type == "kline":
            event = self._parse_candle(msg, symbol)
            if event is not None:
                self.candle_queue.put_nowait(event)
                if self._on_candle:
                    self._on_candle(event)
        elif event_type == "trade":
            event = self._parse_trade(msg, symbol)
            if event is not None:
                self.trade_queue.put_nowait(event)
                if self._on_trade:
                    self._on_trade(event)

    # ── Parsing helpers ───────────────────────

    @staticmethod
    def _parse_candle(msg: dict, symbol: str) -> Optional[CandleEvent]:
        """Converte un messaggio kline Binance in CandleEvent."""
        k = msg.get("k")
        if not k:
            return None
        try:
            return CandleEvent(
                symbol=symbol,
                interval=k.get("i", ""),
                open_time=k.get("t", 0),
                open=float(k.get("o", 0)),
                high=float(k.get("h", 0)),
                low=float(k.get("l", 0)),
                close=float(k.get("c", 0)),
                volume=float(k.get("v", 0)),
                is_closed=k.get("x", False),
            )
        except (TypeError, ValueError) as exc:
            logger.warning("Errore parsing kline per %s: %s", symbol, exc)
            return None

    @staticmethod
    def _parse_trade(msg: dict, symbol: str) -> Optional[TradeEvent]:
        """Converte un messaggio trade Binance in TradeEvent.
        
        Ritorna None se mancano campi essenziali (price, quantity).
        """
        price_raw = msg.get("p")
        qty_raw = msg.get("q")
        trade_id_raw = msg.get("t")
        timestamp_raw = msg.get("T")
        if price_raw is None or qty_raw is None:
            return None
        try:
            return TradeEvent(
                symbol=symbol,
                trade_id=int(trade_id_raw) if trade_id_raw is not None else 0,
                price=float(price_raw),
                quantity=float(qty_raw),
                is_buyer_maker=msg.get("m", False),
                timestamp=int(timestamp_raw) if timestamp_raw is not None else 0,
            )
        except (TypeError, ValueError) as exc:
            logger.warning("Errore parsing trade per %s: %s", symbol, exc)
            return None

    # ── Helper emissione eventi ───────────────

    def _emit_status(self, event: ConnectionStatusEvent) -> None:
        self.status_queue.put_nowait(event)
        if self._on_status:
            self._on_status(event)