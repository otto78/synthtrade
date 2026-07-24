"""Enable spot borrow on OKX (live) and verify."""
import asyncio, json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "synthtrade", "backend"))

from app.config import settings


async def main():
    from app.execution.okx_exchange import OkxExchangeAdapter
    import httpx

    adapter = OkxExchangeAdapter(
        api_key=settings.OKX_API_KEY_LIVE,
        secret=settings.OKX_SECRET_KEY_LIVE,
        passphrase=settings.OKX_PASSPHRASE_LIVE,
        demo=False,
        base_url=settings.OKX_BASE_URL,
    )

    # 1) Enable spot borrow
    path = "/api/v5/account/set-enable-spot-borrow"
    url = adapter._base_url.rstrip("/") + path
    body = json.dumps({"enableSpotBorrow": "true"})
    headers = adapter._sign_headers("POST", path, body=body)
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, headers=headers, content=body)
        print("=== SET enableSpotBorrow ===")
        print(json.dumps(resp.json(), indent=2))

    # 2) Verify config
    path2 = "/api/v5/account/config"
    url2 = adapter._base_url.rstrip("/") + path2
    headers2 = adapter._sign_headers("GET", path2)
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp2 = await client.get(url2, headers=headers2)
        data = resp2.json()
        if data.get("code") == "0" and data.get("data"):
            cfg = data["data"][0]
            print("\n=== VERIFY ===")
            print(f"  acctLv          : {cfg.get('acctLv')}")
            print(f"  enableSpotBorrow: {cfg.get('enableSpotBorrow')}")
            print(f"  posMode         : {cfg.get('posMode')}")
        else:
            print(f"\n=== VERIFY FAILED: {data}")


asyncio.run(main())
