# 2026-07-15 — Full System Audit Recap

## Data: 2026-07-15
## Autore: opencode (audit automated)
## Contesto: Post-migrazione OKX — valutazione completa stato sistema

---

## 1. Decisioni Architetturali (approvate da Andrea)

### 1.1 Binance: Standby, non eliminazione
Il codice Binance (`exchange.py`, `BinanceExchangeAdapter`, `FUTURES_SYMBOL_MAP`, ecc.) va **mantenuto in stand-by**. Binance potrebbe tornare disponibile in Europa in futuro. Il codice Binance non va cancellato ma nemmeno toccato — resta legacy/inattivo.

### 1.2 OKX: Rimozione strato CCXT, REST-only
L'architettura attuale CCXT→REST fallback per OKX EU non ha senso:
- CCXT fallisce sistematicamente su account EU con errore 50119 ("API key doesn't exist")
- I REST diretti funzionano sempre
- Il doppio layer aggiunge latenza, complessità e superficie di errore

**Decisione:** abolire CCXT per OKX, passare a REST diretto (httpx) come unico metodo. Questo semplifica l'adapter, riduce la latenza e elimina tutti i fallback 50119.

**Stato CCXT→REST nel dettaglio (metodi da convertire):**

| Metodo OKX | CCXT usato | REST funziona | Azione |
|---|---|---|---|
| `get_holdings()` | `fetch_balance()` | ✅ `_direct_fetch_balance()` | Elimina CCXT, tieni REST |
| `get_symbol_rules()` | `load_markets()` | ✅ `_direct_fetch_symbol_rules()` | Elimina CCXT, tieni REST |
| `place_market_order()` | `create_order()` | ✅ `_direct_place_market_order()` | Elimina CCXT, tieni REST |
| `place_exit_bracket()` | `create_order(oco)` | ✅ `_direct_place_exit_bracket()` | Elimina CCXT, tieni REST |
| `get_btc_macro_context()` | `fetch_ticker()` + `fetch_ohlcv()` | ✅ `_direct_fetch_btc_macro_context()` | Elimina CCXT, tieni REST |
| `get_trade_fee()` | `fetch_trading_fee()` | ✅ `_direct_fetch_trade_fee()` | Elimina CCXT, tieni REST |
| `get_ticker_price()` | `fetch_ticker()` | ❌ (cache stale) | Implementa REST diretto |
| `get_open_exit_orders()` | `fetch_open_orders()` | ❌ | Implementa REST diretto |
| `cancel_open_exit_orders()` | `cancel_order()` | ❌ | Implementa REST diretto |

**Router — accessi diretti CCXT da eliminare:**
- Line 1809: `exchange.client.fetch_balance()` → usare `exchange.get_holdings()`
- Line 3354: `exchange_stop.client.cancel_order()` → usare `exchange.cancel_open_exit_orders()`

**Mantenere:**
- `ccxt` nelle dipendenze (potrebbe servire per Binance in futuro)
- `BinanceExchangeAdapter` invariato (standby)
- Struttura `exchange_factory.py` provider-neutral

---

## 2. Bug Critici da Fixare

### 2.1 Five NameErrors in `router.py` (CRASH LIVE TRADING)
Tutti nel percorso `_candle_processor()` (trade execution):

| Linea | Variabile | Fix |
|---|---|---|
| 1828 | `current_price` | `float(event.close)` |
| 1838 | `min_qty` | `float(filters["minQty"])` |
| 1856 | `qty_raw` | `_qty_raw` (con underscore) |
| 1819-1820 | `_normalize_binance_total_balance` | Eliminare il blocco (CCXT-specifico, vedi §1.2) |
| 1822-1823 | `_select_preferred_quote_balance` | Eliminare il blocco (CCXT-specifico, vedi §1.2) |

**Nota:** le ultime due funzioni inesistenti si trovano nel blocco CCXT-specifico (lines 1808-1823) che va eliminato interamente con il passaggio a REST-only.

### 2.2 Circuit Breaker `on_success()` mai chiamato (TUTTI I COLLECTOR)
`CollectorCircuitBreaker.on_success()` esiste ma nessun collector la chiama dopo un fetch riuscito. Il CB si blocca in un loop `half_open → success → half_open → failure → open → wait → half_open...`.

**Fix:** aggiungere `self._cb.on_success()` in ogni collector dopo un return riuscito.

