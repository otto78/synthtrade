"""OKX portfolio balance aggregator — TASK-1115.

Recupera il saldo totale del conto OKX (Spot funding + trading wallets),
convertendo tutto in EUR usando i prezzi correnti di mercato via OKX REST.

Returns the same dict contract as binance_balance.get_total_balance_eur():
    {
        "total_eur": float,
        "breakdown": {wallet: {"value_eur": float, "assets": [...]}},
        "assets": [{"asset": str, "quantity": float, "value_eur": float}],
    }
"""
import base64
import hashlib
import hmac
import logging
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_TIMEOUT = 8.0
_MIN_VALUE_EUR = 0.01  # skip dust


def _sign_headers(method: str, path: str, body: str = "") -> dict:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    prehash = ts + method + path + body
    sig = base64.b64encode(
        hmac.new(
            settings.exchange_secret_key.encode(),
            prehash.encode(),
            hashlib.sha256,
        ).digest()
    ).decode()
    headers = {
        "OK-ACCESS-KEY": settings.exchange_api_key,
        "OK-ACCESS-SIGN": sig,
        "OK-ACCESS-TIMESTAMP": ts,
        "OK-ACCESS-PASSPHRASE": settings.exchange_passphrase,
        "Content-Type": "application/json",
    }
    if settings.exchange_demo:
        headers["x-simulated-trading"] = "1"
    return headers


def _get(path: str) -> Any:
    """Synchronous authenticated GET to OKX REST."""
    url = settings.OKX_BASE_URL.rstrip("/") + path
    headers = _sign_headers("GET", path)
    resp = httpx.get(url, headers=headers, timeout=_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != "0":
        raise RuntimeError(f"OKX API error {data.get('code')}: {data.get('msg')}")
    return data.get("data", [])


def _get_eur_price(asset: str, ticker_map: dict) -> float:
    """Get EUR price for an asset using pre-fetched ticker map."""
    if asset == "EUR":
        return 1.0
    # Try direct EUR pair
    direct = ticker_map.get(f"{asset}-EUR")
    if direct:
        return float(direct)
    # Try via USDT then USDT/EUR
    usdt = ticker_map.get(f"{asset}-USDT")
    eur_usdt = ticker_map.get("USDT-EUR") or ticker_map.get("EUR-USDT")
    if usdt and eur_usdt:
        # If EUR-USDT: EUR price = USDT price / (EUR/USDT rate)
        return float(usdt) * float(eur_usdt) if "EUR-USDT" not in ticker_map else float(usdt) / float(eur_usdt)
    # Stablecoins
    if asset in ("USDT", "USDC", "BUSD", "DAI", "TUSD"):
        eur_rate = ticker_map.get("USDT-EUR") or ticker_map.get("USDC-EUR")
        if eur_rate:
            return float(eur_rate)
        return 0.92  # rough fallback
    return 0.0


def get_total_balance_eur() -> dict:
    """Fetch OKX account balance and convert to EUR.

    Queries:
      - /api/v5/asset/balances (funding wallet)
      - /api/v5/account/balance (trading wallet)
    Then fetches tickers for EUR conversion.
    """
    try:
        # ── 1. Collect assets from both wallets ──
        raw_assets: dict[str, float] = {}

        # Funding wallet
        try:
            funding = _get("/api/v5/asset/balances")
            for item in funding:
                asset = item.get("ccy", "")
                bal = float(item.get("availBal", 0) or 0) + float(item.get("frozenBal", 0) or 0)
                if asset and bal > 0:
                    raw_assets[asset] = raw_assets.get(asset, 0) + bal
        except Exception as e:
            logger.warning("OKX funding wallet fetch failed: %s", e)

        # Trading wallet
        try:
            trading = _get("/api/v5/account/balance")
            for account in trading:
                for detail in account.get("details", []):
                    asset = detail.get("ccy", "")
                    bal = float(detail.get("cashBal", 0) or 0)
                    if asset and bal > 0:
                        raw_assets[asset] = raw_assets.get(asset, 0) + bal
        except Exception as e:
            logger.warning("OKX trading wallet fetch failed: %s", e)

        if not raw_assets:
            logger.warning("OKX balance: no assets found")
            return {"total_eur": 0.0, "breakdown": {}, "assets": []}

        # ── 2. Fetch tickers for EUR conversion ──
        ticker_map: dict[str, float] = {}
        try:
            # Fetch all SPOT tickers in one call
            url = settings.OKX_BASE_URL.rstrip("/") + "/api/v5/market/tickers?instType=SPOT"
            resp = httpx.get(url, timeout=_TIMEOUT)
            resp.raise_for_status()
            tickers_data = resp.json().get("data", [])
            for t in tickers_data:
                inst_id = t.get("instId", "")
                last = t.get("last", 0)
                if inst_id and last:
                    ticker_map[inst_id] = float(last)
        except Exception as e:
            logger.warning("OKX tickers fetch failed: %s", e)

        # ── 3. Convert to EUR ──
        assets_list = []
        total_eur = 0.0

        for asset, qty in raw_assets.items():
            price_eur = _get_eur_price(asset, ticker_map)
            value_eur = round(qty * price_eur, 4)
            if value_eur < _MIN_VALUE_EUR:
                continue
            total_eur += value_eur
            assets_list.append({
                "asset": asset,
                "quantity": round(qty, 8),
                "value_eur": value_eur,
            })

        assets_list.sort(key=lambda x: x["value_eur"], reverse=True)
        total_eur = round(total_eur, 2)

        breakdown = {
            "OKX Spot": {
                "value_eur": total_eur,
                "assets": assets_list,
            }
        }

        logger.info("OKX balance fetched: %.2f EUR (%d assets)", total_eur, len(assets_list))
        return {
            "total_eur": total_eur,
            "breakdown": breakdown,
            "assets": assets_list,
        }

    except Exception as e:
        logger.error("OKX balance fetch failed: %s", e)
        return {"total_eur": 0.0, "breakdown": {}, "assets": []}
