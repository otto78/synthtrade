# Bug Fix Summary — Modulo Scalping

## Problemi Critici Identificati

### 1. Trade Non Partono (Signal Aggregator)
**File:** `synthtrade/backend/app/scalping/engine/signal_aggregator.py`

**Problema:** Bias intelligence quasi sempre "neutral" blocca tutti i trade anche quando il segnale tecnico è valido.

**Soluzione Applicata:**
- ✅ Aggiunto parametro `paper_mode` al metodo `should_execute()`
- ✅ In paper mode, se `|score| < 5.0`, usa solo segnale tecnico con confidence check
- ✅ Log PAPER MODE per debug

**File:** `synthtrade/backend/app/scalping/engine/execution_loop.py`

**Soluzione Applicata:**
- ✅ Aggiunto attributo `self.paper_mode: bool = True`
- ✅ Aggiunto attributo `self.session_id: Optional[str] = None`
- ✅ Passa `paper_mode` al signal aggregator in `process_candle()`

### 2. Bug Strutturale `_trade_processor` in `router.py`
**File:** `synthtrade/backend/app/scalping/router.py` (riga ~370)

**Problema:** La closure `_trade_processor` ha solo la docstring `"""Consume trade_queue and broadcast + update PnL."""` ma manca `async def _trade_processor():` quindi il codice è flottante fuori dalla funzione.

**Soluzione da Applicare:**
```python
    async def _trade_processor():
        """Consume trade_queue and broadcast + update PnL."""
        while _execution_state["session"]["status"] != "idle" and not client._stop_event.is_set():
            # ... resto del codice esistente
```

### 3. Paper Mode Non Impostato su ExecutionLoop
**File:** `synthtrade/backend/app/scalping/router.py` (funzione `_start_ws_broadcast`)

**Soluzione da Applicare:**
Dopo creazione `execution_loop`, aggiungere:
```python
    # Set paper_mode on execution loop so signal aggregator can use fallback
    is_paper = _execution_state["session"]["mode"] == "paper"
    execution_loop.paper_mode = is_paper
    if is_paper:
        logger.info(f"{CYAN}PAPER MODE: Signal aggregator will use technical-only fallback when intelligence fails{RESET}")
```

### 4. `_stop_ws_broadcast` Non Awaita la Cancellazione dei Task
**File:** `synthtrade/backend/app/scalping/router.py`

**Problema:** I task vengono cancellati con `.cancel()` ma non viene fatto await, possono rimanere in esecuzione zombie.

**Soluzione da Applicare:**
```python
async def _stop_ws_broadcast():
    """Stop BinanceWSClient and clean up pipeline components."""
    client = _execution_state.get("ws_client")
    if client:
        await client.stop()
        _execution_state["ws_client"] = None
    
    loop = _execution_state.get("loop")
    if loop:
        await loop.stop()
        _execution_state["loop"] = None
    
    _execution_state["signal_engine"] = None

    # Cancel all WS tasks and await their completion
    tasks = _execution_state.get("ws_tasks", [])
    for task in tasks:
        if not task.done():
            task.cancel()
    
    # Await all cancelled tasks to cleanup properly
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    
    _execution_state["ws_tasks"] = []
```

### 5. GET `/session` Non Recupera Sessione da DB al Restart
**File:** `synthtrade/backend/app/scalping/router.py`

**Problema:** Al restart del backend, la sessione in-memory è `idle` anche se c'è una sessione `running` su Supabase.

**Soluzione da Applicare:**
```python
@router.get("/session")
async def get_session() -> Dict:
    """Get current session status — with fallback to DB if backend restarted."""
    session = _execution_state["session"]
    
    # If session is idle but there might be a running session in DB, check
    if session["status"] == "idle":
        try:
            supabase = get_supabase()
            response = supabase.table("scalping_sessions") \
                .select("*") \
                .eq("status", "running") \
                .order("started_at", desc=True) \
                .limit(1) \
                .execute()
            
            if response.data:
                db_session = response.data[0]
                # Restore session from DB (but do NOT restart WS — that's manual)
                session["db_session_id"] = db_session["id"]
                session["symbol"] = db_session["symbol"]
                session["mode"] = db_session["mode"].lower()
                session["status"] = db_session["status"]
                session["started_at"] = db_session["started_at"]
                logger.info(f"Session restored from DB: {db_session['id']} (status={db_session['status']})")
        except Exception as e:
            logger.warning(f"Failed to restore session from DB: {e}")
    
    return session.copy()
```

## Problemi Frontend (Minori ma Importanti)

### 6. SignalScorecard Mostra Dati Hardcoded
**File:** `synthtrade/frontend/synthtrade-ui/src/app/scalping/components/signal-scorecard.component.ts`

**Status:** ✅ GIÀ CORRETTO — il componente si sottoscrive a `ws.intelligence$`

### 7. StrategyPanel Non Reattivo a WS Supervisor
**File:** `synthtrade/frontend/synthtrade-ui/src/app/scalping/components/strategy-panel.component.ts`

**Status:** ✅ GIÀ CORRETTO — il componente si sottoscrive a `ws.supervisorDecision$`

### 8. Soglia Intelligence Troppo Alta per Paper Mode
**File:** `synthtrade/backend/app/config.py`

**Problema:** `SCALPING_SIGNAL_STRENGTH_THRESHOLD: float = 30.0` è troppo alta quando i collector esterni falliscono.

**Soluzione:** Già gestito con paper_mode fallback nel signal aggregator.

## Prossimi Passi

1. ✅ **COMPLETATO:** Fix signal_aggregator.py con paper_mode
2. ✅ **COMPLETATO:** Fix execution_loop.py con paper_mode attribute
3. ⚠️ **DA FARE:** Fix `_trade_processor` in router.py (riga ~370)
4. ⚠️ **DA FARE:** Impostare `execution_loop.paper_mode` in `_start_ws_broadcast`
5. ⚠️ **DA FARE:** Fix `_stop_ws_broadcast` con await dei task
6. ⚠️ **DA FARE:** Fix `GET /session` con fallback da DB
7. **OPZIONALE:** Implementare `session_manager.py` per persistenza completa

## Test da Fare

```bash
# 1. Avvia backend
cd synthtrade/backend
uvicorn app.main:app --reload --port 8008

# 2. Avvia frontend
cd synthtrade/frontend/synthtrade-ui
npm start

# 3. Testa flusso completo
# - Vai su http://localhost:4208/scalping
# - Start session con simbolo BTCUSDT
# - Verifica che il buffer si riempia (100 candele storiche)
# - Verifica che i segnali tecnici vengano generati anche con intelligence bassa
# - Verifica che i trade vengano aperti e chiusi

# 4. Controlla log backend
# Deve mostrare:
# - "PAPER MODE: Signal aggregator will use technical-only fallback..."
# - "📋 PAPER MODE: BUY BTCUSDT @ 0.75 (intelligence bypassed: score=2.3)"
# - "Paper trade opened: BUY BTCUSDT @ 95432.50"
```

## Note Finali

Le modifiche principali sono state applicate. Rimangono da sistemare i bug strutturali in `router.py` che impediscono l'avvio corretto del modulo WS.

**Priorità:**
1. Fix `_trade_processor` — **CRITICO** (sintassi rotta)
2. Impostare `paper_mode` su loop — **ALTA** (trade bloccati)
3. Fix `_stop_ws_broadcast` — MEDIA (memory leak)
4. Fix `GET /session` con DB — BASSA (UX al restart)
