"""
TASK-1105: OkxWSClient — OKX public WebSocket client for market data.

Connects to OKX public WS (wss://wspap.okx.com/ws/v5/public for demo,
wss://ws.okx.com:8443/ws/v5/public for live / EU: wss://wsaws.okx.com:8443/ws/v5/public).

Emits CandleEvent and TradeEvent compatible with the existing pipeline
(same types as BinanceWSClient, from exchange_models).

OKX candle channel: candle1m  -> push on every tick + on close
OKX trade channel:  trades    -> individual trades with side field

OKX taker side mapping:
  side="buy"  -> taker is buyer  -> is_buyer_maker=False (aggressive buy)
  side="sell" -> taker is seller -> is_buyer_maker=True  (aggressive sell)
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Callable, Optional

from app.execution.exchange_models import CandleEvent, TradeEvent, ConnectionStatusEvent

logger = logging.getLogger(__name__)

# OKX REST base URL for public endpoints (market data, candles, tickers)
# eea.okx.com is for authenticated REST only; public data must use www.okx.com
_OKX_PUBLIC_REST = "https://www.okx.com"

# OKX WS endpoints
# brokerId=9999 is ONLY for private WS (orders/algo). Public WS must NOT have brokerId.
# Ref: TASK-1100.G — brokerId on public WS causes subscription to hang.
_WS_DEMO = "wss://wspap.okx.com/ws/v5/public"
_WS_BUSINESS_DEMO = "wss://wspap.okx.com/ws/v5/business?brokerId=9999"

_WS_EU_LIVE = "wss://wsaws.okx.com:8443/ws/v5/public"
_WS_BUSINESS_EU_LIVE = "wss://wsaws.okx.com:8443/ws/v5/business"


def _normalize_okx_symbol(symbol: str) -> str:
    """Normalize any symbol format to OKX instId (e.g. BTC-EUR).

    Handles:
      BTC-EUR   -> BTC-EUR  (noop)
      BTC/EUR   -> BTC-EUR
      BTCUSDT   -> BTC-USDT
      BNBUSDC   -> BNB-USDC
      BTCEUR    -> BTC-EUR
    """
    s = symbol.upper().replace("/", "-")
    if "-" in s:
        return s
    # Try common quote assets longest-first to avoid false matches (e.g. USDC before USD)
    for q in ("USDC", "USDT", "BUSD", "EUR", "USD", "BTC", "ETH", "BNB"):
        if s.endswith(q) and len(s) > len(q):
            base = s[: -len(q)]
            return f"{base}-{q}"
    return s
_WS_LIVE = "wss://ws.okx.com:8443/ws/v5/public"
_WS_BUSINESS_LIVE = "wss://ws.okx.com:8443/ws/v5/business"

_PING_INTERVAL = 25  # OKX requires ping every 30s; use 25 for safety


class OkxWSClient:
    """
    OKX public WebSocket client implementing the same interface as BinanceWSClient.

    Subscribes to candle1m and trades channels for each symbol.
    Emits CandleEvent and TradeEvent on asyncio queues.

    Usage:
        client = OkxWSClient(symbols=["BTC-EUR", "ETH-EUR"], demo=True)
        await client.start()
        candle = await client.candle_queue.get()
    """

    def __init__(
        self,
        symbols: Optional[list[str]] = None,
        demo: bool = True,
        eu: bool = True,
        reconnect_max_delay: float = 30.0,
    ):
        # Accept OKX format (BTC-EUR), CCXT format (BTC/EUR), or compact (BTCUSDT, BNBUSDC)
        # Normalize all to OKX instId format: BTC-EUR, BNB-USDC, etc.
        self.symbols = [_normalize_okx_symbol(s) for s in (symbols or ["BTC-EUR"])]
        self._demo = demo
        self._eu = eu
        self._reconnect_max_delay = reconnect_max_delay

        if demo:
            self._ws_url = _WS_DEMO
            self._ws_business_url = _WS_BUSINESS_DEMO
        elif eu:
            self._ws_url = _WS_EU_LIVE
            self._ws_business_url = _WS_BUSINESS_EU_LIVE
        else:
            self._ws_url = _WS_LIVE
            self._ws_business_url = _WS_BUSINESS_LIVE

        self.candle_queue: asyncio.Queue[CandleEvent] = asyncio.Queue()
        self.trade_queue: asyncio.Queue[TradeEvent] = asyncio.Queue()
        self.status_queue: asyncio.Queue[ConnectionStatusEvent] = asyncio.Queue()

        self._on_candle: Optional[Callable[[CandleEvent], None]] = None
        self._on_trade: Optional[Callable[[TradeEvent], None]] = None
        self._on_status: Optional[Callable[[ConnectionStatusEvent], None]] = None

        self._tasks: list[asyncio.Task] = []
        self._stop_event = asyncio.Event()

    # ── Callback registration ─────────────────────────────────────────────────

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

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self) -> None:
        self._stop_event.clear()
        
        # Start WS connection for trades (candles via REST fallback if WS fails)
        task_public = asyncio.create_task(
            self._run_connection(self._ws_url, "trades"),
            name="okx-ws-trades",
        )
        self._tasks.append(task_public)
        
        # Start REST candle poller as fallback (WS candle1m often idle in demo)
        task_candle_poller = asyncio.create_task(
            self._rest_candle_poller(),
            name="okx-rest-candles",
        )
        self._tasks.append(task_candle_poller)
        
        logger.info("OkxWSClient started for %d symbols: %s", len(self.symbols), self.symbols)

    async def stop(self) -> None:
        self._stop_event.set()
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        logger.info("OkxWSClient stopped.")

    # ── Connection loop ───────────────────────────────────────────────────────

    async def _run_connection(self, url: str, channel: str) -> None:
        import websockets

        delay = 1.0
        while not self._stop_event.is_set():
            try:
                async with websockets.connect(url, ping_interval=None) as ws:
                    logger.info("OKX WS connected: %s (channel: %s)", url, channel)
                    delay = 1.0

                    await self._subscribe(ws, channel)

                    # Emit connected status for all symbols
                    for sym in self.symbols:
                        self._emit_status(ConnectionStatusEvent(sym, connected=True, provider="okx"))

                    ping_task = asyncio.create_task(self._ping_loop(ws))
                    try:
                        async for raw in ws:
                            if self._stop_event.is_set():
                                break
                            text = raw.decode() if isinstance(raw, bytes) else raw
                            await self._dispatch(text)
                    finally:
                        ping_task.cancel()
                        await asyncio.gather(ping_task, return_exceptions=True)

            except asyncio.CancelledError:
                break
            except Exception as exc:
                # Emit disconnection status for all symbols
                for sym in self.symbols:
                    self._emit_status(ConnectionStatusEvent(sym, connected=False, error=str(exc), provider="okx"))
                if self._stop_event.is_set():
                    break
                logger.warning("OKX WS disconnected (%s) on %s. Reconnect in %.1fs...", exc, url, delay)
                await asyncio.sleep(delay)
                delay = min(delay * 2, self._reconnect_max_delay)

    async def _subscribe(self, ws, channel: str) -> None:
        """Send subscription message for the specific channel(s).
        
        Supports single channel (e.g. "candle1m") or combined
        (e.g. "candle1m+trades") which subscribes to both.
        """
        channels = channel.split("+")
        args = []
        for ch in channels:
            for sym in self.symbols:
                args.append({"channel": ch, "instId": sym})
        msg = json.dumps({"op": "subscribe", "args": args})
        await ws.send(msg)
        logger.debug("OKX WS subscribed channels=%s symbols=%s", channels, self.symbols)

    async def _ping_loop(self, ws) -> None:
        """OKX requires a ping every 30s to keep the connection alive."""
        while True:
            await asyncio.sleep(_PING_INTERVAL)
            try:
                await ws.send("ping")
            except Exception:
                break

    # ── Dispatch ──────────────────────────────────────────────────────────────

    async def _dispatch(self, raw: str) -> None:
        if raw == "pong":
            return
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("OKX WS: invalid JSON: %s", raw[:100])
            return

        # Subscription confirmation / error
        if msg.get("event") in ("subscribe", "error"):
            logger.debug("OKX WS event: %s", msg)
            return

        channel = msg.get("arg", {}).get("channel", "")
        inst_id = msg.get("arg", {}).get("instId", "")
        data = msg.get("data", [])

        if channel == "candle1m":
            for row in data:
                event = self._parse_candle(row, inst_id)
                if event:
                    self.candle_queue.put_nowait(event)
                    if self._on_candle:
                        self._on_candle(event)
        elif channel == "trades":
            for row in data:
                event = self._parse_trade(row, inst_id)
                if event:
                    self.trade_queue.put_nowait(event)
                    if self._on_trade:
                        self._on_trade(event)

    # ── Parsers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_candle(row: list, inst_id: str) -> Optional[CandleEvent]:
        """
        OKX candle1m row format:
        [ts, open, high, low, close, vol, volCcy, volCcyQuote, confirm]
        confirm: "0" = live update, "1" = closed candle
        """
        try:
            return CandleEvent(
                symbol=inst_id,
                interval="1m",
                open_time=int(row[0]),
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[5]),
                is_closed=(row[8] == "1") if len(row) > 8 else False,
                provider="okx",
            )
        except (IndexError, TypeError, ValueError) as exc:
            logger.warning("OKX candle parse error for %s: %s", inst_id, exc)
            return None

    @staticmethod
    def _parse_trade(row: dict, inst_id: str) -> Optional[TradeEvent]:
        """
        OKX trades row format:
        {"instId": "BTC-EUR", "tradeId": "...", "px": "...", "sz": "...",
         "side": "buy"|"sell", "ts": "..."}

        OKX side = taker side:
          side="buy"  -> taker is buyer  -> is_buyer_maker=False
          side="sell" -> taker is seller -> is_buyer_maker=True
        """
        try:
            side = row.get("side", "")
            return TradeEvent(
                symbol=inst_id,
                trade_id=int(row.get("tradeId", 0)),
                price=float(row.get("px", 0)),
                quantity=float(row.get("sz", 0)),
                is_buyer_maker=(side == "sell"),
                timestamp=int(row.get("ts", 0)),
                provider="okx",
            )
        except (TypeError, ValueError) as exc:
            logger.warning("OKX trade parse error for %s: %s", inst_id, exc)
            return None

    # ── REST candle poller (fallback quando WS non invia dati) ─────────────

    async def _rest_candle_poller(self) -> None:
        """Poll OKX REST API every ~55s for the latest closed candle.
        
        Used as fallback when WS candle1m subscription doesn't deliver data
        (common in OKX demo environment).
        """
        import httpx
        from app.config import settings
        
        logger.info("OKX REST candle poller started (interval: ~55s) — using %s", _OKX_PUBLIC_REST)
        
        _last_candle_ts = 0
        # Use www.okx.com (public REST) for market data candles.
        # eea.okx.com is for authenticated REST only and does not serve public candles.
        base = _OKX_PUBLIC_REST
        
        while not self._stop_event.is_set():
            try:
                for sym in self.symbols:
                    params = {"instId": sym, "bar": "1m", "limit": "2"}
                    async with httpx.AsyncClient(timeout=10) as client:
                        resp = await client.get(f"{base}/api/v5/market/candles", params=params)
                        resp.raise_for_status()
                        data = resp.json()
                        if data.get("code") == "0" and data.get("data"):
                            rows = data["data"]
                            for row in rows:
                                ts = int(row[0])
                                if ts > _last_candle_ts:
                                    _last_candle_ts = ts
                                    is_closed = (row[8] == "1") if len(row) > 8 else True
                                    event = CandleEvent(
                                        symbol=sym,
                                        interval="1m",
                                        open_time=ts,
                                        open=float(row[1]),
                                        high=float(row[2]),
                                        low=float(row[3]),
                                        close=float(row[4]),
                                        volume=float(row[5]),
                                        is_closed=is_closed,
                                        provider="okx",
                                    )
                                    self.candle_queue.put_nowait(event)
                                    if self._on_candle:
                                        self._on_candle(event)
                                    logger.info("OKX REST candle: %s O=%s H=%s L=%s C=%s V=%s closed=%s",
                                                 sym, row[1], row[2], row[3], row[4], row[5], is_closed)
            except Exception as e:
                logger.error("OKX REST candle poller error: %s", e)
            
            # Sleep ~55s, check stop every 5s
            for _ in range(11):
                if self._stop_event.is_set():
                    return
                await asyncio.sleep(5)

    # ── Helper ────────────────────────────────────────────────────────────────

    def _emit_status(self, event: ConnectionStatusEvent) -> None:
        self.status_queue.put_nowait(event)
        if self._on_status:
            self._on_status(event)
