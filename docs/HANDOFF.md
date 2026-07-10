# Handoff Protocol — SynthTrade

## Ultimo Handoff

### Da: Antigravity -> prossima sessione

**Data:** 2026-07-10 10:41

**Contesto:** TASK-1125 - Fix NameError settings closure in _start_ws_broadcast

---

### FASE COMPLETATA: TASK-1125 - Fix NameError: cannot access free variable settings

**Problema:** Live trade falliva con NameError: cannot access free variable settings where it is not associated with a value in enclosing scope.

**Root cause:** Python closure scoping bug. _start_ws_broadcast() conteneva un import locale 'from app.config import settings' dentro if restore_mode: (riga ~2160). Python marcava settings come variabile locale per TUTTA la funzione e le sue inner function (inclusa _trade_processor). Quando restore_mode=False, l'import non eseguiva ma Python cercava settings come free variable -> NameError.

**Fix:** Rimosso from app.config import settings locale da riga 2160. settings e' gia' importato a livello modulo (riga 46) ed e' accessibile correttamente.

**Stato sistema:**
- Il primo errore del log (NameError) e' ora risolto
- Il secondo errore (51008 EUR balance insufficient) e' un problema REALE di fondi - non e' un bug del codice. L'account non ha abbastanza EUR nel wallet Spot OKX per il trade value configurato (20 EUR).
- Le warning CCXT 50119 sono attese e gestite correttamente con il fallback REST diretto (TASK-1123)

**Prossimi passi:**
- Ricaricare EUR nel wallet Spot OKX (non Earn/Funding) per il trade minimo di 20 EUR
- Riavviare la sessione live e verificare che il trade venga eseguito

---


---

## 🔄 Ultimo Handoff

### Da: Cline → prossima sessione

**Data:** 2026-07-10 09:59

**Contesto:** TASK-1124 — Direct REST fallback per place_exit_bracket + fix double emergency close

---

### ✅ FASE COMPLETATA: TASK-1121 — Fix Pylance NoneType in okx_exchange.py

**Problema:** Pylance segnala `Object of type "None" is not subscriptable` alla riga 90.

**Fix:**
- Aggiunto guard `self.client.urls is not None` prima di accedere a `self.client.urls["api"]`
- Sostituito `.get("api", {})` con `(self.client.urls.get("api") or {})` per gestire `None` values

### ✅ FASE COMPLETATA: TASK-1123 — CCXT create_order fallisce con 50119 su OKX EU, fallback REST diretto per market order

**Problema:** `place_market_order()` chiama `self.client.create_order()` via CCXT, che fallisce con errore `50119 API key doesn't exist` su OKX EU live accounts. Il balance (che usa REST diretto) funzionava già, ma gli ordini erano bloccati.

**Log osservato:**
```
ERROR: Live trade failed: OKX market order failed: okx {"msg":"API key doesn't exist","code":"50119"}
```

**Fix:**
- Aggiunto metodo `_direct_place_market_order()` che usa POST `/api/v5/trade/order` con firma HMAC-SHA256 diretta, bypassando CCXT
- Modificata `place_market_order()`: se CCXT fallisce con `50119` o `"API key doesn't exist"`, usa il fallback REST diretto
- Il fallback supporta sia quantità base che `tgtCcy=quote_ccy` per buy con importo in valuta quota

**File modificati:**
- `synthtrade/backend/app/execution/okx_exchange.py`

**Stato sistema:**
- ✅ Syntax check passato
- ✅ Logica speculare a `_direct_fetch_balance()` già funzionante in produzione
- ✅ Docs aggiornati (TASKS.md, STORY.md, HANDOFF.md)

### ✅ FASE COMPLETATA: TASK-1122 — Fix SymbolRef.from_any() missing

**Problema:** `OkxExchangeAdapter.get_symbol_filters()` chiama `SymbolRef.from_any(symbol)` ma il metodo non esiste.

**Log osservato:**
```
Live trade failed: OKX get_symbol_filters failed for OKB-EUR: type object 'SymbolRef' has no attribute 'from_any'
```

**Fix:**
- Aggiunto `SymbolRef.from_any(symbol: str) -> SymbolRef` in `exchange_models.py`
- Supporta tre formati: OKX (`BTC-EUR`), CCXT (`BTC/EUR`), Compact (`BTCEUR`)

**Stato sistema:**
- ✅ 3 symbol_ref test passano senza modifiche
- ✅ Syntax check su entrambi i file modificati: OK

**File modificati:**
- `synthtrade/backend/app/execution/okx_exchange.py` — TASK-1121
- `synthtrade/backend/app/execution/exchange_models.py` — TASK-1122

---

### ✅ FASE COMPLETATA: Fix Regressione Chart Live

**Problema risolto:**
- Live chart non visualizzava candele (vuota) sia quando si selezionava un simbolo sia quando si avviava una sessione
- L'endpoint `@router.get("/candles/{symbol}")` era erroneamente annidato dentro la funzione `get_trade_history` in `router.py`
- Questo causava errore 404 quando il frontend cercava di recuperare i dati delle candele via REST

**Soluzioni implementate:**

1. **router.py:**
    - Corretta indentazione dell'endpoint `/candles/{symbol}` (righe 2372-2397): spostato da dentro `get_trade_history` a livello di modulo
    - Python syntax check: OK
    - Endpoint REST ora restituisce correttamente i dati delle candele da HistoricalLoader

2. **Verifica funzionamento:**
    - `curl http://localhost:8008/api/scalping/candles/BTC-EUR?limit=5` → restituisce 5 candele corrette
    - Backend riavviato automaticamente con WatchFiles dopo il fix
    - Chart ora visualizza correttamente le candele storiche e gli aggiornamenti real-time

**File modificati:**
- `synthtrade/backend/app/scalping/router.py` (fix indentazione endpoint)

**Commit:**
- `42d95bd` - fix: correct indentation of /candles/{symbol} endpoint in router.py

**Stato sistema:**
- ✅ Endpoint REST `/api/scalping/candles/{symbol}` funzionante
- ✅ Chart visualizza correttamente le candele storiche
- ✅ Codice Python compila senza errori
- ✅ Backend avvia senza errori

---

---

## 🔄 Handoff Precedente

### Da: GitHub Copilot → prossima sessione

