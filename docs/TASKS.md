# TASKS.md — SynthTrade Task Tracking

## Task Attivi

### TASK-1130 — Fix: Missing _get_ccxt_symbol method in OkxExchangeAdapter

**Status:** ⚠️ REVERTED (2026-07-13)
**Priorità:** ALTA
**Dipendenze:** TASK-1129

**Problema:** Durante la riconnessione UDS (User Data Stream), il sistema chiamava `exchange._get_ccxt_symbol(pos.symbol)` ma `OkxExchangeAdapter` non implementava questo metodo, causando errori ripetuti ogni 10 secondi nei log: `'OkxExchangeAdapter' object has no attribute '_get_ccxt_symbol'`.

**Log osservato:**
```
2026-07-13 11:55:07,115 [WARNING] [sess_80352914] app.scalping.router: UDS reconnect sync: fetch_closed_orders failed: 'OkxExchangeAdapter' object has no attribute '_get_ccxt_symbol'
```

**File coinvolti:**
- `synthtrade/backend/app/execution/okx_exchange.py`
- `synthtrade/backend/app/scalping/router.py`

**Stato:** Revertito - il sistema funziona con i fix precedenti (TASK-1126) e il fallback REST polling gestisce correttamente gli eventi.

### TASK-1131 — CCXT REST fallback per OKX EU accounts

**Status:** ⚠️ REVERTED (2026-07-13)
**Priorità:** CRITICA
**Dipendenze:** TASK-1130

**Problema:** CCXT fallisce sistematicamente su OKX EU live accounts con errore 50119 ("API key doesn't exist"), mentre le chiamate REST dirette funzionano. Questo causa warning ripetuti durante la riconnessione UDS ogni 10 secondi quando si cerca di recuperare il fill price degli ordini.

**Stato:** Revertito - il fallback REST polling è operativo e gestisce gli eventi di fill senza errori critici. WS private failure (60032) non è bloccante.

## EPICA OKX — Migrazione Binance -> OKX (PRIORITA' ASSOLUTA)

**Status:** In Planning
**Priorità:** CRITICA
**Architettura:** `docs/architecture/okx-migration-architecture.md`
**Piano:** `docs/plans/okx-migration-implementation-plan.md`
**Breakdown dettagliato:** `docs/plans/okx-migration-task-breakdown.md`
**Motivazione:** Binance non e' piu' utilizzabile per trading in Italia; OKX diventa il provider operativo primario.

**Decisione chiave:** non portare Binance 1:1. Prima si introduce un layer exchange pluggable, poi si implementa OKX come adapter primario. Lo short/margin Binance viene sospeso: TASK-1000 resta storico/di riferimento, ma non e' piu' il prossimo task corretto.

**Regola multi-agente:** prima di iniziare un TASK-1100..1116, leggere il breakdown dettagliato e aggiornare `docs/HANDOFF.md` con stato, payload verificati, test eseguiti e decisioni residue.

### TASK-1100 — OKX Demo Spike: auth, market order, exit bracket, WS fill

**Status:** ✅ DONE — tutti i sottotask A–H completati (14/07/2026)
**Priorità:** CRITICA
**Dipendenze:** API key OKX Demo Trading ✅

**Nota 1100.G (14/07/2026):** chiuso come fatto. Il WS private OKX EEA non è disponibile (errore `60032` "API key doesn't exist") → il sistema usa il **REST polling di default** già implementato e operativo. Nessun lavoro aggiuntivo richiesto.

**Obiettivo:** verificare empiricamente OKX Demo Trading prima di modificare il runtime live.

**Output richiesto:**
- Script isolato `scripts/test_okx_demo.py` ✅
- Documento `docs/analysis/okx-demo-spike-results.md` con payload reali ✅
- Raccomandazione bracket: `order-algo` vs `attachAlgoOrds` ✅

**Stato 2026-07-03 10:45:**
- ✅ **1100.A** — Auth REST: risolto blocco `50119` con URL `eea.okx.com` per EU accounts
- ✅ **1100.B** — Server time: OK
- ✅ **1100.C** — Instrument discovery: 527 spot, 16 EUR live (`BTC-EUR` default confermato)
- ✅ **1100.D** — Fee tier: maker -0.2%, taker -0.35% (rebate!)
- ✅ **1100.E** — Market order: 10€ → 0.00022883 BTC @ 43700€, fee rebate OK
- ✅ **1100.F** — Exit bracket: algoId `3709954518432436224` piazzato con successo, metodo `order-algo` confermato
- ✅ **1100.H** — WS public trades: subscription OK, parser implementato, CVD mapping verificato
- ✅ **1100.G** — WS private EEA bloccato (errore 60032) → REST polling fallback

**Stato 2026-07-08 (Fix grafico OKX end-to-end):**
- ✅ **1100.G (Frontend: symbol normalization)** — Aggiunto `_normalizeSymbol()` in `live-chart.component.ts` per risolvere mismatch `BTCEUR` (stato sessione) vs `BTC-EUR` (instId OKX nei payload WS). Senza questo fix il subscriber scartava silenziosamente ogni candela real-time in arrivo dal backend.
- ✅ **1100.G (Backend: WS business pubblico)** — Spostato canale `candle1m` su WS business (`wss://ws.okx.com:8443/ws/v5/business`), `trades` resta su WS public. OKX ha spostato `candleX` dal public al business in una revisione API.
- ✅ **1100.G (Backend: market data sempre live)** — Rimosso branch EU-specific per WS pubblico (causava DNS loop su `wsaws.okx.com`). Market data usa SEMPRE endpoint live, indipendentemente da `demo` trading execution.
- ✅ **1100.G (Backend: router.py)** — Corretto percorso di ritorno in `GET /candles/{symbol}` per gestire il caso `past_candles` vuoto senza blocchi.
- ✅ **1100.G (Backend: type guard)** — Aggiunto guard difensivo `if current_url is None: current_url = url` in `_run_connection()` per eliminare warning Pylance.
- ⚠️ **Aperti:** Pylance warning su backup URL logic (proposto rimozione completa, non bloccante); audit altri componenti Angular per stesso mismatch simbolo.

**Stato 2026-07-09 (Fix regressione chart):**
- ✅ **1100.G (Backend: router.py indentation fix)** — Corretta indentazione dell'endpoint `@router.get("/candles/{symbol}")` che era erroneamente annidato dentro la funzione `get_trade_history`. Questo causava errore 404 e chart vuote. L'endpoint è ora a livello di modulo e restituisce correttamente i dati delle candele da HistoricalLoader.

**Decisione:**
- Demo mode influenza solo trading execution, MAI market data
- Candele OKX → WS business; Trade → WS public
- Simboli: normalizzare rimuovendo `-` e `/` prima di confrontare

**Verifica:**
- ✅ Backend riceve candele/trade OKX realtime confermato da log `>>> PROCESSING closed candle` senza riga REST corrispondente
- ✅ Frontend grafico si aggiorna in tempo reale dopo normalizzazione simbolo
- ✅ Codice Python compila senza errori

### TASK-1112 — Validazione Demo Trading end-to-end

**Status:** ✅ DONE (paper mode) — sessione BTC-EUR con OKX Demo WS funzionante, 9 bug fixati
**Priorità:** CRITICA
**Dipendenze:** TASK-1103, TASK-1104, TASK-1105, TASK-1106, TASK-1107

