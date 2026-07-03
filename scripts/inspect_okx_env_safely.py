#!/usr/bin/env python3
"""Inspect OKX env values without printing secrets."""

from __future__ import annotations

import hashlib
from pathlib import Path


ENV_PATH = Path(__file__).resolve().parents[1] / "synthtrade" / "backend" / ".env"
KEYS = [
    "OKX_API_KEY",
    "OKX_SECRET_KEY",
    "OKX_PASSPHRASE",
    "OKX_LIVE_API_KEY",
    "OKX_LIVE_SECRET_KEY",
    "OKX_LIVE_PASSPHRASE",
]


def mask(value: str) -> str:
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def main() -> int:
    values: dict[str, tuple[str, str]] = {}
    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#") or "=" not in raw_line:
            continue
        key, raw_value = raw_line.split("=", 1)
        key = key.strip()
        if key not in KEYS:
            continue
        loaded = raw_value.strip().strip('"').strip("'")
        values[key] = (raw_value, loaded)

    print(f"env_file: {ENV_PATH}")
    for key in KEYS:
        raw_value, loaded = values.get(key, ("", ""))
        if not loaded:
            print(f"{key}: missing")
            continue
        digest = hashlib.sha256(loaded.encode("utf-8")).hexdigest()[:12]
        print(f"{key}: present")
        print(f"  masked: {mask(loaded)}")
        print(f"  raw_len: {len(raw_value)}")
        print(f"  loaded_len: {len(loaded)}")
        print(f"  wrapper_changed: {raw_value != loaded}")
        print(f"  has_inner_whitespace: {any(ch.isspace() for ch in loaded)}")
        print(f"  sha256_12: {digest}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
