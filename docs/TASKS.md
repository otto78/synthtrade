# TASKS.md — SynthTrade Task Tracking

> **Aggiornato:** 2026-07-15. Task completati spostati in `docs/ARCHIVE_TASKS.md`.

---

## EPICA AUDIT POST-OKX — Fix critici + semplificazione + refactor

**Status:** In corso
**Priorità:** CRITICA
**Recap audit:** `docs/recap/2026-07-15_full-audit-recap.md`
**Decisione architetturale (Andrea):**
- Binance: codice mantenuto in stand-by (non cancellare) — Binance potrebbe tornare in EU
- OKX: abolire strato CCXT, passare a REST-only (httpx) — CCXT fallisce sistematicamente su EU accounts
- Refactor: router.py monolite → moduli separati, nessun file > 500 righe

### TASK-1160 — Fix 5 NameErrors in router.py live trade path

**Status:** Pending
**Priorità:** 🔴 CRITICA
**Effort stimato:** 1 ora
**Dipendenze:** nessuna

**Problema:** 5 errori `NameError` nel percorso di trade live (`_candle_processor` in `router.py`). Crashano ogni tentativo di esecuzione trade.

| Linea | Variabile mancante | Fix |
|---|---|---|
| 1828 | `current_price` | `float(event.close)` |
| 1838 | `min_qty` | `float(filters["minQty"])` |
| 1856 | `qty_raw` | `_qty_raw` (con underscore) |
| 1819 | `_normalize_binance_total_balance()` | Eliminare blocco (CCXT-specifico, vedi TASK-1164) |
| 1822 | `_select_preferred_quote_balance()` | Eliminare blocco (CCXT-specifico, vedi TASK-1164) |

**File coinvolti:**
- `synthtrade/backend/app/scalping/router.py` (lines 1808-1856)

**Nota:** le ultime due funzioni inesistenti si trovano nel blocco CCXT-specifico (lines 1808-1823) che va eliminato interamente con il passaggio a TASK-1164 (REST-only). Questo task può essere risolto in due modi: (a) fix temporaneo delle 3 NameError rimanenti, oppure (b) integrazione diretta nel TASK-1164. Raccomandato: opzione (b).

**Acceptance Criteria:**
- `python -m py_compile synthtrade/backend/app/scalping/router.py` OK
- Nessun NameError nel path `_candle_processor` live trade
- Test `test_okx_integration.py` passa

### TASK-1161 — Fix circuit breaker on_success() mai chiamato (tutti i collector)

**Status:** Pending
**Priorità:** 🔴 CRITICA
**Effort stimato:** 2 ore
**Dipendenze:** nessuna

**Problema:** `CollectorCircuitBreaker.on_success()` esiste ma nessun collector la chiama. Dopo 3 fallimenti consecutivi il CB si apre per 5 min. In `half_open`, un successo non resetta → al prossimo failure riapre subito. Loop infinito.

**File coinvolti (tutti i collector in `synthtrade/backend/app/scalping/intelligence/collectors/`):**
- `funding_rate.py` — dopo line 125 (OKX) e line 158 (Binance)
- `open_interest.py` — dopo OKX path e Binance path + aggiungere `on_failure()` nel Binance path (line 176-181)
- `long_short_ratio.py` — dopo OKX path e Binance path + aggiungere `on_failure()` nel Binance path (line 164-169)
- `fear_greed.py` — dopo il return riuscito
- `sentiment.py` — dopo il return riuscito
- `whale.py` — dopo il return riuscito
- `onchain.py` — dopo il return riuscito
- `order_book_imbalance.py` — dopo il return riuscito
- `spread.py` — dopo il return riuscito (anche se wiring OFF)

**Implementazione:**
```python
# Pattern da applicare in ogni collector:
async def collect(self, symbol: str) -> dict | None:
    try:
        # ... fetch logic ...
        self._cb.on_success()  # <-- aggiungere qui
        return result
    except Exception as e:
        self._cb.on_failure()
        return None
```

