# Flusso OCO + User Data Stream (UDS) — Specifica Definitiva

> Data: 2026-06-15
> Versione: 2.1 (session load guard + review finale)
> Stato: Implementato

---

## Principi Fondamentali

1. **Solo OCO nativo Binance** — nessun synthetic fallback, nessuno stop loss/limit separati
2. **UDS socket solo quando c'è un ordine attivo** — si apre dopo OCO riuscito, resta aperto per tutta la sessione
3. **Se OCO fallisce → market sell immediato** — nessun asset bloccato senza protezione
4. **Salvataggio DB solo a operazione riuscita** — posizione salvata solo dopo OCO confermato

---

## 0. Pulizia Preliminare

Prima di implementare il nuovo flusso, va rimosso tutto il codice che non serve più:

- [ ] **Rimuovere** `_place_oco_synthetic_inverted()` da `exchange.py` (metodo morto)
- [ ] **Rimuovere** `_place_oco_synthetic()` da `exchange.py` (niente fallback)
- [ ] **Rimuovere** OCO sync su polling candela in `router.py` (righe ~1223-1294)
- [ ] **Rimuovere** `place_stop_loss_order()`, `place_limit_order()` se non usati altrove
- [ ] **Definire** `_on_order_update` in `router.py` (mancante, attualmente NameError)
- [ ] **Rimuovere** ogni altro metodo che piazza ordini di uscita non-OCO

---

## 1. Avvio Sessione

```
POST /scalping/session {action: "start", mode: "live", symbol, trade_value}
```

### Sequenza

1. **Crea sessione su Supabase** `scalping_sessions`:
   - `symbol`, `mode="LIVE"`, `timeframe="1m"`, `status="running"`
   - `trade_value`, `started_at`, `strategy="scalping_v2"`
   - Ottieni `db_session_id` dal DB

2. **Inizializza `BinanceExchangeAdapter`** (solo se mode=live)

3. **Avvia candle stream WebSocket** (BinanceWSClient + ExecutionLoop) per ricevere segnali di trading

4. **UDS socket: NON ANCORA ATTIVO** — partirà solo al primo OCO riuscito
   - **Regola**: l'UDS è un **singleton per sessione**. Prima di ogni `uds.start()`, controllare:
     ```python
     if not _execution_state.get("user_data_stream"):
         uds = UserDataStreamManager(...)
         await uds.start(on_order_update=_on_order_update)
         _execution_state["user_data_stream"] = uds
     ```

---

## 2. Segnale BUY → Market Buy + OCO

```
ExecutionLoop genera segnale BUY → _candle_processor() esegue
```

### Sequenza

```
┌──────────────────────────────────────────────────────────┐
│ 1. Calcola quantity da trade_value / prezzo corrente      │
│ 2. exchange.place_market_order(symbol, "BUY", quantity)   │
│    ├── Se fallisce → stop, errore UI                      │
│    └── Se OK → continua                                   │
│                                                           │
│ 3. exchange.place_oco_order(symbol, "SELL", qty, tp, sl)  │
│    ├── CASO A: RIUSCITO → salva DB + avvia UDS + UI       │
│    └── CASO B: FALLITO → cancella orfani + market sell    │
└──────────────────────────────────────────────────────────┘
```

### Caso A — OCO RIUSCITO ✅

4. **Salva posizione a DB** (`scalping_positions`):
   - `session_id`, `symbol`, `side="BUY"`, `entry_price`
   - `quantity`, `oco_order_list_id`, `sl_order_id`, `tp_order_id`
   - `tp_price`, `sl_price` (⚠️ aggiunti dopo review)
   - `status="open"`, `opened_at`

5. **Avvia UDS socket** se non già attivo (check singleton):
   ```python
   if not _execution_state.get("user_data_stream"):
       uds = UserDataStreamManager(api_key, api_secret, testnet=False)
       await uds.start(on_order_update=_on_order_update)
       _execution_state["user_data_stream"] = uds
   ```

6. **Broadcast a UI**: evento `position` con tutti i dati (entry price, TP, SL, qty)

7. Log: `🎯 OCO ATTIVO: BUY {symbol} @ {price} | TP={tp} | SL={sl}`

### Caso B — OCO FALLITO ❌

4. **Cancella ordini orfani**:
   ```python
   open_orders = await exchange.get_open_orders(symbol)
   for order in open_orders:
       await exchange.client.cancel_order(order["id"], symbol)
   ```

