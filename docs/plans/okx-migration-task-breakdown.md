# SynthTrade — Breakdown Dettagliato Task Migrazione OKX

> Data: 2026-07-02  
> Architettura: `docs/architecture/okx-migration-architecture.md`  
> Piano macro: `docs/plans/okx-migration-implementation-plan.md`  
> Scope: dettaglio operativo TASK-1100 -> TASK-1116 per lavoro parallelo tra piu' agenti/modelli.

---

## Regole di Coordinamento

Questa epica e' grande e verra' probabilmente divisa tra agenti. Per evitare drift:

1. ogni agente deve leggere architettura, piano macro e questo breakdown prima di modificare codice;
2. ogni task deve aggiornare `docs/TASKS.md`, `docs/STORY.md`, `docs/HANDOFF.md` a fine lavoro;
3. ogni task deve lasciare note precise su payload osservati, decisioni prese e test eseguiti;
4. non usare piu' Binance come assunzione implicita in nuovo codice;
5. se un comportamento OKX non e' verificato in Demo Trading, marcarlo come `UNVERIFIED` e non portarlo nel path live;
6. mantenere compatibilita' con storico Binance finche' non esiste un task esplicito di rimozione;
7. non mischiare refactor cosmetici con migrazione OKX;
8. preferire fake adapter/fake stream nei test automatici, Demo Trading solo per validazione manuale controllata.

### Stati Consentiti

- `Pending`: non iniziato.
- `In Progress`: un agente lo sta lavorando.
- `Blocked`: manca credenziale, payload o decisione esterna.
- `Ready for Review`: codice/documentazione pronti, test eseguiti.
- `Done`: verificato e documentato.

### File di Verifica Obbligatori

Ogni task non banale deve aggiornare almeno uno tra:

- `docs/analysis/okx-demo-spike-results.md` per evidenze API/payload;
- `docs/HANDOFF.md` per stato operativo e decisioni;
- test unit/integration vicino al modulo cambiato.

---

## Mappa Dipendenze

```text
TASK-1100
  -> TASK-1101
      -> TASK-1102
          -> TASK-1103
              -> TASK-1104
              -> TASK-1114
              -> TASK-1115
          -> TASK-1105
              -> TASK-1106
              -> TASK-1116
          -> TASK-1107
              -> TASK-1108
              -> TASK-1109
              -> TASK-1111
                  -> TASK-1112
                      -> TASK-1113
```

Parallelizzabile dopo TASK-1102:

- adapter REST: TASK-1103/TASK-1114/TASK-1115;
- WebSocket market data: TASK-1105;
- order stream: TASK-1106;
- frontend: TASK-1109, ma solo dopo endpoint contract stabile;
- collector audit: TASK-1116, dopo modello market data deciso.

---

## TASK-1100 — OKX Demo Spike

**Status:** 🟡 Partial (75%) — E/F/H ✅, G bloccato (fix URL noto)
**Tipo:** Spike bloccante  
**Owner ideale:** agente con accesso credenziali/demo e capacita' API/debug  
**Non modificare:** router live, DB schema, frontend.

### Completato 2026-07-03

- ✅ 1100.A — Auth REST: fix URL `eea.okx.com` per EU accounts
- ✅ 1100.B — Server time OK
- ✅ 1100.C — Instrument discovery: 527 spot, 16 EUR live, BTC-EUR default
- ✅ 1100.D — Fee tier: maker -0.2%, taker -0.35% (rebate)
- ✅ 1100.E — Market order: 10€ → 0.00022883 BTC @ 43700€
- ✅ 1100.F — Exit bracket: algoId piazzato, metodo `order-algo` confermato, minSz ≥ 0.0001 BTC
- ✅ 1100.H — WS public trades: subscription OK, parser CVD verificato
- ❌ 1100.G — WS private: `60032 API key doesn't exist` — workaround: REST polling fallback (TASK-1100.G rimane bloccato per WS privato; i fix del 2026-07-08 riguardano market data pubblica → TASK-1105)

**Report:** `docs/analysis/okx-demo-spike-results.md` + `docs/analysis/okx-demo-spike-results.json`

### Obiettivo

Verificare empiricamente OKX Demo Trading prima di scrivere codice runtime. Questo task decide contratti concreti per adapter, bracket, WS e fee.

### Input Necessari

