#!/usr/bin/env python3
"""OKX Demo Trading spike for SynthTrade TASK-1100.

Default mode is read-only:
- load OKX demo credentials from synthtrade/backend/.env
- verify public instruments
- verify private auth via balance
- try fee tier lookup

Order placement requires an explicit --place-market-order flag.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import hmac
import json
import os
import sys
import time
import traceback
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ENV = PROJECT_ROOT / "synthtrade" / "backend" / ".env"
DEFAULT_SYMBOL = "BTC/EUR"
OKX_BASE_URL = "https://eea.okx.com"


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ[key] = value


def _mask(value: str | None) -> str:
    if not value:
        return "<missing>"
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


@dataclass
class StepResult:
    name: str
    ok: bool
    details: dict[str, Any]


class SpikeRecorder:
    def __init__(self) -> None:
        self.results: list[StepResult] = []

    def add(self, name: str, ok: bool, **details: Any) -> None:
        stored_details = {
            key: _mask(str(value))
            if key.lower() in {"api_key", "secret", "passphrase"}
            else value
            for key, value in details.items()
        }
        self.results.append(StepResult(name=name, ok=ok, details=stored_details))
        status = "OK" if ok else "FAIL"
        print(f"[{status}] {name}")
        for key, value in stored_details.items():
            print(f"  - {key}: {value}")

    def write_report(self, path: Path) -> None:
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "task": "TASK-1100",
            "results": [asdict(r) for r in self.results],
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nReport written: {path}")


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


async def _build_exchange() -> Any:
    try:
        import ccxt.async_support as ccxt
    except ImportError as exc:
        raise RuntimeError("ccxt is not installed. Install backend requirements first.") from exc

    api_key = _require_env("OKX_API_KEY")
    secret = _require_env("OKX_SECRET_KEY")
    passphrase = _require_env("OKX_PASSPHRASE")

    config: dict[str, Any] = {
        "apiKey": api_key,
        "secret": secret,
        "password": passphrase,
        "enableRateLimit": True,
        "headers": {
            "x-simulated-trading": "1",
        },
        "options": {
            "defaultType": "spot",
            # TASK-1100 fix: OKX Demo has instruments with base=None (margin/futures)
            # Restricting to SPOT avoids parse_market() crash in load_markets().
            "fetchMarkets": ["spot"],
        },
    }
    exchange = ccxt.okx(config)
    exchange.set_sandbox_mode(True)
    # Keep the header explicit even after set_sandbox_mode, because historical
    # ccxt OKX sandbox behavior has varied across versions.
    exchange.headers = {
        **getattr(exchange, "headers", {}),
        "x-simulated-trading": "1",
    }
    return exchange


class OkxRestClient:
    def __init__(self) -> None:
        self.api_key = _require_env("OKX_API_KEY")
        self.secret = _require_env("OKX_SECRET_KEY")
        self.passphrase = _require_env("OKX_PASSPHRASE")

    @staticmethod
    def _timestamp() -> str:
        now = datetime.now(timezone.utc)
        return now.isoformat(timespec="milliseconds").replace("+00:00", "Z")

    def _sign(self, timestamp: str, method: str, request_path: str, body: str = "") -> str:
        prehash = f"{timestamp}{method.upper()}{request_path}{body}"
        digest = hmac.new(
            self.secret.encode("utf-8"),
            prehash.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return base64.b64encode(digest).decode("ascii")

    async def request(
        self,
        method: str,
        request_path: str,
        *,
        auth: bool = False,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        import httpx

        method_upper = method.upper()
        body_text = json.dumps(body, separators=(",", ":")) if body else ""
        headers = {
            "Content-Type": "application/json",
            "x-simulated-trading": "1",
        }
        if auth:
            timestamp = self._timestamp()
            headers.update({
                "OK-ACCESS-KEY": self.api_key,
                "OK-ACCESS-SIGN": self._sign(timestamp, method_upper, request_path, body_text),
                "OK-ACCESS-TIMESTAMP": timestamp,
                "OK-ACCESS-PASSPHRASE": self.passphrase,
            })

        async with httpx.AsyncClient(base_url=OKX_BASE_URL, timeout=20.0) as client:
            response = await client.request(
                method_upper,
                request_path,
                headers=headers,
                content=body_text if body_text else None,
            )
            try:
                payload = response.json()
            except Exception:
                payload = {"raw_text": response.text}
            if isinstance(payload, dict):
                payload["_http_status"] = response.status_code
            return payload


def _okx_inst_id(symbol: str) -> str:
    return symbol.replace("/", "-").upper()


# ── 1100.G — WS private: login + orders channel ───────────────────────────

async def spike_ws_private(recorder: SpikeRecorder, timeout: float) -> None:
    """Login to OKX private WS, subscribe to orders + algo-orders, collect events."""
    import websockets

    api_key = _require_env("OKX_API_KEY")
    secret = _require_env("OKX_SECRET_KEY")
    passphrase = _require_env("OKX_PASSPHRASE")

    ts = str(int(time.time()))
    prehash = ts + "GET" + "/users/self/verify"
    sig = base64.b64encode(
        hmac.new(secret.encode(), prehash.encode(), hashlib.sha256).digest()
    ).decode()

    login_msg = json.dumps({
        "op": "login",
        "args": [{"apiKey": api_key, "passphrase": passphrase,
                  "timestamp": ts, "sign": sig}],
    })
    sub_msg = json.dumps({
        "op": "subscribe",
        "args": [
            {"channel": "orders", "instType": "SPOT"},
            {"channel": "algo-orders", "instType": "SPOT"},
        ],
    })

    ws_url = "wss://wspap.okx.com/ws/v5/private?brokerId=9999"
    events_received: list[dict] = []
    login_ok = False
    sub_ok = False

    try:
        async with websockets.connect(ws_url, ping_interval=None, open_timeout=10) as ws:
            await ws.send(login_msg)
            # Wait for login response
            raw = await asyncio.wait_for(ws.recv(), timeout=10)
            resp = json.loads(raw)
            login_ok = resp.get("event") == "login" and resp.get("code") == "0"
            recorder.add(
                "1100G_ws_private_login",
                login_ok,
                event=resp.get("event"),
                code=resp.get("code"),
                msg=resp.get("msg"),
                url=ws_url,
            )
            if not login_ok:
                return

            await ws.send(sub_msg)

            # Collect events for `timeout` seconds
            deadline = asyncio.get_event_loop().time() + timeout
            while asyncio.get_event_loop().time() < deadline:
                remaining = deadline - asyncio.get_event_loop().time()
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=min(remaining, 5))
                    msg = json.loads(raw) if raw != "pong" else {"pong": True}
                    ch = msg.get("arg", {}).get("channel", "")
                    ev = msg.get("event", "")
                    if ev == "subscribe":
                        sub_ok = True
                    if ch in ("orders", "algo-orders") and msg.get("data"):
                        events_received.extend(msg["data"])
                except asyncio.TimeoutError:
                    break

    except Exception as exc:
        recorder.add("1100G_ws_private_login", False, error=repr(exc), url=ws_url)
        return

    recorder.add(
        "1100G_ws_private_subscribe",
        sub_ok,
        channels=["orders", "algo-orders"],
        events_received=len(events_received),
        sample_event=events_received[0] if events_received else None,
        note="No events expected unless an order was placed during the window",
    )


# ── 1100.H — WS public: trades channel for CVD ───────────────────────────

async def spike_ws_public_trades(recorder: SpikeRecorder, symbol: str, timeout: float) -> None:
    """Subscribe to OKX public trades channel, verify side field for CVD mapping."""
    import websockets

    inst_id = _okx_inst_id(symbol)
    # Try demo first, fallback to EU live public WS (no auth needed for public)
    ws_urls = [
        "wss://wspap.okx.com/ws/v5/public?brokerId=9999",  # demo
        "wss://wsaws.okx.com:8443/ws/v5/public",            # EU live public
    ]
    sub_msg = json.dumps({
        "op": "subscribe",
        "args": [{"channel": "trades", "instId": inst_id}],
    })

    trades: list[dict] = []
    sub_ok = False
    used_url = ""

    for ws_url in ws_urls:
        trades = []
        sub_ok = False
        used_url = ws_url
        try:
            async with websockets.connect(ws_url, ping_interval=None, open_timeout=10) as ws:
                await ws.send(sub_msg)
                deadline = asyncio.get_event_loop().time() + timeout
                while asyncio.get_event_loop().time() < deadline:
                    remaining = deadline - asyncio.get_event_loop().time()
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=min(remaining, 5))
                        if raw == "pong":
                            continue
                        msg = json.loads(raw)
                        if msg.get("event") == "subscribe":
                            sub_ok = True
                            continue
                        if msg.get("arg", {}).get("channel") == "trades":
                            trades.extend(msg.get("data", []))
                    except asyncio.TimeoutError:
                        break
        except Exception as exc:
            recorder.add(f"1100H_ws_connect_{ws_url[-20:]}", False, error=repr(exc))
            continue
        if trades:
            break  # got data, stop trying

    # Analyse side field for CVD mapping
    buy_count = sum(1 for t in trades if t.get("side") == "buy")
    sell_count = sum(1 for t in trades if t.get("side") == "sell")
    sample = trades[:3] if trades else []
    # Verify expected fields present
    required_fields = {"tradeId", "px", "sz", "side", "ts"}
    fields_ok = all(required_fields.issubset(t.keys()) for t in sample) if sample else False

    recorder.add(
        "1100H_ws_public_trades",
        sub_ok and len(trades) > 0,
        inst_id=inst_id,
        url_used=used_url,
        subscribed=sub_ok,
        trades_received=len(trades),
        buy_side_count=buy_count,
        sell_side_count=sell_count,
        required_fields_present=fields_ok,
        cvd_mapping="side=buy -> is_buyer_maker=False (aggressive buy); side=sell -> is_buyer_maker=True",
        sample_trades=sample,
        note="side field is TAKER side on OKX",
    )


def _extract_raw_instrument(data: dict[str, Any]) -> dict[str, Any] | None:
    rows = data.get("data") or []
    return rows[0] if rows else None


def _extract_symbol_rules(market: dict[str, Any]) -> dict[str, Any]:
    info = market.get("info") or {}
    return {
        "symbol": market.get("symbol"),
        "id": market.get("id"),
        "base": market.get("base"),
        "quote": market.get("quote"),
        "active": market.get("active"),
        "spot": market.get("spot"),
        "lotSz": info.get("lotSz"),
        "minSz": info.get("minSz"),
        "tickSz": info.get("tickSz"),
        "maxMktSz": info.get("maxMktSz"),
        "maxMktAmt": info.get("maxMktAmt"),
        "state": info.get("state"),
    }


async def run_spike(args: argparse.Namespace) -> int:
    _load_env_file(BACKEND_ENV)
    recorder = SpikeRecorder()

    recorder.add(
        "credentials_present",
        all(os.environ.get(k) for k in ("OKX_API_KEY", "OKX_SECRET_KEY", "OKX_PASSPHRASE")),
        api_key=os.environ.get("OKX_API_KEY"),
        secret=os.environ.get("OKX_SECRET_KEY"),
        passphrase=os.environ.get("OKX_PASSPHRASE"),
        env_file=str(BACKEND_ENV),
    )

    rest = OkxRestClient()
    exchange = None
    try:
        for symbol in args.symbols:
            inst_id = _okx_inst_id(symbol)
            instrument = await rest.request(
                "GET",
                f"/api/v5/public/instruments?instType=SPOT&instId={inst_id}",
            )
            market = _extract_raw_instrument(instrument)
            recorder.add(
                f"instrument_{symbol}",
                market is not None,
                inst_id=inst_id,
                http_status=instrument.get("_http_status"),
                raw_code=instrument.get("code"),
                raw_msg=instrument.get("msg"),
                rules={
                    "instId": market.get("instId"),
                    "baseCcy": market.get("baseCcy"),
                    "quoteCcy": market.get("quoteCcy"),
                    "state": market.get("state"),
                    "lotSz": market.get("lotSz"),
                    "minSz": market.get("minSz"),
                    "tickSz": market.get("tickSz"),
                    "maxMktSz": market.get("maxMktSz"),
                    "maxMktAmt": market.get("maxMktAmt"),
                } if market else None,
            )

        all_spot = await rest.request("GET", "/api/v5/public/instruments?instType=SPOT")
        all_rows = all_spot.get("data") or []
        eur_rows = [
            row.get("instId")
            for row in all_rows
            if row.get("quoteCcy") == "EUR" and row.get("state") == "live"
        ]
        recorder.add(
            "instrument_discovery_summary",
            all_spot.get("code") == "0",
            http_status=all_spot.get("_http_status"),
            total_spot=len(all_rows),
            live_eur_count=len(eur_rows),
            live_eur_examples=eur_rows[:20],
        )

        server_time = await rest.request("GET", "/api/v5/public/time")
        recorder.add("public_time", server_time.get("code") == "0", raw=server_time)

        balance = await rest.request("GET", "/api/v5/account/balance", auth=True)
        balances = balance.get("data") or []
        details = balances[0].get("details", []) if balances else []
        nonzero = [
            {
                "ccy": row.get("ccy"),
                "cashBal": row.get("cashBal"),
                "availBal": row.get("availBal"),
                "eq": row.get("eq"),
            }
            for row in details
            if float(row.get("eq") or 0) > 0
        ]
        recorder.add(
            "private_balance",
            balance.get("code") == "0" and balance.get("_http_status") == 200,
            nonzero_assets=nonzero,
            total_assets=len(details),
            http_status=balance.get("_http_status"),
            raw_code=balance.get("code"),
            raw_msg=balance.get("msg"),
            raw_text=balance.get("raw_text"),
        )

        fee_symbol = args.symbols[0]
        fee_inst_id = _okx_inst_id(fee_symbol)
        try:
            fee = await rest.request(
                "GET",
                f"/api/v5/account/trade-fee?instType=SPOT&instId={fee_inst_id}",
                auth=True,
            )
            fee_row = (fee.get("data") or [{}])[0]
            recorder.add(
                f"fee_tier_{fee_symbol}",
                fee.get("code") == "0",
                maker=fee_row.get("maker") or fee_row.get("makerU"),
                taker=fee_row.get("taker") or fee_row.get("takerU"),
                raw=fee,
            )
        except Exception as exc:
            recorder.add(f"fee_tier_{fee_symbol}", False, error=repr(exc))

        ticker_inst_id = _okx_inst_id(args.symbols[0])
        ticker = await rest.request("GET", f"/api/v5/market/ticker?instId={ticker_inst_id}")
        ticker_row = (ticker.get("data") or [{}])[0]
        recorder.add(
            f"ticker_{args.symbols[0]}",
            ticker.get("code") == "0" and bool(ticker_row.get("last")),
            last=ticker_row.get("last"),
            bid=ticker_row.get("bidPx"),
            ask=ticker_row.get("askPx"),
            raw=ticker_row,
        )

        if args.place_market_order:
            if args.market_quote_amount <= 0:
                raise RuntimeError("--market-quote-amount must be > 0 when placing an order")

            # ── 1100.E — Market order minimo via REST diretto ─────────────────
            # NOTE: ccxt load_markets() crasha su OKX Demo con base=None per strumenti
            # non-spot. Usiamo OkxRestClient direttamente che funziona già perfettamente.
            inst_id = _okx_inst_id(args.symbols[0])
            order_body = {
                "instId": inst_id,
                "tdMode": "cash",
                "side": "buy",
                "ordType": "market",
                "sz": str(args.market_quote_amount),
                "tgtCcy": "quote_ccy",  # sz is in quote (EUR), OKX calculates base qty
            }
            order_resp = await rest.request("POST", "/api/v5/trade/order", auth=True, body=order_body)
            order_data = (order_resp.get("data") or [{}])[0]
            entry_order_id = str(order_data.get("ordId", ""))
            order_ok = order_resp.get("code") == "0" and bool(entry_order_id)

            # Fetch order details to get fill price and qty
            filled_qty = 0.0
            avg_price = 0.0
            if order_ok:
                import asyncio as _asyncio
                await _asyncio.sleep(1.0)  # wait for fill
                detail_resp = await rest.request(
                    "GET",
                    f"/api/v5/trade/order?instId={inst_id}&ordId={entry_order_id}",
                    auth=True,
                )
                detail = (detail_resp.get("data") or [{}])[0]
                filled_qty = float(detail.get("accFillSz") or 0)
                avg_price = float(detail.get("avgPx") or 0)
                fee_raw = float(detail.get("fee") or 0)
                fee_ccy = detail.get("feeCcy", "")

            recorder.add(
                "1100E_market_order_demo",
                order_ok,
                order_id=entry_order_id,
                raw_code=order_resp.get("code"),
                raw_msg=order_resp.get("msg"),
                inst_id=inst_id,
                side="buy",
                quote_amount=args.market_quote_amount,
                filled_base_qty=filled_qty,
                avg_price=avg_price,
                fee=fee_raw if order_ok else None,
                fee_ccy=fee_ccy if order_ok else None,
                method="rest_direct",
                note="Used OkxRestClient REST to avoid ccxt load_markets crash in demo",
            )

            # ── 1100.F — Exit bracket (algo order TP/SL) via REST ─────────────
            if filled_qty > 0 and avg_price > 0 and args.place_bracket:
                tp_price = round(avg_price * 1.005, 1)   # +0.5%
                sl_price = round(avg_price * 0.997, 1)   # -0.3%
                algo_body = {
                    "instId": inst_id,
                    "tdMode": "cash",
                    "side": "sell",
                    "ordType": "oco",
                    "sz": str(filled_qty),
                    "tpTriggerPx": str(tp_price),
                    "tpOrdPx": "-1",        # market order at trigger
                    "slTriggerPx": str(sl_price),
                    "slOrdPx": "-1",        # market order at trigger
                    "tpTriggerPxType": "last",
                    "slTriggerPxType": "last",
                }
                algo_resp = await rest.request(
                    "POST", "/api/v5/trade/order-algo",
                    auth=True, body=algo_body,
                )
                algo_data = (algo_resp.get("data") or [{}])[0]
                algo_id = str(algo_data.get("algoId", ""))
                recorder.add(
                    "1100F_exit_bracket_demo",
                    algo_resp.get("code") == "0" and bool(algo_id),
                    algo_id=algo_id,
                    raw_code=algo_resp.get("code"),
                    raw_msg=algo_resp.get("msg"),
                    tp_price=tp_price,
                    sl_price=sl_price,
                    qty=filled_qty,
                    entry_order_id=entry_order_id,
                    method="rest_order_algo",
                )
            elif args.place_bracket:
                recorder.add(
                    "1100F_exit_bracket_demo",
                    False,
                    skipped=True,
                    reason="market order did not fill (filled_qty=0 or avg_price=0)",
                )
        else:
            recorder.add(
                "1100E_market_order_demo",
                True,
                skipped=True,
                reason="read-only default; rerun with --place-market-order",
            )
            recorder.add(
                "1100F_exit_bracket_demo",
                True,
                skipped=True,
                reason="requires --place-market-order --place-bracket",
            )

        # ── 1100.G ── WS private ────────────────────────────────────────────
        if args.test_ws_private:
            await spike_ws_private(recorder, args.ws_timeout)
        else:
            recorder.add("1100G_ws_private_login", True, skipped=True,
                         reason="rerun with --test-ws-private")

        # ── 1100.H ── WS public trades ───────────────────────────────────────
        if args.test_ws_public:
            await spike_ws_public_trades(recorder, args.symbols[0], args.ws_timeout)
        else:
            recorder.add("1100H_ws_public_trades", True, skipped=True,
                         reason="rerun with --test-ws-public")

    except Exception as exc:
        recorder.add("spike_exception", False, error=repr(exc), traceback=traceback.format_exc())
        return_code = 1
    else:
        return_code = 0
    finally:
        if exchange is not None:
            await exchange.close()
        recorder.write_report(PROJECT_ROOT / "docs" / "analysis" / "okx-demo-spike-results.json")

    return return_code


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OKX Demo Trading spike for SynthTrade.")
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=[DEFAULT_SYMBOL, "ETH/EUR"],
        help="CCXT symbols to inspect. Default: OKB/EUR BNB/USDC",
    )
    parser.add_argument(
        "--place-market-order",
        action="store_true",
        help="Actually place a demo market buy using --market-quote-amount.",
    )
    parser.add_argument(
        "--market-quote-amount",
        type=float,
        default=10.0,
        help="Quote amount for demo market buy when --place-market-order is set.",
    )
    parser.add_argument(
        "--place-bracket",
        action="store_true",
        help="After market order, place TP/SL bracket (requires --place-market-order).",
    )
    parser.add_argument(
        "--test-ws-private",
        action="store_true",
        help="Test private WS login + orders channel (1100.G). Listens for --ws-timeout seconds.",
    )
    parser.add_argument(
        "--test-ws-public",
        action="store_true",
        help="Test public WS trades channel for CVD (1100.H). Listens for --ws-timeout seconds.",
    )
    parser.add_argument(
        "--ws-timeout",
        type=float,
        default=15.0,
        help="Seconds to listen on WS before disconnecting (default: 15).",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    return asyncio.run(run_spike(args))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