5. **⚠️ Market Sell con quantity reale post-fee** (non quella pre-buy):
   ```python
   actual_qty = await exchange._get_available_base_balance(symbol)
   if actual_qty > 0:
       await exchange.place_market_order(symbol, "SELL", actual_qty)
   else:
       logger.error(f"❌ OCO fallito e nessun balance da vendere per {symbol}")
   ```
   **Motivo**: dopo il market buy, Binance deduce la fee in base asset (~0.1%).
   Usare la quantity calcolata inizialmente potrebbe causare un errore LOT_SIZE o "insufficient balance".
   `_get_available_base_balance()` legge il balance reale post-fee dall'exchange.

6. **Nessun salvataggio a DB** — non c'è posizione da registrare

7. **Broadcast a UI**: evento `error`:
   ```json
   {
     "code": "OCO_FAILED",
     "message": "OCO fallito: {motivo}. Trade chiuso, nessun asset bloccato."
   }
   ```

---

## 3. User Data Stream — Ascolto

Il socket UDS, una volta attivo, **resta aperto per tutta la durata della sessione**.

### Handler `_on_order_update(event)`

```python
async def _on_order_update(event: dict):
    """Chiamato da UDS su ogni executionReport FILLED/EXPIRED."""
    symbol = event["symbol"]
    order_id = event["order_id"]
    order_list_id = event["order_list_id"]
    status = event["status"]  # "filled" / "expired"
    fill_price = event["fill_price"]
    
    pos = _execution_state["position_manager"].get_open()
    # ⚠️ Se la posizione è già stata chiusa (es. EXPIRED arrivato dopo FILLED),
    # `pos` è None e usciamo silenziosamente — nessun errore.
    if not pos or pos.oco_order_list_id != order_list_id:
        return  # Non è la nostra posizione o già chiusa
    
    if status == "filled":
        # Determina se è TP o SL
        if order_id == pos.tp_order_id:
            reason = "take_profit"
        elif order_id == pos.sl_order_id:
            reason = "stop_loss"
        else:
            reason = "oco_filled"
        
        # Calcola PnL
        pnl = (fill_price - float(pos.entry_price)) * float(pos.quantity)
        
        # Aggiorna DB
        _update_closed_position_in_db(pos, fill_price, pnl, reason)
        
        # Chiudi posizione in memoria
        _execution_state["position_manager"].close_position(Decimal(fill_price))
        
        # Broadcast UI
        broadcast_scalping_event("trade_closed", {
            "symbol": pos.symbol, "side": pos.side,
            "entry_price": float(pos.entry_price), "exit_price": fill_price,
            "quantity": float(pos.quantity), "pnl": round(pnl, 2),
            "pnl_pct": round(pnl / (float(pos.entry_price) * float(pos.quantity)) * 100, 2),
            "reason": reason, "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        logger.info(f"✅ Trade chiuso da {reason}: {pos.symbol} @ {fill_price} PnL={pnl:.2f}")
    
    elif status == "expired":
        # ⚠️ Binance NON garantisce l'ordine degli eventi.
        # Se arriva EXPIRED prima di FILLED:
        # - Ignoriamo EXPIRED
        # - Se la posizione è ancora aperta, potrebbe essere che l'altro leg
        #   non è ancora stato eseguito. Facciamo una verifica REST.
        # - Se la posizione è già chiusa (None), usciamo silenziosamente.
        logger.info(f"ℹ️ OCO leg EXPIRED (attesa FILLED dell'altro leg): {symbol} orderId={order_id}")
```

**⚠️ Nota sull'ordine degli eventi Binance**: Non è garantito che FILLED arrivi prima di EXPIRED (o viceversa).
- Se arriva prima EXPIRED → la posizione è ancora aperta → il log è informativo, l'altro evento (FILLED) arriverà dopo
- Se arriva dopo EXPIRED → la posizione è già chiusa e `get_open()` restituisce None → usciamo silenziosamente

---

## 4. Stop Sessione

```
POST /scalping/session {action: "stop"}
```

### Sequenza

