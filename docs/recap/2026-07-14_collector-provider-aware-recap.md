# SynthTrade — DCO: Collector Intelligence + decisioni 14/07 (TASK-1100.G, OKX-RECAL, TASK-1154)

**Data:** 14 luglio 2026
**Autore:** Kilo
**Scope sessione:** chiusura TASK-1153 + messa a verde della suite test collector

---

## 1. Stato di partenza

- TASK-1150 (whale enable + verifica sentiment), TASK-1151 (OrderBookImbalanceCollector), TASK-1152 (SpreadCollector) erano già **Done** e committati (commit `7579e44`, `f9fba77`, `203829e`, `7a7c391`).
- TASK-1153 (CollectorAdapter provider-aware) era implementato ma con la suite test in parte rotta.

## 2. Lavoro svolto

### 2.1 — TASK-1153 completato e committato
- Commit `1f0b364` — `feat(intelligence): collector provider-aware con adapter OKX (TASK-1153)`
- Rende `funding_rate` / `open_interest` / `long_short_ratio` provider-aware invece di hardcoded Binance Futures.
- `_provider_maps.py`: `OKX_PERPETUAL_MAP` + `extract_base_asset()`.
- `okx_exchange.py`: adapter methods `get_open_interest(inst_id)` / `get_funding_rate(inst_id)`.
- Collector accettano `adapter` opzionale; se provider=okx e perpetual esiste → endpoint nativi OKX, altrimenti graceful skip (OKB=None → `active=off`; long/short sempre unsupported su OKX → TASK-1158).
- `signal_score_engine.py`: parametro `adapter` in `__init__` e `get_or_create`; `old_coverage_field` mantenuto su singola riga.
- **Bug reale corretto:** `funding_rate.py` usava `timezone` non importato nel ramo OKX → `NameError` a runtime su BTC-EUR. Aggiunto `from datetime import datetime, timezone`.

### 2.2 — Suite test rimessa a verde (inclusa in `1f0b364`)
- `tests/scalping/test_collector_provider_aware.py`: **14/14** (path OKX-native, BTC-EUR active=on, OKB-EUR=None, binance legacy invariato, reweight score).
- 7 failure pre-esistenti nei test legacy corrette:
  - `test_funding_rate.py` / `test_open_interest.py` / `test_long_short_ratio.py`: mock `.json()` da `AsyncMock`→`MagicMock` (httpx `.json()` è sincrono).
  - `test_*_to_score_clamped`: asserzioni ±15/±25 → **±100** (raw score clampa a ±100; il peso 0.20/0.15 scala dopo in engine).
  - `test_long_short_ratio::test_collect_success`: dato di test da percentuale (`65.5`) → **frazione** (`0.655`), coerente con l'API Binance reale (`longAccount`/`shortAccount` sono frazioni) e col `*100` del collector.
  - Rimosso `result.ratio` (campo inesistente nel modello `LongShortRatio`; `ratio` è un metodo).
- Totale collector suite: **42 passed** (14 + 28 legacy).

## 3. Decisioni / note

- **Uncommitted check:** verificato via `git diff` che `signal_score_engine.py` non avesse modifiche misteriose — le uniche diff vs HEAD erano il wiring adapter di TASK-1153 (già committato).
- Nessuna regressione su OKB-EUR (resta strutturalmente assente per design).
- TASK-1153 supersede TASK-1116.C e TASK-COLLECTOR-001 (già marcato in `docs/TASKS.md`).

## 4. Stato attuale Collector Intelligence (TASK-1150→1159)

| Collector | Stato | Note |
|-----------|-------|------|
| Fear & Greed | 🟢 Funzionante | indipendente da exchange |
| Order Book Imbalance | 🟢 Funzionante (TASK-1151) | peso provvisorio 0.15, spot OKX |
| Spread | 🟡 Collezionato (TASK-1152) | wiring OFF, solo diagnostico |
| Whale Alert | 🟡 Abilitato (TASK-1150) | Blockchair su BTC/LTC; OKB-EUR=None |
| Long/Short Ratio | 🟢 Provider-aware (TASK-1153) | OKX: sempre unsupported (TASK-1158) |
| Open Interest | 🟢 Provider-aware (TASK-1153) | BTC/ETH-SWAP okx; OKB=None |
| Funding Rate | 🟢 Provider-aware (TASK-1153) | BTC/ETH-SWAP okx; OKB=None |
| CVD | 🔴 Grace period (TASK-1157) | 100 trade da monitorare |
| Sentiment | 🔴 Da rendere affidabile (TASK-1154) | NO key necessaria: RSS fallback free; key già in backend/.env |
| On-Chain | 🔴 Da rendere affidabile (TASK-1156) | dipende da Dune API key |

## 5. Stato task e prossimi passi (aggiornato 14/07 pomeriggio)