**Acceptance Criteria:**
- Ogni collector chiama `self._cb.on_success()` dopo un fetch riuscito
- `open_interest.py` e `long_short_ratio.py` chiamano `self._cb.on_failure()` anche nel Binance path
- Test esistenti passano senza modifiche al comportamento osservabile

### TASK-1162 — Fix _sign_headers credenziali instance vs settings

**Status:** Pending
**Priorità:** 🔴 CRITICA
**Effort stimato:** 1 ora
**Dipendenze:** nessuna

**Problema:** `_sign_headers()` in `okx_exchange.py:127-143` è `@staticmethod` che legge `settings.exchange_secret_key` etc. Se l'adapter ha credenziali diverse da settings (es. multi-account), le REST call usano le credenziali sbagliate.

**Fix:** convertire in metodo d'istanza:
```python
def _sign_headers(self, method: str, path: str, body: str = "") -> dict[str, str]:
    timestamp = ...
    sign_str = timestamp + method + path + body
    signature = hmac.new(self._secret.encode(), sign_str.encode(), hashlib.sha256).digest()
    return {
        "OK-ACCESS-KEY": self._api_key,
        "OK-ACCESS-SIGN": base64.b64encode(signature).decode(),
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-PASSPHRASE": self._passphrase,
    }
```

**File coinvolti:**
- `synthtrade/backend/app/execution/okx_exchange.py` (lines 127-143)

**Acceptance Criteria:**
- `_sign_headers` è metodo d'istanza, usa `self._api_key/secret/passphrase`
- `@staticmethod` rimosso
- Tutte le chiamate REST dirette passano correttamente

### TASK-1163 — Fix OCO leg detection in order event stream

**Status:** Pending
**Priorità:** 🔴 CRITICA
**Effort stimato:** 2 ore
**Dipendenze:** nessuna

**Problema:** In `okx_order_event_stream.py:466`: `if "tp" in ord_type.lower()` — ma `ordType` per OCO è `"oco"`. Tutti gli ordini OCO ottengono `leg = "algo"` invece di `take_profit`/`stop_loss`. Il router non può distinguere TP fill da SL fill.

**Fix:** leggere il campo `tpTriggerPx`/`slTriggerPx` dalla risposta OKX per determinare il leg:
```python
if algo_order.get("tpTriggerPx"):
    leg = "take_profit"
elif algo_order.get("slTriggerPx"):
    leg = "stop_loss"
else:
    leg = "algo"
```

**File coinvolti:**
- `synthtrade/backend/app/execution/okx_order_event_stream.py` (lines 448-470)

**Acceptance Criteria:**
- Un ordine OCO con `tpTriggerPx` popolato riceve `leg = "take_profit"`
- Un ordine OCO con `slTriggerPx` popolato riceve `leg = "stop_loss"`
- Il router `_on_order_update` gestisce correttamente entrambi i leg

### TASK-1164 — OKX adapter: rimuovere strato CCXT, REST-only (httpx)

**Status:** Pending
**Priorità:** 🔴 CRITICA
**Effort stimato:** 1-2 giorni
**Dipendenze:** TASK-1160, TASK-1162

**Problema:** L'architettura CCXT→REST fallback per OKX EU non ha senso: CCXT fallisce sempre (50119), i REST funzionano sempre. Il doppio layer aggiunge latenza, complessità e superficie di errore.

**Decisione (Andrea):** abolire CCXT per OKX, passare a REST diretto (httpx) come unico metodo.

**Metodi da convertire (CCXT→REST-only):**

