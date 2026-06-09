# Analisi: Perdita di Logging nel Backend Scalping

## Problema Riscontrato
Una sessione di scalping attiva mostra sul frontend stato "running" con dati corretti (session_id, balance, symbol BNBUSDC, trade_value=10), ma **il backend non registra log dopo l'avvio iniziale**. I job Intel snapshot vengono eseguiti normalmente, ma non vi è alcuna altra attività nel log.

## Causa Radice Identificata

### Session Restore NON avvia il pipeline WS
**File:** `synthtrade/backend/app/main.py:96-142`

Il codice di restore sessione carica correttamente lo stato nella variabile `_execution_state`, ma **NON chiama mai `_start_ws_broadcast()`** per avviare:
- Il BinanceWSClient
- Il candle processor (`_candle_processor`)
- Il trade processor (`_trade_processor`)  
- L'intelligence processor (`_intelligence_processor`)

### Conseguenze
1. **Session status = "running"** ma **nessun flusso dati WS attivo**
2. **Buffer candele vuoto** - i candle vengono solo broadcastati inizialmente ma non processati
3. **ExecutionLoop non viene alimentato** - nessun `process_candle()` chiamato
4. **Nessun segnale generato** - le strategie non vengono eseguite
5. **Log Intel snapshot funzionano** perché sono indipendenti e leggono direttamente dal `_execution_state`

## Modifiche dei Commit Analizzati

### Commit 2640ea6 - Race condition fix
- Aggiunge `_session_mode = ...paper"` control nello `_start_ws_broadcast` (linea 402)
- Il mock candle generator è **disabilitato in live mode** (linea 1160-1166)
- Session status impostato a "idle" immediatamente sul stop (linea 1629)

### Commit fa59768 - Trade value default
- Cambia default `trade_value` da 100.0 a 10.0 (linea 572, 762)
- **Non influisce sul logging**

### Commit 03414e1 - StochRSI strategy
- Aggiunge `nonlocal client` nel `_candle_processor` (linea 618)
- **Non influisce sul logging**

## Possibili Cause del Problema

### 1. Session Restore incompleto (CAUSA PRINCIPALE)
**Dove verificare:** `main.py:96-142`

Il restore carica lo stato ma non ricostruisce il pipeline:
```python
# Questo viene fatto
_execution_state["session"]["status"] = "running"
_execution_state["session"]["symbol"] = sess.get("symbol")

# Questo MANCA - necessario per riprendere il trading
# await _start_ws_broadcast(active_symbol)  # NON CHIAMATO!
```

### 2. Livelli di logging potrebbero essere a DEBUG
**Dove verificare:** `app/core/logging.py:37`

- Root logger impostato a INFO
- Molti messaggi importanti sono a `logger.debug()` (es. linea 718, 554)
- In produzione potrebbero non essere visibili

### 3. Buffer ID mismatch (BUG ESISTENTE)
**Dove verificare:** `execution_loop.py:138-143`

Il warmup carica le candele in `candle_buffer`, ma se le istanze sono diverse:
- Buffer warmup: `id(candle_buffer)`
- Buffer execution_loop: `id(execution_loop._candle_buffer)`

### 4. Regime detection potrebbe fallire
**Dove verificare:** `regime_detector.py:29`

Se `len(candles) < 20`, ritorna "unknown" regime, che mappa a `momentum_base`.

### 5. Strategy bias conflict
**Dove verificare:** `signal_aggregator.py:147-153`

Se il bias intelligence è "neutral", il segnale viene bloccato con log a WARNING.

## Raccomandazioni di Verifica

### 1. Verificare Session Restore (PRIORITÀ ALTA)
Aggiungere nel `main.py` dopo il restore:
```python
if active_sessions.data:
    # ... existing restore code ...
    
    # Avvia il pipeline WS
    import asyncio
    asyncio.create_task(_start_ws_broadcast(
        _execution_state["session"]["symbol"].lower()
    ))
```

### 2. Aggiungere log di diagnostic
Nel `_candle_processor` dopo `await asyncio.wait_for`:
```python
except asyncio.TimeoutError:
    logger.debug(f"Candle processor timeout, session status: {_execution_state['session']['status']}")
```

### 3. Verificare che il BinanceWSClient sia connesso
Controllare i log per:
- `"BinanceWSClient connected"` (dovrebbe apparire all'avvio sessione)
- `"Scalping broadcast started for..."`

### 4. Verificare i task WS
Controllare che `_execution_state["ws_tasks"]` sia popolato dopo il restore.

### 5. Verificare il trading mode
Se la sessione è "live", il mock candle generator è disabilitato. Il WS Binance deve fornire i dati.