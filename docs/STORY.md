Storia operativa del progetto con versioni, milestone e decisioni chiave.

---

## 📖 Versioni

### v1.4.23 — 2026-07-21

**Milestone:** Fix leg detection OCO + resilient polling loop

**Completato:**
- ✅ **Fix leg detection `_normalize_algo_order`:** priorità `actualSide` da `orders-algo-history` (autorevole), fallback a confronto fill_price vs trigger_price (affidabile per OCO), ultimo resort `ordType` string matching
- ✅ **Aggiunto step 3 nel polling loop:** query `orders-algo-history?ordType=oco&state=effective` per ottenere `actualSide` corretto e catturare fill con lag API
- ✅ **Seed arricchito:** `algo_leg_map` (algoId → actualSide) popolata da `orders-algo-history` durante seed
- ✅ **Polling loop resiliente:** ogni step ha il suo try/except isolato — un errore in uno step non blocca gli altri
- ✅ **Recovery logging:** flag `_cycle_had_error` traccia errori per ciclo; log `recovered after previous error` al primo ciclo pulito
- ✅ **6 nuovi test** per leg detection: `actualSide` priority, OCO fill proximity, scenario reale bracket `3745204575738245120`

**Bug fix:**
- 🔧 OCO con entrambi trigger non-zero: prima etichettava sempre `take_profit` → ora usa `actualSide` o confronto distanza
- 🔧 Step 3 (`orders-algo-history`) con parametri errati (`instType` senza `ordType`) → aggiunto `ordType=oco`
- 🔧 Step 3 con 400 Bad Request uccideva l'intero polling loop → isolato con try/except separato

**File modificati:**
- `synthtrade/backend/app/execution/okx_order_event_stream.py`
- `synthtrade/backend/tests/unit/test_okx_adapter.py`

---

### v1.4.22 — 2026-07-21

**Milestone:** TASK-1166 completato — Refactoring totale router.py (-95.4%)

**Completato:**
- ✅ **Sub-TASK-1166.D:** Estratto `candle_processor.py` (844 righe), `trade_processor.py` (133 righe), `intel_processor.py` (75 righe) da `market_processors.py`
- ✅ **Sub-TASK-1166.E:** Estratto `rest/position.py` (116 righe), `rest/performance.py` (144 righe), `rest/config.py` (67 righe) da `rest/session.py`
- ✅ **Sub-TASK-1166.F:** `router.py` ridotto a 197 righe (da 4310 originali)
- ✅ `market_processors.py` diventato modulo di re-export (10 righe)
- ✅ Tutti i 12 test di integrazione passanti

**Risultato:**
| Metrica | Prima | Dopo | Riduzione |
|---------|-------|------|-----------|
| `router.py` | 4310 righe | 197 righe | -95.4% |
| `market_processors.py` | 1023 righe | 10 righe (re-export) | -99% |
| `rest/session.py` | 959 righe | 668 righe | -30% |

**File modificati:**
- `synthtrade/backend/app/scalping/candle_processor.py` (creato)
- `synthtrade/backend/app/scalping/trade_processor.py` (creato)
- `synthtrade/backend/app/scalping/intel_processor.py` (creato)
- `synthtrade/backend/app/scalping/market_processors.py` (diventato re-export)
- `synthtrade/backend/app/scalping/rest/position.py` (creato)
- `synthtrade/backend/app/scalping/rest/performance.py` (creato)
- `synthtrade/backend/app/scalping/rest/config.py` (creato)
- `synthtrade/backend/app/scalping/rest/session.py` (ridotto)
- `synthtrade/backend/app/scalping/router.py` (aggiornato include_router)
- `docs/TASKS.md` (aggiornato)

---

### v1.4.21 — 2026-07-21

**Milestone:** Fix critico — TP fill non rilevato da polling REST (2026-07-15)

**Problema:** Il TP su BTC-EUR si è eseguito su OKX alle 17:54, ma l'app non lo ha rilevato. La posizione fantasma è rimasta aperta per ~8 minuti fino allo stop manuale (18:02). Reconciliation allo stop ha trovato il fill in 5 secondi.

**Root cause (doppia):**
1. **seen_algos poisoning:** il seed in `_start_polling()` aggiungeva gli algoId dei pending algos a `seen_algos`. Quando l'algo faceva fill, compariva in `orders-history` con lo stesso algoId → saltato dal check `algo_id not in seen_algos`.
2. **Task asyncio morto silenziosamente:** il polling loop ha subito 9 errori di connessione in 5 ore (14:08→17:50), con frequenza crescente. L'ultimo errore alle 17:50:09, poi silenzio totale per 12 minuti. Nessuno monitorava lo stato del task.

**Fix applicati:**
- ✅ Rimosso il seed dei pending algos da `seen_algos` (inutile: `_normalize_algo_order` filtra `state="live"` → `None`)
- ✅ Spostato `seen_algos.add(algo_id)` in step 3 **dopo** l'emit riuscito (prima era prima)
- ✅ Aggiunto health check in `session_health_job`: se `_listen_task.done()` è True, riavvia automaticamente lo stream

**File modificati:**
- `synthtrade/backend/app/execution/okx_order_event_stream.py`
- `synthtrade/backend/app/scheduler/scalping_jobs.py`

**Lezione appresa:** Il polling REST come unico meccanismo di rilevamento fill richiede robustezza totale. Non basta avere un try/except nel loop — serve anche un health check esterno che rilevi il task morto e lo riavvii.

---

### v1.4.20 — 2026-07-17

**Milestone:** Refactoring `router.py` (Fase 1: Moduli Foglia)

**Completato:**
- ✅ **TASK-1166 (Phase 1):** Iniziato il refactoring del monolitico `router.py` estraendo moduli chiave.
- ✅ Estratto `_state.py` per gestire le variabili globali (`_execution_state`, websocket array, ecc.).
- ✅ Estratto `pricing.py` per le funzioni pure di pricing e size calculations.
- ✅ Estratto `reconciliation.py` contenente `_reconcile_position_with_exchange`.
- ✅ Estratto `db_ops.py` contenente `_save_open_position_to_db` e `_update_closed_position_in_db`.
- ✅ Test suite completa eseguita con successo senza errori di sintassi e import risolti.
- ✅ Il flusso `algoId` per la tracciabilità e riconciliazione degli ordini condizionali è confermato essere persistente e corretto in DB.

**Decisioni chiave:**
- `router.py` manterrà il ruolo di orchestratore esportando gli oggetti necessari all'esterno per backward compatibility.
- Architettura a moduli con separazione chiara (state -> leaf modules -> trade execution -> REST endpoints).

**File modificati:**
- `synthtrade/backend/app/scalping/router.py`
- `synthtrade/backend/app/scalping/_state.py` (creato)
- `synthtrade/backend/app/scalping/pricing.py` (creato)
- `synthtrade/backend/app/scalping/reconciliation.py` (creato)
- `synthtrade/backend/app/scalping/db_ops.py` (creato)
- `docs/TASKS.md`
- `docs/ARCHIVE_TASKS.md`

### v1.4.19 — 2026-07-17

**Milestone:** Completamento epica AlgoId Flow & UI Fixes

**Completato:**
- ✅ **TASK-1180:** Trade fantasma rimosso da UI filtrando `external_close_unknown_price`.
- ✅ **TASK-1181:** Entry price ora riflette il fill reale calcolato via `get_order_by_id`.
- ✅ **TASK-1182:** Badge "RUNNING" / "PAUSED" si sincronizza correttamente con lo stato sessione.
- ✅ **TASK-1183:** Trade Log mostra data e ordina cronologicamente in modo corretto.
- ✅ **TASK-1184, 1185, 1186, 1187, 1188:** Unit test estesi per riconciliazione (A-E), linkage `entry_order_id`, post-fill async fetch, db restore di pos_obj e audit script eseguiti con successo.

**Contesto:** Il flusso di riconciliazione su OKX EU era afflitto da entry prices non realistici e side-effects in UI come ghost trades. Connettendo l'`entry_order_id` in DB, il backend ora rintraccia con 3 retry il fill reale asincrono del market order e lo associa nativamente al DB e al flusso WebSocket `position`. La topbar UI è stata migliorata reattivamente per session states asincroni.

**File modificati:**
- `synthtrade/backend/app/scalping/router.py` (retry fill, `entry_order_id`)
- `synthtrade/backend/tests/unit/test_reconcile_position.py` (casi A-E)
- `synthtrade/backend/app/main.py` (ghost trade filter)
- `synthtrade/frontend/synthtrade-ui/src/app/scalping/components/trade-log.component.ts` (timestamp date + dedup)
- `synthtrade/frontend/synthtrade-ui/src/app/layout/topbar/topbar.component.ts` (sync badge with session.status)
- `docs/TASKS.md` (tasks completati)

### v1.4.18 — 2026-07-16

**Milestone:** Fix restore reconcile dopo riavvio PC — code review post-deploy

**Completato:**
- ✅ **TASK-1174:** Fix P1 — `get_symbol_rules` failure non bloccava più la riconciliazione restore. Rimosso pre-check ridondante, delegato interamente a `_reconcile_position_with_exchange`
- ✅ **TASK-1175:** Fix P1 — Algo history retry ora esegue sempre 3 tentativi con delay, non si blocca su risultati vuoti
- ✅ **TASK-1176:** Fix P2 — Adapter init failure durante restore loggato a `error` con traceback

**Contesto:** Dopo il commit precedente (restore reconcile a doppio livello), una code review ha identificato 3 problemi: (1) se `get_symbol_rules` falliva nel blocco post-WS, la riconciliazione veniva silenziosamente saltata; (2) il retry su algo history si bloccava al primo tentativo vuoto; (3) il fallimento dell'adapter era solo un warning.

**File modificati:**
- `synthtrade/backend/app/scalping/router.py` (blocco restore in `_start_ws_broadcast` + fallback algo history)
- `synthtrade/backend/app/main.py` (log level adapter init)

### v1.4.17 — 2026-07-15

**Milestone:** Fix Change Detection prezzo live chart + EPICA AUDIT POST-OKX completamento

**Completato:**
- ✅ **TASK-1173:** Fix `LiveChartComponent` prezzo non si aggiorna — Change Detection mancante (`live-chart.component.ts`)
- ✅ **TASK-1172:** Fix chart preview symbol blocked by stale session status (`live-chart.component.ts`)
- ✅ **TASK-1164:** OKX adapter REST-only completo (`okx_exchange.py`)
- ✅ **TASK-907:** Frontend PAUSED session bug fix (`trade-log.component.ts`, `performance-panel.component.ts`)
- ✅ Broadcast race condition fix (`router.py`)
- ✅ OKBEUR phantom engine fix (`router.py`)
- ✅ POSITION_RECONCILE cashBal fix (`okx_exchange.py`)
- ✅ Stale price on symbol switch fix (`live-chart.component.ts`)
- ✅ Candle HTTP timeout fix (`live-chart.component.ts`)

**Root cause TASK-1173:** Tutti gli altri componenti scalping usano `cdr.detectChanges()` dopo ogni mutazione di stato da WS. `LiveChartComponent` era l'unico senza — il prezzo veniva aggiornato nella memoria ma Angular non lo sapeva e non ridisegnava il template. Il click sulla select funzionava perché forzava un giro di change detection.

**File modificati:**
- `synthtrade/frontend/synthtrade-ui/src/app/scalping/components/live-chart.component.ts`
- `synthtrade/backend/app/execution/okx_exchange.py`
- `synthtrade/frontend/synthtrade-ui/src/app/scalping/components/trade-log.component.ts`
- `synthtrade/frontend/synthtrade-ui/src/app/scalping/components/performance-panel.component.ts`
- `synthtrade/backend/app/scalping/router.py`

### v1.4.16 — 2026-07-14

**Milestone:** Fix TP/SL fill detection OKX EU — Consolidamento polling loop

