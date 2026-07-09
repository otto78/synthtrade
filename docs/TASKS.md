# TASKS.md — SynthTrade Task Tracking

## Task Attivi

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

**Status:** Partial ✅ — Sottotask E/F/H completati, G workaround implementato
**Priorità:** CRITICA
**Dipendenze:** API key OKX Demo Trading ✅

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

### TASK-1101 — Config provider OKX e credenziali demo/live

**Status:** ✅ DONE — implementato 2026-07-03 (verificato 2026-07-08)
**Priorità:** ALTA
**Dipendenze:** TASK-1100 per conferma header demo

**Obiettivo:** aggiungere `EXCHANGE_PROVIDER=okx`, credenziali OKX demo/live e computed field generici senza rompere Binance legacy.

**Completato:**
- ✅ **1101.A — Settings**: `EXCHANGE_PROVIDER`, `OKX_API_KEY`, `OKX_SECRET_KEY`, `OKX_PASSPHRASE`, `OKX_BASE_URL` in `config.py` (linee 107-120)
- ✅ **1101.B — Computed fields**: `exchange_api_key`, `exchange_secret_key`, `exchange_passphrase`, `exchange_demo`, `exchange_display_name` (linee 135-167)
- ✅ **1101.C — Sicurezza live**: `ALLOW_LIVE_MODE=false` blocca live, nessun log di secret/passphrase
- ✅ **1101.D — Env example**: `.env.example` documenta OKX demo/live, passphrase obbligatoria, differenza URL EU vs global
- ✅ **1101.E — Test**: Default provider okx, override env OKX, Binance legacy backward compat

**File coinvolti:**
- `synthtrade/backend/app/config.py` — Settings class con campi OKX
- `synthtrade/backend/.env.example` — documentazione setup OKX

### TASK-1102 — ExchangeProtocol v2 provider-neutral

**Status:** ✅ DONE — implementato 2026-07-03 (verificato 2026-07-08)
**Priorità:** ALTA
**Dipendenze:** TASK-1101

**File coinvolti:**
- `synthtrade/backend/app/execution/exchange_models.py`

**Obiettivo:** sostituire semantiche Binance-specifiche (`place_oco_order`, symbol compact-only, filtri Binance) con richieste di dominio SynthTrade: market order, close position, symbol rules, exit bracket, fee tier certificato.

**Completato:**
- ✅ **1102.A — Modelli dominio**: `SymbolRef`, `SymbolRules`, `MarketOrderRequest`, `ClosePositionRequest`, `ExitBracketRequest`, `ExchangeOrder`, `ExitBracketOrder`, `FeeTier` tutti in `exchange_models.py`
- ✅ **1102.B — Protocollo**: `ExchangeAdapterProtocol` in `exchange_models.py` (linee 212-237) con `place_exit_bracket` (non `place_oco_order`)
- ✅ **1102.C — Compat Binance**: `BinanceExchangeAdapter` preservato, `place_oco_order` come wrapper deprecato
- ✅ **1102.D — Errori comuni**: `ExitProtectionError`, `ExchangeAuthError`, `ExchangeNetworkError`, `UnsupportedInstrumentError`
- ✅ **1102.E — Test**: FakeOkxAdapter implementa protocollo, testato in test_okx_integration.py (12/12 PASS)

### TASK-1103 — OkxExchangeAdapter REST base

**Status:** ✅ DONE — implementato 2026-07-03
**Priorità:** ALTA
**Dipendenze:** TASK-1102

**Obiettivo:** implementare balance, holdings, ticker, symbol rules, instrument discovery, market order e fee tier per OKX via ccxt/nativo, usando Demo Trading in test manuale.

**Completato 2026-07-03:**
- ✅ `synthtrade/backend/app/execution/okx_exchange.py` implementa `ExchangeAdapterProtocol`
- ✅ `get_balance(asset)`, `get_holdings()`, `get_ticker_price(symbol)` con cache 15s
- ✅ `get_symbol_rules(SymbolRef)` con cache 5min (lotSz/minSz/tickSz/maxMktSz/maxMktAmt)
- ✅ `get_trade_fee(SymbolRef)` — fee OKX sono rebate negativi (maker=-0.002, taker=-0.0035)
- ✅ `place_market_order(MarketOrderRequest)` — spot cash, supporta `tgtCcy=quote_ccy`
- ✅ `close_position(ClosePositionRequest)`, `place_exit_bracket(ExitBracketRequest)`
- ✅ `get_open_exit_orders()`, `cancel_open_exit_orders()`
- ✅ `from_settings()` classmethod costruisce da `app.config.settings`

