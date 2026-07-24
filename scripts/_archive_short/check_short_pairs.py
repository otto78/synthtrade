"""Check which pairs support short selling on OKX."""
import asyncio, json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "synthtrade", "backend"))

from app.config import settings
from app.execution.okx_exchange import OkxExchangeAdapter
import httpx


async def main():
    adapter = OkxExchangeAdapter(
        api_key=settings.OKX_API_KEY_LIVE,
        secret=settings.OKX_SECRET_KEY_LIVE,
        passphrase=settings.OKX_PASSPHRASE_LIVE,
        demo=False,
        base_url=settings.OKX_BASE_URL,
    )

    pairs = ["BTC-EUR", "BTC-USDT", "BTC-USD", "BTC-USDC", "ETH-EUR", "ETH-USDT", "ETH-USDC"]

    for pair in pairs:
        # max-loan
        path = f"/api/v5/account/max-loan?instId={pair}&mgnMode=cross"
        url = settings.OKX_BASE_URL.rstrip("/") + path
        headers = adapter._sign_headers("GET", path)
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            data = resp.json()

        code = data.get("code")
        msg = data.get("msg", "")
        rows = data.get("data", [])
        sell_rows = [r for r in rows if r.get("side") == "sell"]
        max_loan = sell_rows[0].get("maxLoan", "?") if sell_rows else "N/A"

        status = "OK" if code == "0" else f"FAIL({code})"
        print(f"{pair:12s} | max-loan: {status:12s} | maxLoan(sell): {max_loan:8s} | msg: {msg}")

    # Also try with mgnCcy for pairs that failed
    print("\n--- Retry with mgnCcy ---")
    for pair in ["BTC-USDT", "ETH-USDT"]:
        base = pair.split("-")[0]
        path = f"/api/v5/account/max-loan?instId={pair}&mgnMode=cross&mgnCcy={base}"
        url = settings.OKX_BASE_URL.rstrip("/") + path
        headers = adapter._sign_headers("GET", path)
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            data = resp.json()

        code = data.get("code")
        rows = data.get("data", [])
        sell_rows = [r for r in rows if r.get("side") == "sell"]
        max_loan = sell_rows[0].get("maxLoan", "?") if sell_rows else "N/A"

        status = "OK" if code == "0" else f"FAIL({code})"
        print(f"{pair:12s} | max-loan: {status:12s} | maxLoan(sell): {max_loan:8s}")


asyncio.run(main())