**File coinvolti (tutti i collector in `synthtrade/backend/app/scalping/intelligence/collectors/`):**
- `funding_rate.py` — dopo line 125 (OKX) e line 158 (Binance)
- `open_interest.py` — dopo OKX path e Binance path
- `long_short_ratio.py` — dopo OKX path e Binance path
- `fear_greed.py` — dopo il return riuscito
- `sentiment.py` — dopo il return riuscito
- `whale.py` — dopo il return riuscito
- `onchain.py` — dopo il return riuscito
- `order_book_imbalance.py` — dopo il return riuscito
- `cvd_calculator.py` — non usa CB (WS-driven, skip)

### 2.3 `_sign_headers` usa `settings.*` invece delle credenziali dell'istanza
In `okx_exchange.py:127-143`, `_sign_headers()` è `@staticmethod` che legge `settings.exchange_secret_key` etc. Se l'adapter ha credenziali diverse da settings, le REST call usano le credenziali sbagliate.

**Fix:** convertire in metodo d'istanza che usa `self._api_key`, `self._secret`, `self._passphrase`.

### 2.4 OCO leg detection rotta
In `okx_order_event_stream.py:466`: `if "tp" in ord_type.lower()` — ma `ordType` per OCO è `"oco"`. Tutti gli ordini OCO ottengono `leg = "algo"`.

**Fix:** aggiungere controllo per `ordType == "oco"` e leggere il campo `tpTriggerPx`/`slTriggerPx` per determinare il leg.

---

## 3. Bug Alti da Fixare

### 3.1 `sl_pct_net` inconsistente
- WS initial state (line 480): `(sl_pct_cfg * 100) - fee_round_trip` → se `sl_pct_cfg=0.3`, result = `29.8`
- Candle processor (line 2241): `(_sl_cfg) - fee_round_trip` → result = `0.1`

**Fix:** allineare a un'unica formula. Con SL=1.05% configurato, entrambi dovrebbero produrre ~0.35%.

### 3.2 Binance-specific code nel live path di router.py
- `_bnb_price_cache` (line 232-236) — dead code
- `_convert_bnb_commission_to_usdc()` (lines 378-417) — Binance-only
- `@router.get("/binance/exchange-info")` (line 2492-2518) — fallisce con OKX
- Import `from app.execution.exchange import ExchangeOrderError` (line 2065)
- Blocco lines 1808-1823 — `exchange.client.fetch_balance()` Binance-specific

**Fix:** marcare come standby con commento `# BINANCE STANDBY`, non eliminare.

### 3.3 PnL calcolato 6 volte
Fee-adjusted PnL in: `_on_order_update`, `_on_uds_reconnect_sync`, `_close_position_and_record`, `_candle_processor` broadcast, `_trade_processor`, `/position` endpoint.

**Fix:** estrarre `calculate_pnl()` helper unico.

### 3.4 DB write failures silently swallowed
- Line 788-789: INSERT posizione aperta fallisce → warning, posizione persa al restart
- Line 889-890: UPDATE posizione chiusa fallisce → trade fantasma

**Fix:** retry logic o almeno log ERROR (non warning) + alert via WS.

### 3.5 `_execution_state` race conditions
- Stop vs Start: status="idle" impostato PRIMA della chiusura posizione
- Session start DB insert vs stop: check-then-act non atomico
- UDS fill vs force-close: entrambi chiamano `pm.close_position()`

**Fix:** introduzione di un semplice lock async (asyncio.Lock) per le operazioni critiche.

---

## 4. Refactoring Proposto

### 4.1 Router.py — Estrazione moduli
Il file è un monolite di 4160 righe. Decomposizione proposta:

| Nuovo modulo | Contenuto estratto | Righe stimate |
|---|---|---|
| `router/pricing.py` | `_net_to_gross_pct`, fee helpers, PnL calc | ~200 |
| `router/session_lifecycle.py` | `_start_session`, `_stop_session`, restore | ~400 |
| `router/trade_executor.py` | `_candle_processor` + `_trade_processor` | ~800 |
| `router/ws_broadcast.py` | `_start_ws_broadcast`, `_stop_ws_broadcast`, broadcast | ~300 |
| `router/db_ops.py` | `_open_position`, `_close_position_and_record`, reconcile | ~300 |
| `router/rest_endpoints.py` | Tutt gli `@router.get/post` | ~600 |

