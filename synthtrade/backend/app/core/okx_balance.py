"""OKX portfolio balance aggregator — TASK-1115.

Recupera il saldo totale del conto OKX (Spot funding + trading wallets),
convertendo tutto in USD usando i prezzi correnti di mercato via OKX REST.

Returns dict contract:
    {
        "total_usd": float,
        "total_eur": float,   # backward compat alias
        "breakdown": {wallet: {"value_usd": float, "assets": [...]}},
        "assets": [{"asset": str, "quantity": float, "value_usd": float}],
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
_MIN_VALUE_USD = 0.01  # skip dust


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


def _get_usd_price(asset: str, ticker_map: dict) -> float:
    """Get USD price for an asset using pre-fetched ticker map."""
    if asset in ("USD", "USDT", "USDC", "BUSD", "DAI", "TUSD", "USDG", "RLUSD"):
        return 1.0
    # Try direct USD pair
    direct = ticker_map.get(f"{asset}-USD")
    if direct:
        return float(direct)
    # Try direct USDT pair (USDT ≈ 1 USD)
    usdt = ticker_map.get(f"{asset}-USDT")
    if usdt:
        return float(usdt)
    # Try via USDC pair
    usdc = ticker_map.get(f"{asset}-USDC")
    if usdc:
        return float(usdc)
    return 0.0


def _get_eur_price(asset: str, ticker_map: dict) -> float:
    """Get EUR price for an asset using pre-fetched ticker map (backward compat)."""
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
        return float(usdt) * float(eur_usdt) if "EUR-USDT" not in ticker_map else float(usdt) / float(eur_usdt)
    # Stablecoins
    if asset in ("USDT", "USDC", "BUSD", "DAI", "TUSD", "USD", "USDG", "RLUSD"):
        eur_rate = ticker_map.get("USDT-EUR") or ticker_map.get("USDC-EUR")
        if eur_rate:
            return float(eur_rate)
        return 0.92  # rough fallback
    return 0.0


def _collect_assets() -> dict[str, float]:
    """Collect assets from both funding and trading wallets."""
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

    return raw_assets


def _fetch_ticker_map() -> dict[str, float]:
    """Fetch all SPOT tickers in one call."""
    ticker_map: dict[str, float] = {}
    try:
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
    return ticker_map


def get_total_balance_usd() -> dict:
    """Fetch OKX account balance and convert to USD.

    Queries:
      - /api/v5/asset/balances (funding wallet)
      - /api/v5/account/balance (trading wallet)
    Then fetches tickers for USD conversion.
    """
    try:
        raw_assets = _collect_assets()
        if not raw_assets:
            logger.warning("OKX balance: no assets found")
            return {"total_usd": 0.0, "total_eur": 0.0, "breakdown": {}, "assets": []}

        ticker_map = _fetch_ticker_map()

        # Convert to USD
        assets_list = []
        total_usd = 0.0

        for asset, qty in raw_assets.items():
            price_usd = _get_usd_price(asset, ticker_map)
            value_usd = round(qty * price_usd, 4)
            if value_usd < _MIN_VALUE_USD:
                continue
            total_usd += value_usd
            assets_list.append({
                "asset": asset,
                "quantity": round(qty, 8),
                "value_usd": value_usd,
                "value_eur": value_usd,  # backward compat
            })

        assets_list.sort(key=lambda x: x["value_usd"], reverse=True)
        total_usd = round(total_usd, 2)

        # Also compute EUR total for backward compat
        total_eur = 0.0
        usd_eur_rate = 0.0
        try:
            eur_usd_ticker = ticker_map.get("EUR-USD") or ticker_map.get("USDT-EUR")
            if eur_usd_ticker:
                # EUR-USD means 1 EUR = X USD, so 1 USD = 1/X EUR
                if "EUR-USD" in ticker_map:
                    usd_eur_rate = 1.0 / float(eur_usd_ticker)
                else:
                    usd_eur_rate = float(eur_usd_ticker)
            if usd_eur_rate > 0:
                total_eur = round(total_usd * usd_eur_rate, 2)
        except Exception:
            pass

        breakdown = {
            "OKX Spot": {
                "value_usd": total_usd,
                "value_eur": total_eur,
                "assets": assets_list,
            }
        }

        logger.info("OKX balance fetched: $%.2f USD (%d assets)", total_usd, len(assets_list))
        return {
            "total_usd": total_usd,
            "total_eur": total_eur,
            "breakdown": breakdown,
            "assets": assets_list,
        }

    except Exception as e:
        logger.error("OKX balance fetch failed: %s", e)
        return {"total_usd": 0.0, "total_eur": 0.0, "breakdown": {}, "assets": []}


def get_total_balance_eur() -> dict:
    """Fetch OKX account balance and convert to EUR (backward compat).

    For USD-denominated accounts, uses get_total_balance_usd and converts.
    """
    try:
        raw_assets = _collect_assets()
        if not raw_assets:
            logger.warning("OKX balance: no assets found")
            return {"total_eur": 0.0, "breakdown": {}, "assets": []}

        ticker_map = _fetch_ticker_map()

        assets_list = []
        total_eur = 0.0

        for asset, qty in raw_assets.items():
            price_eur = _get_eur_price(asset, ticker_map)
            value_eur = round(qty * price_eur, 4)
            if value_eur < _MIN_VALUE_USD:
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