**Obiettivo:** sessione scalping completa in OKX Demo Trading con trade minimo, bracket server-side, fill e restore verificati.

**Completato 2026-07-03:**
- ✅ OKX Demo WS connesso `wss://wspap.okx.com/ws/v5/public?brokerId=9999`
- ✅ HistoricalLoader carica 100 candele OKX reali BTC-EUR via REST diretto (httpx)
- ✅ `demo=True` corretto quando `TRADING_MODE=test`
- ✅ Nessun errore 400 Binance Futures per EUR symbols (TASK-1116)
- ✅ Session save/stop/trade DB puliti
- ✅ "No open row found" risolto (mock generator non chiamava `_save_open_position_to_db`)
- ✅ PnL 54000% risolto (session_stop paper usava prezzo reale OKX invece di entry_price)
- ✅ 12/12 integration tests pass

**Bug fixati durante validazione:**
1. `set_sandbox_mode()` crash NoneType dopo EU URL override → rimosso, usa solo header
2. ccxt URL override fragile → sostituito con httpx diretto `eea.okx.com/api/v5/market/candles`
3. Mock generator mancava `_save_open_position_to_db` → aggiunto
4. Strategy 2 lookup entry_time string mismatch → Strategy 2a usa solo session+price
5. Paper session_stop usava `candle_buffer.latest` (prezzo reale ~54k€) per posizioni mock → usa `entry_price`
6. OkxWSClient symbol normalization (`BNBUSDC` → `BNB-USDC`) → aggiunto `_normalize_okx_symbol`

**Nota:** WS private (fill eventi bracket) non ancora testato in demo reale — richiede TASK-1100.G fix URL private endpoint.

### TASK-1126 — Fix: TP/SL fill detection su OKX EU accounts

**Status:** ✅ DONE (2026-07-13)
**Priorità:** CRITICA
**Dipendenze:** TASK-1100

**Problema:** OKX EU accounts hanno permessi limitati su `/api/v5/trade/orders-algo-history?ordType=oco` che ritorna 400 Bad Request. Questo causa TP/SL non rilevati, posizioni rimangono "open" dopo esecuzione, PnL calcolato solo su fees.

**File coinvolti:**
- `synthtrade/backend/app/execution/okx_order_event_stream.py`
- `synthtrade/backend/app/execution/okx_exchange.py`
- `synthtrade/backend/app/execution/exchange_models.py`
- `synthtrade/backend/app/scalping/router.py`
- `synthtrade/backend/app/main.py`

**Fix implementato:**
- Usare `/api/v5/trade/orders-history?state=filled` invece di `orders-algo-history`
- OKX EU: gli ordini algo (TP/SL) appaiono in `orders-history` con `algoId` popolato
- Consolidato chiamate duplicate in un'unica richiesta `orders-history?state=filled`
- Seed iniziale include sia ordini regolari che algo orders

**Verifica:**
- ✅ Nessun errore 400 nei log di startup
- ⏳ In attesa di esecuzione TP/SL reale per conferma fill detection

### TASK-1116.B — Bug: OKB-EUR mancante in FUTURES_SYMBOL_MAP collector

**Status:** 🐞 Bug — OKB-EUR causa 400 Bad Request Binance Futures
**Priorità:** ALTA
**Dipendenze:** TASK-1116

**Problema:** Sessione OKB-EUR (paper/demo) tenta chiamate a `fapi.binance.com/fapi/v1/openInterest?symbol=OKB-EUR` generando errori 400. Il simbolo OKB-EUR non è incluso nella mappa `FUTURES_SYMBOL_MAP` dei collector.

**Log osservato:**
```
2026-07-09 09:40:37 WARN OpenInterestCollector error for OKB-EUR: Client error '400 Bad Request' for url 'https://fapi.binance.com/fapi/v1/openInterest?symbol=OKB-EUR'
```

**File coinvolti:**
- `synthtrade/backend/app/scalping/intelligence/collectors/open_interest.py`
- `synthtrade/backend/app/scalping/intelligence/collectors/funding_rate.py`
- `synthtrade/backend/app/scalping/intelligence/collectors/long_short_ratio.py`

**Fix:**
- Aggiungere `"OKBEUR": None, "OKB-EUR": None` a `FUTURES_SYMBOL_MAP` in tutti e 3 i collector.
- OKX non ha futures perpetual per OKB-EUR → graceful skip corretto.

**Verifica:**
- Riavviare sessione OKB-EUR in paper mode.
- Verificare assenza warning 400 nei log.
- Score intelligence deve ricalcolare con collector disponibili.

### TASK-1116.C — Collector adapter provider-aware (OKX derivatives)

**Status:** ⚠️ Superseded — il lavoro è stato consolidato in TASK-1153 (vedi EPICA COLLECTOR INTELLIGENCE CONSOLIDATA sotto)
**Priorità:** —
**Dipendenze:** TASK-1116.B

**Nota:** Questo task è stato assorbito nel nuovo piano consolidato `docs/plans/collector-intelligence-implementation-plan.md` (TASK-1153). Non avviare implementazioni basate su questa sezione.

**Obiettivo:** rendere i collector (open_interest, funding_rate, long_short_ratio) provider-aware invece di hardcoded Binance Futures. Quando `EXCHANGE_PROVIDER=okx`, usare endpoint OKX derivatives (se disponibili) o graceful skip con log esplicito.

**Problema:** i collector chiamano direttamente `fapi.binance.com` ignorando `settings.EXCHANGE_PROVIDER`. Questo invalida le decisioni del supervisor quando si usa OKX.

**File coinvolti:**
- `synthtrade/backend/app/scalping/intelligence/collectors/open_interest.py`
- `synthtrade/backend/app/scalping/intelligence/collectors/funding_rate.py`
- `synthtrade/backend/app/scalping/intelligence/collectors/long_short_ratio.py`
- `synthtrade/backend/app/scalping/intelligence/signal_score_engine.py` (wiring)
- `synthtrade/backend/app/execution/exchange_factory.py` (eventuale factory collector)

**Sottotask:**
1. **1116.C.1 — CollectorAdapter interface**
   - Definire interfaccia read-only: `get_open_interest(symbol)`, `get_funding_rate(symbol)`, `get_long_short_ratio(symbol, period)`.
   - Implementare in `OkxExchangeAdapter` (OKX derivatives) o `None` se non disponibile.

2. **1116.C.2 — Refactor OpenInterestCollector**
   - Accettare `adapter` opzionale in `__init__`.
   - Se `adapter` fornito e provider=okx → chiamare `adapter.get_open_interest()`.
   - Se OKX non ha futures per il simbolo → log `UNAVAILABLE` e return `None`.
   - Se `adapter=None` → fallback Binance (backward compat).

3. **1116.C.3 — Refactor FundingRateCollector**
   - Stesso pattern: `adapter.get_funding_rate(symbol)`.
   - OKX funding rate via `/api/v5/public/funding-rate` (derivatives).

### TASK-1116.G — Instrument discovery deve essere environment-aware (Demo vs Live)

**Status:** Pending
**Priorità:** ALTA — causa fallimenti fee/trading silenziosi e fuorvianti per simboli validi in live ma assenti in demo