`router.py` resterebbe come orchestratore leggero (~200 righe) che importa e collega i moduli.

### 4.2 `_candle_processor` in `TradeExecutor` class
La funzione interna di ~750 righe diventa una classe con:
- `async def process_candle(event)` — logica trade
- `async def process_trade(event)` — logica trade updates
- `async def process_intelligence()` — logica scoring
- `_execution_state` iniettato come dipendenza, non globale

---

## 5. Sicurezza

| Issue | Severità | Fix |
|---|---|---|
| No rate limiting su alcun endpoint | CRITICA | SlowAPI o custom middleware |
| Default secrets `changeme`/`dev-secret-change-in-prod` | CRITICA | Startup validation con `sys.exit(1)` |
| No startup validation config | ALTA | Check API key non vuote in live mode |
| WS token in query string | BASSA | Valutare subprotocol auth |
| `config_api.py:90` muta Settings singleton | MEDIA | Usare environment reload |

---

## 6. Test Mancanti

| Area | Stato | Priorità |
|---|---|---|
| `tests/e2e/` | Vuota | ALTA |
| Test per `POST /api/config/mode` | Assente | ALTA |
| Test per trade execution live path | Parziale | ALTA |
| Test per session restore | Parziale | MEDIA |
| Test per circuit breaker recovery | Assente | MEDIA |

---

## 7. Intelligence Layer — Stato

| Collector | OKX | Bug noti |
|---|---|---|
| fear_greed | ✅ | Nessuno |
| long_short_ratio | ✅ | Nessuno |
| open_interest | ✅ | Nessuno |
| funding_rate | ✅ | Nessuno |
| sentiment | ✅ | Nessuno |
| order_book_imbalance | ✅ | Nessuno |
| cvd | ✅ | TASK-1157 pending |
| spread | ✅ | Wiring OFF (by design) |
| whale | ⚠️ | OKB non coperto (low priority) |
| onchain | ✅ | Dune key opzionale |

**Bug sistemico:** circuit breaker `on_success()` non chiamato (vedi §2.2).

---

## 8. Task Pendenti da TASKS.md

| Task | Stato | Impatto |
|---|---|---|
| TASK-903 (Regime hysteresis) | Pending | Alto — regime flickering |
| TASK-906 (Falling knife protection) | Pending | Alto — 4 trade errati |
| TASK-907 (Frontend paused reload) | Pending | Medio — usabilità |
| TASK-908 (Resume guard) | Reserved | Alto — safety net |
| TASK-1157 (CVD grace period) | Pending | Basso — verifica empirica |
| TASK-1159 (Weight recalibration) | Pending | Medio — dopo 2-3 sessioni |

---

## 9. Ordine di Esecuzione Consigliato

### Fase 1 — Fix Critici (2-4 ore)
1. Fix NameErrors in `router.py` (§2.1) — insieme al blocco CCXT→REST
2. Fix circuit breaker `on_success()` (§2.2) — tutti i collector
3. Fix `_sign_headers` credenziali (§2.3)
4. Fix OCO leg detection (§2.4)

### Fase 2 — Semplificazione OKX (1-2 gg)
1. Eliminare strato CCXT da `okx_exchange.py` — REST-only
2. Fix accessi diretti CCXT in `router.py`
3. Implementare metodi mancanti in REST (`get_ticker_price`, `get_open_exit_orders`, `cancel_open_exit_orders`)
4. Rimuovere `ccxt` da `self.client` nell'adapter (mantenere nelle dipendenze)

### Fase 3 — Refactoring Router (2-3 gg)
1. Estrai `pricing.py` + `calculate_pnl()`
2. Estrai `trade_executor.py` da `_candle_processor`
3. Estrai `session_lifecycle.py`
4. Estrai `ws_broadcast.py` e `db_ops.py`
5. Estrai `rest_endpoints.py`

### Fase 4 — Sicurezza e Qualità (1 gg)
1. Rate limiting (SlowAPI)
2. Startup config validation
3. Fix `sl_pct_net` inconsistente
4. Fix Binance standby code (commentare, non eliminare)

### Fase 5 — Task Pendenti (variabile)
1. TASK-903 Regime hysteresis
2. TASK-906 Falling knife protection
3. TASK-907 Frontend paused reload
4. Test E2E per path critici