**Completato:**
- ✅ **TASK-1126:** Consolidato chiamate duplicate `orders-history` in un'unica richiesta con `state=filled`
- ✅ **TASK-1126:** Seed iniziale ora include sia ordini regolari che algo orders (TP/SL)
- ✅ **TASK-1126:** OKX EU: gli ordini algo appaiono in `orders-history` con `algoId` popolato
- ✅ **TASK-1126:** Rimosso tentativo fallito di `orders-algo-history?ordType=oco` (400 su OKX EU)

**Decisioni chiave:**
- OKX EU accounts hanno permessi limitati su `orders-algo-history` → usare `orders-history?state=filled`
- Unica chiamata riduce pressione rate limit
- Seed iniziale cattura TP/SL già eseguiti prima del restart

**File modificati:**
- `synthtrade/backend/app/execution/okx_order_event_stream.py`

### v1.4.15 — 2026-07-13

**Milestone:** Revert TASK-1130/1131 + Stato operativo sistema OKX EU live

**Completato:**
- ✅ **Revert TASK-1130/1131:** Tutti i cambiamenti sono stati revertiti (`git checkout --`)
- ✅ **Sistema operativo:** Sessione BTC-EUR avviata con successo in modalità live
- ✅ **Saldo EUR:** 23.10 disponibile, sufficiente per trade_value 20.0
- ✅ **Bracket OCO:** Piazzato via REST diretto, algoId=3739635723994378240
- ✅ **WS private fallback:** REST polling attivo (2s interval) dopo errore 60032
- ✅ **Nessun errore critico:** Il fallback REST polling gestisce gli eventi di fill correttamente

**Decisioni chiave:**
- WS private failure (60032) su OKX EU non è un errore bloccante
- REST polling fallback è operativo e sufficiente
- I fix TASK-1126, TASK-1121, TASK-1122, TASK-1123 rimangono in atto

**File modificati:**
- Nessuno - stato originale ripristinato

### v1.4.14 — 2026-07-13 (REVERTED)

**Milestone:** TASK-1130 + TASK-1131 — CCXT REST fallback per OKX EU accounts + ulteriori fix

**Stato:** Revertito - il sistema funziona con i fix precedenti.

**Decisioni chiave:**
- Revertito perché il fallback REST polling è operativo
- WS private failure non segnalato come errore se c'è fallback funzionante

**File modificati:**
- Revertiti tutti i file modificati

### v1.4.13 — 2026-07-10

**Milestone:** Fix bracket OKX — SL sopra entry (sCode 51280)

**Completato:**
- ✅ **Bug SL BUY con fee OKX alte:** `_net_to_gross_pct(-sl)` positivo con taker 0.35%/maker 0.2% → SL calcolato sopra entry → OKX 51280 → emergency sell
- ✅ **Helper `_sl_price_from_entry`:** movimento lordo sempre positivo, direzione corretta per BUY/SELL
- ✅ **Test integrazione** aggiornato per fee OKX reali

**Decisioni chiave:**
- Non assumere il segno del risultato di `_net_to_gross_pct` per lo SL — usare sempre magnitudine assoluta
- I warning CCXT 50119 sono non-bloccanti (fallback REST operativo)

**File modificati:**
- `synthtrade/backend/app/scalping/router.py`
- `synthtrade/backend/tests/integration/test_okx_integration.py`

### v1.4.8 — 2026-07-09

**Milestone:** Bug OKB-EUR collector + supporto demo mode OKX

**Completato:**
- ✅ **Bug fix OKB-EUR in FUTURES_SYMBOL_MAP:** Aggiunto `"OKBEUR": None, "OKB-EUR": None` a `open_interest.py`, `funding_rate.py`, `long_short_ratio.py` per evitare chiamate 400 a Binance Futures
- ✅ **Router supporto demo mode:** `control.get("mode") == "live"` → `in ("live", "test")` per costruire adapter anche in demo mode
- ✅ **Frontend session.model.ts:** aggiunto `'test'` ai tipi `mode`
- ✅ **Frontend session-api.service.ts:** aggiunto `'test'` al parametro `start()`
- ✅ **Frontend session-controls.component.ts:** mappato `globalMode='test'` → `mode='test'` (prima era mappato a 'paper')
- ✅ **Frontend session-controls.component.ts:** template mostra "DEMO" quando `session.mode === 'test'`
- ✅ **TASK-1116.F:** Fix `mode_valid` health check per accettare `mode='test'`

**Decisioni chiave:**
- OKX non ha futures perpetual per OKB-EUR → graceful skip corretto
- Il router deve costruire l'adapter anche per `mode=test` (OKX Demo Trading)
- Il frontend deve supportare `mode='test'` per avviare sessioni demo
- Health check deve validare `mode='test'` come valore legittimo

**File modificati:**
- `synthtrade/backend/app/scalping/intelligence/collectors/open_interest.py`
- `synthtrade/backend/app/scalping/intelligence/collectors/funding_rate.py`
- `synthtrade/backend/app/scalping/intelligence/collectors/long_short_ratio.py`
- `synthtrade/backend/app/scalping/router.py`
- `synthtrade/backend/app/execution/okx_exchange.py` — fallback REST per get_trade_fee()
- `synthtrade/backend/app/scheduler/scalping_jobs.py` — fix mode_valid health check
- `synthtrade/frontend/synthtrade-ui/src/app/scalping/models/session.model.ts`
- `synthtrade/frontend/synthtrade-ui/src/app/scalping/services/session-api.service.ts`
- `synthtrade/frontend/synthtrade-ui/src/app/scalping/components/session-controls.component.ts`
- `synthtrade/supabase/migrations/20260709000000_task1116d_add_test_mode_check.sql` — nuova migration
- `docs/TASKS.md` — task 1116.D, 1116.E, 1116.F, 1116.G, 1119, 1120

### v1.4.10 — 2026-07-09

**Milestone:** Fix Pylance NoneType error in self.client.urls["api"] access

**Completato:**
- ✅ **TASK-1121:** Aggiunto guard `self.client.urls is not None` per evitare `Object of type "None" is not subscriptable` quando ccxt restituisce `None` per `urls`
- ✅ **TASK-1121:** Sostituito `.get("api", {})` con `(self.client.urls.get("api") or {})` per gestire `None` values nel dict
- ✅ **TASK-1121:** isinstance guard già presente per saltare valori `None` nel dict comprehension

**Decisioni chiave:**
- CCXT può restituire `None` per `urls` in certe modalità operative → doppia guardia necessaria
- Il fix è conservativo: non modifica la logica, aggiunge solo safety checks

### v1.4.11 — 2026-07-10

**Milestone:** Fix UDS reconnect sync error - missing _fetch_fill_price_by_order_id method

**Completato:**
- ✅ **TASK-1126:** Aggiunto metodo `_fetch_fill_price_by_order_id` a `OkxExchangeAdapter` per recupero fill price durante riconnessione UDS
- ✅ **TASK-1126:** Il metodo converte simbolo OKX (OKB-EUR) a formato CCXT (OKB/EUR) e recupera ordini chiusi recenti
- ✅ **TASK-1126:** Risolto errore `'OkxExchangeAdapter' object has no attribute '_fetch_fill_price_by_order_id'` durante session stop con trade aperto

**Decisioni chiave:**
- Il metodo mancava in `OkxExchangeAdapter` ma era presente in `BinanceExchangeAdapter`
- La riconnessione UDS usava questo metodo per recuperare il fill price dell'OCO eseguito durante la disconnessione
- Senza questo metodo, il recupero falliva e il trade rimaneva in stato inconsistente

**File modificati:**
- `synthtrade/backend/app/execution/okx_exchange.py` — aggiunto `_fetch_fill_price_by_order_id` method

### v1.4.12 — 2026-07-10

**Milestone:** Fix OKX fee API returns negative fees for base level accounts

**Completato:**
- ✅ **TASK-1127:** Aggiunto conversione automatica fee negative in positive per account base level (Lv1)
- ✅ **TASK-1127:** OKX API restituisce fee negative anche per account "Utente regolare" che non hanno rebate
- ✅ **TASK-1127:** Corretto calcolo TP/SL che erroneamente piazzava TP sotto entry per BUY orders
- ✅ **TASK-1127:** Mantenute fee negative per account VIP con rebate reali

**Decisioni chiave:**
- L'API OKX `/api/v5/account/trade-fee` restituisce fee negative per tutti gli account, indipendentemente dal livello VIP
- Per account base level (Lv1), le fee negative sono errate - non hanno rebate reali
- Il sistema ora converte automaticamente le fee negative in positive per account base level
- Per account VIP con rebate reali, mantiene le fee negative

**Problema risolto:**
- TP era calcolato SOTTO l'entry per BUY orders (es: entry 70.9€, TP 70.86€)
- Questo causava chiusura immediata del trade
- Ora con fee positive, TP viene calcolato correttamente SOPRA l'entry

**File modificati:**
- `synthtrade/backend/app/execution/okx_exchange.py` — conversione fee base level, rimozione metodo duplicato
- `synthtrade/backend/app/scalping/router.py` — aggiornato calcolo TP/SL per fee positive

**File modificati:**
- `synthtrade/backend/app/execution/okx_exchange.py`

### v1.4.14 — 2026-07-10

**Milestone:** TASK-1124 — Direct REST fallback per place_exit_bracket + fix double emergency close

**Completato:**
- ✅ **Aggiunto `_direct_place_exit_bracket()`** — chiama direttamente POST `/api/v5/trade/order-algo` con firma HMAC-SHA256, body speculare a quello passato via ccxt, e stessa gestione errori di `_direct_place_market_order()` (sCode, sMsg, full_data)
- ✅ **Modificato `place_exit_bracket()`** — se CCXT fallisce con `50119` o `"API key doesn't exist"`, prova il fallback REST diretto prima di arrendersi
- ✅ **Eliminata race condition double emergency close** — l'adapter non tenta più `close_position()` interno; solleva solo `ExitProtectionError` e lascia che il router (`BRACKET_FLOW CASO B`) sia l'unico proprietario della chiusura d'emergenza
- ✅ **Se l'errore CCXT NON è 50119** (es. parametri invalidi), solleva direttamente `ExitProtectionError` senza fallback REST

**Decisioni chiave:**
- Stesso pattern di fallback già usato con successo per `_direct_place_market_order()` — esteso ora agli ordini algo bracket
- Il doppio tentativo di emergency close (adapter + router) causava l'errore 51008 ("margin borrowing") sulla prima chiusura — ora un solo owner
- Se entrambi CCXT e REST falliscono, l'adapter non lascia mai la posizione scoperta: il router gestisce l'emergency close come unico responsabile

**File modificati:**
- `synthtrade/backend/app/execution/okx_exchange.py` — nuovo metodo `_direct_place_exit_bracket()` + refactor `place_exit_bracket()` con fallback REST e rimozione emergency close interno

**Verifica:** Il prossimo bracket su OKX EU non deve più produrre `[OKX BRACKET FAILED]` per 50119 — deve passare tramite REST diretto e piazzare correttamente il TP/SL server-side.

### v1.4.13 — 2026-07-10

**Milestone:** Fix sCode=51020 — Router passa quote_amount invece di quantity per BUY market order su OKX

**Completato:**
- ✅ **FIX-2026-07-10:** Il `MarketOrderRequest` per BUY live ora passa `quote_amount=_trade_val` (20.0 EUR) invece di `quantity=_qty_precise` (0.2851 OKB), permettendo a OKX di usare `tgtCcy=quote_ccy` e calcolare autonomamente la quantità base nel rispetto dei propri vincoli `minSz`
- ✅ **FIX-2026-07-10:** `exec_qty` ora prende la quantità filled dalla risposta OKX (`market_res.filled` o `market_res.quantity`) invece di usare la quantità precalcolata
- ✅ **FIX-2026-07-10:** Il calcolo di `_qty_precise` rimane come guardia per il balance check e il controllo `minQty`, ma non viene più passato all'exchange

**Decisioni chiave:**
- Per BUY market su OKX, passare sempre l'importo in quote currency (EUR) e lasciare che OKX calcoli la quantità base — questo rispetta automaticamente i vincoli `minSz` del symbol
- La quantità precalcolata (`_qty_precise`) resta utile solo per il balance check preventivo e il controllo `minQty`, non per l'ordine reale
- Stesso pattern già confermato funzionante nello spike (docs/analysis/okx-demo-spike-results.md §5)