**Data:** 2026-07-09 09:45

**Contesto:** Bug collector OKB-EUR + task 1116.C per provider-aware collectors.

### ✅ FASE COMPLETATA: Bug OKB-EUR in FUTURES_SYMBOL_MAP + TASK-1116.C

**Problema risolto:**
- Sessione OKB-EUR (paper mode) tentava chiamate a Binance Futures per OpenInterest, FundingRate, LongShortRatio
- OKB-EUR non era nella mappa `FUTURES_SYMBOL_MAP` → 400 Bad Request
- I collector non sono provider-aware: ignorano `EXCHANGE_PROVIDER=okx`

**Soluzioni implementate:**

1. **FUTURES_SYMBOL_MAP (3 collector):**
   - Aggiunto `"OKBEUR": None, "OKB-EUR": None` a `open_interest.py`, `funding_rate.py`, `long_short_ratio.py`
   - OKX non ha futures perpetual per OKB-EUR → graceful skip corretto

2. **TASK-1116.C creato in TASKS.md:**
   - Refactor collector per accettare `adapter` opzionale
   - Implementare `CollectorAdapter` interface in `OkxExchangeAdapter`
   - SignalScoreEngine wiring per passare adapter ai collector
   - Test con fake adapter

**File modificati:**
- `synthtrade/backend/app/scalping/intelligence/collectors/open_interest.py`
- `synthtrade/backend/app/scalping/intelligence/collectors/funding_rate.py`
- `synthtrade/backend/app/scalping/intelligence/collectors/long_short_ratio.py`
- `docs/TASKS.md` (nuovo task 1116.C)

**Stato sistema:**
- ✅ OKB-EUR ora graceful skip nei collector (nessun 400)
- ✅ Router ora supporta `mode=test` (OKX Demo Trading) oltre a `mode=live`
- ✅ Frontend session-api.service.ts aggiornato con `mode: 'paper' | 'live' | 'test'`
- ⏳ TASK-1116.C pending: collector provider-aware (OKX derivatives o skip)

**Modifiche appena fatte:**
1. `router.py`: `control.get("mode") == "live"` → `in ("live", "test")` per costruire adapter anche in demo mode
2. `session.model.ts`: aggiunto `'test'` ai tipi `mode`
3. `session-api.service.ts`: aggiunto `'test'` al parametro `start()`
4. `session-controls.component.ts`: mappato `globalMode='test'` → `mode='test'` (prima era mappato a 'paper')
5. `session-controls.component.ts`: template mostra "DEMO" quando `session.mode === 'test'`
6. `okx_exchange.py`: aggiunto `_direct_fetch_trade_fee()` fallback REST diretto per `get_trade_fee()`
7. `20260709000000_task1116d_add_test_mode_check.sql`: migration per aggiungere `mode='TEST'` al CHECK constraint

**Stato sistema:**
- ✅ OKB-EUR ora graceful skip nei collector (nessun 400)
- ✅ Router supporta `mode=test` (OKX Demo Trading)
- ✅ Frontend supporta `mode='test'`
- ✅ TASK-1116.D completato: migration DB applicata (commit d5ef9c3)
- ✅ TASK-1116.E completato: fallback REST fee implementato
- ✅ TASK-1116.F completato: fix mode_valid health check (commit 14d5af2)
- ✅ TASK-1119 completato: get_symbol_filters e get_btc_macro_context (commit 9461f82)
- ✅ TASK-1120 completato: get_balance usa solo availBal (commit 16b26f2)

**Demo mode checklist (per test OKX Demo Trading):**
- ✅ `TRADING_MODE=test` in `.env` → OKX Demo Trading (non paper)
- ✅ `EXCHANGE_PROVIDER=okx` → usa OkxExchangeAdapter
- ✅ `OKX_API_KEY`, `OKX_SECRET_KEY`, `OKX_PASSPHRASE` valorizzati con credenziali demo
- ✅ `OKX_BASE_URL=https://eea.okx.com` (per account EU)
- ⚠️ `PAPER_TRADING=true` deve essere `false` per demo reale (altrimenti usa fake adapter)
- ⚠️ OKX Demo Trading non supporta WS private → order stream usa REST polling fallback

**Prossimo step:**
- ✅ Migration SQL applicata a Supabase (confermare)
- ✅ Backend riavviato con `PAPER_TRADING=false`
- ✅ Sessione avviata con `mode=test` dal frontend
- ✅ Verificare log senza warning `mode_valid` nei health check

---

### TASK-1116.G — Instrument discovery environment-aware (pending)

**Problema:** OKB-EUR non disponibile in Demo Trading (errore 51001), ma è nella dropdown e causa fallimenti silenziosi.

**File coinvolti:**
- `synthtrade/backend/app/execution/okx_exchange.py`
- `synthtrade/backend/app/scalping/router.py`
- `synthtrade/frontend/synthtrade-ui/src/app/scalping/services/exchange-symbols.service.ts`
- `synthtrade/frontend/synthtrade-ui/src/app/scalping/components/session-controls.component.ts`

**Sottotask:**
1. Discovery cache separata per demo/live
2. Endpoint `/api/scalping/exchange/instruments` filtra per ambiente
3. Validazione pre-avvio sessione con errore esplicito
4. Dropdown Angular filtrato dinamicamente al cambio modalità
5. Tooltip per simboli non disponibili in demo
6. Test unit + integration

---

### TASK-1119/1120 — Fix LIVE trading OKX (completato)

**Completato:**
- ✅ `get_symbol_filters()` aggiunto come wrapper su `get_symbol_rules()` (commit 6d3b52b)
- ✅ `get_btc_macro_context()` con fallback REST diretto per EU accounts (commit 6d3b52b)
- ✅ `get_balance()` usa solo `availBal` via REST diretto (commit 16b26f2)

**Verifica:** Sessione LIVE deve completare il ciclo senza AttributeError e con saldo corretto.

**Sottotask:**
1. Discovery cache separata per demo/live
2. Endpoint `/api/scalping/exchange/instruments` filtra per ambiente
3. Validazione pre-avvio sessione con errore esplicito
4. Dropdown Angular filtrato dinamicamente al cambio modalità
5. Tooltip per simboli non disponibili in demo
6. Test unit + integration

---