1. **Se posizione aperta** (trade in corso con OCO attivo):
   - **Cancella OCO**: `exchange.cancel_open_orders(symbol)` — rimuove TP/SL
   
   - **⚠️ Attendi conferma cancellazione** prima del market sell:
     ```python
     # Aspetta che Binance confermi la cancellazione
     await asyncio.sleep(0.5)
     
     # Verifica che gli ordini aperti siano effettivamente zero
     retry = 0
     while retry < 3:
         remaining = await exchange.get_open_orders(symbol)
         if not remaining:
             break
         await asyncio.sleep(0.3)
         retry += 1
     ```
     **Motivo**: se cancelli e vendi immediatamente, Binance potrebbe eseguire l'OCO
     nel mezzo (race condition). Il delay + verifica evitano che TP/SL vengano
     eseguiti durante la market sell.
   
   - **Market Sell**: `exchange.place_market_order(symbol, "SELL", pos.quantity)`
   - **Aggiorna DB**: posizione chiusa con `exit_reason="session_stop"`
   - **Broadcast UI**: `trade_closed`

2. **Stop UDS**: `_execution_state["user_data_stream"].stop()` → cancella listenKey

3. **Stop WebSocket stream** (candle + trade + intelligence)

4. **Aggiorna sessione DB**: `scalping_sessions.status = "stopped"`, `stopped_at = now`

### Crash PC / Perdita Connessione

L'OCO su Binance **resta attivo** con TP e SL. Il trade è completamente protetto. Nessuna azione necessaria.

```
┌──────────────────────────────────────┐
│ PC crash / perdita connessione       │
│                                      │
│ Binance ha OCO attivo → TP o SL     │
│ esegue automaticamente               │
│                                      │
│ Al riavvio → restore session         │
│ → scopre posizione chiusa via UDS/API│
└──────────────────────────────────────┘
```

---

## 5. Riavvio App — Restore Sessione

```
GET /scalping/session
Viene chiamato automaticamente quando l'utente apre la pagina /scalping
```

### Sequenza

1. **Query Supabase**: `SELECT * FROM scalping_sessions WHERE status = 'running' AND mode = 'LIVE' LIMIT 1`

2. **Se sessione attiva trovata**:
   - Ripristina `_execution_state["session"]` con i dati del DB
   - Cerca posizione aperta: `SELECT * FROM scalping_positions WHERE session_id = X AND status = 'open' LIMIT 1`

3. **Se posizione aperta trovata**:
   - **Verifica su Binance**:
     ```python
     open_orders = await exchange.get_open_orders(pos.symbol)
     ```
   
   - **Se OCO ancora attivo** (open_orders non vuoti):
     - Riavvia UDS socket (check singleton) e riprendi ascolto
     - Broadcast a UI: evento `position` con stato corrente
     - Log: `♻️ Sessione restored: {symbol} OCO ancora attivo`
   
   - **Se OCO già eseguito** (open_orders vuoti):
     - **⚠️ Usa sl_order_id / tp_order_id salvati in DB** per la query specifica:
       ```python
       # Usa GET /api/v3/allOrders filtrando per orderId (NON per symbol generico)
       # Questo evita di ricevere ordini di altre sessioni
       order_id_to_check = pos.sl_order_id or pos.tp_order_id
       if order_id_to_check:
           fill_price = await exchange._fetch_fill_price_by_order_id(
               symbol=pos.symbol,
               order_id=order_id_to_check
           )
       ```
     - Aggiorna DB: chiudi posizione con exit_price reale
     - Broadcast a UI: evento `trade_closed` con dati
     - Log: `♻️ Sessione restored: {symbol} già chiuso da OCO @ {fill_price}`

4. **Se nessuna sessione attiva**: UI mostra stato "idle"

---

## 3b. UDS — Riconnessione e Sync su Disconnessione Temporanea

**⚠️ Aggiunto dopo review — CRITICO per evitare disallineamento.**

Il `UserDataStreamManager` già implementa riconnessione automatica (`_reconnect` in `user_data_stream.py`).
Tuttavia, serve una logica aggiuntiva per gestire il caso in cui l'OCO viene eseguito **durante**
la finestra di disconnessione del socket UDS.

### Logica da aggiungere a `_listen_loop()` in `user_data_stream.py`