**File modificati:**
- `synthtrade/backend/app/scalping/router.py` — righe 1634-1645: `quantity=_qty_precise` → `quote_amount=_trade_val`

**Verifica:** Il prossimo BUY market su OKX per OKB-EUR non deve più produrre sCode=51020.

### v1.4.15 — 2026-07-10

**Milestone:** TASK-1129 — Fix type errors in okx_exchange.py

**Completato:**
- ✅ **TASK-1129:** Rimosso metodo duplicato `get_trade_fee` (seconda definizione senza logica TASK-1127)
- ✅ **TASK-1129:** Rimosso metodo duplicato `_direct_place_market_order`
- ✅ **TASK-1129:** Aggiunto `or 0` a tutte le conversioni float() per gestire valori None
- ✅ **TASK-1129:** Aggiunto `cast(dict[str, Any], ...)` per convertire oggetti CCXT in dict dove richiesto
- ✅ **TASK-1129:** Sostituito chiamata `_get_ccxt_symbol(sym_ref.okx)` con `sym_ref.ccxt` diretto
- ✅ **TASK-1129:** Inizializzato qty, tp_price, sl_price prima del try-catch in place_exit_bracket
- ✅ **TASK-1129:** Aggiunto tipi di ritorno specifici per dict methods (dict[str, Any])

**Decisioni chiave:**
- I duplicati erano residui di refactoring precedenti e causavano errori Pylance
- CCXT restituisce spesso None per campi op → necessarie guardie or 0 nelle conversioni float
- CCXT Order objects non sono dict nativi → necessaria conversione con cast()
- Metodo _get_ccxt_symbol non esisteva → sostituito con accesso diretto a sym_ref.ccxt
- Variabili unbound in exception handler causavano errori runtime in edge cases

**File modificati:**
- `synthtrade/backend/app/execution/okx_exchange.py` — cleanup duplicati, fix type errors, aggiunti cast

**Effetto:** Tutti gli errori Pylance risolti, type checking ora passa senza errori.

### v1.4.12 — 2026-07-10

**Milestone:** TASK-1125 — Collector Intelligence: Diagnostica Coverage Reale per Simbolo

**Completato:**
- ✅ **TASK-1125:** Aggiunto `is_symbol_supported()` a `FundingRateCollector`, `OpenInterestCollector`, `LongShortRatioCollector` — ogni collector ora sa dire se un simbolo può strutturalmente avere quel dato (es. OKB-EUR non ha perpetual futures → `False`)
- ✅ **TASK-1125:** Aggiunto `get_configurable_weight_total(symbol)` in `SignalScoreEngine` — calcola il peso configurabile totale ESCLUDENDO i collector strutturalmente impossibili per quel simbolo
- ✅ **TASK-1125:** Aggiunto log diagnostico `[COVERAGE_REAL]` in `_build_snapshot()` — mostra `real_coverage`, `structurally_unavailable`, `no_response_transient`, `old_coverage_field` per ogni ciclo di scoring

**Decisioni chiave:**
- Coverage reale = peso risposto / peso configurabile (esclude collector che non risponderanno MAI per quel simbolo)
- `old_coverage_field` viene loggato accanto per confronto — nessun comportamento di trading cambiato
- La diagnostica copre: OKB-EUR (3 collector structuralmente assenti), BTC-EUR (quasi tutti presenti), e qualsiasi simbolo

**File modificati:**
- `synthtrade/backend/app/scalping/intelligence/collectors/funding_rate.py` — nuovo metodo `is_symbol_supported()`
- `synthtrade/backend/app/scalping/intelligence/collectors/open_interest.py` — nuovo metodo `is_symbol_supported()`
- `synthtrade/backend/app/scalping/intelligence/collectors/long_short_ratio.py` — nuovo metodo `is_symbol_supported()`
- `synthtrade/backend/app/scalping/intelligence/signal_score_engine.py` — nuovo metodo `get_configurable_weight_total()` + log `[COVERAGE_REAL]`

**Verifica:** Syntax check passato su tutti e 4 i file. Commit `1263803`.

### v1.4.11 — 2026-07-09

**Milestone:** CCXT create_order fallisce con 50119 su OKX EU — fallback REST diretto per market order

**Completato:**
- ✅ **TASK-1123:** Aggiunto metodo `_direct_place_market_order()` che usa POST `/api/v5/trade/order` con firma HMAC-SHA256 diretta, bypassando CCXT
- ✅ **TASK-1123:** Modificata `place_market_order()`: se CCXT fallisce con `50119` o `"API key doesn't exist"`, usa il fallback REST diretto
- ✅ **TASK-1123:** Il fallback supporta sia quantità base che `tgtCcy=quote_ccy` per buy con importo in valuta quota

**Decisioni chiave:**
- Stesso pattern di fallback già usato con successo per `_direct_fetch_balance()` — esteso ora agli ordini market
- CCXT `create_order()` fallisce con 50119 su EU accounts per lo stesso motivo di `load_markets()` — REST diretto risolve

**File modificati:**
- `synthtrade/backend/app/execution/okx_exchange.py` — nuovo metodo `_direct_place_market_order()` + fallback in `place_market_order()`

### v1.4.10 — 2026-07-09

**Milestone:** Fix Pylance NoneType error in self.client.urls["api"] access

**Completato:**
- ✅ **TASK-1119:** `get_symbol_filters()` aggiunto come wrapper su `get_symbol_rules()` (commit 6d3b52b)
- ✅ **TASK-1119:** `get_btc_macro_context()` con fallback REST diretto per EU accounts (commit 6d3b52b)
- ✅ **TASK-1120:** `get_balance()` usa solo `availBal` via REST diretto, allineato a okx_balance.py (commit 16b26f2)

**Decisioni chiave:**
- OkxExchangeAdapter deve implementare tutti i metodi chiamati dal router LIVE path
- Balance deve usare la stessa logica del dashboard per coerenza
- CCXT fallisce con 50119 su EU accounts → fallback REST diretto necessario

**File modificati:**
- `synthtrade/backend/app/execution/okx_exchange.py`

### v1.4.7 — 2026-07-09

**Milestone:** Fix regressione chart live - indentazione endpoint /candles/{symbol}

**Completato:**
- ✅ **TASK-1100.G (Chart fix v5)** — Corretta indentazione dell'endpoint `@router.get("/candles/{symbol}")` in `router.py` che era erroneamente annidato dentro la funzione `get_trade_history`. Questo causava errore 404 e chart vuote quando il frontend cercava di recuperare i dati delle candele.
- ✅ **Verifica endpoint REST** — L'endpoint `/api/scalping/candles/{symbol}` ora restituisce correttamente i dati delle candele da HistoricalLoader per simboli come BTC-EUR.
- ✅ **Chart funzionante** — La live chart ora visualizza correttamente le candele storiche e gli aggiornamenti real-time sia quando si seleziona un simbolo sia quando si avvia una sessione.

**Decisioni chiave:**
- L'endpoint deve essere a livello di modulo per essere registrato correttamente da FastAPI
- La regressione era introdotta probabilmente durante un refactor precedente

**File modificati:**
- `synthtrade/backend/app/scalping/router.py` — Fix indentazione endpoint candles

### v1.4.6 — 2026-07-08

**Milestone:** TASK-1113 Cutover OKX live readiness + TASK-1114 Fee tier parity completati

**Completato:**
- ✅ TASK-1113: Cutover OKX live readiness (config, safety gates, smoke tests, runbook)
- ✅ TASK-1114: OKX fee tier e net pricing parity (FeeTier model, log [NET_PRICING] arricchito, abs() rebate, quote-aware commission conversion)

**Completato:**
- ✅ **1113.A — Default config**: `.env.example` già configurato con `EXCHANGE_PROVIDER=okx`, `TRADING_MODE=test`. Binance legacy documentato come fallback.
- ✅ **1113.B — Safety gates**: `ALLOW_LIVE_MODE=false`, `TRADING_MODE=test`, `SCALPING_FORCE_PAPER=true` attivi. Trade value minimo consigliato nel runbook.
- ✅ **1113.C — Smoke tests**: Health check OK (`{"status":"ok"}`), Instruments OKX caricati (16 EUR pairs), endpoint `/candles/btceur` funzionante.
- ✅ **1113.D — Runbook**: Creato `docs/analysis/okx-live-runbook.md` con setup API key, safety gates, smoke test checklist, emergency stop procedure, go-live checklist e rischi.
- ✅ **1113.E — Decisione go-live**: Documentata nel runbook §7. Primo trade live (20€) richiede conferma manuale esplicita.

**Decisioni chiave:**
- OKX è default operativo — confermato da sessioni paper di luglio con dati reali
- Live trading non può partire accidentalmente (safety gates molteplici)
- Prima del go-live live reale, serve validazione bracket in demo (TASK-1100.G pendente)

**File creati:**
- `docs/analysis/okx-live-runbook.md` — runbook operativo completo

### v1.4.5 — 2026-07-08

**Milestone:** Fix grafico OKX - candele real-time e completamento storico

**Completato:**
- ✅ **TASK-1100.G (Chart fix v1)** — Implementato WS candle1m subscription come primary source invece di REST poller
- ✅ **TASK-1100.G (Chart fix v1)** — Broadcast completo di tutte le 100 candele storiche durante preload al frontend
- ✅ **TASK-1100.G (Chart fix v1)** — REST poller ora fallback intelligente che si disabilita automaticamente quando WS attivo
- ✅ **TASK-1100.G (Chart fix v1)** — Tracking attività WS per switch automatico tra WS e REST
- ✅ **Bug fix router.py:** Corretto riferimento variabile `selected_balance` non definita → `available_balance`
- ✅ **Bug fix okx_ws_client.py:** Aggiunta dichiarazione variabile `_check_counter` mancante
- ✅ **TASK-1100.G (Chart fix v2)** — Rimosso broadcast WS non necessario (frontend usa HTTP per storico)
- ✅ **TASK-1100.G (Chart fix v2)** — HTTP /candles/{symbol} ora usa sempre HistoricalLoader come primary
- ✅ **TASK-1100.G (Chart fix v2)** — Assicurato caricamento dati storici completi via HTTP
- ✅ **TASK-1100.G (Chart fix v3)** — Sostituito demo network con live network per dati di mercato
- ✅ **TASK-1100.G (Chart fix v3)** — OKX live network ha liquidità normale, demo network aveva candele piatte
- ✅ **TASK-1100.G (Chart fix v4)** — Aggiunto URL WS backup per problemi DNS e migliorata gestione connessione

**Decisioni chiave:**
- Il frontend usa HTTP per dati storici e WS solo per aggiornamenti real-time
- WS candle1m deve essere primary source per aggiornamenti real-time, REST solo fallback
- Auto-switching intelligente WS/REST garantisce massima affidabilità dati
- Broadcast WS di candele storiche era non necessario e causava problemi
- Demo network OKX ha bassa liquidità → usare sempre live network per dati di mercato
- Demo mode deve essere solo per trading execution, non per market data
- Fallback automatico WS backup quando primary URL fallisce per DNS

**File modificati:**
- `synthtrade/backend/app/scalping/router.py` — WS primary, REST fallback, HTTP endpoint fix
- `synthtrade/backend/app/scalping/engine/okx_ws_client.py` — WS candle subscription primary

### v1.4.4 — 2026-07-03

**Milestone:** TASK-1107 100% + TASK-1111 12/12 PASS