### Da: Kilo → prossima sessione

**Data:** 2026-07-09 08:24

**Contesto:** Sessione corrente — fix avvio backend + verifica balance OKX live mode.

---

### ✅ FASE COMPLETATA: Fix IndentationError + verifica OKX live balance

**Problema risolto:**
- Backend non partiva per `IndentationError` in `router.py:2400` (funzione `_stop_ws_broadcast()` con indentazione mista: 8 spazi invece di 4)
- Verificato funzionamento balance fetch in live mode OKX (errore 50119 precedente risolto)

**Soluzioni implementate:**

1. **router.py:**
    - Corretta indentazione di `_stop_ws_broadcast()` (riga 2400): body della funzione ora a 4 spazi invece di 8
    - Python syntax check: OK

2. **okx_exchange.py (verificato, non modificato):**
    - Confermata presenza del CCXT→REST fallback (`_direct_fetch_balance` → `/api/v5/account/balance`)
    - `OKX_BASE_URL` correttamente configurato per EEA (`https://eea.okx.com`)
    - Log di conferma: `OKX balance fetched: 29.28 EUR (2 assets)` in live mode senza errori 50119

**File modificati:**
- `synthtrade/backend/app/scalping/router.py` (fix indentazione)

**Commit:**
- (nessun commit — modifica minore indentazione)

**Stato sistema:**
- ✅ Backend avvia senza errori di sintassi
- ✅ Live mode balance fetch OK: `29.28 EUR` caricato correttamente
- ✅ Paper mode funzionante (sessione BTC-EUR completata con PnL -0.21%)
- ✅ 100 candele storiche caricate via HistoricalLoader
- ✅ Nessun errore 50119 in live mode

---

## 🔄 Handoff Precedente

### Da: Cline → prossima sessione

**Data:** 2026-07-08 14:53

**Contesto:** Sessione paper BTCEUR completa (2h53m, 6 trade, PnL -0.94) + TASK-1113 completato

---

### ✅ FASE COMPLETATA: TASK-1113 — Cutover OKX Live Readiness

**Completato:**
- ✅ **1113.A — Default config**: `.env.example` già OKX default, `TRADING_MODE=test`, Binance legacy documentato
- ✅ **1113.B — Safety gates**: `ALLOW_LIVE_MODE=false`, `SCALPING_FORCE_PAPER=true`, trade value minimo consigliato
- ✅ **1113.C — Smoke tests**: Health check OK (`{"status":"ok"}`), Instruments OKX caricati (16 EUR pairs), endpoint `/candles/btceur` funzionante
- ✅ **1113.D — Runbook**: Creato `docs/analysis/okx-live-runbook.md` con setup API key, safety gates, smoke test checklist, emergency stop procedure, go-live checklist e rischi
- ✅ **1113.E — Decisione go-live**: Documentata in runbook §7. Primo trade live minimo (20€) richiede conferma manuale esplicita

### 📊 Stato Epica OKX (aggiornato)

| Task | Stato |
|------|-------|
| TASK-1100 | Partial (G bloccato WS privato EU) |
| TASK-1101-1103 | ✅ DONE |
| TASK-1104 | Pending |
| TASK-1105-1112 | ✅ DONE |
| TASK-1113 | ✅ DONE |
| TASK-1114 | ✅ DONE |
| TASK-1115-1116 | ✅ DONE |
| **TASK-1117** | **✅ DONE (questo)** |
| TASK-1118 | Pending |

**Prossimo task consigliato:** TASK-1118 (audit symbol normalization frontend) o TASK-1104 (OKX Exit Bracket server-side)

---

### ✅ FASE COMPLETATA: TASK-1100.G Fix Grafico OKX

**Problema risolto:**
- Il grafico mostrava solo una linea piatta perché veniva broadcastata solo l'ultima candela storica
- Il REST poller (55s interval) era la fonte primaria invece di WS real-time
- Variabili non definite causavano errori in router.py e okx_ws_client.py
- Frontend usa HTTP per dati storici, non WebSocket (broadcast WS non necessario)

**Soluzioni implementate:**

1. **router.py (v1):**
   - Broadcast completo di tutte le 100 candele storiche durante preload al frontend
   - Corretto riferimento variabile `selected_balance` → `available_balance`

2. **okx_ws_client.py:**
   - Abilitata WS candle1m subscription come primary source
   - REST poller ora fallback intelligente che si disabilita automaticamente quando WS attivo
   - Tracking attività WS per switch automatico WS/REST
   - Aggiunta dichiarazione variabile `_check_counter` mancante

3. **router.py (v2):**
   - Rimosso broadcast WS non necessario (frontend usa HTTP /candles/{symbol})
   - HTTP /candles/{symbol} ora usa sempre HistoricalLoader come primary
   - Assicurato caricamento dati storici completi via HTTP

4. **historical_loader.py (v3):**
   - Rimosso header `x-simulated-trading` per usare sempre live market data
   - Demo network ha bassa liquidità con candele piatte → usare live network

5. **okx_ws_client.py (v3):**
   - Sempre usa live WS URLs per market data (non demo)
   - Demo mode ora solo per trading execution, non per market data

6. **okx_ws_client.py (v4):**
   - Aggiunto URL WS backup per problemi DNS (wspap.okx.com come fallback)
   - Fallback automatico a backup URL quando primary fallisce con DNS error
   - REST poller rimane come fallback finale
   - Ridotto warning spam di connessione

**File modificati:**
- `synthtrade/backend/app/scalping/router.py`
- `synthtrade/backend/app/scalping/engine/okx_ws_client.py`

**Commit:**
- `c7e1840` - fix: OKX chart display - broadcast full historical candles and enable WS candle subscription
- `514630a` - fix: OKX chart display - remove unnecessary WS broadcast and ensure HTTP endpoint always loads historical candles
- `327724a` - fix: Use live OKX market data instead of demo network for better liquidity
- `86de737` - fix: Add WS fallback URLs for OKX to handle DNS connectivity issues

**Stato sistema:**
- ✅ Codice Python compila senza errori
- ✅ WS candle1m subscription configurata come primary per aggiornamenti real-time
- ✅ REST poller fallback intelligente implementato
- ✅ HTTP /candles/{symbol} usa sempre HistoricalLoader per dati storici
- ✅ Variabili non definite corrette
- ✅ Frontend riceve dati storici via HTTP e aggiornamenti via WS
- ✅ Market data da live network OKX (non demo) → liquidità normale

