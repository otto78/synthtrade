"""Verify which symbols allow short trading in OKX demo vs live.

Calls the OKX private API directly to check:
1. Public instruments (which pairs exist)
2. Short availability per symbol (via get_short_availability)
3. Max leverage per symbol (via get_max_leverage)
"""
import asyncio
import httpx
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "synthtrade", "backend"))


async def check_short_availability(demo: bool):
    """Check short availability for all EUR pairs in demo or live mode."""
    from dotenv import load_dotenv
    load_dotenv("synthtrade/backend/.env")
    from app.config import settings

    base_url = settings.OKX_BASE_URL.rstrip("/")
    api_key = settings.exchange_api_key
    secret = settings.exchange_secret_key
    passphrase = settings.exchange_passphrase

    print(f"\n{'='*60}")
    print(f" MODE: {'DEMO' if demo else 'LIVE'}")
    print(f" BASE URL: {base_url}")
    print(f"{'='*60}\n")

    # 1. Fetch public instruments
    headers = {}
    if demo:
        headers["x-simulated-trading"] = "1"

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{base_url}/api/v5/public/instruments",
            params={"instType": "SPOT"},
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()

    raw = data.get("data", [])
    eur_pairs = [item for item in raw if item.get("quoteCcy") == "EUR" and item.get("state") == "live"]
    print(f"Total SPOT instruments: {len(raw)}")
    print(f"EUR pairs (live): {len(eur_pairs)}")
    print()

    # 2. Check short availability for each EUR pair
    from app.execution.exchange_models import SymbolRef
    from app.execution.okx_exchange import OkxExchangeAdapter

    adapter = OkxExchangeAdapter(
        api_key=api_key,
        secret=secret,
        passphrase=passphrase,
        demo=demo,
    )

    results = []
    for item in eur_pairs[:20]:  # cap to avoid rate limits
        inst_id = item["instId"]
        base_ccy = item["baseCcy"]
        sym = SymbolRef.from_okx(inst_id)

        try:
            avail = await adapter.get_short_availability(sym)
            max_lev = "N/A"
            if avail.available:
                try:
                    max_lev = await adapter.get_max_leverage(sym, mgn_mode="cross")
                except Exception:
                    max_lev = "error"
            results.append({
                "symbol": inst_id,
                "base": base_ccy,
                "available": avail.available,
                "borrow_apr": avail.borrow_rate_apr,
                "max_loan_qty": avail.max_loan_qty,
                "max_loan_ccy": avail.max_loan_ccy,
                "max_leverage": max_lev,
            })
        except Exception as e:
            results.append({
                "symbol": inst_id,
                "base": base_ccy,
                "available": False,
                "borrow_apr": None,
                "max_loan_qty": None,
                "max_loan_ccy": None,
                "max_leverage": "N/A",
                "error": str(e),
            })

    await adapter.close()

    # 3. Print results
    print(f"{'Symbol':<12} {'Base':<6} {'Short OK':<10} {'Borrow APR':<12} {'Max Loan':<12} {'Loan Ccy':<10} {'Max Leverage':<12}")
    print("-" * 80)
    for r in results:
        apr_str = f"{r['borrow_apr']:.4f}" if r['borrow_apr'] is not None else "N/A"
        loan_str = f"{r['max_loan_qty']:.6f}" if r['max_loan_qty'] is not None else "N/A"
        print(f"{r['symbol']:<12} {r['base']:<6} {str(r['available']):<10} {apr_str:<12} {loan_str:<12} {r.get('max_loan_ccy') or 'N/A':<10} {r['max_leverage']:<12}")

    borrowable = [r for r in results if r['available']]
    print(f"\nBorrowable symbols: {len(borrowable)}/{len(results)}")
    if borrowable:
        print("  " + ", ".join(r['symbol'] for r in borrowable))

    await adapter.close()
    return results


async def main():
    # Check LIVE mode first (most reliable for short availability)
    live_results = await check_short_availability(demo=False)

    # Check DEMO mode
    demo_results = await check_short_availability(demo=True)

    # Compare
    print(f"\n{'='*60}")
    print(" COMPARISON: DEMO vs LIVE")
    print(f"{'='*60}\n")

    live_map = {r['symbol']: r for r in live_results}
    demo_map = {r['symbol']: r for r in demo_results}

    all_symbols = sorted(set(list(live_map.keys()) + list(demo_map.keys())))
    print(f"{'Symbol':<12} {'LIVE':<10} {'DEMO':<10} {'Match':<8}")
    print("-" * 45)
    for sym in all_symbols:
        l = live_map.get(sym, {})
        d = demo_map.get(sym, {})
        l_ok = l.get('available', False)
        d_ok = d.get('available', False)
        match = "YES" if l_ok == d_ok else "NO"
        print(f"{sym:<12} {str(l_ok):<10} {str(d_ok):<10} {match:<8}")

    # Summary
    live_borrowable = set(r['symbol'] for r in live_results if r['available'])
    demo_borrowable = set(r['symbol'] for r in demo_results if r['available'])
    print(f"\nLIVE borrowable: {len(live_borrowable)} — {', '.join(sorted(live_borrowable))}")
    print(f"DEMO borrowable: {len(demo_borrowable)} — {', '.join(sorted(demo_borrowable))}")
    only_live = live_borrowable - demo_borrowable
    only_demo = demo_borrowable - live_borrowable
    if only_live:
        print(f"Only in LIVE: {', '.join(sorted(only_live))}")
    if only_demo:
        print(f"Only in DEMO: {', '.join(sorted(only_demo))}")


if __name__ == "__main__":
    asyncio.run(main())