**Completato:**
- ✅ **TASK-1100.G — WS private EU workaround:** A causa di limitazioni di policy OKX per account EEA (errore `60032` su websocket private), implementato fallback via REST polling (2s) in `OkxOrderEventStream` intercettando `/api/v5/trade/orders-history` e `orders-algo-history` per i fill TP/SL. Valido e performante per operazioni di scalping che durano minuti/ore con ordini condizionali on-exchange.
- ✅ `_live_close_position` convertito a provider-neutral: usa `cancel_open_exit_orders`, `get_holdings`, `get_symbol_rules`, `close_position(ClosePositionRequest)` — zero metodi Binance-specific residui
- ✅ **TASK-1107 ora al 100%** — tutto il router scalping è provider-neutral
- ✅ `fake_okx_adapter.py` — FakeOkxAdapter (ExchangeAdapterProtocol senza rete) + FakeOrderStream con `fire_fill()` per eventi WS sintetici
- ✅ `test_okx_integration.py` — 12 test integration, tutti PASS: happy path, bracket failure, stop session, restore open, restore closed, fee pricing
- ✅ **Bug fix critico in router.py:** `abs()` su `entry_fee_pricing`/`exit_fee_pricing` — fee OKX negative (rebate) producevano TP/SL invertiti in `_net_to_gross_pct`

**Decisioni chiave:**
- `_net_to_gross_pct` si aspetta rate positivi; fee OKX sono rebate negativi → `abs()` obbligatorio
- `_live_close_position` Scenario 1 (bracket già fillato): usa `get_ticker_price` come fallback invece di `fetch_closed_orders` Binance-specific — meno preciso ma provider-neutral
- FakeOkxAdapter usa `holdings_data` per simulare balance base asset post-buy

### v1.4.3 — 2026-07-03

**Milestone:** TASK-1107 Router scalping provider-neutral completato

**Completato:**
- ✅ **Entry flow provider-neutral:** sostituito `place_oco_order` con `place_exit_bracket(ExitBracketRequest)` — funziona per OKX e Binance
- ✅ **`_handle_bracket_failed`:** rimpiazza `_handle_oco_failed`, usa `cancel_open_exit_orders` + `ClosePositionRequest` dal protocollo
- ✅ **`_on_order_update` provider-neutral:** usa `bracket_id` (provider-neutral) invece di `order_list_id` Binance-only; usa campo `leg` da OKX (`take_profit`/`stop_loss`) direttamente senza dover matchare orderId
- ✅ **TASK-1108 verificato:** migration DB applicata su Supabase con colonne provider-neutral e backfill legacy
- ✅ **Tutti i file OKX compilano senza errori**

**Decisioni chiave:**
- `_live_close_position` lasciata Binance-specific per ora: usa path manuale via segnale (non bracket), non blocca OKX
- `_on_order_update` ora usa `leg` field da OKX algo-orders per determinare TP vs SL senza matchare orderId (che OKX non espone sullo stesso channel)
- Compatibility Binance: `pos.oco_order_list_id` usato ancora come bracket_id per matching — lo stesso campo viene mappato da entrambi i provider

**File modificati:**
- `synthtrade/backend/app/scalping/router.py` — entry flow, bracket failure handler, order update handler

### v1.4.2 — 2026-07-03

**Milestone:** TASK-1100 OKX Demo Spike — Sottotask E/F/H completati

**Completato:**
- ✅ **Audit file OKX implementati:** okx_exchange.py, okx_ws_client.py, okx_order_event_stream.py, exchange_models.py, exchange_factory.py tutti verificati completi e coerenti
- ✅ **TASK-1100.E — Market order:** 10€ → 0.00022883 BTC @ 43700€ su OKX Demo, fee rebate -0.0000008 BTC confermato
- ✅ **TASK-1100.F — Exit bracket:** algoId `3709954518432436224` piazzato con successo via `/api/v5/trade/order-algo`, TP +0.5% @ 43918.5€, SL -0.3% @ 43568.9€
- ✅ **TASK-1100.H — WS public trades:** subscription OK su `wss://wspap.okx.com/ws/v5/public?brokerId=9999`, parser CVD implementato e mapping verificato (`side=sell → is_buyer_maker=True`)
- ✅ **Decisione bracket finale:** usare `order-algo` standard (non `attachAlgoOrds`), minSz ≥ 0.0001 BTC (~4€+)

**Blocco rimanente:**
- ❌ **TASK-1100.G — WS private:** auth fallisce `60032 API key doesn't exist`, richiede fix URL EU `wss://wsaws.okx.com:8443/ws/v5/private` (già identificato)
- **Decisione:** validare WS private fill events in TASK-1112 (Demo E2E) quando il flusso completo è cablato, procedere con TASK-1101+ (config, protocol, integration)

**Decisioni chiave:**
- Exit bracket OKX usa endpoint `/api/v5/trade/order-algo` con `tpTriggerPx`/`slTriggerPx` + `tpOrdPx="-1"`/`slOrdPx="-1"` per market order al trigger
- minSz bracket: 0.0001 BTC minimo (4€+ a prezzi attuali), sotto questa soglia OKX rifiuta con `51000 Parameter sz error`
- CVD mapping OKX: `side=buy` (taker buyer) → `is_buyer_maker=False`, `side=sell` (taker seller) → `is_buyer_maker=True`
- Default symbol: `BTC-EUR` (OKB-EUR non disponibile né in demo né live EU)
- WS private validation rinviata a TASK-1112 end-to-end (fix URL già noto)

### v1.4.1 — 2026-07-03

**Milestone:** Fix Pylance type errors in test files

**Completato:**
- ✅ Aggiunto `# type: ignore[arg-type]` su `test_settings_validation()` in `loom/tests/test_task_015.py` per sopprimere falso positivo Pylance quando si passa `"not-a-number"` a un campo `float`.
- ✅ Fixati ~30 errori Pylance in `synthtrade/backend/tests/unit/test_okx_adapter.py`:
  - Rimosso import inutilizzato `asyncio` e `patch`
  - Aggiunto `# noqa: F841` su `_FEE` (variabile inutilizzata)
  - Aggiunti `# type: ignore[attr-defined]` su tutti gli accessi a metodi/campi protetti (~20 occorrenze)
  - Aggiunto `# type: ignore[assignment]` su `adapter.close_position = fake_close`
  - Sostituiti accessi a `call_args.kwargs` con `call_args[1]` + `# type: ignore[index]`
  - Aggiunti `# type: ignore[union-attr]` su accessi a `candle_queue`/`trade_queue` dopo `_dispatch()`
  - Aggiunte type hints espliciti (`list[dict]`, `dict` parameter) su handler asincroni
  - Rimosso import inutilizzato `asyncio` e `patch`

**Decisioni chiave:**
- I test per metodi privati (`_parse_candle`, `_dispatch`, ecc.) sono intenzionali: verificano la logica interna di parsing senza dover connettere WebSocket reali. I type ignore sono la scelta corretta.
- Il test `test_parse_trade_invalid_row` verifica che un dict vuoto produca un evento con prezzi zero (comportamento voluto, non errore).

### v1.4.0 — 2026-07-02

**Milestone:** Architettura definitiva migrazione Binance -> OKX

**Completato:**
- ✅ Creata `docs/architecture/okx-migration-architecture.md` come fonte architetturale per il cutover OKX.
- ✅ Creato `docs/plans/okx-migration-implementation-plan.md` con fasi operative e ordine task.
- ✅ Creato `docs/plans/okx-migration-task-breakdown.md` con subtasks, ownership, file, test e acceptance criteria per lavoro multi-agente.
- ✅ Aggiunta EPICA OKX in `docs/TASKS.md` con TASK-1100 -> TASK-1116.
- ✅ TASK-1000 WalletOrchestrator Binance marcato come superseded/sospeso: il modello OKX margin richiede ripianificazione dopo il cutover.
- ✅ Aggiornato `docs/BACKLOG.md` con link a architettura e piano reali.
- ✅ Integrati requisiti fee/net pricing, symbol discovery, default `OKB-EUR`, dashboard balance provider-neutral e audit collector Binance/Futures.
- ✅ Avviato TASK-1100 con `scripts/test_okx_demo.py` in modalita' read-only: public time OKX OK, discovery Demo OK, auth privata bloccata da `50119 API key doesn't exist`.
- ✅ Documentato report spike in `docs/analysis/okx-demo-spike-results.md` e JSON raw sanitizzato.

**Decisioni chiave:**
- OKX diventa provider operativo primario perche' Binance non e' piu' utilizzabile per trading in Italia.
- La migrazione non sara' un porting 1:1: si introduce un layer exchange pluggable e si normalizzano adapter REST, market WS e order event stream.
- Prima del codice live e' obbligatorio TASK-1100: spike OKX Demo Trading su auth, market order, TP/SL server-side e fill WS.
- Lo short/margin viene rinviato: prima si ripristina il flusso long protetto da bracket server-side su OKX.
- La parita' fee e' requisito bloccante: fee tier certificato, target netti TP/SL, log e PnL devono restare coerenti come nel flusso Binance attuale.
- La lista coppie consentite va letta da OKX all'avvio; `OKB-EUR` e' default iniziale ma sempre validato runtime.
- Ogni agente che prende un task OKX deve usare il breakdown dettagliato e lasciare handoff puntuale.
- Primo run Demo: `OKB-EUR` e `BNB-USDC` non sono disponibili in Demo Trading; fallback EUR da discovery (`SOL-EUR`, `BTC-EUR`, `ETH-EUR`, ecc.).
- TASK-1100 e' bloccato finche' la API key demo non viene riconosciuta da OKX private API.

### v1.3.9 — 2026-07-01

**Milestone:** docs/ cleanup — rimossi file task ridondanti

**Completato:**
- ✅ **Eliminati 8 file di task ridondanti da `docs/`**:
  - `TASK_813_ALL_ACTIONS_STATUS.md` — TASK-813 già in ARCHIVE_TASKS.md
  - `TASK_813_COMPLETE_ANALYSIS.md` — TASK-813 già in ARCHIVE_TASKS.md
  - `TASK_813_FINAL_SUMMARY.md` — TASK-813 già in ARCHIVE_TASKS.md
  - `TASK_813_IMPLEMENTATION_COMPLETE.md` — TASK-813 già in ARCHIVE_TASKS.md
  - `TASK_TP_SL_NET_PRICING.md` — TASK-905 ✅ già dettagliato in TASKS.md
  - `TASK-907_bug_frontend_paused_reload.md` — TASK-907 Pending già in TASKS.md
  - `SynthTrade_TASK_Fix_Signal_Log_Decision_Types.md` — TASK-912 ✅ già in TASKS.md
  - `SynthTrade_Short_Selling_Architecture_1.md` — duplicato di SynthTrade_Short_Selling_Architecture.md
- ✅ **Verificato** che tutti i contenuti fossero già presenti in TASKS.md o ARCHIVE_TASKS.md
- ✅ **docs/ ora contiene solo**: documentazione standard loom (7 file), architettura/reference (8 file), recap sessioni (9 file), fix/summary (4 file) = 28 file .md

---

### v1.3.8 — 2026-07-01

**Milestone:** Loom rules sync + docs/ cleanup

**Completato:**
- ✅ **Spostati script Python da `docs/` a `loom/scripts/`**: `extract_tasks.py`, `parse_tasks.py` spostati nella posizione corretta secondo il framework loom
- ✅ **Rimosso `capital_allocator.py` da `docs/`**: era una vecchia versione duplicata (l'originale è in `synthtrade/backend/app/execution/capital_allocator.py`)
- ✅ **Aggiornati tutti i config IDE**: `.clinerules/loom.md`, `.cursorrules`, `.windsurfrules`, `CLAUDE.md`, `.cursor/rules/loom.mdc`, `AGENTS.md`
- ✅ **Aggiunta sezione "Documentation Update MANDATORY"** a tutti i config IDE
- ✅ **Aggiunti comandi `parse tasks` e `extract tasks`** in tutti i config
- ✅ **Verificato che `docs/` contenga solo file `.md`**

**File modificati:**
- `.clinerules/loom.md` — aggiunti comandi update/plugins/parse/extract + doc update section
- `.cursorrules` — aggiunti parse/extract + doc update section
- `.windsurfrules` — aggiunti parse/extract + doc update section
- `CLAUDE.md` — aggiunti parse/extract + doc update section
- `.cursor/rules/loom.mdc` — aggiunti parse/extract + doc update section
- `AGENTS.md` — aggiunti parse/extract
- `loom/scripts/extract_tasks.py` — copiato da docs/, aggiunto path resolution
- `loom/scripts/parse_tasks.py` — copiato da docs/, aggiunto path resolution
- Rimossi da `docs/`: `capital_allocator.py`, `extract_tasks.py`, `parse_tasks.py`

---

### v1.3.7 — 2026-06-29

**Milestone:** Fix Pylance + SessionLogHandler summary

**Completato:**
- ✅ Fix Pylance error: `_signal_log_id` possibly unbound in `router.py`
- ✅ Fix `SessionLogHandler._analyze()`: wrong key path `analysis["pipeline_decisions"]` → `analysis["trades"]["pipeline_decisions"]`
- ✅ Session Analysis Summary spostato all'inizio del dump log (prima delle entry di log)

**Dettagli TASK-887:**
- `supervisor_client.py`: usa `service.create_model_client(use_case="supervisor")`
- `llm_model_service.py`: handling dedicato per use_case "supervisor"
- `config.py`: cascade configurata con Haiku 4.5 primario, Sonnet fallback
- Costo prevedibile (~€0.09/giorno) per decisioni su capitale reale

**File modificati:**
- `docs/TASKS.md` — rimossi 69 task completati, corretto ID duplicati
- `docs/ARCHIVE_TASKS.md` — aggiunta sezione con TASK-887 e task fee reali
- `docs/STORY.md` — aggiunta versione v1.3.6

---

### v1.3.5 — 2026-06-26

**Milestone:** Archiviazione piano deploy Render - Blocco Binance su server americani

**Completato:**
- ❌ TASK-DEPLOY-001 archiviato come FALLITO
- ❌ Pianificato deploy su Render (e altre piattaforme PaaS americane) non realizzabile
- ❌ Blocco Binance API su server con IP americani impedisce funzionamento backend
- ✅ Documentazione aggiornata in TASKS.md (archivio)
- ✅ Soluzione alternativa identificata: VPS europea necessaria

**Motivo fallimento:**
- Render (e altre piattaforme PaaS americane) non possono connettersi a Binance API
- Il geo-blocco di Binance blocca le connessioni da IP americani
- L'unico modo per andare online è utilizzare una VPS europea

**File modificati:**
- `docs/TASKS.md` — TASK-DEPLOY-001 marcato come fallito e spostato in archivio

**Nota:** I file di configurazione creati per il tentativo (render.yaml, GitHub Actions workflow, etc.) sono stati mantenuti nel repository per riferimento futuro.

---

### v1.3.4 — 2026-06-25

**Milestone:** GitHub Pages fix - Correzione path artifact

**Completato:**
- ✅ Corretto path artifact da `dist` a `dist/synthtrade-ui` nel workflow
- ✅ Rimozione path filtering per trigger su tutti i push main
- ✅ Fix struttura build Angular per GitHub Pages

**File modificati:**
- `.github/workflows/deploy-frontend.yml`

---

### v1.3.3 — 2026-06-25

**Milestone:** GitHub Pages fix - Correzione baseHref

**Completato:**
- ✅ Corretto baseHref da `/synthtrade-ui/` a `/synthtrade/` in angular.json
- ✅ Allineamento con URL GitHub Pages reale: https://otto78.github.io/synthtrade/
- ✅ Fix deploy workflow trigger con path filtering corretto

**File modificati:**
- `synthtrade/frontend/synthtrade-ui/angular.json`

---

### v1.3.2 — 2026-06-25

**Milestone:** Deploy Phase 1 - Correzione URL Render backend

**Completato:**
- ✅ Aggiornato tutti i file di configurazione con URL Render corretto: `https://synthtrade.onrender.com`
- ✅ `environment.prod.ts`: apiUrl e wsUrl aggiornati
- ✅ `proxy.conf.json`: target /api e /ws aggiornati
- ✅ `.env.example`: CORS_ORIGINS aggiornato
- ✅ `.env` locale: CORS_ORIGINS aggiornato
- ✅ `render.yaml`: CORS_ORIGINS aggiornato
- ✅ `docs/TASKS.md`: TASK-DEPLOY-001 aggiornato con URL confermato