- API key OKX Demo Trading.
- Passphrase OKX.
- Permessi trade demo.
- Account mode OKX configurato manualmente.

### File da Creare

- `scripts/test_okx_demo.py`
- `docs/analysis/okx-demo-spike-results.md`

### Sottotask

1. **1100.A — Auth REST** ✅ DONE
   - Key/secret/passphrase verificati su entrambe le key (demo e live).
   - Causa radice blocco `50119`: account OKX EU (my.okx.com) richiede `https://eea.okx.com` come base URL, non `www.okx.com`.
   - Header `x-simulated-trading: 1` confermato necessario per Demo Trading.
   - `ccxt.okx().set_sandbox_mode(True)` non sufficiente da solo: base URL deve essere `eea.okx.com`.

2. **1100.B — Server time e timestamp** ✅ DONE
   - `GET /api/v5/public/time` risponde `code=0`.
   - Nessun drift rilevato.
   - Formato timestamp: ISO 8601 UTC con milliseconds, es. `2026-07-02T10:00:00.000Z`.

3. **1100.C — Instrument discovery** ✅ DONE
   - 527 strumenti spot, 16 coppie EUR live su `eea.okx.com`.
   - `OKB-EUR` non disponibile né in demo né live su EU: `51001`.
   - Default aggiornato a `BTC-EUR`; fallback: `ETH-EUR`, poi primo EUR live da endpoint.
   - `lotSz`, `minSz`, `tickSz`, `maxMktSz`, `maxMktAmt` disponibili via `GET /api/v5/public/instruments`.

4. **1100.D — Fee tier** ✅ DONE
   - `GET /api/v5/account/trade-fee?instType=SPOT&instId=BTC-EUR` risponde `code=0`.
   - maker: `-0.002` (-0.2% rebate), taker: `-0.0035` (-0.35% rebate) — OKX paga il maker.
   - Fee EUR-specific confermate nel campo `fiat[{ccy:EUR}]`.
   - Payload raw salvato in `docs/analysis/okx-demo-spike-results.json`.

5. **1100.E — Market order minimo**
   - Eseguire market buy minimo.
   - Confermare significato di `sz` e `tgtCcy`.
   - Documentare fill price, quantity, commissione e asset commissione.

6. **1100.F — Exit bracket**
   - Provare `attachAlgoOrds`.
   - Provare `order-algo` separato.
   - Decidere quale usare in `place_exit_bracket`.
   - Verificare failure mode: cosa succede se bracket non viene accettato.

7. **1100.G — WS fill**
   - Login WS private/business.
   - Sottoscrivere canale corretto per ordine normale e algo/bracket.
   - Documentare payload normalizzato per `_on_order_update`.

8. **1100.H — Public trades per CVD**
   - Sottoscrivere trades OKX.
   - Verificare campo lato taker.
   - Stabilire mapping verso `TradeEvent.is_buyer_maker` oppure nuovo campo provider-neutral.

### Acceptance Criteria

- `docs/analysis/okx-demo-spike-results.md` contiene payload reali per auth, instruments, fee, order, bracket, WS fill e trades.
- Esiste una raccomandazione chiara: `attachAlgoOrds` oppure `order-algo`.
- Esiste una tabella mapping payload OKX -> modelli SynthTrade.
- Nessun codice runtime live modificato.

### Rischi

- Demo Trading non supporta una funzione disponibile live.
- OKB-EUR live ma non demo.
- ccxt astrae male gli algo order OKX.

---

## TASK-1101 — Config Provider OKX

**Tipo:** Backend config  
**Owner ideale:** agente backend prudente, test-first.

### Obiettivo

Aggiungere configurazione provider-neutral e credenziali OKX senza rompere Binance legacy.

### File Coinvolti

- `synthtrade/backend/app/config.py`
- `synthtrade/backend/.env.example`
- `synthtrade/backend/tests/unit/test_scalping_settings.py` o nuovo `test_exchange_config.py`
- eventuali docs setup.

### Sottotask

1. **1101.A — Settings**
   - Aggiungere `EXCHANGE_PROVIDER`.
   - Aggiungere `OKX_API_KEY`, `OKX_SECRET_KEY`, `OKX_PASSPHRASE`.
   - Aggiungere equivalenti live.
   - Aggiungere `OKX_DEMO_TRADING`.

