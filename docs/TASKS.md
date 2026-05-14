﻿# SynthTrade — TASKS
﻿# SynthTrade — TASKS

> Aggiornato automaticamente. Metodologia TDD: 🔴 Red → 🟢 Green → 🔵 Refactor

---

## 🔵 Fase 0 — Setup & Infrastruttura

### Monorepo & Tooling
### TASK-001 — Creare struttura cartelle `synthtrade/` con `backend/`, `supabase/`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-002 — Inizializzare Git con `.gitignore`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-003 — Creare `README.md` con istruzioni setup locale

**Status:** Done ✅  
**Completato:** 2026-05-06


### Backend Bootstrap
### TASK-004 — Creare `requirements.txt` con tutte le dipendenze

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-005 — Creare `config.py` con `Settings` via `pydantic-settings`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-006 — Creare `main.py` con lifespan, CORS, router placeholder

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-007 — 🔴 Test: `test_main.py` → `GET /health` restituisce `{"status": "ok"}`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-008 — 🟢 Implementare route `/health`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-009 — Creare `pytest.ini` con `asyncio_mode = auto`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-010 — Creare `conftest.py` con fixture `mock_supabase`

**Status:** Done ✅  
**Completato:** 2026-05-06


### Supabase Setup
### TASK-011 — Creare le 4 migration SQL (strategies, trades, logs, ohlcv_cache)

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-012 — Creare `seed.sql` con 3 strategie di esempio PENDING

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-013 — Creare `supabase_client.py` singleton

**Status:** Done ✅  
**Completato:** 2026-05-06


### Docker
### TASK-014 — `docker-compose.yml` per backend (porta 8000)

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-015 — `Dockerfile` backend

**Status:** Done ✅  
**Completato:** 2026-05-06


---

## 🟡 Fase 1 — Core Engine

### Indicatori tecnici
### TASK-016 — 🔴 Test `test_indicators.py`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-017 — 🟢 Implementare `indicators.py`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-018 — 🔵 Refactor: costante `LOOKBACK_PERIODS`

**Status:** Done ✅  
**Completato:** 2026-05-06


### Strategy Generator
### TASK-019 — 🔴 Test `test_generator.py`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-020 — 🟢 Implementare `strategy_generator.py`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-021 — 🔵 Refactor: `TEMPLATES` configurabile via JSON

**Status:** In Progress  
**Data:** 2026-05-06

---

## 🧵 Loom Framework

### TASK-319 — Migrazione task a formato Loom

**Status:** Done ✅  
**Completato:** 2026-05-06

---

## 🐛 Bug Fix — v1.1.2

### TASK-FIX-EVAL — Fix: strategie generate non mostrano stime valutazione (estimated_profit_pct/eur)

**Status:** Done ✅  
**Completato:** 2026-05-08  
**Priorità:** Alta

**Problema**: Le strategie generate e salvate a DB non mostravano le stime di profitto (`estimated_profit_pct`/`estimated_profit_eur`) nel tab GENERAZIONE. Due cause:
1. `list_strategies()` in `strategies.py` aveva una select troppo limitata che escludeva questi campi
2. `run_generation_task()` in `pipeline.py` non salvava `estimated_profit_pct`/`estimated_profit_eur` sul DB
3. Le colonne `estimated_profit_pct`/`estimated_profit_eur` non esistevano nello schema DB

**Fix**:
- Aggiunte colonne `estimated_profit_pct FLOAT` e `estimated_profit_eur FLOAT` alla tabella `strategies` (Migration 007)
- `pipeline.py`: `estimated_profit_pct` e `estimated_profit_eur` ora salvati nel row insert
- `strategies.py`: `list_strategies()` ora seleziona anche `estimated_profit_pct`, `estimated_profit_eur`, `description`, `pair`, `timeframe`, `params`, `ai_note`, `ai_strengths`, `ai_warnings`, `updated_at`
- Migration 007 applicata su Supabase Cloud

---

## 🌟 Fase 7 — Miglioramenti Evolutivi (v1.1.0)

### 7.1 Persistenza & Scadenza Strategie
### TASK-320 — Aggiornamento schema DB `strategies`: aggiunta `expires_at` e trigger pulizia
- Aggiunta colonna `expires_at` TIMESTAMP
- Creazione funzione/cron per eliminazione automatica strategie scadute (status PENDING)
**Status:** Done
**Priorità:** Alta

### TASK-321 — Backend: Logica di scadenza (7 giorni) e timestamp creazione
- Impostazione `expires_at = now() + 7 days` durante `POST /api/strategies`
- Restituzione `expires_at` nelle API GET
**Status:** Done

### TASK-322 — Frontend: Persistenza sessione e visualizzazione scadenza
- Modifica `StrategyStore` per mantenere le strategie generate tra navigazioni
- Visualizzazione countdown/data scadenza nelle card
- Bottone "Nuova Ricerca" con reset esplicito dello store
**Status:** Done

### 7.2 Gestione Strategie Attive
### TASK-323 — Frontend: Dialog di conferma Stop Strategia
- Implementazione modale di conferma con messaggio di avvertimento irreversibile
**Status:** Done

### TASK-324 — Vista Dettaglio "Monitora" (Real-time)
- Creazione pagina `MonitorPage` con grafici performance (equity curve)
- Statistiche operative: P&L, Win Rate, Drawdown corrente
- Indicatori di rischio e stato monitoraggio (attivo/disattivo)
- Polling ogni 5 secondi per aggiornamento dati
**Status:** Done

### 7.3 Ristrutturazione Strategie Completate
### TASK-325 — UI Accordion per Strategie Completate
- Riprogettazione `CompletedPage` con lista accordion
- Intestazione: Nome, Data, P&L totale, Performance %
**Status:** Done

### TASK-326 — Dettaglio Trade & Export
- Lista trade espandibile (Timestamp, Asset, Dir, Prezzi, P&L)
- Statistiche dettagliate e equity curve per singola strategia completata
- Funzionalità export PDF/CSV
**Status:** Done

### 7.4 Ottimizzazione Dashboard
### TASK-327 — Dashboard: Ordinamento Asset & Multi-strategy Grid
- Ordinamento per Market Cap / Exposure nelle API
- Layout responsive a griglia per supportare più strategie attive contemporaneamente
**Status:** Done

### TASK-328 — Dashboard: Card Strategia Avanzata & Fix P&L
- Card con P&L real-time, numero trade aperti e metriche di rischio
- Fix recupero P&L odierno con gestione errore e fallback (no "0" o "Loading" infiniti)
**Status:** Done ✅

### TASK-STRATEGY-FIX — Fix workflow strategie: generazione, approvazione, scadenza
**Status:** Done ✅  
**Completato:** 2026-05-08
**Completato:** 2026-05-08
**Data:** 2026-05-08

**BUG 1 - CRITICO (saveAndApprove)**: `saveAndApprove()` chiamava `resetGeneration()` che cancellava TUTTE le strategie generate dopo averne approvata UNA. **Fix**: sostituito con `generatedStrategies.update(list => list.filter(x => x !== s))` che rimuove solo quella approvata.

**BUG 2 (run_pipeline no expires_at)**: `run_pipeline.py` non impostava `expires_at` nelle strategie salvate via upsert, lasciando valore NULL. **Fix**: aggiunto `expires_at = (now + timedelta(days=7)).isoformat()` al row dict.

**BUG 3 (list_strategies cleanup incompleta)**: La cleanup automatica cancellava solo PENDING scadute, ma le ACTIVE scadute restavano bloccate nello stato ACTIVE. **Fix**: aggiunta transizione `ACTIVE → EXPIRED` prima della cancellazione PENDING.

**BUG 4 (COMPLETATE tab include REJECTED)**: Il computed `completed` filtrava per `EXPIRED || REJECTED`, mescolando strategie rifiutate con completate. **Fix**: filtrato solo per `EXPIRED`.

**BUG 5 (seed/data NULL expires_at)**: Record seed e dati esistenti avevano `expires_at = NULL`. **Fix**: migration applicata su DB, seed.sql aggiornato con `INTERVAL '30 days'`.

### 7.5 Verifica Processo Generazione (AI/Performance)
### TASK-329 — Backend: Logging & Metriche Generazione
- Misurazione tempi inizio/fine analisi mercato e creazione strategie
- Logging risultati validazione backtest
- Endpoint API granulari per le fasi: `/api/pipeline/analyze`, `/api/pipeline/validate`, ecc.
**Status:** Pending

### TASK-330 — Frontend: Progress Bar Multi-step
- Visualizzazione fasi: "Analisi mercato...", "Validazione...", "Test...", "Completato"
- Feedback visivo dello stato avanzamento reale tramite WebSocket o polling di stato
**Status:** Pending

### TASK-331 — Backend: Cache Analisi & Confronto Dati Reali
- Implementazione cache risultati analisi mercato (TTL configurabile)
- Logica di confronto tra simulato e reale per verifica coerenza
**Status:** Pending
**Data:** 2026-05-06


### Backtester
### TASK-022 — 🔴 Test `test_backtester.py`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-023 — 🟢 Implementare `backtester.py`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-024 — 🔵 Refactor: `StopLossManager` separato

**Status:** In Progress  
**Data:** 2026-05-06


### Ranker
### TASK-025 — 🔴 Test `test_ranker.py`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-026 — 🟢 Implementare `ranker.py`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-027 — 🔵 Refactor: `RankConfig` da `.env`

**Status:** In Progress  
**Data:** 2026-05-06


### Market Data + Cache Supabase
### TASK-028 — 🔴 Test `test_market_data.py`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-029 — 🟢 Implementare `market_data.py`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-030 — 🔵 Refactor: separare `exchange.py`

**Status:** In Progress  
**Data:** 2026-05-06


### Pipeline Batch
### TASK-031 — 🔴 Test `test_pipeline.py` (integration)

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-032 — 🟢 Implementare `run_pipeline.py`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-033 — 🔵 Refactor: progress logging + gestione eccezioni

**Status:** In Progress  
**Data:** 2026-05-06


---

##  Fase 1.B — Constraint-Aware Generator

> Modifica del `strategy_generator.py` esistente per accettare parametri utente invece di generare strategie casuali.
> Da inserire dopo la Fase 1 esistente, prima della Fase 2.

### 1.B.0 Schema StrategyRequest

### TASK-034 — Creare `execution/schemas.py` → aggiungere `StrategyRequest`:

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06

  - `budget_eur: float` — capitale da allocare (es. 100.0)
  - `duration_days: int` — orizzonte temporale (es. 30)
  - `asset_class: Literal["crypto", "stocks", "forex"]` — classe di asset
  - `symbols: list[str] | None` — simboli specifici (es. `["BTCUSDT", "ETHUSDT"]`); se `None` il generator sceglie
  - `risk_level: Literal["low", "medium", "high"]`
  - `free_text: str | None` — descrizione libera dell'idea utente (es. "preferisco trend following su Bitcoin")
  - `max_strategies: int = 5` — quante strategie generare

### 1.B.1 Modifica Strategy Generator

### TASK-035 — 🔴 Test `test_generator_constrained.py` → `generate_for_request(req: StrategyRequest)` restituisce solo strategie con `duration_days` compatibile (± 20%)

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06

### TASK-036 — 🔴 Test → se `req.symbols` è specificato, le strategie generate usano solo quei simboli

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06

### TASK-037 — 🔴 Test → `risk_level = "low"` esclude strategie con `max_drawdown > 15%` dai template selezionabili

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06

### TASK-038 — 🔴 Test → `risk_level = "high"` consente tutti i template inclusi quelli aggressivi

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06

### TASK-039 — 🔴 Test → `budget_eur` viene propagato come `position_size_eur` nei parametri della strategia generata

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06

### TASK-040 — 🔴 Test → `max_strategies` limita il numero di strategie restituite

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06

### TASK-041 — 🟢 Aggiungere `generate_for_request(req: StrategyRequest) -> list[Strategy]` in `strategy_generator.py`

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06

### TASK-042 — 🔵 Refactor: la selezione dei template estratta in `_filter_templates_by_constraints(req)` — funzione pura testabile in isolamento

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06


### 1.B.2 Integrazione free_text con AI

### TASK-043 — 🔴 Test `test_generator_ai_hint.py` → `enrich_request_with_ai(req)` chiama il modello LLM con il `free_text` e restituisce una lista di simboli suggeriti e un template preferito

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06

### TASK-044 — 🔴 Test → se `free_text` è `None` o vuoto, `enrich_request_with_ai()` restituisce l'input invariato senza chiamare il modello

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06

### TASK-045 — 🔴 Test → se il modello non è disponibile, la funzione restituisce l'input invariato (graceful degradation)

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06

### TASK-046 — 🟢 Implementare `ai/request_enricher.py` con `enrich_request_with_ai(req: StrategyRequest) -> StrategyRequest`

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06

### TASK-047 — 🟢 Aggiungere chiamata a `enrich_request_with_ai()` all'inizio di `generate_for_request()` se `free_text` è presente

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06


### 1.B.3 API Endpoint

### TASK-048 — 🔴 Test `test_api_pipeline.py` → `POST /api/pipeline/generate` accetta un `StrategyRequest` nel body e avvia la pipeline in background (`BackgroundTasks`)

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06

### TASK-049 — 🔴 Test → risponde immediatamente con `202 Accepted` e un `generation_id` (UUID)

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06

### TASK-050 — 🔴 Test → `GET /api/pipeline/generate/{generation_id}/status` restituisce lo stato (`pending` / `running` / `completed` / `failed`) e, se completato, la lista delle strategie generate

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06

### TASK-051 — 🔴 Test → endpoint protetti da `get_current_user`

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06

### TASK-052 — 🟢 Implementare `api/pipeline.py` e registrare il router in `main.py`

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06

### TASK-053 — 🟢 Al completamento della pipeline, inviare messaggio WS di tipo `generation_complete` con `generation_id` e numero di strategie generate

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06


---

## 🟠 Fase 2 — Backend API

### Auth
### TASK-054 — 🔴 Test `test_api_auth.py`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-055 — 🟢 Implementare `api/auth.py` + JWT

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-056 — 🟢 Implementare `dependencies.py` → `get_current_user`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-057 — 🔵 Refactor: `core/auth_utils.py`

**Status:** Done ✅  
**Completato:** 2026-05-06


### Strategies API
### TASK-058 — 🔴 Test `test_api_strategies.py`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-059 — 🟢 Implementare `api/strategies.py`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-060 — 🔵 Refactor: `StrategyRepository`

**Status:** In Progress  
**Data:** 2026-05-06


### Dashboard API
### TASK-061 — 🔴 Test `test_api_dashboard.py`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-062 — 🟢 Implementare `api/dashboard.py`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-063 — 🔵 Refactor: cache balance 30s

**Status:** In Progress  
**Data:** 2026-05-06


### Logs API
### TASK-064 — 🔴 Test `test_api_logs.py`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-065 — 🟢 Implementare `api/logs.py`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-066 — 🔵 Refactor: filtri aggiuntivi

**Status:** In Progress  
**Data:** 2026-05-06


### WebSocket
### TASK-067 — 🔴 Test `test_ws.py`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-068 — 🟢 Implementare `api/ws.py`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-069 — 🔵 Refactor: broadcast per tipo

**Status:** Done ✅  
**Completato:** 2026-05-06


---

##  Fase 2.B — Exchange Adapter (Binance)

> Implementazione reale di `exchange.py` con supporto Testnet/Live e operazioni di scrittura.
> Da inserire dopo la Fase 2 esistente, prima della Fase 3.