### TASK-1104 — OKX Exit Bracket server-side

**Status:** ✅ DONE — implementato 2026-07-03 (verificato 2026-07-08)
**Priorità:** CRITICA
**Dipendenze:** TASK-1100, TASK-1103

**Obiettivo:** implementare `place_exit_bracket()` per OKX con TP/SL server-side e emergency close se la protezione fallisce.

**Completato:**
- ✅ **1104.A — Decisione tecnica**: Confermato uso `order-algo` (POST `/api/v5/trade/order-algo`) con `tpTriggerPx`/`slTriggerPx` e `tpOrdPx="-1"`/`slOrdPx="-1"` per market order al trigger. Documentato in `okx-demo-spike-results.md`.
- ✅ **1104.B — Request model**: `ExitBracketRequest(symbol, side, quantity, tp_price, sl_price, entry_order_id, fee_tier)` in `exchange_models.py`
- ✅ **1104.C — Price validation**: `rules.round_price()` e `rules.round_qty()` applicati. Long close sell: TP sopra last, SL sotto last.
- ✅ **1104.D — Place bracket**: `place_exit_bracket()` in `okx_exchange.py` (righe 279-359) parametri OKX mappati, `algoId` parsato da risposta, raw payload preservato.
- ✅ **1104.E — Emergency close**: Se bracket fallisce → market close immediato + `ExitProtectionError` sollevato. Se emergency close fallisce → log error ma eccezione propagata comunque.
- ✅ **1104.F — Test**: TASK-1111 test 1111.B copre bracket reject → emergency close → no DB open. Test 1111.A copre happy path bracket success.

**File coinvolti:**
- `synthtrade/backend/app/execution/okx_exchange.py` — `place_exit_bracket()`
- `synthtrade/backend/app/execution/exchange_models.py` — `ExitBracketRequest`, `ExitBracketOrder`, `ExitProtectionError`
- `synthtrade/backend/tests/integration/test_okx_integration.py` — test 1111.A e 1111.B
- `synthtrade/backend/tests/integration/fake_okx_adapter.py` — `simulate_tp_fill()`, `bracket_fails`

**Verifica:** Nessuna posizione salvata su DB senza bracket confermato o close di emergenza (testato in 1111.B).

### TASK-1105 — OkxWSClient market data

**Status:** ✅ DONE — completato 2026-07-08 con fix end-to-end grafico live
**Priorità:** ALTA
**Dipendenze:** TASK-1100

**Obiettivo:** sostituire `BinanceWSClient` nel path scalping con un client provider-neutral e parser OKX per candle/trade.

**Completato 2026-07-08:**
- ✅ Market data (candele/trade) sempre su endpoint live, non condizionato da `demo`
- ✅ Canale `candle1m` spostato su WS business (`wss://ws.okx.com:8443/ws/v5/business`), `trades` resta su WS public
- ✅ Rimosso logica EU-specific per WS pubblico (causava DNS loop su `wsaws.okx.com`)
- ✅ Frontend `_normalizeSymbol()` aggiunto per risolvere mismatch `BTCEUR` vs `BTC-EUR`
- ✅ `router.py`: corretto return path in `GET /candles/{symbol}` per `past_candles` vuoto

**File:**
- `synthtrade/backend/app/scalping/engine/okx_ws_client.py`
- `synthtrade/backend/app/scalping/router.py`
- `synthtrade/frontend/synthtrade-ui/src/app/scalping/components/live-chart.component.ts`

### TASK-1106 — OkxOrderEventStream per fill TP/SL

**Status:** ✅ DONE — implementato 2026-07-03
**Priorità:** CRITICA
**Dipendenze:** TASK-1100, TASK-1104

**Obiettivo:** normalizzare gli eventi OKX di fill bracket nello stesso formato consumato da `_on_order_update`.

