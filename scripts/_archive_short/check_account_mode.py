"""Check OKX account mode (acctLv) and enableSpotBorrow for both demo and live."""
import asyncio, json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "synthtrade", "backend"))

from app.config import settings

# Save originals
orig_mode = settings.TRADING_MODE


async def check(label: str, is_demo: bool):
    from app.execution.okx_exchange import OkxExchangeAdapter
    import httpx
    if is_demo:
        adapter = OkxExchangeAdapter(
            api_key=settings.OKX_API_KEY,
            secret=settings.OKX_SECRET_KEY,
            passphrase=settings.OKX_PASSPHRASE,
            demo=True,
            base_url=settings.OKX_BASE_URL,
        )
    else:
        adapter = OkxExchangeAdapter(
            api_key=settings.OKX_API_KEY_LIVE,
            secret=settings.OKX_SECRET_KEY_LIVE,
            passphrase=settings.OKX_PASSPHRASE_LIVE,
            demo=False,
            base_url=settings.OKX_BASE_URL,
        )
    path = "/api/v5/account/config"
    url = adapter._base_url.rstrip("/") + path
    headers = adapter._sign_headers("GET", path)
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, headers=headers)
        data = resp.json()
        if data.get("code") == "0" and data.get("data"):
            cfg = data["data"][0]
            print(f"\n=== {label} ===")
            print(f"  acctLv          : {cfg.get('acctLv')}  (1=Spot, 2=Multi-currency margin, 3=Futures, 4=Portfolio margin)")
            print(f"  enableSpotBorrow: {cfg.get('enableSpotBorrow')}  (margin trading spot)")
            print(f"  posMode         : {cfg.get('posMode')}")
            print(f"  type            : {cfg.get('type')}")
        else:
            print(f"\n=== {label} === FAILED: {data}")


async def main():
    await check("LIVE", is_demo=False)
    await check("DEMO", is_demo=True)


asyncio.run(main())