**Dipendenze:** TASK-1103 (OkxExchangeAdapter), TASK-1109 (Frontend exchange-neutral), TASK-1116.E (fallback fee REST)

**Problema:** OKB-EUR è tradeable in live ma non esiste in Demo Trading (errore 51001). Il sistema non distingue i due cataloghi, causando fallimenti silenziosi in fee/trading.

**File coinvolti:**
- `synthtrade/backend/app/execution/okx_exchange.py`
- `synthtrade/backend/app/scalping/router.py`
- `synthtrade/frontend/synthtrade-ui/src/app/scalping/services/exchange-symbols.service.ts`
- `synthtrade/frontend/synthtrade-ui/src/app/scalping/components/session-controls.component.ts`

**Sottotask:**
1. **1116.G.1 — Discovery cache environment-aware**: cache separata per demo/live
2. **1116.G.2 — Endpoint backend filtra per ambiente**: `/api/scalping/exchange/instruments` risponde solo strumenti validi
3. **1116.G.3 — Validazione pre-avvio sessione**: errore esplicito se simbolo non disponibile nell'ambiente
4. **1116.G.4 — Frontend: dropdown simboli filtrato dinamicamente**: aggiornamento al cambio modalità
5. **1116.G.5 — Messaggio UI esplicativo**: tooltip per simboli non disponibili in demo
6. **1116.G.6 — Test**: unit + integration test

**Verifica:** OKB-EUR non disponibile in dropdown demo; errore chiaro se forzato via API.

4. **1116.C.4 — Refactor LongShortRatioCollector**
   - OKX non ha long/short ratio → graceful skip con log `UNAVAILABLE`.

5. **1116.C.5 — SignalScoreEngine wiring**
   - Passare `adapter` ai collector in `get_or_create()` o costruttore.
   - Leggere `settings.EXCHANGE_PROVIDER` e `settings.exchange_demo`.

6. **1116.C.6 — Test**
   - Fake adapter con `get_open_interest` mockato.
   - Sessione OKX con collector OKX (o skip) → nessun 400 Binance.
   - Score reweighted correttamente quando collector non disponibile.

**Acceptance Criteria:**
- Sessione OKX non chiama mai Binance Futures per collector provider-bound.
- Log mostra `collector=okx_unavailable` o dati OKX reali.
- Score intelligence riflette i collector attivi/disponibili.

---

## EPICA COLLECTOR INTELLIGENCE — Consolidata (piano unico)

**Status:** In Planning
**Priorità:** CRITICA
**Piano:** `docs/plans/collector-intelligence-implementation-plan.md`
**Motivazione:** 5/8 collector non funzionanti (Funding Rate, CVD, Sentiment, Whale, On-Chain). Senza dati di mercato, SignalScoreEngine lavora con solo 3 collector. Questo profilo è inaccettabile nel nuovo contesto micro-swing (SL/TP 1,05%/1,55%, 10-30 trade/giorno).

**Nota:** I vecchi task TASK-1116.C e TASK-COLLECTOR-001→005 sono **Superseded**. Il lavoro descritto vive ora nei TASK-1150→1159 del piano consolidato.

### TASK-1150 — Abilitare whale collector + verificare sentiment su OKX

**Status:** Done ✅  
**Completato:** 2026-07-14
**Priorità:** 🔴 Alta — zero rischio, zero codice nuovo
**Stima:** 30 minuti
**Dipendenze:** nessuna

**Obiettivo:** Il collector `whale` (Whale Alert RSS + Blockchair, TASK-804) è già implementato e indipendente dall'exchange, ma disabilitato di default. Il collector `sentiment` (CryptoCompare + NewsAPI, TASK-804) è anch'esso indipendente dall'exchange ma non è mai stato riverificato con OKX attivo.

**Modifiche:**
1. In `.env`: `SCALPING_WHALE_ENABLED=true`
2. Verificare in log se la sola fonte Blockchair (senza `WHALE_ALERT_API_KEY`) produce dati utilizzabili
3. Avviare una sessione paper/demo e osservare per 30-60 minuti se `sentiment` risponde regolarmente

**Verifica di completamento:**
- Log mostra righe `whale` con valore popolato (non più sempre `None`)
- `[COVERAGE_REAL]` (TASK-1125) mostra un aumento del `configurable_total` e, se whale risponde, del `responded_weight`

### TASK-1151 — OrderBookImbalanceCollector

**Status:** ✅ Done (14/07/2026) — vedi piano consolidato `docs/plans/collector-intelligence-implementation-plan.md` §Fase 2
**Priorità:** 🔴 Alta
**Stima:** 3-4 ore
**Dipendenze:** nessuna

**Obiettivo:** Nuovo collector exchange-agnostico che calcola lo squilibrio bid/ask dall'order book pubblico OKX. Funziona su qualunque coppia spot OKX, incluso OKB-EUR.

**File:** `synthtrade/backend/app/scalping/intelligence/collectors/order_book_imbalance.py`

**Endpoint:** `GET https://eea.okx.com/api/v5/market/books?instId={instId}&sz=20`

### TASK-1152 — SpreadCollector

**Status:** ✅ Done (14/07/2026) — collector+modello implementati; wiring INTENZIONALMENTE DISATTIVATO (vedi piano consolidato)
**Priorità:** 🟡 Media
**Stima:** 2 ore
**Dipendenze:** nessuna

**Obiettivo:** Nuovo collector exchange-agnostico che calcola lo spread relativo come proxy di liquidità/incertezza.

**File:** `synthtrade/backend/app/scalping/intelligence/collectors/spread.py`

**Endpoint:** `GET https://eea.okx.com/api/v5/market/ticker?instId={instId}`

### TASK-1153 — CollectorAdapter provider-aware per funding_rate / open_interest / long_short_ratio

**Status:** Done ✅ — *supersede TASK-1116.C, TASK-COLLECTOR-001*
**Completato:** 2026-07-14
**Priorità:** 🟡 Media (impatto nullo su OKB-EUR, alto se si opera su BTC/ETH)
**Stima:** 4-5 ore
**Dipendenze:** TASK-1116.B (già fatto)

**Obiettivo:** Rendi i 3 collector provider-aware invece di hardcoded Binance Futures. Per OKB-EUR restano strutturalmente assenti per design.