**Prossimi step raccomandati:**
- Testare il grafico con i nuovi dati OKX completi
- Verificare che gli aggiornamenti real-time funzionino correttamente
- Procedere con TASK-1101 (config OKX) e TASK-1102 (ExchangeProtocol v2)

---

## 🔄 Handoff Precedente

### Da: Kiro → prossima sessione

**Data:** 2026-07-03 16:06

**Contesto:** TASK-1112 paper mode completato — sessione BTC-EUR paper su OKX Demo stabile e pulita.

---

### ✅ FASE COMPLETATA: TASK-1112 Validazione Demo (paper mode)

**Commit sessione odierna:**

| Hash | Contenuto |
|------|-----------|
| `71e4562` | TASK-1110 HistoricalLoader OKX + TASK-1116 EUR collector graceful skip |
| `52ac12d` | Fix PnL 54000% paper session_stop |
| `67f414f` | Fix NoneType ccxt URL + lookup trade robusto Strategy 2a |
| `09defc1` | Docs |
| `66fed39` | OkxWSClient `_normalize_okx_symbol` (BNBUSDC→BNB-USDC) |
| `8fbcba6` | Remove `set_sandbox_mode` dopo EU URL override (NoneType crash) |
| `53f225f` | Rewrite `_load_from_okx` con httpx diretto — zero ccxt fragility |
| `8efdc21` | Mock generator mancava `_save_open_position_to_db` — "No open row found" |
| `df586ef` | Log strings provider-neutral |

**Stato sistema verificato dai log:**
- ✅ `HistoricalLoader: loaded 100 candles from OKX for BTC-EUR (1m)`
- ✅ `OKX WS connected: wss://wspap.okx.com/ws/v5/public?brokerId=9999`
- ✅ `demo=True` con `TRADING_MODE=test`
- ✅ Nessun "No open row found"
- ✅ Nessun errore 400 Binance Futures per EUR symbols
- ✅ Session save/stop/trade DB corretti
- ✅ 12/12 integration tests pass

---

### ⏳ PROSSIMI TASK

**TASK-1100.G** — WS private EU fix (PRIORITÀ CRITICA per live/demo reale):
- URL: `wss://wsaws.okx.com:8443/ws/v5/private`
- Serve per ricevere fill bracket (TP/SL hit) in sessione live
- File: `synthtrade/backend/app/execution/okx_order_event_stream.py`

**TASK-1113** — Cutover OKX live readiness:
- Prerequisito: TASK-1100.G per fill events
- Checklist go-live, test live minimo con conferma manuale

**TASK-1109** — Frontend label "Saldo Binance" → provider-neutral

**TASK-1115** — Dashboard balance OKX

---

### ✅ FASE COMPLETATA: TASK-1110 + TASK-1116 + Bug fixes

**Commit pushati:**

| Hash | Contenuto |
|------|-----------|
| `71e4562` | TASK-1110 HistoricalLoader OKX + TASK-1116 EUR collector graceful skip + watchdog log |
| `52ac12d` | Fix paper mode session_stop usa entry_price non prezzo OKX reale (bug 54000% PnL) |
| `67f414f` | Fix NoneType ccxt URL override + lookup trade chiusura robusto (session+price senza entry_time string eq) |

**Bug fixati:**

1. **NoneType crash in `_load_from_okx`** — `exchange.urls["api"]` ha valori `None`; fix: `if v else v` nel dict comprehension. Stesso fix in `okx_exchange.py`.

2. **PnL 54016% su session_stop paper** — `close_price` usava `candle_buffer.latest.close` (prezzo reale OKX ~54000€) per posizioni mock aperte a ~100€. Fix: in paper mode usa `pos.entry_price` salvo che il prezzo del buffer sia entro 9x.

3. **"No open row found for close"** — Strategy 2 lookup usava `.eq("entry_time", entry_time_str)` — Supabase normalizza `timestamptz` diversamente dall'ISO string Python. Fix: Strategy 2a usa solo `session_id + entry_price + status`; Strategy 2b usa range `±2s`.

**Stato sistema:**
- ✅ OKX Demo WS connesso (`wspap.okx.com`) con `TRADING_MODE=test`
- ✅ HistoricalLoader carica 100 candele OKX reali per BTC-EUR
- ✅ Nessun errore 400 Binance Futures per EUR symbols
- ✅ 12/12 integration tests pass

---

### ⏳ PROSSIMI TASK

**TASK-1112** — Validazione Demo Trading end-to-end (PRIORITÀ CRITICA):
- Eseguire sessione live=False, mode=test su OKX Demo
- Verificare entry → bracket → fill → DB closed con ordini reali demo
- Prerequisito: `TRADING_MODE=test` nel `.env`, `EXCHANGE_PROVIDER=okx`
- WS private: `wss://wsaws.okx.com:8443/ws/v5/private` (TASK-1100.G)

**TASK-1109** — Frontend label "Saldo Binance" → provider-neutral

**TASK-1115** — Dashboard balance OKX

3. **Bug fix in router.py:** fee OKX negative (`-0.0035`) ora wrapped con `abs()` prima di `_net_to_gross_pct` — senza fix i prezzi bracket TP/SL erano invertiti

**File modificati:**
- `synthtrade/backend/tests/integration/fake_okx_adapter.py` (nuovo)
- `synthtrade/backend/tests/integration/test_okx_integration.py` (nuovo)
- `synthtrade/backend/app/scalping/router.py` (bug fix fee abs)

**Prossimo step:**
- **TASK-1112** — Demo E2E validation su OKX Demo Trading (manuale con credenziali reali)
- Oppure se vuoi test più sicuro prima: verifica che i test esistenti non siano rotti

---

### Da: Kiro → prossima sessione

**Data:** 2026-07-03 11:15

**Contesto:** TASK-1107 Router provider-neutral completato al 95%.

---

### ✅ FASE COMPLETATA: TASK-1107 Entry Flow Provider-Neutral

**Cosa è stato fatto:**