```python
async def _listen_loop(self):
    """Loop che mantiene attiva la connessione WebSocket."""
    import websockets
    
    while self._running:
        try:
            # ... connessione WS ...
            async with websockets.connect(self._ws_url) as ws:
                self._ws_connection = ws
                logger.info("📡 UDS SOCKET ATTIVO")
                
                while self._running:
                    try:
                        message = await asyncio.wait_for(ws.recv(), timeout=60)
                        await self._dispatch_message(json.loads(message))
                    except asyncio.TimeoutError:
                        continue
                    except websockets.exceptions.ConnectionClosed:
                        logger.warning("UDS WebSocket disconnesso")
                        break
        
        except Exception as e:
            logger.error(f"UDS error: {e}")
            if self._running:
                logger.info(f"Riconnessione UDS in {self.RECONNECT_DELAY}s...")
                await asyncio.sleep(self.RECONNECT_DELAY)
                await self._reconnect()
                
                # ⚠️ DOPO LA RICONNESSIONE: verifica stato ordini via REST
                # L'OCO potrebbe essere stato eseguito durante la disconnessione
                if self._on_order_update and self._on_reconnect_sync:
                    try:
                        await self._on_reconnect_sync()
                    except Exception as sync_e:
                        logger.warning(f"Reconnect sync failed: {sync_e}")
```

### Nuovo parametro in `UserDataStreamManager.__init__`

```python
def __init__(self, api_key, api_secret, testnet=False):
    # ... esistente ...
    self._on_order_update: Optional[Callable] = None
    self._on_reconnect_sync: Optional[Callable] = None  # ⚠️ NUOVO
```

### In router.py, durante start UDS

```python
uds = UserDataStreamManager(api_key, api_secret, testnet=False)
await uds.start(
    on_order_update=_on_order_update,
    on_reconnect_sync=_on_uds_reconnect_sync,  # ⚠️ NUOVO
)
_execution_state["user_data_stream"] = uds
```

### Handler `_on_uds_reconnect_sync()`

```python
async def _on_uds_reconnect_sync():
    """Chiamato dopo ogni riconnessione UDS per verificare
    se l'OCO è stato eseguito durante la disconnessione."""
    pos = _execution_state["position_manager"].get_open()
    if not pos:
        return  # Nessuna posizione aperta, nulla da sincronizzare
    
    exchange = _execution_state.get("exchange")
    if not exchange:
        return
    
    try:
        open_orders = await exchange.get_open_orders(pos.symbol)
        if not open_orders:
            # OCO eseguito durante la disconnessione!
            logger.info("🔄 UDS riconnesso: OCO già eseguito durante la disconnessione")
            
            # Recupera il fill price via REST
            closed = await exchange.client.fetch_closed_orders(
                await exchange._get_ccxt_symbol(pos.symbol),
                limit=5
            )
            for order in closed:
                if order.get("status") == "closed" and order.get("side") == "SELL":
                    fill_price = float(order.get("price") or 0)
                    if fill_price > 0:
                        # Chiudi posizione direttamente
                        pnl = (fill_price - float(pos.entry_price)) * float(pos.quantity)
                        _update_closed_position_in_db(pos, fill_price, pnl, "take_profit" if pnl > 0 else "stop_loss")
                        _execution_state["position_manager"].close_position(Decimal(fill_price))
                        broadcast_scalping_event("trade_closed", {
                            "symbol": pos.symbol,
                            "entry_price": float(pos.entry_price),
                            "exit_price": fill_price,
                            "pnl": pnl,
                            "reason": "take_profit" if pnl > 0 else "stop_loss",
                        })
                        logger.info(f"✅ Trade chiuso da UDS reconnect sync @ {fill_price}")
                        break
    except Exception as e:
        logger.warning(f"UDS reconnect sync error (non-fatal): {e}")
```

---

## 5. Session Load Guard — Blocco Trade Durante Avvio/Restore

**⚠️ Aggiunto dopo review — CRITICO per evitare OCO duplicati dopo restart.**

Durante restore o avvio sessione, `_start_ws_broadcast()` può entrare in background prima che exchange, posizione aperta e warmup candele siano completamente pronti.
Per evitare che `_candle_processor()` generi un nuovo trade mentre una posizione esistente è ancora in fase di verifica, tutte le operazioni di trading passano attraverso `SessionLoadGuard`.

### Fasi richieste

La sessione diventa tradeable solo dopo:

```text
db_phase → exchange_phase → position_phase → buffer_phase → pipeline_phase → READY
```