2. **1101.B — Computed fields generici**
   - `exchange_provider`
   - `exchange_api_key`
   - `exchange_secret_key`
   - `exchange_passphrase`
   - `exchange_demo`
   - `exchange_display_name`

3. **1101.C — Sicurezza live**
   - Mantenere `ALLOW_LIVE_MODE`.
   - Bloccare provider live se mancano credenziali.
   - Non loggare secret/passphrase.

4. **1101.D — Env example**
   - Documentare differenza demo/live.
   - Specificare che OKX passphrase e' obbligatoria.

5. **1101.E — Test**
   - Default provider.
   - Override env OKX.
   - Se `TRADING_MODE=live` e `ALLOW_LIVE_MODE=false`, comportamento sicuro.
   - Binance legacy continua a leggere vecchie key.

### Acceptance Criteria

- Test config verdi.
- Nessuna rottura import di `settings.binance_*`.
- `.env.example` contiene setup OKX chiaro.

---

## TASK-1102 — ExchangeProtocol v2 Provider-Neutral

**Tipo:** Refactor contrattuale  
**Owner ideale:** agente senior backend; impatto alto.

### Obiettivo

Separare l'interfaccia di dominio SynthTrade dai nomi Binance (`OCO`, `LOT_SIZE`, simboli compatti).

### File Coinvolti

- `synthtrade/backend/app/execution/exchange.py`
- possibile nuovo `synthtrade/backend/app/execution/exchange_models.py`
- test unitari exchange protocol.

### Sottotask

1. **1102.A — Modelli dominio**
   - `SymbolRef`
   - `SymbolRules`
   - `MarketOrderRequest`
   - `ClosePositionRequest`
   - `ExitBracketRequest`
   - `ExchangeOrder`
   - `ExitBracketOrder`
   - `FeeTier`

2. **1102.B — Protocollo**
   - Definire `ExchangeAdapterProtocol`.
   - Includere `place_exit_bracket`, non `place_oco_order`.
   - Includere `get_instruments` / `get_symbol_rules`.

3. **1102.C — Compat Binance**
   - Adattare `BinanceExchangeAdapter` senza cambiare comportamento.
   - `place_oco_order` puo' restare wrapper deprecato.
   - Non rompere test esistenti.

4. **1102.D — Errori comuni**
   - `ExchangeOrderError`
   - `ExitProtectionError`
   - `ExchangeAuthError`
   - `ExchangeNetworkError`
   - `UnsupportedInstrumentError`

5. **1102.E — Test**
   - Protocol con fake adapter.
   - Symbol mapping.
   - Wrapper Binance legacy.

### Acceptance Criteria

- Router puo' ancora usare Binance.
- Nuovi adapter possono implementare protocollo senza importare dettagli Binance.
- Test esistenti passano o sono aggiornati con motivazione.

---

## TASK-1103 — OkxExchangeAdapter REST Base ✅ DONE

File creato: `synthtrade/backend/app/execution/okx_exchange.py`

Implementa `ExchangeAdapterProtocol` con:
- `get_balance(asset)`, `get_holdings()`
- `get_ticker_price(symbol)` con cache 15s
- `get_symbol_rules(SymbolRef)` con cache 5min, mappa `lotSz/minSz/tickSz/maxMktSz/maxMktAmt`
- `get_trade_fee(SymbolRef)` — fee OKX sono rebate negativi (maker=-0.002, taker=-0.0035)
- `place_market_order(MarketOrderRequest)` — spot cash, supporta `tgtCcy=quote_ccy` per buy con importo quote
- `close_position(ClosePositionRequest)`
- `place_exit_bracket(ExitBracketRequest)` — algo order OKX, emergency close se fallisce, solleva `ExitProtectionError`
- `get_open_exit_orders(SymbolRef)`, `cancel_open_exit_orders(SymbolRef)`
- `from_settings()` classmethod — costruisce da `app.config.settings`

**TASK-1100.F (bracket spike) ancora pending**: `place_exit_bracket` usa approccio algo order standard ma va validato in Demo Trading prima del live.

## TASK-1104 — OKX Exit Bracket Server-Side

**Tipo:** Trading safety critical  
**Owner ideale:** agente backend esperto, preferibilmente dopo TASK-1100 completo.

### Obiettivo