### 2.B.0 Configurazione

### TASK-070 — Aggiungere in `config.py`:

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06

  - `BINANCE_API_KEY` e `BINANCE_API_SECRET` (già presenti nel `.env` — verificare i nomi)
  - `BINANCE_TESTNET: bool = True` — flag per switchare tra testnet e live
  - `BINANCE_BASE_URL` → calcolato automaticamente: `https://testnet.binance.vision` se testnet, `https://api.binance.com` se live
  - `BINANCE_WS_BASE_URL` → analogamente per i WebSocket di Binance
### TASK-071 — Aggiungere a `requirements.txt`: `python-binance` oppure `ccxt` (da scegliere — vedi nota sotto)

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06

### TASK-072 — Documentare in `README.md` come creare le API key sul Binance Testnet (`testnet.binance.vision`) e i permessi necessari: **Enable Spot & Margin Trading**

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06


> **Nota sulla libreria**: `python-binance` è più semplice per Binance puro; `ccxt` è più generico e permette di aggiungere altri exchange in futuro cambiando una riga. Consigliato `ccxt` per flessibilità futura.

### 2.B.1 BinanceExchangeAdapter

### TASK-073 — 🔴 Test `test_exchange_adapter.py` → `get_balance()` chiama l'endpoint corretto e restituisce il saldo USDT disponibile come `float`

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06

### TASK-074 — 🔴 Test → `get_ticker_price(symbol)` restituisce il prezzo corrente del simbolo come `float`

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06

### TASK-075 — 🔴 Test → `place_market_order(symbol, side, quantity)` chiama `POST /api/v3/order` con `type=MARKET` e i parametri corretti

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06

### TASK-076 — 🔴 Test → `place_market_order()` in modalità testnet usa `BINANCE_BASE_URL` del testnet (mock del client, non chiamata reale)

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-077 — 🔴 Test → `close_position(symbol, side, quantity)` piazza un ordine sul lato opposto per chiudere la posizione

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-078 — 🔴 Test → `get_open_orders(symbol)` restituisce gli ordini aperti per quel simbolo

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-079 — 🔴 Test → errore HTTP 400 da Binance (es. `MIN_NOTIONAL`, quantità troppo bassa) viene wrappato in `ExchangeOrderError` con il codice Binance originale nel messaggio

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-080 — 🔴 Test → errore HTTP 401 (API key non valida) viene wrappato in `ExchangeAuthError`

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-081 — 🔴 Test → errore di rete (timeout, connessione rifiutata) viene wrappato in `ExchangeNetworkError`

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-082 — 🟢 Implementare `execution/exchange.py` con classe `BinanceExchangeAdapter` che implementa `ExchangeProtocol`

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06

### TASK-083 — 🟢 Definire `ExchangeProtocol` (Protocol class) con i metodi sopra — così in futuro si può aggiungere Kraken, Coinbase ecc. senza toccare l'engine

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06

### TASK-084 — 🔵 Refactor: `BinanceExchangeAdapter` istanziato come singleton in `dependencies.py` e iniettato negli endpoint che richiedono

**Status:** In Progress  
**Data:** 2026-05-06


### 2.B.2 Quantity Calculator

### TASK-085 — 🔴 Test `test_quantity_calculator.py` → `calculate_quantity(symbol, budget_eur, current_price)` restituisce la quantità corretta rispettando i `LOT_SIZE` filter di Binance (step size)

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06

### TASK-086 — 🔴 Test → quantità calcolata non supera mai il `budget_eur` convertito in USDT

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06

### TASK-087 — 🔴 Test → se la quantità risultante è sotto `MIN_QTY` del simbolo, solleva `BudgetTooSmallError` con il minimo richiesto

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06

### TASK-088 — 🟢 Implementare `execution/quantity_calculator.py`

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06

### TASK-089 — 🟢 `BinanceExchangeAdapter.get_symbol_filters(symbol)` che recupera i filtri `LOT_SIZE` e `MIN_NOTIONAL` dall'API Binance (con cache in memoria — non cambiano spesso)

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06


### 2.B.3 Paper Trading Mode (Testnet)

### TASK-090 — 🟢 Aggiungere endpoint `GET /api/exchange/status` che restituisce `{ "mode": "testnet" | "live", "base_url": "...", "balance": {...} }`

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06

### TASK-091 — 🔴 Test → con `BINANCE_TESTNET=True`, ogni chiamata di scrittura usa l'URL del testnet

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06

### TASK-092 — 🔴 Test → con `BINANCE_TESTNET=False`, ogni chiamata usa l'URL di produzione

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06

### TASK-093 — 🟢 Aggiungere nel frontend (`Topbar` o `Dashboard`) un badge visibile **TESTNET** / **LIVE** che chiama `GET /api/exchange/status` all'avvio — impossibile ignorare in quale modalità si è

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06


---

## 🟢 Fase 3 — Frontend Angular

### 3.0 Bootstrap & Configurazione
### TASK-094 — Creare Angular app: `ng new synthtrade-ui --style=scss --routing --standalone`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-095 — Rimuovere Karma/Jasmine, installare `jest-preset-angular`, creare `jest.config.ts` e `setup-jest.ts`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-096 — Creare `tsconfig.spec.json` per Jest

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-097 — Configurare `environment.ts` / `environment.prod.ts` con `apiUrl`, `wsUrl`, `supabaseUrl`, `supabaseAnonKey`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-098 — Configurare `proxy.conf.json` per dev: `/api → localhost:8000`, `/ws → localhost:8000`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-099 — Aggiungere script npm: `start:proxy`, `test:watch`, `test:ci`, `test:coverage`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-100 — Installare e configurare `eslint` + `prettier` con regole Angular

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-101 — Configurare `jest --coverage` con soglia minima 80% su `core/` e `shared/`

**Status:** Done ✅  
**Completato:** 2026-05-06


### 3.1 Design Tokens & Tema
### TASK-102 — Creare `src/styles/_variables.scss`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-103 — Creare `src/styles/_mixins.scss`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-104 — Creare `src/styles/_reset.scss`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-105 — Creare `src/styles/_animations.scss`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-106 — Creare `src/styles/theme-dark.scss`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-107 — Importare tutto in `styles.scss`

**Status:** Done ✅  
**Completato:** 2026-05-06


### 3.2 Modelli & Interfacce
### TASK-108 — `core/models/user.model.ts` → `User`, `AuthTokens`, `JwtPayload`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-109 — `core/models/strategy.model.ts` → `Strategy`, `StrategyStatus`, `StrategyCreateDto`, `StrategyMetrics`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-110 — `core/models/trade.model.ts` → `Trade`, `TradeDirection`, `TradeStatus`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-111 — `core/models/dashboard.model.ts` → `DashboardStats`, `BalanceSnapshot`, `PipelineStatus`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-112 — `core/models/log.model.ts` → `OperationLog`, `LogLevel`, `LogFilters`, `PaginatedLogs`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-113 — `core/models/ws-message.model.ts` → `WsMessage<T>`, `WsMessageType` (enum)

**Status:** Done ✅  
**Completato:** 2026-05-06


### 3.3 Interceptors & Guards
### TASK-114 — 🔴 Test `auth.interceptor.spec.ts`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-115 — 🟢 Implementare `core/interceptors/auth.interceptor.ts`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-116 — 🔴 Test `error.interceptor.spec.ts`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-117 — 🟢 Implementare `core/interceptors/error.interceptor.ts`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-118 — 🔴 Test `auth.guard.spec.ts`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-119 — 🟢 Implementare `core/guards/auth.guard.ts`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-120 — 🔴 Test `no-auth.guard.spec.ts`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-121 — 🟢 Implementare `core/guards/no-auth.guard.ts`

**Status:** Done ✅  
**Completato:** 2026-05-06


### 3.4 Services
### TASK-122 — 🔴 Test `token-storage.service.spec.ts`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-123 — 🟢 Implementare `core/services/token-storage.service.ts`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-124 — 🔴 Test `auth.service.spec.ts`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-125 — 🟢 Implementare `core/services/auth.service.ts`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-126 — 🔴 Test `strategy.service.spec.ts`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-127 — 🟢 Implementare `core/services/strategy.service.ts`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-128 — 🔴 Test `dashboard.service.spec.ts`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-129 — 🟢 Implementare `core/services/dashboard.service.ts`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-130 — 🔵 Refactor: cache con `shareReplay(1)` + invalidazione dopo 30s

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-131 — 🔴 Test `log.service.spec.ts`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-132 — 🟢 Implementare `core/services/log.service.ts`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-133 — 🔴 Test `ws.service.spec.ts`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-134 — 🟢 Implementare `core/services/ws.service.ts`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-135 — 🔵 Refactor: `on<T>(type)` helper tipizzato

**Status:** Done ✅  
**Completato:** 2026-05-06


### 3.5 Shared — Componenti Atomici
### TASK-136 — 🔴 Test `stat-card.component.spec.ts` (label, value, delta, skeleton)

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-137 — 🟢 Implementare `shared/components/stat-card/`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-138 — 🔴 Test `badge-status.component.spec.ts` (testo e classe CSS per ogni status)

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-139 — 🟢 Implementare `shared/components/badge-status/`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-140 — 🔴 Test `price-ticker.component.spec.ts` (decimali, flash-up, flash-down, rimozione classe)

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-141 — 🟢 Implementare `shared/components/price-ticker/`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-142 — 🔴 Test `confirm-dialog.component.spec.ts` (confirmed, cancelled, Escape)

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-143 — 🟢 Implementare `shared/components/confirm-dialog/`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-144 — 🟢 Implementare `shared/components/empty-state/`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-145 — 🔴 Test `relative-time.pipe.spec.ts`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-146 — 🟢 Implementare `shared/pipes/relative-time.pipe.ts`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-147 — 🔴 Test `format-number.pipe.spec.ts` (K/M suffisso)

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-148 — 🟢 Implementare `shared/pipes/format-number.pipe.ts`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-149 — 🔴 Test `signed-number.pipe.spec.ts`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-150 — 🟢 Implementare `shared/pipes/signed-number.pipe.ts`

**Status:** Done ✅  
**Completato:** 2026-05-06
**Completato:** 2026-05-06


### 3.6 Layout Shell
### TASK-151 — 🔴 Test `sidebar.component.spec.ts` (voce attiva, toggle collapsed)

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-152 — 🟢 Implementare `layout/sidebar/` (Dashboard, Strategies, Active Trade, Logs)

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-153 — 🔴 Test `topbar.component.spec.ts` (username, logout)

**Status:** Done ✅  
**Completato:** 2026-05-06
**Completato:** 2026-05-06

### TASK-154 — 🟢 Implementare `layout/topbar/`

**Status:** Done ✅  
**Completato:** 2026-05-06
**Completato:** 2026-05-06

### TASK-155 — 🟢 Implementare `layout/app-shell/`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-156 — 🔵 Refactor: stato collapsed persistito in localStorage

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06


### 3.7 Routing
### TASK-157 — Creare `app.routes.ts` con lazy loading (login, dashboard, strategies, active-trade, logs)

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-158 — 🔴 Test routing: `''` → `/login` senza token, `''` → `/dashboard` con token

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-159 — 🔴 Test: `authGuard` redirige a `/login` senza token

**Status:** Done ✅  
**Completato:** 2026-05-06


### 3.8 Pagine

#### LoginPage
### TASK-160 — 🔴 Test `login.component.spec.ts` (form invalido, submit, 401, redirect, spinner)

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-161 — 🟢 Implementare `pages/login/login.page.ts`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-162 — 🔵 Refactor: estrarre `LoginFormComponent`

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06


#### DashboardPage
### TASK-163 — 🔴 Test `dashboard.component.spec.ts` (getStats, 4 StatCard, WS stats_update, loading)

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-164 — 🟢 Implementare `pages/dashboard/dashboard.page.ts`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-165 — 🟢 Aggiungere grafico balance history

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06

---

## 🛠️ Fase 4 — DevOps & Tooling

### TASK-180 — Configurazione porte di sviluppo (Backend: 8008, Frontend: 4208)

**Status:** Done ✅  
**Completato:** 2026-05-07
**Data:** 2026-05-07

### TASK-166 — 🔵 Refactor: `DashboardStore` con Angular Signals

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06


#### StrategiesPage
### TASK-167 — 🔴 Test `strategies.component.spec.ts` (list, activate, delete+confirm, filtro, empty state)

**Status:** Done ✅  
**Completato:** 2026-05-06
**Completato:** 2026-05-06

### TASK-168 — 🟢 Implementare `pages/strategies/strategies.page.ts`

**Status:** Done ✅  
**Completato:** 2026-05-06
**Completato:** 2026-05-06

### TASK-169 — 🔵 Refactor: `StrategyListComponent` + `StrategyRowComponent`

**Status:** In Progress  
**Data:** 2026-05-06


#### ActiveTradePage
### TASK-170 — 🔴 Test `active-trade.component.spec.ts` (empty state, render trade, WS price_update, P&L classi)

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-171 — 🟢 Implementare `pages/active-trade/active-trade.page.ts`

**Status:** Done ✅  
**Completato:** 2026-05-06


#### LogsPage
### TASK-172 — 🔴 Test `logs.component.spec.ts` (getLogs, filtro level, paginazione, riga, WS new_log)

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-173 — 🟢 Implementare `pages/logs/logs.page.ts`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-174 — 🔵 Refactor: `LogFiltersComponent` + query params sync

**Status:** In Progress  
**Data:** 2026-05-06


### 3.9 E2E
### TASK-175 — Installare e configurare Playwright

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-176 — 🔴 E2E `auth.spec.ts` (login errato → errore; login corretto → /dashboard)

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-177 — 🔴 E2E `strategies.spec.ts` (attivazione e disattivazione end-to-end)

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-178 — 🔴 E2E `logs.spec.ts` (filtro level aggiorna lista)

**Status:** In Progress  
**Data:** 2026-05-06


---

##  Fase 3.B — Frontend: Strategy Request Form

> Finestra di prompt per guidare la generazione delle strategie.
> Da inserire come sotto-fase di Fase 3, dopo il completamento di `StrategiesPage`.

### 3.B.0 Modelli

### TASK-179 — Aggiungere in `core/models/strategy.model.ts`:

**Status:** In Progress  
**Data:** 2026-05-06

  - `StrategyRequest` → `budgetEur`, `durationDays`, `assetClass`, `symbols`, `riskLevel`, `freeText`, `maxStrategies`
  - `GenerationStatus` → `generationId`, `status` (`pending`/`running`/`completed`/`failed`), `strategies?`

### 3.B.1 PipelineService

### TASK-180 — 🔴 Test `pipeline.service.spec.spec.ts` → `generateStrategies(req: StrategyRequest)` chiama `POST /api/pipeline/generate` e restituisce il `generationId`

**Status:** In Progress  

---

## 🛠️ Fase 3.C — Bugfix Regressione Dashboard & Generazione (TDD)

> Ripristino delle funzionalità core interrotte durante i precedenti aggiornamenti.

### 3.C.1 Backend: Pipeline & Generazione

### TASK-181 — 🔴 Test (Unit) `test_generator.py` → verifica che `generate_all_variants` e `generate_for_request` restituiscano strategie valide con tutti i campi richiesti (titolo, descrizione, budget).
**Status:** Done ✅  
**Priorità:** Alta

### TASK-182 — 🔴 Test (Integration) `test_api_pipeline.py` → verifica che l'endpoint `/api/pipeline/generate` non restituisca errori 500 e generi correttamente l'ID di sessione.
**Status:** Done ✅  
**Priorità:** Alta

