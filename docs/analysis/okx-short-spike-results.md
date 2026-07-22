# OKX Short Selling — Spike Results (TASK-1220)

> Generated: 2026-07-22
> Account: LIVE (eea.okx.com) — uid 858315397756873787

## Risultato Finale

**GATE: PASSATO** — short selling è tecnicamente possibile.

| Check | Risultato |
|-------|-----------|
| `enableSpotBorrow` | **`True`** ✅ |
| `acctLv` | **`1` (Simple mode)** — solo **cross** margin |
| BTC-EUR borrowable | **Yes** — `maxLoan: 0.00188 BTC` (cross) ✅ |
| ETH-EUR borrowable | **Yes** — `maxLoan: 0.0644 ETH` (cross) ✅ |
| APR reale BTC/ETH | `0.00612%/hour` = `22.3%/anno` |
| Costo 2h scalp | `~0.015%` — trascurabile vs fee 0.70% round-trip |
| Leva | `5x cross` ✅ |
| Gate pre-apertura | **PASSATO** ✅ |

## Step Summary

| Step | Status | Detail |
|------|--------|--------|
| 1220A — account/config | ✅ | `enableSpotBorrow: True`, `acctLv: 1` |
| 1220B — max-loan (isolated) | ❌ | `51000` — Simple mode non supporta isolated |
| 1220B — max-loan (cross) | ✅ | BTC: 0.00188, ETH: 0.0644 |
| 1220C — interest-rate-loan-quota | ⚠️ | Public endpoint: rate=null (EU Simple mode). Rate reale da interest-limits. |
| 1220D — leverage (isolated) | ❌ | `51000` — Simple mode non supporta isolated |
| 1220D — leverage (cross) | ✅ | 5x per BTC-EUR e ETH-EUR |
| 1220E — positions?instType=MARGIN | ✅ | Empty list (corretto) |
| 1220F — position-tiers | ❌ | `51000` — Simple mode non supporta questo endpoint |
| 1220G — borrow-repay-history | ❌ | 404 — non disponibile in Simple mode |
| 1220G — interest-limits | ✅ | **Fonte APR reale**: BTC/ETH 0.0000612/h |
| 1220H — gate check | ✅ | Passa con cross mode |

## Implicazioni per l'architettura

1. **Cross margin (non isolated):** il conto Simple supporta solo cross. Il rischio non è segregato per posizione — una posizione short in perdita intacca tutto il saldo.
2. **Isolated margin — FROZEN:** richiede Multi-currency margin (`acctLv: 2`), che a sua volta richiede saldo minimo $10k USD. Con saldo attuale ~$300, isolated non è praticabile. L'ipotesi è congelata fino a quando il saldo non raggiunge la soglia.
3. **Sicurezza con cross margin:** SL stretto, time-stop, e risk manager impediscono perdite eccessive. Il sistema è progettato per scalping con posizioni piccole e chiusura rapida.
4. **position-tiers non disponibile:** con cross margin, il maintenance margin è gestito a livello di conto, non per posizione.
5. **Limiti di prestito:** 0.00188 BTC (~€110) e 0.0644 ETH (~€195) — sufficienti per test, non per trading size significativo.

## Prossimi Passi

1. Aggiornare `tdMode` da `"isolated"` a `"cross"` nel codice (architettura prevedeva isolated)
2. Procedere con TASK-1221+ usando cross margin
3. Opzionale: passare a Multi-currency margin in futuro per isolated margin

---

*Script: `scripts/test_okx_short_spike.py`*
*Raw JSON: `docs/analysis/okx-short-spike-results.json`*