**Completato 2026-07-03:**
- ✅ `synthtrade/backend/app/execution/okx_order_event_stream.py` implementa stessa interfaccia di `UserDataStreamManager`
- ✅ Login WS OKX con firma HMAC-SHA256 + base64
- ✅ Sottoscrizione canali `orders` e `algo-orders`
- ✅ `_normalize_order` e `_normalize_algo_order` mappano stati OKX → dict contratto router
- ✅ Fee OKX negative (rebate) → `commission = abs(fee)` per compatibilità router
- ✅ `from_settings()` classmethod
- ✅ `exchange_factory.py` aggiornato con `get_order_event_stream()` provider-aware

### TASK-1107 — Router scalping provider-neutral

**Status:** ✅ DONE (100%) — provider-neutral completo incluso `_live_close_position`
**Priorità:** CRITICA
**Dipendenze:** TASK-1102, TASK-1105, TASK-1106

**Obiettivo:** rimuovere assunzioni Binance da start/stop/restore sessione, costruendo exchange, market WS e order stream via factory.

**Completato 2026-07-03:**
- ✅ Entry flow: `place_exit_bracket(ExitBracketRequest)` provider-neutral
- ✅ Bracket failure handler: `_handle_bracket_failed` usa `cancel_open_exit_orders` + `ClosePositionRequest`
- ✅ `_on_order_update`: usa `bracket_id` e campo `leg` (OKX: take_profit/stop_loss diretto)
- ✅ `_live_close_position`: convertito a provider-neutral (`cancel_open_exit_orders`, `get_holdings`, `get_symbol_rules.round_qty`, `close_position(ClosePositionRequest)`)
- ✅ Session start/DB/WS/order stream provider-neutral
- ✅ 12/12 integration tests passano (TASK-1111)

### TASK-1108 — DB migration provider e order ids generici

**Status:** ✅ DONE — Migration applicata a Supabase
**Priorità:** ALTA
**Dipendenze:** TASK-1107

**Obiettivo:** aggiungere provider, account mode, order ids e raw payload a sessioni/trade mantenendo compatibilita' con lo storico Binance.

**File:** `synthtrade/supabase/migrations/20260703000000_task1108_okx_provider_columns.sql`

**Colonne aggiunte e verificate:**
- `scalping_sessions`: exchange_provider, exchange_account_mode, exchange_demo, fee_tier_*
- `scalping_trades`: exchange_provider, exchange_order_id, exchange_bracket_id, exchange_tp/sl_order_id, exchange_raw
- Index: idx_scalping_trades_exchange_order_id/bracket_id
- Backfill: oco_order_list_id → exchange_bracket_id

### TASK-1109 — Frontend exchange-neutral

**Status:** ✅ DONE — label "Saldo Binance" dinamica (OKX/Binance/Exchange)
**Priorità:** MEDIA
**Dipendenze:** TASK-1107, TASK-1108

**Completato 2026-07-03:**
- ✅ `dashboard.model.ts`: aggiunto `exchange_provider?: string` a `DashboardStats`
- ✅ `dashboard.page.ts`: `balanceLabel()` computed signal → "Saldo OKX" / "Saldo Binance" / "Saldo Exchange"
- ✅ `dashboard.py`: aggiunto `exchange_provider` nel return dict

### TASK-1110 — Market data/backtest factory cleanup

**Status:** ✅ DONE — HistoricalLoader OKX via ccxt, Binance come fallback
**Priorità:** MEDIA
**Dipendenze:** TASK-1101, TASK-1103

**Obiettivo:** rimuovere `ccxt.binance()` diretto da market data, generator/backtest e servizi condivisi; usare factory provider-aware.

**Completato 2026-07-03:**
- ✅ `_load_from_okx()` via ccxt async `fetch_ohlcv`, EU URL override con guard `if v`
- ✅ `_load_from_binance()` come metodo separato
- ✅ `load_ohlcv()` dispatch su `settings.EXCHANGE_PROVIDER`
- ✅ Fallback a Binance solo per simboli non-EUR se OKX fallisce
- ✅ Fix NoneType in ccxt URL dict comprehension (`if v else v`)

**File:** `synthtrade/backend/app/scalping/backtest/historical_loader.py`

### TASK-1111 — Test integration con fake OKX adapter

**Status:** ✅ DONE — 12/12 test passano
**Priorità:** ALTA
**Dipendenze:** TASK-1107

