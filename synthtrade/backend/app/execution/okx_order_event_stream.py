"""
TASK-1106: OkxOrderEventStream — OKX private WebSocket order event stream.

Connects to OKX private WS, subscribes to orders and algo-orders channels,
normalizes fill events to the same dict contract as UserDataStreamManager:

    {
        "provider":          "okx",
        "symbol":            "BTC-EUR",          # OKX instId format
        "side":              "BUY" | "SELL",
        "order_id":          str,
        "bracket_id":        str | None,         # algoId if algo order
        "order_list_id":     str,                # bracket_id or "-1"
        "status":            "filled" | "expired" | "cancelled",
        "fill_price":        float,
        "commission":        float,
        "commission_asset":  str | None,
        "leg":               "take_profit" | "stop_loss" | "market" | "algo",
    }

OKX WS private endpoints:
  Demo:    wss://wspap.okx.com/ws/v5/private?brokerId=9999
  EU Live: wss://wsaws.okx.com:8443/ws/v5/private

Login: sign(timestamp + "GET" + "/users/self/verify", secret) with HMAC-SHA256.

Channels:
  orders      -> normal spot orders (market/limit)
  algo-orders -> TP/SL bracket orders (order-algo)

TASK-1100.G (WS fill spike) still pending — payload mapping marked UNVERIFIED
where OKX demo confirmation is missing.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)

_WS_DEMO = "wss://wspap.okx.com/ws/v5/private?brokerId=9999"
_WS_EU_LIVE = "wss://wspap.okx.com:8443/ws/v5/private"  # Changed from wsaws.okx.com to wspap.okx.com
_WS_LIVE = "wss://ws.okx.com:8443/ws/v5/private"

_PING_INTERVAL = 25
_RECONNECT_DELAY = 10  # seconds between reconnect attempts
_MAX_NOISY_FAILURES = 3  # after this many consecutive failures, log at DEBUG instead of WARNING


class OkxOrderEventStream:
    """
    OKX private WebSocket order event stream.

    Implements the same lifecycle interface as UserDataStreamManager:
        await stream.start(on_order_update, on_reconnect_sync)
        await stream.stop()

    Emits normalized order update dicts to on_order_update.
    """

    def __init__(
        self,
        api_key: str,
        secret: str,
        passphrase: str,
        demo: bool = True,
        eu: bool = True,
    ):
        self._api_key = api_key
        self._secret = secret
        self._passphrase = passphrase
        self._demo = demo
        self._eu = eu

        if demo:
            self._ws_url = _WS_DEMO
        elif eu:
            self._ws_url = _WS_EU_LIVE
        else:
            self._ws_url = _WS_LIVE

        self._running = False
        self._on_order_update: Optional[Callable] = None
        self._on_reconnect_sync: Optional[Callable] = None
        self._listen_task: Optional[asyncio.Task] = None
        self._consecutive_failures = 0  # suppress repeated WS failure spam

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(
        self,
        on_order_update: Callable,
        on_reconnect_sync: Optional[Callable] = None,
    ) -> None:
        if self._running:
            logger.warning("OkxOrderEventStream already running")
            return
        self._on_order_update = on_order_update
        self._on_reconnect_sync = on_reconnect_sync
        self._running = True
        self._listen_task = asyncio.create_task(
            self._listen_loop(), name="okx-order-stream"
        )
        logger.info("OkxOrderEventStream started (demo=%s)", self._demo)

    async def stop(self) -> None:
        self._running = False
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        self._listen_task = None
        logger.info("OkxOrderEventStream stopped")

    # ── Auth ──────────────────────────────────────────────────────────────────

    def _build_login_msg(self) -> dict:
        """
        OKX WS login: sign(timestamp + "GET" + "/users/self/verify") with HMAC-SHA256,
        then base64-encode.
        """
        ts = str(int(time.time()))
        prehash = ts + "GET" + "/users/self/verify"
        sig = base64.b64encode(
            hmac.new(
                self._secret.encode("utf-8"),
                prehash.encode("utf-8"),
                hashlib.sha256,
            ).digest()
        ).decode("utf-8")
        return {
            "op": "login",
            "args": [{
                "apiKey": self._api_key,
                "passphrase": self._passphrase,
                "timestamp": ts,
                "sign": sig,
            }],
        }

    # ── Connection loop ───────────────────────────────────────────────────────

    async def _listen_loop(self) -> None:
        import websockets

        while self._running:
            # TASK-XXXX: EU accounts (MiCA EEA license) cannot authenticate via WS private.
            # Skip the ~1s login attempt entirely and go directly to REST polling.
            if self._eu and not self._demo:
                logger.info("OKX order stream: EU account detected — WS private not available by design. Falling back to REST polling.")
                await self._start_polling()
                break
            
            try:
                async with websockets.connect(self._ws_url, ping_interval=None) as ws:
                    # Login
                    await ws.send(json.dumps(self._build_login_msg()))
                    resp_raw = await asyncio.wait_for(ws.recv(), timeout=10)
                    resp = json.loads(resp_raw)
                    if resp.get("event") != "login" or resp.get("code") != "0":
                        logger.error("OKX WS login failed: %s", resp)
                        raise ConnectionError(f"OKX WS login failed: {resp}")
                    logger.info("OKX order stream: logged in")

                    # Subscribe
                    await ws.send(json.dumps({
                        "op": "subscribe",
                        "args": [
                            {"channel": "orders", "instType": "SPOT"},
                            {"channel": "algo-orders", "instType": "SPOT"},
                        ],
                    }))

                    ping_task = asyncio.create_task(self._ping_loop(ws))
                    try:
                        async for raw in ws:
                            if self._stop_requested():
                                break
                            text = raw.decode() if isinstance(raw, bytes) else raw
                            if text == "pong":
                                continue
                            await self._dispatch(text)
                    finally:
                        ping_task.cancel()
                        await asyncio.gather(ping_task, return_exceptions=True)

            except asyncio.CancelledError:
                break
            except Exception as exc:
                if not self._running:
                    break
                
                if "60032" in str(exc):
                    logger.info("OKX WS private not available for this account (60032) — REST polling fallback active. This is expected for EU accounts.")
                    await self._start_polling()
                    break

                self._consecutive_failures += 1
                if self._consecutive_failures <= _MAX_NOISY_FAILURES:
                    logger.warning("OKX order stream disconnected (%s). Reconnect in %ds...",
                                   exc, _RECONNECT_DELAY)
                else:
                    logger.debug("OKX order stream disconnected (%s). Reconnect in %ds... [failure #%d, suppressing repeated warnings]",
                                 exc, _RECONNECT_DELAY, self._consecutive_failures)
                await asyncio.sleep(_RECONNECT_DELAY)

                if self._on_reconnect_sync:
                    try:
                        await self._on_reconnect_sync()
                    except Exception as sync_e:
                        logger.debug("OKX order stream reconnect sync failed: %s", sync_e)

    async def _start_polling(self) -> None:
        """Fallback polling loop using REST API."""
        logger.info("OKX order stream: starting REST polling fallback (2s interval)")
        seen_orders = set()
        seen_algos = set()
        
        # Seed con ordini storici esistenti (non emetterli)
        # NOTE: On OKX EU, algo orders (TP/SL) appear in orders-history with algoId populated
        # TASK-XXXX: Only seed completed orders (filled/cancelled). Do NOT seed pending algos
        # into seen_algos — when a pending algo fills, it reappears in orders-history with
        # state="filled" and the same algoId. If already in seen_algos, the fill is silently
        # skipped (the "seen_algos poisoning" bug that caused the 2026-07-15 TP miss).
        try:
            resp = await self._rest_request("GET", "/api/v5/trade/orders-history", params={"instType": "SPOT", "state": "filled"})
            for item in resp.get("data", []):
                oid = item.get("ordId")
                aid = item.get("algoId")
                if oid and not aid:
                    seen_orders.add(oid)
                if aid:
                    seen_algos.add(aid)
            logger.info("OKX REST polling: seeded %d historical orders, %d algo orders", len(seen_orders), len(seen_algos))
        except Exception as e:
            logger.warning("OKX REST polling: seed orders failed: %s", e)
        
        while self._running:
            try:
                # 1. Fetch pending (in-flight) orders — catches fills in real-time
                resp_pend = await self._rest_request("GET", "/api/v5/trade/orders-pending", params={"instType": "SPOT"})
                for item in resp_pend.get("data", []):
                    ord_id = item.get("ordId")
                    if ord_id and ord_id not in seen_orders:
                        seen_orders.add(ord_id)
                        norm = self._normalize_order(item)
                        if norm:
                            await self._emit(norm)
                
                # 2. Fetch recently completed orders (filled/cancelled)
                # NOTE: On OKX EU, algo orders (TP/SL) appear in orders-history with algoId populated
                # We need to check both regular orders and algo orders in one call
                resp_hist = await self._rest_request("GET", "/api/v5/trade/orders-history", params={"instType": "SPOT", "state": "filled"})
                for item in resp_hist.get("data", []):
                    ord_id = item.get("ordId")
                    algo_id = item.get("algoId")
                    
                    # Regular order (non-algo)
                    if ord_id and ord_id not in seen_orders and not algo_id:
                        seen_orders.add(ord_id)
                        norm = self._normalize_order(item)
                        if norm:
                            await self._emit(norm)
                    
                    # Algo order (TP/SL bracket)
                    if algo_id and algo_id not in seen_algos:
                        seen_algos.add(algo_id)
                        norm = self._normalize_algo_order(item)
                        if norm:
                            await self._emit(norm)
                
                # 3. Fetch algo orders pending/active (still need this for in-flight orders)
                resp_algo = await self._rest_request(
                    "GET", 
                    "/api/v5/trade/orders-algo-pending", 
                    params={"instType": "SPOT", "ordType": "oco"}
                )
                for item in resp_algo.get("data", []):
                    algo_id = item.get("algoId")
                    if algo_id and algo_id not in seen_algos:
                        norm = self._normalize_algo_order(item)
                        if norm:
                            await self._emit(norm)
                            # Add to seen_algos ONLY after successful emit to prevent
                            # skipping the fill when it later appears in orders-history
                            seen_algos.add(algo_id)
                
            except Exception as e:
                logger.error("OKX REST polling error: [%s] %s", type(e).__name__, e)
            
            # Sleep in chunks to allow fast shutdown
            for _ in range(10):
                if not self._running:
                    break
                await asyncio.sleep(0.2)

    async def _rest_request(self, method: str, request_path: str, params: dict | None = None) -> dict:
        import httpx
        import urllib.parse
        from datetime import datetime, timezone
        from app.config import settings

        if params:
            query = urllib.parse.urlencode(params)
            request_path = f"{request_path}?{query}"

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        prehash = ts + method.upper() + request_path
        sig = base64.b64encode(
            hmac.new(
                self._secret.encode("utf-8"),
                prehash.encode("utf-8"),
                hashlib.sha256,
            ).digest()
        ).decode("utf-8")

        headers = {
            "OK-ACCESS-KEY": self._api_key,
            "OK-ACCESS-SIGN": sig,
            "OK-ACCESS-TIMESTAMP": ts,
            "OK-ACCESS-PASSPHRASE": self._passphrase,
            "Content-Type": "application/json"
        }
        if self._demo:
            headers["x-simulated-trading"] = "1"

        base_url = settings.OKX_BASE_URL.rstrip("/")
        
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.request(method, base_url + request_path, headers=headers)
            resp.raise_for_status()
            return resp.json()

    def _stop_requested(self) -> bool:
        return not self._running

    async def _ping_loop(self, ws) -> None:
        while True:
            await asyncio.sleep(_PING_INTERVAL)
            try:
                await ws.send("ping")
            except Exception:
                break

    # ── Dispatch ──────────────────────────────────────────────────────────────

    async def _dispatch(self, raw: str) -> None:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("OKX order stream: invalid JSON: %s", raw[:100])
            return

        event_type = msg.get("event")
        if event_type in ("subscribe", "error"):
            logger.debug("OKX order stream event: %s", msg)
            return

        channel = msg.get("arg", {}).get("channel", "")
        data = msg.get("data", [])

        if channel == "orders":
            for item in data:
                normalized = self._normalize_order(item)
                if normalized:
                    await self._emit(normalized)
        elif channel == "algo-orders":
            for item in data:
                normalized = self._normalize_algo_order(item)
                if normalized:
                    await self._emit(normalized)

    async def _emit(self, event: dict) -> None:
        if self._on_order_update:
            try:
                await self._on_order_update(event)
            except Exception as e:
                logger.error("OKX order stream handler error: %s", e)

    # ── Normalizers ───────────────────────────────────────────────────────────

    @staticmethod
    def _normalize_order(item: dict) -> Optional[dict]:
        """
        Normalize OKX orders channel payload to router contract.

        OKX order states: live, partially_filled, filled, cancelled, mmp_canceled
        We emit only: filled, cancelled (mapped to "expired" for compat).

        UNVERIFIED: field names confirmed from OKX docs, not yet from live Demo payload.
        """
        state = item.get("state", "")
        if state not in ("filled", "cancelled"):
            return None

        inst_id = item.get("instId", "")
        side = item.get("side", "").upper()
        order_id = str(item.get("ordId", ""))
        # avgPx: average fill price; fillPx: last fill price
        fill_price = float(item.get("avgPx") or item.get("fillPx") or 0)
        # fee is negative on OKX (rebate); fillFee is the last fill fee
        fee_raw = float(item.get("fee") or item.get("fillFee") or 0)
        commission = abs(fee_raw)
        commission_asset = item.get("feeCcy") or item.get("fillFeeCcy")

        status = "filled" if state == "filled" else "expired"

        return {
            "provider": "okx",
            "symbol": inst_id,
            "side": side,
            "order_id": order_id,
            "bracket_id": None,
            "order_list_id": "-1",
            "status": status,
            "fill_price": fill_price,
            "commission": commission,
            "commission_asset": commission_asset,
            "leg": "market",
        }

    @staticmethod
    def _normalize_algo_order(item: dict) -> Optional[dict]:
        """
        Normalize OKX algo-orders channel payload (TP/SL bracket).

        OKX algo states: live, pause, partially_effective, effective, canceled, order_failed
        We emit on: effective (filled), canceled, filled (from orders-history).

        algoClOrdId / algoId: bracket identifier
        tpOrdId / slOrdId: individual leg order IDs (UNVERIFIED: may not be in WS payload)

        NOTE: When called from orders-history (OKX EU fallback), state="filled" and algoId is populated.
        """
        state = item.get("state", "")
        # Accept both algo states (effective) and regular order states (filled)
        if state not in ("effective", "canceled", "order_failed", "filled"):
            return None

        inst_id = item.get("instId", "")
        side = item.get("side", "").upper()
        algo_id = str(item.get("algoId", ""))
        order_id = str(item.get("ordId") or algo_id)

        fill_price = float(item.get("avgPx") or item.get("fillPx") or 0)
        fee_raw = float(item.get("fee") or item.get("fillFee") or 0)
        commission = abs(fee_raw)
        commission_asset = item.get("feeCcy") or item.get("fillFeeCcy")

        status = "filled" if state in ("effective", "filled") else "expired"

        # Determine leg: prefer tpTriggerPx/slTriggerPx (reliable for OCO,
        # where ordType is "oco" and doesn't contain "tp"/"sl").
        tp_trigger = item.get("tpTriggerPx")
        sl_trigger = item.get("slTriggerPx")
        if tp_trigger and str(tp_trigger) not in ("", "0", "0.0"):
            leg = "take_profit"
        elif sl_trigger and str(sl_trigger) not in ("", "0", "0.0"):
            leg = "stop_loss"
        else:
            ord_type = item.get("ordType", "")
            if "tp" in ord_type.lower():
                leg = "take_profit"
            elif "sl" in ord_type.lower():
                leg = "stop_loss"
            else:
                leg = "algo"

        return {
            "provider": "okx",
            "symbol": inst_id,
            "side": side,
            "order_id": order_id,
            "bracket_id": algo_id,
            "order_list_id": algo_id,  # used by router to match bracket
            "status": status,
            "fill_price": fill_price,
            "commission": commission,
            "commission_asset": commission_asset,
            "leg": leg,
        }

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def from_settings(cls) -> "OkxOrderEventStream":
        from app.config import settings
        return cls(
            api_key=settings.exchange_api_key,
            secret=settings.exchange_secret_key,
            passphrase=settings.exchange_passphrase,
            demo=settings.exchange_demo,
            eu=True,
        )
