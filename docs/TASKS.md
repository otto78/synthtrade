# TASKS.md — SynthTrade Task Tracking

## Active Tasks

### TASK-876 — Fee reali: Fase 1 - Catturare commissione reale dal WebSocket (2026-06-24) ✅

**Status:** Complete ✅

**Obiettivo:** Propagare `n` (commission) e `N` (commissionAsset) dal payload Binance fino al chiamante, per ogni fill.

**File:** `synthtrade/backend/app/execution/user_data_stream.py`

**Intervento puntuale in `_dispatch_message`, dentro il blocco `if event_type == "executionReport":`:**

1. Aggiungere l'estrazione dei due campi, vicino a dove viene letto `fill_price`:
   ```python
   commission = float(event.get("n", 0) or 0)
   commission_asset = event.get("N")
   ```

2. Aggiungere questi due valori al dict passato a `on_order_update`:
   ```python
   await self._on_order_update({
       "symbol": symbol,
       "side": order_side,
       "order_id": order_id,
       "order_list_id": order_list_id,
       "status": order_status.lower(),
       "fill_price": fill_price,
       "commission": commission,
       "commission_asset": commission_asset,
       "leg": ...,
   })
   ```

**Verifica:** Loggare temporaneamente il dict completo ricevuto al prossimo fill reale e confermare che `commission` e `commission_asset` arrivano popolati e coerenti con quanto visibile su Binance (sezione "Trade History" / "Fee" dell'account).

---

### TASK-877 — Fee reali: Fase 2 - Recuperare fee tier account con certezza (2026-06-24) ✅

**Status:** Complete ✅

**Obiettivo:** Avere a disposizione, senza ipotesi, il tier fee corrente dell'account per il symbol tradato — necessario per i calcoli di PnL non realizzato e come cross-check rispetto alla commissione realizzata.

**File:** `synthtrade/backend/app/execution/exchange.py` (o dove risiede `BinanceExchangeAdapter`)

**Intervento:**
1. Aggiungere un metodo che chiama l'endpoint firmato Binance `GET /sapi/v1/asset/tradeFee` con `symbol=BNBUSDC`. Risposta contiene `makerCommission` e `takerCommission` esatti per l'account, in quel momento, incluso eventuale sconto BNB già applicato.
2. Chiamarlo una volta all'avvio sessione (dove oggi si inizializza l'`ExecutionLoop` / la sessione di trading) e salvare il risultato in `_execution_state` in `router.py`, nuova chiave `fee_tier`.
3. Definire una politica di refresh: refresh ad ogni avvio sessione è sufficiente; opzionale refresh ogni 24h via APScheduler come miglioria non bloccante.

**Verifica:** Confrontare il valore restituito dall'endpoint con quanto mostrato nella UI Binance (Account → Fee). Devono coincidere esattamente.

---

### TASK-878 — Fee reali: Fase 3A - Sostituire hardcode riga 590 (2026-06-24) ✅

**Status:** Complete ✅

**Obiettivo:** Sostituire fee hardcoded (0.001) con commissione reale per PnL realizzato in `on_order_update` (chiusura trade via OCO fill).

**File:** `synthtrade/backend/app/scalping/router.py`

**Riga target:** 590 — `on_order_update` — chiusura trade via OCO fill (la funzione che produce il log `✅ Trade chiuso da...`)

