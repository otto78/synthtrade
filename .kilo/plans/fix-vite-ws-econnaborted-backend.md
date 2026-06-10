# Fix ECONNABORTED ws proxy — causa: WebSocket backend senza keepalive

## Root cause confermata

Il messaggio `Page reload sent to client(s)` + `ECONNABORTED` è generato da Vite quando il **browser chiude la connessione WS** e Vite prova a scrivere sul socket già chiuso.  
In un progetto Angular CLI (che usa Vite internamente in dev), questo accade quando:

1. Il frontend non invia ping → il backend/uvicorn/eventuale proxy intermedio considera la connessione idle e la chiude dopo il timeout di default (~20s per uvicorn).
2. Il client riceve `close` silenzioso, il WS viene ricreato dal `retryWhen`, ma **Vite non sa che il client è già andato via** e continua a scrivere verso il backend → schermata `ECONNABORTED`.

## Piano (solo backend)

### 1\. Aggiungere keepalive all'endpoint WebSocket scalping  
File: `synthtrade/backend/app/scalping/router.py`

- La route esistente (`@ws_scalping_router.websocket("/scalping")`) accetta già un ping applicativo (`"type": "ping"` → `"type": "pong"`), ma **non invia ping attivi**.  
- Aggiungere un task asincrono interno che, dopo `N` secondi di inattività, invia automaticamente un ping al client.  
- Se il client non risponde entro il timeout, chiudere la connessione.  
- Importante: **non bloccante** e cancellabile al disconnect.

### 2\. Aumentare i timeout di Uvicorn per i WebSocket  
File: `start.ps1` e `synthtrade/backend/app/main.py`

- Uvicorn usa di default `ws_ping_interval=20`, `ws_ping_timeout=20`, `ws_close_timeout=10`.  
- Aumentare questi valori solo per il WS scalping (senza intaccare le API HTTP).

Opzioni:
- **A**: parametri globali di uvicorn in `start.ps1` → `--ws-ping-interval 60 --ws-ping-timeout 30 --ws-close-timeout 10`
- **B**: `WebSocket` ASGI `subprotocols` + middleware custom (più complesso, non serve qui).
- **C**: configurare la classe `WebSocket` in FastAPI con timeout custom.

Scelta consigliata: **A** (semplice, impatta solo WS e non le API REST).

### 3\. Spezzare il loop di broadcast pesante quando il client non sta scrivendo  
File: `synthtrade/backend/app/scalping/router.py:185` (`broadcast_scalping_event`)

- Se un client WS è chiuso ma ancora in lista, ogni `send_json` fallisce e viene aggiunto a `dead`.  
- Già gestito, ma aggiungere un contatore di errori consecutivi e un log chiaro quando un client viene rimosso per capire se sono i client a morire per timeout.

### 4\. (Opzionale ma utile) Aggiornare il frontend per mandare pong/pro puppare WS anche senza dati  
File: `synthtrade/frontend/synthtrade-ui/src/app/scalping/scalping-ws.service.ts`

- Aggiungere un timer locale che invia `ping` ogni 15s verso il backend.  
- Questo NON risolve il problema di fondo (è il backend che chiude), ma rende esplicito che il client è vivo e aiuta a capire chi sta morendo.

---

## Domande

1. **Vuoi modificare solo `start.ps1` (Opzione A) o anche aggiungere il ping attivo nel backend?**  
   Consiglio entrambi: aumentare il timeout uvicorn E aggiungere il ping attivo nel WS scalping.

2. **Hai bisogno di mantenere il supporto a `--reload`?**  
   Se sì, le modifiche a uvicorn in `start.ps1` non toccano il reload; se no, rimuovere `--reload` evita anche altri problemi di WS durante i reload del codice.

3. **Vuoi loggare ogni disconnect del WS scalping con l'eccezione esatta (errore + client IP)?**  
   Utile per capire se i client si disconnettono sempre dallo stesso browser o da più fonti.
