#!/usr/bin/env python3
"""Check OKX fee tier for your account by calling the API directly.

Usage:
    python scripts/check_fee_tier.py              # Check BTC-EUR fees
    python scripts/check_fee_tier.py BTC-USD      # Check specific symbol
"""

import argparse
import asyncio
import base64
import hashlib
import hmac
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

sys.path.insert(0, "synthtrade/backend")


def get_okx_credentials():
    """Get OKX credentials from .env file."""
    env_path = Path("synthtrade/backend/.env")
    env = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip()

    return {
        "api_key": env.get("OKX_API_KEY_LIVE"),
        "secret": env.get("OKX_SECRET_KEY_LIVE"),
        "passphrase": env.get("OKX_PASSPHRASE_LIVE"),
        "base_url": env.get("OKX_BASE_URL", "https://eea.okx.com"),
    }


def sign_request(method: str, path: str, secret: str) -> dict:
    """Generate OKX API signature headers."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    message = f"{timestamp}{method}{path}"
    signature = base64.b64encode(
        hmac.new(secret.encode(), message.encode(), hashlib.sha256).digest()
    ).decode()
    return {
        "OK-ACCESS-SIGN": signature,
        "OK-ACCESS-TIMESTAMP": timestamp,
    }


async def fetch_trade_fee(symbol: str) -> dict:
    """Fetch trade fee from OKX API."""
    creds = get_okx_credentials()
    path = f"/api/v5/account/trade-fee?instType=SPOT&instId={symbol}"
    url = creds["base_url"].rstrip("/") + path

    headers = sign_request("GET", path, creds["secret"])
    headers["OK-ACCESS-KEY"] = creds["api_key"]
    headers["OK-ACCESS-PASSPHRASE"] = creds["passphrase"]

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()


def format_fee(fee_rate: float) -> str:
    """Format fee rate as percentage."""
    return f"{fee_rate * 100:.4f}%"


async def main():
    parser = argparse.ArgumentParser(description="Check OKX account fee tier")
    parser.add_argument("symbol", nargs="?", default="BTC-EUR", help="Trading pair (default: BTC-EUR)")
    args = parser.parse_args()

    print(f"OKX Fee Tier Check — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Symbol: {args.symbol}")
    print("-" * 50)

    try:
        data = await fetch_trade_fee(args.symbol)

        if data.get("code") != "0":
            print(f"API Error: {data.get('msg')} (code: {data.get('code')})")
            return

        fee_data = data.get("data", [])
        if not fee_data:
            print("No fee data returned for this symbol.")
            return

        for item in fee_data:
            maker_raw = float(item.get("maker", 0))
            taker_raw = float(item.get("taker", 0))
            level = item.get("level", "unknown")

            # OKX returns negative for rebates; for Lv1 base accounts convert to positive
            if level in ["Lv1", ""] or not any(char.isalpha() for char in level):
                maker = abs(maker_raw)
                taker = abs(taker_raw)
                note = " (Lv1 base, converted to positive)"
            else:
                maker = maker_raw
                taker = taker_raw
                note = " (VIP, keeping rebate)"

            print(f"\nAccount Level: {level}")
            print(f"  Maker fee: {format_fee(maker)}{note}")
            print(f"  Taker fee: {format_fee(taker)}{note}")

            # Round-trip (both legs taker for OCO)
            round_trip = taker * 2
            print(f"\nRound-trip (taker+taker): {format_fee(round_trip)}")

            # Net profit targets with these fees
            sl_net = 0.50
            tp_net = 0.80
            sl_gross = sl_net + round_trip * 100
            tp_gross = tp_net + round_trip * 100

            print(f"\nWith current fees:")
            print(f"  SL net {sl_net}% -> gross {sl_gross:.2f}%")
            print(f"  TP net {tp_net}% -> gross {tp_gross:.2f}%")
            print(f"  R/R ratio: 1:{tp_gross / sl_gross:.2f}")

    except httpx.HTTPStatusError as e:
        print(f"HTTP Error: {e.response.status_code}")
        print(e.response.text)
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