**Obiettivo:** coprire start -> entry -> bracket -> fill -> DB/UI close senza chiamate reali, con fake adapter e fake order stream.

**Completato 2026-07-03:**
- ✅ `fake_okx_adapter.py` — FakeOkxAdapter + FakeOrderStream senza rete
- ✅ **1111.A** — Happy path: entry → bracket → TP fill → position closed
- ✅ **1111.B** — Bracket failure: entry OK → bracket reject → emergency close → no DB open
- ✅ **1111.C** — Stop session: cancel bracket → market close → DB reason=session_stop
- ✅ **1111.D** — Restore open: bracket attivo → order stream restart → TP fill ricevuto
- ✅ **1111.E** — Restore closed: no bracket su exchange → DB reconciled
- ✅ **1111.F** — Fee/net pricing: OKX rebate abs() corretto

**Bug trovato e fixato:** router usava fee OKX negative raw (`-0.0035`) in `_net_to_gross_pct`, producendo TP/SL invertiti. Fix: `abs(fee)` su `entry_fee_pricing` e `exit_fee_pricing` in `router.py`.

**File:**
- `synthtrade/backend/tests/integration/fake_okx_adapter.py`
- `synthtrade/backend/tests/integration/test_okx_integration.py`
- `synthtrade/backend/app/scalping/router.py` (bug fix fee abs)

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

### TASK-1113 — Cutover OKX live readiness

**Status:** ✅ DONE — 2026-07-08
**Priorità:** CRITICA
**Dipendenze:** TASK-1112

**Obiettivo:** rendere OKX provider primario, aggiornare setup operativo, checklist go-live e primo test live minimo solo dopo conferma manuale.

**Completato 2026-07-08:**
- ✅ **1113.A — Default config**: `.env.example` già configurato con `EXCHANGE_PROVIDER=okx` e `TRADING_MODE=test`. Binance legacy documentato come fallback.
- ✅ **1113.B — Safety gates**: `ALLOW_LIVE_MODE=false`, `TRADING_MODE=test`, `SCALPING_FORCE_PAPER=true` già attivi. Trade value minimo consigliato: Paper 10€, Demo 10€, Live iniziale 20€.
- ✅ **1113.C — Smoke tests**: Health check OK (`{"status":"ok"}`), Instruments OKX caricati (1INCH-EUR, BTC-EUR, ecc.), Candele OKX verificabili via `/candles/btceur`.
- ✅ **1113.D — Runbook**: Creato `docs/analysis/okx-live-runbook.md` con setup API key, safety gates, smoke test checklist, emergency stop procedure, go-live checklist, rischi e mitigazioni.
- ✅ **1113.E — Decisione go-live**: Documentata in runbook §7. Primo trade live minimo (20€) richiede conferma manuale esplicita.

**Decisioni chiave:**
- OKX è default operativo dal 2026-07-03 (TASK-1101), confermato da sessioni paper di luglio
- Live trading non può partire accidentalmente (ALLOW_LIVE_MODE=false, SCALPING_FORCE_PAPER=true)
- Runbook disponibile per agenti futuri in `docs/analysis/okx-live-runbook.md`
- Prima del go-live live reale, serve validazione bracket in demo reale (TASK-1100.G pendente)

### TASK-1114 — OKX fee tier e net pricing parity

**Status:** ✅ DONE — 2026-07-08
**Priorità:** CRITICA
**Dipendenze:** TASK-1100, TASK-1103, TASK-1104

**Obiettivo:** preservare su OKX la logica attuale di fee reali: recupero fee tier a inizio sessione, `fee_tier_certified`, calcolo TP/SL lordo da target netto, log `[NET_PRICING]`, PnL/trade log coerenti e commissioni reali da fill.