| Metodo | CCXT da eliminare | REST da promuovere |
|---|---|---|
| `get_holdings()` | `fetch_balance()` | `_direct_fetch_balance()` → unico path |
| `get_symbol_rules()` | `load_markets()` | `_direct_fetch_symbol_rules()` → unico path |
| `place_market_order()` | `create_order()` | `_direct_place_market_order()` → unico path |
| `place_exit_bracket()` | `create_order(oco)` | `_direct_place_exit_bracket()` → unico path |
| `get_btc_macro_context()` | `fetch_ticker()` + `fetch_ohlcv()` | `_direct_fetch_btc_macro_context()` → unico path |
| `get_trade_fee()` | `fetch_trading_fee()` | `_direct_fetch_trade_fee()` → unico path |

**Metodi da implementare in REST (non esistono ancora):**

| Metodo | Endpoint OKX | Note |
|---|---|---|
| `get_ticker_price()` | `GET /api/v5/market/ticker?instId=X` | Attualmente CCXT-only |
| `get_open_exit_orders()` | `GET /api/v5/trade/orders-algo-pending` | Attualmente CCXT-only |
| `cancel_open_exit_orders()` | `DELETE /api/v5/trade/order-algo` | Attualmente CCXT-only |

**Router — accessi diretti CCXT da eliminare:**
- Line 1809: `exchange.client.fetch_balance()` → usare `adapter.get_holdings()` (TASK-1160)
- Line 3354: `exchange_stop.client.cancel_order()` → usare `adapter.cancel_open_exit_orders()`

**Modifiche strutturali:**
- `OkxExchangeAdapter.__init__`: rimuovere `self.client = ccxt.okx(config)` e tutto il setup CCXT
- Mantenere `ccxt` nelle dipendenze (Binance standby)
- Mantenere `BinanceExchangeAdapter` invariato
- Rinominare i metodi `_direct_*` eliminando il prefisso `_direct_` (diventano i path principali)
- Gli `_sign_headers` diventano metodo d'istanza (TASK-1162)

**Mantenere in stand-by (commentare, non eliminare):**
- `_bnb_price_cache` → commento `# BINANCE STANDBY`
- `_convert_bnb_commission_to_usdc()` → commento `# BINANCE STANDBY`
- `@router.get("/binance/exchange-info")` → commento `# BINANCE STANDBY`
- Import `from app.execution.exchange import ExchangeOrderError` → commento `# BINANCE STANDBY`

**File coinvolti:**
- `synthtrade/backend/app/execution/okx_exchange.py` — refactor principale
- `synthtrade/backend/app/scalping/router.py` — eliminare accessi diretti CCXT
- `synthtrade/backend/app/execution/exchange_factory.py` — aggiornare se necessario

**Acceptance Criteria:**
- `okx_exchange.py` non importa più `ccxt`
- Tutti i metodi dell'adapter usano REST diretto (httpx)
- Nessun `self.client.*` nel file
- `test_okx_integration.py` passa
- `python -m py_compile` su tutti i file modificati OK
- Sessione paper/demo OKX funziona end-to-end

### TASK-1165 — Fix sl_pct_net inconsistente (WS initial state vs candle processor)

**Status:** Pending
**Priorità:** 🟠 ALTA
**Effort stimato:** 1 ora
**Dipendenze:** nessuna

**Problema:** Il calcolo di `sl_pct_net` e `tp_pct_net` è diverso in due location:
- WS initial state (line 480): `(sl_pct_cfg * 100) - fee_round_trip` → con SL=0.3%, result = `29.8`
- Candle processor (line 2241): `(_sl_cfg) - fee_round_trip` → result = `0.1`

Con SL ricalibrato a 1.05%, entrambi dovrebbero produrre ~0.35%.

**File coinvolti:**
- `synthtrade/backend/app/scalping/router.py` (lines 475-485 e lines 2235-2250)

**Acceptance Criteria:**
- WS initial state e position broadcast usano la stessa formula
- Con SL=1.05%, TP=1.55%, fee_round_trip=0.70%: `sl_pct_net=0.35`, `tp_pct_net=0.85`

### TASK-1166 — Refactor router.py: estrazione moduli

**Status:** Pending
**Priorità:** 🟡 MEDIA
**Effort stimato:** 2-3 giorni
**Dipendenze:** TASK-1160, TASK-1164

