# OKX Short Selling — Spike Results (TASK-1220)

> Generated: 2026-07-22 09:37 UTC (updated with fixes)
> Account: LIVE (eea.okx.com) — uid 858315397756873787

## CRITICAL BLOCKER

The account is in **Simple mode** (`acctLv: 1`) with **Spot Borrow disabled** (`enableSpotBorrow: False`).
All margin-related endpoints (max-loan, position-tiers) return error `51010: You can't complete this request under your current account mode`.

**To unblock:** Manual action in OKX UI required:
1. Switch account from Simple → **Multi-currency margin** (`acctLv: 2`)
2. Enable **Spot borrow** (`enableSpotBorrow: true`)

## Step Summary

| Step | Status | Detail |
|------|--------|--------|
| 1220A — account/config | ✅ | `enableSpotBorrow: False`, `acctLv: 1`, `posMode: net_mode` |
| 1220B — max-loan | ❌ | `51010: You can't complete this request under your current account mode.` |
| 1220C — interest-rate-loan-quota | ⚠️ | `code: 0` but `rate: null` in public endpoint (possible EU restriction). Real rate from interest-limits below. |
| 1220D — leverage-info | ✅ | `lever: 5`, `mgnMode: isolated` for BTC-EUR and ETH-EUR |
| 1220E — positions?instType=MARGIN | ✅ | Empty list (correct — no margin positions yet) |
| 1220F — position-tiers | ❌ | `51000: Parameter instType error` (likely requires `acctLv >= 2`) |
| 1220G — borrow-repay-history | ❌ | `404 Not Found` (endpoint may not exist on Simple mode) |
| 1220G — interest-limits | ✅ | **This is where real APR lives** — see table below |
| 1220H — gate check | ❌ | Cannot pass until `enableSpotBorrow=true` |
| 1220I — USDT fallback | ❌ | Same `51010` error — account-wide blocker |

## Real APR (from interest-limits)

| Asset | Hourly rate | APR (annualized) | Cost per 2h scalp | LoanQuota |
|-------|-------------|-------------------|-------------------|-----------|
| BTC | 0.0000612 | ~22.3% | ~0.015% | 10 BTC |
| ETH | 0.0000612 | ~22.3% | ~0.015% | 200 ETH |
| SOL | 0.0000612 | ~22.3% | ~0.015% | 4,000 SOL |
| DOGE | 0.0000276 | ~10.1% | ~0.007% | 100,000 DOGE |
| XRP | 0.0000276 | ~10.1% | ~0.007% | 250,000 XRP |

**Gate evaluation:** Even at 22.3% APR, a 2-hour scalping hold costs only ~0.015% in interest — well under the 0.35% SL gross fee. Interest is **not** a blocker for scalping. The only blocker is the account mode.

## Leverage

BTC-EUR and ETH-EUR: **5x isolated** (already set).

## Next Steps

1. User switches account to Multi-currency margin in OKX UI
2. User enables Spot borrow in OKX UI
3. Re-run `scripts/test_okx_short_spike.py` to confirm `enableSpotBorrow: true`
4. If gate passes → proceed to TASK-1221+

---

*Script: `scripts/test_okx_short_spike.py`*
*Raw JSON: `docs/analysis/okx-short-spike-results.json`*