**Completato 2026-07-08:**
- ✅ **1114.A — Fee model**: `FeeTier(maker, taker, certified, raw, source)` già in `exchange_models.py` (linee 96-102). Persistenza su sessione via `_execution_state["fee_tier"]` e `fee_tier_certified`.
- ✅ **1114.B — Quote-aware commission conversion**: Già implementata in `router.py` — se `exit_commission_asset != quote_asset`, usa `exchange.get_ticker_price(f"{asset}/{quote}")` per conversione generica (es. OKB/EUR, BNB/USDT). Non più hardcoded BNB→USDC.
- ✅ **1114.C — Net to gross**: `_net_to_gross_pct()` parametrizzata con `entry_fee_pricing` e `exit_fee_pricing`. OKX rebate negativi gestiti con `abs()` (fix TASK-1111).
- ✅ **1114.D — Log `[NET_PRICING]` arricchito**: Ora include `provider`, `symbol`, `maker`, `taker`, `certified` in aggiunta ai target netti/lordi esistenti.
- ✅ **1114.E — Position/trade updates**: Position update mostra target netti (TASK-885). Trade log salva fee reali via WebSocket e fee tier attese. Commissioni negative OKX (rebate) normalizzate con `abs()`.
- ✅ **1114.F — Tests**: Coperto dal test `test_1111f_net_to_gross_pricing_okx_fees()` in `test_okx_integration.py` — verifica fee OKX rebate + net pricing con `abs()` corretto.

**File coinvolti:**
- `synthtrade/backend/app/scalping/router.py` — `[NET_PRICING]` log arricchito, `abs()` su fee OKX rebate
- `synthtrade/backend/app/execution/exchange_models.py` — `FeeTier` dataclass
- `synthtrade/backend/app/execution/okx_exchange.py` — `get_trade_fee()` con OKX rebate
- `synthtrade/backend/tests/integration/test_okx_integration.py` — test 1111f fee/net pricing

**Verifica:** log sessione paper 2026-07-08 mostra `[NET_PRICING] provider=okx symbol=BTCEUR maker=... taker=... certified=...` con target netti e lordi coerenti.

### TASK-1115 — Dashboard balance provider-neutral

**Status:** ✅ DONE — okx_balance.py + dispatch provider in dashboard API
**Priorità:** ALTA
**Dipendenze:** TASK-1101, TASK-1103

**Completato 2026-07-03:**
- ✅ `okx_balance.py`: fetch funding + trading wallet OKX, conversione EUR via tickers REST
- ✅ `dashboard.py`: dispatch dinamico `okx_balance` vs `binance_balance` su `EXCHANGE_PROVIDER`
- ✅ Smoke test: 112k€ saldo demo OKX (BTC, XRP, EUR, USDC, ETH) ✅

### TASK-1116 — Audit collector Binance/Futures per migrazione OKX

**Status:** ✅ DONE — EUR symbols graceful skip implementato su tutti i collector Binance Futures
**Priorità:** ALTA
**Dipendenze:** TASK-1105

**Obiettivo:** identificare e gestire tutte le fonti Binance usate dai segnali e opportunity: funding rate, open interest, long/short ratio, CVD trade stream, Binance announcements, market data/backtest.

**Completato 2026-07-03:**
- ✅ `open_interest.py`: EUR symbols → `None` in `FUTURES_SYMBOL_MAP` + `logger.debug` + `return None`
- ✅ `funding_rate.py`: idem
- ✅ `long_short_ratio.py`: idem
- ✅ Nessun WARNING 400 Bad Request su BTC-EUR, ETH-EUR, SOL-EUR ecc.
- ⚠️ **Bug scoperto 2026-07-09**: OKB-EUR non è nella mappa `FUTURES_SYMBOL_MAP` → tenta chiamata Binance Futures e fallisce con 400. Vedi TASK-1116.B.

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

### TASK-1116.D — DB migration: aggiungere mode='TEST' al CHECK constraint

**Status:** ✅ DONE — migration creata e committata (commit d5ef9c3)
**Priorità:** CRITICA
**Dipendenze:** TASK-1116

**Problema:** Sessione avviata con `mode='test'` (OKX Demo Trading) fallisce l'INSERT in `scalping_sessions` perché il CHECK constraint `scalping_sessions_mode_check` ammette solo `'PAPER', 'LIVE', 'BACKTEST'`.

**Log osservato:**
```
Failed to insert session in DB: {'code': '23514', 'message': "new row for relation 'scalping_sessions' violates check constraint 'scalping_sessions_mode_check'"}
```

**File coinvolti:**
- `synthtrade/supabase/migrations/20260709000000_task1116d_add_test_mode_check.sql` (nuovo)