Implementare TP/SL server-side OKX con garanzia: se la protezione fallisce, chiusura market immediata.

### File Coinvolti

- `OkxExchangeAdapter`
- `router.py` solo se necessario per integrazione
- test bracket.

### Sottotask

1. **1104.A — Decisione tecnica**
   - Applicare risultato TASK-1100: `attachAlgoOrds` o `order-algo`.
   - Documentare parametri nativi OKX usati.

2. **1104.B — Request model**
   - `ExitBracketRequest(symbol, side, quantity, tp_price, sl_price, entry_order_id, fee_model)`.

3. **1104.C — Price validation**
   - Long close sell: TP sopra last, SL sotto last.
   - Short close buy: TP sotto last, SL sopra last.
   - Arrotondamento a `tickSz`.

4. **1104.D — Place bracket**
   - Chiamata OKX.
   - Parsing ids: bracket/algo id, tp id, sl id se disponibili.
   - Raw payload in `exchange_raw`.

5. **1104.E — Emergency close**
   - Se entry eseguita ma bracket fallisce: market close.
   - Cancellare eventuali ordini parziali.
   - Sollevare `ExitProtectionError`.

6. **1104.F — Test**
   - Bracket success.
   - Bracket reject -> emergency close chiamato.
   - Arrotondamento prezzi.
   - Lato short preparato ma non abilitato nel runtime.

### Acceptance Criteria

- Impossibile salvare posizione open senza bracket confermato o close di emergenza.
- Log espliciti su failure.
- Test failure path obbligatori.

---

## TASK-1105 — OkxWSClient Market Data ✅ DONE

File creato: `synthtrade/backend/app/scalping/engine/okx_ws_client.py`

Implementa la stessa interfaccia di `BinanceWSClient` con:
- Connessione a `wss://wspap.okx.com` (demo) / `wss://ws.okx.com:8443` (live)
- Sottoscrizione canali `candle1m` su WS **business** e `trades` su WS **public**
- Parser `_parse_candle`: mappa row OKX `[ts, o, h, l, c, vol, ..., confirm]` → `CandleEvent` (confirm=1 → is_closed=True)
- Parser `_parse_trade`: mappa `side=buy` → `is_buyer_maker=False`, `side=sell` → `is_buyer_maker=True` (CVD corretto)
- Ping loop ogni 25s (OKX richiede ping entro 30s)
- Reconnect con backoff esponenziale
- `provider="okx"` su tutti gli eventi
- Normalizzazione simboli: `BTC/EUR` → `BTC-EUR` automatica
- Market data sempre su endpoint live, indipendentemente da `demo` trading execution

`CandleEvent`, `TradeEvent`, `ConnectionStatusEvent` spostati in `exchange_models.py` (condivisi).
`BinanceWSClient` aggiornato per importarli da lì (backward compat preservata).

**Fix 2026-07-08:**
- ✅ Rimosso `wsaws.okx.com` (DNS non risolvibile)
- ✅ Separato canale `candle1m` su WS business da `trades` su WS public (revisione API OKX)
- ✅ Rimosso branch EU-specific per WS pubblico
- ✅ Frontend: `_normalizeSymbol()` aggiunto per evitare silenzioso scarto candele real-time (`BTCEUR` vs `BTC-EUR`)

## TASK-1106 — OkxOrderEventStream ✅ DONE

File creato: `synthtrade/backend/app/execution/okx_order_event_stream.py`

Implementa la stessa interfaccia di `UserDataStreamManager` con:
- Login WS OKX con firma HMAC-SHA256 + base64
- Sottoscrizione canali `orders` (spot normali) e `algo-orders` (bracket TP/SL)
- `_normalize_order`: mappa stato `filled`/`cancelled` → dict contratto router
- `_normalize_algo_order`: mappa stato `effective`/`canceled` → dict con `bracket_id`, `order_list_id`, `leg` (take_profit/stop_loss/algo)
- Fee OKX negative (rebate) → `commission = abs(fee)` per compatibilità router
- Reconnect con `on_reconnect_sync` callback
- `from_settings()` classmethod
- **UNVERIFIED**: payload algo-orders da Demo Trading (TASK-1100.G pending)

`exchange_factory.py` aggiornato con:
- `get_adapter()` → OkxExchangeAdapter o BinanceExchangeAdapter
- `get_market_ws_client(symbols)` → OkxWSClient o BinanceWSClient
- `get_order_event_stream()` → OkxOrderEventStream o UserDataStreamManager