**Modifiche (su working tree, da committare con TASK-1153):**
- `_provider_maps.py`: `OKX_PERPETUAL_MAP` (BTC→BTC-USDT-SWAP, ETH→ETH-USDT-SWAP, **OKB→OKB-USDT-SWAP** — il `None` era un bug, corretto 2026-07-14) + `extract_base_asset()`.
- `okx_exchange.py`: adapter methods `get_open_interest(inst_id)` / `get_funding_rate(inst_id)` / `get_long_short_ratio(base_asset, period)` (rubik endpoint, ritorna ratio).
- `open_interest.py` / `funding_rate.py` / `long_short_ratio.py`: accettano `adapter` opzionale; se provider=okx e perpetual esiste → endpoint nativi OKX, altrimenti graceful skip. **TASK-1158 implementato (2026-07-14):** `long_short_ratio.py` ora provider-aware OKX (rubik `ccy`, converte ratio→long/short% `ratio/(1+ratio)*100`, riusa `ratio_to_score`). `OKX_PERPETUAL_MAP["OKB"]="OKB-USDT-SWAP"` sblocca OI/funding/LSR su OKB.
- `signal_score_engine.py`: parametro `adapter` in `__init__` e `get_or_create` (risolve l'adapter via `get_adapter()` quando `EXCHANGE_PROVIDER=okx`, degrade a None su errore).
- `fake_okx_adapter.py`: adapter fake per test (`get_open_interest`/`get_funding_rate` + tracciamento `self.calls`).

**Test:** `tests/scalping/test_collector_provider_aware.py` (14 test, verdi) — path OKX-native, BTC-EUR active=on, OKB-EUR=None, binance legacy invariato, reweight score.

**Note:** `funding_rate.py` aveva un bug reale (uso di `timezone` non importato nel ramo OKX → `NameError` a runtime su BTC-EUR) corretto in questo task. I test pre-esistenti `test_funding_rate.py`/`test_open_interest.py`/`test_long_short_ratio.py` (7 failure) usano un mock `.json()` `AsyncMock` errato (httpx `.json()` è sincrono) e restano da sistemare (fuori scope, vedi fix successivo).

**File coinvolti:**
- `synthtrade/backend/app/scalping/intelligence/collectors/open_interest.py`
- `synthtrade/backend/app/scalping/intelligence/collectors/funding_rate.py`
- `synthtrade/backend/app/scalping/intelligence/collectors/long_short_ratio.py`
- `synthtrade/backend/app/scalping/intelligence/signal_score_engine.py`
- `synthtrade/backend/app/execution/okx_exchange.py`

### TASK-1154 — Sentiment collector: fallback affidabile

**Status:** Done — *supersede TASK-COLLECTOR-002* (14/07/2026)
**Priorità:** 🟡 Media
**Dipendenze:** TASK-1150 (verifica preliminare già fatta)

**Obiettivo:** Implementare fallback robusto quando API key mancano o sorgenti sono intermittenti.

**File:** `synthtrade/backend/app/scalping/intelligence/collectors/sentiment.py`

**Chiarimento dipendenza API key (14/07/2026):** TASK-1154 NON richiede di procurarsi alcuna API key.
Il `SentimentCollector` (`sentiment.py`) ha già 3 fonti: CryptoCompare (key opzionale), NewsAPI (key opzionale) e RSS feed (gratuito, sempre disponibile → fallback finale). `backend/.env` contiene GIÀ `NEWSAPI_API_KEY` e `CRYPTOCOMPARE_API_KEY` (verificato), quindi oggi gira con tutte e tre le fonti (confermato in TASK-1150: `source=cryptocompare+newsapi+rss`). Lo scope di 1154 è rendere il fallback *robusto* (ordine di priorità, fallback keyword se tutto fallisce, cache 5 min, log compatto su errori DNS) — funziona anche a zero key (solo RSS). Si può avviare subito, senza cercare chiavi.

### TASK-1155 — Whale collector: fonti OKX-compatibili

**Status:** 🔍 Analisi fatta (2026-07-14) — concluso: richiede Whale Alert API (a pagamento), nessuna fonte gratuita per OKB
**Priorità:** 🟢 Bassa
**Dipendenze:** TASK-1150

**Obiettivo:** Se dopo TASK-1150 il solo Blockchair risulta insufficiente, aggiungere Whale Alert API come opzione a pagamento.

**File:** `synthtrade/backend/app/scalping/intelligence/collectors/whale.py`

**Analisi (sessione live OKB-EUR, 2026-07-14):**
- `whale` risulta `active=on` ma `status=NONE` a ogni snapshot (`[COLLECTORS] ... whale=NONE`).
- Motivo: il `WhaleCollector` (TASK-804) usa **Blockchair**, che copre solo **BTC** ed **LTC**. OKB
  non esiste su Blockchair → nessun dato whale per OKB-EUR.
- L'unica fonte whale "exchange-aware" per asset OKX è **Whale Alert API** (a pagamento): va
  aggiunta come source opzionale nel collector, attivata solo se `WHALE_ALERT_API_KEY` è presente.
- **Nota per OKB:** anche con Whale Alert, la copertura di asset "mid-cap" come OKB è parziale
  (Whale Alert si concentra sui top asset). È quindi atteso che `whale` resti `NONE` su OKB-EUR
  finché non si valuta l'utilità reale del segnale. Per BTC-EUR/LTC-EUR il collector continua a
  funzionare con Blockchair.
- Il collector resta comunque "pronto a contribuire quando possibile" (graceful `None`, nessun
  impatto su score/coverage: `whale` è in `no_response_transient`, non in `structurally_unavailable`).

**Decisione:** TASK-1155 rimane aperto ma a bassa priorità. Non blocca la raccolta dati su OKB-EUR.
Da riprendere solo se si vuole il segnale whale anche su asset non-BTC/LTC (acquisto API key).

### TASK-1156 — On-chain collector: fallback Blockchair

**Status:** Pending — *supersede TASK-COLLECTOR-004*
**Priorità:** 🟢 Bassa
**Dipendenze:** nessuna

**Obiettivo:** Rendi funzionante con fonti gratuite. Per simboli EUR non-BTC/ETH, usare dati BTC/ETH come proxy macro.

**File:** `synthtrade/backend/app/scalping/intelligence/collectors/onchain.py`

### TASK-1157 — Verifica CVD grace period

**Status:** Pending — *supersede TASK-COLLECTOR-005*
**Priorità:** 🟡 Media
**Dipendenze:** nessuna

**Obiettivo:** Verificare se CVD funziona dopo 100 trade su OKB-EUR.

**File:** `synthtrade/backend/app/scalping/intelligence/collectors/cvd_calculator.py`

### TASK-1158 — Spike: esiste un equivalente OKX per Long/Short Ratio?

**Status:** ✅ Done (verifica empirica completata 2026-07-14)
**Priorità:** 🟢 Bassa
**Stima:** 1 ora (solo verifica documentale/empirica, no implementazione)
**Dipendenze:** nessuna

**Obiettivo:** Verificare su docs-v5 OKX se esiste un endpoint equivalente al long/short ratio Binance. Se esiste, aprire task dedicato. Se non esiste, documentarlo esplicitamente come strutturalmente assente.

**Risultato — SÌ, OKX ha l'endpoint (verificato con dati reali):**

- `GET /api/v5/rubik/stat/contracts/long-short-account-ratio?ccy=OKB&period=5m`
  → `code:"0"`, `data: [[ts, ratio], ...]`. Ultimo OKB (2026-07-14): **ratio ≈ 2.45**
  (≈ 71% long / 29% short). `ccy` = base asset (`OKB`, `BTC`, `ETH`).
- Variante per-strumento: `.../long-short-account-ratio-contract?instId=OKB-USDT-SWAP&period=5m`
  → stesso dato, più preciso (2.4534...).
- Limite rate: 5 req / 2s (IP + instrument). Periodi: `5m,1H,4H,1D,...`.

**Differenza chiave vs Binance:** OKX ritorna un **ratio** (`longShortAccount`), NON le
percentuali separate `longAccount`/`shortAccount` di Binance. Conversione da applicare:
`long_pct = ratio/(1+ratio)*100`, `short_pct = 100 - long_pct`. Per ratio=2.45 → 71.0% / 29.0%
(centra esattamente la soglia ">70% long → short squeeze" del `LongShortRatioCollector`).

**Scoperta collaterale (bug):** `OKX_PERPETUAL_MAP["OKB"] = None` in
`app/scalping/intelligence/collectors/_provider_maps.py:15` è **ERRATO**. OKX ha
`OKB-USDT-SWAP` (open-interest reale ~16.4M USD, verificato). Quel `None` blocca anche
`funding_rate.py` e `open_interest.py` per OKB (ritornano `NONE` pur essendo disponibili).
→ Da correggere a `"OKB-USDT-SWAP"` (vedi task implementazione sotto).

**Implementazione (2026-07-14, completata):** `LongShortRatioCollector` reso provider-aware
per OKX (ramo OKX in `is_symbol_supported`/`collect`); aggiunto `OkxExchangeAdapter.get_long_short_ratio`
(endpoint rubik) + `get_long_short_ratio` a `FakeOkxAdapter`; corretto `OKX_PERPETUAL_MAP["OKB"]="OKB-USDT-SWAP"`.
Conversione ratio→long/short% (`ratio/(1+ratio)*100`), riuso di `ratio_to_score`. Test aggiornati in
`tests/scalping/test_collector_provider_aware.py` (OKB-EUR ora supporta anche LSR/OI/funding).

### TASK-1159 — Ricalibrazione pesi SignalScoreEngine + nota cadenza micro-swing

**Status:** Pending — *bloccata finché le Fasi 1-5 non sono attive per almeno 2-3 sessioni reali*
**Priorità:** 🔴 Alta
**Dipendenze:** TASK-1150, 1151, 1152, 1153, 1154, 1157

**Obiettivo:** Redistribuire i pesi in `SignalScoreEngine.WEIGHTS` su numeri osservati dai log reali, non su placeholder.

**Nota:** Con 10-30 trade/giorno, il CVD potrebbe perdere peso relativo a favore di segnali più strutturali come Order Book Imbalance su finestre più larghe. Decisione da prendere solo dopo dati raccolti.

---

### TASK-906 — Trend Analysis: Prevenzione Falling Knife in Mean-Reversion (2026-06-30)

**Status:** Pending (in attesa del prossimo drop di mercato per raccogliere i dati reali)
**Priorità:** ALTA

**Obiettivo:** Bloccare i trade in "mean-reversion" durante crolli verticali improvvisi (falling knives), sfruttando le metriche di trend e velocità.

**Contesto:** Il bot ha effettuato 4 ingressi errati consecutivi durante un forte calo. L'eccezione del mean-reversion permetteva i BUY ignorando il bias bearish. Abbiamo aggiunto `trend_str` (che contiene `trend_5m` e `trend_direction`) ai log di esecuzione.

**Task (ex Step 5):**
1. **Data Collection:** Monitorare i log (live/paper) durante i prossimi cali improvvisi per registrare la velocità (`trend_5m`) in fase di "diverging".
2. **Rule Definition:** Definire la soglia dinamica corretta (es: `if trend_direction == "diverging" and trend_5m <= -X`).
3. **Implementation:** Aggiornare `app/scalping/engine/signal_aggregator.py` bloccando il trade in mean-reversion se la regola scatta.
4. **Verification:** Verificare che prevenga l'ingresso sui falling knife senza bloccare il mean-reversion legittimo su trend deboli.

---

### TASK-903 — RegimeDetector: isteresi K candele (2026-06-29)

**Status:** Pending
**Priorità:** MEDIA

**Problema:** Il regime cambia ad ogni candela se le soglie ATR/price_change oscillano vicino ai boundary → flickering → supervisor riceve contesti contraddittori → dati storici per regime inquinati.

**File da modificare:** `synthtrade/backend/app/scalping/engine/regime_detector.py`

**Implementazione:**
- Aggiungere `_pending_regime: Optional[str]` e `_pending_count: int`
- Il regime committed cambia SOLO se lo stesso candidato si osserva per K candele consecutive (default K=3, configurabile da `scalping_runtime_config`)
- Se il candidato cambia prima di K → reset counter
- Proprietà pubblica `pending_regime` per debug nel `/debug/pipeline` endpoint

**Verifica:** Su log di una sessione di 30 minuti, il regime non cambia più di 1 volta ogni 3 minuti.

---

### TASK-904 — StrategySelector DB-driven (2026-06-29)

**Status:** Pending
**Priorità:** BASSA
**Dipendenze:** TASK-902 (prerequisito logico — il supervisor context-aware è il consumatore principale)

**Problema:** Il mapping `regime → strategia_consentita` è hardcoded in due posti (`strategy_selector.py` e `supervisor_scheduler.py`). Il supervisor non può modificarlo senza deploy.

**File da modificare:**
- `synthtrade/backend/app/scalping/engine/strategy_selector.py` — leggere mapping da `scalping_runtime_config` con fallback agli attuali valori hardcoded
- `synthtrade/backend/app/scalping/supervisor/supervisor_scheduler.py` — sostituire `REGIME_ALLOWED_STRATEGIES` dict hardcoded con lettura da DB
- Migration: aggiungere chiavi `regime_strategy_*` a `scalping_runtime_config`

**Verifica:** Modificare via DB la strategia per `ranging` e verificare che il selector la usi nella sessione successiva senza restart.

---

### TASK-898 — Analisi Trend basata su dati persistiti (2026-06-29)

**Status:** Pending
**Priorità:** BASSA — dipende da raccolta dati reali
**Dipendenze:** TASK-895 ✅ + almeno 20 trade chiusi con `signal_log_id` popolato e `trend_direction` non null

**Prerequisito:** Verificare con:
```sql
SELECT COUNT(*) FROM scalping_trades t
JOIN session_signal_log sl ON sl.id = t.signal_log_id
WHERE t.status = 'closed' AND sl.trend_direction IS NOT NULL;
```
Se < 20 → non partire.

**Obiettivo:** Verificare se `trend_direction` (converging/diverging/stable) al momento dell'apertura è predittivo dell'outcome.

**Query di analisi:**
```sql
SELECT sl.trend_direction, sl.regime, sl.strategy_type,
    COUNT(t.id) AS n_trades,
    COUNT(t.id) FILTER (WHERE t.pnl > 0) AS n_wins,
    ROUND(AVG(t.pnl), 4) AS avg_pnl
FROM session_signal_log sl
JOIN scalping_trades t ON t.signal_log_id = sl.id
WHERE sl.decision_type = 'execute' AND t.status = 'closed'
  AND sl.trend_direction IS NOT NULL
GROUP BY sl.trend_direction, sl.regime, sl.strategy_type
HAVING COUNT(t.id) >= 5
ORDER BY sl.trend_direction, sl.regime;
```

**Note:** combinazioni con n_trades < 5 → "campione insufficiente". Incrociare con `tech_signal` per ipotesi direzionali.

**File da creare:** `docs/trend_analysis_report.md`

---

### TASK-907 — Bug Frontend: dati mancanti su reload con sessione PAUSED (2026-06-30)

**Status:** Pending
**Priorità:** ALTA — impatta l'usabilità della dashboard ogni volta che si ricarica la pagina con sessione in pausa

**Problema:** Ricaricando la pagina mentre la sessione è in stato `PAUSED`, i pannelli
`PERFORMANCE`, `TRADE LOG` e `RISK CONTROLS` risultano vuoti ("No performance yet",
"No trades yet", "Loading..." bloccato su Risk Controls), nonostante la sessione
abbia trade storici e configurazione di rischio attiva (visibili correttamente
quando la sessione è `RUNNING`).

**Ipotesi (da verificare):** il fetch iniziale di questi pannelli sul frontend è
probabilmente condizionato allo stato `running` della sessione (es.
`if (session.status === 'running') fetchData()`), oppure i dati arrivano solo via
WebSocket broadcast che parte/riprende solo in stato `running`, e il path di
caricamento REST iniziale per sessioni `paused` non viene eseguito o non gestisce
correttamente lo stato pausa.

**Comportamento atteso:** indipendentemente dallo stato della sessione (`running`,
`paused`), al caricamento/reload della pagina i pannelli devono mostrare i dati
storici già esistenti per la sessione corrente (trade log, performance aggregata,
risk controls configurati) — lo stato `paused` deve solo disabilitare nuove
operazioni, non nascondere lo storico.

**File coinvolti (da verificare, lato Angular):**
- `frontend/src/app/scalping/services/scalping-api.service.ts` (o equivalente) —
  verificare se le chiamate REST per trade log / performance / risk config sono
  condizionate dallo stato sessione
- `frontend/src/app/scalping/components/trade-log/` — verificare guardia su stato
  sessione nel template/component
- `frontend/src/app/scalping/components/performance-panel/` — idem
- `frontend/src/app/scalping/components/risk-controls/` — idem, capire perché resta
  su "Loading..." indefinito invece di andare in errore o popolarsi
- `frontend/src/app/scalping/services/scalping-ws.service.ts` — verificare se il
  fetch iniziale dipende da un primo messaggio WS che in stato `paused` potrebbe
  non arrivare mai

**Task:**
1. **Repro:** mettere una sessione in pausa, ricaricare la pagina, verificare in
   DevTools quali chiamate REST partono e quali no rispetto al caso `running`
2. **Root cause:** identificare se il problema è (a) guardia condizionale su
   `session.status` nei component, (b) dati attesi solo da WS che non arriva in
   pausa, o (c) endpoint backend che filtra erroneamente per `status='running'`
3. **Fix:** disaccoppiare il caricamento dello storico (trade log, performance,
   risk controls) dallo stato live della sessione — questi pannelli devono fare
   fetch REST al mount del componente indipendentemente da `running`/`paused`,
   mentre solo gli aggiornamenti realtime via WS restano legati allo stato attivo
4. **Verifica:** reload pagina con sessione `paused` → tutti e 3 i pannelli
   popolati con dati storici corretti, coerenti con quanto mostrato quando la
   sessione torna `running`

**Note:** il `RISK CONTROLS` bloccato su "Loading..." (invece di un empty state
o di un errore visibile) suggerisce che la promise/observable da cui dipende non
si risolve mai in questo stato — probabilmente sintomo della stessa causa radice
del punto 2(b) sopra.

---

### TASK-908 — Hardcoded Resume Guard (no-short, regime bearish) (2026-06-30)

**Status:** Riservato per analisi (richiesta Andrea 14/07/2026) — non implementare ora
**Priorità:** ALTA — *sospesa: da analizzare assieme a TASK-909*

**Nota 14/07/2026:** per decisione di Andrea, questo task e TASK-909 restano *riservati per analisi* (non avviati ora). TASK-909 è archiviato come Done in `docs/ARCHIVE_TASKS.md:2533` (isolamento chiamate AI sincrone via `asyncio.to_thread`), ma è richiamato per rivalutazione.

**Obiettivo:** impedire `resume_trading` quando `regime ∈ {trending_down}` con confidence
alta, `allows_short = False` (o short non implementato) e nessuna posizione aperta —
indipendentemente dal giudizio del modello AI.

**Contesto:** sessione live 30/06/2026 su BNBUSDC — 6 stop_loss consecutivi, ~5 segnali
SELL validi scartati (`Short selling non implementato`), `pause_trading` alle 16:43
(confidence 95%, motivata), `resume_trading` alle 16:54 con motivazione debole (Fear&Greed
extreme come contrarian, score -4.4) mentre il regime era ancora `trending_down` e lo
short non disponibile. Il pause era corretto; il resume successivo no, e ha riesposto
il sistema a un regime ancora avverso senza che nulla di strutturale fosse cambiato.

**File coinvolti:**
- `app/scalping/supervisor/parameter_updater.py`
- `app/scalping/supervisor/supervisor_scheduler.py` (o dove viene applicata la decisione)
- `app/scalping/supervisor/context_builder.py` (per esporre `short_enabled` nel context,
  già pianificato in `SynthTrade_Short_Selling_Architecture.md` §12)

#### Red — Test
- [ ] `test_resume_guard.py::test_blocks_resume_when_trending_down_and_no_short`
  — regime=`trending_down`, regime_confidence ≥ 0.7, `allows_short=False`,
  decisione AI=`resume_trading` → il guard la converte in `no_action` con
  `blocked_reason="resume_blocked: trending_down senza short abilitato"`
- [ ] `test_resume_guard.py::test_allows_resume_when_regime_not_bearish`
  — regime=`ranging` o `trending_up` → decisione AI `resume_trading` passa invariata
- [ ] `test_resume_guard.py::test_allows_resume_when_short_enabled`
  — regime=`trending_down`, `allows_short=True` → decisione passa invariata (il guard
  non deve interferire una volta implementato lo short)
- [ ] `test_resume_guard.py::test_allows_resume_when_confidence_low`
  — regime=`trending_down` ma `regime_confidence < 0.7` → decisione passa invariata
  (regime incerto, non vale la pena bloccare)
- [ ] `test_resume_guard.py::test_guard_does_not_affect_other_actions`
  — decisione AI=`update_params` con regime bearish → il guard non tocca nulla
  (si applica solo a `resume_trading`)
- [ ] `test_resume_guard.py::test_was_applied_false_and_reason_logged`
  — quando il guard blocca, il record salvato in `supervisor_memory` ha
  `was_applied=False` e `blocked_reason` valorizzato (stesso pattern già usato per i
  cooldown esistenti)

#### Green — Implementazione
- [ ] Aggiungere `short_enabled: bool` e `regime_confidence: float` al
  `SupervisorContext` (se non già presenti) in `context_builder.py`
- [ ] Implementare `_check_resume_guard(decision, context) -> tuple[bool, str | None]`
  in `parameter_updater.py`: ritorna `(blocked: bool, reason: str | None)`
- [ ] Soglia confidence hardcoded: `RESUME_GUARD_MIN_CONFIDENCE = 0.7` (costante, non
  DB — è una safety net, non un parametro di tuning)
- [ ] Applicare il guard PRIMA di eseguire `Resuming trading per supervisor decision`
  (stesso punto di log osservato: `app.scalping.supervisor.parameter_updater`)
- [ ] Se bloccato: log warning esplicito (`"Resume blocked by guard: regime=%s
  confidence=%.2f short_enabled=%s"`) e persistere `was_applied=False,
  blocked_reason=...`

#### Refactor
- [ ] Estrarre `RESUME_GUARD_MIN_CONFIDENCE` e la lista di regimi bloccanti
  (`{"trending_down"}`) in costanti di modulo riutilizzabili — quando lo short sarà
  implementato, valutare se includere anche `trending_up` simmetricamente per i long
  in caso di short-only temporanei (non ora, solo nota per il futuro)
- [ ] Aggiungere il campo `short_enabled` anche al payload broadcast via WebSocket
  della decisione supervisor, così il frontend può mostrare il motivo del blocco in
  AI Supervisor Log invece di un generico "no_action"

**Note di contesto per l'implementazione:**
- Il bug osservato non è nel `pause_trading` (motivato, confidence 95%, corretto) ma
  nel `resume_trading` successivo (confidence 72%, motivazione debole)
- Il guard deve essere **hardcoded**, non delegato al prompt — stesso principio già
  applicato per `_auto_adjust_threshold()` e i bound min/max della soglia
- Non bloccare `pause_trading` né `update_params` né `update_threshold` — solo
  `resume_trading` in queste condizioni specifiche

---

### EPICA SHORT SELLING

### TASK-1000 — WalletOrchestrator: Fase 1 (resolve puro + snapshot) (2026-06-30)

**Status:** Superseded by EPICA OKX (non avviare prima di TASK-1113)
**Priorità:** SOSPESA — il modello Binance Margin non e' piu' il percorso primario

**Nota 2026-07-02:** questo task era corretto per Binance Margin, ma OKX usa un modello diverso con Trading Account/tdMode e possibile auto-borrow/auto-repay. Conservare come riferimento storico; ripianificare lo short dopo la migrazione OKX.

**Obiettivo originale:** primo modulo della pipeline short, secondo
`SynthTrade_Short_Selling_Architecture.md` §3. Solo `snapshot()` e `resolve()` in
questo task — `execute()` e `verify()` (chiamate API reali) sono un task futuro
(TASK-910, da creare quando si arriva a quel punto).

**File coinvolti (nuovi):**
- `app/scalping/wallet_orchestrator.py`
- `tests/unit/test_wallet_orchestrator.py`

#### Red — Test (tutti su `resolve()`, puro, nessun mock API necessario)
- [ ] `test_resolve_funds_already_in_margin` — `snapshot.margin >= required` →
  `resolve()` ritorna lista vuota di `TransferStep` (nessun trasferimento necessario)
- [ ] `test_resolve_funds_only_in_spot` — margin=0, spot >= required → un solo
  `TransferStep(source=SPOT, target=MARGIN, amount=required)`
- [ ] `test_resolve_funds_distributed_spot_and_funding` — margin=0, spot=required*0.5,
  funding=required*0.5 → due `TransferStep`, totale = required, ordine: spot prima di
  funding (priorità da architettura §3.2)
- [ ] `test_resolve_funds_insufficient_total` — somma di tutti i wallet < required →
  solleva `InsufficientFundsError` con il deficit calcolato nel messaggio
- [ ] `test_resolve_uses_earn_as_last_resort` — margin=0, spot=0, funding=0,
  earn >= required → due step: redeem earn→spot, poi spot→margin (con nota
  `requires_delay=True` per il delay 2s tra i due step, da architettura §3.2)
- [ ] `test_resolve_excludes_locked_and_LD_prefixed_from_spot` — uno snapshot con
  `LDUSDC` nel balance spot non lo conta come fondo disponibile (stesso bug già
  risolto nel balance reader principale, da applicare anche qui)
- [ ] `test_resolve_does_not_call_any_api` — verificare (anche solo per design, es.
  controllo che `resolve()` non sia una coroutine `async`) che il metodo sia
  sincrono e puro, nessuna dipendenza da rete

#### Green — Implementazione
- [ ] Definire dataclass `WalletSnapshot(spot, margin, funding, earn)` e
  `TransferStep(source, target, asset, amount, requires_delay=False)` in
  `wallet_orchestrator.py`
- [ ] Implementare `WalletOrchestrator.resolve(snapshot, required, target) -> list[TransferStep]`
  seguendo l'ordine di priorità: margin già disponibile → spot → funding → earn (con redeem)
- [ ] Implementare `InsufficientFundsError(Exception)` con attributo `.deficit: float`
- [ ] Implementare `WalletOrchestrator.snapshot(asset) -> WalletSnapshot` — stub che
  in questo task può restituire dati letti da API reali (Binance) ma SENZA test live;
  i test su `snapshot()` reale (con mock httpx) sono in un task futuro insieme a
  `execute()`/`verify()`
- [ ] Filtro esplicito su asset `LD`-prefissati nel calcolo dello spot balance (stesso
  pattern già presente nel balance reader principale — riusare la stessa funzione di
  filtro se già esiste, altrimenti estrarla in helper condiviso)

#### Refactor
- [ ] Se esiste già una funzione di filtro `LD`-prefix nel balance reader principale,
  estrarla in `app/scalping/utils/balance_filters.py` e riusarla sia nel reader
  esistente sia in `WalletOrchestrator`, per evitare duplicazione della logica già
  corretta in produzione
- [ ] Documentare nel docstring di `resolve()` che è puro per design (nessuna chiamata
  di rete), così resta testabile senza mock in futuro

---

## Migrazione Bybit — CHIUSA

**Motivazione:** Dopo analisi e tentativo di verifica (TASK-1200), l'account Bybit EU (`bybit.eu`, MiCA) non permette la generazione di API key HMAC "System-generated" per trading automatizzato da client custom. L'unica opzione disponibile è "Connect to Third-Party Applications", un flusso pensato per bot/piattaforme whitelistate da Bybit (es. 3Commas, Bitsgap) — non utilizzabile dal backend FastAPI SynthTrade. La documentazione di supporto di 3Commas conferma: *"Bybit EU accounts cannot be connected to 3Commas via Fast Connect or API keys."*

**Conseguenza:** Si resta su OKX come unico exchange operativo. Il problema delle fee alte OKX (0.20%/0.35%, round-trip 0.70%) non viene risolto cambiando exchange, ma affrontato con la ricalibrazione di SL/TP (TASK-OKX-RECAL di seguito).

**Riferimenti ancora validi come documentazione tecnica (non come piano attivo):**
- `docs/analysis/bybit-api-reference-analysis.md`
- `docs/plans/bybit-migration-architecture-and-plan.md`
- `docs/plans/bybit-migration-plan-v2.md`

---

## TASK-OKX-RECAL — Ricalibrazione SL/TP su fee OKX reali

**Status:** ✅ Done (14/07/2026)
**Priorità:** CRITICA (completata) — SL/TP ricalibrati su fee OKX reali (STOP_LOSS=1.05%, TAKE_PROFIT=1.55% in backend/.env)
**Piano dettagliato:** `docs/plans/okx-sl-tp-recalibration-task.md`

**Motivazione:** Lo SL configurato a 0.3% è geometricamente impossibile con le fee OKX reali. Il round-trip taker+taker costa 0.70%. Qualunque SL con magnitudine < 0.70% è matematicamente insostenibile — il prezzo dovrebbe muoversi nella direzione opposta a quella di uno stop loss per far quadrare i conti.

**Fee OKX reali (confermate da screenshot "Il mio livello di commissioni"):** maker=0.20%, taker=0.35%
**Round-trip reale (entry market + exit market al trigger, entrambi taker):** R = 0.35% + 0.35% = **0.70%**

**Opzione B — raccomandata per il primo test:**
| Parametro | Valore netto | Distanza gross |
|-----------|-------------|----------------|
| SL | 1.05% | 0.35% |
| TP | 1.55% | 2.26% |
| R:R | 1.48:1 | — |

### Modifiche da applicare

**`.env` / `config.py`:**
```bash
# PRIMA (insostenibile con fee reali OKX):
SCALPING_STOP_LOSS_PCT=0.3
SCALPING_TAKE_PROFIT_PCT=0.5

# DOPO (opzione B, ricalibrata su fee reale 0.20%/0.35%):
SCALPING_STOP_LOSS_PCT=1.05
SCALPING_TAKE_PROFIT_PCT=1.55
```

**Verifica preliminare obbligatoria (§1 del piano):**
Prima di procedere, eseguire audit Supabase per verificare che `fee_tier_certified=true` sulle sessioni recenti:
```sql
SELECT id, started_at, mode, fee_tier_certified, fee_tier_raw
FROM scalping_sessions
WHERE mode = 'live' AND started_at > now() - interval '14 days'
ORDER BY started_at DESC;
```
Se `fee_tier_certified=false` sulla maggioranza, il problema non è solo il target SL/TP ma il fatto che `get_trade_fee()` sta fallendo silenziosamente e cadendo sul fallback 0.001/0.001 — va fixato prima di procedere (fix non stimato in questo task, da valutare separatamente).

### Test da aggiungere
Test esplicito in `test_okx_integration.py` con fee OKX reali (maker=0.0020, taker=0.0035) e target ricalibrati, verificando:
- Segno corretto di sl_price per BUY (sotto entry)
- Distanza gross corrispondente alla tabella (tolleranza 0.01%)

### Sequenza di verifica
1. Applicare modifiche `.env`
2. Eseguire test — deve passare senza modificare logica esistente
3. Avviare sessione **paper**: verificare log `[NET_PRICING]` con i nuovi target
4. Solo se §1 conferma `fee_tier_certified=true`: avviare sessione **demo** OKX con trade minimo
5. Solo dopo demo pulita: valutare live con capitale minimo (conferma manuale)

**Nota sul confronto economico:** Il win rate storico (34.3% su 70 trade) non è un baseline affidabile perché quei trade usavano SL/TP 0.3%/0.5% geometricamente incoerenti con le fee reali. Serve un nuovo campione di sessioni con target ricalibrati prima di trarre conclusioni quantitative.

---

## Ordine di esecuzione consigliato

1. **TASK-1100** ✅ partial — spike OKX Demo Trading completato (A-F/H ✅, G workaround REST polling per WS privato bloccato).
2. **TASK-1101 -> TASK-1116** ✅ config, adapter REST, WS market data, order stream, router provider-neutral, DB migration, frontend exchange-neutral, backtest factory, integration tests, validazione e2e.
3. **TASK-1113** — Cutover OKX live readiness: rendere OKX provider primario e preparare go-live (prossimo passo critico).
4. **TASK-1114** — OKX fee tier e net pricing parity: preservare logica fee-aware su OKX.
5. **TASK-1117 -> TASK-1118** — Bug da recap 2026-07-08: constraint DB `rejected_short_unsupported` e audit frontend symbol normalization.
6. **TASK-OKX-RECAL** — Ricalibrazione SL/TP su fee OKX reali (NUOVO, priorità assoluta)
7. **TASK-907 / TASK-908** — bug non OKX (frontend paused reload, resume guard).

Le fasi successive dello short (`MarginBorrowManager`, `OrderExecutor` margin,
`ExecutionLoop` branch short, migration DB) restano come da
`SynthTrade_Short_Selling_Architecture.md` §11, Fasi 2-6, da spezzare in task
separati (TASK-910 in poi) quando si arriva a quel punto.

---

## 📋 Task da Investigare — Risultati

> Bug identificati in `MASTER_RECAP.md` del 26/06/2026. Verifica completata il 01/07/2026.

| Task | Status | Note |
|------|--------|------|
| **TASK-INVEST-001** — sync strategy_selected vs strategy_executed | ✅ **FATTO** | Corretto in frontend |
| **TASK-INVEST-002** — Regressione doppio avvio WS | ✅ **FATTO** | Risolta regressione 27-28/06 |
| **TASK-INVEST-003** — Buffer mismatch warmup/ExecutionLoop | ✅ **FATTO** | Allineamento buffer confermato |
| **TASK-INVEST-004** — pause_trading permanente su regime unknown | ✅ **FATTO** | Ripresa automatica regime unknown implementata |
| **TASK-INVEST-005** — Position.entry_commission non popolato | ✅ **FATTO** | Popolato via WebSocket commission reali (TASK-876) |
| **TASK-INVEST-006** — get_trade_fee() fallback silenzioso | ✅ **FATTO** | flag `fee_tier_certified` implementato e funzionante |
| **TASK-INVEST-007** — GET /position non converte BNB→USDC | ✅ **FATTO** | Fix conversione BNB→USDC applicato in router.py |
| **TASK-INVEST-008** — SELL mean-reversion bloccato da bias bullish | ✅ **FATTO** | Sblocco SELL mean-reversion confermato simmetrico a BUY |
| **TASK-INVEST-009** — Insufficient funds per minNotional | ✅ **FATTO** | Fix minNotional in router.py applicato e funzionante |
| **TASK-INVEST-010** — Assenza cooldown dopo consecutive losses | ✅ **FATTO** | Pausa automatica dopo N stop_loss consecutivi implementata |
| **TASK-INVEST-011** — Regime misclassification (volume-confirmed breakdown) | 🟡 **APERTO** | Nessuna logica volume-confirmed in `regime_detector.py` |
| **TASK-INVEST-012** — Falling Knife Protection non implementata | 🟡 **APERTO** | Tendenza allineata a TASK-906 (in attesa dati reali) |
| **TASK-INVEST-013** — trend_direction stabile su variazioni piccole persistenti | ⚠️ **PARZIALE** | Codice presente ma soglia troppo sensibile |
| **TASK-INVEST-014** — Supervisor non ha visibilità blocco SHORT nel prompt | ✅ **FATTO** | System prompt menziona blocco short |
| **TASK-INVEST-015** — APScheduler job missed ripetuti | ✅ **FATTO** | Log APScheduler puliti, nessun job missed |
| **TASK-INVEST-016** — CryptoCompare/RSS feed intermittenti | ✅ **FATTO** | Feed CryptoCompare + RSS stabili |
| **TASK-INVEST-017** — Bias outcome_label Supervisor in mercato laterale | ⚠️ **PARZIALE** | Codice presente ma outcome_label usa solo PnL (no bias regime) |
| **TASK-INVEST-018** — Soglia dinamica Supervisor senza decadimento | ⚠️ **PARZIALE** | Commenti in `supervisor_client.py` ma decay/degradation non implementato |
| **TASK-INVEST-019** — 5/8 collector Intelligence non funzionanti | ⚠️ **PARZIALE** | Circuit breaker presenti ma CVD/OI/LSR dipendono da futures (5/8 falliscono) |
| **TASK-INVEST-020** — Slope filter su EMA Cross causa regressione | 🟡 **APERTO** | Nessuno slope filter in `ema_cross.py` |