- `db_phase`: sessione letta da DB in restore oppure salvata su Supabase dopo start
- `exchange_phase`: adapter live inizializzato e saldo disponibile, oppure fase exchange skipped per paper
- `position_phase`: posizione aperta restaurata/verificata oppure position manager resettato per nuova sessione
- `buffer_phase`: warmup storico candele completato in `_start_ws_broadcast()`
- `pipeline_phase`: `BinanceWSClient.start()` completato

### Comportamento

- Stato iniziale: `loading`
- Timeout: 30s, poi stato `failed`
- Log: warning ogni 5s durante il caricamento
- Gate: `_candle_processor`, `_trade_processor` e trade live inline bloccano qualsiasi trade se `guard.is_ready() == False`
- Monitoraggio: tentativi bloccati salvati in `deque(maxlen=100)`
- Endpoint: `GET /scalping/debug/session-load`
- WebSocket: nuovo client riceve evento `session_loading` con `guard.monitor_data`

### Implementazione

- `synthtrade/backend/app/scalping/session_load_guard.py`: state manager
- `synthtrade/backend/app/main.py`: fasi restore
- `synthtrade/backend/app/scalping/router.py`: fasi start, warmup, pipeline e gate

---

## 6. Schema DB (con correzioni review)

```sql
-- Tabella sessioni
CREATE TABLE scalping_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol TEXT NOT NULL,
    mode TEXT NOT NULL DEFAULT 'PAPER',
    timeframe TEXT NOT NULL DEFAULT '1m',
    status TEXT NOT NULL DEFAULT 'running',
    trade_value FLOAT NOT NULL DEFAULT 10.0,
    strategy TEXT NOT NULL DEFAULT 'scalping_v2',
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    stopped_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Tabella posizioni (⚠️ contiene tp_price e sl_price aggiunti dopo review)
CREATE TABLE scalping_positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES scalping_sessions(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('BUY', 'SELL')),
    entry_price FLOAT NOT NULL,
    quantity FLOAT NOT NULL,
    exit_price FLOAT,
    pnl FLOAT,
    pnl_pct FLOAT,
    exit_reason TEXT CHECK (exit_reason IN ('take_profit', 'stop_loss', 'session_stop', 'oco_failed', 'manual_close')),
    -- Prezzi target OCO (⚠️ aggiunto dopo review — servono a UI per mostrare TP/SL)
    tp_price FLOAT,
    sl_price FLOAT,
    -- ID ordini Binance
    oco_order_list_id TEXT,
    sl_order_id TEXT,
    tp_order_id TEXT,
    -- Stato
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'closed')),
    opened_at TIMESTAMP NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMP
);
```

---

## 7. Solo OCO — Vietato Usare

Durante la normale operatività della sessione:
- ❌ `place_stop_loss_order()` — non usare
- ❌ `place_limit_order()` — non usare
- ❌ `_place_oco_synthetic()` — non usare (da rimuovere)
- ❌ `_place_oco_synthetic_inverted()` — non usare (da rimuovere)
- ❌ `close_position()` con market sell durante trade in corso — non usare
- ❌ Polling OCO su ogni candela — non usare (da rimuovere)
- ❌ Qualsiasi fallback automatico se OCO fallisce

**Unico metodo di uscita**: `place_oco_order()` (nativo Binance)

**Eccezioni consentite**:
- `place_market_order(symbol, "SELL")` → solo in caso di **OCO fallito** o **stop sessione**
- `cancel_open_orders()` → solo in caso di **OCO fallito** o **stop sessione**

---

## Riepilogo Modifiche Rispetto alla V1

| # | Modifica | Sezione | Priorità |
|---|----------|---------|----------|
| 1 | UDS singleton check prima di `uds.start()` | 1, 2 | 🔴 Alta |
| 2 | Market sell emergenza usa `_get_available_base_balance()` | 2 (Caso B) | 🔴 Alta |
| 3 | Gestione ordine EXPIRED + FILLED in `_on_order_update` | 3 | 🟡 Media |
| 4 | Wait conferma cancellazione OCO prima di market sell | 4 | 🟡 Media |
| 5 | `tp_price` e `sl_price` aggiunti a schema DB e save | 2, 6 | 🟡 Media |
| 6 | Restore usa `sl_order_id`/`tp_order_id` specifici per query | 5 | 🟡 Media |
| 7 | UDS reconnect sync: `on_reconnect_sync` parametro | 3b | 🔴 Alta |
| 8 | Session Load Guard blocca trade finché restore/start non è READY | 5 | 🔴 Alta |