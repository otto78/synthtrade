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
import traceback
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ENV = PROJECT_ROOT / "synthtrade" / "backend" / ".env"
DEFAULT_SYMBOL = "OKB/EUR"
OKX_BASE_URL = "https://www.okx.com"


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

    exchange = ccxt.okx({
        "apiKey": api_key,
        "secret": secret,
        "password": passphrase,
        "enableRateLimit": True,
        "headers": {
            "x-simulated-trading": "1",
        },
        "options": {
            "defaultType": "spot",
        },
    })
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
            exchange = await _build_exchange()
            if args.market_quote_amount <= 0:
                raise RuntimeError("--market-quote-amount must be > 0 when placing an order")
            order = await exchange.create_order(
                args.symbols[0],
                "market",
                "buy",
                args.market_quote_amount,
                None,
                {
                    "tdMode": "cash",
                    "tgtCcy": "quote_ccy",
                },
            )
            recorder.add(
                "market_order_demo",
                True,
                id=order.get("id"),
                status=order.get("status"),
                symbol=order.get("symbol"),
                side=order.get("side"),
                amount=order.get("amount"),
                filled=order.get("filled"),
                average=order.get("average"),
                fee=order.get("fee"),
                fees=order.get("fees"),
                raw=order.get("info"),
            )
        else:
            recorder.add(
                "market_order_demo",
                True,
                skipped=True,
                reason="read-only default; rerun with --place-market-order to test order placement",
            )

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
        default=[DEFAULT_SYMBOL, "BNB/USDC"],
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
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    return asyncio.run(run_spike(args))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