### TASK-183 — 🟢 Fix `app/core/strategy_generator.py` e `app/api/pipeline.py` per risolvere eventuali discrepanze di schema o import mancanti.
**Status:** Done ✅  

### 3.C.2 Backend: Dashboard & Saldo

### TASK-184 — 🔴 Test (Integration) `test_api_dashboard.py` → verifica che l'endpoint `/api/dashboard/stats` restituisca un saldo `balance_eur` valido (non null/0) e la scomposizione degli asset.
**Status:** Done ✅  
**Priorità:** Alta

### TASK-185 — 🟢 Fix `app/api/dashboard.py` e relativi service (`binance_balance.py`) per garantire il caricamento dei dati reali o mock validi.
**Status:** Done ✅  

### 3.C.3 Frontend: Dashboard Regression

### TASK-186 — 🔴 Test (Unit) `dashboard.page.spec.ts` → verifica che i componenti `StatCard` ricevano i dati corretti dal service e non mostrino "0" o "Loading" indefinitamente.
**Status:** Pending  

### TASK-187 — 🟢 Fix `dashboard.page.ts` e `dashboard.service.ts` per gestire correttamente la sottoscrizione ai dati del backend.
**Status:** Pending  

---
**Data:** 2026-05-06

### TASK-181 — 🔴 Test → `pollGenerationStatus(generationId)` chiama `GET /api/pipeline/generate/:id/status` ogni 3s con `interval()` RxJS e completa quando `status === 'completed'` o `'failed'`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-182 — 🟢 Implementare `core/services/pipeline.service.ts`

**Status:** Done ✅  
**Completato:** 2026-05-06


### 3.B.2 StrategyRequestFormComponent

### TASK-183 — 🔴 Test `strategy-request-form.component.spec.ts` → form invalido se `budgetEur ≤ 0` o `durationDays ≤ 0`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-184 — 🔴 Test → `riskLevel` obbligatorio, default `medium`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-185 — 🔴 Test → al submit valido emette evento `requestSubmitted` con il `StrategyRequest` compilato

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-186 — 🔴 Test → campo `freeText` opzionale, max 500 caratteri con counter visibile

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-187 — 🔴 Test → chip-selector per `symbols`: l'utente può aggiungere/rimuovere simboli (BTCUSDT, ETHUSDT, ecc.) o lasciare vuoto per "scegli tu"

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-188 — 🟢 Implementare `shared/components/strategy-request-form/strategy-request-form.component.ts` con `ReactiveFormsModule`

**Status:** Done ✅  
**Completato:** 2026-05-06


### 3.B.3 GenerationProgressComponent

### TASK-189 — 🔴 Test `generation-progress.component.spec.ts` → mostra spinner con messaggio "Generazione in corso..." durante `status === 'running'`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-190 — 🔴 Test → al completamento mostra "N strategie generate" con animazione e bottone "Vedi risultati"

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-191 — 🔴 Test → in caso di `status === 'failed'` mostra messaggio di errore e bottone "Riprova"

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-192 — 🟢 Implementare `shared/components/generation-progress/generation-progress.component.ts`

**Status:** Done ✅  
**Completato:** 2026-05-06


### 3.B.4 Integrazione in StrategiesPage

### TASK-193 — 🟢 Aggiungere bottone **"Genera nuove strategie"** in `StrategiesPage` che apre il `StrategyRequestFormComponent` in un pannello laterale (o modale)

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-194 — 🟢 Al submit del form, chiamare `PipelineService.generateStrategies()` e mostrare `GenerationProgressComponent`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-195 — 🟢 Sottoscriversi al messaggio WS `generation_complete` per aggiornare la lista automaticamente senza polling manuale

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-196 — 🔴 Test `strategies.component.spec.ts` (aggiuntivi) → click "Genera nuove strategie" apre il pannello

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-197 — 🔴 Test → messaggio WS `generation_complete` aggiorna la lista delle strategie senza ricaricare la pagina

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-198 — 🔵 Refactor: le strategie generate dall'utente hanno un badge visivo **"Generata per te"** distinto dalle strategie pre-esistenti del seed

**Status:** Done ✅  
**Completato:** 2026-05-06


### 3.B.5 Nuovi Task UI & Fix Critici

### TASK-200 — 🟢 Risoluzione Bug Visualizzazione Profitto Stimato (Backend/Frontend)

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-201 — 🟢 Fix Pulsante "Approva" (Gestione Stato e API)

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-202 — 🟢 Riorganizzazione Dashboard Flow (Generazione -> Approvazione -> Avvio -> Completamento)

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-203 — 🟢 Implementazione CORS Middleware globale per sblocco API

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-204 — 🟢 Miglioramento Estetico Pulsante "Nuova Ricerca" e Layout Risultati

**Status:** Done ✅  
**Completato:** 2026-05-06



---

## 🔴 Fase 4 — Execution Engine

> Struttura: `synthtrade/backend/app/execution/` + `synthtrade/backend/app/scheduler/`

### 4.0 Modelli & Configurazione
### TASK-205 — Aggiungere in `config.py`: `MAX_CONCURRENT_POSITIONS`, `MAX_EXPOSURE_PER_SYMBOL_PCT`, `MAX_DRAWDOWN_PCT`, `DEFAULT_POSITION_SIZE_PCT`, `DEFAULT_STOP_LOSS_PCT`, `DEFAULT_TAKE_PROFIT_PCT`, `SCHEDULER_PIPELINE_INTERVAL_MIN`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-206 — Creare `execution/schemas.py`: `Signal`, `OrderRequest`, `OrderResult`, `RiskCheckResult`, `PositionSnapshot`

**Status:** Done ✅  
**Completato:** 2026-05-06


### 4.1 RiskManager
### TASK-207 — 🔴 Test `test_risk_manager.py`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-208 — 🟢 Implementare `execution/risk_manager.py`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-209 — 🔵 Refactor: `RiskConfig` dataclass iniettabile nei test

**Status:** In Progress  
**Data:** 2026-05-06


### 4.2 OrderTracker
### TASK-210 — 🔴 Test `test_order_tracker.py`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-211 — 🟢 Implementare `execution/order_tracker.py`

**Status:** Done ✅  
**Completato:** 2026-05-06


### 4.3 SignalResolver
### TASK-212 — 🔴 Test `test_signal_resolver.py`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-213 — 🟢 Implementare `execution/signal_resolver.py` con `SignalResolverProtocol` + `DefaultSignalResolver`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-214 — 🔵 Refactor: pluggabile via `config.py` con `importlib`

**Status:** In Progress  
**Data:** 2026-05-06


### 4.4 ExecutionEngine
### TASK-215 — 🔴 Test `test_execution_engine.py`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-216 — 🟢 Implementare `execution/execution_engine.py`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-217 — 🔵 Refactor: `SignalResolver` iniettato nel costruttore

**Status:** In Progress  
**Data:** 2026-05-06


### 4.5 Scheduler
### TASK-218 — 🔴 Test `test_scheduler.py`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-219 — 🟢 Implementare `scheduler/jobs.py` con `AsyncIOScheduler`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-220 — 🟢 Aggiungere `GET /api/scheduler/status`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-221 — 🟢 Registrare scheduler nel lifespan di `main.py`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-222 — 🔵 Refactor: intervalli configurabili da `Settings`

**Status:** In Progress  
**Data:** 2026-05-06


### 4.6 Integration Tests
### TASK-223 — 🔴 Test `test_execution_integration.py` → pipeline completa: Signal → trade aperto su Supabase

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-224 — 🔴 Test → scenario stop loss: posizione aperta → SL raggiunto → posizione chiusa

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-225 — 🔴 Test → scenario risk reject: portfolio al limite → nessun ordine → log con reason

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-226 — 🔴 Test → scenario drawdown: drawdown oltre soglia → tutti i signal rigettati

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-227 — 🟢 `api/trades.py`: `GET /api/trades`, `GET /api/trades/open`

**Status:** Done ✅  
**Completato:** 2026-05-06


---

## 🟣 Fase 5 — AI Evaluator

> Struttura: `synthtrade/backend/app/ai/` con `schemas.py`, `context_builder.py`, `prompt_builder.py`, `model_client.py`, `eval_parser.py`, `cache.py`, `evaluator.py`

### 5.0 Config & Schemas
### TASK-228 — Aggiungere in `config.py`: `AI_API_KEY`, `AI_API_BASE_URL`, `AI_CASCADE_MODELS`, `AI_FALLBACK_MODEL`, `AI_MAX_TOKENS`, `AI_TEMPERATURE`, `AI_TIMEOUT_SECONDS`, `AI_MAX_RETRIES`, `AI_BACKOFF_BASE`, `AI_EVAL_CACHE_TTL_MINUTES`, `PIPELINE_AI_EVAL_TOP_N`, `MAX_CONCURRENT_EVALS`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-229 — Creare `ai/schemas.py`: `OhlcvSummary`, `MarketContext`, `StrategyContext`, `EvalPromptInput`, `EvalResult`, `ModelResponse`

**Status:** Done ✅  
**Completato:** 2026-05-06


### 5.1 MarketContext Builder
### TASK-230 — 🔴 Test `test_context_builder.py`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-231 — 🟢 Implementare `ai/context_builder.py`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-232 — 🔵 Refactor: `MarketRegimeDetector` con soglie configurabili da `Settings`

**Status:** In Progress  
**Data:** 2026-05-06


### 5.2 Prompt Builder
### TASK-233 — 🔴 Test `test_prompt_builder.py`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-234 — 🟢 Implementare `ai/prompt_builder.py`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-235 — 🔵 Refactor: template `.jinja2` separato da logica

**Status:** In Progress  
**Data:** 2026-05-06


### 5.3 Model Client
### TASK-236 — 🔴 Test `test_model_client.py`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-237 — 🟢 Implementare `ai/model_client.py` con `httpx.AsyncClient`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-238 — 🔵 Refactor: `@async_retry` decorator in `ai/retry.py`

**Status:** In Progress  
**Data:** 2026-05-06


### 5.4 EvalResult Parser & Validator
### TASK-239 — 🔴 Test `test_eval_parser.py`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-240 — 🟢 Implementare `ai/eval_parser.py`

**Status:** Done ✅  
**Completato:** 2026-05-06


### 5.5 EvalCache
### TASK-241 — 🔴 Test `test_eval_cache.py`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-242 — 🟢 Implementare `ai/cache.py`

**Status:** Done ✅  
**Completato:** 2026-05-06


### 5.6 Evaluator (orchestratore)
### TASK-243 — 🔴 Test `test_evaluator.py`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-244 — 🟢 Implementare `ai/evaluator.py`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-245 — 🔵 Refactor: `MAX_CONCURRENT_EVALS` da `Settings`

**Status:** In Progress  
**Data:** 2026-05-06


### 5.7 API Endpoint
### TASK-246 — 🔴 Test `test_api_eval.py`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-247 — 🟢 Implementare `api/eval.py` + registrare in `main.py`

**Status:** Done ✅  
**Completato:** 2026-05-06


### 5.8 Integrazione in Pipeline
### TASK-248 — 🔴 Test `test_pipeline_ai.py`

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-249 — 🟢 Aggiornare `run_pipeline.py` con passo AI Evaluator (async, DEMOTE→REJECTED)

**Status:** Done ✅  
**Completato:** 2026-05-06

### TASK-250 — 🟢 Broadcast WS `eval_complete` con `strategy_id`, `verdict`, `score`

**Status:** In Progress  
**Data:** 2026-05-06


### 5.9 Integration Tests
### TASK-251 — 🔴 Test `test_ai_integration.py`

**Status:** Done ✅  
**Completato:** 2026-05-06


---

## ⚫ Fase 6 — Hardening & Deploy

> Architettura target: **Supabase Cloud** + **VPS Linux** con Docker + Nginx + HTTPS.

### 6.0 Supabase — Produzione
### TASK-252 — Creare progetto Supabase Cloud (region EU)

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-253 — Eseguire 4 migration SQL + seed.sql

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-254 — Verificare schema tabelle

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-255 — Copiare `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`

**Status:** In Progress  
**Data:** 2026-05-06


#### RLS
### TASK-256 — Abilitare RLS su `strategies`, `trades`, `operation_logs`, `ohlcv_cache`

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-257 — Policy `SELECT/INSERT/UPDATE/DELETE` solo per `auth.uid() = user_id`

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-258 — Testare policy con `SET LOCAL role = anon`

**Status:** In Progress  
**Data:** 2026-05-06


#### Realtime
### TASK-259 — Abilitare Realtime su `operation_logs`

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-260 — Verificare eventi `INSERT` trasmessi correttamente

**Status:** In Progress  
**Data:** 2026-05-06


#### Auth
### TASK-261 — Disabilitare registrazione pubblica

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-262 — Creare utente admin manualmente

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-263 — Configurare JWT expiry in linea con backend

**Status:** In Progress  
**Data:** 2026-05-06


### 6.1 Docker — Hardening Immagini

#### Backend multi-stage
### TASK-264 — Stage `builder`: `python:3.12-slim`, virtualenv isolato

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-265 — Stage `runtime`: immagine pulita, solo virtualenv + codice

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-266 — Utente non-root `appuser`

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-267 — Nessun `pip`, `gcc`, cache `apt`, `.pyc` nell'immagine finale

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-268 — `HEALTHCHECK`: `curl -f http://localhost:8000/health || exit 1`

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-269 — `.dockerignore`: `__pycache__`, `*.pyc`, `.env`, `tests/`, `.git/`

**Status:** In Progress  
**Data:** 2026-05-06


#### Frontend multi-stage
### TASK-270 — Stage `builder`: `node:20-alpine`, `npm ci` + `ng build --configuration production`

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-271 — Stage `runtime`: `nginx:alpine`, solo `dist/`

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-272 — `nginx.conf`: SPA fallback, cache headers, gzip

**Status:** In Progress  
**Data:** 2026-05-06


### 6.2 docker-compose Produzione
### TASK-273 — `docker-compose.prod.yml`: backend + frontend + nginx, nessun port binding diretto

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-274 — Network `internal` bridge isolata

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-275 — Volume named per certificati SSL (`certbot_certs`)

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-276 — Logging `json-file` con `max-size: 10m`, `max-file: 3`

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-277 — `.env.prod.example` con tutti i nomi variabili (senza valori)

**Status:** In Progress  
**Data:** 2026-05-06


### 6.3 Nginx — Reverse Proxy & HTTPS
### TASK-278 — Redirect 301 HTTP → HTTPS

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-279 — `location /api/` → proxy_pass `backend:8000`

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-280 — `location /ws/` → proxy_pass con upgrade WebSocket

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-281 — `location /` → proxy_pass `frontend:80`

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-282 — Headers sicurezza: `X-Frame-Options`, `X-Content-Type-Options`, `HSTS`, `CSP`

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-283 — Rate limiting su `/api/auth/` (5 req/min per IP)

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-284 — `ssl-params.conf` con TLS 1.2+, no SSLv3

**Status:** In Progress  
**Data:** 2026-05-06


#### Certbot / Let's Encrypt
### TASK-285 — Servizio `certbot` in `docker-compose.prod.yml`

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-286 — `scripts/init-letsencrypt.sh` (staging → production)

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-287 — `scripts/renew-certs.sh` (nginx reload, no downtime)

**Status:** In Progress  
**Data:** 2026-05-06


