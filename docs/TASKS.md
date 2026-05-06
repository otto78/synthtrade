# SynthTrade — TASKS

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

## � Fase 1.B — Constraint-Aware Generator

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

## �🟠 Fase 2 — Backend API

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

## � Fase 2.B — Exchange Adapter (Binance)

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

## �🟢 Fase 3 — Frontend Angular

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

## � Fase 3.B — Frontend: Strategy Request Form

> Finestra di prompt per guidare la generazione delle strategie.
> Da inserire come sotto-fase di Fase 3, dopo il completamento di `StrategiesPage`.

### 3.B.0 Modelli

### TASK-179 — Aggiungere in `core/models/strategy.model.ts`:

**Status:** In Progress  
**Data:** 2026-05-06

  - `StrategyRequest` → `budgetEur`, `durationDays`, `assetClass`, `symbols`, `riskLevel`, `freeText`, `maxStrategies`
  - `GenerationStatus` → `generationId`, `status` (`pending`/`running`/`completed`/`failed`), `strategies?`

### 3.B.1 PipelineService

### TASK-180 — 🔴 Test `pipeline.service.spec.ts` → `generateStrategies(req: StrategyRequest)` chiama `POST /api/pipeline/generate` e restituisce il `generationId`

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-181 — 🔴 Test → `pollGenerationStatus(generationId)` chiama `GET /api/pipeline/generate/:id/status` ogni 3s con `interval()` RxJS e completa quando `status === 'completed'` o `'failed'`

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-182 — 🟢 Implementare `core/services/pipeline.service.ts`

**Status:** In Progress  
**Data:** 2026-05-06


### 3.B.2 StrategyRequestFormComponent

### TASK-183 — 🔴 Test `strategy-request-form.component.spec.ts` → form invalido se `budgetEur ≤ 0` o `durationDays ≤ 0`

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-184 — 🔴 Test → `riskLevel` obbligatorio, default `medium`

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-185 — 🔴 Test → al submit valido emette evento `requestSubmitted` con il `StrategyRequest` compilato

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-186 — 🔴 Test → campo `freeText` opzionale, max 500 caratteri con counter visibile

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-187 — 🔴 Test → chip-selector per `symbols`: l'utente può aggiungere/rimuovere simboli (BTCUSDT, ETHUSDT, ecc.) o lasciare vuoto per "scegli tu"

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-188 — 🟢 Implementare `shared/components/strategy-request-form/strategy-request-form.component.ts` con `ReactiveFormsModule`

**Status:** In Progress  
**Data:** 2026-05-06


### 3.B.3 GenerationProgressComponent

### TASK-189 — 🔴 Test `generation-progress.component.spec.ts` → mostra spinner con messaggio "Generazione in corso..." durante `status === 'running'`

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-190 — 🔴 Test → al completamento mostra "N strategie generate" con animazione e bottone "Vedi risultati"

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-191 — 🔴 Test → in caso di `status === 'failed'` mostra messaggio di errore e bottone "Riprova"

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-192 — 🟢 Implementare `shared/components/generation-progress/generation-progress.component.ts`

**Status:** In Progress  
**Data:** 2026-05-06


### 3.B.4 Integrazione in StrategiesPage

### TASK-193 — 🟢 Aggiungere bottone **"Genera nuove strategie"** in `StrategiesPage` che apre il `StrategyRequestFormComponent` in un pannello laterale (o modale)

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-194 — 🟢 Al submit del form, chiamare `PipelineService.generateStrategies()` e mostrare `GenerationProgressComponent`

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-195 — 🟢 Sottoscriversi al messaggio WS `generation_complete` per aggiornare la lista automaticamente senza polling manuale

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-196 — 🔴 Test `strategies.component.spec.ts` (aggiuntivi) → click "Genera nuove strategie" apre il pannello

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-197 — 🔴 Test → messaggio WS `generation_complete` aggiorna la lista delle strategie senza ricaricare la pagina

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-198 — 🔵 Refactor: le strategie generate dall'utente hanno un badge visivo **"Generata per te"** distinto dalle strategie pre-esistenti del seed

**Status:** In Progress  
**Data:** 2026-05-06


### 3.B.5 Dettaglio Strategia

### TASK-199 — 🟢 Creare `pages/strategy-detail/strategy-detail.component.ts` raggiungibile da `/strategies/:id`

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-200 — 🔴 Test `strategy-detail.component.spec.ts` → mostra tutti i parametri della strategia: simbolo, timeframe, indicatori usati, metriche backtest (Sharpe, Win Rate, Max Drawdown, Total Trades)

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-201 — 🔴 Test → mostra il `reasoning` dell'AI Evaluator (se disponibile) con score e verdict badge

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-202 — 🔴 Test → bottone **"Attiva questa strategia"** chiama `StrategyService.activateStrategy(id)` e naviga a `/active-trade`

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-203 — 🔴 Test → bottone **"Attiva questa strategia"** è disabilitato se `budget` della strategia supera il saldo disponibile

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-204 — 🟢 Aggiungere la route `/strategies/:id` in `app.routes.ts`

**Status:** In Progress  
**Data:** 2026-05-06


---

## �🔴 Fase 4 — Execution Engine

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

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-296 — `core/logging.py` con `setup_logging()` e `JsonFormatter`

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-297 — Chiamare `setup_logging()` nel lifespan di `main.py`

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-298 — Sostituire tutti i `print()` con `logger = logging.getLogger(__name__)`

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-299 — Middleware FastAPI con `request_id` (UUID) in ogni log

**Status:** In Progress  
**Data:** 2026-05-06


### 6.6 Error Handling Globale
### TASK-300 — `core/exceptions.py`: `SynthTradeError`, `RiskViolationError`, `ModelUnavailableError`, `OrderExecutionError`

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-301 — Handler globale `Exception` → `{"error": "internal_server_error", "request_id": "..."}`

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-302 — Handler `HTTPException` con `request_id`

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-303 — Handler `RequestValidationError` con errori Pydantic leggibili

**Status:** In Progress  
**Data:** 2026-05-06

### TASK-304 — Nessun stack trace esposto in produzione

**Status:** In Progress  
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