### Completati / decisi in questa sessione
- ✅ **TASK-1100.G** — chiuso come fatto: WS private OKX EEA non disponibile → REST polling di default già operativo.
- ✅ **TASK-OKX-RECAL** — SL/TP ricalibrati su fee OKX reali (`STOP_LOSS=1.05%`, `TAKE_PROFIT=1.55%` in backend/.env).
- 🟡 **TASK-908 / TASK-909** — *riservati per analisi* (non avviati): resume guard bearish + isolamento chiamate AI (quest'ultimo archiviato Done, richiamato per rivalutazione).

### Prossimi (da cui proseguire)
In ordine di priorità dal piano consolidato `docs/plans/collector-intelligence-implementation-plan.md`:

1. ~~**TASK-1154** — Sentiment collector: fallback affidabile (🔴 media). **Nessuna API key da procurarsi**: RSS fallback free sempre disponibile, e `backend/.env` ha già NEWSAPI/CRYPTOCOMPARE key. Si avvia subito.~~ **DONE (14/07)**: priorità CC→NewsAPI→RSS, cache 5 min, fallback neutrale `source="fallback"` se tutto fallisce, log compatto su errori DNS. 6 test Red→Green in `tests/scalping/test_sentiment_collector.py`.
2. **TASK-1157** — Verifica CVD grace period su OKB-EUR dopo 100 trade (🔴 media).
3. **TASK-1158** — Spike documentale: equivalente OKX per Long/Short Ratio? (🟢 bassa).
4. **TASK-1155 / TASK-1156** — Whale/On-chain fonti OKX-compatibili (🟢 basse).
5. **TASK-1159** — Ricalibrazione pesi SignalScoreEngine — **BLOCCATA** finché Fasi 1-5 non sono attive per 2-3 sessioni reali con log `[COVERAGE_REAL]`/`[COLLECTORS_DIAG_TEMP]` popolati.

## 6. File coinvolti (TASK-1153, già committati)

- `synthtrade/backend/app/scalping/intelligence/collectors/{open_interest,funding_rate,long_short_ratio}.py`
- `synthtrade/backend/app/scalping/intelligence/signal_score_engine.py`
- `synthtrade/backend/app/execution/okx_exchange.py`
- `synthtrade/backend/app/scalping/intelligence/collectors/_provider_maps.py` (nuovo)
- `synthtrade/backend/tests/scalping/test_collector_provider_aware.py` (nuovo)
- `synthtrade/backend/tests/integration/fake_okx_adapter.py`
- `synthtrade/backend/tests/scalping/{test_funding_rate,test_open_interest,test_long_short_ratio}.py`

---

## 7. Addendum — decisioni 14/07 (pomeriggio) e analisi TASK-1154

### 7.1 — Chiusura TASK-1100.G
WS private OKX EEA bloccato da `60032` → il runtime usa il REST polling di default già implementato. Nessun ulteriore lavoro: marcato Done in `docs/TASKS.md`.

### 7.2 — TASK-OKX-RECAL Done
SL/TP ricalibrati su fee OKX reali (round-trip taker 0.70%): `SCALPING_STOP_LOSS_PCT=1.05`, `SCALPING_TAKE_PROFIT_PCT=1.55` (backend/.env, gitignored). Marcato Done.

### 7.3 — TASK-908 / TASK-909 riservati per analisi
Per richiesta di Andrea non si implementano ora:
- **TASK-908** (resume guard bearish, `parameter_updater.py`): blocco hardcoded di `resume_trading` in regime `trending_down` senza short.
- **TASK-909** (isolamento chiamate AI sincrone, `supervisor_client.py` via `asyncio.to_thread`): già archiviato Done (`docs/ARCHIVE_TASKS.md:2533`), richiamato per rivalutazione.

### 7.4 — Analisi "TASK-1154 dipende da API key?"
**Risposta: NO. Nessuna chiave da cercare.**
- `SentimentCollector` (`collectors/sentiment.py`) ha 3 fonti in cascata: CryptoCompare (key opzionale) → NewsAPI (key opzionale) → RSS feed (gratuito, sempre disponibile).
- `backend/.env` contiene GIÀ `NEWSAPI_API_KEY` e `CRYPTOCOMPARE_API_KEY` (verificato a repo). Il test live TASK-1150 riportava `source=cryptocompare+newsapi+rss`, `news_count=10`.
- Anche senza alcuna key, il collector degrada a RSS-only e continua a funzionare.
- Scope reale di TASK-1154 (da piano consolidato §Fase 4): priorità esplicita, fallback keyword "bull"/"bear" se tutto fallisce, cache 5 min (rate-limit), log compatto su errori DNS ripetuti. Tutto implementabile ora, senza procurarsi chiavi.

### 7.5 — TASK-1154 implementato (Done, 14/07)
File modificati/aggiunti:
- `synthtrade/backend/app/scalping/intelligence/collectors/sentiment.py` — priorità esplicita CC→NewsAPI→RSS; cache per-simbolo 5 min (`CACHE_TTL_SEC`); fallback neutro `SentimentData(source="fallback", score=0.0)` quando nessuna fonte risponde (invece di `None`); `_log_compact()` sopprime warning ripetuti per tipologia di errore consecutivo (nessun traceback moltiplicato).
- `synthtrade/backend/tests/scalping/test_sentiment_collector.py` (nuovo) — 6 test Red→Green: `test_priority_order_cryptocompare_first`, `test_fallback_to_newsapi_when_cryptocompare_fails`, `test_fallback_to_rss_when_both_key_sources_fail`, `test_keyword_fallback_when_all_sources_fail`, `test_zero_keys_uses_rss_only`, `test_cache_prevents_repeated_calls_within_5min`, `test_dns_failure_logs_compact_warning_not_full_traceback`.
- Verifica: `pytest tests/scalping/test_sentiment_collector.py tests/scalping/test_collector_provider_aware.py` → 21 passed. (I 41 fallimenti nello suite `tests/scalping` completo sono pre-esistenti e non legati a sentiment: es. `test_ws_client` `AttributeError: 'BinanceWSClient' object has no attribute '_dispatch'`, confermato anche stashando sentiment.py.)
- Log live atteso: `source=cryptocompare+newsapi+rss` in funzionamento normale; `source=fallback` solo in caso di outage totale di rete.