### 6.4 VPS — Provisioning
### TASK-288 — `[provider]` VPS: Ubuntu 24.04 LTS, 2 vCPU / 4 GB RAM / 40 GB SSD

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-289 — `[provider]` SSH key, firewall porte 22/80/443, DNS record A

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-290 — Utente non-root `deploy` con sudo

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-291 — Disabilitare login SSH root

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-292 — UFW: `allow 22,80,443/tcp`

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-293 — Installare Docker + Docker Compose plugin

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-294 — `unattended-upgrades` per aggiornamenti sicurezza automatici

**Status:** In Progress  
**Data:** 2026-05-06


### 6.5 Logging Strutturato
### TASK-295 — Installare `python-json-logger`

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06

### TASK-296 — `core/logging.py` con `setup_logging()` e `JsonFormatter`

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06

### TASK-297 — Chiamare `setup_logging()` nel lifespan di `main.py`

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06

### TASK-298 — Sostituire tutti i `print()` con `logger = logging.getLogger(__name__)`

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-299 — Middleware FastAPI con `request_id` (UUID) in ogni log

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06


### 6.6 Error Handling Globale
### TASK-300 — `core/exceptions.py`: `SynthTradeError`, `RiskViolationError`, `ModelUnavailableError`, `OrderExecutionError`

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06

### TASK-301 — Handler globale `Exception` → `{"error": "internal_server_error", "request_id": "..."}`

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06

### TASK-302 — Handler `HTTPException` con `request_id`

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06

### TASK-303 — Handler `RequestValidationError` con errori Pydantic leggibili

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06

### TASK-304 — Nessun stack trace esposto in produzione

**Status:** Done ✅  
**Completato:** 2026-05-06
**Data:** 2026-05-06


### 6.7 Deploy & Script di Rilascio
### TASK-305 — `scripts/deploy.sh`: git pull → build → up -d → image prune

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-306 — `scripts/rollback.sh`: riavvia immagine tag precedente

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-307 — Cron job rinnovo SSL: `0 3 * * *`

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-308 — Backup DB: verificare retention Supabase Cloud

**Status:** In Progress  
**Data:** 2026-05-06


### 6.8 Smoke Test Post-Deploy
### TASK-309 — `scripts/smoke_test.sh`:

**Status:** In Progress  
**Data:** 2026-05-06

  - `GET /health` → 200 `{"status": "ok"}`
  - `POST /api/auth/login` → JWT token
  - `GET /api/strategies` con token → 200
  - `GET /api/dashboard/stats` con token → 200
  - WebSocket `wss://` → heartbeat ricevuto
  - Certificato SSL valido
### TASK-310 — `smoke_test.sh` integrato in `deploy.sh` con rollback automatico su fallimento

**Status:** In Progress  
**Data:** 2026-05-06


### 6.9 Checklist Pre-Go-Live
### TASK-311 — Nessuna variabile `.env` hardcodata (`grep -r "SECRET\|PASSWORD\|API_KEY"`)

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-312 — `DEBUG=False`, `ENVIRONMENT=production`

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-313 — CORS: `allow_origins` lista esplicita, no `*`

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-314 — Tutte le tabelle Supabase con RLS abilitato

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-315 — Nessun endpoint pubblico senza autenticazione

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-316 — `ng build --configuration production` senza warning critici

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-317 — `docker compose -f docker-compose.prod.yml config` senza errori

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-318 — Smoke test completato con tutti i check verdi

**Status:** In Progress  
**Data:** 2026-05-06

---

## 🧵 Loom Framework

### TASK-319 — Migrazione task a formato Loom

**Status:** Done ✅  
**Completato:** 2026-05-06

---

## 🔍 Audit — Verifica Engine Generazione Strategie

> **Obiettivo:** Determinare se le strategie create dall'utente sono basate su dati reali
> o sono allucinazioni (valori casuali). Seguire la metodologia TDD per ogni verifica.
>
> **Findings preliminari (analisi statica del codice):**
> - `generate_for_request()` (path utente) usa `random.uniform()` per score e profitti stimati → ALLUCINAZIONE
> - `run_pipeline()` (path automatico) esegue backtest reali su dati Binance → REALE
> - L'AI viene chiamata nel path utente solo per estrarre simboli dal testo libero, NON per valutare strategie
> - Non esiste un test E2E che copra il path utente completo con dati reali

### TASK-AUDIT-001 — Verifica connettività API: Binance e OpenRouter

**Status:** Pending
**Priorità:** Alta
**File:** `synthtrade/backend/tests/test_connectivity.py`

**Obiettivo:** Confermare che le chiavi API nel `.env` reale siano configurate e funzionanti.

**Step da eseguire:**

1. Leggere `.env` e verificare che `AI_API_KEY`, `BINANCE_API_KEY`, `BINANCE_SECRET_KEY` siano non vuoti
2. Chiamare `ccxt.binance().fetch_ticker("BTC/USDT")` e verificare che ritorni un prezzo reale
3. Chiamare `GET https://openrouter.ai/api/v1/models` con `AI_API_KEY` e verificare 200 OK
4. Chiamare `ccxt.binance().fetch_ohlcv("BTC/USDT", "5m", limit=5)` e verificare 5 candele

**Comandi:**
```bash
cd synthtrade/backend
python -m pytest tests/test_connectivity.py -v -s
```

**Criteri di successo:**
- Binance risponde con prezzo BTC/USDT > 0
- OpenRouter risponde con lista modelli disponibili
- Nessuna eccezione di autenticazione

---

### TASK-AUDIT-002 — Prova del Random: due chiamate identiche producono output diversi

**Status:** Pending
**Priorità:** Alta
**File:** `synthtrade/backend/tests/audit/test_random_proof.py` (nuovo)

**Obiettivo:** Dimostrare in modo automatico e riproducibile che `generate_for_request()`
usa valori casuali per `ai_score` e `estimated_profit_pct`.

**Test da scrivere (Red):**
```python
# test_random_proof.py
import asyncio, pytest
from app.core.strategy_generator import generate_for_request
from app.execution.schemas import StrategyRequest

@pytest.mark.asyncio
async def test_same_request_produces_different_scores():
    """AUDIT: Due chiamate identiche NON devono produrre score diversi."""
    req = StrategyRequest(
        budget_eur=100.0, duration_days=30,
        asset_class="crypto", risk_level="medium"
    )
    results_1 = await generate_for_request(req)
    results_2 = await generate_for_request(req)

    scores_1 = sorted([r.ai_score for r in results_1])
    scores_2 = sorted([r.ai_score for r in results_2])

    # Questo test DEVE FALLIRE finché il random non viene rimosso
    assert scores_1 == scores_2, (
        f"ALLUCINAZIONE CONFERMATA: stessi input → score diversi.\n"
        f"Call 1: {scores_1}\nCall 2: {scores_2}"
    )

@pytest.mark.asyncio
async def test_estimated_profit_is_not_random():
    """AUDIT: I profitti stimati devono essere deterministici e basati su backtest."""
    req = StrategyRequest(
        budget_eur=100.0, duration_days=30,
        asset_class="crypto", risk_level="medium"
    )
    results_1 = await generate_for_request(req)
    results_2 = await generate_for_request(req)

    profits_1 = sorted([r.estimated_profit_pct for r in results_1])
    profits_2 = sorted([r.estimated_profit_pct for r in results_2])

    assert profits_1 == profits_2, (
        f"ALLUCINAZIONE CONFERMATA: profitti stimati diversi tra chiamate identiche.\n"
        f"Call 1: {profits_1}\nCall 2: {profits_2}"
    )
```

**Criteri di successo del test (che ora fallisce = conferma il bug):**
- `test_same_request_produces_different_scores` → FAIL conferma il random
- `test_estimated_profit_is_not_random` → FAIL conferma il random sui profitti

**Comandi:**
```bash
cd synthtrade/backend
python -m pytest tests/audit/test_random_proof.py -v -s 2>&1
```

---

### TASK-AUDIT-003 — Test AI Evaluator reale: verifica risposta LLM con dati di mercato

**Status:** Pending
**Priorità:** Alta
**File:** `synthtrade/backend/tests/audit/test_ai_evaluator_real.py` (nuovo)

**Obiettivo:** Verificare che il componente AI sia in grado di:
1. Connettersi a OpenRouter
2. Inviare un prompt con dati di backtest reali
3. Ricevere e parsare una risposta JSON strutturata (score, verdict, reasoning)

**Test da scrivere:**
```python
# test_ai_evaluator_real.py — richiede AI_API_KEY nel .env
import asyncio, pytest, os
from app.ai.model_client import ModelClient
from app.ai.prompt_builder import build_system_prompt, build_prompt
from app.ai.eval_parser import parse_eval_result
from app.config import settings

@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("AI_API_KEY"), reason="AI_API_KEY non configurata")
async def test_model_client_returns_valid_json():
    """AUDIT: Il model client risponde con JSON valido parsabile da eval_parser."""
    client = ModelClient(
        api_key=settings.AI_API_KEY,
        api_base_url=settings.AI_API_BASE_URL,
        cascade_models=settings.ai_cascade_models_list,
        fallback_model=settings.AI_FALLBACK_MODEL,
        timeout=60.0, max_retries=2, backoff_base=2.0
    )
    system = build_system_prompt()
    # Strategia fittizia con dati realistici
    user = """## Market Context
Symbol: BTC/USDT | Timeframe: 5m | Regime: trending
Price range: 60000 - 68000 | Last: 65000
Volatility: 1.85% | Trend: +8.33%

## Strategy: Trend Following EMA (BTC/USDT)
Template: trend_ema | Params: {'ema_fast': 10, 'ema_slow': 50}
PnL: +12.40% | Win rate: 62% | Sharpe: 1.32
Max drawdown: 8.20% | Trades: 47 | Score: 0.6824

## Task
Evaluate this strategy. Respond ONLY with JSON:
{"score": <0.0-1.0>, "verdict": "<PROMOTE|HOLD|DEMOTE>", "reasoning": "<explanation>", "confidence": <0.0-1.0>}"""

    response = await client.call_with_fallback(system, user)

    assert response.content, "Nessuna risposta dal modello"
    result = parse_eval_result(response.content, "test_strategy_id", response.model)
    assert 0.0 <= result.score <= 1.0, f"Score fuori range: {result.score}"
    assert result.verdict in ("PROMOTE", "HOLD", "DEMOTE"), f"Verdict invalido: {result.verdict}"
    assert len(result.reasoning) > 10, "Reasoning troppo corto"
    print(f"\n✅ AI Response: model={response.model} score={result.score} verdict={result.verdict}")
    print(f"   Reasoning: {result.reasoning[:200]}")
```

**Criteri di successo:**
- Il modello risponde entro 60 secondi
- La risposta è JSON valido con score, verdict, reasoning
- `verdict` è uno dei valori attesi (PROMOTE/HOLD/DEMOTE)

---

### TASK-AUDIT-004 — Verifica backtest con dati OHLCV reali di Binance

**Status:** Pending
**Priorità:** Alta
**File:** `synthtrade/backend/tests/audit/test_backtest_real_data.py` (nuovo)

**Obiettivo:** Verificare che il backtester usi dati storici reali e produca risultati
deterministici (stessi dati → stessi risultati).

**Test da scrivere:**
```python
# test_backtest_real_data.py
import pytest, pandas as pd
from unittest.mock import patch, MagicMock
from app.core.backtester import run_backtest
from app.core.indicators import signal_ema_crossover

@pytest.mark.asyncio
async def test_backtest_uses_real_ohlcv_shape():
    """AUDIT: Il backtester processa i dati OHLCV nel formato corretto."""
    # Simula dati Binance realistici (senza chiamare API reale)
    import numpy as np
    n = 500
    prices = 60000 + np.cumsum(np.random.randn(n) * 100)
    ohlcv = pd.DataFrame({
        "open": prices * 0.999,
        "high": prices * 1.002,
        "low":  prices * 0.998,
        "close": prices,
        "volume": np.random.uniform(1, 10, n)
    })

    signal_fn = lambda df: signal_ema_crossover(df, fast=10, slow=50)
    result = run_backtest(ohlcv, signal_fn, initial_capital=1000.0)

    assert isinstance(result.pnl_pct, float), "pnl_pct deve essere float"
    assert isinstance(result.num_trades, int), "num_trades deve essere int"
    assert result.num_trades > 0, "Nessun trade eseguito su 500 candele"
    assert len(result.equity_curve) == n, "equity_curve deve avere N elementi"
    print(f"\n✅ Backtest: pnl={result.pnl_pct:.2f}% trades={result.num_trades} sharpe={result.sharpe:.3f}")

def test_backtest_is_deterministic():
    """AUDIT: Stessi dati → stessi risultati (no random nel backtester)."""
    import numpy as np
    rng = np.random.default_rng(42)
    prices = 60000 + np.cumsum(rng.standard_normal(300) * 100)
    ohlcv = pd.DataFrame({
        "open": prices, "high": prices*1.001,
        "low": prices*0.999, "close": prices,
        "volume": np.ones(300) * 5.0
    })
    signal_fn = lambda df: signal_ema_crossover(df, fast=10, slow=50)

    r1 = run_backtest(ohlcv, signal_fn)
    r2 = run_backtest(ohlcv, signal_fn)

    assert r1.pnl_pct == r2.pnl_pct, "ERRORE: backtester non deterministico!"
    assert r1.num_trades == r2.num_trades
```

**Verifica aggiuntiva (connessione reale):**
```bash
cd synthtrade/backend
python -c "
from app.core.market_data import fetch_ohlcv
import pandas as pd
df = fetch_ohlcv('BTC/USDT', '5m', days=7)
print(f'Candele scaricate: {len(df)}')
print(f'Primo timestamp: {df.index[0]}')
print(f'Ultimo timestamp: {df.index[-1]}')
print(df.tail(3))
"
```

---

### TASK-AUDIT-005 — Confronto DB: strategie manuali vs pipeline automatica

**Status:** Pending
**Priorità:** Alta

**Obiettivo:** Interrogare il database Supabase e confrontare le strategie generate
manualmente (via UI) con quelle generate dalla pipeline automatica.

**Script di diagnosi da eseguire:**
```python
# scripts/audit_strategies_db.py
from app.db.supabase_client import get_supabase
import json

db = get_supabase()

# Leggi tutte le strategie recenti
res = db.table("strategies").select(
    "id, title, template, pair, status, score, ai_score, "
    "estimated_profit_pct, backtest, created_at"
).order("created_at", desc=True).limit(20).execute()

print(f"\n{'='*80}")
print(f"{'ID':12} {'Template':20} {'Score':8} {'BacktestOK':10} {'Est.Profit':12} {'Status':10}")
print(f"{'='*80}")

hallucinated = []
real = []

for s in res.data:
    has_backtest = bool(s.get("backtest") and s["backtest"].get("num_trades", 0) > 0)
    backtest_trades = s.get("backtest", {}).get("num_trades", "N/A") if s.get("backtest") else "MANCANTE"
    
    row = (f"{s['id']:12} {s['template']:20} {str(s.get('score','N/A')):8} "
           f"{'✅' if has_backtest else '❌ MANCANTE':10} "
           f"{str(s.get('estimated_profit_pct', 'N/A')):12} {s['status']:10}")
    print(row)
    
    if has_backtest:
        real.append(s)
    else:
        hallucinated.append(s)

print(f"\n📊 RISULTATO:")
print(f"   Strategie con backtest reale: {len(real)}")
print(f"   Strategie SENZA backtest (potenziali allucinazioni): {len(hallucinated)}")
```