**Fix:**
```sql
ALTER TABLE scalping_sessions DROP CONSTRAINT scalping_sessions_mode_check;
ALTER TABLE scalping_sessions ADD CONSTRAINT scalping_sessions_mode_check
  CHECK (mode IN ('PAPER', 'LIVE', 'BACKTEST', 'TEST'));
```

**Verifica:** Migration creata, da applicare a Supabase.

---

### TASK-1116.E — Fallback REST diretto per get_trade_fee() OKX

**Status:** ✅ DONE — fallback implementato (commit d5ef9c3)
**Priorità:** ALTA
**Dipendenze:** TASK-1103

**Problema:** `get_trade_fee()` fallisce con errore `50119 API key doesn't exist` su account EU OKX. La chiave è valida (il balance viene letto), ma ccxt routing interno punta a `www.okx.com` invece che a `eea.okx.com`.

**Log osservato:**
```
OKX get_trade_fee failed for OKB/EUR: okx {"msg":"API key doesn't exist","code":"50119"} — using fallback
Fee tier [okx]: maker=0.001, taker=0.001 certified=False
```

**File coinvolti:**
- `synthtrade/backend/app/execution/okx_exchange.py`

**Fix:**
- Aggiungere fallback REST diretto in `get_trade_fee()` analogo a quello esistente per `fetch_balance()`
- Endpoint: `GET /api/v5/account/trade-fee?instType=SPOT&instId={symbol}`

**Verifica:** Fee tier OKX Demo (rebate negativi) viene letto correttamente, `certified=True`.

---

### TASK-1116.C — Collector adapter provider-aware (OKX derivatives)

**Status:** Pending
**Priorità:** ALTA
**Dipendenze:** TASK-1116.B

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

### TASK-1116.F — Fix `mode_valid` sempre FAILED nel session health check

**Status:** Pending
**Priorità:** MEDIA — non blocca la sessione (resta `running`), ma inquina i log ogni ~30-90s e nasconde altri problemi reali nel rumore

**Dipendenze:** TASK-1116.D (ha introdotto `mode='TEST'` come valore valido a livello DB, ma non a livello di health check applicativo)

**Problema:** `session_health_job` in `app/scheduler/scalping_jobs.py` valida `mode` contro `("paper", "live")` senza includere `"test"`.

**File coinvolto:**
- `synthtrade/backend/app/scheduler/scalping_jobs.py` — linea 226

**Impatto:** Warning falso-positivo ogni ~60-90s, rumore log, rischio azioni indesiderate future.

**Fix:** Aggiornare `mode_valid` per accettare anche `"test"` (case-insensitive).

**Verifica:** Sessione `mode=test` mostra `mode_valid=True` nei log health check.

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

### TASK-1117 — Fix DB constraint `session_signal_log_decision_type_check`

**Status:** ✅ DONE — 2026-07-08
**Priorità:** MEDIA
**Dipendenze:** TASK-1100

**Problema:** nel log compare `decision_type='rejected_short_unsupported'`, valore non incluso nel CHECK constraint della tabella `session_signal_log` (che ammette solo `execute`, `block_conflict`, `mean_reversion_override`, `hold_existing_position`, `rejected_other`). Coerente con il gap noto sullo short selling (nessuna implementazione ancora), ma comporta la perdita silenziosa di questi log specifici.

**Obiettivo:** aggiungere `rejected_short_unsupported` (o valore equivalente) al CHECK constraint, oppure mappare esplicitamente su `rejected_other` nel writer finché lo short non è implementato.

**Completato 2026-07-08:**
- ✅ **1117.A — Audit writer**: `log_rejected_short_unsupported()` si trova in `app/core/signal_log_writer.py` (linee 197-222). Usa `decision_type="rejected_short_unsupported"` dentro `log_signal_decision()`. Il valore non era incluso nel CHECK constraint DB.
- ✅ **1117.B — Migration**: Creata `synthtrade/supabase/migrations/20260708000000_task1117_fix_decision_type_check.sql`. DROP + ADD del constraint con valori aggiuntivi: `rejected_short_unsupported`, `execution_error` (già usato da `log_execution_error` ma assente dal constraint).
- ✅ **1117.C — Verifica**: Log nei log della sessione paper 2026-07-08 mostrano 5 occorrenze di `error 23514` per `rejected_short_unsupported` — confermato che il problema era attivo. Con la migration applicata, questi insert non produrranno più violazioni.

