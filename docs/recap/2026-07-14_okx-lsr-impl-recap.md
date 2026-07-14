# Recap 2026-07-14 — TASK-1158: implementazione LSR OKX + fix mappa OKB

**Autore:** Kilo (auto, dopo commit merge-conflict/OBI)
**Branch:** `main` (non committato)
**Prerequisito:** `docs/recap/2026-07-14_okx-lsr-spike-recap.md` (spike: OKX HA endpoint rubik)

## 1. Obiettivo

Implementare quanto scoperto nello spike:
1. Correggere il bug `OKX_PERPETUAL_MAP["OKB"] = None` → `"OKB-USDT-SWAP"`.
2. Rendere `LongShortRatioCollector` provider-aware per OKX (endpoint rubik, ratio→%).

## 2. Modifiche codice

### `collectors/_provider_maps.py`
- `OKX_PERPETUAL_MAP["OKB"]`: `None` → `"OKB-USDT-SWAP"`.
  Questo sblocca **automaticamente** `open_interest.py` e `funding_rate.py` per OKB
  (prima ritornavano `NONE` pur essendo disponibili), oltre al nuovo LSR.

### `execution/okx_exchange.py`
- Aggiunto `async def get_long_short_ratio(base_asset, period="5m") -> Optional[float]`.
  Endpoint pubblico: `GET /api/v5/rubik/stat/contracts/long-short-account-ratio?ccy=<BASE>&period=5m`.
  Ritorna l'ultimo **ratio** (`data[0][1]`), es. `2.45`. `None` su errore/empty.
  (Ripristinato anche `get_funding_rate` che era stato accidentalmente sovrascritto.)

### `collectors/long_short_ratio.py`
- Import `OKX_PERPETUAL_MAP`, `extract_base_asset`, `timezone`.
- `is_symbol_supported`: per OKX ritorna `OKX_PERPETUAL_MAP[base] is not None`
  (unified con OI/funding).
- `collect`: ramo OKX provider-aware — mappa `OKB-EUR`→`ccy=OKB`, chiama
  `adapter.get_long_short_ratio`, converte `ratio→long_pct = ratio/(1+ratio)*100`,
  `short_pct = 100 - long_pct`, ritorna `LongShortRatio`. Ramo Binance legacy invariato.

### `tests/integration/fake_okx_adapter.py`
- Aggiunto `async def get_long_short_ratio(base_asset, period="5m")` + tracciamento `self.calls`.

## 3. Test

`tests/scalping/test_collector_provider_aware.py` aggiornati (vecchi test codificavano il
comportamento "OKB unsupported / LSR unavailable" ora superato):
- `TestProviderAwareLongShortRatio`: OKX OKB usa adapter e converte ratio (2.45 → 71.01%/28.99%),
  `is_symbol_supported` True per OKB/BTC/ETH, ratio None → None, Binance legacy invariato.
- `TestScoreReweightWhenUnavailable`: OKB-EUR ora SUPPORTA funding_rate/open_interest/long_short_ratio
  (mappa corretta); BTC-EUR tutti e tre attivi.
- `OpenInterest`/`FundingRate` OKB-EUR: ora `is_symbol_supported` True + chiamata adapter fatta.

**Risultato:** `test_collector_provider_aware.py` + `test_long_short_ratio.py` +
`test_order_book_imbalance.py` + `test_signal_aggregator.py` + `test_spread.py` =
**60 passed**. Backend importabile. (2 failure pre-esistenti in `test_signal_score_engine.py`
sui test CVD, non correlati — verificati via `git stash`.)

## 4. Impatto a runtime

- Su OKB-EUR (provider okx) LSR/OI/Funding entrano ora nel punteggio (proxy via USDT-SWAP).
- `SignalScoreEngine` già usava `LongShortRatioCollector.ratio_to_score(ls.long_pct)` → lo score
  LSR è automaticamente attivo una volta che `collect` ritorna dati reali OKX.
- Coverage configurable su OKB-EUR sale da 3/9 a 6/9 (OBI, Sentiment, LSR, OI, Funding + whale BTC/LTC).

## 5. File toccati

- `app/scalping/intelligence/collectors/_provider_maps.py`
- `app/execution/okx_exchange.py`
- `app/scalping/intelligence/collectors/long_short_ratio.py`
- `tests/integration/fake_okx_adapter.py`
- `tests/scalping/test_collector_provider_aware.py`
- `docs/HANDOFF.md`, `docs/TASKS.md` (tabella collector + TASK-1158 Done/implementato)
