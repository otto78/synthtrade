# Fix ECONNABORTED su proxy WebSocket Vite

## Problema
Ogni page reload genera errori `[vite] ws proxy error: Error: write ECONNABORTED` e `[vite] ws proxy socket error`.  
Il browser chiude la connessione WS prima che Vite possa inviare i dati buffered; il proxy quindi fallisce in scrittura verso il backend. È un comportamento noto di Vite in dev-mode quando il client disconnette bruscamente.

L'architettura WS è corretta:
- Backend: `ws_scalping_router` montato su `/ws/scalping` in `main.py:346`
- Frontend: `ScalpingWsService` con URL `${proto}//${loc.host}/ws/scalping`
- Proxy: `proxy.conf.json` regola `/ws` → `ws://localhost:8888` con `ws: true`

## Piano

### 1. Aggiungere `vite.config.ts` nella root del progetto frontend
Percorso: `synthtrade/frontend/synthtrade-ui/vite.config.ts`

Configurazione minima per Angular CLI: non esiste un file Vite nativo (Angular usa `@angular/build:dev-server` che usa Vite internamente ma non espone un file di config utente convenzionale).  
Tuttavia **Angular 20 + @angular/build:dev-server** supporta `vite.config.ts` se presente, oppure usa `server.extraOptions` in `angular.json`.  
Verificare se `vite.config.ts` viene caricato, altrimenti usare `angular.json`.

Opzione A (preferita, più pulita): creare `vite.config.ts`  
Opzione B: aggiungere `server` options in `angular.json` → `architect.serve.options`

### 2. Impostazioni Vite consigliate
- Aumentare `server.keepaliveTimeout` e `server.fsPoll` per non chiudere WS in idle
- `server.headers` con `Connection: keep-alive`
- `proxy` con `ws: true, xfwd: true, secure: false` (fallback se il proxy nativo di Angular non passa opzioni)

### 3. Angular `angular.json`: aggiungere `server.extraOptions`
Se Vite config non viene caricato direttamente, usare:
```json
"serve": {
  "builder": "@angular/build:dev-server",
  "options": {
    "proxyConfig": "proxy.conf.json",
    "extraOptions": {
      "keepaliveTimeout": 60000,
      "headers": {
        "Connection": "keep-alive"
      }
    }
  }
}
```

### 4. Frontend `scalping-ws.service.ts`: robustezza al reload
Il servizio già ha `retryWhen` con backoff. Aggiungere:
- Chiusura esplicita del `WebSocketSubject` al `ngOnDestroy`
- Gestione evento `close` con riconnessione immediata
- Opzionale: ping/pong heartbeat per mantenere alive la connessione

---

## Decisioni da confermare

1. **Usare `vite.config.ts` (Opzione A) o modificare `angular.json` (Opzione B)?**  
   Angular 20 usa Vite internamente; `vite.config.ts` è supportato se il build system lo carica. Se non funziona, fallback a `angular.json`.

2. **L'utente vuole anche fare refactoring del WS service per maggiore robustezza?**  
   Oppure vuole solo eliminare l'errore ECONNABORTED nel console?

3. **Il backend deve ricevere timeout più lunghi o logging aggiuntivo?**  
   Attualmente Uvicorn/FastAPI non ha `ws_ping_interval` configurato.