**File modificati:**
- `synthtrade/frontend/synthtrade-ui/src/environments/environment.prod.ts`
- `synthtrade/frontend/synthtrade-ui/proxy.conf.json`
- `synthtrade/backend/.env.example`
- `synthtrade/backend/.env` (locale, non committato)
- `render.yaml`
- `docs/TASKS.md`

---

### v1.3.1 — 2026-06-24

**Milestone:** Fee reali - Fase 4B: Popolare entry_commission con dato reale (TASK-886)

**Completato:**
- ✅ Backend: `place_market_order` estrae commission/commission_asset da CCXT response
- ✅ Backend: `open_position` accetta parametri opzionali entry_commission/entry_commission_asset
- ✅ Backend: flusso LIVE passa commissione reale al momento dell'apertura posizione
- ✅ Backend: flusso PAPER mantiene None (fallback a fee tier intenzionale)
- ✅ Backend: aggiunto flag `fee_tier_certificated` nello stato sessione per tracciare fallback silenziosi
- ✅ TASK-886 completato: entry_commission ora popolato con dato reale quando disponibile

**File modificati:**
- `synthtrade/backend/app/execution/exchange.py` — estrazione fee da CCXT response
- `synthtrade/backend/app/scalping/engine/position_manager.py` — parametri opzionali in open_position
- `synthtrade/backend/app/scalping/router.py` — propagazione commissione reale + flag fee_tier_certified
- `docs/TASKS.md` — TASK-886 marcato come complete

---

### v1.3.0 — 2026-06-24

**Milestone:** Fee reali - Fase 4: UI target netti TP/SL (TASK-885)

**Completato:**
- ✅ Backend: calcolo e invio `stop_loss_pct_net` e `take_profit_pct_net` nello stato posizione iniziale
- ✅ Backend: fee round-trip calcolato come `(entry_fee_rate + exit_fee_rate) * 100`
- ✅ Backend: percentuali nette = percentuali lordi - fee round-trip
- ✅ Frontend: PositionTickerComponent mostra percentuali nette con fallback a lordi
- ✅ Model: `position.model.ts` già include campi `*_pct_net`
- ✅ TASK-885 completato: UI ora mostra target fee-adjusted

**File modificati:**
- `synthtrade/backend/app/scalping/router.py` — calcolo target netti in stato iniziale
- `synthtrade/frontend/synthtrade-ui/src/app/scalping/components/position-ticker.component.ts` — display net percentages
- `docs/TASKS.md` — TASK-885 marcato come complete

---

### v0.1.0 — 2025-01-15

**Milestone:** Fase 0 — Setup & Infrastruttura completata

**Completato:**
- Struttura monorepo `synthtrade/` (backend, supabase)
- `.gitignore`, `README.md`
- Backend FastAPI: `main.py`, `config.py`, `supabase_client.py`
- Route `GET /health` → `{"status": "ok"}` ✅
- `pytest.ini` + `conftest.py` con fixture `mock_supabase`
- 4 migration SQL (strategies, trades, operation_logs, ohlcv_cache)
- `seed.sql` con 3 strategie PENDING di esempio
- `Dockerfile` + `docker-compose.yml`
- `requirements.txt` con tutte le dipendenze

**Decisioni chiave:**
- Stack: FastAPI + Supabase + ccxt (Binance) + OpenRouter AI cascade
- Frontend: Angular 17+ con dark terminal UI (lightweight-charts)
- AI: cascade 4 modelli free OpenRouter + fallback Claude Haiku pagante
- Paper trading obbligatorio fino alla Fase 6
- TDD con pytest per backend, Jest per frontend

### v1.1.0 — 2026-06-09

**Milestone:** Scalping pipeline restore + logging visibility fix

**Completato:**
- Session restore ora avvia automaticamente il pipeline WS (BinanceWSClient + ExecutionLoop)
- Aggiunto parametro `restore_mode` a `_start_ws_broadcast()` per saltare INSERT DB su restore
- Fix logger invisibili su Windows/uvicorn: handler forzato sui moduli scalping
- Aggiunto logging periodico "no data received" a 30s/60s
- SupervisorScheduler avviato anche in restore_mode

**File modificati:**
- `synthtrade/backend/app/main.py` — `_restore_scalping_session()` Step 5
- `synthtrade/backend/app/scalping/router.py` — restore_mode, logging watchdog
- `synthtrade/backend/app/core/logging.py` — handler forzato per moduli scalping

---

### v1.0.1 — 2026-05-07

**Milestone:** Standardizzazione porte di sviluppo

**Completato:**
- Backend configurato sulla porta 8008 (FastAPI, Docker, Docker Compose)
- Frontend configurato sulla porta 4208 (Angular, package.json, proxy)
- Aggiornata documentazione (README.md, PROJECT.md, HANDOFF.md)
- Allineate variabili d'ambiente (.env.example)

### v1.1.0 — 2026-05-07

**Milestone:** Fase 7 — Miglioramenti Evolutivi UX

**Completato:**
- ✅ **7.1 Persistenza & Scadenza Strategie**: Migration 005 con `expires_at`, trigger automatico 7gg, funzione cleanup. Backend/frontend già implementati per gestione scadenza e auto-pulizia. Migrazione applicata su Supabase Cloud (colonna + funzioni + trigger).
- ✅ **7.2 Gestione Strategie Attive**: Dialog conferma Stop, pagina Monitoraggio Real-time con polling 5s, equity curve, P&L, Win Rate.
- ✅ **7.3 Strategie Completate**: UI Accordion con intestazione (nome, data, P&L, performance%), dettaglio trade espandibile, statistiche, equity curve, pulsante Esporta Report.
- ✅ **7.4 Dashboard**: Ordinamento asset per valore EUR decrescente, colonna % Portfolio, Card strategia attiva con Score/Budget/Rischio AI, navigazione one-click alla vista Monitoraggio.
- Fix build frontend (errori TS, duplicati, unused imports) per bundle pulito.

### v1.1.1 — 2026-05-08

**Milestone:** Fix workflow strategie — persistenza, approvazione, scadenza

**Completato:**
- ✅ **Persistenza strategie su DB**: Le strategie generate vengono ora salvate immediatamente su Supabase con status `PENDING` e `expires_at = now + 7gg` (in `pipeline.py`). Non più solo in memoria.
- ✅ **Ricarica PENDING dal DB**: Il tab GENERAZIONE carica le strategie PENDING dal DB all'avvio della pagina. Navigando via e tornando, le strategie sono ancora lì.
- ✅ **Approvazione diretta**: `saveAndApprove()` approva l'ID già presente su DB invece di ricreare la strategia.
- ✅ **Fix BUG approvazione**: Non cancella più tutte le strategie generate dopo averne approvata una.
- ✅ **Transizione ACTIVE→EXPIRED**: Le strategie ACTIVE scadute ora transitano a EXPIRED (non solo cancellazione PENDING).
- ✅ **Tab COMPLETATE**: Mostra solo strategie EXPIRED, non più REJECTED.
- ✅ **Migration 006**: Fix `expires_at` NULL su tutti i record esistenti, funzione cleanup aggiornata.

**Decisioni chiave:**
- Le strategie generate vengono salvate su DB subito per garantire persistenza tra navigazioni e sessioni
- La cleanup PENDING scadute cancella i record, mentre ACTIVE scadute diventano EXPIRED per tracciabilità

### v1.2.6 — 2026-05-15

**Milestone:** Refactor Supabase Client & Dependency Injection (TASK-033)

**Completato:**
- ✅ **Supabase Singleton**: Il client Supabase è ora un singleton gestito con `@lru_cache` in `app/db/supabase_client.py`.
- ✅ **FastAPI Dependency**: Implementata la dependency `get_db` in `app/dependencies.py` per iniettare il client nelle route.
- ✅ **Fix Dummy Client**: Potenziato il `_DummyTable` per supportare il metodo `.single()`, risolvendo crash negli endpoint di metriche durante i test.
- ✅ **Test di regressione**: Risolti problemi di importazione e formato delle risposte nei test di integrazione (`test_pipeline_metrics.py`).