---

## TASK-1107 — Router Scalping Provider-Neutral

**Status:** ✅ Done — 2026-07-03
**Tipo:** Integrazione backend critica  
**Owner ideale:** agente senior backend con attenzione stato globale.

### Obiettivo

Rimuovere assunzioni Binance da start/stop/restore e wiring sessione.

### File Coinvolti

- `synthtrade/backend/app/scalping/router.py`
- factory exchange/ws/order stream.

### Completato

- ✅ Entry flow: `place_exit_bracket(ExitBracketRequest)` provider-neutral
- ✅ `_handle_bracket_failed`: `cancel_open_exit_orders` + `ClosePositionRequest`
- ✅ `_on_order_update`: usa `bracket_id` e campo `leg` (OKX direct, Binance fallback)
- ✅ `_live_close_position`: convertito a `cancel_open_exit_orders`, `get_holdings`, `get_symbol_rules`, `close_position(ClosePositionRequest)`
- ✅ Session start / DB / WS / order stream via factory
- ✅ Bug fix: `abs()` su fee OKX rebate per `_net_to_gross_pct`

### Sottotask

1. **1107.A — Builder functions**
   - `_build_exchange_adapter(mode)`
   - `_build_market_ws(symbols, mode)`
   - `_build_order_event_stream(mode)`

2. **1107.B — Start session**
   - Validare instrument.
   - Recuperare fee tier.
   - Salvare provider nello stato sessione.
   - Avviare WS provider corretto.

3. **1107.C — Entry flow**
   - Usare `place_market_order`.
   - Usare `place_exit_bracket`.
   - Salvare posizione solo dopo bracket confermato.

4. **1107.D — Stop session**
   - Cancel bracket/open exit orders.
   - Attendere conferma cancellazione.
   - Market close provider-neutral.

5. **1107.E — Restore**
   - Ricostruire adapter provider da DB.
   - Verificare open bracket.
   - Riconciliare chiusure avvenute offline.

6. **1107.F — API instruments**
   - Nuova route `/api/scalping/exchange/instruments`.
   - Rimuovere path hardcoded `/binance/exchange-info` dal nuovo frontend.

7. **1107.G — Test**
   - Fake adapter success.
   - Fake bracket failure.
   - Restore open.
   - Restore closed.
   - Stop race condition.

### Acceptance Criteria

- Router non importa direttamente `BinanceExchangeAdapter` nel nuovo path.
- Session load guard resta rispettato.
- Binance legacy ancora recuperabile se provider=binance.

---

## TASK-1108 — DB Migration Provider e Order IDs

**Status:** ✅ Done — 2026-07-03 (migration applicata a Supabase)
**Tipo:** Database/backend persistence  
**Owner ideale:** agente backend DB.

### Obiettivo

Tracciare provider, demo/live, order ids generici, raw payload e fee.

### File Coinvolti

- `synthtrade/supabase/migrations/20260703000000_task1108_okx_provider_columns.sql`

### Completato

- ✅ `scalping_sessions`: exchange_provider, exchange_account_mode, exchange_demo, fee_tier_*
- ✅ `scalping_trades`: exchange_provider, exchange_order_id, exchange_bracket_id, tp/sl order ids, exchange_raw
- ✅ Index su exchange_order_id e exchange_bracket_id
- ✅ Backfill: oco_order_list_id → exchange_bracket_id per storico Binance
- ✅ Router salva tutte le nuove colonne

### Sottotask

1. **1108.A — Audit schema attuale**
   - Verificare colonne esistenti in `scalping_sessions`, `scalping_trades`, `scalping_positions`.
   - Evitare duplicati.

2. **1108.B — Migration sessions**
   - `exchange_provider`
   - `exchange_account_mode`
   - `exchange_demo`
   - `fee_tier_certified`
   - `fee_tier_raw`

3. **1108.C — Migration trades/positions**
   - `exchange_provider`
   - `exchange_order_id`
   - `exchange_bracket_id`
   - `exchange_sl_order_id`
   - `exchange_tp_order_id`
   - `exchange_raw`
   - fee rates e commission assets.

4. **1108.D — Backward compatibility**
   - Default `binance` per storico.
   - Nessuna query esistente deve smettere di leggere trade vecchi.