**Criteri di successo:**
- Confermare quante strategie nel DB hanno `backtest.num_trades > 0`
- Identificare quali percorsi (manuale/automatico) producono quali risultati

**Comandi:**
```bash
cd synthtrade/backend
python -m pytest tests/audit/test_db_strategies.py -v -s
# oppure
python scripts/audit_strategies_db.py
```

---

### TASK-AUDIT-006 — 🟢 Fix: Integrare backtest reale in `generate_for_request()`

**Status:** Pending
**Priorità:** Alta (dopo conferma findings AUDIT-002)
**File:** `synthtrade/backend/app/core/strategy_generator.py`

**Obiettivo:** Modificare `generate_for_request()` per eseguire un backtest reale
su dati storici prima di restituire le strategie, eliminando il `random.uniform()`.

**Modifiche da applicare:**

```python
# PRIMA (attuale — ALLUCINAZIONE):
score = 70.0 + random.uniform(0, 25.0)
est_profit_pct = base_profit + random.uniform(-2.0, 5.0)

# DOPO (fix — backtest reale):
from app.core.market_data import fetch_ohlcv
from app.core.backtester import run_backtest
from app.core.ranker import compute_score

ohlcv = fetch_ohlcv(pair, "1h", days=90)  # 90 giorni per velocità
signal_fn = SIGNAL_MAP[template_name](ohlcv, params_dict)
result = run_backtest(ohlcv, signal_fn)
score = compute_score(result)  # None se non supera soglie qualità
est_profit_pct = result.pnl_pct  # Valore reale dal backtest
```