**Decisioni chiave:**
- Utilizzo della Dependency Injection di FastAPI come standard per l'accesso al database, facilitando il testing e il mocking.
- Unificazione del comportamento dei dummy client tra lo stub di root e quello del backend.

### v1.2.7 — 2026-05-15

**Milestone:** MarketData Service Refactor - OhlcvRepository (TASK-038)

**Completato:**
- ✅ **OhlcvRepository**: Creazione di un repository dedicato per la tabella `ohlcv_cache` in `app/db/repositories/`.
- ✅ **Dependency Injection**: Aggiunta di `get_ohlcv_repo` in `app/dependencies.py`.
- ✅ **Test di copertura**: Test unitari per il repository (`tests/test_task_038.py`) con mock Supabase.

---

## 🎯 Roadmap

### v0.2.0 — Core Engine
- [x] `indicators.py` (EMA, RSI, Bollinger + signal functions)
- [x] `strategy_generator.py` (prodotto cartesiano parametri)
- [x] `backtester.py` (simulazione OHLCV con fee/slippage)
- [x] `ranker.py` (score composito con filtri hard)
- [x] `market_data.py` (fetch Binance + cache Supabase)
- [x] `run_pipeline.py` (pipeline batch completa)

### v0.3.0 — Backend API
- [x] Auth JWT
- [x] API strategies, dashboard, logs
- [x] WebSocket live feed

### v0.4.0 — Frontend Angular ✅
- [x] Dark terminal UI completa
- [x] 3.0 Bootstrap (Angular, Jest, proxy, environments, eslint, prettier)
- [x] 3.1 Design Tokens (_variables, _mixins, _reset, _animations, theme-dark)
- [x] 3.2 Modelli TypeScript (user, strategy, trade, dashboard, log, ws-message)
- [x] 3.3 Interceptors & Guards (auth, error, authGuard, noAuthGuard)
- [x] 3.4 Services (TokenStorage, Auth, Strategy, Dashboard, Log, WebSocket)
- [x] 3.5 Shared Components & Pipes (StatCard, BadgeStatus, PriceTicker, ConfirmDialog, EmptyState, RelativeTime, FormatNumber, SignedNumber)
- [x] 3.6 Layout Shell (Sidebar, Topbar, AppShell)
- [x] 3.7 Routing (lazy loading, authGuard, noAuthGuard, redirect)
- [x] 3.8 Pagine (Login, Dashboard, Strategies, ActiveTrade, Logs)

### v0.5.0 — Execution Engine + AI ✅ (parziale)
- [x] `execution/schemas.py` (Signal, OrderRequest, OrderResult, RiskCheckResult, PositionSnapshot)
- [x] `execution/risk_manager.py` (RiskConfig, validate_signal, SL/TP calc) — 13 test
- [x] `execution/order_tracker.py` (open/close/get positions, unrealized P&L) — 7 test
- [x] `execution/signal_resolver.py` (SignalResolverProtocol + DefaultSignalResolver) — 5 test
- [x] `execution/execution_engine.py` (process_signal, check_exit_conditions) — 11 test
- [x] `scheduler/jobs.py` (APScheduler: pipeline, monitor, heartbeat) — 4 test
- [x] 4.6 Integration Tests (pipeline completa, stop loss, risk reject, drawdown) + `api/trades.py`

### v0.6.0 — AI Evaluator ✅
- [x] `ai/schemas.py` (MarketContext, StrategyContext, EvalPromptInput, EvalResult, ModelResponse)
- [x] `ai/context_builder.py` (build_market_context, detect_market_regime) — 7 test
- [x] `ai/prompt_builder.py` (build_prompt, build_system_prompt, token budget) — 6 test
- [x] `ai/model_client.py` (httpx, cascade, retry backoff, fallback, custom errors) — 7 test
- [x] `ai/eval_parser.py` (parse_eval_result, EvalParseError, markdown strip) — 8 test
- [x] `ai/cache.py` (get_cached_eval, save_eval, TTL Supabase) — 4 test
- [x] `ai/evaluator.py` (evaluate_strategy, evaluate_all con Semaphore) — 7 test
- [x] `api/eval.py` (GET eval, POST refresh, BackgroundTasks) — 4 test
- [x] Integrazione in `run_pipeline.py` (PROMOTE/DEMOTE/HOLD logic) — 4 test
- [x] Integration tests (happy path, fallback, cache hit, JSON malformato, all models down) — 5 test

### v2.0.0 — Modulo Scalping (Signal Intelligence) 🚀

**2026-06-24 — TASK-879 completato:**
- Fix hardcoded fees in UDS reconnect sync function
- Ora usa commissioni reali di entrata (se disponibili da WebSocket) e fee tier per uscita attesa
- Conversione automatica BNB→USDC quando necessario
- [ ] **Fase 1: Foundation & Models** (TASK-801 -> 804)
- [ ] **Fase 2: Signal Intelligence Collectors** (TASK-805 -> 810)
- [ ] **Fase 3: Engine & Signal Aggregation** (TASK-811 -> 813)
- [ ] **Fase 4: Fast Execution Engine (L1)** (TASK-814 -> 817)
- [ ] **Fase 5: Opportunity Monitor (AI News)** (TASK-818 -> 820)
- [ ] **Fase 6: AI Supervisor v2.0 (L2)** (TASK-821 -> 823)
- [ ] **Fase 7: Frontend Scalping Dashboard** (TASK-824 -> 828)
- [ ] **Fase 8: Backtest & Validation** (TASK-829 -> 832)

### v1.0.0 — Hardening & Deploy

- [ ] Supabase Cloud: RLS, Realtime, Auth
- [ ] Docker multi-stage: backend (python:3.12-slim) + frontend (node:20-alpine + nginx:alpine)
- [ ] docker-compose.prod.yml con network interna, logging json-file
- [ ] Nginx: reverse proxy, HTTPS, WebSocket upgrade, security headers, rate limiting
- [ ] Certbot / Let's Encrypt con rinnovo automatico
- [ ] VPS Ubuntu 24.04: utente non-root, UFW, Docker, unattended-upgrades
- [ ] Logging strutturato JSON con python-json-logger + request_id middleware
- [ ] Error handling globale con eccezioni custom e handler FastAPI
- [ ] scripts/deploy.sh + scripts/rollback.sh + scripts/smoke_test.sh
- [ ] Checklist pre-go-live (CORS, RLS, no hardcoded secrets, bundle size)

---

## 📊 Stato dei Moduli Architetturali

> Aggiornato al 2026-07-01. Fonte: `docs/MASTER_RECAP.md` (consolidamento 20-28/06/2026) + verifica su task completati.

| Modulo | Stato | Note |
|---|---|---|
| **Execution Engine (L1)** | 🟢 Operativo, con bug noti | SL/TP/Max Daily Loss reali; regressione 27-28/06 in rollback |
| **Risk Manager** | 🟡 Parziale | SL, TP, Max Daily Loss reali; Leverage e Max Drawdown decorativi (per design attuale) |
| **Signal Intelligence Layer** | 🔴 30% funzionante | Solo Fear&Greed, Long/Short Ratio, Open Interest attivi; Funding Rate, CVD, Sentiment, Whale, On-Chain non funzionanti |
| **Strategie tecniche** | 🟢 4+1 implementate | EMA Cross, Momentum Base, RSI+Bollinger, VWAP Reversion + stoch_rsi_bb_squeeze |
| **Regime Detector** | 🔴 Inaffidabile | Misclassifica breakdown con volume come ranging — root cause di più sintomi |
| **AI Supervisor** | 🟡 Operativo con limiti | Cooldown 20min e whitelist regime→strategia fixati; bias outcome_label noto |
| **Short Selling** | 🔴 Zero implementazione | Architettura completa a 4 fasi pronta, nessun codice scritto |
| **Fee/PnL transparency** | 🟡 Strutturalmente fixato | Fix principali applicati, verifica empirica end-to-end mancante |
| **Trailing Stop Loss** | 🔴 Solo proposta | Nessun codice, nessuna decisione su collocazione |
| **Market Structure (S/R)** | 🔴 Solo proposta | MarketStructureCollector non esiste ancora |
| **Wallet Orchestrator** | 🔴 Solo snippet | Non scritto nel progetto reale |
| **Frontend Angular** | 🟡 Funzionale con bug noto | Sync bug strategia selezionata/eseguita mai fixato |

### Bug aperti noti

Vedi `docs/TASKS.md` sezione "🎯 Task da Investigare (da MASTER_RECAP.md)" per 20 bug da verificare (TASK-INVEST-001 → 020).

---

## 📊 Metriche

### Progresso Generale

- **Task completati:** 435 (Fase 7 completata)
- **Test passati:** 214 backend + 116 frontend = 330 totali
- **Test coverage:** ~82% backend, ~85% frontend core/shared

---

## 📝 Decisioni Architetturali

**2026-05-07 — Fase 7: Persistenza, Dashboard Avanzata, Fix Build**
- Problema: Strategie non avevano scadenza, Dashboard mancava di card strategia attiva e ordinamento asset, build frontend con errori.
- Soluzione: Migration 005 per `expires_at`, trigger auto cleanup. Dashboard con card interattiva e asset ordinati per exposure. Fix di tutti gli errori TS.
- Beneficio: Strategie auto-pulite dopo 7gg, UX dashboard migliorata, build pulito.

**2026-05-06 — Enhanced Strategy Generation & Rich UI**
- Problema: Varianti generate tutte uguali e mancanza di informazioni per l'utente nella scelta.
- Soluzione: Refactor di `strategy_generator.py` per generare varianti reali basate su griglie di parametri, timeframe e asset diversi. Implementata una UI "Rich Card" con descrizioni, tag dei parametri e punteggio AI.
- Beneficio: L'utente può ora confrontare le strategie in base a dati reali e punteggi suggeriti dall'AI.

**2026-05-06 — Integrazione UI Generatore Intelligente e Fix Networking**
- Problema: Necessità di un'interfaccia Angular per il nuovo generatore e conflitti di porte locali.
- Soluzione: Implementati componenti `StrategyRequestForm` e `GenerationProgress`. Spostato Frontend su porta 4201 e Backend su porta 8001 con prefisso `/api`.
- Beneficio: UX fluida per la creazione di strategie e ambiente di sviluppo isolato da altre app.

**2026-05-06 — Integrazione Framework Loom**
- Problema: Necessità di un workflow standardizzato per task management e TDD.
- Soluzione: Configurato framework Loom (DOE Architecture) e migrato tutti i task esistenti in `docs/TASKS.md` al nuovo formato `### TASK-XXX`.
- Beneficio: Piena compatibilità con gli script di automazione `loom/scripts/task.py` e tracciamento rigoroso dello stato.

---

## 📝 Decisioni Architetturali (Precedenti)

**2025-01-15 — Cascade AI con 5 tier**
- Problema: costo AI per valutare 200–800 strategie/giorno
- Soluzione: 4 modelli free OpenRouter in cascade, fallback Haiku pagante
- Costo worst case: ~$0.01/pipeline (solo se tutti i free falliscono)

**2025-01-15 — Cache OHLCV su Supabase**
- Problema: rate limit Binance (1200 weight/min)
- Soluzione: cache su tabella `ohlcv_cache`, fetch solo delta mancante
- Beneficio: riduce chiamate Binance del ~95% dopo il primo fetch

**2025-01-15 — Paper trading obbligatorio**
- Nessun ordine reale fino alla Fase 6 esplicita
- `PAPER_TRADING=true` in `.env` come default

---

### v1.1.2 — 2026-05-08

**Milestone:** Fix valutazione strategie — estimated_profit_pct/eur

**Completato:**
- ✅ **Migration 007**: Aggiunte colonne `estimated_profit_pct FLOAT` e `estimated_profit_eur FLOAT` alla tabella `strategies`
- ✅ **Fix `pipeline.py`**: `estimated_profit_pct` e `estimated_profit_eur` ora salvati nel row insert su DB
- ✅ **Fix `strategies.py`**: `list_strategies()` ora seleziona tutti i campi di valutazione (`estimated_profit_pct`, `estimated_profit_eur`, `description`, `pair`, `timeframe`, `params`, `ai_note`, `ai_strengths`, `ai_warnings`)
- ✅ Migration applicata su Supabase Cloud