5. **1108.E — Test/SQL verification**
   - Migration idempotente.
   - Query select su record vecchio e nuovo.

### Acceptance Criteria

- DB distingue Binance/OKX.
- Raw payload disponibile per debug.
- Storico trade non sparisce dalla UI.

---

## TASK-1109 — Frontend Exchange-Neutral

**Tipo:** Frontend Angular  
**Owner ideale:** agente frontend.

### Obiettivo

Rimuovere hardcoding Binance dalla UI e caricare strumenti OKX.

### File Coinvolti

- `synthtrade/frontend/synthtrade-ui/src/app/scalping/services/binance-symbols.service.ts`
- session controls/scalping dashboard component
- dashboard page/topbar
- modelli TS.

### Sottotask

1. **1109.A — Service rename**
   - `BinanceSymbolsService` -> `ExchangeSymbolsService`.
   - Endpoint `/api/scalping/exchange/instruments`.

2. **1109.B — Models**
   - `ExchangeInstrument`.
   - provider/mode/demo metadata.

3. **1109.C — Default symbol**
   - Preferire `OKB-EUR` se presente.
   - Fallback: primo EUR live.
   - Fallback ulteriore: primo spot live configurato.

4. **1109.D — Labels**
   - "Saldo Binance" -> provider-aware.
   - Badge `OKX DEMO`, `OKX LIVE`, legacy `BINANCE TEST/LIVE`.

5. **1109.E — Tests**
   - Service API.
   - Default selection.
   - Dashboard label.

### Acceptance Criteria

- Nessuna nuova UI mostra Binance quando provider OKX.
- Dropdown simboli mostra solo strumenti forniti dal backend.

---

## TASK-1110 — Market Data/Backtest Factory Cleanup

**Tipo:** Backend shared services  
**Owner ideale:** agente backend data.

### Obiettivo

Rimuovere `ccxt.binance()` diretto da market data, generator e backtest.

### File Coinvolti

- `synthtrade/backend/app/core/market_data.py`
- `synthtrade/backend/app/services/market_data_service.py`
- `synthtrade/backend/app/core/strategy_generator.py`
- `synthtrade/backend/app/core/backtester.py`
- tests market data/generator.

### Sottotask

1. **1110.A — Audit chiamate Binance**
   - Cercare `ccxt.binance`, `binance`, `data_source=binance`.

2. **1110.B — Provider factory**
   - Usare exchange factory provider-aware.
   - Separare market data pubblico da trading adapter se utile.

3. **1110.C — Cache key**
   - Includere `exchange_provider` in cache OHLCV se serve.

4. **1110.D — Data source**
   - `okx_1h_60d`, non `binance_...`.

5. **1110.E — Tests**
   - Cache non mischia provider.
   - Generator funziona con fake OKX OHLCV.

### Acceptance Criteria

- Nuove strategie/backtest non dipendono implicitamente da Binance.
- Dati Binance storici non contaminano OKX senza provider marker.

---

## TASK-1111 — Integration Tests con Fake OKX Adapter

**Status:** ✅ Done — 2026-07-03 (12/12 test PASS)
**Tipo:** Test/integration  
**Owner ideale:** agente QA/backend.

### Obiettivo

Provare il ciclo completo senza rete: start -> entry -> bracket -> fill -> close.

### File Coinvolti

- `synthtrade/backend/tests/integration/fake_okx_adapter.py` (nuovo)
- `synthtrade/backend/tests/integration/test_okx_integration.py` (nuovo)

### Scenari Obbligatori

1. **1111.A — Happy path**
   - Start session OKX demo.
   - Market entry ok.
   - Bracket ok.
   - Fill TP.
   - DB closed + WS event.

2. **1111.B — Bracket failure**
   - Entry ok.
   - Bracket reject.
   - Emergency close.
   - Nessuna posizione open salvata.

3. **1111.C — Stop session**
   - Posizione open.
   - Cancel bracket.
   - Market close.
   - DB closed reason `session_stop`.

4. **1111.D — Restore open**
   - DB posizione open.
   - Exchange open bracket.
   - UDS/order stream restart.

5. **1111.E — Restore closed**
   - DB open.
   - Exchange no open bracket, closed order presente.
   - DB reconciled.

