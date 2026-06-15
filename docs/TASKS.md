# TASKS.md — SynthTrade Task Tracking

## Active Tasks

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