**Decisioni chiave:**
- Le stime di profitto vengono salvate direttamente sul DB durante la generazione, non solo in memoria
- La SELECT di `list_strategies` è stata espansa da 9 a 18 campi per garantire la visibilità di tutti i dati di valutazione

### v1.1.3 — 2026-05-08

**Milestone:** Fix flusso UI generazione, nome personalizzato strategie, build error

**Completato:**
- ✅ **Spinner attesa**: Aggiunto `checkingSaved` signal con spinner "Verifico se ci sono strategie salvate..." durante il caricamento dal DB
- ✅ **Welcome card condizionale**: Appare solo dopo il caricamento e se non ci sono strategie salvate
- ✅ **Pulsante rinominato**: "Nuova Ricerca" → "Genera Nuove Strategie"
- ✅ **Cancellazione PENDING su generazione**: `startNewGeneration()` cancella tutte le PENDING dal DB prima di mostrare il form
- ✅ **Migration 008**: `ALTER TABLE strategies ADD COLUMN custom_name TEXT` applicata su Supabase Cloud
- ✅ **Nomi automatici AI**: Il generator crea nomi simpatici per template (es. "Il Seguace su BTC", "Mr RSI su ETH", "Lo Squartatore su SOL")
- ✅ **Override utente**: Il campo "Nome Personalizzato" nel form sovrascrive il nome automatico se compilato
- ✅ **Nome visibile in tutti i tab**: GENERAZIONE, APPROVATE, ATTIVE, COMPLETATE
- ✅ **Fix build TS2559**: Risolta collisione `MonitorData` tra interfaccia globale e locale

