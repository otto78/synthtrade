"""UserDataStreamManager — Binance User Data Stream WebSocket.

Gestisce il ciclo di vita del WebSocket User Data Stream di Binance:
1. POST /api/v3/userDataStream → ottieni listenKey
2. Apri WSS wss://stream.binance.com:9443/ws/<listenKey>
3. Ogni 30 min → PUT /api/v3/userDataStream (keepalive, scade dopo 60 min)
4. Su disconnessione → riconnetti con nuovo listenKey
5. Su ogni executionReport con orderStatus FILLED/EXPIRED → dispatch all'handler

TASK-824: Implementato per risolvere il disallineamento trade log vs Binance.
Prima di questo fix, l'app scopriva l'esecuzione OCO solo al prossimo polling
sulla candela (~60 secondi). Con User Data Stream, la chiusura viene rilevata
in tempo reale (< 1 secondo).
"""

import asyncio
import json
import logging
import time
from typing import Callable, Optional, Dict, Any

import httpx

logger = logging.getLogger(__name__)


class UserDataStreamError(Exception):
    """Errore generico del User Data Stream."""
    pass


class UserDataStreamManager:
    """Manages Binance User Data Stream lifecycle.

    Usage:
        uds = UserDataStreamManager(api_key="xxx", api_secret="yyy")
        await uds.start(on_order_update=my_handler)
        # ... session runs ...
        await uds.stop()
    """

    # Binance API endpoints
    TESTNET_BASE = "https://testnet.binance.vision"
    LIVE_BASE = "https://api.binance.com"
    TESTNET_WS = "wss://testnet.binance.vision/ws"
    LIVE_WS = "wss://stream.binance.com:9443/ws"

    KEEPALIVE_INTERVAL = 1800  # 30 minuti (Binance richiede ogni 60 min)
    RECONNECT_DELAY = 5  # secondi prima di riconnettere

    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        self._api_key = api_key
        self._api_secret = api_secret
        self._testnet = testnet

        self._listen_key: Optional[str] = None
        self._ws_url: Optional[str] = None
        self._running = False
        self._ws_connection = None  # websocket connection
        self._on_order_update: Optional[Callable] = None
        self._keepalive_task: Optional[asyncio.Task] = None
        self._listen_task: Optional[asyncio.Task] = None

        self._base_url = self.TESTNET_BASE if testnet else self.LIVE_BASE
        self._ws_base = self.TESTNET_WS if testnet else self.LIVE_WS

    async def start(self, on_order_update: Callable):
        """Avvia il User Data Stream.

        Args:
            on_order_update: Callable async che riceve il dict dell'executionReport.
                Verrà chiamata ogni volta che un ordine viene FILLED o EXPIRED.
        """
        if self._running:
            logger.warning("UserDataStream already running")
            return

        self._on_order_update = on_order_update
        self._running = True

        try:
            await self._create_listen_key()
            # _listen_key è garantito non-None dopo _create_listen_key (altrimenti solleva eccezione)
            listen_key = self._listen_key or ""
            self._ws_url = f"{self._ws_base}/{listen_key}"
            logger.info(f"UserDataStream listenKey ottenuto: {listen_key[:8]}...")

            # Avvia keepalive ogni 30 minuti
            self._keepalive_task = asyncio.create_task(
                self._keepalive_loop(),
                name="uds-keepalive"
            )

            # Avvia il listener WebSocket
            self._listen_task = asyncio.create_task(
                self._listen_loop(),
                name="uds-listen"
            )

            logger.info("UserDataStream avviato con successo")
        except Exception as e:
            self._running = False
            logger.error(f"Failed to start UserDataStream: {e}")
            raise UserDataStreamError(f"Failed to start UserDataStream: {e}")

    async def stop(self):
        """Ferma il User Data Stream e cancella la listenKey su Binance."""
        self._running = False

        # Cancella keepalive task
        if self._keepalive_task and not self._keepalive_task.done():
            self._keepalive_task.cancel()
            try:
                await self._keepalive_task
            except asyncio.CancelledError:
                pass
        self._keepalive_task = None

        # Cancella listen task
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        self._listen_task = None

        # Chiudi WebSocket
        if self._ws_connection:
            try:
                await self._ws_connection.close()
            except Exception:
                pass
            self._ws_connection = None

        # DELETE listenKey su Binance
        if self._listen_key:
            try:
                async with httpx.AsyncClient() as client:
                    await client.delete(
                        f"{self._base_url}/api/v3/userDataStream",
                        params={"listenKey": self._listen_key},
                        headers={"X-MBX-APIKEY": self._api_key},
                    )
                logger.info("ListenKey cancellata da Binance")
            except Exception as e:
                logger.warning(f"Failed to delete listenKey: {e}")

        self._listen_key = None
        self._ws_url = None
        logger.info("UserDataStream fermato")

    async def _create_listen_key(self):
        """Crea una nuova listenKey via POST /api/v3/userDataStream."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/api/v3/userDataStream",
                headers={"X-MBX-APIKEY": self._api_key},
            )
            resp.raise_for_status()
            data = resp.json()
            self._listen_key = data.get("listenKey")
            if not self._listen_key:
                raise UserDataStreamError("No listenKey in response")

    async def _keepalive_listen_key(self):
        """Rinnova la listenKey via PUT /api/v3/userDataStream."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.put(
                    f"{self._base_url}/api/v3/userDataStream",
                    params={"listenKey": self._listen_key},
                    headers={"X-MBX-APIKEY": self._api_key},
                )
                resp.raise_for_status()
                listen_key = self._listen_key or ""
                logger.debug(f"ListenKey keepalive: {listen_key[:8]}...")
        except Exception as e:
            logger.warning(f"Keepalive failed (will reconnect): {e}")
            # Se keepalive fallisce, la listenKey potrebbe essere scaduta
            # Ricreiamo tutto
            await self._reconnect()

    async def _keepalive_loop(self):
        """Loop che rinnova la listenKey ogni 30 minuti."""
        try:
            while self._running:
                await asyncio.sleep(self.KEEPALIVE_INTERVAL)
                if not self._running:
                    break
                await self._keepalive_listen_key()
        except asyncio.CancelledError:
            pass

    async def _listen_loop(self):
        """Loop che mantiene attiva la connessione WebSocket."""
        import websockets

        while self._running:
            try:
                if not self._ws_url:
                    await self._reconnect()
                    continue

                logger.info(f"Connecting to User Data Stream: {self._ws_url[:40]}...")
                async with websockets.connect(self._ws_url) as ws:
                    self._ws_connection = ws
                    logger.info(f"\033[96m📡 UDS SOCKET ATTIVO: User Data Stream connesso per monitoraggio OCO in tempo reale\033[0m")

                    while self._running:
                        try:
                            message = await asyncio.wait_for(
                                ws.recv(), timeout=60
                            )
                            await self._dispatch_message(json.loads(message))
                        except asyncio.TimeoutError:
                            # Timeout normale — ping/pong gestito da websockets
                            continue
                        except websockets.exceptions.ConnectionClosed:
                            logger.warning("User Data Stream WebSocket disconnected")
                            break

            except Exception as e:
                logger.error(f"User Data Stream error: {e}")
                if self._running:
                    logger.info(f"Reconnecting in {self.RECONNECT_DELAY}s...")
                    await asyncio.sleep(self.RECONNECT_DELAY)
                    await self._reconnect()
            finally:
                self._ws_connection = None

    async def _reconnect(self):
        """Riconnessione completa: nuova listenKey + nuovo WS."""
        try:
            # Cancella la vecchia listenKey
            if self._listen_key:
                try:
                    async with httpx.AsyncClient() as client:
                        await client.delete(
                            f"{self._base_url}/api/v3/userDataStream",
                            params={"listenKey": self._listen_key},
                            headers={"X-MBX-APIKEY": self._api_key},
                        )
                except Exception:
                    pass

            # Crea nuova listenKey
            await self._create_listen_key()
            new_key = self._listen_key or ""
            self._ws_url = f"{self._ws_base}/{new_key}"
            logger.info(f"Reconnected with new listenKey: {new_key[:8]}...")
        except Exception as e:
            logger.error(f"Reconnect failed: {e}")
            raise

    async def _dispatch_message(self, data: Dict[str, Any]):
        """Analizza e dispatches i messaggi ricevuti dal WebSocket.

        I messaggi che ci interessano sono solo executionReport con:
        - e: "executionReport"
        - X: "FILLED" o "EXPIRED" (order status)

        Altri tipi di messaggi (outboundAccountPosition, balanceUpdate, etc.)
        vengono ignorati perché non rilevanti per la chiusura trade.
        """
        event_type = data.get("e")

        if event_type == "executionReport":
            order_status = data.get("X")  # "FILLED", "EXPIRED", "NEW", etc.
            order_side = data.get("S")     # "BUY" o "SELL"
            order_id = str(data.get("i"))
            order_list_id = str(data.get("g", "-1"))
            symbol = data.get("s")
            fill_price = float(data.get("L", 0) or data.get("Z", 0) or 0)

            # Ci interessano solo ordini FILLED o EXPIRED (OCO cancellato)
            if order_status not in ("FILLED", "EXPIRED"):
                return

            # Log OCO fill with visibility
            if order_list_id != "-1":
                color = "92" if order_status == "FILLED" else "93"
                logger.info(f"\033[{color}m⚡ OCO {order_status}: {symbol} orderId={order_id} orderListId={order_list_id} @ {fill_price}\033[0m")

            # Dispatch all'handler se registrato
            if self._on_order_update:
                try:
                    await self._on_order_update({
                        "symbol": symbol,
                        "side": order_side,
                        "order_id": order_id,
                        "order_list_id": order_list_id,
                        "status": order_status.lower(),
                        "fill_price": fill_price,
                    })
                except Exception as e:
                    logger.error(f"[UDS] Handler error: {e}")

        elif event_type == "outboundAccountPosition":
            # Aggiornamento balance — non ci serve per la chiusura trade
            pass
        else:
            logger.debug(f"[UDS] Ignored event type: {event_type}")