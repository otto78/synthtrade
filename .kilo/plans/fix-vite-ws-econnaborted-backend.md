# Fix ECONNABORTED ws proxy — piano implementazione backend

## Root cause confermato

Vite (`[vite] ws proxy error: write ECONNABORTED`) riceve un `Page reload sent to client(s)` dal browser, che chiude la connessione WS. Vite poi prova a scrivere verso il backend su un socket già killato → errore.  
Quando il backend WS uccide la connessione per inattività (timeout uvicon troppo stretti), il browser/WS client chiude e ricrea, innescando il reload loop.

## Implementazione

### 1. Aumentare timeout WebSocket in `start.ps1`
**File**: `start.ps1` (linea 121)  
**Cambiamento**: aggiungere flag uvicorn per WS keepalive.

```powershell
# PRIMA
uvicorn app.main:app --port $BACKEND_PORT

# DOPO
uvicorn app.main:app --port $BACKEND_PORT --ws-ping-interval 60 --ws-ping-timeout 30 --ws-close-timeout 10
```

Valori:
- `--ws-ping-interval 60`: uvicorn pinga ogni 60s (default 20)
- `--ws-ping-timeout 30`: attende 30s la risposta (default 20)
- `--ws-close-timeout 10`: concede 10s al client per confermare close (default 10)

### 2. Aggiungere ping attivo nell'endpoint scalping WS
**File**: `synthtrade/backend/app/scalping/router.py`  
**Luogo**: funzione `scalping_websocket` (riga 102)

Dopo `await ws.accept()` (riga 115), aggiungere task asincrono di keepalive:

```python
async def _ws_keepalive(ws: WebSocket, interval: int = 30):
    """Mantiene viva la connessione WS inviando ping ogni interval secondi."""
    try:
        while True:
            await asyncio.sleep(interval)
            await ws.send_json({"type": "ping", "timestamp": _now()})
    except Exception:
        pass  # client disconnesso o altro errore — silent exit

keepalive_task = asyncio.create_task(_ws_keepalive(ws))
try:
    # ... codice esistente del loop ...
finally:
    keepalive_task.cancel()
    try:
        await keepalive_task
    except asyncio.CancelledError:
        pass
```

Importante: integrare con il try/except esistente senza rompere la logica di pulizia `_scalping_ws_connections.remove(ws)`.

### 3. Gestire `ping` in arrivo dal backend → rispondere `pong`
Già implementato nella sezione `msg.get("type") == "ping"` (righe 171-172).  
Verificare che continui a funzionare. **Nessuna modifica necessaria qui**.

### 4. Logging migliorato per disconnect
**File**: `synthtrade/backend/app/scalping/router.py` (righe 175-182)

Aggiungere log dell'eccezione esatta per capire se i client si disconnettono per timeout, errore di rete, o altro:

```python
except WebSocketDisconnect as e:
    if ws in _scalping_ws_connections:
        _scalping_ws_connections.remove(ws)
    logger.info("Scalping WS client disconnected (%d remaining): %s", len(_scalping_ws_connections), e)
except Exception as e:
    if ws in _scalping_ws_connections:
        _scalping_ws_connections.remove(ws)
    logger.error("Scalping WS error (%d remaining): %s", len(_scalping_ws_connections), e)
```

## Note

- Non toccare il frontend: il problema è nel backend che chiude WS troppo presto.
- Non rimuovere `--reload` da uvicorn: serve in dev.
- Dopo le modifiche, riavviare backend e testare reload del browser: gli errori `ECONNABORTED` dovrebbero sparire o ridursi drasticamente.
- Se persistono, il prossimo step è aggiungere il ping anche dal frontend (`ScalpingWsService`) per avere un keepalive bidirezionale.