6. **1111.F — Fee/net pricing**
   - Fee tier fake.
   - TP/SL lordo coerente con target netto.

### Acceptance Criteria

- Test automatici coprono i failure path monetariamente rischiosi.
- Nessuna chiamata rete nei test.

---

## TASK-1112 — Validazione Demo Trading End-to-End

**Tipo:** Manual/integration controlled  
**Owner ideale:** agente con credenziali demo e supervisione utente.

### Obiettivo

Eseguire una sessione scalping completa su OKX Demo Trading.

### Checklist

1. Config `.env` OKX demo.
2. Avvio backend.
3. Avvio frontend.
4. Dashboard mostra saldo OKX demo.
5. Dropdown simboli contiene `OKB-EUR` o fallback documentato.
6. Start session demo.
7. Warmup candle OKX.
8. Entry market minimo.
9. Exit bracket server-side.
10. Fill TP o SL indotto/manuale se possibile.
11. Trade log chiuso.
12. PnL con fee coerente.
13. Stop session pulito.
14. Restart app e restore/reconcile.

### Output

- `docs/analysis/okx-demo-e2e-report.md`
- screenshot/log opzionali in `.tmp/` non committati se grandi.
- aggiornamento HANDOFF.

### Acceptance Criteria

- Un ciclo completo documentato.
- Nessuna posizione demo lasciata aperta.
- Nessun ordine bracket orfano.

---

## TASK-1113 — Cutover OKX Live Readiness

**Tipo:** Release readiness  
**Owner ideale:** agente release/backend.

### Obiettivo

Preparare OKX come provider primario, senza eseguire live reale senza conferma manuale.

### Sottotask

1. **1113.A — Default config**
   - `.env.example` default `EXCHANGE_PROVIDER=okx`.
   - Binance legacy documentato.

2. **1113.B — Safety gates**
   - `ALLOW_LIVE_MODE=true` obbligatorio.
   - Conferma UI per live.
   - Trade value minimo consigliato.

3. **1113.C — Smoke tests**
   - Backend health.
   - Instruments.
   - Dashboard.
   - Start paper.
   - Start demo.

4. **1113.D — Runbook**
   - Setup API key OKX.
   - Demo checklist.
   - Live checklist.
   - Emergency stop.

5. **1113.E — Decisione go-live**
   - Chiedere conferma utente prima di trade live minimo.

### Acceptance Criteria

- OKX e' default operativo.
- Live non puo' partire accidentalmente.
- Runbook chiaro per agenti futuri.

---

## TASK-1114 — OKX Fee Tier e Net Pricing Parity

**Tipo:** Trading math / PnL correctness  
**Owner ideale:** agente backend numerico/test.

### Obiettivo

Preservare il comportamento fee-aware attuale: target TP/SL configurati sono netti, prezzi ordine sono lordi calcolati da fee.

### File Coinvolti

- `router.py`
- adapter OKX
- `position_manager.py`
- test pricing.

### Sottotask

1. **1114.A — Fee model**
   - `FeeTier(maker, taker, certified, raw, source)`.
   - Persistenza su sessione.

2. **1114.B — Quote-aware commission conversion**
   - Rimuovere assunzioni BNB->USDC nel path provider-neutral.
   - Con `OKB-EUR`, quote currency e' EUR.
   - Se commission asset diverso da quote, convertire via ticker provider.

3. **1114.C — Net to gross**
   - Riutilizzare `_net_to_gross_pct`.
   - Parametrizzare entry fee e exit fee in base al tipo ordine OKX.

4. **1114.D — Logs**
   - `[NET_PRICING] provider=okx symbol=... maker=... taker=... certified=...`

5. **1114.E — Position/trade updates**
   - Position update mostra target netti e prezzi reali.
   - Trade log salva fee reali/attese.

6. **1114.F — Tests**
   - TP netto +0.5%.
   - SL netto -0.3%.
   - Fee non certificata.
   - Commission asset diverso da quote.

### Acceptance Criteria

- PnL netto nei log e DB e' coerente con fee.
- Nessun fallback 0.001 silenzioso.

---

## TASK-1115 — Dashboard Balance Provider-Neutral

**Tipo:** Backend/frontend balance  
**Owner ideale:** agente full-stack o backend+frontend coordinati.

### Obiettivo

Sostituire `binance_balance.py` nel dashboard con servizio generico.

