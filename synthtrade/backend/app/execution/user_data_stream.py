"""UserDataStreamManager — Binance User Data Stream WebSocket (API v2).

Binance ha deprecato l'endpoint REST /api/v3/userDataStream (listenKey).
Il nuovo metodo usa il WebSocket API con autenticazione HMAC-SHA256:

1. Connetti a wss://ws-api.binance.com:443/ws-api/v3
2. Invia userDataStream.subscribe.signature con apiKey + timestamp + signature
3. Ricevi eventi executionReport via WS
4. Su disconnessione → riconnetti e reinvia la subscribe request
5. Su ogni executionReport con orderStatus FILLED/EXPIRED → dispatch all'handler

Riferimento: https://developers.binance.com/docs/binance-spot-api-docs/websocket-api/user-data-stream-requests

TASK-824: Implementato per risolvere il disallineamento trade log vs Binance.
FIX-2026-06-12: Migrato da listenKey REST (410 Gone) a WS API con firma HMAC.
TASK-876: Catturare commissione reale dal WebSocket (campi n e N).
"""

import asyncio
import hashlib
import hmac
import json
import logging
import time
import uuid
from typing import Callable, Optional, Dict, Any

logger = logging.getLogger(__name__)


class UserDataStreamError(Exception):
    """Errore generico del User Data Stream."""
    pass