**Problema:** `router.py` è un monolite di 4160 righe. `_candle_processor()` è una inner function di ~750 righe. Nessun file dovrebbe superare 500 righe (perdita contesto).

**Decomposizione proposta:**

| Nuovo modulo | Contenuto | Righe stimate |
|---|---|---|
| `router/pricing.py` | `_net_to_gross_pct`, fee helpers, `calculate_pnl()` unico | ~200 |
| `router/session_lifecycle.py` | `_start_session`, `_stop_session`, `_restore_scalping_session` | ~400 |
| `router/trade_executor.py` | `_candle_processor` → `TradeExecutor` class | ~800 |
| `router/ws_broadcast.py` | `_start_ws_broadcast`, `_stop_ws_broadcast`, `broadcast_scalping_event` | ~300 |
| `router/db_ops.py` | `_open_position`, `_close_position_and_record`, `_update_closed_position_in_db` | ~300 |
| `router/rest_endpoints.py` | Tutti gli `@router.get/post` | ~600 |

`router.py` resterebbe come orchestratore leggero (~200 righe) che importa e collega i moduli.

**Acceptance Criteria:**
- Nessun file in `router/` supera 500 righe
- `router.py` è < 300 righe (orchestratore)
- Tutti i test passano
- Nessuna modifica al comportamento osservabile

---

## TASK-1130/1131 — Reverted (riferimento)

### TASK-1130 — Fix: Missing _get_ccxt_symbol method in OkxExchangeAdapter

**Status:** ⚠️ REVERTED (2026-07-13)
**Priorità:** ALTA

Il sistema funziona con i fix precedenti (TASK-1126) e il fallback REST polling gestisce correttamente gli eventi.

### TASK-1131 — CCXT REST fallback per OKX EU accounts

**Status:** ⚠️ REVERTED (2026-07-13)
**Priorità:** CRITICA

Il fallback REST polling è operativo e gestisce gli eventi di fill senza errori critici. WS private failure (60032) non è bloccante.

---

## TASK-1116.G — Instrument discovery environment-aware (Demo vs Live)

**Status:** Pending
**Priorità:** ALTA — causa fallimenti fee/trading silenziosi per simboli validi in live ma assenti in demo

**Dipendenze:** TASK-1103 (OkxExchangeAdapter), TASK-1109 (Frontend exchange-neutral), TASK-1116.E (fallback fee REST)

**Problema:** OKB-EUR è tradeable in live ma non esiste in Demo Trading (errore 51001). Il sistema non distingue i due cataloghi.

**File coinvolti:**
- `synthtrade/backend/app/execution/okx_exchange.py`
- `synthtrade/backend/app/scalping/router.py`
- `synthtrade/frontend/synthtrade-ui/src/app/scalping/services/exchange-symbols.service.ts`
- `synthtrade/frontend/synthtrade-ui/src/app/scalping/components/session-controls.component.ts`

**Sottotask:**
1. **1116.G.1 — Discovery cache environment-aware**: cache separata per demo/live
2. **1116.G.2 — Endpoint backend filtra per ambiente**: endpoint risponde solo strumenti validi
3. **1116.G.3 — Validazione pre-avvio sessione**: errore esplicito se simbolo non disponibile
4. **1116.G.4 — Frontend: dropdown simboli filtrato dinamicamente**
5. **1116.G.5 — Messaggio UI esplicativo**: tooltip per simboli non disponibili in demo
6. **1116.G.6 — Test**: unit + integration test

---

## EPICA COLLECTOR INTELLIGENCE — Task pending

### TASK-1157 — Verifica CVD grace period

**Status:** Pending — *supersede TASK-COLLECTOR-005*
**Priorità:** 🟡 Media
**Dipendenze:** nessuna

**Obiettivo:** Verificare se CVD funziona dopo 100 trade su OKB-EUR.

