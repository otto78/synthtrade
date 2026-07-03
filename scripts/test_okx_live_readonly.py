#!/usr/bin/env python3
"""Read-only OKX live auth check.

Loads OKX_LIVE_* credentials from synthtrade/backend/.env and calls only
GET /api/v5/account/balance. It never prints secrets.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ENV = PROJECT_ROOT / "synthtrade" / "backend" / ".env"
OKX_BASE_URL = "https://eea.okx.com"


def load_env(path: Path) -> None:
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ[key.strip()] = value.strip().strip('"').strip("'")


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def mask(value: str) -> str:
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def sign(secret: str, ts: str, method: str, request_path: str, body: str = "") -> str:
    prehash = f"{ts}{method.upper()}{request_path}{body}"
    digest = hmac.new(secret.encode("utf-8"), prehash.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(digest).decode("ascii")


async def request_private_get(base_url: str, request_path: str) -> dict[str, Any]:
    api_key = require_env("OKX_LIVE_API_KEY")
    secret = require_env("OKX_LIVE_SECRET_KEY")
    passphrase = require_env("OKX_LIVE_PASSPHRASE")

    method = "GET"
    ts = timestamp()
    headers = {
        "Content-Type": "application/json",
        "OK-ACCESS-KEY": api_key,
        "OK-ACCESS-SIGN": sign(secret, ts, method, request_path),
        "OK-ACCESS-TIMESTAMP": ts,
        "OK-ACCESS-PASSPHRASE": passphrase,
    }

    print("[OK] credentials_present")
    print(f"  - api_key: {mask(api_key)}")
    print(f"  - secret: {mask(secret)}")
    print(f"  - passphrase: {mask(passphrase)}")
    print(f"  - env_file: {BACKEND_ENV}")

    async with httpx.AsyncClient(base_url=base_url, timeout=20.0) as client:
        response = await client.request(method, request_path, headers=headers)
        try:
            payload = response.json()
        except json.JSONDecodeError:
            payload = {"raw_text": response.text[:500]}
        payload["_http_status"] = response.status_code
        return payload


async def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only OKX live private API check.")
    parser.add_argument("--base-url", default=OKX_BASE_URL)
    parser.add_argument("--path", default="/api/v5/account/balance")
    args = parser.parse_args()

    load_env(BACKEND_ENV)
    payload = await request_private_get(args.base_url, args.path)
    ok = payload.get("code") == "0" and payload.get("_http_status") == 200
    print("[OK] live_private_get" if ok else "[FAIL] live_private_get")
    print(f"  - base_url: {args.base_url}")
    print(f"  - path: {args.path}")
    print(f"  - http_status: {payload.get('_http_status')}")
    print(f"  - raw_code: {payload.get('code')}")
    print(f"  - raw_msg: {payload.get('msg')}")
    data = payload.get("data") or []
    details = data[0].get("details", []) if data else []
    nonzero = [
        {"ccy": row.get("ccy"), "availBal": row.get("availBal"), "eq": row.get("eq")}
        for row in details
        if float(row.get("eq") or 0) > 0
    ]
    print(f"  - total_assets: {len(details)}")
    print(f"  - nonzero_assets: {nonzero[:20]}")
    return 0 if ok else 1


if __name__ == "__main__":
    import asyncio

    raise SystemExit(asyncio.run(main()))