1. **Entry flow** — sostituito `place_oco_order` con `place_exit_bracket(ExitBracketRequest)`:
   ```python
   bracket_req = ExitBracketRequest(symbol=sym_ref, side="sell", quantity=exec_qty,
       tp_price=tp_price, sl_price=sl_price, entry_order_id=..., fee_tier=...)
   bracket_res = await exchange.place_exit_bracket(bracket_req)
   ```
   
2. **Bracket failure handler** `_handle_bracket_failed` — rimpiazza `_handle_oco_failed`:
   - Usa `exchange.cancel_open_exit_orders(sym_ref)` provider-neutral
   - Usa `exchange.get_holdings()` + `exchange.close_position(ClosePositionRequest)` 
   - Nessuna dipendenza da `_get_available_base_balance` (Binance-only)

3. **`_on_order_update`** — aggiornato per provider-neutral:
   - Legge `bracket_id` (OKX) + `order_list_id` (Binance) con OR
   - Legge `leg` field (`take_profit`/`stop_loss`) da OKX algo-orders
   - Fallback su `tp_order_id`/`sl_order_id` matching per Binance

4. **Verifica sintassi** — tutti i file compilano senza errori

**Pending (non bloccante):**
- `_live_close_position` ancora Binance-specific (cancella OCO via `client.cancel_order` diretto)
  - Non blocca OKX: questa funzione è chiamata solo su chiusura manuale via segnale
  - TODO marcato nel codice

**File modificati:**
- `synthtrade/backend/app/scalping/router.py`

**Prossimo step:**
1. **TASK-1111** — Integration tests con fake adapter (verifica entry → bracket → fill → close)
2. **TASK-1112** — Demo E2E validation su OKX Demo Trading

---

### Da: Kiro → prossima sessione

**Data:** 2026-07-03 10:45

**Contesto:** TASK-1100 OKX Demo Spike — audit file modificati e completamento test mancanti E/F/H.

---

### ✅ FASE COMPLETATA: TASK-1100 Sottotask E/F/H

**Cosa è stato fatto:**

1. **Audit file OKX già implementati:**
   - `okx_exchange.py` — adapter completo, `place_exit_bracket` pronto
   - `okx_ws_client.py` — market data WS completo, CVD mapping corretto
   - `okx_order_event_stream.py` — order stream WS implementato
   - `exchange_models.py` — protocolli e modelli domain pronti
   - `exchange_factory.py` — routing provider OKX/Binance pronto
   - `config.py` — computed fields exchange-neutral già presenti

2. **Eseguiti test Demo Trading OKX:**
   - **1100.E** ✅ Market order 10€ → 0.00022883 BTC @ 43700€, fee rebate -0.0000008 BTC
   - **1100.F** ✅ Exit bracket piazzato: algoId `3709954518432436224`, TP +0.5%, SL -0.3%
   - **1100.H** ✅ WS public trades subscription OK, parser verificato (zero trade = mercato demo inattivo normale)

3. **Decisioni chiave:**
   - Exit bracket OKX: usare `/api/v5/trade/order-algo` standard (non `attachAlgoOrds`)
   - minSz bracket: qty ≥ 0.0001 BTC (~4€+)
   - CVD mapping OKX: `side=sell` → `is_buyer_maker=True`

**File modificati:**
- `scripts/test_okx_demo.py` — fix WS demo URL
- `docs/analysis/okx-demo-spike-results.json` — payload test aggiornati

**Blocco rimanente:**
- **1100.G** — WS private auth fallisce (`60032 API key doesn't exist`), stesso problema URL EU già risolto su REST
- Fix proposto: `wss://wsaws.okx.com:8443/ws/v5/private` per EU accounts

**Prossimo step:**
- **Opzione A (raccomandata):** procedere TASK-1101+ (config, protocol, integration), validare WS private in TASK-1112 (Demo E2E)
- **Opzione B:** fix 1100.G ora modificando `OkxOrderEventStream` per URL EU

---

### Da: Cline → prossima sessione

**Data:** 2026-07-03

**Contesto:** Fix Pylance type error in `test_task_015.py` — `test_settings_validation()` passing `"not-a-number"` to `float` field `AI_CASCADE_TIMEOUT`.

---

### ✅ FASE COMPLETATA: Fix Pylance type error in TASK-015 test

**Cosa è stato fatto:**

1. **Diagnosi:** In `loom/tests/test_task_015.py`, `test_settings_validation()` passa `"not-a-number"` a `Settings(AI_CASCADE_TIMEOUT=...)`. Pylance segnala errore perché il campo `AI_CASCADE_TIMEOUT` è tipizzato come `float` in `config.py` (linea 202). Il test è intenzionale: verifica che Pydantic sollevi `ValidationError` per input invalido a runtime.

2. **Fix:** Aggiunto `# type: ignore[arg-type]` sulla riga incriminata, analogamente a `# type: ignore[call-arg]` già presente sulla riga 18.

3. **Verifica:** `python -m pytest loom/tests/test_task_015.py -v` → 6/6 PASS.

**File modificati:**
- `loom/tests/test_task_015.py` — aggiunto type ignore
- `docs/STORY.md` — aggiunta v1.4.1

**Prossimo step:** Nessuno per questo task. TASK-015 già in ARCHIVE_TASKS.md.

### Da: Codex → prossima sessione

**Data:** 2026-07-02

**Contesto:** Pianificazione migrazione urgente Binance -> OKX per blocco trading Binance in Italia.

---

### ✅ FASE COMPLETATA: Architettura definitiva OKX + piano task

**Cosa e' stato fatto:**

1. **Creata architettura definitiva**
   - File: `docs/architecture/okx-migration-architecture.md`
   - Decisione: introdurre exchange provider pluggable, non porting 1:1 Binance.
   - Scope: config, adapter REST, market WS, order event stream, router, DB, frontend.

2. **Creato piano implementazione**
   - File: `docs/plans/okx-migration-implementation-plan.md`
   - Fasi: spike demo, config/factory, protocollo exchange, adapter OKX, WS, order stream, router, DB, frontend, cutover.

2b. **Creato breakdown dettagliato multi-agente**
   - File: `docs/plans/okx-migration-task-breakdown.md`
   - Contiene subtasks TASK-1100.A..1116.I, file coinvolti, test, acceptance criteria, rischi e checklist finale.

