"""Quick diagnostics: balance + leverage-info + max-loan for live account."""
import asyncio, json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "synthtrade", "backend"))

from app.config import settings
from app.execution.okx_exchange import OkxExchangeAdapter
from app.execution.exchange_models import SymbolRef
import httpx


async def main():
    adapter = OkxExchangeAdapter(
        api_key=settings.OKX_API_KEY_LIVE,
        secret=settings.OKX_SECRET_KEY_LIVE,
        passphrase=settings.OKX_PASSPHRASE_LIVE,
        demo=False,
        base_url=settings.OKX_BASE_URL,
    )

    # 1) Balance
    print("=== BALANCE ===")
    raw = await adapter._direct_fetch_balance()
    print(json.dumps(raw, indent=2))

    # 2) leverage-info with instId=BTC-USDT (USDT margin pair)
    print("\n=== LEVERAGE-INFO (instId=BTC-USDT) ===")
    path = "/api/v5/account/leverage-info?instId=BTC-USDT&mgnMode=cross"
    url = settings.OKX_BASE_URL.rstrip("/") + path
    headers = adapter._sign_headers("GET", path)
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, headers=headers)
        print(json.dumps(resp.json(), indent=2))

    # 3) max-loan with instId=BTC-USDT + mgnCcy=BTC
    print("\n=== MAX-LOAN (instId=BTC-USDT, mgnCcy=BTC) ===")
    path2 = "/api/v5/account/max-loan?instId=BTC-USDT&mgnMode=cross&mgnCcy=BTC"
    url2 = settings.OKX_BASE_URL.rstrip("/") + path2
    headers2 = adapter._sign_headers("GET", path2)
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp2 = await client.get(url2, headers=headers2)
        print(json.dumps(resp2.json(), indent=2))

    # 4) max-loan with instId=ETH-USDT + mgnCcy=ETH
    print("\n=== MAX-LOAN (instId=ETH-USDT, mgnCcy=ETH) ===")
    path3 = "/api/v5/account/max-loan?instId=ETH-USDT&mgnMode=cross&mgnCcy=ETH"
    url3 = settings.OKX_BASE_URL.rstrip("/") + path3
    headers3 = adapter._sign_headers("GET", path3)
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp3 = await client.get(url3, headers=headers3)
        print(json.dumps(resp3.json(), indent=2))


asyncio.run(main())