**File:** `synthtrade/backend/app/scalping/intelligence/collectors/cvd_calculator.py`

### TASK-1159 — Ricalibrazione pesi SignalScoreEngine + nota cadenza micro-swing

**Status:** Pending — *bloccata finché le Fasi 1-5 non sono attive per almeno 2-3 sessioni reali*
**Priorità:** 🔴 Alta
**Dipendenze:** TASK-1150, 1151, 1152, 1153, 1154, 1157

**Obiettivo:** Redistribuire i pesi in `SignalScoreEngine.WEIGHTS` su numeri osservati dai log reali, non su placeholder.

**Nota:** Con 10-30 trade/giorno, il CVD potrebbe perdere peso relativo a favore di segnali più strutturali come Order Book Imbalance su finestre più larghe. Decisione da prendere solo dopo dati raccolti.

---

## Task pending (non OKX-specific)

### TASK-906 — Trend Analysis: Prevenzione Falling Knife in Mean-Reversion

**Status:** Pending (in attesa del prossimo drop di mercato per raccogliere dati reali)
**Priorità:** ALTA

**Obiettivo:** Bloccare trade in "mean-reversion" durante crolli verticali improvvisi.

**Task:**
1. **Data Collection:** Monitorare log durante cali per registrare velocità (`trend_5m`) in fase "diverging"
2. **Rule Definition:** Soglia dinamica (`if trend_direction == "diverging" and trend_5m <= -X`)
3. **Implementation:** Aggiornare `signal_aggregator.py` bloccando trade in mean-reversion
4. **Verifica:** Prevenga falling knife senza bloccare mean-reversion legittimo

---

### TASK-903 — RegimeDetector: isteresi K candele

**Status:** Pending
**Priorità:** MEDIA

**Problema:** Il regime cambia ad ogni candela se le soglie oscillano vicino ai boundary → flickering → supervisor riceve contesti contraddittori.

**File:** `synthtrade/backend/app/scalping/engine/regime_detector.py`

**Implementazione:**
- Aggiungere `_pending_regime: Optional[str]` e `_pending_count: int`
- Regime committed cambia SOLO se lo stesso candidato si osserva per K candele consecutive (default K=3)
- Se il candidato cambia prima di K → reset counter
- Proprietà pubblica `pending_regime` per debug

---

### TASK-904 — StrategySelector DB-driven

**Status:** Pending
**Priorità:** BASSA
**Dipendenze:** TASK-902

**Problema:** Mapping `regime → strategia_consentita` hardcoded in due posti.

**File:**
- `strategy_selector.py` — leggere da `scalping_runtime_config`
- `supervisor_scheduler.py` — sostituire dict hardcoded con lettura da DB
- Migration: chiavi `regime_strategy_*` a `scalping_runtime_config`

---

### TASK-898 — Analisi Trend basata su dati persistiti

**Status:** Pending
**Priorità:** BASSA — dipende da raccolta dati reali
**Dipendenze:** TASK-895 + almeno 20 trade chiusi con `signal_log_id` e `trend_direction` non null

**Prerequisito:**
```sql
SELECT COUNT(*) FROM scalping_trades t
JOIN session_signal_log sl ON sl.id = t.signal_log_id
WHERE t.status = 'closed' AND sl.trend_direction IS NOT NULL;
```
Se < 20 → non partire.

**File da creare:** `docs/trend_analysis_report.md`

---

### TASK-907 — Bug Frontend: dati mancanti su reload con sessione PAUSED

**Status:** Pending
**Priorità:** ALTA — impatta usabilità dashboard ogni reload con sessione in pausa

**Problema:** Ricaricando la pagina in stato `PAUSED`, pannelli PERFORMANCE, TRADE LOG e RISK CONTROLS risultano vuoti.