3. **Aggiornati task loom**
   - Aggiunta EPICA OKX in `docs/TASKS.md`.
   - Creati TASK-1100 -> TASK-1116.
   - Primo task obbligatorio: TASK-1100 spike OKX Demo Trading.
   - TASK-1000 WalletOrchestrator Binance marcato come superseded/sospeso.

4. **Aggiornati indici**
   - `docs/BACKLOG.md`: link corretti a architettura e piano OKX.
   - `docs/STORY.md`: aggiunta milestone v1.4.0.
   - `docs/CHANGELOG.md`: aggiunta entry documentale.

**Decisioni chiave:**
- OKX diventa provider operativo primario.
- Binance resta legacy solo temporaneamente.
- Non implementare lo short/margin prima del cutover OKX long-only.
- Non toccare runtime live prima dello spike OKX Demo Trading.
- Fee/net pricing e' requisito bloccante: recupero fee tier a inizio sessione, `fee_tier_certified`, TP/SL netti e PnL/log coerenti.
- Symbol discovery obbligatoria: default `OKB-EUR`, ma validato dalla lista strumenti OKX all'avvio.
- Dashboard balance e collector intelligence vanno migrati/auditati: oggi esistono chiamate Binance fuori dall'ordine execution.
- Per assegnare lavoro a piu' agenti, usare `docs/plans/okx-migration-task-breakdown.md` come contratto operativo.

**Prossimo step consigliato:**
1. TASK-1100 — risolvere blocco private auth OKX Demo (`50119 API key doesn't exist`).
2. Key UI verificata su OKX Trading demo; IP whitelist verificato da terminale (`77.32.127.105`). Seconda key demo rigenerata e caricata correttamente dal codice, ma OKX risponde ancora `50119`; anche `ccxt.fetch_balance()` con header demo conferma lo stesso errore. Provata anche key live separata `OKX_LIVE_*` su balance read-only senza header demo: stesso `50119`.
3. Dopo auth OK, rieseguire `python scripts/test_okx_demo.py`, poi ordine demo minimo solo con flag esplicito.
4. Solo dopo TASK-1100, partire con TASK-1101 e TASK-1102.

---

### Da: Cline → prossima sessione

**Data:** 2026-07-01

**Contesto:** Sincronizzazione regole loom su tutti i config IDE + pulizia docs/ da file .py.

---

### ✅ FASE COMPLETATA: docs/ cleanup — rimossi file task ridondanti (2026-07-01)

**Cosa è stato fatto:**

1. **Analizzati tutti i 36 file in `docs/`** e categorizzati:
   - 8 file di task ridondanti → eliminati (contenuto già in TASKS.md o ARCHIVE_TASKS.md)
   - 1 duplicato → eliminato (SynthTrade_Short_Selling_Architecture_1.md)
   - 28 file di documentazione legittima → mantenuti

2. **Criterio di eliminazione:**
   - Task completati (TASK-813, TASK-905, TASK-912) → già in TASKS.md o ARCHIVE_TASKS.md → elimina file standalone
   - Task pending (TASK-907) → già in TASKS.md → elimina file standalone
   - Duplicati → elimina la copia più vecchia

3. **File eliminati (x8):**
   - `TASK_813_ALL_ACTIONS_STATUS.md` — TASK-813 già in ARCHIVE_TASKS.md
   - `TASK_813_COMPLETE_ANALYSIS.md` — TASK-813 già in ARCHIVE_TASKS.md
   - `TASK_813_FINAL_SUMMARY.md` — TASK-813 già in ARCHIVE_TASKS.md
   - `TASK_813_IMPLEMENTATION_COMPLETE.md` — TASK-813 già in ARCHIVE_TASKS.md
   - `TASK_TP_SL_NET_PRICING.md` — TASK-905 ✅ già dettagliato in TASKS.md
   - `TASK-907_bug_frontend_paused_reload.md` — TASK-907 Pending già in TASKS.md
   - `SynthTrade_TASK_Fix_Signal_Log_Decision_Types.md` — TASK-912 ✅ già in TASKS.md
   - `SynthTrade_Short_Selling_Architecture_1.md` — duplicato

4. **docs/ ora contiene 28 file .md** categorizzati:
   - Documentazione standard loom (7): ARCHIVE_TASKS, BACKLOG, CHANGELOG, HANDOFF, STORY, TASKS, TDD_LOG
   - Architettura/reference (8): OCO_FLOW, OKX_API_Reference, Piano_Implementazione_supervisor, SynthTrade_MASTER_RECAP, SynthTrade_Scalping_DataFlow_Reference, SynthTrade_ScalpingModule_Plan, SynthTrade_Short_Selling_Architecture, synthtrade-considerazioni-roadmap
   - Recap sessioni (9): RECAP_EPICA_MEMORY_LEARNING, SynthTrade_Piano_Logging_Decisionale_Livello1, SynthTrade_Recap_Errori_Notturni_29-30Giugno2026, SynthTrade_Recap_Sessione_Debug_22-23Giugno2026, SynthTrade_Recap_Sessione_Mean-Reversion-Bug_Short-Selling_25Giugno2026, SynthTrade_Recap_Sessione_Review_Memory_Learning_01Luglio2026, SynthTrade_Recap_Sessione_Strategie_Scalping, SynthTrade_Recap_Sessione_Trailing_Stop_Loss_Strategy_26Giugno2026, synthtrade-recap-sessione-risk-controls-audit
   - Fix/summary (4): BUG_FIX_SUMMARY, PERSISTENCE_FIX, PERSISTENCE_SUMMARY, STOP_WITH_OPEN_POSITION_ANALYSIS

**File modificati:**
- `docs/STORY.md` — aggiunta v1.3.9
- `docs/TASKS.md` — aggiunto TASK-DOCS-CLEANUP
- `docs/HANDOFF.md` — aggiornato

**Verifica:** `dir docs\*.md` → 28 file, nessun .py, nessun file di task standalone

---

### ✅ FASE COMPLETATA: Loom rules sync + docs/ cleanup (2026-07-01)

**Cosa è stato fatto:**

1. **Spostati script Python da `docs/` a `loom/scripts/`**:
   - `extract_tasks.py` e `parse_tasks.py` spostati nella posizione corretta secondo il framework loom
   - Aggiunto path resolution (SCRIPT_DIR → PROJECT_ROOT) per funzionare da `loom/scripts/`