**Nota:** La migration va applicata su Supabase tramite psql o Supabase MCP. Il backend in esecuzione usa `_DummyClient` (test/dev), non il client Supabase reale.

**File coinvolti:**
- `synthtrade/supabase/migrations/20260708000000_task1117_fix_decision_type_check.sql` — migration creata
- `synthtrade/backend/app/core/signal_log_writer.py` — writer già corretto (usa `rejected_short_unsupported`)

### TASK-1118 — Audit symbol normalization in frontend Angular

**Status:** ✅ DONE — 2026-07-08
**Priorità:** MEDIA
**Dipendenze:** TASK-1105

**Problema:** il mismatch simbolo `BTCEUR` (stato sessione) vs `BTC-EUR` (instId OKX) causava scarto silenzioso di ogni candela real-time nel `LiveChartComponent`. Lo stesso tipo di mismatch potrebbe presentarsi in altri componenti Angular che consumano il WS scalping.

**Obiettivo:** auditare tutti i componenti che confrontano simboli provenienti da fonti diverse (stato sessione vs eventi WS provider-specific) e applicare `_normalizeSymbol()` dove serve.

**Completato 2026-07-08:**
- ✅ **1118.A — grep confronti:** Trovati 3 componenti con confronto simbolo non normalizzato:
  - `live-chart.component.ts` — già fixato (usava `_normalizeSymbol()` privato)
  - `market-intel-panel.component.ts` (linea 200) — `data.symbol.toUpperCase() !== this.symbol.toUpperCase()` → scartava eventi `BTC-EUR` se la sessione riportava `BTCEUR`
  - `performance-panel.component.ts` — solo analisi quote asset (safe)
  - `session-controls.component.ts` — solo analisi quote asset (safe)
- ✅ **1118.B — Fix componenti:** `market-intel-panel.component.ts` fixato con `SymbolUtils.equals()`
- ✅ **1118.C — Refactor:** Creato `synthtrade/frontend/synthtrade-ui/src/app/scalping/utils/symbol-utils.ts` con `SymbolUtils.normalize()` e `SymbolUtils.equals()`. `live-chart.component.ts` refattorizzato per usare `SymbolUtils.equals()` invece del metodo privato.
- ✅ **1118.D — Verifica:** I componenti `trade-log/`, `position-ticker/` e `supervisor-log/` NON hanno confronti simbolo diretti — ricevono eventi WS già corretti dal backend. Il bug era limitato ai componenti che filtrano eventi per simbolo lato frontend.

**File creati/modificati:**
- `synthtrade/frontend/synthtrade-ui/src/app/scalping/utils/symbol-utils.ts` (NUOVO)
- `synthtrade/frontend/synthtrade-ui/src/app/scalping/components/live-chart.component.ts` — refactor a SymbolUtils
- `synthtrade/frontend/synthtrade-ui/src/app/scalping/components/market-intel-panel.component.ts` — fix confronto simbolo

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

**Status:** Pending
**Priorità:** ALTA

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

## Ordine di esecuzione consigliato

1. **TASK-1100** ✅ partial — spike OKX Demo Trading completato (A-F/H ✅, G workaround REST polling per WS privato bloccato).
2. **TASK-1101 -> TASK-1116** ✅ config, adapter REST, WS market data, order stream, router provider-neutral, DB migration, frontend exchange-neutral, backtest factory, integration tests, validazione e2e.
3. **TASK-1113** — Cutover OKX live readiness: rendere OKX provider primario e preparare go-live (prossimo passo critico).
4. **TASK-1114** — OKX fee tier e net pricing parity: preservare logica fee-aware su OKX.
5. **TASK-1117 -> TASK-1118** — Bug da recap 2026-07-08: constraint DB `rejected_short_unsupported` e audit frontend symbol normalization.
6. **TASK-907 / TASK-908** — bug non OKX (frontend paused reload, resume guard).

Le fasi successive dello short (`MarginBorrowManager`, `OrderExecutor` margin,
`ExecutionLoop` branch short, migration DB) restano come da
`SynthTrade_Short_Selling_Architecture.md` §11, Fasi 2-6, da spezzare in task
separati (TASK-910 in poi) quando si arriva a quel punto.

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

---

## Task Archiviati

Vedi `docs/ARCHIVE_TASKS.md`
