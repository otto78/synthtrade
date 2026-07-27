#!/usr/bin/env python3
"""Test OKX asset valuation/PnL history APIs."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'synthtrade', 'backend'))
import json

from app.core.okx_balance import _get

def test_account_valuation():
    """Test authenticated account valuation endpoints."""
    endpoints = [
        # OKX documented endpoints
        '/api/v5/account/bills?type=2&ccy=EUR&limit=5',  # type=2 = transfer
        '/api/v5/asset/bills?ccy=EUR&limit=5',
    ]
    for ep in endpoints:
        try:
            data = _get(ep)
            print(f"\n=== {ep} ===")
            if data:
                print(f"Entries: {len(data)}")
                print(json.dumps(data[:3], indent=2))
            else:
                print("Empty response")
        except Exception as e:
            print(f"\n=== {ep} === Error: {e}")

    # Try OKX account PnL endpoint
    pnl_endpoints = [
        '/api/v5/asset/asset-pnl-history?ccy=EUR',
        '/api/v5/asset/pnl-history?ccy=EUR',
        '/api/v5/account/pnl?ccy=EUR',
        '/api/v5/asset/daily-pnl?ccy=EUR',
    ]
    for ep in pnl_endpoints:
        try:
            data = _get(ep)
            print(f"\n=== {ep} ===")
            if data:
                print(f"Entries: {len(data)}")
                print(json.dumps(data[:3], indent=2))
            else:
                print("Empty response")
        except Exception as e:
            print(f"\n=== {ep} === Error: {e}")

if __name__ == "__main__":
    test_account_valuation()