**Decisioni chiave:**
- I nomi personalizzati sono generati dall'AI in base al template, non dall'utente (ma l'utente può sovrascriverli)
- La cancellazione delle PENDING su "Genera Nuove Strategie" evita accumulo di strategie orfane

---

## 🎯 Prossimi Task (da BACKLOG)

### TASK-DASH-PNL — Fix P&L Dashboard sempre a 0
**Priorità:** Alta
- Verificare che l'API Binance restituisca il P&L reale
- Fixare il calcolo/visualizzazione del P&L nella Dashboard
- Aggiungere logging per debug del dato

### TASK-DASH-STRAT — Lista strategie attive riassuntiva in Dashboard
**Priorità:** Alta
- Mostrare tutte le strategie attive (non solo una) con: nome, budget iniziale, data avvio, saldo attuale, stima profitto %, risultato corrente
- Pulsante "Vedi Dettaglio" che porta alla pagina strategie attive

### TASK-DASH-GRAFICO — Grafico andamento saldo mensile in Dashboard
**Priorità:** Media
- Aggiungere grafico con l'andamento del saldo a scala mensile
- Usare lightweight-charts o barre semplici

### TASK-TRADE-PAGE — Refactoring pagina Active Trade
**Priorità:** Alta
- Mostrare lista di tutti i trade in corso e sotto quelli conclusi
- Ogni trade deve mostrare: nome strategia, asset, direzione, prezzo entry/exit, P&L, data
- Filtro dropdown per strategia
- Il pulsante "Monitora" nelle card strategie deve portare qui con filtro pre-attivato

### TASK-AUDIT-GEN — Audit processo generazione strategie
**Priorità:** Alta
- Aggiungere logging dettagliato su ogni fase: analisi mercato, creazione, validazione, backtest
- Verificare che i dati di mercato vengano caricati correttamente da Binance
- Verificare che le analisi AI siano basate su dati reali, non allucinate
- Aggiungere endpoint `/api/pipeline/audit/{generation_id}` per tracciare ogni step

### TASK-AUDIT-ACTIVATE — Audit processo attivazione ed esecuzione strategie
**Priorità:** Critica
- Analizzare il flusso di attivazione: APPROVED → ACTIVE → execution
- Verificare che all'avvio ci sia disponibilità economica reale nel saldo
- Testare l'esecuzione reale dei trade (paper trading)
- Verificare che stop loss / take profit vengano piazzati correttamente
- Aggiungere test di integrazione per l'intero ciclo vita

---

### v1.2.0 — 2026-05-12

**Milestone:** 🔴 Fix Allucinazioni — Backtest reale sostituisce random.uniform()

**Completato:**
- ✅ **Strategy Generator riscritto**: Rimosso `import random`, `random.uniform()`, `random.choice()`, `random.shuffle()`
- ✅ **Backtest reale**: `generate_for_request()` ora scarica OHLCV da Binance (90gg), esegue backtest reale, calcola score via `compute_score()`
- ✅ **StrategyParams aggiornato**: Rinominato `ai_score` → `score` (range [0,1]), aggiunti campi backtest: `backtest_pnl`, `backtest_win_rate`, `backtest_sharpe`, `backtest_drawdown`, `backtest_trades`, `data_source`
- ✅ **Nomi deterministici**: Rimossi nomi casuali tipo "Il Seguace", "Rompiballe". Usa titolo derivato da template + pair
- ✅ **Pipeline.py**: Salva `backtest` completo nel DB, WS progress events (fetching_market_data, saving), gestione lista vuota con messaggio utente
- ✅ **Test**: 21 test PASS (generator, constrained, random_proof, e2e_pipeline). Zero regressioni nella suite unità (152/157)

**Decisioni chiave:**
- Le strategie generate via UI ora si basano su dati storici reali Binance, non su valori casuali
- Score nel range [0,1] da `compute_score()` invece di range arbitrario [70,99]
- I nomi delle strategie ora sono deterministici invece di random.choice()
- Cache OHLCV per (pair, timeframe) evita N chiamate API per lo stesso asset
- Se backtest fallisce o score è None, la variante viene esclusa silenziosamente

---

### v1.2.1 — 2026-05-13

**Milestone:** 🔴 Fix Profitti Irrealistici — Soglie Ranker Ottimizzate

**Completato:**
- ✅ **Diagnosi profitti irrealistici**: Analisi su 8 asset top marketcap (BTC, ETH, SOL, BNB, ADA, DOT, LINK, AVAX) con 180gg di dati
- ✅ **Scoperta chiave**: Timeframe 15m perde su TUTTI gli asset (-43% a -60%). Solo RSI 1h su altcoin è profittevole (+10-20%). RSI 4h produce Sharpe 27+ con soli 5-9 trades — artefatto statistico che causava profitti "finti"
- ✅ **Ranker**: min_trades 8→15, min_sharpe 0.3→0.0, max_drawdown 22.0→40.0, min_pnl 2%→0%
- ✅ **Generator**: lookback 180→60gg, pairs default BTC/ETH/SOL/BNB, timeframes rimosso 15m
- ✅ **Test pipeline**: 5 strategie con P&L medio +16.78%, drawdown 11.1%, trades 16 — realistico per crypto

**Decisioni chiave:**
- 60 giorni di lookback sono sufficienti per significatività statistica (vs 180 che includeva trend obsoleti)
- Quattro asset default (BTC, ETH, SOL, BNB) aumentano le opportunità di trovare strategie valide
- Timeframe 1h è il miglior compromesso segnale/rumore per crypto
- Soglia min_trades=15 garantisce significatività statistica senza escludere strategie valide
- max_drawdown=40% riflette la volatilità reale delle crypto (drawdown 30-40% è normale)

---

## [1.2.3] — 2026-05-14

**Milestone:** Completamento Epica Execution & Monitoraggio Real-time

**Completato:**
- ✅ **TASK-400 - 403**: Implementazione `CapitalAllocator` e attivazione operativa delle strategie con acquisto asset su Binance.
- ✅ **TASK-414 - 416**: Monitoraggio real-time via WebSocket. Broadcasting automatico di eventi di trade e aggiornamento live del P&L.
- ✅ **TASK-417**: Endpoint `/trades/active` con join strategie via resource embedding di Supabase per una visualizzazione avanzata.
- ✅ **TASK-406 - 413**: Finalizzazione motore di esecuzione (`StrategyRunner`, `ExecutionEngine`, `OrderTracker`) e gestione dello stop operativo.

**Decisioni chiave:**
- Utilizzo della Dependency Injection in FastAPI per migliorare la testabilità degli endpoint critici.
- Broadcasting proattivo dal motore di esecuzione per garantire una UI sempre sincronizzata.
- Unificazione del formato dei messaggi WS per semplificare il consumo lato frontend.

---

### v1.2.2 — 2026-05-14

**Milestone:** Implementazione Peak-to-Trough Drawdown (TASK-415)

**Completato:**
- ✅ **Migration 009**: Aggiunta colonna `peak_equity_usdt` alla tabella `strategies`.
- ✅ **OrderTracker**: Implementato `get_realized_pnl` e potenziato `get_open_positions` per filtri per strategia.
- ✅ **StrategyRunner**: Integrato calcolo dinamico dell'equity (Realized + Unrealized PnL) e aggiornamento automatico del picco massimo per un calcolo accurato del Drawdown.

**Decisioni chiave:**
- Il drawdown viene ora calcolato dal punto di massimo profitto raggiunto (Peak-to-Trough) anziché dal capitale iniziale, garantendo una protezione più robusta dei profitti accumulati.

### v1.2.4 — 2026-05-14

**Milestone:** Fix Operativi Testnet — Dashboard, Trade View, Stop

**Completato:**
- ✅ **Bug 1 — Dashboard pending**: Aggiunto timeout (15s) + fallback OFFLINE in `dashboard.service.ts`. La dashboard ora non resta più bloccata su "loading" se il backend è lento/offline.
- ✅ **Bug 2 — Trade attivi non visibili**: Riscritta `active-trade.page.ts` per supportare MULTIPLE strategie attive con caricamento dati via `GET /api/strategies/active/pnl` e `GET /api/monitor/{id}`. Aggiunte interfacce `ActivePnlItem`, `MonitorStrategyInfo` in `strategy.service.ts`. Fix calcolo P&L cumulativo in `monitor.py`.
- ✅ **Bug 3 — Stop non chiude trade su DB**: La chiusura trade su DB ora avviene SEMPRE, indipendentemente dal successo/failure di `exchange.close_position()`. Se exchange fallisce, mantiene il prezzo entry e P&L=0, ma i trade passano comunque a status CLOSED.

**Decisioni chiave:**
- La dashboard deve essere resiliente al fallimento del backend — timeout + fallback anziché loading infinito
- I trade vengono chiusi su DB **sempre**, anche se l'exchange non risponde, per evitare trade orfani
- La pagina Active Trades ora supporta n strategie attive in contemporanea, non più una sola

---

### v1.2.5 — 2026-05-14

**Milestone:** Stato Attuale EPIC-400 Execution Epic

**EPIC-400 Execution Epic completato all'85%** (42 task Done su 49 totali della sezione dedicata EPIC-400/Fase 4)

**Completato oggi:**
- ✅ Fix duplicato status TASK-425 in TASKS.md (era "Pending" + "Done ✅", ora corretto a "Done ✅")
- ✅ Sync documentazione: TASKS.md e STORY.md allineati

**EPIC-400 Execution Epic — Riepilogo Task:**
- **Fase A (Allocazione Capitale)**: ✅ 4/4 completati (TASK-400 → 403)
- **Fase B (Loop Esecuzione)**: ✅ 7/7 completati (TASK-404 → 410)
- **Fase C (Stop Strategia)**: ✅ 3/3 completati (TASK-411 → 413)
- **Fase D (P&L Real-time)**: ✅ 4/4 completati (TASK-414 → 417)
- **Fase E (Frontend Active Trades)**: 🔴 1/4 completati (solo TASK-420 Done; TASK-418, 419, 421 Pending)
- **Fase F (P&L Live Strategie)**: ✅ 3/3 completati (TASK-422 → 424)
- **Fase G (Multi-Crypto)**: 🟡 1/3 completati (TASK-425 Done, TASK-426 In Progress, TASK-427 Pending)
- **Fase H (Stabilizzazione E2E)**: 🔴 0/3 completati (TASK-428, 429, 430 tutti Pending)
- **Bug Fix**: ✅ 1/1 completato (TASK-431)

---

---

### v1.2.8 — 2026-05-19

**Milestone:** 🔴 Fix saldo dashboard — 1500€ fittizio → saldo reale testnet

**Completato:**
- ✅ **Performance `get_total_balance_eur()`**: Riscritta con `fetch_tickers()` batch invece di `fetch_ticker()` individuale per ogni asset. Tempo di esecuzione: da **240 secondi** a **4.7 secondi** per 433 asset.
- ✅ **Fallback hardcoded 1500€ rimosso**: La dashboard ora mostra il saldo reale (anche 0.0) invece di iniettare un valore fittizio quando il saldo è 0 o c'è timeout.
- ✅ **Test aggiornato**: `test_dashboard_fallback_when_balance_zero` rinominato in `test_dashboard_shows_real_balance_when_zero` con asserzione 0.0.

**Decisioni chiave:**
- `fetch_tickers()` in una singola chiamata batc h invece di N chiamate individuali evita rate-limit e timeout
- Il saldo reale (anche 0) è sempre preferibile a un valore fittizio — l'utente deve vedere la verità del proprio conto

---

### v1.2.9 — 2026-05-20

**Milestone:** Diversificazione strategie — da 3 a 8 template con nomi descrittivi

**Completato:**
- ✅ **Da 3 a 8 template**: aggiunti `trend_ema_fast` (Fast EMA Momentum), `mean_reversion_rsi_aggressive` (Aggressive RSI Reversal), `breakout_bb_tight` (Bollinger Squeeze), `momentum_macd` (MACD Momentum), `scalp_short_term` (Short-Term Scalping)
- ✅ **Più varietà di parametri**: ogni template ha ora più combinazioni (es. ema_fast da [10,20] → [10,20,50])
- ✅ **Range durate ampliato**: da 3gg (scalp) a 30gg (trend), coprendo ogni esigenza di trading
- ✅ **Filtri rilassati**: tolleranza durata 80% (era 50%), fallback su 3 template invece di 1 solo
- ✅ **Nomi descrittivi**: tutti i template titolo umano (es. "Trend Following EMA — BTC/USDT 1h" invece di "trend_ema BTC/USDT 1h")
- ✅ **Fix `run_pipeline.py`**: titolo ora usa `strategy.title` invece di concatenare template ID tecnico
- ✅ **Nuove funzioni indicatore**: `signal_macd_crossover`, `signal_ema_dual_crossover`, `macd()`
- ✅ **Registry aggiornato**: tutti gli 8 template registrati in `StrategyRegistry._load_defaults()`
- ✅ **Prompt AI esteso**: `request_enricher.py` aggiornato con tutti gli 8 template

**Decisioni chiave:**
- Aumentare i template da 3 a 8 garantisce che anche con filtri attivi, l'utente veda sempre strategie diversificate
- La tolleranza durata 80% evita che template validi vengano esclusi per piccole differenze di durata
- I titoli descrittivi migliorano UX: l'utente capisce subito la logica della strategia

---

### v1.3.0 — 2026-05-20

**Milestone:** Modalità TEST/LIVE, separazione dati, API key, toggle UI (TASK-431)

**Completato:**
- ✅ **Separazione dati TEST/LIVE**: Aggiunta colonna `trading_mode` a `strategies`, `trades` e `operation_logs` con filtri automatici nelle query di repository.
- ✅ **ExchangeFactory centralizzato**: Gestione dinamica delle chiavi API (live vs testnet) e reconnect a runtime senza riavvio del server.
- ✅ **Toggle UI e indicatore topbar**: Visualizzazione dello stato attuale (TEST/LIVE) nella barra di navigazione con switcher sicuro (conferma obbligatoria per passare a LIVE).
- ✅ **Endpoint `/api/config/mode`**: Permette la lettura e il cambio della modalità operativa a runtime, con protezioni di sicurezza.

**Decisioni chiave:**
- La modalità LIVE richiede l'abilitazione esplicita tramite variabile d'ambiente `ALLOW_LIVE_MODE=true` per prevenire attivazioni accidentali.
- Il database usa la colonna `trading_mode` per isolare in modo sicuro i trade e le strategie reali da quelle di test.

---

### v1.3.1 — 2026-05-22

**Milestone:** Fix favicon — saetta vettoriale al posto di Angular e emoji

**Completato:**
- ✅ **Favicon SVG**: Sostituito `<text>⚡</text>` con path vettoriale della saetta per compatibilità browser
- ✅ **Fallback .ico rimosso**: Rimosso `<link rel="alternate icon" href="favicon.ico">` da `index.html` (mostrava ancora logo Angular)
- ✅ **Budget warning fix**: `anyComponentStyle` aumentato da 8kB a 10kB in `angular.json` per evitare warning build

**Decisioni chiave:**
- Le favicon SVG con emoji (`<text>⚡</text>`) non sono supportate universalmente come favicon; serve un path vettoriale reale

### v1.3.2 — 2026-05-22

**Milestone:** TASK-800 completato — ScalpingSettings in config.py

**Completato:**
- ✅ **ScalpingSettings**: Classe Pydantic in `app/config.py` con 13 parametri scalping (rischio, timeframe, intelligenza, supervisor, opportunity)
- ✅ **settings.scalping**: Property cached su Settings singleton per accesso centralizzato
- ✅ **.env aggiornato**: Sezione `# Scalping Module v2.0` con tutte le variabili documentate
- ✅ **30/30 test PASS**: Default values, override via env, type coercion, access via settings.scalping
- ✅ **Fix .env bug**: Commento sulla stessa riga di `CRYPTOPANIC_API_KEY` parsato come valore — spostato su riga separata

**Decisioni chiave:**
- `ScalpingSettings` è una classe separata da `Settings` per isolamento delle responsabilità, accessibile via `settings.scalping`
- Caching con `@cached_property` per evitare ricreazione dell'istanza a ogni accesso

---



### v1.1.0-hotfix.1 — 2026-06-10

**Milestone:** 🔴 Fix persistenza sessione scalping — saldo, trade history, posizione aperta

**Completato:**
- ✅ **Bug 1 — Saldo 10,000 falso**: `_restore_scalping_session()` ora inizializza `BinanceExchangeAdapter` e fa `fetch_balance()` da Binance per sessioni live, mostrando il saldo reale invece del default 10,000
- ✅ **Bug 2 — Lista trade vuota**: Ora carica fino a 200 trade storici da `scalping_trades` su DB e popola `trade_history` in memoria
- ✅ **Bug 3 — Performance vuota**: Stessa causa del Bug 2 — risolto, ora la performance è calcolata sui dati reali
- ✅ **Bug 4 — Trade notturni persi**: Aggiunta persistenza posizione aperta su DB (`status='open'`) subito dopo `pm.open_position()`. Alla chiusura UPDATE della stessa riga (non più INSERT). Al restore sessione, la posizione aperta viene ricaricata in memoria.
- ✅ **Migration 010**: Aggiunta colonna `trade_value FLOAT` a `scalping_sessions`
- ✅ Funzione `_save_open_position_to_db()` per INSERT posizione aperta
- ✅ Funzione `_update_closed_position_in_db()` per UPDATE chiusura (UPDATE vs INSERT)
- ✅ Step 7 in `_restore_scalping_session()`: carica posizione aperta da DB

**File modificati:**
- `synthtrade/backend/app/main.py` — `_restore_scalping_session()` resa async, Steps 5-8
- `synthtrade/backend/app/scalping/router.py` — funzioni helper persistenza, chiamate dopo open_position

**Ultima modifica:** 2026-06-10 — Cline (TASK-823 bug fix persistenza)

---

### v1.3.8 — 2026-07-01

**Milestone:** TASK-911 completato — Epica Memory & Learning chiusa

**Completato:**
- ✅ TASK-911: Nuovo endpoint GET `/scalping/supervisor/history?session_id={session_id}`
- ✅ Nuovo frontend `SupervisorApiService` per fetch storico decisioni
- ✅ `SupervisorLogComponent` ora carica lo storico al mount e su cambio sessione
- ✅ Visualizzazione decisioni bloccate (`was_applied=False`, `blocked_reason`)
- ✅ Epica Memory & Learning completamente implementata livelli 1-3 + frontend

**File creati/modificati:**
- `synthtrade/backend/app/scalping/router.py` — nuovo endpoint GET `/supervisor/history`
- `synthtrade/frontend/synthtrade-ui/src/app/scalping/services/supervisor-api.service.ts` — nuovo service
- `synthtrade/frontend/synthtrade-ui/src/app/scalping/components/supervisor-log.component.ts` — caricamento storico + display blocked
- `synthtrade/frontend/synthtrade-ui/src/app/scalping/services/scalping-ws.service.ts` — nuovi campi `was_applied`, `blocked_reason`

**Verifica:** Aprire la dashboard con una sessione che ha decisioni supervisor in `supervisor_memory`. La scheda SupervisorLog mostra lo storico al caricamento. Le nuove decisioni via WS si accodano in cima.

---

### v2.0.0-alpha.5 — 2026-05-27

**Milestone:** Scalping Module - Fix Frontend UI (14 bug fix)

**Completato:**
- ✅ **Fix Binance WS URL**: URL combinata `/stream?streams=` → connessioni separate `/ws/SYMBOL@kline` e `/ws/SYMBOL@trade` per compatibilità Testnet
- ✅ **Fix dispatch combined-stream**: Unwrap envelope `{stream, data}` per messaggi Binance
- ✅ **Fix proxy.conf.json**: Aggiunto `"ws": true` alla regola `/api` per WebSocket upgrade
- ✅ **Fix WS endpoint route**: Spostato da `/api/scalping/ws/scalping` a `/ws/scalping`
- ✅ **Fix initial session state**: Rimosso invio stato idle su WS connect (sovrascriveva "running")
- ✅ **Fix session UI**: Rimosso polling, usa solo POST response + ChangeDetectorRef
- ✅ **Fix position ticker**: Ora usa WS `position$` invece di REST call una tantum
- ✅ **Fix trade log**: Ora usa WS `trade_closed$` invece di polling REST
- ✅ **Fix performance panel**: snake_case → camelCase mapping, refresh su trade_closed
- ✅ **Fix PnL live**: `position_update` broadcast su ogni candela mock per PnL in tempo reale
- ✅ **Fix mock generator**: Avviato (era definito ma mai lanciato via `asyncio.create_task`)
- ✅ **Fix collector bug**: `await response.json()` → `response.json()` in 4 collectors
- ✅ **Fix Decimal serialization**: Aggiunto `float()` per long_pct/short_pct in snapshot job
- ✅ **Aggiunto endpoint `/api/scalping/trade-history`**: Recupera storico trade chiusi


**Milestone:** Scalping Module - Scheduler, Supervisor, Backtest Engine

**Completato:**
- ✅ **TASK-806 - AI Supervisor**: Integrazione moduli core esistenti. Esteso supervisor context, parameter updater, supervisor scheduler con 20+ test.
- ✅ **TASK-807 - Scheduler Centralizzato**: 4 job scalping registrati, SupervisorScheduler con run_once(), 15 test passanti.
- ✅ **TASK-808 - Backtest Engine**: HistoricalLoader, BacktestEngine, PerformanceCalculator, 10+ test su dati storici mock.

---

## v0.1.6 — 2026-06-16

**Milestone:** Supervisor Threshold Control + Context Enrichment

**Completato:**
- ✅ **TASK-849** — Fix log soglia in SignalAggregator (mostra threshold reale 15.0, non |score|)
- ✅ **TASK-850** — Threshold dinamico da ConfigLoader in SignalScoreEngine (aggiornabile a runtime)
- ✅ **TASK-851** — Azione `update_threshold` nel Supervisor AI (nuova action, model, parameter_updater, prompt)
- ✅ **TASK-852** — Context arricchito threshold per Supervisor (score, gap, collector attivi/assenti, coverage)
- ✅ **TASK-853** — Limiti sicurezza [5.0, 30.0] e cooldown 30 min per update_threshold