2. **Rimosso `capital_allocator.py` da `docs/`**:
   - Era una vecchia versione duplicata (l'originale è in `synthtrade/backend/app/execution/capital_allocator.py`)

3. **Aggiornati tutti i config IDE** con regole loom complete:
   - `.clinerules/loom.md` — aggiunti comandi update/plugins/parse/extract + doc update section
   - `.cursorrules` — aggiunti parse/extract + doc update section
   - `.windsurfrules` — aggiunti parse/extract + doc update section
   - `CLAUDE.md` — aggiunti parse/extract + doc update section
   - `.cursor/rules/loom.mdc` — aggiunti parse/extract + doc update section
   - `AGENTS.md` — aggiunti parse/extract

4. **Aggiunta sezione "Documentation Update — MANDATORY"** a tutti i config IDE (obbligo di aggiornare TASKS.md, STORY.md, HANDOFF.md alla fine di ogni sessione)

5. **Verificato che `docs/` contenga solo file `.md`**

**File modificati:**
- `.clinerules/loom.md` — riscritto con tutti i comandi + doc update sezione
- `.cursorrules` — aggiunti parse/extract + doc update
- `.windsurfrules` — aggiunti parse/extract + doc update
- `CLAUDE.md` — aggiunti parse/extract + doc update
- `.cursor/rules/loom.mdc` — aggiunti parse/extract + doc update
- `AGENTS.md` — aggiunti parse/extract
- `loom/scripts/extract_tasks.py` — copiato da docs/ con path resolution
- `loom/scripts/parse_tasks.py` — copiato da docs/ con path resolution
- `docs/STORY.md` — aggiunta v1.3.8
- `docs/TASKS.md` — aggiunto TASK-LOOM-CONFIG
- Rimossi da `docs/`: `capital_allocator.py`, `extract_tasks.py`, `parse_tasks.py`

**Verifica:** `dir docs\*.py` → "File non trovato" (nessun .py in docs/)

---

### ✅ FASE COMPLETATA: Riorganizzazione docs/ — ridenominazione, backlog, stato moduli (2026-07-01)

**Cosa è stato fatto:**

1. **Eliminati 4 file ridondanti** (contenuto già in STORY.md):
   - `BUG_FIX_SUMMARY.md`, `PERSISTENCE_FIX.md`, `PERSISTENCE_SUMMARY.md`, `STOP_WITH_OPEN_POSITION_ANALYSIS.md`

2. **Rinominati 15 file** con formato data/topic per identificazione immediata:
   - 9 recap sessioni: `2026-06-20_risk-controls-audit.md`, `2026-06-22_debug-analisi.md`, `2026-06-25_mean-reversion-short.md`, `2026-06-26_trailing-stop-loss.md`, `2026-06-27_strategie-scalping.md`, `2026-06-29_errori-notturni.md`, `2026-06-29_logging-decisionale.md`, `2026-07-01_epica-memory-learning.md`, `2026-07-01_review-memory-learning.md`
   - 6 architettura: `oco-flow-spec.md`, `scalping-dataflow-reference.md`, `scalping-module-plan.md`, `short-selling-architecture.md`, `supervisor-implementation-plan.md`, `roadmap-considerazioni.md`, `okx-api-reference.md`

3. **Aggiunti 20 task investigativi** in TASKS.md (TASK-INVEST-001 → 020) da MASTER_RECAP.md, con status 🔍 "Da Investigare" — non assumiamo siano ancora aperti, ma non li perdiamo.

4. **BACKLOG.md riscritto** come indice strutturato con link ai file di dettaglio:
   - Piani di sviluppo (Short Selling, Trailing Stop Loss, Market Structure, Wallet Orchestrator, Supervisor)
   - Bug da investigare (cross-link a TASKS.md)
   - Reference architetturale (tabella con tutti i documenti)
   - Idee da esplorare ed esperimenti

5. **STORY.md arricchita** con sezione "Stato dei Moduli Architetturali" (tabella 12 moduli con stato 🟢🟡🔴) e link ai bug investigativi.

**File modificati:**
- `docs/BACKLOG.md` — riscritto come indice strutturato
- `docs/STORY.md` — aggiunta sezione stato moduli + v1.3.9
- `docs/TASKS.md` — aggiunti 20 task investigativi
- `docs/HANDOFF.md` — aggiornato
- Eliminati: `BUG_FIX_SUMMARY.md`, `PERSISTENCE_FIX.md`, `PERSISTENCE_SUMMARY.md`, `STOP_WITH_OPEN_POSITION_ANALYSIS.md`
- Rinominati: 15 file recap/architettura

---

### ✅ FASE COMPLETATA: Riorganizzazione recap per argomento (2026-07-02)

**Cosa è stato fatto:**

1. **Creata directory `docs/recap/`** — spostati 10 file:
   - 9 recap sessioni rinominati (formato `YYYY-MM-DD_topic.md`)
   - `MASTER_RECAP.md` (consolidamento generale)

2. **Eliminato `2026-06-27_strategie-scalping.md`** (28 righe ultra-sintetiche, contenuto già in MASTER_RECAP §2.7)

3. **Creati 5 file di analisi tematica** che consolidano informazioni sparse in più recap:

   | File | Tema | Fonti |
   |------|------|-------|
   | `docs/regime-detection-analysis.md` | Regime misclassification, Falling Knife, MarketStructureCollector | 4 recap |
   | `docs/short-selling-roadmap.md` | Short selling, dettagli tecnici Binance Margin, decisioni aperte | 3 recap |
   | `docs/supervisor-issues.md` | Issue note del Supervisor, fix applicati, proposte | 3 recap |
   | `docs/collector-intelligence-status.md` | Stato 8 collector (30% funzionante), priorità fix | 2 recap |
   | `docs/oco-dust-fee-analysis.md` | Bug fee/OCO/dust risolti e da verificare | 3 recap |

4. **Aggiornato BACKLOG.md** — ora funge da indice centrale con:
   - Piani di sviluppo (link alle 5 analisi tematiche)
   - Reference architetturale (tabella completa)
   - Recap storici (tabella con tutti i file in `docs/recap/`)
   - Bug da investigare (cross-link a TASKS.md)

---

### 📊 Stato Attuale

**Fase corrente:** Riorganizzazione docs/ completata

**Struttura finale:**

```
docs/
├── (7 standard loom)          ← ARCHIVE_TASKS, BACKLOG, CHANGELOG, HANDOFF, STORY, TASKS, TDD_LOG
├── analysis/ (5 analisi)      ← analisi tematiche consolidate da più recap
├── plans/ (7 piani/architetture) ← specifiche architetturali e piani implementazione
└── recap/ (9 cronologici)     ← MASTER_RECAP + 8 recap sessioni
```

### `docs/analysis/` — Analisi tematiche (5 file)
- `regime-detection-analysis.md` — Regime misclassification, Falling Knife
- `short-selling-analysis.md` — Short selling roadmap, decisioni aperte
- `supervisor-analysis.md` — Issue note del Supervisor
- `collector-intelligence-analysis.md` — Stato 8 collector (30% funzionante)
- `oco-dust-fee-analysis.md` — Bug fee/OCO/dust

### `docs/plans/` — Piani e architetture (7 file)
- `oco-flow-architecture.md` — Specifica OCO + User Data Stream
- `scalping-dataflow-architecture.md` — Data flow scalping
- `scalping-module-plan.md` — Piano implementazione scalping v2.0
- `short-selling-architecture.md` — Architettura short selling
- `supervisor-implementation-plan.md` — Piano implementazione supervisor
- `okx-api-reference.md` — Riferimento API OKX
- `roadmap-considerazioni.md` — Roadmap alternativa

### `docs/recap/` — Recap storici (9 file)
- `MASTER_RECAP.md` + 8 recap cronologici `YYYY-MM-DD_topic.md`

**Regola per nuovi file:**
- Nuova analisi → `docs/analysis/argomento-analysis.md`
- Nuovo piano/architettura → `docs/plans/argomento-plan.md` o `docs/plans/argomento-architecture.md`
- Nuovo recap sessione → `docs/recap/YYYY-MM-DD_topic.md`

---

### 🎯 Prossimi Step (in ordine)

1. **TASK-907** — Bug Frontend: dati mancanti su reload con sessione PAUSED
2. **TASK-908** — Hardcoded Resume Guard (no-short, regime bearish)
3. **TASK-1000** — WalletOrchestrator: Fase 1 (resolve puro + snapshot)
4. **TASK-INVEST-001→020** — Verificare se i 20 bug di MASTER_RECAP sono ancora aperti o già risolti

---

### 📝 Note Importanti

- **Documentation update obbligatorio** alla fine di OGNI sessione: aggiornare TASKS.md, STORY.md, HANDOFF.md
- **Script Python in `loom/scripts/`**: `parse_tasks.py` e `extract_tasks.py` risolvono i path relativi alla project root
- **docs/ organizzato**: root = standard loom + architettura + analisi tematiche (18 file); `docs/recap/` = cronologia sessioni (9 file)
- **BACKLOG.md** è l'indice centrale che collega tutti i documenti
- **5 analisi tematiche** consolidano informazioni da multipli recap, eliminando ridondanze
- **20 bug da investigare** in TASKS.md sezione "🎯 Task da Investigare"
- Backend: `http://localhost:8888` (porta configurata in `.env`)

**Ultima modifica:** 2026-07-02 — Cline

---

### ✅ FASE COMPLETATA: Close Positions on Session Stop (2026-06-03)

**Cosa è stato fatto:**

1. **Session stop chiude posizioni aperte** — Quando l'utente preme STOP (action: "stop" su `POST /scalping/session`), il backend ora:
   - Recupera il prezzo corrente (candle buffer → Binance REST → entry price fallback)
   - Calcola PnL/PnL% della posizione aperta
   - In **Paper Mode**: chiude la posizione in memoria via `PositionManager.close_position()`
   - In **Live Mode**: esegue market order tramite `Exchange.close_position()` (se exchange configurato)
   - Broadcast evento WS `trade_closed` al frontend
   - Salva il trade chiuso su Supabase (tabella `scalping_trades`)
   - Poi ferma WS broadcast, supervisor, e aggiorna stato sessione come prima

2. **`PositionManager.force_close_all()`** — Nuovo metodo per chiudere forzatamente TUTTE le posizioni aperte contemporaneamente, con log e conteggio.

3. **Fix type safety** — Gestito caso `current_price = None` con fallback a entry price (PnL=0) per evitare crash.

**File modificati:**
- `synthtrade/backend/app/scalping/router.py` — Logica di chiusura posizioni in `action == "stop"`
- `synthtrade/backend/app/scalping/engine/position_manager.py` — Aggiunto `force_close_all()`, import logging

---

### 📊 Stato Attuale

**Fase corrente:** TASK-813 — Bug Fixes & Improvements (close positions su stop ✅)

**Completato:**
- ✅ TASK-800 → TASK-810 (tutti completati)
- ✅ Pipeline diagnostics (log colorati, debug endpoint)
- ✅ MomentumBaseStrategy, CVD simulator, Warmup retry
- ✅ Close positions on session stop (paper + live)

---

### 🎯 Prossimi Step (in ordine)

1. **Avviare sessione scalping** — Testare che i trade partano effettivamente con i nuovi log
2. **Verificare endpoint `/api/scalping/debug/pipeline`** — Controllare collector health e score
3. **TASK-813 completamento** — Eventuali fix rimanenti (dropdown simbolo, pulsanti Watch/Ignore, pulizia directory)
4. **TASK-811 — Regressione E2E**: Test Playwright per scalping session
5. **TASK-812 — Go Live**: Review sicurezza ordini, test LIVE con trade minimo

---

### 📝 Note Importanti

- Backend: `http://localhost:8888` (porta configurata in `.env`)
- Pipeline debug: `GET http://localhost:8888/api/scalping/debug/pipeline`
- I log colorati funzionano su terminali ANSI (PowerShell 7+, VS Code terminal, WSL)
- **Stop session chiude posizioni automaticamente** — non lascia trade orfani
- In live mode l'exchange adapter deve essere configurato in `_execution_state["exchange"]`
- Se exchange non configurato → fallback a chiusura in memoria (come paper)

---

**Ultima modifica:** 2026-06-03 — Cline
