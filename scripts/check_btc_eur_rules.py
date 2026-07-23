"""Check OKX BTC-EUR minimum order sizes and raw instrument data."""
import asyncio, json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "synthtrade", "backend"))
from app.config import settings
from app.execution.okx_exchange import OkxExchangeAdapter
from app.execution.exchange_models import SymbolRef

async def main():
    adapter = OkxExchangeAdapter(
        api_key=settings.OKX_API_KEY,
        secret=settings.OKX_SECRET_KEY,
        passphrase=settings.OKX_PASSPHRASE,
        demo=True,
        base_url=settings.OKX_BASE_URL,
    )
    rules = await adapter.get_symbol_rules(SymbolRef.from_okx("BTC-EUR"))
    print(f"BTC-EUR rules:")
    print(f"  lot_sz (step)  : {rules.lot_sz}")
    print(f"  minSz          : {rules.min_sz}")
    print(f"  tickSz (price) : {rules.tick_sz}")
    print(f"  maxMktSz       : {rules.max_mkt_sz}")
    print(f"  maxMktAmt      : {rules.max_mkt_amt}")
    print()
    print(f"  Raw instrument data:")
    print(json.dumps(rules.raw, indent=2))

    # Also check what minSz is for algo orders specifically
    import httpx
    path = "/api/v5/public/instruments?instType=SPOT&instId=BTC-EUR"
    url = adapter._base_url.rstrip("/") + path
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
        data = resp.json()
        if data.get("code") == "0" and data.get("data"):
            inst = data["data"][0]
            print(f"\n  OKX public instrument data:")
            print(f"    minSz        : {inst.get('minSz')}")
            print(f"    lotSz        : {inst.get('lotSz')}")
            print(f"    tickSz       : {inst.get('tickSz')}")
            print(f"    maxMktSz     : {inst.get('maxMktSz')}")
            print(f"    ctMult       : {inst.get('ctMult')}")
            print(f"    ctType       : {inst.get('ctType')}")
            print(f"    ctVal        : {inst.get('ctVal')}")
            print(f"    ctValCcy     : {inst.get('ctValCcy')}")

asyncio.run(main())