class UserDataStreamManager:
    """Manages Binance User Data Stream lifecycle via WebSocket API.

    Usage:
        uds = UserDataStreamManager(api_key="xxx", api_secret="yyy")
        await uds.start(on_order_update=my_handler)
        # ... session runs ...
        await uds.stop()
    """

    # Binance WebSocket API endpoints
    LIVE_WS_API = "wss://ws-api.binance.com:443/ws-api/v3"
    TESTNET_WS_API = "wss://testnet.binance.vision/ws-api/v3"

    RECONNECT_DELAY = 5  # secondi prima di riconnettere

    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        self._api_key = api_key
        self._api_secret = api_secret
        self._testnet = testnet

        self._ws_url = self.TESTNET_WS_API if testnet else self.LIVE_WS_API
        self._running = False
        self._ws_connection = None
        self._on_order_update: Optional[Callable] = None
        self._on_reconnect_sync: Optional[Callable] = None  # TASK-830
        self._listen_task: Optional[asyncio.Task] = None
        self._subscription_id: Optional[int] = None

    def _sign(self, params: Dict[str, Any]) -> str:
        """Genera la firma HMAC-SHA256 per i parametri della request."""
        query = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        return hmac.new(
            self._api_secret.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _build_subscribe_request(self) -> Dict[str, Any]:
        """Costruisce la request userDataStream.subscribe.signature."""
        req_id = str(uuid.uuid4())
        timestamp = int(time.time() * 1000)
        params: Dict[str, Any] = {
            "apiKey": self._api_key,
            "timestamp": timestamp,
        }
        params["signature"] = self._sign(params)
        return {
            "id": req_id,
            "method": "userDataStream.subscribe.signature",
            "params": params,
        }

    async def start(self, on_order_update: Callable, on_reconnect_sync: Optional[Callable] = None):
        """Avvia il User Data Stream.

        Args:
            on_order_update: Callable async che riceve il dict dell'executionReport.
                Verrà chiamata ogni volta che un ordine viene FILLED o EXPIRED.
            on_reconnect_sync: Callable async opzionale (TASK-830).
                Verrà chiamata dopo ogni riconnessione per verificare se
                l'OCO è stato eseguito durante la finestra di disconnessione.
        """
        if self._running:
            logger.warning("UserDataStream already running")
            return

        self._on_order_update = on_order_update
        self._on_reconnect_sync = on_reconnect_sync
        self._running = True

        self._listen_task = asyncio.create_task(
            self._listen_loop(),
            name="uds-listen"
        )
        logger.info("UserDataStream avviato (WS API mode)")

    async def stop(self):
        """Ferma il User Data Stream."""
        self._running = False

        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        self._listen_task = None

        if self._ws_connection:
            try:
                await self._ws_connection.close()
            except Exception:
                pass
            self._ws_connection = None

        logger.info("UserDataStream fermato")

    async def _listen_loop(self):
        """Loop principale: connette, sottoscrive, riceve eventi, riconnette."""
        import websockets

        while self._running:
            try:
                logger.info(f"UDS: Connecting to {self._ws_url}...")
                async with websockets.connect(
                    self._ws_url,
                    ping_interval=20,
                    ping_timeout=30,
                ) as ws:
                    self._ws_connection = ws

                    # Invia la subscribe request con firma
                    sub_req = self._build_subscribe_request()
                    await ws.send(json.dumps(sub_req))
                    logger.info(f"UDS: subscribe.signature inviata (id={sub_req['id'][:8]}...)")

                    # Attendi la risposta di conferma
                    try:
                        resp_raw = await asyncio.wait_for(ws.recv(), timeout=10)
                        resp = json.loads(resp_raw)
                        if resp.get("status") == 200:
                            result = resp.get("result", {})
                            self._subscription_id = result.get("subscriptionId")
                            logger.info(
                                f"\033[96m📡 UDS SOCKET ATTIVO: subscriptionId={self._subscription_id}\033[0m"
                            )
                        else:
                            logger.error(f"UDS subscribe failed: {resp}")
                            raise UserDataStreamError(f"Subscribe failed: {resp}")
                    except asyncio.TimeoutError:
                        raise UserDataStreamError("UDS subscribe response timeout")

                    # Loop ricezione eventi
                    while self._running:
                        try:
                            message = await asyncio.wait_for(ws.recv(), timeout=60)
                            data = json.loads(message)
                            await self._dispatch_message(data)
                        except asyncio.TimeoutError:
                            # Timeout normale — ping/pong gestito da websockets
                            continue
                        except websockets.exceptions.ConnectionClosed:
                            logger.warning("UDS WebSocket disconnesso")
                            break

            except UserDataStreamError:
                raise  # Non riconnettere su errori di autenticazione
            except Exception as e:
                logger.error(f"UDS error: {e}")
                if self._running:
                    logger.info(f"UDS: riconnessione in {self.RECONNECT_DELAY}s...")
                    await asyncio.sleep(self.RECONNECT_DELAY)

                    # TASK-830: dopo la riconnessione, verifica OCO eseguito durante disconnessione
                    if self._on_reconnect_sync:
                        try:
                            await self._on_reconnect_sync()
                        except Exception as sync_e:
                            logger.warning(f"UDS reconnect sync failed (non-fatal): {sync_e}")
            finally:
                self._ws_connection = None

    async def _dispatch_message(self, data: Dict[str, Any]):
        """Analizza i messaggi del WebSocket API Binance.

        Il WebSocket API wrappa gli eventi in un oggetto con campo "event":
        {
            "subscriptionId": 0,
            "event": { "e": "executionReport", ... }
        }

        Gestisce anche i messaggi diretti (no wrapper) per compatibilità.
        """
        # Il WS API wrappa gli eventi in { "subscriptionId": N, "event": {...} }
        if "event" in data:
            event = data["event"]
        else:
            event = data  # fallback per messaggi non wrappati

        event_type = event.get("e")

        if event_type == "executionReport":
            order_status = event.get("X")  # "FILLED", "EXPIRED", "NEW", etc.
            order_side = event.get("S")    # "BUY" o "SELL"
            order_id = str(event.get("i"))
            order_list_id = str(event.get("g", "-1"))
            symbol = event.get("s")
            # L: last executed price; Z: cumulative quote qty (fallback)
            fill_price = float(event.get("L", 0) or event.get("Z", 0) or 0)
            # TASK-876: cattura commissione reale dal payload Binance
            commission = float(event.get("n", 0) or 0)
            commission_asset = event.get("N")

            # Ci interessano solo FILLED o EXPIRED
            if order_status not in ("FILLED", "EXPIRED"):
                return

            if order_list_id != "-1":
                if order_status == "FILLED":
                    logger.info(
                        f"\033[92m🟢 OCO FILLED: {symbol} "
                        f"orderId={order_id} orderListId={order_list_id} @ {fill_price}\033[0m"
                    )
                elif order_status == "EXPIRED":
                    logger.info(
                        f"\033[93m🟡 OCO EXPIRED: {symbol} "
                        f"orderId={order_id} orderListId={order_list_id}\033[0m"
                    )

            if self._on_order_update:
                try:
                    await self._on_order_update({
                        "symbol": symbol,
                        "side": order_side,
                        "order_id": order_id,
                        "order_list_id": order_list_id,
                        "status": order_status.lower(),
                        "fill_price": fill_price,
                        "commission": commission,  # TASK-876
                        "commission_asset": commission_asset,  # TASK-876
                        "leg": "take_profit" if order_id and order_list_id != "-1" and self._is_tp_order(order_id, order_list_id) else "stop_loss" if order_id and order_list_id != "-1" and self._is_sl_order(order_id, order_list_id) else "oco",
                    })
                except Exception as e:
                    logger.error(f"[UDS] Handler error: {e}")

        elif event_type == "outboundAccountPosition":
            pass  # Balance update — non necessario
        elif event_type == "eventStreamTerminated":
            logger.warning("[UDS] eventStreamTerminated ricevuto — riconnessione necessaria")
            raise ConnectionError("UDS stream terminated by Binance")
        else:
            logger.debug(f"[UDS] Ignored event: {event_type}")

    def _is_tp_order(self, order_id: str, order_list_id: str) -> bool:
        """Controlla se l'orderId ricevuto corrisponde al TP salvato."""
        from app.scalping.router import _execution_state
        pos = _execution_state.get("position_manager", type("PM", (), {"get_open": lambda self: None})()).get_open()
        if not pos or pos.oco_order_list_id != order_list_id:
            return False
        return bool(pos.tp_order_id and str(pos.tp_order_id) == str(order_id))

    def _is_sl_order(self, order_id: str, order_list_id: str) -> bool:
        """Controlla se l'orderId ricevuto corrisponde allo SL salvato."""
        from app.scalping.router import _execution_state
        pos = _execution_state.get("position_manager", type("PM", (), {"get_open": lambda self: None})()).get_open()
        if not pos or pos.oco_order_list_id != order_list_id:
            return False
        return bool(pos.sl_order_id and str(pos.sl_order_id) == str(order_id))