### File Coinvolti

- `synthtrade/backend/app/core/binance_balance.py`
- nuovo `exchange_balance.py`
- `api/dashboard.py`
- dashboard Angular.

### Sottotask

1. **1115.A — Service design**
   - `ExchangeBalanceService.get_total_balance(target_ccy="EUR")`.
   - Provider corrente da settings/factory.

2. **1115.B — OKX conversion**
   - Direct `{ASSET}/EUR`.
   - Via USDT/USDC/EUR.
   - Via BTC/EUR come fallback.

3. **1115.C — Binance legacy**
   - Conservare LD handling solo provider=binance.
   - Non applicare LD a OKX.

4. **1115.D — API payload**
   - `exchange_provider`.
   - `balance_eur`.
   - `balance_assets`.
   - `balance_breakdown`.
   - `balance_certified` o error metadata se fetch fallisce.

5. **1115.E — Frontend**
   - Label provider-aware.
   - Empty/error state se balance non disponibile.

6. **1115.F — Tests**
   - OKX holdings conversion.
   - Binance legacy still works.
   - Timeout returns real zero/error, no fake balance.

### Acceptance Criteria

- Dashboard non chiama piu' Binance quando provider=OKX.
- UI non dice "Saldo Binance" in modalita' OKX.

---

## TASK-1116 — Audit Collector Binance/Futures

**Tipo:** Intelligence/source audit  
**Owner ideale:** agente backend/data.

### Obiettivo

Assicurare che il SignalScoreEngine in sessione OKX non usi fonti Binance in modo implicito.

### File Coinvolti

- funding/open interest/long-short collectors.
- CVD calculator.
- opportunity Binance RSS.
- signal score engine.
- scheduler scalping jobs.

### Sottotask

1. **1116.A — Inventory**
   - Elencare ogni chiamata Binance/Futures.
   - Classificare: execution-critical, signal, opportunity, historical.

2. **1116.B — Policy**
   - `provider_bound`: deve usare OKX.
   - `external_market_signal`: puo' usare fonte esterna ma va dichiarata.
   - `disabled_for_okx`: non disponibile.

3. **1116.C — Funding rate**
   - Verificare equivalente OKX.
   - Se spot-only, disabilitare o usare derivatives matching.

4. **1116.D — Open interest**
   - OKX derivatives se simbolo esiste.
   - Altrimenti unavailable.

5. **1116.E — Long/short ratio**
   - Cercare equivalente OKX.
   - Se assente, ripesare score.

6. **1116.F — CVD**
   - Usare trade stream OKX.
   - Validare segno taker.

7. **1116.G — Opportunity poller**
   - Rinominare `BinanceRSSPoller` o sostituire con OKX announcements.
   - Se resta Binance announcements, marcarlo come external source, non exchange provider.

8. **1116.H — Score weighting**
   - Collector unavailable non deve contare come score zero se mancano dati.
   - Log coverage chiaro.

9. **1116.I — Tests**
   - Provider OKX con collector Binance disabilitati.
   - Reweighting.
   - CVD OKX payload.

### Acceptance Criteria

- Sessione OKX non chiama Binance per fonti provider-bound.
- SignalScoreEngine logga collector attivi/assenti e pesi effettivi.
- Nessun segnale viene falsato da collector unavailable.

---

## Checklist Finale Cross-Task

Prima di dichiarare completa l'epica OKX:

- [ ] TASK-1100 ha payload reali documentati.
- [ ] OKX config non logga segreti.
- [ ] Adapter OKX implementa protocollo.
- [ ] Exit bracket server-side verificato.
- [ ] Emergency close testato.
- [ ] Fee tier certificato o fallback esplicito.
- [ ] Net pricing coerente in log/UI/DB.
- [ ] Instruments caricati runtime.
- [ ] Default `OKB-EUR` validato o fallback documentato.
- [ ] Market WS alimenta candle buffer.
- [ ] CVD OKX segno corretto.
- [ ] Order event stream chiude trade.
- [ ] Restore riconcilia offline fills.
- [ ] Dashboard balance OKX.
- [ ] Collector Binance auditati.
- [ ] Frontend provider-neutral.
- [ ] Fake integration tests verdi.
- [ ] Demo E2E completata senza ordini orfani.
- [ ] Runbook live pronto.
