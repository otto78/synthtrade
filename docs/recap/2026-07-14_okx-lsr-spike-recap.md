# Recap 2026-07-14 — TASK-1158: spike equivalente OKX Long/Short Ratio

**Autore:** Kilo (auto, post merge-conflict + OBI fix)
**Branch:** `main` (non committato)
**Punto di partenza:** TASK-1158 "Spike: esiste un equivalente OKX per Long/Short Ratio?"

## 1. Domanda dello spike

Il collector `long_short_ratio.py` ritorna sempre `None` su OKX con commento:
"OKX non ha un endpoint equivalente confermato per il long/short ratio (TASK-1158)".
Verificare se esiste davvero un endpoint OKX.

## 2. Risposta — SÌ (verificata con dati reali OKX, 2026-07-14)

**Endpoint 1 — per valuta:**
```
GET https://www.okx.com/api/v5/rubik/stat/contracts/long-short-account-ratio?ccy=OKB&period=5m
```
→ `code:"0"`, `data: [[ts_ms, ratio], ...]` (lista di coppie, più recente per prima).
Ultimo OKB: `["1784038800000","2.45"]` → **ratio ≈ 2.45**.
`ccy` = base asset (`OKB`, `BTC`, `ETH`).

**Endpoint 2 — per strumento (più preciso):**
```
GET https://www.okx.com/api/v5/rubik/stat/contracts/long-short-account-ratio-contract?instId=OKB-USDT-SWAP&period=5m
```
→ stesso dato, es. `2.4534722222222222`.

**Limiti:** 5 req / 2s (IP + instrument). Periodi: `5m,1H,4H,1D,...`.
**Auth:** nessuna (endpoint pubblico, verificato da IP locale senza key).

## 3. Differenza vs Binance (importante per l'implementazione)

| | Binance `globalLongShortAccountRatio` | OKX `long-short-account-ratio` |
|---|---|---|
| Parametro | `symbol` (es. `BTCUSDT`) | `ccy` (es. `OKB`) / `instId` (`-contract`) |
| Risposta | `longAccount`, `shortAccount` (%, es. `71.0`,`29.0`) | `longShortAccount` = **ratio** (es. `2.45`) |

OKX ritorna un **ratio**, non le % separate. Conversione da applicare:
```
long_pct  = ratio / (1 + ratio) * 100
short_pct = 100 - long_pct
```
Per ratio=2.45 → **71.0% long / 29.0% short** (centra la soglia ">70% long → short squeeze"
già presente in `LongShortRatioCollector.ratio_to_score`).

## 4. Scoperta collaterale (bug reale)

`OKX_PERPETUAL_MAP["OKB"] = None` in
`app/scalping/intelligence/collectors/_provider_maps.py:15` è **ERRATO**.

Verifica open-interest OKX:
```
GET https://www.okx.com/api/v5/public/open-interest?instType=SWAP&instId=OKB-USDT-SWAP
→ {"code":"0","data":[{"instId":"OKB-USDT-SWAP","oiUsd":"16411038.1188",...}]}
```
`OKB-USDT-SWAP` **esiste** (OI ~16.4M USD). Quel `None`:
- blocca `funding_rate.py` e `open_interest.py` per OKB (ritornano `NONE` pur essendo disponibili);
- è la ragione per cui i 3 collector perpetual compaiono `active=off` su OKB-EUR nei log `[COVERAGE_REAL]`.

Correzione: `"OKB": "OKB-USDT-SWAP"`.

## 5. Conclusione / prossimo passo (fuori dallo spike)

TASK-1158 = **Done** (risposta: sì, esiste). L'implementazione è un task a parte:

1. Correggere `OKX_PERPETUAL_MAP["OKB"] = "OKB-USDT-SWAP"`.
2. In `long_short_ratio.py`: rimuovere il ramo OKX che ritorna `None`; aggiungere path
   provider-aware che mappa spot `OKB-EUR` → `ccy=OKB`, chiama endpoint rubik, converte
   ratio→long/short%, riusa `ratio_to_score` esistente.
3. Test: `tests/scalping/test_collector_provider_aware.py`, `tests/scalping/test_long_short_ratio.py`.

## 6. File toccati (solo doc, nessun codice modificato in questo spike)

- `docs/TASKS.md` — TASK-1158 sezione aggiornata a Done + findings + task implementazione;
  corretta nota a riga ~318 ("long/short sempre unsupported su OKX" → smentita).
- `docs/HANDOFF.md` — tabella collector: Long/Short Ratio, Open Interest, Funding Rate
  aggiornati a 🟡 (bloccati da bug mappa / da rendere provider-aware).
- `docs/recap/2026-07-14_okx-lsr-spike-recap.md` — questo file.