**Task:**
1. **Repro:** sessione in pausa → reload → verificare in DevTools quali chiamate REST partono
2. **Root cause:** identificare se (a) guardia su `session.status`, (b) dati attesi solo da WS, o (c) endpoint filtra per `status='running'`
3. **Fix:** disaccoppiare caricamento storico dallo stato live
4. **Verifica:** reload con sessione `paused` → pannelli popolati

---

### TASK-908 — Hardcoded Resume Guard (no-short, regime bearish)

**Status:** Riservato per analisi (richiesta Andrea 14/07/2026) — non implementare ora
**Priorità:** ALTA — *sospesa: da analizzare assieme a TASK-909*

**Obiettivo:** Impedire `resume_trading` quando regime bearish, confidence alta, `allows_short=False` e nessuna posizione aperta — indipendentemente dal giudizio AI.

**Contesto:** Sessione live 30/06 — 6 stop_loss consecutivi, 5 segnali SELL scartati, `resume_trading` con motivazione debole mentre regime era ancora `trending_down`.

**File:**
- `parameter_updater.py`
- `supervisor_scheduler.py`
- `context_builder.py`

#### Red — Test
- [ ] `test_blocks_resume_when_trending_down_and_no_short`
- [ ] `test_allows_resume_when_regime_not_bearish`
- [ ] `test_allows_resume_when_short_enabled`
- [ ] `test_allows_resume_when_confidence_low`
- [ ] `test_guard_does_not_affect_other_actions`
- [ ] `test_was_applied_false_and_reason_logged`

#### Green — Implementazione
- [ ] `short_enabled: bool` e `regime_confidence: float` in `SupervisorContext`
- [ ] `_check_resume_guard(decision, context) -> tuple[bool, str | None]` in `parameter_updater.py`
- [ ] `RESUME_GUARD_MIN_CONFIDENCE = 0.7` (costante hardcoded)
- [ ] Applicare guard PRIMA di eseguire `Resuming trading`
- [ ] Se bloccato: log warning + persistere `was_applied=False, blocked_reason=...`

#### Refactor
- [ ] Costanti `RESUME_GUARD_MIN_CONFIDENCE` e `{"trending_down"}` in costanti di modulo
- [ ] Campo `short_enabled` nel payload broadcast WS decisione supervisor

---

## EPICA SHORT SELLING — Superseded

### TASK-1000 — WalletOrchestrator: Fase 1 (resolve puro + snapshot)

**Status:** Superseded by EPICA OKX (non avviare prima di TASK-1113)
**Priorità:** SOSPESA

**Nota:** Il modello Binance Margin non è più il percorso primario. OKX usa un modello diverso con Trading Account/tdMode. Da ripianificare dopo migrazione OKX.

**Riferimento:** `SynthTrade_Short_Selling_Architecture.md` §3, §11 Fasi 2-6.

---

## Task da Investigare — Aperti/Parziali

> Da `MASTER_RECAP.md` 26/06/2026. Verifica 01/07/2026. Aggiornato 15/07/2026.

| Task | Status | Note |
|------|--------|------|
| TASK-INVEST-011 — Regime misclassification (volume-confirmed) | 🟡 APERTO | Nessuna logica volume-confirmed in `regime_detector.py` |
| TASK-INVEST-012 — Falling Knife Protection | 🟡 APERTO | Allineata a TASK-906 (in attesa dati reali) |
| TASK-INVEST-013 — trend_direction troppo sensibile | ⚠️ PARZIALE | Codice presente ma soglia troppo sensibile |
| TASK-INVEST-017 — Bias outcome_label Supervisor | ⚠️ PARZIALE | Usa solo PnL (no bias regime) |
| TASK-INVEST-018 — Soglia dinamica senza decadimento | ⚠️ PARZIALE | Decay/degradation non implementato |
| TASK-INVEST-020 — Slope filter su EMA Cross | 🟡 APERTO | Nessuno slope filter in `ema_cross.py` |

**Nota:** TASK-INVEST-019 (5/8 collector non funzionanti) è ora risolto con provider-aware collectors (TASK-1153).
