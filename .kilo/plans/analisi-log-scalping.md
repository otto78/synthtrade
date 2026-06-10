# Analisi Log Scalping - 2026-06-10

## Problemi Identificati

### 1. CRITICO: Exchange non inizializzato (ERROR)
- **Log**: `Live mode requested but exchange is not initialized!`
- **Root cause**: Session in modalità `live`, ma `_execution_state["exchange"]` è `None`
- **Analisi codice**: `router.py:1553` inizializza a `None`, `router.py:1566-1567` imposta l'adapter SOLO se `session["mode"] == "live"`
- **Problema**: Il log mostra `mode=paper` nella session (line 393), ma i trade segnalati hanno `side=BUY` senza controllare se l'exchange esiste

### 2. WARNING: APScheduler jobs missed
- **Log**: `Run time of job "heartbeat_job" was missed by 0:00:01-3s`
- **Root cause**: Task di longo esecuzione blocca l'event loop
- **Analisi**: Le chiamate al modello AI (model_client.py) durano 25+ secondi, causando delay accumulati

### 3. Supervisor ticker error: 'choices' (ERROR)
- **Log**: `Supervisor tick error: 'choices'`
- **Root cause**: `model_client.py:65` accede a `data["choices"]` senza verificare che esista
- **Problema**: Risposta non standard dal modello AI (probabilmente errore 404 o formato diverso)

### 4. Cooldown strategia supervisore attivo
- **Log**: `Strategy change cooldown attivo — 10/3 min rimanenti`
- **Root cause**: `supervisor_scheduler.py:130-138` blocca cambio strategia troppo frequente
- **Analisi**: Supervisor propone `rsi_bollinger` ma cooldown di 20 minuti blocca l'attuazione

## Azioni Richieste

### Priorità 1: Fix Exchange Initialization
1. Verificare che la sessione sia realmente in modalità `live` prima di tentare trade live
2. Aggiungere controllo robusto: se `live` ma exchange mancante, rifiutare esplicitamente

### Priorità 2: Fix Scheduler Jobs Missed
1. Spostare le chiamate AI in threadpool separato o aumentare timeout
2. Usare `asyncio.to_thread` per non bloccare l'event loop principale

### Priorità 3: Fix Model Response Parsing
1. `model_client.py:65`: aggiungere fallback se `data.get("choices")` è None
2. `eval_parser.py:64-66`: gestire risposta vuota o malformato

### Priorità 4: Configurazione API Mancanti
- WhaleAlert API key: `skipping`
- CoinGecko /news: `requires paid API key`
- BinanceRSS: `empty response body`

## File Coinvolti
- `app/scalping/router.py` - logica sessione, trade live/paper
- `app/ai/model_client.py` - chiamate ai modelli, parsing risposta
- `app/scalping/supervisor/supervisor_scheduler.py` - cooldown strategia
- `app/scalping/opportunity/pollers/*` - polleri API esterne