**Caso A — PnL realizzato (trade chiuso, fill avvenuto):**
- Usare commissione reale entry (da salvare su `pos` al momento dell'apertura del trade — verificare se `pos` ha già un campo adatto o va aggiunto a `PositionManager`/al modello posizione)
- Usare commissione reale exit (da Fase 1, TASK-876, sullo stesso evento che triggera questa riga)
- Se `commission_asset` non è `USDC` (es. è `BNB`), convertire in USDC al prezzo di mercato BNB/USDC al momento del fill — prezzo ottenibile da un ticker spot in tempo reale (dato reale, non stimato)

**Sostituire:**
```python
fees = (entry_f * qty_f * 0.001) + (fill_price * qty_f * 0.001)
```
con la somma delle commissioni reali di entrata + uscita.

**Verifica:** Dopo il deploy, osservare il prossimo trade chiuso reale e confrontare manualmente: prezzo entry, prezzo exit (fill reali dai log), commissioni reali (dal payload Fase 1), e il PnL finale calcolato dal sistema. Il conto deve quadrare a mano.

---

### TASK-879 — Fee reali: Fase 3B - Verificare e fixare riga 692 (2026-06-24) ✅

**Status:** Complete ✅

**Obiettivo:** Verificare se il codice alla riga 692 è raggiungibile o dead code, quindi applicare fix se necessario.

**File:** `synthtrade/backend/app/scalping/router.py`

**Riga target:** 692 — sezione duplicata/simile alla riga 590

**Azione:**
1. ✅ Verificato: il codice è **raggiungibile** (non dead code) - è nella funzione `_on_uds_reconnect_sync()` che gestisce riconnessioni UDS
2. ✅ Applicato fix: ora usa commissioni reali di entrata (se disponibili da WebSocket) e fee tier per uscita attesa
3. ✅ Conversione automatica BNB→USDC quando necessario

**Modifiche:**
- Sostituito hardcode `fees = (entry_f * qty_f * 0.001) + (fill_price * qty_f * 0.001)` con logica reali/attese
- Entry: usa `pos.entry_commission` se disponibile, altrimenti fee tier
- Exit: usa fee tier (costo atteso, dato che non abbiamo dati WebSocket in riconnessione)
- Aggiunto logging debug per tracciamento

**Verifica:** ✅ Completato - il codice è mantenuto e ora usa la stessa logica della riga 590 (TASK-878)

---

### TASK-880 — Fee reali: Fase 3C - Sostituire hardcode righe 805-806 (2026-06-24) ✅

**Status:** Complete ✅

**Obiettivo:** Sostituire fee hardcoded con commissione reale per PnL realizzato in `_close_position_and_record` (helper di chiusura manuale/signal-based).

**File:** `synthtrade/backend/app/scalping/router.py`

**Righe target:** 805-806 — `_close_position_and_record` — helper di chiusura manuale/signal-based

**Caso A — PnL realizzato:**
- ✅ Applicato stesso trattamento del TASK-878
- ✅ Entry: commissione reale se disponibile da WebSocket, altrimenti fee tier
- ✅ Exit: fee tier (costo atteso per chiusura manuale)
- ✅ Conversione automatica BNB→USDC quando necessario

**Modifiche:**
- Sostituito hardcode `fees = (entry_val * 0.001) + (exit_val * 0.001)` con logica reali/attese
- Entry: usa `pos.entry_commission` se disponibile, altrimenti fee tier (taker)
- Exit: usa fee tier (taker per market order di chiusura manuale)
- Aggiunto logging debug per tracciamento

**Verifica:** ✅ Completato - pronta per test con chiusura manuale/signal-based

---

### TASK-881 — Fee reali: Fase 3D - Sostituire hardcode righe 1066-1067 (2026-06-24) ✅

**Status:** Complete ✅

**Obiettivo:** Sostituire fee hardcoded con fee tier per PnL non realizzato durante il loop di monitoraggio candele.

**File:** `synthtrade/backend/app/scalping/router.py`

**Righe target:** 1066-1067 — calcolo PnL non realizzato durante il loop di monitoraggio candele

**Caso B — PnL non realizzato (posizione ancora aperta, mostrato live in UI):**
- ✅ Fee di entrata: commissione reale del fill di apertura (TASK-876), altrimenti fee tier
- ✅ Fee di uscita: fee tier certo recuperato in Fase 2 (TASK-877) come "costo di chiusura atteso al tier corrente"
- ✅ Conversione automatica BNB→USDC quando necessario
- ✅ Logging debug per tracciamento

**Modifiche:**
- Sostituito hardcode `fees = (entry_val * 0.001) + (current_val * 0.001)` con logica reali/attese
- Entry: usa `pos.entry_commission` se disponibile, altrimenti fee tier (taker)
- Exit: usa fee tier (maker per OCO orders)
- Aggiunto logging debug per tracciamento

**Verifica:** ✅ Completato - PnL non realizzato coerente con fee tier

---

### TASK-882 — Fee reali: Fase 3E - Sostituire hardcode righe 1629-1630 (2026-06-24) ✅

**Status:** Complete ✅

**Obiettivo:** Sostituire fee hardcoded con fee tier per PnL non realizzato in altro punto del loop monitoraggio.

**File:** `synthtrade/backend/app/scalping/router.py`

**Righe target:** 1629-1630 — calcolo PnL non realizzato, altro punto del loop monitoraggio

**Caso B — PnL non realizzato:**
- ✅ Stesso trattamento del TASK-881
- ✅ Fee entrata reale + fee uscita attesa (fee tier)
- ✅ Conversione automatica BNB→USDC quando necessario
- ✅ Logging debug per tracciamento

**Modifiche:**
- Sostituito hardcode `fees = (entry_val * 0.001) + (current_val * 0.001)` con logica reali/attese
- Entry: usa `pos.entry_commission` se disponibile, altrimenti fee tier (taker)
- Exit: usa fee tier (maker per OCO orders)
- Aggiunto logging debug per tracciamento

**Verifica:** ✅ Completato - Coerenza con TASK-881 e dati UI

---

### TASK-883 — Fee reali: Fase 3F - Sostituire hardcode righe 1736-1737 (2026-06-24) ✅

**Status:** Complete ✅

**Obiettivo:** Sostituire fee hardcoded con fee tier per PnL non realizzato nel consumo del trade_queue (per CVD/broadcast).

**File:** `synthtrade/backend/app/scalping/router.py`

**Righe target:** 1736-1737 — calcolo PnL non realizzato nel consumo del trade_queue (per CVD/broadcast)

**Caso B — PnL non realizzato:**
- ✅ Stesso trattamento del TASK-881
- ✅ Fee entrata reale + fee uscita attesa (fee tier)
- ✅ Conversione automatica BNB→USDC quando necessario
- ✅ Logging debug per tracciamento

**Modifiche:**
- Sostituito hardcode `fees = (entry_val * 0.001) + (current_val * 0.001)` con logica reali/attese
- Entry: usa `pos.entry_commission` se disponibile, altrimenti fee tier (taker)
- Exit: usa fee tier (maker per OCO orders)
- Aggiunto logging debug per tracciamento

**Verifica:** ✅ Completato - Broadcast CVD coerente con fee tier

---

### TASK-886 — Fee reali: Fase 4B - Popolare entry_commission con dato reale (2026-06-24) ✅

**Status:** Complete ✅

**Obiettivo:** Popolare `pos_obj.entry_commission` con la commissione reale dell'ordine market invece di lasciarlo None (che attiva sempre il fallback a fee tier).

**File modificati:**
- `synthtrade/backend/app/execution/exchange.py` — `place_market_order` ora estrae e restituisce commission/commission_asset
- `synthtrade/backend/app/scalping/engine/position_manager.py` — `open_position` accetta parametri opzionali entry_commission/entry_commission_asset
- `synthtrade/backend/app/scalping/router.py` — flusso LIVE passa commissione reale a `open_position`; flusso PAPER mantiene None (fallback corretto)
- `synthtrade/backend/app/scalping/router.py` — aggiunto flag `fee_tier_certified` nello stato sessione per tracciare fallback silenziosi

**Modifiche:**
1. **exchange.py**: `place_market_order` estrae fee da CCXT response (order["fee"] o order["fees"]), somma per asset, logga warning se multi-asset o nessun dato
2. **position_manager.py**: `open_position` accetta parametri opzionali e li passa al costruttore Position
3. **router.py** (flusso LIVE): dopo `place_market_order`, estrae `commission` e `commission_asset` e li passa a `open_position`
4. **router.py** (flusso PAPER): nessuna modifica — fallback a fee tier rimane intenzionale per paper mode
5. **router.py** (fee tier): aggiunto `_execution_state["fee_tier_certified"]` per tracciare se il fee tier è certificato da Binance o fallback non verificato; esposto in GET /session

**Verifica:** Al prossimo trade chiuso live, verificare nel log che `entry_commission` sia popolato con valore reale (non None)

---

### TASK-884 — Fee reali: Fase 3G - Sostituire hardcode righe 2768-2769 (2026-06-24) ✅

**Status:** Done

**Obiettivo:** Sostituire fee hardcoded con fee tier per PnL in endpoint di lettura stato.

**File:** `synthtrade/backend/app/scalping/router.py`

**Righe target:** 2768-2769 — calcolo PnL in endpoint `/position`

**Caso B — PnL non realizzato:**
- ✅ Stesso trattamento del TASK-881
- ✅ Fee entrata reale + fee uscita attesa (fee tier)
- ✅ Conversione automatica BNB→USDC quando necessario (con limitazioni per endpoint sincrono)
- ✅ Logging debug per tracciamento

**Modifiche:**
- Sostituito hardcode `fees = (entry_val * 0.001) + (current_val * 0.001)` con logica reali/attese
- Entry: usa `pos.entry_commission` se disponibile, altrimenti fee tier (taker)
- Exit: usa fee tier (maker per OCO orders)
- Nota: per endpoint sincrono non è possibile chiamare exchange per conversione BNB→USDC, assume valore già convertito

**Verifica:** ✅ Completato - Endpoint `/position` restituisce PnL coerente con fee tier

---

### TASK-885 — Fee reali: Fase 4 - UI: mostrare target netti TP/SL separati da realizzato (2026-06-24) ✅

**Status:** Complete ✅

**Obiettivo:** La card POSITION deve mostrare TP%/SL% che riflettono il guadagno/perdita netto reale atteso, non il movimento di prezzo lordo.

**File:** `synthtrade/backend/app/scalping/router.py` (backend) + frontend Angular

**Intervento Backend:**
1. ✅ Aggiunto calcolo target netti TP/SL nel blocco WebSocket iniziale (righe 134-153)
2. ✅ Già implementato nei `position_update` events (righe 1188-1211 e 1787-1795)
3. ✅ Calcolo fee round-trip: `(entry_fee_rate + exit_fee_rate) * 100`
4. ✅ Net percentages: `sl_pct_net = (sl_pct * 100) - fee_round_trip`, `tp_pct_net = (tp_pct * 100) - fee_round_trip`

**Intervento Frontend (Angular):**
1. ✅ Model position già include campi `stop_loss_pct_net` e `take_profit_pct_net`
2. ✅ PositionTickerComponent aggiornato per mostrare percentuali nette con fallback a lordi
3. ✅ Template: `{{ position.stop_loss_pct_net ?? position.stop_loss_pct | number:'1.2-2' }}%`

**Verifica:** ✅ Completato - Backend invia target netti, frontend mostra con fallback sicuro

---

### TASK-814 — Live Mode Bug Fixes (2026-06-05 → 2026-06-09) ✅

**Status:** Complete ✅

Fix issues identified from live session logs:
- [x] **Issue 1-8**: All fixed — WS handshake, RSS/CoinGecko/Whale pollers, OCO balance settlement, logging visibility, session restore pipeline, minNotional, OCO post-fee balance
- [x] Update docs and commit

---

### TASK-815 — SignalScoreEngine: soglia dinamica e pesi calibrati (2026-06-09) ✅

**Status:** Complete ✅
**Commit:** `123976e`
**File:** `signal_score_engine.py`

**Modifiche:**
- Pesi ridistribuiti (funding_rate 0.20, cvd 0.20, OI 0.15, L/S 0.15, F&G 0.15, whale 0.10, sentiment 0.05, onchain 0.0)
- Normalizzazione USDC→USDT per collector futures
- Soglia scalata: `effective_threshold = threshold * coverage`

---

### TASK-816 — RSI Bollinger: soglie calibrate per mercato ranging (2026-06-09) ✅

**Status:** Complete ✅
**Commit:** `123976e`
**File:** `rsi_bollinger.py`

**Modifiche:**
- RSI_OVERSOLD: 30 → 38
- RSI_OVERBOUGHT: 70 → 62
- BB tolleranza: 1.01 → 1.015
- Confidence: 0.7 → 0.6

---

### TASK-817 — SignalAggregator: bypass mean-reversion per ranging (2026-06-09) ✅

**Status:** Complete ✅
**Commit:** `123976e`
**File:** `signal_aggregator.py`

**Modifiche:**
- `MEAN_REVERSION_STRATEGIES = ("rsi_bollinger", "stoch_rsi_bb_squeeze")`
- Permette SELL da mean-reversion in ranging quando bias intelligence è bullish
- Permette BUY da mean-reversion in ranging quando bias intelligence è bearish

---

### TASK-818 — StrategySelector: mapping regimi corretto (2026-06-09) ✅

**Status:** Complete ✅
**Commit:** `123976e`
**File:** `strategy_selector.py`

**Modifiche:**
- `ranging` → `rsi_bollinger`
- `volatile` → `stoch_rsi_bb_squeeze`
- `trending_up/down` → `ema_cross`
- `unknown` → `momentum_base`

---

### TASK-819 — Supervisor: cooldown e regime validation (2026-06-09) ✅

**Status:** Complete ✅
**Commit:** `123976e`
**File:** `supervisor_scheduler.py`, `supervisor_client.py`

**Modifiche:**
- Cooldown cambio strategia: 20 minuti
- Cooldown aggiornamento parametri: 10 minuti
- Regime validation: blocca strategie non compatibili col regime corrente
- Se strategia proposta non ammessa, resetta cooldown per prossimo tick valido
- `REGIME_ALLOWED_STRATEGIES` mapping completo nel prompt AI

---

### TASK-820 — EMA Cross: rimuovere slope filter + registrazione nuove strategie (2026-06-09) ✅

**Status:** Complete ✅
**Commit:** `123976e`
**File:** `ema_cross.py`, `stoch_rsi_bb_squeeze.py`, `registry.py`

**Modifiche:**
- `ema_cross.py`: Rimosso MIN_SLOPE e logica pendenza — segnale BUY se EMA9 > EMA21, SELL se EMA9 < EMA21
- `stoch_rsi_bb_squeeze.py`: Creata strategia StochRSI + BB Squeeze per regime volatile
- `registry.py`: Registrata `stoch_rsi_bb_squeeze`

---

### TASK-821 — Frontend: default BNBUSDC e rimozione initial load (2026-06-09) ✅

**Status:** Complete ✅

**Modifiche:**
- Default symbol: BTCUSDT → BNBUSDC in tutti i componenti scalping
- Default strategia: scalping_v2 → momentum_base
- Dropdown strategie: aggiunto `stoch_rsi_bb_squeeze`, rimosso `scalping_v2`, nomi normalizzati
  (`RSI + Bollinger` invece di `RSI con Bollinger`, `StochRSI BB Squeeze` invece di `Stoch RSI con BB Squeeze`)
- Rimosso initial load da TradeLog e PerformancePanel (attendono sessione attiva)
- `strategy-panel.component.ts`: fallback `STRATEGY_DEFAULTS['momentum_base']` invece di `scalping_v2`

**File modificati:**
- `session-controls.component.ts`
- `live-chart.component.ts`
- `market-intel-panel.component.ts`
- `session-api.service.ts`
- `trade-log.component.ts`
- `performance-panel.component.ts`
- `strategy-panel.component.ts`

---

### TASK-823 — Fix persistenza sessione scalping: saldo, trade history, posizione aperta (2026-06-10) ✅

**Status:** Complete ✅

**Bug 1 — Saldo 10,000 falso dopo restart:**
- `_restore_scalping_session()` ora inizializza `BinanceExchangeAdapter` e fa `fetch_balance()` da Binance per sessioni live
- Usa `_normalize_binance_total_balance()` e `_select_preferred_quote_balance()` per trovare il saldo corretto

**Bug 2 — Lista trade vuota dopo restart:**
- Step 5: carica fino a 200 trade dalla tabella `scalping_trades` via `session_id`
- Popola `_execution_state["trade_history"]` in memoria

**Bug 3 — Performance vuota dopo restart:**
- Stessa causa del Bug 2 — dipende da `trade_history` popolato

**Bug 4 — Trade persi al restart (posizione aperta non persistita):**
- Nuova funzione `_save_open_position_to_db()`: salva posizione aperta su DB con `status='open'` subito dopo `pm.open_position()`
- Nuova funzione `_update_closed_position_in_db()`: UPDATE della stessa riga alla chiusura (anziché INSERT)
- La funzione `_close_position_and_record()` ora usa `_update_closed_position_in_db()` invece di INSERTare ex-novo
- Step 7: carica eventuale posizione con `status='open'` da DB e la ripristina in `PositionManager`
- `_restore_scalping_session()` resa async per supportare le chiamate CCXT

**Migration 010:** Aggiunta colonna `trade_value FLOAT` a `scalping_sessions`

**File modificati:**
- `synthtrade/backend/app/main.py` — `_restore_scalping_session()` async, Steps 5-8
- `synthtrade/backend/app/scalping/router.py` — funzioni helper persistenza

---

---

## Epica 800 — OCO Flow + UDS Definitivo

### TASK-824 — Pulizia codice legacy OCO sintetico e polling (2026-06-12)

**Status:** Complete ✅

**Scope completato:**
- [x] Rimosso `_place_oco_synthetic_inverted()` da `exchange.py`
- [x] Rimosso `_place_oco_synthetic()` da `exchange.py`
- [x] Rimosso polling OCO su ogni candela in `router.py` (sezione `FIX-2026-06-05: Sync OCO`)
- [x] Rimossi `place_stop_loss_order()`, `place_limit_order()` da `exchange.py`
- [x] Rimossi dal `ExchangeProtocol` i metodi non più necessari
- [x] `place_oco_order()` ora lancia `ExchangeOrderError` se OCO fallisce (no silent fallback)

---

### TASK-825 — Schema DB: aggiungere tp_price, sl_price a scalping_positions (2026-06-12)

**Status:** Complete ✅

**Scope completato:**
- [x] Migration SQL: `supabase/migrations/20260612_oco_flow_v2.sql`
  - Colonne aggiunte: `tp_price`, `sl_price`, `oco_order_list_id`, `sl_order_id`, `tp_order_id`
- [x] `_save_open_position_to_db()` aggiornata con nuovi parametri `tp_price`, `sl_price` e OCO IDs

---

### TASK-826 — Implementare `_on_order_update` in router.py (2026-06-12)

**Status:** Complete ✅

**Scope completato:**
- [x] Definito `_on_order_update(event)` in `router.py`
- [x] Gestione `status == "filled"`: determina TP/SL da orderId, calcola PnL, aggiorna DB, chiude posizione, broadcast UI
- [x] Gestione `status == "expired"`: log informativo, nessuna azione
- [x] Guard: se `pos` è None o `oco_order_list_id` non corrisponde → return silenzioso

---

### TASK-827 — UDS singleton check + avvio post OCO riuscito (2026-06-12)

**Status:** Complete ✅

**Scope completato:**
- [x] Rimosso avvio UDS immediato da `action == "start"` in `control_session()`
- [x] Aggiunta funzione `_start_uds_if_needed()` con singleton check
- [x] UDS avviato SOLO dopo OCO confermato (Caso A) nel `_candle_processor()`
- [x] UDS avviato in restore sessione se posizione aperta trovata
- [x] `on_reconnect_sync=_on_uds_reconnect_sync` passato a `uds.start()`
- [x] UDS stoppato correttamente in `action == "stop"`

---

### TASK-828 — Market sell emergenza con `_get_available_base_balance()` (2026-06-12)

**Status:** Complete ✅

**Scope completato:**
- [x] Funzione `_handle_oco_failed(exchange, symbol)` implementata in `router.py`
- [x] Cancella ordini orfani via `get_open_orders` + `cancel_order`
- [x] Market sell con `_get_available_base_balance()` (qty reale post-fee)
- [x] Broadcast UI `error` con `code: "OCO_FAILED"`
- [x] Nessun salvataggio DB — `continue` nel flusso live

---

### TASK-829 — Stop sessione: wait conferma cancellazione OCO prima di market sell (2026-06-12)

**Status:** Complete ✅

**Scope completato:**
- [x] Dopo `cancel_open_orders()` in stop sessione: `asyncio.sleep(0.5)`
- [x] Loop di verifica max 3 retry × 0.3s che `get_open_orders()` sia vuoto
- [x] Solo dopo conferma → prosegue con `_close_position_and_record()`

---

### TASK-830 — UDS reconnect sync: parametro `on_reconnect_sync` (2026-06-12)

**Status:** Complete ✅

**Scope completato:**
- [x] `self._on_reconnect_sync: Optional[Callable] = None` in `UserDataStreamManager.__init__`
- [x] Parametro `on_reconnect_sync` aggiunto a `uds.start()`
- [x] Dopo `_reconnect()` in `_listen_loop()`: chiamata `await self._on_reconnect_sync()` se impostato
- [x] Implementata `_on_uds_reconnect_sync()` in `router.py`:
  - Query specifica per `tp_order_id` / `sl_order_id` via `_fetch_fill_price_by_order_id()`
  - Fallback a `fetch_closed_orders` se IDs non disponibili
  - Chiude posizione, aggiorna DB, broadcast UI

---

### TASK-831 — Restore sessione: query specifica per sl_order_id/tp_order_id (2026-06-12)

**Status:** Complete ✅

**Scope completato:**
- [x] In `_restore_scalping_session()`: ripristina `oco_order_list_id`, `sl_order_id`, `tp_order_id` dal DB sul position object
- [x] `exchange._fetch_fill_price_by_order_id()` implementato in `exchange.py`
- [x] Restore usa `_fetch_fill_price_by_order_id()` invece di `fetch_my_trades` generico
- [x] Fallback a `fetch_closed_orders` filtrato per side se IDs non trovano match
- [x] UDS riavviato post-restore se posizione aperta trovata

---

### TASK-832 — Session Load Guard: bloccare trade durante avvio/restore sessione (2026-06-15)

**Status:** Complete ✅

**Scope completato:**
- [x] Aggiunta `SessionLoadGuard` in `_execution_state["session_load_guard"]`
- [x] Fasi richieste: `db_phase`, `exchange_phase`, `position_phase`, `buffer_phase`, `pipeline_phase`
- [x] Timeout 30s con log periodici ogni 5s e stato `failed` se una fase non completa
- [x] `_restore_scalping_session()` marca `loading` all'avvio e completa DB/exchange/position
- [x] `control_session(action="start")` resetta il guard, completa exchange/position e DB dopo insert
- [x] `_start_ws_broadcast()` completa `buffer_phase` dopo warmup e `pipeline_phase` dopo `BinanceWSClient.start()`
- [x] Gate in `_candle_processor`, `_trade_processor` e trade live inline: nessun trade finché `guard.is_ready()` è false
- [x] WebSocket `session_loading` e endpoint `GET /scalping/debug/session-load` per osservabilità
- [x] Tentativi trade bloccati salvati in `deque(maxlen=100)` per evitare crescita illimitata

**File modificati:**
- `synthtrade/backend/app/scalping/session_load_guard.py`
- `synthtrade/backend/app/scalping/router.py`
- `synthtrade/backend/app/main.py`
- `docs/TASKS.md`
- `docs/OCO_FLOW.md`

---

---

## Epica 800 — Supervisor Intelligence + Fix Critici (Piano v3.1)

### TASK-833 — FASE A1: Rimuovere force_execute hardcoded (2026-06-15)

**Status:** Done ✅  
**Completato:** 2026-06-15
**Priorità:** CRITICA — bypassa SignalAggregator, RiskManager e tutti i filtri  
**Fase:** A (prerequisito per tutto il resto)  
**Stima:** 0.5h  
**File coinvolti:** `router.py`, `signal_aggregator.py`

**Scope:**
- [ ] Rimuovere `execution_loop.force_execute = True` da `router.py`
- [ ] Rimuovere attributo `self.force_execute` dalla classe `ExecutionLoop`
- [ ] Rimuovere il "Caso 0: FORCE_EXECUTE" da `signal_aggregator.py`
- [ ] Verifica: avviare sessione paper e controllare che non appaia `LIVE MODE: ... (intelligence bypassed)`

---

### TASK-834 — FASE A2: Supervisor interval da .env (2026-06-15)

**Status:** Done ✅  
**Completato:** 2026-06-15
**Priorità:** CRITICA — supervisor gira ogni 45s invece di 10min, spreca API  
**Fase:** A (prerequisito per tutto il resto)  
**Stima:** 0.5h  
**File coinvolti:** `router.py`, `supervisor_scheduler.py`, `.env`, `config.py`

**Scope:**
- [ ] Aggiungere `SCALPING_SUPERVISOR_INTERVAL_SEC=600` a `.env`
- [ ] Aggiungere `SCALPING_SUPERVISOR_INTERVAL_SEC`, `SCALPING_STRATEGY_COOLDOWN_SEC`, `SCALPING_PARAM_UPDATE_COOLDOWN_SEC` a `config.py`
- [ ] Sostituire `interval_seconds=45` con `settings.SCALPING_SUPERVISOR_INTERVAL_SEC` nei 2 punti di istanziazione `SupervisorScheduler` in `router.py`
- [ ] Sostituire costanti hardcoded `STRATEGY_CHANGE_COOLDOWN = 1200` e `PARAM_UPDATE_COOLDOWN = 600` in `supervisor_scheduler.py` con valori da `settings`
- [ ] Verifica: log supervisor ogni ~600 secondi, missed jobs APScheduler spariti

---

### TASK-835 — FASE B1-B2: .env completo e config.py aggiornato (2026-06-15)

**Status:** Done ✅  
**Completato:** 2026-06-15
**Priorità:** Alta — prerequisito per B3-B5  
**Fase:** B (dopo Fase A)  
**Stima:** 1h  
**File coinvolti:** `.env`, `config.py`

**Scope:**
- [ ] Sostituire sezione scalping in `.env` con versione completa e commentata (da piano §B1)
- [ ] Aggiungere/sostituire sezione scalping in `config.py` con tutti i campi tipizzati (da piano §B2)
- [ ] Verificare compatibilità con pattern `settings.scalping.*` se usato nel codice esistente

---

### TASK-836 — FASE B3: Migration DB tabella `scalping_runtime_config` (2026-06-15)

**Status:** Done ✅  
**Completato:** 2026-06-15
**Priorità:** Alta  
**Fase:** B  
**Stima:** 0.5h  
**File coinvolti:** nuova migration Supabase

**Scope:**
- [ ] Creare migration SQL con `CREATE TABLE scalping_runtime_config (key, value, value_type, description, updated_at)`
- [ ] Inserire valori di default (specchio del .env) per tutti i 15 parametri `[RUNTIME]`
- [ ] Applicare migration su Supabase

---

### TASK-837 — FASE B4: Nuovo `ScalpingConfigLoader` (2026-06-15)

**Status:** Done ✅  
**Completato:** 2026-06-15
**Priorità:** Alta  
**Fase:** B  
**Stima:** 1h  
**File coinvolti:** nuovo `app/scalping/config_loader.py`

**Scope:**
- [ ] Creare `app/scalping/config_loader.py` con classe `ScalpingConfigLoader`
- [ ] Implementare `_load()`: step 1 da settings, step 2 override da DB con type-casting
- [ ] Implementare `reload()` per aggiornamento runtime senza restart
- [ ] Implementare proprietà typed per tutti i parametri configurabili
- [ ] Esporre singleton `get_scalping_config()`

---

### TASK-838 — FASE B5: Endpoint API config scalping (2026-06-15)

**Status:** Done ✅  
**Completato:** 2026-06-15
**Priorità:** Media  
**Fase:** B  
**Stima:** 0.5h  
**File coinvolti:** `router.py` o nuovo `config_scalping_api.py`

**Scope:**
- [ ] `GET /api/scalping/config` — ritorna config corrente merge .env+DB
- [ ] `POST /api/scalping/config/{key}` — aggiorna valore nel DB e ricarica
- [ ] `POST /api/scalping/config/reload` — ricarica senza restart
- [ ] Test: modificare un valore via POST e verificare che il reload abbia effetto

---

### TASK-839 — FASE C1: Sostituire Fear & Greed con alternative.me (2026-06-15)

**Status:** Done ✅  
**Completato:** 2026-06-15
**Priorità:** Alta — F&G congelato a 8, dato falso guida tutte le decisioni AI  
**Fase:** C (dopo Fase B)  
**Stima:** 1h  
**File coinvolti:** `app/scalping/intelligence/collectors/fear_greed.py`

**Scope:**
- [ ] Riscrivere `FearGreedCollector` per usare `https://api.alternative.me/fng/?limit=1` (gratuita, no API key)
- [ ] Implementare cache intraday con TTL 4h
- [ ] Implementare `value_to_score(value)` con logica contrarian (-100..+100)
- [ ] Impostare `SCALPING_FEAR_GREED_SOURCE=alternative_me` in `.env`
- [ ] Verifica log: `FearGreed aggiornato: XX (Fear/Greed)` con valore reale, non 8

---

### TASK-840 — FASE C2: Fix copertura whale collector disabilitato (2026-06-15)

**Status:** Done ✅  
**Completato:** 2026-06-15
**Priorità:** Alta — peso 0.10 fantasma riduce coverage artificialmente  
**Fase:** C  
**Stima:** 0.5h  
**File coinvolti:** `signal_score_engine.py`

**Scope:**
- [ ] Escludere whale da `active_collectors` se `settings.SCALPING_WHALE_ENABLED=False`
- [ ] Correggere formula coverage: `total_weight_configured` calcolato solo sui collector attivi con peso > 0
- [ ] Aggiungere `SCALPING_WHALE_ENABLED=false` a `.env`
- [ ] Verifica: coverage non più penalizzata dal whale assente

---

### TASK-841 — FASE D1: Log diagnostica score engine (2026-06-15)

**Status:** Done ✅  
**Completato:** 2026-06-15
**Priorità:** Alta — senza diagnosi non si sa se i score sono in [-1,+1] o [-100,+100]  
**Fase:** D (dopo Fase C)  
**Stima:** 0.5h  
**File coinvolti:** `signal_score_engine.py`

**Scope:**
- [ ] Aggiungere log DEBUG in `compute()` con breakdown raw score per collector
- [ ] Log deve mostrare: `breakdown raw`, `weighted_avg`, `total_weight`, `coverage`
- [ ] Avviare sessione paper e analizzare 2-3 cicli di output
- [ ] Determinare Scenario A (scala già -100..+100) o Scenario B (scala -1..+1)

---

### TASK-842 — FASE D2-D3: Fix normalizzazione score e soglie (2026-06-15)

**Status:** Done ✅  
**Completato:** 2026-06-15
**Priorità:** Alta — score mai supera 1.0 con soglia a 15, nessun trade passa il gate  
**Fase:** D (dopo TASK-841)  
**Stima:** 2h  
**File coinvolti:** `signal_score_engine.py`, `.env`

**Scope:**
- [ ] In base alla diagnosi D1: se Scenario B, scalare ogni `*_to_score()` da [-1,+1] a [-100,+100]
- [ ] Verificare che `weighted_avg` non venga diviso per 100 prima di confronto soglia
- [ ] Aggiornare `SCALPING_SIGNAL_STRENGTH_THRESHOLD=15.0` in `.env` con commenti di interpretazione
- [ ] Verifica log: score appare in range [-100,+100]

---

### TASK-843 — FASE D4: SignalAggregator min_collectors da config (2026-06-15)

**Status:** Done ✅  
**Completato:** 2026-06-15
**Priorità:** Media  
**Fase:** D  
**Stima:** 0.25h  
**File coinvolti:** `signal_aggregator.py`

**Scope:**
- [ ] Sostituire `num_collectors_responded <= 3` hardcoded con `get_scalping_config().min_collectors`
- [ ] Importare `get_scalping_config` da `app.scalping.config_loader`

---

### TASK-844 — FASE E1-E2: Supervisor — contesto arricchito con performance sessione (2026-06-15)

**Status:** Complete ✅
**Completato:** 2026-06-19 (implementato come TASK-860)

Implementato in TASK-860: `build_scalping_context()` calcola `session_performance` da `trade_history` in-memory, con fallback DB. Sezione `=== PERFORMANCE SESSIONE ===` nel prompt supervisor.

---

### TASK-845 — FASE E3: Aggiornare system prompt supervisor (2026-06-15)

**Status:** Complete ✅
**Completato:** 2026-06-19 (implementato come TASK-861)

Implementato in TASK-861: `_SUPERVISOR_SYSTEM_PROMPT` aggiornato con sezione `⚠️ REGOLA QUANDO NON AGIRE` (< 5 trade, win_rate > 60%, coverage < 50%, loop decisioni, score neutrale).

---

### TASK-846 — FASE F1: Migration DB tabella `supervisor_memory` (2026-06-15)

**Status:** Complete ✅
**Completato:** 2026-06-16

Migration `supabase/migrations/20260616_supervisor_memory.sql` applicata. Tabella presente su Supabase con tutti i campi pianificati.

---

### TASK-847 — FASE F2-F3: Persistenza e caricamento memoria supervisor (2026-06-15)

**Status:** Complete ✅
**Completato:** 2026-06-19 (implementato come TASK-862)

Implementato in TASK-862: `_save_decision_to_memory()` popola `session_perf` reale. `build_scalping_context()` carica ultimi 10 record da `supervisor_memory` e li mostra nel prompt come `=== DECISIONI PRECEDENTI ===`.

---

### TASK-848 — FASE F4: Job APScheduler verifica outcome decisioni (2026-06-15)

**Status:** Complete ✅
**Completato:** 2026-06-19 (implementato come TASK-863)

Implementato in TASK-863: `verify_supervisor_outcomes_job()` in `scalping_jobs.py`, registrato ogni 5 minuti. Query decisioni applicate 25-35 min fa, classifica `positive/negative/neutral`.

---

### TASK-849 — Fix log soglia in SignalAggregator (2026-06-16)

**Status:** Complete ✅

**Problema:** Il log mostrava `🔴 BLOCK: score -9.5 < soglia 9.5` usando `signal_strength` (valore assoluto dello score) come soglia, facendo sembrare che la soglia fosse ancora scalata dynamicamente. In realtà la soglia era già fissa a 15.0.

**Fix:** Sostituito `market_score.signal_strength` con `settings.scalping.SCALPING_SIGNAL_STRENGTH_THRESHOLD` nel messaggio di log.

**Log dopo il fix:** `🔴 BLOCK: score -9.4 < threshold 15.0 (|score|=9.4) (bias=neutral)` ✅

---

### TASK-850 — Threshold dinamico da ConfigLoader in SignalScoreEngine (2026-06-16)

**Status:** Complete ✅

**Problema:** `SignalScoreEngine` leggeva la soglia da `settings.__init__()` e non si aggiornava a runtime. Il Supervisor non poteva modificarla.

**Fix:** `get_snapshot()` ora legge la soglia da `ScalpingConfigLoader` a ogni ciclo:
```python
config_loader = get_scalping_config()
runtime_threshold = config_loader.signal_strength_threshold
```
Un cambio su DB (via `POST /api/scalping/config/signal_strength_threshold`) ha effetto immediato, senza restart.

---

### TASK-851 — Azione update_threshold nel Supervisor AI (2026-06-16)

**Status:** Complete ✅

**Nuova azione** `update_threshold` nel repertorio del Supervisor.

**File modificati:**
- `app/scalping/models/supervisor.py` — regex action include `update_threshold`
- `app/scalping/supervisor/parameter_updater.py` — nuovo metodo `_update_threshold()`: upsert su `scalping_runtime_config` + reload config loader
- `app/scalping/supervisor/supervisor_scheduler.py` — broadcast mapping per nuova azione
- `app/ai/supervisor_context.py` — `current_threshold` aggiunto al contesto del Supervisor
- `app/scalping/supervisor/supervisor_client.py` — prompt aggiornato con regole per update_threshold, threshold mostrato nel context formattato
- `app/ai/eval_parser.py` — `update_threshold` aggiunto a `_VALID_ACTIONS`

**Regole nel prompt:**
- Se score sempre sotto soglia ma segnale tecnico forte → abbassa (10.0 consigliato)
- Se molti falsi segnali → alza (18.0 consigliato)
- Se coverage < 60% → non abbassare (dati inaffidabili)
- Usa update_threshold prima di change_strategy come alternativa conservativa

---

### TASK-852 — Fase 0: Context arricchito threshold per Supervisor (2026-06-16)

**Status:** Complete ✅

**Problema:** Il Supervisor non conosceva il valore corrente della soglia quando prendeva decisioni. Senza vedere score, gap, collector attivi/assenti, non poteva ragionare in modo informato.

**Cosa aggiunto al prompt utente:**
```
=== CONFIGURAZIONE INTELLIGENCE ===
Soglia score minima (threshold): 15.0
Score attuale: -9.5 (|score|=9.5)
Gap per passare il gate: -5.5 punti
Bias: neutral
Collector attivi: 5/7 (funding_rate, cvd, open_interest, fear_greed, sentiment)
Collector assenti: whale
Coverage: 71%
✅ Coverage buono — modifiche soglia consentite
```

**File modificati:**
- `app/ai/supervisor_context.py` — `threshold_gap`, `active_collectors`, `missing_collectors` nel context
- `app/scalping/supervisor/supervisor_client.py` — `_format_context()` sezione `=== CONFIGURAZIONE INTELLIGENCE ===`

---

### TASK-853 — Limiti sicurezza e cooldown per update_threshold (2026-06-16)

**Status:** Complete ✅

**Problema:** Il Supervisor poteva azzerare la soglia (trade senza filtro) o impostarla a valori irraggiungibili (nessun trade). Poteva anche cambiarla a ogni tick, causando instabilità.

**Aggiunte:**
1. **Limiti di sicurezza** in `parameter_updater._update_threshold()`: soglia clampata tra [5.0, 30.0]
2. **Cooldown 30 minuti** in `supervisor_scheduler.py`: `THRESHOLD_CHANGE_COOLDOWN = 1800` + tracking `_last_threshold_change`
3. **Prompt aggiornato** con regole aggiuntive:
   - Score stabile tra -5 e +5 per 10+ candele in ranging → abbassa a 8-10
   - Trade in perdita consecutiva → alza di 2-3 punti
   - Non modificare più di una volta ogni 30 minuti
   - Limiti: min 5.0, max 30.0

**File modificati:**
- `app/scalping/supervisor/parameter_updater.py` — clamp [5.0, 30.0]
- `app/scalping/supervisor/supervisor_scheduler.py` — cooldown 30min
- `app/scalping/supervisor/supervisor_client.py` — prompt esteso


---


### TASK-854: Fix dust residue on live trades

**Status:** Complete ✅

- math.floor per qty calculation pre-buy
- exec_qty = _qty_precise invece di market_res.quantity
- Verificare: BUY qty == OCO qty su prossimo trade live


---

## Epica 800 — Audit Fix Scalping Module (2026-06-19)

### TASK-855 — BUG CRITICO: Rimuovere SL/TP software da _trade_processor in live mode (2026-06-19)

**Status:** Complete ✅

- [x] In `_trade_processor()`: aggiunto guard `if _mode_trade != "live"` attorno al blocco `hit_sl`/`hit_tp`
- [x] In live mode SL/TP sono gestiti esclusivamente da OCO Binance via UDS (`_on_order_update`)
- [x] Previene doppia vendita: software close + OCO close su stesso asset

**File:** `synthtrade/backend/app/scalping/router.py`

---

### TASK-856 — BUG: Fix broadcast signal type (sempre BUY) (2026-06-19)

**Status:** Complete ✅

- [x] Sostituito `"BUY" if decision.confidence > 0 else "SELL"` con `decision.signal_type`
- [x] Il frontend ora riceve il tipo segnale corretto (BUY/SELL/CLOSE)

**File:** `synthtrade/backend/app/scalping/router.py`

---

### TASK-857 — BUG: Fix `get_holdings()` in BinanceExchangeAdapter (2026-06-19)

**Status:** Complete ✅

- [x] Corretto accesso a `balance["free"]` invece di `balance["total"][asset]["free"]`
- [x] Previene `TypeError: float object is not subscriptable`

**File:** `synthtrade/backend/app/execution/exchange.py`

---

### TASK-858 — BUG: Fix session_perf in supervisor_memory (2026-06-19)

**Status:** Complete ✅

- [x] `_save_decision_to_memory()` ora accetta parametro `trade_history: list`
- [x] `_tick()` recupera `trade_history` da `_execution_state` del router e la passa esplicitamente
- [x] `session_perf` non è più sempre vuoto nel DB

**File:** `synthtrade/backend/app/scalping/supervisor/supervisor_scheduler.py`

---

### TASK-859 — BUG: Fix SupervisorScheduler score_engine per simbolo corretto (2026-06-19)

**Status:** Complete ✅

- [x] `SupervisorScheduler.__init__`: `score_engine or SignalScoreEngine(symbol=symbol)` (era default BTCUSDT)
- [x] In `router.py`: entrambe le istanziazioni del supervisor passano `score_engine=_execution_state.get("signal_engine")`

**File:** `synthtrade/backend/app/scalping/supervisor/supervisor_scheduler.py`, `router.py`

---

### TASK-860 — Supervisor context arricchito con performance sessione (2026-06-19)

**Status:** Complete ✅

- [x] `supervisor_scheduler._tick()` recupera `trade_history` e la passa a `client.decide()`
- [x] `supervisor_client.decide()` accetta `trade_history` e la passa a `build_scalping_context()`
- [x] `build_scalping_context()` calcola `session_performance` in-memory (total_trades, win_rate, pnl, last_5)
- [x] `_format_context()` mostra sezione `=== PERFORMANCE SESSIONE ===`

**File:** `supervisor_scheduler.py`, `supervisor_client.py`, `supervisor_context.py`

---

### TASK-861 — Aggiornare system prompt supervisor: regole "quando NON agire" (2026-06-19)

**Status:** Complete ✅

- [x] Aggiunta sezione `⚠️ REGOLA QUANDO NON AGIRE` nel `_SUPERVISOR_SYSTEM_PROMPT`
- [x] Regole: < 5 trade → no_action, win_rate > 60% → no_action, coverage < 50% → no_action, loop decisioni → no_action

**File:** `synthtrade/backend/app/scalping/supervisor/supervisor_client.py`

---

### TASK-862 — Caricamento storico decisioni supervisor nel context (2026-06-19)

**Status:** Complete ✅

- [x] `build_scalping_context()` carica ultimi 10 record da `supervisor_memory` per symbol/session
- [x] `_format_context()` mostra sezione `=== DECISIONI PRECEDENTI (ultime 10) ===`
- [x] Tabella `supervisor_memory` già presente (migration 20260616 applicata)

**File:** `supervisor_context.py`, `supervisor_client.py`

---

### TASK-863 — Job APScheduler verifica outcome decisioni supervisor (2026-06-19)

**Status:** Complete ✅

- [x] `verify_supervisor_outcomes_job()` aggiunto in `scalping_jobs.py`
- [x] Query decisioni applicate 25-35 min fa senza outcome, classifica positive/negative/neutral
- [x] Registrato in `setup_scheduler()` con `interval_minutes=5`

**File:** `synthtrade/backend/app/scheduler/scalping_jobs.py`, `jobs.py`

---

### TASK-864 — Circuit breaker per collector HTTP (2026-06-19)

**Status:** Complete ✅

- [x] Creato `circuit_breaker.py` con `CollectorCircuitBreaker` (closed→open→half_open, 3 failures, 5min reset)
- [x] Integrato in tutti i 6 collector HTTP: `funding_rate`, `open_interest`, `long_short_ratio`, `fear_greed`, `sentiment`, `whale`, `onchain`
- [x] Ogni collector controlla `is_available()` prima di fare HTTP call

**File:** `collectors/circuit_breaker.py` + tutti i collector

---

### TASK-865 — Health check endpoint modulo scalping (2026-06-19)

**Status:** Complete ✅

- [x] Aggiunto `GET /scalping/health` in `router.py`
- [x] Restituisce stato di: ws_client, UDS, supervisor, candle_buffer, signal_engine, session_guard

**File:** `synthtrade/backend/app/scalping/router.py`

---

### TASK-866 — Rate limit budget giornaliero chiamate AI supervisor (2026-06-19)

**Status:** Complete ✅

- [x] Aggiunto `SCALPING_SUPERVISOR_MAX_DAILY_CALLS=100` in `.env` e `config.py`
- [x] `SupervisorScheduler._tick()` controlla e incrementa `_daily_ai_calls`, reset a mezzanotte

**File:** `supervisor_scheduler.py`, `config.py`, `.env`

---

### TASK-867 — PositionManager: aggiungere exit_price e closed_at (2026-06-19)

**Status:** Complete ✅

- [x] Aggiunti campi `exit_price: Optional[Decimal]` e `closed_at: Optional[datetime]` al dataclass `Position`
- [x] `close_position()` popola entrambi i campi al momento della chiusura

**File:** `synthtrade/backend/app/scalping/engine/position_manager.py`

---

### TASK-868 — Test suite per componenti core scalping (2026-06-19)

**Status:** Complete ✅

- [x] Creato `tests/test_scalping_core.py` con 13 test
- [x] Coverage: `SessionLoadGuard` (4 test), `PositionManager` (2 test), `SignalAggregator` (5 test), `CircuitBreaker` (2 test)
- [x] **Tutti i test passano: 13/13 PASSED** (verificato `pytest tests/test_scalping_core.py -v`)
- [x] Fix collaterale: rimossi frammenti di docstring orfani in `long_short_ratio.py`, `sentiment.py`, `onchain.py`, `whale.py` (causa: patch circuit breaker aveva lasciato resti di docstring originale dopo `return None`)

**File:** `synthtrade/backend/tests/test_scalping_core.py`

---


### TASK-822 — Config panel: rimuovere sub-tab "Strategy" e aggiungere titolo "Session" con ID (2026-06-09)

**Status:** Complete ✅

**Problema:** Nel pannello di configurazione principale è presente una sub-scheda "Strategy" che mostra la strategia selezionata inizialmente ma non si aggiorna quando la strategia corrente cambia (es. dopo una decisione del supervisor AI). Esiste già una sezione più completa e aggiornata nel pannello Strategy dedicato.

**Soluzione:**
1. Rimuovere la sub-scheda "Strategy" dal pannello di configurazione principale
2. Aggiungere un titolo principale "Session" al pannello di configurazione
3. Mostrare l'ID della sessione in testo più piccolo sotto il titolo
4. Mantenere visibili le impostazioni di configurazione del trade già esistenti nel sistema

**Modifiche:**
- Rimuovere sub-tab "Strategy" dal componente del pannello configurazione sessione
- Aggiungere header con titolo "Session" + session ID
- Lasciare al loro posto le impostazioni esistenti (symbol, strategy selector, trade value)

**Rischio:** Basso — rimozione UI senza impatto su logica backend.

---

## Epica Scalping Logs — TASK-880 ÷ TASK-883 (2026-06-19)
  ├────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ BUG-02 │ 🔴 CRITICO │ Doppia chiusura posizione in live: _trade_processor esegue SL/TP software (_close_position_and_record) anche in live mode dove │
  │        │            │ Binance chiude già via OCO. Se arriva un tick trade con prezzo sotto SL mentre l'OCO non è ancora eseguito, il router vende a  │
  │        │            │ mercato E poi l'OCO si esegue = doppia vendita su asset già venduto.                                                           │
  ├────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ BUG-03 │ 🟡 MEDIO   │ Broadcast signal type sempre BUY: "type": "BUY" if decision.confidence > 0 else "SELL" — confidence è sempre >0, il frontend   │
  │        │            │ vede solo BUY nel signal panel.                                                                                                │
  ├────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ BUG-04 │ 🟡 MEDIO   │ get_holdings() crash: balance["total"][asset]["free"] — balance["total"] è Dict[str, float], non un dict di oggetti. TypeError │
  │        │            │ se chiamato.                                                                                                                   │
  ├────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ BUG-05 │ 🟡 MEDIO   │ session_perf sempre vuoto in supervisor_memory: getattr(self._loop, "_execution_state", {}) ritorna sempre {} perché           │
  │        │            │ ExecutionLoop non ha _execution_state.                                                                                         │
  ├────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ BUG-06 │ 🟡 MEDIO   │ _save_decision_to_memory() non gestisce i task TASK-844/847: Il caricamento storico decisioni dal DB nel context del           │
  │        │            │ supervisor non è ancora implementato (TASK-847), ma il salvataggio sì — il supervisor opera "senza memoria" nonostante la      │
  │        │            │ tabella esista.                                                                                                                │
  ├────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ BUG-07 │ 🟠 BASSO   │ Race condition in SessionLoadGuard: _check_timeout() dentro complete_phase() può impostare stato failed prima del check        │
  │        │            │ issubset() se il timeout scatta nell'ultimo millisecondo.                                                                      │
  ├────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ BUG-08 │ 🟠 BASSO   │ supervisor_scheduler._score_engine default BTCUSDT: Se SupervisorScheduler viene istanziato senza score_engine, usa            │
  │        │            │ SignalScoreEngine() default che opera su BTCUSDT anche se il simbolo attivo è BNBUSDC. In pratica il supervisor riceve dati    │
  │        │            │ intelligence per il simbolo sbagliato.                                                                                         │
  └────────┴────────────┴────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

  ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

---

## Epica Scalping Logs — TASK-880 ÷ TASK-883 (2026-06-19)
  ├────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ BUG-02 │ 🔴 CRITICO │ Doppia chiusura posizione in live: _trade_processor esegue SL/TP software (_close_position_and_record) anche in live mode dove │
  │        │            │ Binance chiude già via OCO. Se arriva un tick trade con prezzo sotto SL mentre l'OCO non è ancora eseguito, il router vende a  │
  │        │            │ mercato E poi l'OCO si esegue = doppia vendita su asset già venduto.                                                           │
  ├────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ BUG-03 │ 🟡 MEDIO   │ Broadcast signal type sempre BUY: "type": "BUY" if decision.confidence > 0 else "SELL" — confidence è sempre >0, il frontend   │
  │        │            │ vede solo BUY nel signal panel.                                                                                                │
  ├────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ BUG-04 │ 🟡 MEDIO   │ get_holdings() crash: balance["total"][asset]["free"] — balance["total"] è Dict[str, float], non un dict di oggetti. TypeError │
  │        │            │ se chiamato.                                                                                                                   │
  ├────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ BUG-05 │ 🟡 MEDIO   │ session_perf sempre vuoto in supervisor_memory: getattr(self._loop, "_execution_state", {}) ritorna sempre {} perché           │
  │        │            │ ExecutionLoop non ha _execution_state.                                                                                         │
  ├────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ BUG-06 │ 🟡 MEDIO   │ _save_decision_to_memory() non gestisce i task TASK-844/847: Il caricamento storico decisioni dal DB nel context del           │
  │        │            │ supervisor non è ancora implementato (TASK-847), ma il salvataggio sì — il supervisor opera "senza memoria" nonostante la      │
  │        │            │ tabella esista.                                                                                                                │
  ├────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ BUG-07 │ 🟠 BASSO   │ Race condition in SessionLoadGuard: _check_timeout() dentro complete_phase() può impostare stato failed prima del check        │
  │        │            │ issubset() se il timeout scatta nell'ultimo millisecondo.                                                                      │
  ├────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ BUG-08 │ 🟠 BASSO   │ supervisor_scheduler._score_engine default BTCUSDT: Se SupervisorScheduler viene istanziato senza score_engine, usa            │
  │        │            │ SignalScoreEngine() default che opera su BTCUSDT anche se il simbolo attivo è BNBUSDC. In pratica il supervisor riceve dati    │
  │        │            │ intelligence per il simbolo sbagliato.                                                                                         │
  └────────┴────────────┴────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

  ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

---

## Epica Scalping Logs — TASK-880 ÷ TASK-883 (2026-06-19)
  ├────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ BUG-02 │ 🔴 CRITICO │ Doppia chiusura posizione in live: _trade_processor esegue SL/TP software (_close_position_and_record) anche in live mode dove │
  │        │            │ Binance chiude già via OCO. Se arriva un tick trade con prezzo sotto SL mentre l'OCO non è ancora eseguito, il router vende a  │
  │        │            │ mercato E poi l'OCO si esegue = doppia vendita su asset già venduto.                                                           │
  ├────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ BUG-03 │ 🟡 MEDIO   │ Broadcast signal type sempre BUY: "type": "BUY" if decision.confidence > 0 else "SELL" — confidence è sempre >0, il frontend   │
  │        │            │ vede solo BUY nel signal panel.                                                                                                │
  ├────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ BUG-04 │ 🟡 MEDIO   │ get_holdings() crash: balance["total"][asset]["free"] — balance["total"] è Dict[str, float], non un dict di oggetti. TypeError │
  │        │            │ se chiamato.                                                                                                                   │
  ├────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ BUG-05 │ 🟡 MEDIO   │ session_perf sempre vuoto in supervisor_memory: getattr(self._loop, "_execution_state", {}) ritorna sempre {} perché           │
  │        │            │ ExecutionLoop non ha _execution_state.                                                                                         │
  ├────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ BUG-06 │ 🟡 MEDIO   │ _save_decision_to_memory() non gestisce i task TASK-844/847: Il caricamento storico decisioni dal DB nel context del           │
  │        │            │ supervisor non è ancora implementato (TASK-847), ma il salvataggio sì — il supervisor opera "senza memoria" nonostante la      │
  │        │            │ tabella esista.                                                                                                                │
  ├────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ BUG-07 │ 🟠 BASSO   │ Race condition in SessionLoadGuard: _check_timeout() dentro complete_phase() può impostare stato failed prima del check        │
  │        │            │ issubset() se il timeout scatta nell'ultimo millisecondo.                                                                      │
  ├────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ BUG-08 │ 🟠 BASSO   │ supervisor_scheduler._score_engine default BTCUSDT: Se SupervisorScheduler viene istanziato senza score_engine, usa            │
  │        │            │ SignalScoreEngine() default che opera su BTCUSDT anche se il simbolo attivo è BNBUSDC. In pratica il supervisor riceve dati    │
  │        │            │ intelligence per il simbolo sbagliato.                                                                                         │
  └────────┴────────────┴────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

  ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

---

## Epica Scalping Logs — TASK-880 ÷ TASK-883 (2026-06-19)
  ├────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ BUG-02 │ 🔴 CRITICO │ Doppia chiusura posizione in live: _trade_processor esegue SL/TP software (_close_position_and_record) anche in live mode dove │
  │        │            │ Binance chiude già via OCO. Se arriva un tick trade con prezzo sotto SL mentre l'OCO non è ancora eseguito, il router vende a  │
  │        │            │ mercato E poi l'OCO si esegue = doppia vendita su asset già venduto.                                                           │
  ├────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ BUG-03 │ 🟡 MEDIO   │ Broadcast signal type sempre BUY: "type": "BUY" if decision.confidence > 0 else "SELL" — confidence è sempre >0, il frontend   │
  │        │            │ vede solo BUY nel signal panel.                                                                                                │
  ├────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ BUG-04 │ 🟡 MEDIO   │ get_holdings() crash: balance["total"][asset]["free"] — balance["total"] è Dict[str, float], non un dict di oggetti. TypeError │
  │        │            │ se chiamato.                                                                                                                   │
  ├────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ BUG-05 │ 🟡 MEDIO   │ session_perf sempre vuoto in supervisor_memory: getattr(self._loop, "_execution_state", {}) ritorna sempre {} perché           │
  │        │            │ ExecutionLoop non ha _execution_state.                                                                                         │
  ├────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ BUG-06 │ 🟡 MEDIO   │ _save_decision_to_memory() non gestisce i task TASK-844/847: Il caricamento storico decisioni dal DB nel context del           │
  │        │            │ supervisor non è ancora implementato (TASK-847), ma il salvataggio sì — il supervisor opera "senza memoria" nonostante la      │
  │        │            │ tabella esista.                                                                                                                │
  ├────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ BUG-07 │ 🟠 BASSO   │ Race condition in SessionLoadGuard: _check_timeout() dentro complete_phase() può impostare stato failed prima del check        │
  │        │            │ issubset() se il timeout scatta nell'ultimo millisecondo.                                                                      │
  ├────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ BUG-08 │ 🟠 BASSO   │ supervisor_scheduler._score_engine default BTCUSDT: Se SupervisorScheduler viene istanziato senza score_engine, usa            │
  │        │            │ SignalScoreEngine() default che opera su BTCUSDT anche se il simbolo attivo è BNBUSDC. In pratica il supervisor riceve dati    │
  │        │            │ intelligence per il simbolo sbagliato.                                                                                         │
  └────────┴────────────┴────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

  ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

---

## Epica Scalping Logs — TASK-880 ÷ TASK-883 (2026-06-19)

**Descrizione:** Implementare la sezione log dello scalping nella pagina `/logs` del frontend. Mostrare la lista delle sessioni storiche in formato accordion: ogni sessione è espandibile e mostra i trade di quella sessione. Calcolare durata sessione e durata trade direttamente lato frontend.

---

### TASK-880 — Backend: Nuovo endpoint `GET /scalping/sessions` (lista sessioni storiche)

**Status:** Complete ✅
**Completato:** 2026-06-19
**Priorità:** Alta — prerequisito per la UI delle sessioni
**Stima:** 30 min
**File coinvolti:** `synthtrade/backend/app/scalping/router.py`

**Scope:**
- [ ] Aggiungere nuovo endpoint:
  ```python
  @router.get("/sessions")
  async def list_scalping_sessions(limit: int = 50, offset: int = 0) -> List[Dict]:
  ```
- [ ] Query `scalping_sessions` in Supabase ordinata per `started_at DESC`
- [ ] Campi nel response JSON:
  ```json
  {
    "id": "uuid",
    "symbol": "BNBUSDC",
    "mode": "LIVE",
    "status": "stopped",
    "started_at": "2026-06-19T09:30:00Z",
    "stopped_at": "2026-06-19T12:15:00Z",
    "duration_seconds": 9900,
    "total_pnl": 3.45,
    "trade_count": 12,
    "win_count": 8,
    "strategy": "momentum_base",
    "trade_value": 100.0
  }
  ```
- [ ] `duration_seconds` = differenza tra `stopped_at` e `started_at` se status è `stopped`, altrimenti `null`
- [ ] Supporto paginazione via `limit` e `offset`
- [ ] Se non ci sono sessioni, ritornare lista vuota `[]` (non errore)
- [ ] Verifica: chiamare `GET /scalping/sessions` e leggere output

---

### TASK-881 — Backend: Aggiungere filtro `session_id` + campi `entry_time`/`exit_time` a `GET /scalping/trade-history`

**Status:** Complete ✅
**Completato:** 2026-06-19
**Priorità:** Alta — prerequisito per mostrare i trade di una singola sessione
**Stima:** 15 min
**File coinvolti:** `synthtrade/backend/app/scalping/router.py`

**Scope:**
- [ ] Modificare firma endpoint:
  ```python
  @router.get("/trade-history")
  async def get_trade_history(session_id: Optional[str] = None, limit: int = 50) -> List[Dict]:
  ```
- [ ] Se `session_id` è fornito:
  - Query `scalping_trades` filtrata per `session_id`
  - Ordinata per `entry_time DESC`
  - Response con campi: `symbol`, `side`, `entry_price`, `exit_price`, `quantity`, `pnl`, `pnl_pct`, `entry_time`, `exit_time`, `signal_reason`, `status`
- [ ] Se `session_id` non è fornito:
  - Comportamento attuale: ritorna `trade_history` dalla memoria `_execution_state`
  - **Inoltre**: aggiungere `entry_time` e `exit_time` ai trade in memoria:
    - `entry_time` = `timestamp` del trade (già presente)
    - `exit_time` = `timestamp` del trade (stesso valore, perché in memoria il trade è già chiuso)
- [ ] Retrocompatibilità garantita: chi chiama senza `session_id` continua a funzionare
- [ ] Verifica: chiamare `GET /scalping/trade-history?session_id=<uuid>` e ottenere lista trade filtrata

---

### TASK-882 — Frontend: Modelli + Servizio per le sessioni scalping nella pagina logs

**Status:** Complete ✅
**Completato:** 2026-06-19
**Priorità:** Alta — strato dati per la UI
**Stima:** 15 min
**File coinvolti:**
  - Nuovo `synthtrade/frontend/synthtrade-ui/src/app/pages/logs/logs.model.ts`
  - Nuovo `synthtrade/frontend/synthtrade-ui/src/app/pages/logs/logs.service.ts`

**Scope:**

**File: `logs.model.ts`**
- [ ] Interfaccia `ScalpingSessionLog`:
  ```typescript
  export interface ScalpingSessionLog {
    id: string;
    symbol: string;
    mode: 'PAPER' | 'LIVE';
    status: 'running' | 'paused' | 'stopped';
    started_at: string;
    stopped_at?: string;
    duration_seconds?: number;
    total_pnl: number;
    trade_count: number;
    win_count: number;
    strategy?: string;
    trade_value?: number;
  }
  ```
- [ ] Interfaccia `SessionTradeLog`:
  ```typescript
  export interface SessionTradeLog {
    symbol: string;
    side: 'BUY' | 'SELL';
    entry_price: number;
    exit_price?: number;
    quantity: number;
    pnl?: number;
    pnl_pct?: number;
    entry_time: string;
    exit_time?: string;
    signal_reason?: string;
    status?: string;
  }
  ```

**File: `logs.service.ts`**
- [ ] Servizio injectable `ScalpingSessionLogsService`:
  ```typescript
  @Injectable({ providedIn: 'root' })
  export class ScalpingSessionLogsService {
    private http = inject(HttpClient);
    private base = '/api/scalping';

    getSessions(limit = 50, offset = 0): Observable<ScalpingSessionLog[]>
    getSessionTrades(sessionId: string): Observable<SessionTradeLog[]>
  }
  ```
- [ ] `getSessions()`: GET `${this.base}/sessions?limit=${limit}&offset=${offset}`
- [ ] `getSessionTrades()`: GET `${this.base}/trade-history?session_id=${sessionId}`
- [ ] Gestione errori base (log warning, return array vuoto)

---

### TASK-883 — Frontend: Tab "Scalping" con accordion sessioni e trade annidati

**Status:** Complete ✅
**Completato:** 2026-06-19

**Fix post-screenshot (2026-06-19):**
- [x] Aggiunta header row con label colonne (Simbolo, Modo, Inizio, Fine, Durata, Trade, Wins, P&L €, Win%)
- [x] Layout a grid CSS con colonne a larghezza fissa (non più flex → tutto a sinistra)
- [x] Paginazione sessioni: 10 sessioni per pagina con Prev/Next
- [x] Backend fix: al stop sessione ora salva `trade_count`, `win_count`, `total_pnl` su `scalping_sessions`
**Priorità:** Alta — UI finale
**Stima:** 2h
**File coinvolti:** `synthtrade/frontend/synthtrade-ui/src/app/pages/logs/logs.page.ts`

**Scope — Template:**

**1. Aggiungere terzo tab:**
```html
<button class="tab-btn" [class.active]="activeTab() === 'scalping'" (click)="switchTab('scalping')">🧵 Scalping</button>
```
- Aggiornare il tipo `activeTab` a `'logs' | 'trades' | 'scalping'`

**2. Nuova sezione `@if (activeTab() === 'scalping')`:**
- Se `sessions().length === 0` → mostra `<div class="empty-state">Nessuna sessione di scalping trovata.</div>`
- Altrimenti → container accordion

**3. Riga header accordion** per ogni sessione (cliccabile → `toggleSession(s.id)`):
```html
<div class="session-row" [class.expanded]="expandedSessionId() === s.id" (click)="toggleSession(s.id)">
  <!-- Pallino stato -->
  <span class="status-dot" [class.running]="s.status === 'running'" [class.stopped]="s.status === 'stopped'"></span>
  
  <!-- Symbol + Mode badge -->
  <span class="session-symbol">{{ s.symbol }}</span>
  <span class="mode-badge" [class.live]="s.mode === 'LIVE'" [class.paper]="s.mode === 'PAPER'">{{ s.mode }}</span>
  
  <!-- Data inizio -->
  <span class="session-start">{{ s.started_at | date:'dd/MM/yy HH:mm' }}</span>
  
  <!-- Data fine / "In corso" -->
  @if (s.status === 'running') {
    <span class="session-end">In corso</span>
  } @else {
    <span class="session-end">{{ s.stopped_at | date:'dd/MM/yy HH:mm' }}</span>
  }
  
  <!-- Durata sessione (calcolata in frontend) -->
  <span class="session-duration">{{ calcDuration(s.started_at, s.stopped_at) }}</span>
  
  <!-- Trade count -->
  <span class="session-trades">📊 {{ s.trade_count }}</span>
  
  <!-- Win count / total -->
  @if (s.trade_count > 0) {
    <span class="session-wins">✅ {{ s.win_count }}/{{ s.trade_count }}</span>
  }
  
  <!-- P&L total (colorato) -->
  <span class="session-pnl" [ngClass]="{ positive: s.total_pnl >= 0, negative: s.total_pnl < 0 }">
    {{ s.total_pnl >= 0 ? '+' : '' }}{{ s.total_pnl | number:'1.2-2' }} €
  </span>
  
  <!-- Win rate -->
  @if (s.trade_count > 0) {
    <span class="session-winrate" [ngClass]="{ positive: winRate(s) >= 50, negative: winRate(s) < 50 }">
      {{ winRate(s) | number:'1.1-1' }}%
    </span>
  }
  
  <!-- Freccia espansione -->
  <span class="expand-arrow">{{ expandedSessionId() === s.id ? '🔼' : '🔽' }}</span>
</div>
```

**4. Body accordion** (dopo header, visibile solo se espanso):
```html
@if (expandedSessionId() === s.id) {
  <div class="session-detail">
    @if (sessionTrades().length === 0) {
      <div class="empty-state">Nessun trade in questa sessione.</div>
    } @else {
      <div class="trades-table-wrapper">
        <table class="trades-table">
          <thead>
            <tr>
              <th>Ora</th>
              <th>Pair</th>
              <th>Tipo</th>
              <th>Entry</th>
              <th>Exit</th>
              <th>Q.tà</th>
              <th>Durata</th>
              <th>P&L €</th>
              <th>P&L %</th>
              <th>Motivo</th>
            </tr>
          </thead>
          <tbody>
            @for (t of sessionTrades(); track trackByTrade(i, t)) {
              <tr>
                <td class="cell-date">{{ t.entry_time | date:'HH:mm' }}</td>
                <td class="cell-pair">{{ t.symbol }}</td>
                <td class="cell-side" [ngClass]="{ buy: t.side === 'BUY', sell: t.side === 'SELL' }">{{ t.side }}</td>
                <td class="cell-price">{{ t.entry_price | number:'1.2-6' }}</td>
                <td class="cell-exit">{{ t.exit_price != null ? (t.exit_price | number:'1.2-6') : '—' }}</td>
                <td class="cell-qty">{{ t.quantity | number:'1.4-8' }}</td>
                <td class="cell-duration">{{ tradeDuration(t.entry_time, t.exit_time) }}</td>
                <td class="cell-pnl-eur" [ngClass]="{ positive: (t.pnl ?? 0) >= 0, negative: (t.pnl ?? 0) < 0 }">
                  {{ t.pnl != null ? ((t.pnl >= 0 ? '+' : '') + (t.pnl | number:'1.2-2') + ' €') : '—' }}
                </td>
                <td class="cell-pnl" [ngClass]="{ positive: (t.pnl_pct ?? 0) >= 0, negative: (t.pnl_pct ?? 0) < 0 }">
                  {{ t.pnl_pct != null ? ((t.pnl_pct >= 0 ? '+' : '') + (t.pnl_pct | number:'1.2-2') + '%') : '—' }}
                </td>
                <td class="cell-reason">{{ t.signal_reason ?? '—' }}</td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    }
  </div>
}
```

**5. Helper functions (metodi del component):**

- **`calcDuration(startIso: string, endIso?: string): string`**
  - Calcola `endIso ? new Date(endIso) - new Date(startIso) : Date.now() - new Date(startIso)`
  - Formatta output:
    - `>= 86400s` → `Xg Yh`
    - `>= 3600s` → `Xh Ym`
    - `>= 60s` → `Xm Ys`
    - `< 60s` → `Xs`
  - Se sessione ancora running, mostra durata progressiva

- **`winRate(s: ScalpingSessionLog): number`**
  - Se `s.trade_count > 0` → `(s.win_count / s.trade_count) * 100`
  - Altrimenti → `0`

- **`tradeDuration(entryIso: string, exitIso?: string): string`**
  - Calcola `exitIso ? new Date(exitIso) - new Date(entryIso) : Date.now() - new Date(entryIso)`
  - Se trade ancora aperto (`exitIso == null`) → mostra "aperto"
  - Formatta:
    - `>= 3600s` → `Xh Ym`
    - `>= 60s` → `Ym Zs`
    - `< 60s` → `Xs`
  - Esempi: "12m", "1h 30m", "3s", "45m 20s"

- **`trackByTrade(index: number, trade: SessionTradeLog): string`**
  - `trade.entry_time + trade.symbol + trade.side` — per track by univoco

**Scope — Class:**

**6. Nuovi signal e stato:**
```typescript
sessions = signal<ScalpingSessionLog[]>([]);
expandedSessionId = signal<string | null>(null);
sessionTrades = signal<SessionTradeLog[]>([]);
private sessionsOffset = signal(0);
private sessionsLoaded = signal(false);
```

**7. Inject servizio:**
```typescript
private scalpingSessionLogsService = inject(ScalpingSessionLogsService);
```

**8. Nuovi metodi:**
- `loadSessions()` — chiama `getSessions(50, 0)`, setta `sessions` e `sessionsLoaded`
- `toggleSession(sessionId)` — se già espansa → collassa; altrimenti → espande e carica trade
- `loadSessionTrades(sessionId)` — chiama `getSessionTrades(sessionId)`, setta `sessionTrades`

**9. Modifica `switchTab()`:**
```typescript
switchTab(tab: 'logs' | 'trades' | 'scalping'): void {
  this.activeTab.set(tab);
  if (tab === 'scalping') {
    if (!this.sessionsLoaded()) this.loadSessions();
    this.expandedSessionId.set(null);
    this.sessionTrades.set([]);
  } else if (tab === 'trades') { ... }
  else { ... }
}
```

**Scope — Styles:**

**10. Stili aggiuntivi:**
```scss
/* Accordion session row */
.session-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 6px;
  margin-bottom: 4px;
  cursor: pointer;
  font-size: 13px;
  transition: background 0.15s;
  &:hover { background: rgba(255,255,255,0.03); }
  &.expanded {
    border-color: var(--accent-primary);
    border-bottom-left-radius: 0;
    border-bottom-right-radius: 0;
    margin-bottom: 0;
  }
}

/* Stato pallino */
.status-dot {
  width: 10px; height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
  &.running { background: #26a69a; box-shadow: 0 0 6px rgba(38,166,154,0.5); }
  &.stopped { background: #555; }
}

/* Symbol */
.session-symbol {
  font-family: monospace;
  font-weight: 700;
  color: var(--text-primary);
  min-width: 80px;
}

/* Badge mode */
.mode-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 3px;
  text-transform: uppercase;
  &.live { background: rgba(239,83,80,0.2); color: #ef5350; }
  &.paper { background: rgba(38,166,154,0.2); color: #26a69a; }
}

/* Date colonne */
.session-start,
.session-end,
.session-duration {
  font-family: monospace;
  font-size: 11px;
  color: var(--text-muted);
  min-width: 80px;
}

/* Durata */
.session-duration { color: var(--text-secondary); min-width: 60px; }

/* Trade count */
.session-trades { color: var(--text-secondary); min-width: 50px; text-align: center; }

/* Win count */
.session-wins { color: var(--text-secondary); font-size: 12px; min-width: 60px; }

/* P&L */
.session-pnl { font-family: monospace; font-weight: 700; min-width: 80px; text-align: right; }

/* Win rate */
.session-winrate { font-family: monospace; font-weight: 600; font-size: 12px; min-width: 50px; text-align: right; }

/* Expand arrow */
.expand-arrow { margin-left: auto; font-size: 12px; }

/* Detail panel (body accordion) */
.session-detail {
  background: var(--bg-elevated);
  border: 1px solid var(--accent-primary);
  border-top: none;
  border-bottom-left-radius: 6px;
  border-bottom-right-radius: 6px;
  padding: 8px;
  margin-bottom: 4px;
}

/* Durata trade nella tabella */
.cell-duration { font-family: monospace; font-size: 11px; color: var(--text-muted); white-space: nowrap; }

/* Reason cell */
.cell-reason { font-size: 11px; color: var(--text-secondary); max-width: 80px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
```

**11. Verifica finale (checklist):**
- [ ] Tre tab funzionanti: Log, Storico Trade, Scalping
- [ ] Click su tab "Scalping" carica lista sessioni
- [ ] Ogni riga mostra: stato, symbol, mode, inizio, fine, durata, trade count, win/total, P&L €, win rate %, freccia
- [ ] Click su riga espande accordion con tabella trade
- [ ] Tabella trade mostra: ora, pair, tipo, entry, exit, q.tà, durata trade, P&L €, P&L %, motivo
- [ ] Click su altra riga cambia espansione (collassa precedente, espande nuova)
- [ ] Durata sessione in formato leggibile (es: "2h 15m")
- [ ] Durata trade in formato leggibile (es: "12m", "45s")
- [ ] Empty state se nessuna sessione
- [ ] Empty state nella tabella se sessione senza trade
- [ ] P&L colorato verde/rosso
- [ ] Win rate colorato verde (≥50%) / rosso (<50%)
- [ ] Performance decente con molte sessioni (OnPush change detection)