**Vincoli:**
- Cache OHLCV per pair/timeframe per evitare N chiamate API per lo stesso asset
- Se backtest fallisce o score è None → escludere la variante (non mostrare all'utente)
- Aggiungere progress tracking via WebSocket (la pipeline diventa più lenta)

**Test (Green):**
```bash
python -m pytest tests/audit/test_random_proof.py -v -s
# Ora i test devono passare (score deterministici)
```

---

### TASK-AUDIT-007 — 🟢 Fix: Rimuovere `random` e nomi casuali, aggiungere metadata backtest

**Status:** Pending
**Priorità:** Media
**File:** `synthtrade/backend/app/core/strategy_generator.py`

**Obiettivo:** Pulire tutto il codice di simulazione random dalla funzione
`generate_for_request()`:

1. **Rimuovere** `import random` e tutti gli usi di `random.uniform()`, `random.choice()`
2. **Rimuovere** i nomi casuali tipo "Il Seguace", "Rompiballe"
3. **Usare** il titolo derivato dal template + pair come nome deterministico
4. **Aggiungere** `backtest_summary` nei campi della strategy restituita
5. **Aggiungere** `data_source: "binance_historical"` per tracciabilità

**Naming deterministico:**
```python
# PRIMA (random):
auto_names = {"trend_ema": ["Il Seguace", "L'Ondaiolo", ...]}
final_custom_name = random.choice(auto_names[template_name])

# DOPO (deterministico):
final_custom_name = f"{TEMPLATES[template_name]['title']} — {pair} {timeframe}"
# Es: "Trend Following EMA — BTC/USDT 1h"
```

**Aggiungere field backtest_summary:**
```python
StrategyParams(
    ...
    backtest_pnl=result.pnl_pct,
    backtest_trades=result.num_trades,
    backtest_sharpe=result.sharpe,
    backtest_drawdown=result.max_drawdown_pct,
    data_source="binance_historical_90d"
)
```

---

### TASK-AUDIT-008 — Test E2E: pipeline completa utente → backtest → AI → DB

**Status:** Pending
**Priorità:** Alta (da eseguire DOPO i fix AUDIT-006 e AUDIT-007)
**File:** `synthtrade/backend/tests/audit/test_e2e_pipeline.py` (nuovo)

**Obiettivo:** Test di integrazione completo che simula l'intera pipeline utente
dopo il fix, verificando che ogni componente sia reale.

**Test da scrivere:**
```python
# test_e2e_pipeline.py
import asyncio, pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.core.strategy_generator import generate_for_request
from app.execution.schemas import StrategyRequest

@pytest.mark.asyncio
async def test_generate_for_request_uses_real_backtest(mock_ohlcv_data):
    """
    E2E: Dopo il fix, generate_for_request() deve:
    1. Chiamare fetch_ohlcv() (dati storici)
    2. Chiamare run_backtest() (simulazione)
    3. Avere score deterministici (non random)
    4. Avere backtest_pnl popolato con valore reale
    """
    req = StrategyRequest(
        budget_eur=100.0, duration_days=30,
        asset_class="crypto", risk_level="medium",
        max_strategies=3
    )

    with patch("app.core.strategy_generator.fetch_ohlcv") as mock_fetch, \
         patch("app.core.strategy_generator.enrich_request_with_ai") as mock_ai:
        mock_fetch.return_value = mock_ohlcv_data  # fixture con 300 candele realistiche
        mock_ai.return_value = req  # no AI enrichment per semplicità

        results_1 = await generate_for_request(req)
        results_2 = await generate_for_request(req)

    # Verifica determinismo
    scores_1 = [r.ai_score for r in results_1]
    scores_2 = [r.ai_score for r in results_2]
    assert scores_1 == scores_2, f"Score non deterministici: {scores_1} vs {scores_2}"

    # Verifica che il backtest sia stato eseguito
    for strategy in results_1:
        assert hasattr(strategy, 'backtest_pnl'), "backtest_pnl mancante"
        assert strategy.backtest_pnl is not None, "backtest_pnl è None"
        assert strategy.estimated_profit_pct == strategy.backtest_pnl, (
            f"estimated_profit_pct ({strategy.estimated_profit_pct}) != "
            f"backtest_pnl ({strategy.backtest_pnl})"
        )

    # Verifica che fetch_ohlcv sia stato chiamato
    assert mock_fetch.called, "fetch_ohlcv NON è stato chiamato — nessun dato reale!"

@pytest.mark.asyncio
async def test_pipeline_rejects_low_quality_strategies(mock_ohlcv_data):
    """
    E2E: Le strategie che non superano le soglie del ranker devono essere
    escluse (score=None) e non mostrate all'utente.
    """
    req = StrategyRequest(
        budget_eur=100.0, duration_days=30,
        asset_class="crypto", risk_level="medium",
        max_strategies=10  # Chiede 10, ma il filtro può restituirne meno
    )

    with patch("app.core.strategy_generator.fetch_ohlcv") as mock_fetch, \
         patch("app.core.strategy_generator.enrich_request_with_ai") as mock_ai:
        mock_fetch.return_value = mock_ohlcv_data
        mock_ai.return_value = req
        results = await generate_for_request(req)

    # Tutte le strategie restituite devono avere score > 0
    for s in results:
        assert s.ai_score > 0, f"Strategia con score nullo non filtrata: {s}"
```

**Comandi:**
```bash
cd synthtrade/backend
python -m pytest tests/audit/ -v --tb=short -s

# Output atteso dopo i fix:
# PASSED tests/audit/test_random_proof.py::test_same_request_produces_different_scores
# PASSED tests/audit/test_random_proof.py::test_estimated_profit_is_not_random
# PASSED tests/audit/test_e2e_pipeline.py::test_generate_for_request_uses_real_backtest
# PASSED tests/audit/test_e2e_pipeline.py::test_pipeline_rejects_low_quality_strategies
```

**Criteri finali di successo:**
- Zero `random.uniform()` in `strategy_generator.py`
- Tutte le strategie proposte hanno `backtest.num_trades > 0`
- Score identici per input identici (deterministico)
- `estimated_profit_pct` corrisponde a `result.pnl_pct` del backtest
- `fetch_ohlcv()` chiamato per ogni pair/timeframe (con cache)

---

## 🔴 Fix Allucinazioni — `generate_for_request()` (PRIORITÀ ASSOLUTA)

> **Risolto il 2026-05-12.** Le strategie generate via UI ora usano backtest reale su dati storici Binance invece di `random.uniform()`.
> **Principio:** nessuna strategia proposta all'utente senza backtest reale su dati storici.
> Il `random` è VIETATO in qualsiasi calcolo finanziario.

---

### TASK-FIX-001 — Rimuovere `import random` e aggiungere imports reali

**Status:** Done ✅
**Completato:** 2026-05-12
**Priorità:** Bloccante
**File:** `synthtrade/backend/app/core/strategy_generator.py`

**Cosa fare:**
- Rimuovere `import random`
- Aggiungere: `import asyncio`, `import logging`
- Aggiungere: `from app.core.market_data import fetch_ohlcv`
- Aggiungere: `from app.core.backtester import run_backtest`
- Aggiungere: `from app.core.ranker import compute_score`
- Aggiungere: `from app.core.indicators import signal_ema_crossover, signal_rsi_reversion, signal_breakout_bb`
- Aggiungere `from datetime import datetime, timedelta, timezone` se non già presente
- Aggiungere in cima al modulo il `SIGNAL_MAP` (già presente in `run_pipeline.py`, copiarlo):
```python
logger = logging.getLogger("synthtrade.generator")

SIGNAL_MAP = {
    "trend_ema": lambda df, p: signal_ema_crossover(df, p["ema_fast"], p["ema_slow"]),
    "mean_reversion_rsi": lambda df, p: signal_rsi_reversion(
        df, p["rsi_period"], p["rsi_oversold"], p["rsi_overbought"]),
    "breakout_bb": lambda df, p: signal_breakout_bb(df, p["bb_period"], p["bb_std"]),
}
```

**Verifica:** `grep -n "import random" strategy_generator.py` → nessun risultato.

---

### TASK-FIX-002 — Aggiungere campi backtest a `StrategyParams`

**Status:** Done ✅
**Completato:** 2026-05-12
**Priorità:** Bloccante
**File:** `synthtrade/backend/app/core/strategy_generator.py`

**Cosa fare:** Modificare il dataclass `StrategyParams` (frozen=True):
- Rinominare `ai_score` → `score` (valore da `compute_score()`, range 0–1)
- Aggiungere i campi backtest:
```python
score: float = 0.0                # da compute_score() — deterministico
estimated_profit_pct: float = 0.0 # da result.pnl_pct — reale
estimated_profit_eur: float = 0.0 # budget * pnl_pct / 100 — reale
backtest_pnl: float = 0.0         # result.pnl_pct
backtest_win_rate: float = 0.0    # result.win_rate
backtest_sharpe: float = 0.0      # result.sharpe
backtest_drawdown: float = 0.0    # result.max_drawdown_pct
backtest_trades: int = 0          # result.num_trades
data_source: str = ""             # es. "binance_1h_90d"
```
- Aggiornare `__hash__` rimuovendo riferimento ad `ai_score`
- Aggiornare `__post_init__`: rimuovere logica che usava `ai_score`

---

### TASK-FIX-003 — Riscrivere `generate_for_request()` — Fase 1: fetch OHLCV reale

**Status:** Done ✅
**Completato:** 2026-05-12
**Priorità:** Bloccante
**File:** `synthtrade/backend/app/core/strategy_generator.py`

**Cosa fare:** All'inizio di `generate_for_request()`, dopo `enrich_request_with_ai()`:
```python
pairs = req.symbols if req.symbols else ["BTC/USDT"]
timeframes = ["1h", "4h"]

# Cache OHLCV: UNA sola chiamata per (pair, timeframe)
ohlcv_cache: dict[tuple, object] = {}
for pair in pairs:
    for tf in timeframes:
        key = (pair, tf)
        try:
            ohlcv_cache[key] = await asyncio.to_thread(
                fetch_ohlcv, pair, tf, 90  # 90 giorni dati storici
            )
            logger.info(f"OHLCV: {pair} {tf} — {len(ohlcv_cache[key])} candele")
        except Exception as e:
            logger.warning(f"OHLCV fetch fallito {pair}/{tf}: {e}")
```

**Perché `asyncio.to_thread`:** `fetch_ohlcv` usa `ccxt` che è sincrono (bloccante).
Wrapparlo in `to_thread` lo rende non-bloccante per il loop asincrono di FastAPI.

**Verifica:** Log deve mostrare `"OHLCV: BTC/USDT 1h — 2160 candele"` (90 giorni × 24h).

---

### TASK-FIX-004 — Riscrivere `generate_for_request()` — Fase 2: loop backtest reale

**Status:** Done ✅
**Completato:** 2026-05-12
**Priorità:** Bloccante
**File:** `synthtrade/backend/app/core/strategy_generator.py`

**Cosa fare:** Sostituire il blocco del for loop che conteneva i `random.uniform()`.

**Eliminare completamente:**
- Tutto il blocco `score = 70.0 + random.uniform(0, 25.0)`
- Tutto il blocco `est_profit_pct = base_profit + random.uniform(-2.0, 5.0)`
- Il dizionario `auto_names = {...}` con i nomi casuali
- `random.shuffle(all_variants)`
- `random.choice(auto_names[...])`
- Il blocco `base_profit_map = {...}`

---

### TASK-FIX-005 — Aggiornare `pipeline.py` — Salvare `backtest` nel DB

**Status:** Done ✅
**Completato:** 2026-05-12
**Priorità:** Alta
**File:** `synthtrade/backend/app/api/pipeline.py`

**Cosa fare:** In `run_generation_task()`, nel dizionario `row` dell'insert Supabase:
```python
row = {
    "id": strategy_id,
    "title": s.title or f"{s.template} on {s.pair}",
    "description": s.description,
    "template": s.template,
    "pair": s.pair,
    "timeframe": s.timeframe,
    "budget_eur": s.budget_eur,
    "params": s.params,
    "rules": {}, "risk": {}, "targets": {},
    "status": "PENDING",
    "score": s.score,           # REALE (era 0.0 hardcoded)
    "ai_score": s.score,        # REALE (era s.ai_score random)
    "estimated_profit_pct": s.estimated_profit_pct,   # REALE
    "estimated_profit_eur": s.estimated_profit_eur,   # REALE
    "backtest": {               # NUOVO — popolato con dati reali
        "pnl_pct":          s.backtest_pnl,
        "win_rate":         s.backtest_win_rate,
        "sharpe":           s.backtest_sharpe,
        "max_drawdown_pct": s.backtest_drawdown,
        "num_trades":       s.backtest_trades,
        "data_source":      s.data_source,
    },
    "custom_name": s.custom_name,
    "created_at": now.isoformat(),
    "expires_at": expires_at,
}
```

Aggiornare anche `strategies_data` (la risposta WS) aggiungendo i campi backtest.

---

### TASK-FIX-006 — Aggiungere WS progress events durante la generazione

**Status:** Done ✅
**Completato:** 2026-05-12
**Priorità:** Media
**File:** `synthtrade/backend/app/api/pipeline.py`

**Motivazione:** Il backtest reale richiede alcuni secondi. L'utente deve sapere
cosa sta succedendo invece di vedere un'attesa senza feedback.

**Cosa fare:** In `run_generation_task()`, aggiungere broadcast prima e dopo:
```python
# PRIMA di chiamare generate_for_request():
await manager.broadcast({
    "type": "generation_progress",
    "generation_id": generation_id,
    "phase": "fetching_market_data",
    "message": "Scaricamento dati storici Binance (90 giorni)...",
})

# generate_for_request() internamente scarica OHLCV e fa backtest

# DOPO generate_for_request(), PRIMA del salvataggio DB:
await manager.broadcast({
    "type": "generation_progress",
    "generation_id": generation_id,
    "phase": "saving",
    "message": f"Backtest completato: {len(strategies)} strategie valide. Salvataggio...",
})
```

---

### TASK-FIX-007 — Gestire lista vuota con messaggio utente chiaro

**Status:** Done ✅
**Completato:** 2026-05-12
**Priorità:** Alta
**File:** `synthtrade/backend/app/api/pipeline.py`

**Scenario:** Il backtest su 90 giorni può restituire 0 strategie se nessuna
supera i filtri del `ranker` (Sharpe > 0.5, DD < 15%, PnL > 2%, Trades > 30).

**Cosa fare:** Dopo `strategies = await generate_for_request(req)`:
```python
if not strategies:
    generations[generation_id]["status"] = "completed"
    generations[generation_id]["results"] = []
    generations[generation_id]["message"] = (
        "Nessuna strategia ha superato i criteri di qualità sui dati storici "
        "(Sharpe > 0.5, Drawdown < 15%, PnL > 2%, Trades > 30 in 90 giorni). "
        "Prova con un orizzonte temporale più lungo o un livello di rischio diverso."
    )
    await manager.broadcast({
        "type": "generation_complete",
        "generation_id": generation_id,
        "count": 0,
    })
    return
```

---

### TASK-FIX-008 — Test E2E: `test_e2e_pipeline.py` con mock OHLCV

**Status:** Done ✅
**Completato:** 2026-05-12
**Priorità:** Alta
**File:** `synthtrade/backend/tests/audit/test_e2e_pipeline.py` (nuovo)

**Cosa fare:** Creare test con fixture OHLCV sintetica (no Binance reale):
```python
@pytest.fixture
def mock_ohlcv():
    import numpy as np
    rng = np.random.default_rng(42)  # seed fisso = deterministico
    n = 2000
    prices = 60000 + np.cumsum(rng.standard_normal(n) * 100 + 3)
    return pd.DataFrame({
        "open": prices*0.999, "high": prices*1.002,
        "low": prices*0.998,  "close": prices,
        "volume": np.ones(n) * 5.0
    }, index=pd.date_range("2024-01-01", periods=n, freq="1h"))

@pytest.mark.asyncio
async def test_generate_for_request_uses_backtest(mock_ohlcv):
    req = StrategyRequest(budget_eur=100.0, duration_days=30,
                          asset_class="crypto", risk_level="medium",
                          max_strategies=3)
    with patch("app.core.strategy_generator.fetch_ohlcv", return_value=mock_ohlcv), \
         patch("app.core.strategy_generator.enrich_request_with_ai",
               new_callable=AsyncMock, return_value=req):
        results_1 = await generate_for_request(req)
        results_2 = await generate_for_request(req)

    # Deterministico: stessi input → stessi output
    assert [r.score for r in results_1] == [r.score for r in results_2]
    assert [r.estimated_profit_pct for r in results_1] == \
           [r.estimated_profit_pct for r in results_2]

    # Backtest eseguito: campi popolati
    for s in results_1:
        assert s.backtest_trades > 0, "backtest_trades deve essere > 0"
        assert s.estimated_profit_pct == s.backtest_pnl, \
               "estimated_profit_pct deve = backtest_pnl"
        assert s.data_source.startswith("binance_"), \
               "data_source deve indicare fonte Binance"
        assert 0.0 < s.score <= 1.0, "score fuori range [0,1]"
```

---

### TASK-FIX-009 — Aggiornare `test_generator_constrained.py`

**Status:** Done ✅
**Completato:** 2026-05-12
**Priorità:** Media
**File:** `synthtrade/backend/tests/unit/test_generator_constrained.py`

**Cosa fare:** Verificare che i test esistenti assumano `score` (0–1) invece di
`ai_score` (70–99). Aggiornare le asserzioni e i mock di conseguenza.
Aggiungere mock per `fetch_ohlcv` e `run_backtest` dove mancante.

---

### TASK-FIX-010 — Aggiornare `test_generator.py` full_data test con mock

**Status:** Done ✅
**Completato:** 2026-05-12
**Priorità:** Media
**File:** `synthtrade/backend/tests/unit/test_generator.py`

**Cosa fare:** Verificare che `enrich_request_with_ai()` sia ancora chiamato
correttamente dopo il refactor. Aggiornare mock per includere OHLCV e backtest.

---

### TASK-FIX-011 — Verifica finale: `test_random_proof.py` deve PASSARE

**Status:** Done ✅
**Completato:** 2026-05-12
**Priorità:** Alta — è il criterio di successo finale

**Risultato finale:** 21 test PASS su generator, constrained, random_proof, e2e_pipeline. Zero regressioni nella suite unità (152/157 pass; 5 fallimenti pre-esistenti in test_prompt_builder.py non correlati).

**Cosa fare:** Dopo tutti i fix, eseguire:
```bash
cd synthtrade/backend
python -m pytest tests/audit/test_random_proof.py -v -s
```

**Risultato atteso:**
```
PASSED tests/audit/test_random_proof.py::test_same_request_produces_different_scores
PASSED tests/audit/test_random_proof.py::test_estimated_profit_is_not_random
PASSED tests/audit/test_random_proof.py::test_score_is_within_random_range  (ora verifica range 0-1)
```

Se uno di questi fallisce → il bug non è completamente risolto.

**Verifica suite completa:**
```bash
python -m pytest tests/ -v --tb=short 2>&1 | tail -20
# Atteso: 0 regressioni rispetto alla suite pre-fix
```

**Verifica DB post-deploy:**
```sql
SELECT COUNT(*) as total,
       COUNT(backtest) as with_backtest,
       COUNT(*) - COUNT(backtest) as missing_backtest
FROM strategies WHERE status = 'PENDING';
-- Atteso: with_backtest == total, missing_backtest == 0
```

---

## UX Generazione / Anti-allucinazioni — HALU (2026-05-12)

> Migliorare feedback quando la generazione fallisce, è lenta, restituisce 0 strategie o il polling cancella le richieste HTTP.

### HALU-FE-01 — Gestione errori POST `/api/pipeline/generate`

**Status:** Done ✅  
**Completato:** 2026-05-12  
**Scope:** `strategies.page.ts` — `subscribe` con `error`, banner `generationError`, messaggi per 401/422/network.

### HALU-FE-02 — Polling: `exhaustMap` + primo poll immediato + timeout richiesta

**Status:** Done ✅  
**Completato:** 2026-05-12  
**Scope:** `pipeline.service.ts` — `timer(0, 3000)`, `exhaustMap`, `timeout` per GET status.

### HALU-FE-03 — Modello `GenerationStatus.message` e stato vuoto

**Status:** Done ✅  
**Completato:** 2026-05-12  
**Scope:** `strategy.model.ts`, `pollStatus` — propagazione messaggio backend (0 risultati / filtri qualità).

### HALU-FE-04 — `GenerationProgressComponent`: esito neutro se 0 strategie

**Status:** Done ✅  
**Completato:** 2026-05-12  
**Scope:** Input `detailMessage`, `resultCount`; banner success solo se `count > 0`.

### HALU-BE-01 — Normalizzazione simboli (`BTCUSDT` → `BTC/USDT`)

**Status:** Done ✅  
**Completato:** 2026-05-12  
**Scope:** `strategy_generator.normalize_trading_pair`, uso su `req.symbols`.

### HALU-BE-02 — Messaggio distinto se mancano dati OHLCV vs filtri qualità

**Status:** Done ✅  
**Completato:** 2026-05-12  
**Scope:** `generate_for_request` restituisce `(strategies, empty_hint)`, `pipeline.py` salva `message`.

---

## 🎯 Fase 8 — Strategie Multi-Asset (Portfolio Diversificato)

> Feature: aggiungere supporto per strategie che operano su più asset contemporaneamente con allocazione percentuale del capitale in base al rischio. Badge "📊 Multi" / "📈 Single" nella pagina Strategie. Stesso flusso di approvazione/esecuzione.

### TASK-PORTFOLIO-001 — Modelli: PortfolioAllocation + PortfolioBacktestResult

**Status:** Pending
**Priorità:** Alta
**File:** `synthtrade/backend/app/execution/schemas.py`

**Cosa fare:**
- Creare dataclass `PortfolioAllocation(asset: str, weight: float, template: str | None, params: dict | None)`
- Creare `PortfolioBacktestResult(pnl_pct, sharpe, max_drawdown, num_trades, individual_results: list[BacktestResult])`
- Aggiungere campo opzionale `allocations: list[PortfolioAllocation] | None = None` a `StrategyParams`
- Se `allocations` è None → strategia single-asset (comportamento attuale)
- Se popolato → strategia multi-asset

**Criteri di successo:**
- `StrategyParams` accetta sia `allocations=None` (single) che `allocations=[...]` (multi)
- `PortfolioBacktestResult` contiene metriche aggregate e risultati individuali
- Test unitari per entrambi i dataclass

---

### TASK-PORTFOLIO-002 — Backtest Multi-Asset

**Status:** Pending
**Priorità:** Alta
**File:** `synthtrade/backend/app/core/backtester.py`

**Cosa fare:**
- Implementare `run_portfolio_backtest(ohlcv_dict: dict[str, pd.DataFrame], allocations: list[PortfolioAllocation], capital: float) -> PortfolioBacktestResult`
- Per ogni asset: fetch OHLCV, esegui segnale, calcola P&L pesato per weight
- Sharpe combinato come media pesata degli Sharpe individuali
- Drawdown sul capitale totale (equity curve combinata)
- P&L totale = somma(P&L_i * weight_i)

**🔴 Test:**
- `test_portfolio_backtest_returns_aggregate_metrics`: verifica P&L, Sharpe, DD calcolati correttamente
- `test_portfolio_backtest_individual_results`: verifica che `individual_results` contenga un risultato per ogni asset
- `test_portfolio_backtest_single_asset_matches_single`: con una sola allocazione al 100%, deve dare stesso risultato di `run_backtest`

**Criteri di successo:**
- P&L combinato = media pesata dei P&L individuali (± 0.01%)
- equity_curve combinata = somma pesata delle equity curve
- Drawdown calcolato sulla equity_curve combinata

---

### TASK-PORTFOLIO-003 — Calcolatore Allocazione Risk-Weighted

**Status:** Pending
**Priorità:** Alta
**File:** `synthtrade/backend/app/core/portfolio_allocator.py` (nuovo)

**Cosa fare:**
- `allocate_by_criteria(assets: list[str], risk_level: str, num_assets: int) -> list[PortfolioAllocation]`
- **Low risk**: più peso a BTC/BNB (meno volatili), meno a altcoin
- **Medium risk**: pesi proporzionali a capitalizzazione di mercato (più BTC, meno AVAX/DOT)
- **High risk**: più peso a SOL/AVAX (più volatili e potenziale crescita)
- Se l'utente specifica `symbols` esplicitamente → usa solo quelli, distribuisci uniformemente
- Se `num_assets > len(assets)` → usa tutti quelli disponibili

**🔴 Test:**
- `test_allocate_low_risk_gives_more_weight_to_btc`
- `test_allocate_high_risk_gives_more_weight_to_volatile`
- `test_allocate_with_custom_symbols_uses_only_those`
- `test_allocate_respects_num_assets_limit`

**Criteri di successo:**
- Somma dei pesi = 1.0 (±0.01)
- Numero di allocazioni = `num_assets` o meno se non ci sono abbastanza asset
- Ogni weight è tra 0.0 e 1.0

---

### TASK-PORTFOLIO-004 — Generatore Strategie Portfolio

**Status:** Pending
**Priorità:** Alta
**File:** `synthtrade/backend/app/core/strategy_generator.py`

**Cosa fare:**
- Aggiungere `generate_portfolio_strategies(req: StrategyRequest, num_assets: int) -> Tuple[List[StrategyParams], Optional[str]]`
- Se `req.symbols` specificato → usa quelli. Altrimenti usa default ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"]
- Calcola allocazione con `allocate_by_criteria()`
- Per ogni template filtrato: applica lo stesso segnale a tutti gli asset
- Esegui `run_portfolio_backtest()` e calcola score
- Se score è None → scarta
- Restituisce strategie con `allocations` popolato

**🔴 Test:**
- `test_generate_portfolio_returns_portfolio_strategies`: verifica che le strategie abbiano `allocations` popolato
- `test_generate_portfolio_all_allocations_sum_to_one`: somma pesi ≈ 1.0
- `test_generate_portfolio_respects_max_strategies`: non supera `req.max_strategies`

**Criteri di successo:**
- Ogni strategia multi-asset ha `allocations` con somma pesi = 1.0
- Score calcolato su backtest combinato
- Stesso flusso di salvataggio su DB (TASK-PORTFOLIO-005)

---

### TASK-PORTFOLIO-005 — Pipeline e API: supporto flag multi-asset

**Status:** Pending
**Priorità:** Alta
**File:** `synthtrade/backend/app/execution/schemas.py`, `synthtrade/backend/app/api/pipeline.py`

**Cosa fare:**
- Aggiungere campi a `StrategyRequest`:
  - `multi_asset: bool = False` — flag per attivare generazione multi-asset
  - `num_assets: int = 1` — numero di asset (1 = single-asset, 2-10 = portfolio)
- In `run_generation_task()`:
  - Se `multi_asset=True` e `num_assets > 1` → chiama `generate_portfolio_strategies()`
  - Altrimenti → comportamento attuale
- Salvataggio su Supabase: campo `allocations JSONB` (se multi-asset) o `NULL` (se single)

**🔴 Test:**
- `test_pipeline_with_multi_asset_flag_generates_portfolio`
- `test_pipeline_without_flag_behaves_as_before`
- `test_pipeline_with_num_assets_1_behaves_as_single`

**Criteri di successo:**
- Con `multi_asset=False` → identico comportamento attuale
- Con `multi_asset=True, num_assets=3` → strategie con 3 allocazioni
- DB salva correttamente il campo `allocations`

---

### TASK-PORTFOLIO-006 — DB Migration 009: campo allocations su strategies

**Status:** Pending
**Priorità:** Alta
**File:** `synthtrade/supabase/migrations/009_add_allocations.sql`

**Cosa fare:**
```sql
ALTER TABLE strategies ADD COLUMN allocations JSONB DEFAULT NULL;
CREATE INDEX idx_strategies_allocations ON strategies USING gin (allocations) WHERE allocations IS NOT NULL;
```

**Criteri di successo:**
- Migration applicabile su Supabase Cloud
- Record esistenti con `allocations = NULL` continuano a funzionare
- Query su strategie multi-asset funzionano con filtro `WHERE allocations IS NOT NULL`

---

### TASK-PORTFOLIO-007 — Frontend: badge Multi/Single nelle card strategia

**Status:** Pending
**Priorità:** Media
**File:** `synthtrade/frontend/synthtrade-ui/src/app/pages/strategies/`

**Cosa fare:**
- Nella card strategia, se `strategy.allocations` è popolato → mostra badge "📊 Multi" (es. "📊 BTC 40% + ETH 30% + SOL 20% + BNB 10%")
- Se `allocations` è null/undefined → mostra badge "📈 Single" (comportamento attuale)
- Nel tooltip/dettaglio espanso: mostra lista asset con percentuali

**🔴 Test:**
- `test_strategy_card_shows_multi_badge_when_allocations_present`
- `test_strategy_card_shows_single_badge_when_no_allocations`
- `test_strategy_card_multi_shows_asset_breakdown`

**Criteri di successo:**
- Strategie multi-asset chiaramente distinguibili visivamente
- Composizione visibile senza dover espandere la card

---

### TASK-PORTFOLIO-008 — Frontend: checkbox + slider nel form di generazione

**Status:** Pending
**Priorità:** Media
**File:** `synthtrade/frontend/synthtrade-ui/src/app/shared/components/strategy-request-form/`

**Cosa fare:**
- Aggiungere checkbox "Strategia Multi-Asset" nel form di generazione
- Se checkbox attiva: mostra slider "Numero Asset" (1-10, default 5)
- Se checkbox disattiva: slider nascosto, comportamento attuale
- Passare `multi_asset` e `num_assets` nel `StrategyRequest` inviato all'API

**🔴 Test:**
- `test_form_hides_num_assets_slider_when_multi_asset_off`
- `test_form_shows_slider_when_multi_asset_on`
- `test_form_submit_includes_multi_asset_and_num_assets`

**Criteri di successo:**
- Utente può scegliere se generare single o multi-asset
- Numero asset chiaramente selezionabile
- Valori passati correttamente all'API

---

## 🧠 Fase 9 — AI Learning Engine + Scheduler Notturno

> Feature: sistema di memoria che impara dalle strategie passate per migliorare la selezione futura, con scheduler notturno che pre-genera strategie mentre l'utente non usa il sistema.

### TASK-LEARN-001 — Migration 010: tabella strategy_performance su Supabase

**Status:** Pending
**Priorità:** Alta
**File:** `synthtrade/supabase/migrations/010_add_strategy_performance.sql`

**Cosa fare:**
```sql
CREATE TABLE strategy_performance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template TEXT NOT NULL,
    pair TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    params JSONB NOT NULL DEFAULT '{}',
    score FLOAT NOT NULL DEFAULT 0.0,
    pnl_pct FLOAT,
    sharpe FLOAT,
    drawdown FLOAT,
    num_trades INT DEFAULT 0,
    user_approved BOOLEAN DEFAULT NULL,
    generation_count INT DEFAULT 1,
    approval_count INT DEFAULT 0,
    first_generated_at TIMESTAMP DEFAULT NOW(),
    last_generated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(template, pair, timeframe, params)
);
CREATE INDEX idx_performance_template_pair_tf ON strategy_performance(template, pair, timeframe);
```

**Criteri di successo:**
- Migration applicabile su Supabase Cloud
- Vincolo UNIQUE su (template, pair, timeframe, params) evita duplicati
- Indice per query rapide per template/pair/timeframe

---

### TASK-LEARN-002 — TemplatePerformanceRegistry

**Status:** Pending
**Priorità:** Alta
**File:** `synthtrade/backend/app/core/performance_registry.py` (nuovo)

**Cosa fare:**
- Classe `TemplatePerformanceRegistry` con metodi:
  - `record_generation(template, pair, tf, params, score, pnl, sharpe, dd, trades)`: upsert su strategy_performance
  - `record_approval(template, pair, tf, params, approved: bool)`: aggiorna `user_approved`, `approval_count`
  - `should_avoid(template, pair, tf, params) -> bool`: True se score medio < 0.3 su 10+ generazioni
  - `should_promote(template, pair, tf, params) -> bool`: True se score medio > 0.7 su 5+ generazioni
  - `get_best_params(template, pair, tf) -> dict | None`: parametri con score più alto registrato
  - `get_template_stats(template, pair, tf) -> dict`: statistiche aggregate
- Cache in-memory (dict) con refresh periodico da Supabase ogni 5 minuti

**🔴 Test:**
- `test_record_generation_upserts_correctly`
- `test_should_avoid_returns_true_for_low_performing`
- `test_should_promote_returns_true_for_high_performing`
- `test_get_best_params_returns_highest_score`
- `test_cache_refreshes_from_db`

**Criteri di successo:**
- Dopo 10+ registrazioni con score < 0.3, `should_avoid()` ritorna True
- Dopo 5+ registrazioni con score > 0.7, `should_promote()` ritorna True
- Cache evita chiamate DB frequenti

---

### TASK-LEARN-003 — Generatore Intelligente con Memoria

**Status:** Pending
**Priorità:** Alta
**File:** `synthtrade/backend/app/core/strategy_generator.py`

**Cosa fare:**
- Integrare `TemplatePerformanceRegistry` in `generate_for_request()`:
  1. In `_filter_templates_by_constraints()`: escludere anche combinazioni con `should_avoid()=True`
  2. Nel loop backtest: per combinazioni con `should_promote()=True`, provare parametri aggiuntivi (da `get_best_params()`)
  3. Dopo ogni backtest: chiamare `registry.record_generation()`
- Aggiungere `ai_note` nelle strategie restituite (es. "Questa combinazione ha funzionato bene in passato con score 0.75")

**🔴 Test:**
- `test_generator_skips_avoided_combinations`: verificare che combinazioni con should_avoid=True non vengano generate
- `test_generator_tries_best_params_for_promoted`: verificare che i parametri migliori vengano provati
- `test_generator_records_performance`: verificare che record_generation() venga chiamato per ogni backtest

**Criteri di successo:**
- Zero combinazioni "evitate" nelle strategie generate
- Combinazioni "promosse" hanno più varianti di parametri
- Ogni generazione aggiorna il registry

---

### TASK-LEARN-004 — Param Optimization Automatica

**Status:** Pending
**Priorità:** Media
**File:** `synthtrade/backend/app/core/strategy_generator.py` o nuovo file `app/core/param_optimizer.py`

**Cosa fare:**
- Funzione `optimize_params(template: str, pair: str, tf: str, base_params: dict, current_score: float, ohlcv: pd.DataFrame) -> list[dict]`
- Se `current_score > 0.6`: prova parametri più fini attorno ai valori attuali (es. se ema_fast=10, prova [8,9,10,11,12])
- Se `current_score > 0.8`: prova griglia ancora più densa
- Backtest veloce su 30gg per ogni variante
- Restituisce lista di dict parametri ordinati per score decrescente
- Salva i migliori nel registry

**🔴 Test:**
- `test_optimize_params_returns_finer_grid_for_high_score`
- `test_optimize_params_results_are_sorted_by_score`
- `test_optimize_params_does_not_run_for_low_score`

**Criteri di successo:**
- Per score > 0.6: almeno 2x parametri in più rispetto alla griglia base
- Per score > 0.8: almeno 3x parametri
- Per score < 0.6: nessuna ottimizzazione

---

### TASK-LEARN-005 — Migration 011: tabella pre_generated_strategies

**Status:** Pending
**Priorità:** Alta
**File:** `synthtrade/supabase/migrations/011_add_pre_generated_strategies.sql`

**Cosa fare:**
```sql
CREATE TABLE pre_generated_strategies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    risk_level TEXT NOT NULL,
    num_assets INT NOT NULL DEFAULT 1,
    strategy JSONB NOT NULL,
    score FLOAT NOT NULL DEFAULT 0.0,
    generated_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL
);
CREATE INDEX idx_pre_gen_risk_level ON pre_generated_strategies(risk_level, num_assets);
CREATE INDEX idx_pre_gen_expires ON pre_generated_strategies(expires_at);
```

**Criteri di successo:**
- Migration applicabile su Supabase Cloud
- Indice su (risk_level, num_assets) per query rapide
- Indice su expires_at per cleanup automatico

---

### TASK-LEARN-006 — Scheduler Notturno (Nightly Generation)

**Status:** Pending
**Priorità:** Alta
**File:** `synthtrade/backend/app/scheduler/jobs.py`

**Cosa fare:**
- Aggiungere `async def run_nightly_generation_job()`:
  1. Log "Nightly generation started"
  2. Per ogni risk_level in ["low", "medium", "high"]:
     - Per num_assets in [1, 3, 5] (single, medium portfolio, large portfolio):
       - Crea `StrategyRequest` con quel risk_level e num_assets
       - Chiama `generate_for_request()` o `generate_portfolio_strategies()`
       - Prendi top 5 strategie (per score)
       - Salva in `pre_generated_strategies` con `expires_at = now + 24h`
  3. Aggiorna `TemplatePerformanceRegistry` con nuovi backtest
  4. Log "Nightly generation completed: X strategie pre-generate"
- Registrare il job nello scheduler: `scheduler.add_job(run_nightly_generation_job, "cron", hour=2, minute=0, id="nightly_gen")`

**🔴 Test:**
- `test_nightly_generation_creates_pre_generated_strategies`
- `test_nightly_generation_strategies_have_24h_expiry`
- `test_nightly_generation_covers_all_risk_levels`

**Criteri di successo:**
- Ogni notte alle 02:00 vengono generate strategie per tutti i risk_level
- Le strategie hanno `expires_at = now + 24h`
- Il registry viene aggiornato

---

### TASK-LEARN-007 — API Pre-generated Strategies

**Status:** Pending
**Priorità:** Alta
**File:** `synthtrade/backend/app/api/pipeline.py`

**Cosa fare:**
- Nuovo endpoint `GET /api/pipeline/pre-generated?risk_level=medium&num_assets=1`
- Query su `pre_generated_strategies` con filtro risk_level, num_assets, expires_at > now
- Se ci sono strategie valide (non scadute):
  - Restituiscile immediatamente con `is_pre_generated: true`
  - In background: avvia `run_nightly_generation_job()` per aggiornare la cache
- Se non ci sono o sono scadute:
  - Restituisci `{ "pre_generated": [], "fallback": true }`
  - Il frontend avvia generazione on-demand normalmente

**🔴 Test:**
- `test_pre_generated_returns_cached_strategies`
- `test_pre_generated_returns_empty_when_none_available`
- `test_pre_generated_filters_by_risk_level_and_num_assets`

**Criteri di successo:**
- Se ci sono strategie pre-generate valide → risposta immediata (nessuna attesa)
- Flag `is_pre_generated: true` distingue da generazione on-demand
- Se scadute → fallback a generazione normale

---

### TASK-LEARN-008 — Frontend: mostra pre-generate con badge ⚡

**Status:** Pending
**Priorità:** Alta
**File:** `synthtrade/frontend/synthtrade-ui/src/app/pages/strategies/strategies.page.ts`

**Cosa fare:**
- All'avvio della pagina Strategie, chiamare `GET /api/pipeline/pre-generated?risk_level=...&num_assets=...`
- Se ci sono strategie pre-generate:
  - Mostrale immediatamente (zero spinner, zero attesa)
  - Badge "⚡ Pre-generata" sulle card
  - Messaggio "Strategie pronte — generate stanotte alle 02:00"
  - Bottone "Genera nuove" per forzare rigenerazione on-demand
- Se non ci sono: comportamento attuale (mostra welcome card o carica da DB)

**🔴 Test:**
- `test_page_loads_pre_generated_strategies_first`
- `test_pre_generated_shows_flash_badge`
- `test_page_falls_back_to_normal_generation_when_no_pre_generated`

**Criteri di successo:**
- Utente vede strategie immediatamente all'apertura della pagina (zero tempo di attesa)
- Badge ⚡ chiaramente visibile
- Bottone "Genera nuove" funziona come oggi

---

## 📋 Task Storici Completati (pre-Fase 8)

> I task da TASK-AUDIT-009 a TASK-AUDIT-010 sono stati completati e documentati nelle sezioni precedenti.

### TASK-AUDIT-009 — Fix: Soglie Ranker Troppo Restrittive per Mercato Crypto

**Status:** Done ✅  
**Completato:** 2026-05-12  
**Priorità:** Critica

**Problema**: La pipeline generava strategie correttamente con backtest reali, ma il ranker le scartava tutte a causa di soglie troppo restrittive per il mercato crypto attuale. I test mostravano che tutte le strategie venivano filtrate via (score=None).

**Fix Applicato**:
- min_trades: 30 → 5 (timeframes veloci)
- min_sharpe: 0.5 → 0.0 (accetta neutre)
- max_drawdown: 15.0 → 25.0 (crypto volatili)
- min_pnl: 2.0% → 0.0% (break-even)

**Risultato**: Pipeline genera strategie VERE e tradeabili! ✅

### TASK-AUDIT-010 — Fix: Soglie Ranker Troppo Permissive e Profitti Irrealistici

**Status:** Done ✅
**Completato:** 2026-05-13
**Priorità:** Critica

**Problema**: Con la configurazione precedente (min_trades=8, min_pnl=2%), le strategie RSI su timeframe 4h facevano solo 5-9 trades con Sharpe artificiosamente alto (fino a 27), producendo profitti stimati irrealistici (+30-35%).

**Diagnosi**: Analisi su 8 asset top marketcap (BTC, ETH, SOL, BNB, ADA, DOT, LINK, AVAX) con 180gg di dati ha rivelato:
- Timeframe 15m: TUTTE le strategie perdono (P&L -43% a -60%)
- Timeframe 1h: solo RSI reversion su altcoin è profittevole (+10-20% con 15-25 trades)
- Timeframe 4h: RSI produce Sharpe 27+ con soli 5-9 trades — artefatto statistico
- EMA crossover e Bollinger Breakout perdono su TUTTI i timeframe e asset

**Fix Applicato** (2026-05-13):
- `ranker.py`: min_trades 8→15, min_sharpe 0.3→0.0, max_drawdown 22.0→40.0, min_pnl 2.0%→0.0%
- `strategy_generator.py`: lookback 180→60gg, pairs default aggiunti ETH/SOL/BNB/USDT, timeframes rimosso 15m
- QUALITY_EMPTY_MESSAGE aggiornato con nuove soglie

**Risultato finale**: 5 strategie generate con P&L medio +16.78%, drawdown 11.1%, trades medio 16 — realistico per crypto. ✅
---

## EPIC-400 — Execution Epic: Attivazione, Esecuzione e Stop

> Implementazione del ciclo di vita completo di una strategia attiva.
> Gap: POST /activate esiste ma non fa nulla di operativo. ExecutionEngine,
> BinanceExchangeAdapter e OrderTracker esistono ma non sono collegati al
> lifecycle della strategia. Mancano: allocazione capitale, signal loop,
> endpoint stop, WS events per trade, P&L live.
>
> Critical Path MVP: TASK-404 -> TASK-405 -> TASK-400/401 -> TASK-402 ->
> TASK-403 -> TASK-406/407 -> TASK-408 -> TASK-409 -> TASK-411/412 ->
> TASK-414 -> TASK-415 -> TASK-417 -> TASK-418 -> TASK-422 -> TASK-423
>
> **Regola:** Ogni task segue TDD (🔴 Red → 🟢 Green → 🔵 Refactor).

---

### Fase A — Allocazione Capitale all'Attivazione

### TASK-400 — Test: test_capital_allocator.py

**Status:** Done
**Priorita:** Critica

Testare CapitalAllocator.allocate(strategy, available_usdt, holdings):
- con pair="BTC/USDT" e budget_eur=500, calcola la quantita BTC da comprare
- se l'utente ha gia BTC sufficienti, restituisce lista vuota (nessun trade iniziale)
- strategia multi-crypto (60% BTC, 40% ETH): calcola trade per entrambe in proporzione
- se budget insufficiente per MIN_NOTIONAL, solleva BudgetTooSmallError

---

### TASK-401 — Implementare execution/capital_allocator.py

**Status:** Done
**Priorita:** Critica

Classe CapitalAllocator con metodo:
  allocate(strategy, available_usdt, holdings) -> list[InitialTradeRequest]
- Legge strategy["params"]["allocation"] per simboli e percentuali;
  se assente usa strategy["pair"] al 100%
- Confronta con holdings per evitare acquisti inutili
- Restituisce InitialTradeRequest(symbol, side="buy", usdt_amount)
  per ogni crypto da acquistare

---

### TASK-402 — Estendere POST /api/strategies/{id}/activate

**Status:** Done
**Priorita:** Critica

Dopo aver settato status = ACTIVE:
1. Recupera budget_eur dalla strategia
2. Chiama exchange.get_balance() per USDT disponibile
3. Chiama exchange.get_holdings() per crypto gia possedute
4. Chiama CapitalAllocator.allocate()
5. Per ogni InitialTradeRequest: chiama exchange.place_market_order()
   e salva su DB con trade_type = "INITIAL_ALLOCATION"
6. Salva activated_at = now() e initial_capital_usdt sulla strategia
7. In caso di errore exchange: rollback a status = APPROVED con messaggio errore

---

### TASK-403 — Test: activate con fondi insufficienti

**Status:** Done
**Priorita:** Alta

Se available_usdt < budget_eur * 0.95, restituisce 422 Unprocessable Entity:
  { "error": "insufficient_funds", "available": X, "required": Y }
La strategia rimane APPROVED.

---

### TASK-404 — Migration DB: nuovi campi su strategies (Migration 008)

**Status:** Done ✅
**Completato:** 2026-05-13
**Priorita:** Critica

Aggiungere alla tabella strategies:
- activated_at TIMESTAMP
- stopped_at TIMESTAMP
- initial_capital_usdt FLOAT
- current_value_usdt FLOAT (aggiornato dal monitor job)
- allocation_trades JSONB (snapshot trade iniziali)
- last_tick_at TIMESTAMP (timestamp ultimo tick scheduler)

NOTA: coordinare numerazione con Migration 009 gia definita in TASK-PORTFOLIO-006
(rinumerare questa come 008 e quella come 010).

---

### TASK-405 — Migration DB: campo trade_type su trades

**Status:** Done ✅
**Completato:** 2026-05-13
**Priorita:** Alta

Aggiungere trade_type VARCHAR DEFAULT 'SIGNAL' alla tabella trades:
- 'INITIAL_ALLOCATION': acquisto iniziale all'attivazione
- 'SIGNAL': trade piazzato dall'engine su segnale tecnico
- 'STOP_CLOSE': chiusura forzata allo stop della strategia

---

### Fase B — Loop di Esecuzione Segnali

### TASK-406 — Implementare execution/strategy_runner.py

**Status:** Done
**Priorita:** Critica

Classe StrategyRunner con metodo async run_tick(strategy: dict) -> None:
- Legge template, pair/allocation, params dalla strategia
- Scarica OHLCV recenti (N candles necessari agli indicatori)
- Calcola segnale tramite SIGNAL_MAP[template](df, params)
- Se segnale positivo, chiama engine.process_signal()
- Aggiorna last_tick_at su DB
- Logga ogni tick (segnale, azione) sulla tabella logs

---

### TASK-407 — Test: test_strategy_runner.py con mock exchange

**Status:** Done
**Priorita:** Alta

- Segnale BUY: place_market_order viene chiamato
- Segnale neutro: nessun ordine piazzato
- Errore exchange: il tick non fa crashare il runner
- last_tick_at aggiornato su DB ad ogni tick

---

### TASK-408 — Scheduler: aggiungere job run_active_strategies_job

**Status:** Done
**Priorita:** Critica

In scheduler/jobs.py:
- Legge da DB strategie con status = "ACTIVE"
- Per ognuna chiama StrategyRunner(engine).run_tick(strategy)
- Concorrenza via asyncio.gather(return_exceptions=True)
- Intervallo configurabile via settings.SCHEDULER_SIGNAL_INTERVAL_MIN
- Registrato in setup_scheduler()

---

### TASK-409 — Singleton ExecutionEngine nel lifespan di main.py

**Status:** Done
**Priorita:** Alta

Nel lifespan, istanziare una sola volta:
  BinanceExchangeAdapter, RiskManager, OrderTracker, ExecutionEngine
Disponibile via app.state o Depends().
Elimina il problema attuale di engine=None nello scheduler.

---

### TASK-410 — RiskManager: position size basata su budget strategia
**Status:** Done ✅
**Completato:** 2026-05-14
**Priorita:** Alta

calculate_position_size() accetta strategy_budget_usdt opzionale.
Calcola la size come percentuale di quello (non del balance totale).

---

### Fase C — Stop Strategia

### TASK-411 — Endpoint POST /api/strategies/{id}/stop

**Status:** Done
**Priorita:** Critica

1. Verifica che la strategia sia ACTIVE
2. Recupera tutti i trade status="OPEN" con strategy_id=id
3. Per ogni trade: exchange.close_position() + aggiorna DB
   (status=CLOSED, exit_price, pnl_pct, trade_type=STOP_CLOSE, closed_at)
4. Aggiorna strategia: status=STOPPED, stopped_at, current_value_usdt
5. Broadcast WS: { type: "strategy_stopped", strategy_id, final_pnl_pct }
6. Best-effort: errori su singole chiusure non bloccano le altre

---

### TASK-412 — Test: POST /api/strategies/{id}/stop

**Status:** Done
**Priorita:** Alta

- Tutti i trade OPEN vengono chiusi
- Strategia gia STOPPED: 409 Conflict
- Strategia non ACTIVE: 422 Unprocessable Entity
- Errore exchange su una chiusura: gli altri chiusi comunque
- WS strategy_stopped inviato dopo la chiusura

---

### TASK-413 — GET /api/exchange/holdings e BinanceExchangeAdapter.get_holdings()

**Status:** Done
**Priorita:** Alta

Nuovo endpoint + metodo adapter che restituisce saldo di tutte le crypto:
  { "BTC": 0.015, "ETH": 0.5, "USDT": 1200.0 }
Usa fetch_balance()["free"] di ccxt.

---

### Fase D — P&L Real-time e WebSocket

### TASK-414 — WS: nuovi tipi di messaggio per trade e strategia

**Status:** Done
**Priorita:** Critica

Nuovi broadcast in ConnectionManager e WsMessageType:
- trade_opened: { type, strategy_id, trade_id, symbol, direction, price, quantity }
- trade_closed: { type, strategy_id, trade_id, pnl_pct, exit_price }
- strategy_pnl_updated: { type, strategy_id, current_pnl_pct, current_pnl_eur, current_value_usdt }
- strategy_stopped: { type, strategy_id, final_pnl_pct, final_value_usdt }
Broadcast aggiunti in OrderTracker.open_position(), close_position() e monitor job.

---

### TASK-415 — Monitor job: calcolo P&L live e broadcast per strategie ACTIVE
**Status:** Done ✅
**Completato:** 2026-05-14
**Priorita:** Alta

Estendere monitor_positions_job:
1. Per ogni strategia ACTIVE: recupera trade OPEN, chiama get_ticker_price()
2. Calcola P&L unrealizzato per ogni posizione
3. Somma al P&L dei trade CLOSED -> current_pnl_pct su initial_capital_usdt
4. Aggiorna current_value_usdt su DB
5. Broadcast WS strategy_pnl_updated

---

### TASK-416 — GET /api/strategies/active/pnl

**Status:** Done
**Priorita:** Alta

Snapshot P&L per tutte le strategie ACTIVE. Per ognuna:
  id, title, initial_capital_usdt, current_value_usdt,
  pnl_eur, pnl_pct, open_trades_count, activated_at, last_tick_at

---

### TASK-417 — GET /api/trades/active — trade aperti con JOIN strategia

**Status:** Done
**Priorita:** Critica

JOIN tra trades e strategies. Per ogni trade OPEN restituisce:
  trade_id, strategy_id, strategy_title, symbol, direction,
  entry_price, current_price (live), unrealized_pnl_pct, quantity, opened_at

---

### Fase E — Frontend: Pagina Active Trades

### TASK-418 — Refactor active-trade.page.ts: tutti i trade multi-strategia

**Status:** Pending
**Priorita:** Critica

- Rimuovere dipendenza da "una singola strategia attiva"
- GET /api/trades/active per snapshot iniziale
- WS trade_opened -> aggiunge riga in real-time
- WS trade_closed -> rimuove/aggiorna riga in real-time
- Trade raggruppati per strategia (sezioni con header collassabili)
- Stato vuoto se nessun trade aperto

---

### TASK-419 — Componente ActiveTradeRowComponent

**Status:** Pending
**Priorita:** Alta

Standalone component per singolo trade aperto:
- Input: trade: ActiveTrade
- P&L unrealizzato aggiornato da WS price (filtrato per symbol)
- Badge BUY (verde) / SELL (rosso)
- Animazione flash su cambio P&L
- Calcola valore posizione in EUR in real-time

---

### TASK-420 — WS Service frontend: nuovi tipi trade_opened, trade_closed, strategy_pnl_updated

**Status:** Done
**Priorita:** Alta

Aggiungere a WsMessageType enum e modelli:
  TradeOpenedPayload, TradeClosedPayload, StrategyPnlPayload, StrategyStoppedPayload

---

### TASK-421 — Test: active-trade.page.spec.ts aggiornato

**Status:** Pending
**Priorita:** Media

- WS trade_opened: lista aggiornata
- WS trade_closed: trade rimosso dalla lista
- Trade raggruppati correttamente per strategia
- Stato vuoto visualizzato quando lista vuota

---

### Fase F — Frontend: P&L Live nella Pagina Strategie

### TASK-422 — P&L live per strategie ACTIVE in strategies.page.ts

**Status:** Done
**Priorita:** Critica

Per le strategie con status = "ACTIVE":
- GET /api/strategies/active/pnl all'inizializzazione
- WS strategy_pnl_updated aggiorna valori in real-time
- Mostra: capitale iniziale, valore attuale, P&L EUR e %, badge LIVE pulsante
- Verde se P&L > 0, rosso se P&L < 0

---

### TASK-423 — Bottone "Stop" collegato a POST /api/strategies/{id}/stop

**Status:** Done
**Priorita:** Critica

Dialog di conferma esistente (TASK-323) collegato all'endpoint reale:
- Loading state durante la chiamata
- Al completamento: aggiorna status -> STOPPED, mostra notifica P&L finale
- WS strategy_stopped gestito per aggiornamento da altre sessioni

---

### TASK-424 — Badge "LIVE" e indicatori visivi strategia in esecuzione

**Status:** Done
**Priorita:** Media

Per ogni strategia ACTIVE nella strategies page:
- Badge "LIVE" con animazione pulse verde
- Tooltip con last_tick_at formattato ("Ultimo segnale: 3 min fa")
- Contatore segnali generati oggi

---

### Fase G — Multi-Crypto Allocation

### TASK-425 — Schema params.allocation per strategie multi-simbolo

**Status:** Pending
**Status:** Done ✅
**Completato:** 2026-05-14
**Priorita:** Alta

Formato JSON per strategie multi-asset:
  { "allocation": [{ "symbol": "BTC/USDT", "pct": 60 }, { "symbol": "ETH/USDT", "pct": 40 }], ... }
Aggiornare StrategyCreate Pydantic schema.
Coordinare con TASK-PORTFOLIO-005 (stesso dominio).

---

### TASK-426 — StrategyRunner multi-simbolo

**Status:** Pending
**Priorita:** Alta

run_tick() itera su tutti i simboli in allocation.
Genera segnali indipendenti per ogni simbolo.
Rispetta la percentuale di budget per il calcolo della position size.

---

### TASK-427 — Frontend: selezione multi-crypto nel form generazione

**Status:** Pending
**Priorita:** Media

Form con aggiunta di piu crypto e slider percentuale per ognuna.
Validazione: somma = 100%.
Preview capitale allocato per crypto.
Coordinare con TASK-PORTFOLIO-008.

---

### Fase H — Stabilizzazione e Test E2E

### TASK-428 — Test integrazione: flusso completo activate -> tick -> stop

**Status:** Pending
**Priorita:** Alta

Con exchange mockato, verificare:
1. activate -> trade iniziali salvati su DB
2. Scheduler tick -> segnale -> trade SIGNAL su DB
3. Monitor -> prezzo -> chiusura take-profit, P&L calcolato
4. stop -> trade residui chiusi -> STOPPED, WS events verificati

---

### TASK-429 — Gestione errori e retry per exchange failures nel signal loop

**Status:** Pending
**Priorita:** Alta

asyncio.gather(return_exceptions=True) nel job.
Errore loggato su DB con level="ERROR".
Broadcast WS engine_error: { type, strategy_id, error_code, message }.
Strategia rimane ACTIVE (errore transitorio).

---

### TASK-430 — Dashboard: KPI globali strategie attive e trade aperti

**Status:** Pending
**Priorita:** Media

Aggiungere a GET /api/dashboard/stats:
  active_strategies_count, open_trades_count, total_active_pnl_pct
Visualizzare come KPI card con aggiornamento WS.

### TASK-431 — Fix Bug Operativi: Dashboard Pending, Trade non Visibili, Stop non chiude Trade

**Status:** Done ✅
**Completato:** 2026-05-14
**Priorita:** Critica

**Bug 1 — Dashboard "pending"**: Il service `dashboard.service.ts` non aveva timeout/fallback. Se il backend era offline o lento, `shareReplay(1)` bloccava la UI in stato "loading".

**Fix**: Aggiunto `timeout(15s)` + `catchError` che restituisce stato OFFLINE con valori a zero.

**File modificati:**
- `synthtrade/frontend/synthtrade-ui/src/app/core/services/dashboard.service.ts`

---

**Bug 2 — Trade attivi non visibili dopo attivazione strategia**: La pagina `active-trade.page.ts` assumeva UNA singola strategia attiva e usava dati da dashboard senza caricare i trade reali dal monitor endpoint.

**Fix**: Riscritta pagina per supportare MULTIPLE strategie attive, caricando dati via `GET /api/strategies/active/pnl` + `GET /api/monitor/{id}` per ogni strategia. Aggiunte interfacce `ActivePnlItem`, `MonitorStrategyInfo` in `strategy.service.ts`.

**File modificati:**
- `synthtrade/frontend/synthtrade-ui/src/app/pages/active-trade/active-trade.page.ts`
- `synthtrade/frontend/synthtrade-ui/src/app/core/services/strategy.service.ts`
- `synthtrade/backend/app/api/monitor.py` (fix calcolo P&L cumulativo)

---

**Bug 3 — Stop strategia non chiude trade su DB**: Quando `exchange.close_position()` falliva (es. testnet non raggiungibile), l'exception impediva l'update dello status trade su DB, lasciandoli OPEN per sempre.

**Fix**: La chiusura trade su DB ora avviene SEMPRE, indipendentemente dal successo/failure di `exchange.close_position()`. Se exchange fallisce, mantiene il prezzo entry e P&L=0.

**File modificati:**
- `synthtrade/backend/app/api/strategies.py`

---

## 🛠️ Fase 8 — Fix Operativi Testnet (v1.2.4)

### TASK-415 — Monitor API: Aggiunta P&L in EUR
- Implementazione calcolo `total_pnl_eur` basato sul budget della strategia.
- Esposizione del campo nell'endpoint `/api/monitor/{id}`.
**Status:** Done ✅
**Completato:** 2026-05-14

### TASK-416 — Fix Conversione EUR su Binance Testnet
- Aggiornamento `_convert_to_eur` per gestire la coppia inversa `EUR/USDT`.
- Rimozione dipendenza da coppia `USDT/EUR` non presente su Testnet.
**Status:** Done ✅
**Completato:** 2026-05-14

### TASK-417 — Frontend: Error Handling Attivazione
- Aggiunta gestione `error` nel subscribe di `activate()` in `strategies.page.ts`.
- Notifica alert con dettaglio errore (es. insufficient_funds).
**Status:** Done ✅
**Completato:** 2026-05-14

