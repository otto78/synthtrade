# Archive of Completed Tasks — SynthTrade

Questo file contiene lo storico di tutti i task completati, spostati qui da `TASKS.md` per mantenere il file operativo leggibile e focalizzato sul lavoro corrente.

---

## ✅ Fase 1 — Core & Backend Base (v1.0.0)

### TASK-001 — Setup ambiente virtuale e dipendenze
**Status:** Done ✅  
**Completato:** 2025-01-15

### TASK-002 — Configurazione Pydantic Settings
**Status:** Done ✅  
**Completato:** 2025-01-15

### TASK-003 — Setup Supabase Client
**Status:** Done ✅  
**Completato:** 2025-01-15

### TASK-004 — Implementazione Indicators (EMA, RSI, Bollinger)
**Status:** Done ✅  
**Completato:** 2025-01-16

... [Omettendo per brevità le migliaia di righe di task già completati e documentati in STORY.md] ...

### TASK-319 — Migrazione task a formato Loom
**Status:** Done ✅  
**Completato:** 2026-05-06

---

## 🔴 Fix Allucinazioni (v1.2.0)

### TASK-FIX-001 — Rimuovere import random e aggiungere imports reali
**Status:** Done ✅  
**Completato:** 2026-05-12

### TASK-FIX-002 — Aggiungere campi backtest a StrategyParams
**Status:** Done ✅  
**Completato:** 2026-05-12

... [Tutti i task FIX-001 -> FIX-011 completati] ...

---

## ⚡ UX Generazione / Anti-allucinazioni — HALU (v1.2.1)

### HALU-FE-01 — Gestione errori POST /api/pipeline/generate
**Status:** Done ✅  
**Completato:** 2026-05-12

... [Tutti i task HALU completati] ...

---

## 🏗️ EPIC-400 — Execution Epic (Fasi Completate)

### TASK-400 a TASK-417 (Fase A, B, C, D)
**Status:** Done ✅  
**Completato:** 2026-05-14

... [Tutti i task dell'Epic 400 già completati] ...

## ??? Fase 6 � Stabilizzazione & Completamento (Debito Tecnico) [Aggiornamento 2026-05-15]

### TASK-015 � Refactor config.py (Pydantic Settings)
**Status:** Done ?
**Completato:** 2026-05-15

### TASK-041 — Refactor Ranker con Pydantic e configurazione dinamica
**Status:** Done ✅  
**Completato:** 2026-05-15

### TASK-068 — Refactor StrategyGenerator (performance & service integration)
**Status:** Done ✅  
**Completato:** 2026-05-15

### TASK-069 — Refactor StopLossManager (Service pattern)
**Status:** Done ✅  
**Completato:** 2026-05-15

### TASK-038 — Refactor MarketData (Service pattern centralizzato)
**Status:** Done ✅  
**Completato:** 2026-05-15

### TASK-070 — Refactor TradeExecutor (Supporto per ExecutionEngine)
**Status:** Done ✅  
**Completato:** 2026-05-15

---

## 📈 EPIC-400 — Pipeline di Esecuzione (Completato 2026-05-18)

### TASK-426 — StrategyRunner multi-simbolo
**Status:** Done ✅  
**Completato:** 2026-05-18
**Priorità:** Alta  
**Dettagli:**
- `run_tick()` deve iterare su tutti i simboli in `allocation`.
- Generazione segnali indipendenti per ogni simbolo.
- Rispetto delle percentuali di budget per il calcolo della position size.

---

## 🛠️ Fase 6 — Stabilizzazione & Completamento (Completato 2026-05-18)

### TASK-130 — Refactor Dashboard: cache con `shareReplay(1)` + invalidazione dopo 30s
**Status:** Done ✅  
**Completato:** 2026-05-18
**Priorità:** Media  
**Dettagli:**
- Implementare `shareReplay(1)` nel `DashboardService` per evitare chiamate ridondanti.
- Aggiungere logica di invalidazione per forzare il refresh dei dati.

### TASK-174 — Refactor: `LogFiltersComponent` + query params sync
**Status:** Done ✅
**Completato:** 2026-05-18
**Priorità:** Media

### TASK-067 — Refactor `RankConfig`
**Status:** Done ✅  
**Completato:** 2026-05-18
**Priorità:** Media  
**Dettagli:** Refactoring della configurazione del ranker completato e integrato con successo.

### TASK-169 — Refactor: `StrategyListComponent` + `StrategyRowComponent`
**Status:** Done ✅  
**Completato:** 2026-05-18
**Priorità:** Media  
**Dettagli:** Consolidamento e ottimizzazione della visualizzazione della lista strategie completata.

---

## 🧪 Test Suite Stabilization & Quality Assurance (Completato 2026-05-18)

### TASK-501 — Fix `test_activate_strategy.py` (Insufficient Funds)
**Status:** Done ✅  
**Completato:** 2026-05-18
**Priorità:** Alta  
**Dettagli:** Risolvere il `KeyError: 'detail'` causato dal formato di risposta 422 non allineato tra router e test.

### TASK-502 — Fix `test_api_pipeline.py` (Status Check)
**Status:** Done ✅  
**Completato:** 2026-05-18
**Priorità:** Media  
**Dettagli:** Risolvere il fallimento di `test_get_generation_status` dovuto a discrepanze nel mock dello stato della pipeline.

### TASK-503 — Fix `test_execution_integration.py` (Signal Flow)
**Status:** Done ✅  
**Completato:** 2026-05-18
**Priorità:** Alta  
**Dettagli:** Ripristinare i test di integrazione del ciclo operativo (signal -> trade) che falliscono dopo l'introduzione di `ExecutionEngine`.

### TASK-504 — Fix Unit Tests: `test_ranker.py` (compute_score NameError)
**Status:** Done ✅  
**Completato:** 2026-05-18
**Priorità:** Alta  
**Dettagli:** Aggiornare tutti i test unitari del Ranker per utilizzare la nuova classe `Ranker` e `RankConfig` invece della funzione deprecata.

### TASK-217 — 🔵 Refactor: `SignalResolver` iniettato nel costruttore
**Status:** Done ✅  
**Completato:** 2026-05-19
**Priorità:** Media

**Descrizione:**
Refactoring dell'architettura di gestione dei segnali per permettere l'iniezione del resolver. Attualmente i segnali vengono processati individualmente; il resolver permette di valutare un set di segnali collettivamente (es. per limitare posizioni simultanee o scegliere il segnale più forte).

**Piano di Attuazione:**
1.  **Definizione Configurazione**:
    *   Aggiungere `SIGNAL_STRENGTH_THRESHOLD` (default: 0.6) in `app/config.py`.
2.  **Refactor `ExecutionEngine`**:
    *   Aggiornare il costruttore in `app/execution/execution_engine.py` per accettare obbligatoriamente (o con default tipizzato) un `SignalResolverProtocol`.
    *   Aggiungere un metodo `process_signals(signals, balance, current_drawdown_pct)` che:
        *   Recupera le posizioni aperte correnti.
        *   Usa `self.signal_resolver.resolve(...)` per filtrare i segnali.
        *   Itera sui segnali risolti e chiama `process_signal` per ognuno.
3.  **Refactor `StrategyRunner`**:
    *   Modificare `run_tick` in `app/execution/strategy_runner.py` per accumulare i segnali di tutti i simboli in una lista invece di processarli uno alla volta.
    *   Chiamare `engine.process_signals(...)` alla fine del loop di scansione simboli.
4.  **Integrazione `main.py`**:
    *   Inizializzare `DefaultSignalResolver` con la soglia dai settings.
    *   Passarlo all'istanza singleton di `ExecutionEngine`.
5.  **Verifica**:
    *   Aggiornare `tests/unit/test_signal_resolver.py` se necessario.
    *   Creare un nuovo test unitario per verificare la catena `StrategyRunner` -> `ExecutionEngine` -> `SignalResolver`.

### TASK-232 — 🔵 Refactor: `MarketRegimeDetector` con soglie configurabili
**Status:** Done ✅  
**Completato:** 2026-05-19
**Priorità:** Media

**Descrizione:**
Estrarre le soglie di rilevamento del regime di mercato da `app/ai/context_builder.py` e renderle configurabili tramite `app.config.Settings`. Questo permette di adattare il comportamento di `detect_market_regime` a mercati volatili, trending o ranging senza cambiare il codice.

**Piano di Attuazione:**
1.  **Audit della logica attuale**:
    *   Identificare le costanti hardcoded in `app/ai/context_builder.py` come `_VOLATILE_ATR_THRESHOLD` e `_TRENDING_SLOPE_THRESHOLD`.
    *   Verificare l'uso di `detect_market_regime` in `app/ai/context_builder.py` e nei test esistenti.
2.  **Definizione dei setting**:
    *   Aggiungere in `app/config.py` i campi configurabili:
        *   `MARKET_REGIME_ATR_THRESHOLD: float = 0.025`
        *   `MARKET_REGIME_TRENDING_R2_THRESHOLD: float = 0.15`
        *   `MARKET_REGIME_MIN_CANDLES: int = 20` (se serve per i controlli di validità dati)
    *   Aggiornare `.env.example` con i valori di default.
3.  **Refactor `context_builder`**:
    *   Rimuovere le costanti locali e leggere i valori da `settings`.
    *   Valutare se trasformare `detect_market_regime` in funzione parametrizzata per aumentare testabilità.
    *   Mantenere i tre stati esistenti `trending`, `volatile`, `ranging`.
4.  **Integrazione e documentazione**:
    *   Aggiornare i commenti in `app/ai/context_builder.py` e `app/config.py` perché i soglie siano esplicite.
    *   Documentare il significato di ogni soglia: volatility threshold vs trend R² threshold.
5.  **Verifica e test**:
    *   Aggiornare i test in `synthtrade/backend/tests/unit/test_context_builder.py` per verificare che i nuovi setting influenzino l'esito.
    *   Aggiungere un test che forzi regime `volatile`/`trending` cambiando i valori di soglia.

### TASK-245 — 🔵 Refactor: `MAX_CONCURRENT_EVALS` da `Settings`
**Status:** Done ✅  
**Completato:** 2026-05-19
**Priorità:** Media

**Descrizione:**
Garantire che la concorrenza dell'evaluator AI sia controllata esclusivamente da `settings.MAX_CONCURRENT_EVALS` e non da valori hardcoded sparsi nel codice.

**Piano di Attuazione:**
1.  **Audit dell'uso corrente**:
    *   Verificare `synthtrade/backend/app/core/run_pipeline.py`, `synthtrade/backend/app/ai/evaluator.py` e ogni test che passi un valore di `max_concurrent`.
    *   Cercare hardcoded `asyncio.Semaphore(...)` e default `max_concurrent=3`.
2.  **Refactor dell'evaluator**:
    *   In `app/ai/evaluator.py`, cambiare il default del parametro `max_concurrent` da `3` a `None`.
    *   All'interno del metodo, impostare `max_concurrent = settings.MAX_CONCURRENT_EVALS` se non specificato.
3.  **Allineamento della pipeline**:
    *   Lasciare la chiamata in `run_pipeline` come fallback esplicito, ma assicurarsi che il comportamento predefinito del metodo sia sempre basato su `settings`.
4.  **Documentazione e configurazione**:
    *   Aggiornare `.env.example` e `app/config.py` per chiarire il ruolo di `MAX_CONCURRENT_EVALS`.
5.  **Verifica e test**:
    *   Aggiungere test che verificano il valore usato quando `evaluate_all()` viene chiamato senza `max_concurrent`.
    *   Aggiungere test di regressione per assicurare che il valore impostato in `settings` venga propagato al semaforo.

### TASK-186 — Unit Test `dashboard.page.spec.ts`
**Status:** Done ✅  
**Completato:** 2026-05-19
**Priorità:** Media  
**Dettagli:** Eseguito `npm test -- --runInBand src/app/pages/dashboard/dashboard.page.spec.ts`; 9 test passati, coperta la logica di rendering delle StatCard, aggiornamento WS e gestione errori.

### TASK-421 — Unit Test `active-trade.page.spec.ts`
**Status:** Done ✅  
**Completato:** 2026-05-19
**Priorità:** Media  
**Dettagli:** Eseguito `npm test -- --runInBand src/app/pages/active-trade/active-trade.page.spec.ts`; 8 test passati, coperto il rendering delle strategie, KPI, WS trade events e calcolo P&L.

### TASK-AUDIT-001 — Verifica connettività API: Binance e OpenRouter
**Status:** Done ✅  
**Completato:** 2026-05-18
**Priorità:** Alta  
**File:** `synthtrade/backend/tests/test_connectivity.py`
**Dettagli:** Verificare connettività reale con chiavi di test/read-only.

### TASK-AUDIT-002 — Prova del Random (Verifica Allucinazioni)
**Status:** Done ✅  
**Completato:** 2026-05-18
**Priorità:** Critica  
**Dettagli:** `tests/audit/test_random_proof.py` fallisce con AttributeErrors. Necessario refactoring per testare il determinismo della nuova pipeline.

### TASK-AUDIT-003 — Test AI Evaluator reale
**Status:** Done ✅  
**Completato:** 2026-05-18
**Priorità:** Alta  
**Dettagli:** Inviare dati OHLCV reali a OpenRouter e validare il parsing del verdetto AI.

### TASK-AUDIT-004 — Verifica backtest con dati OHLCV reali
**Status:** Done ✅  
**Completato:** 2026-05-18
**Priorità:** Alta  
**Dettagli:** Garantire che il backtest produca gli stessi risultati caricando OHLCV da file vs API.

### TASK-AUDIT-005 — Confronto DB: strategie manuali vs automatiche
**Status:** Done ✅  
**Completato:** 2026-05-18
**Priorità:** Media  
**Dettagli:** Verificare la coerenza dei dati nel database dopo una generazione massiva.

### TASK-175 — Installare e configurare Playwright (Frontend E2E)
**Status:** Done ✅  
**Completato:** 2026-05-18
**Priorità:** Alta  
**Dettagli:**
- Setup dell'ambiente di test Playwright completato.
- Configurazione dei browser Chromium e Firefox per i test cross‑browser.
- Aggiunto script `test:e2e` e configurazione Playwright.
- Test di prova creato in `e2e/strategies.spec.ts`.

### TASK-209 — 🔵 Refactor: `RiskConfig` dataclass iniettabile nei test
**Status:** Done ✅  
**Completato:** 2026-05-18
**TDD Workflow:**
- [x] 🔴 Red: Tests created and failing
- [x] 🟢 Green: Implement feature to pass tests
- [x] 🔵 Refactor: Clean up code
- [x] ✅ Complete: All tests passing

### TASK-214 — 🔵 Refactor: pluggabile via `config.py` con `importlib`
**Status:** Done ✅  
**Completato:** 2026-05-18
**TDD Workflow:**
- [x] 🔴 Red: Tests created and failing
- [x] 🟢 Green: Implement feature to pass tests
- [x] 🔵 Refactor: Clean up code
- [x] ✅ Complete: All tests passing

### TASK-250 — 🟢 Broadcast WS `eval_complete` con strategy_id, verdict, score
**Status:** Done ✅
**Completato:** 2026-05-18
**Priorità:** Media

### TASK-418 — Refactor `active-trade.page.ts`: supporto multi-strategia
**Status:** Done ✅
**Completato:** 2026-05-19
**Priorità:** Critica
**Dettagli:**
- ✅ Rimuovere dipendenza da "una singola strategia attiva".
- ✅ GET /api/trades/active per snapshot iniziale.
- ✅ WS trade_opened/closed per aggiornamento real-time.
- ✅ Trade raggruppati per strategia con header collassabili.
- ✅ 17/17 test passati.

### TASK-419 — Componente `ActiveTradeRowComponent`
**Status:** Done ✅
**Completato:** 2026-05-19
**Priorità:** Alta
**Dettagli:**
- ✅ P&L unrealizzato aggiornato da WS price in tempo reale.
- ✅ Badge BUY/SELL con animazioni flash al cambio prezzo (flash-up/flash-down).
- ✅ Calcolo valore posizione in EUR in tempo reale (current_price * quantity).
- ✅ Bug fix: positionValueEur ora usa current_price invece di entry_price.
- ✅ 19 test Python + 12 test Angular = 31 test passati.

### TASK-427 — Frontend: selezione multi-crypto nel form generazione
**Status:** Done ✅
**Completato:** 2026-05-19
**Priorità:** Media
**Dettagli:**
- ✅ Form con aggiunta di più crypto e slider percentuale.
- ✅ Validazione: somma delle percentuali = 100%.
- ✅ Backend: AllocationItem model con validazione.
- ✅ Frontend: toggle AI auto-selection vs allocation manuale.

### TASK-429 — Gestione errori e retry per exchange failures nel signal loop
**Status:** Done ✅
**Completato:** 2026-05-19
**Priorità:** Alta
**Dettagli:**
- ✅ asyncio.gather con `return_exceptions=True` gestisce eccezioni senza bloccare altre strategie.
- ✅ Broadcast errori exchange via WebSocket con `broadcast_exchange_error()`.
- ✅ Logging dettagliato con strategy_id, error_type, error_message.
- ✅ Statistiche success/error nel log del job.
- ✅ 17 test passati + 11 test strategy_runner esistenti confermati.

### TASK-430 — Dashboard: KPI globali strategie attive e trade aperti
**Status:** Done ✅
**Completato:** 2026-05-19
**Priorità:** Media
**Dettagli:**
- ✅ Aggiunto `active_strategies_count` (conteggio strategie ACTIVE).
- ✅ Aggiunto `total_active_pnl_pct` (P&L aggregato calcolato da current_value vs initial_capital).
- ✅ Integrati i KPI nell'endpoint GET /api/dashboard.
- ✅ 17 test passati.

---

## 🎉 EPIC-400 — Pipeline di Esecuzione (COMPLETATA 2026-05-19)

**Task Completati:**
- TASK-418: Refactor `active-trade.page.ts` supporto multi-strategia
- TASK-419: Componente `ActiveTradeRowComponent` con P&L real-time
- TASK-426: StrategyRunner multi-simbolo
- TASK-427: Frontend selezione multi-crypto nel form generazione
- TASK-429: Gestione errori exchange failures con broadcast WebSocket
- TASK-430: Dashboard KPI globali strategie attive

**Totale Test:** 31 (TASK-419) + 28 (TASK-429) + 17 (TASK-430) = **76+ test passati per questa sessione**

---

## 🛠️ Fase 6A — Refactoring & Logica Applicativa (Inizio 2026-05-19)

### TASK-187 — Fix `dashboard.page.ts` e `dashboard.service.ts`
**Status:** Done ✅
**Completato:** 2026-05-19
**Priorità:** Alta
**Dettagli:**
- ✅ Aggiunto `invalidateCache()` method per forzare refresh dati.
- ✅ Implementato retry logic con exponential backoff (1s, 2s, 4s) - max 3 retry.
- ✅ Gestione errori timeout (15s) con fallback graceful.
- ✅ catchError ritorna dati fallback senza propagare errori sensibili.
- ✅ Aggiornati campi DashboardStats con `active_strategies_count` e `total_active_pnl_pct`.
- ✅ 18 test passati (9 service + 9 page).

---

## 🧪 Fase 6B — Test Suite & Stabilità Frontend (Inizio 2026-05-19)

### TASK-FE-001 — ✅ Migliora progress bar generazione con stepper a 3 fasi proporzionale
**Status:** Done ✅  
**Completato:** 2026-05-19
**Priorità:** Media

**Descrizione:**
Sostituita la progress bar animata fittizia (che partiva al 100% in 30s) con uno stepper visivo a 3 fasi (Analisi Mercato → Ottimizzazione AI → Backtesting) con larghezza proporzionale allo stato backend.

**Modifiche:**
- `generation-progress.component.ts`: nuovo layout stepper con cerchi ✅/⏳/○, barra proporzionale (33/66/100%), indicatori visivi, step 3 "Backtesting" ora correttamente attivato su `completed`

### TASK-176 — E2E `auth.spec.ts` (login errato → errore; login corretto → /dashboard)
**Status:** Done ✅
**Completato:** 2026-05-19
**Priorità:** Alta
**Dettagli:**
- ✅ Creato `e2e/auth.spec.ts` con 6 scenari di test Playwright.
- ✅ Test login con credenziali errate → mostra errore.
- ✅ Test login con credenziali corrette → redirect a /dashboard.
- ✅ Test accesso route protetta senza auth → redirect a /login.
- ✅ Test logout → redirect a /login e token rimosso.
- ✅ Test persistenza autenticazione dopo page reload.
- ✅ Test loading state durante autenticazione.
- ✅ Auth usa solo password (no email) - password di test: "testpass".
- ⚠️ I test E2E richiedono backend su http://localhost:8008 e frontend su http://localhost:4208.

### TASK-177 — E2E `strategies.spec.ts` (attivazione e disattivazione end-to-end)
**Status:** Done ✅
**Completato:** 2026-05-19
**Priorità:** Alta
**Dettagli:**
- ✅ Creato `e2e/strategies.spec.ts` con 8 scenari di test Playwright.
- ✅ Test caricamento pagina e visualizzazione tab.
- ✅ Test navigazione tra tab (GENERAZIONE, APPROVATE, ATTIVE, COMPLETATE).
- ✅ Test approvazione strategia PENDING → passa ad APPROVATE.
- ✅ Test attivazione strategia APPROVED → passa ad ATTIVE.
- ✅ Test disattivazione strategia ACTIVE → passa a COMPLETATE.
- ✅ Test visualizzazione P&L real-time per strategie attive.
- ✅ Test reject strategia approved.
- ✅ Test empty state quando non ci sono strategie.
- ⚠️ I test E2E richiedono backend su http://localhost:8008 e frontend su http://localhost:4208.

### TASK-178 — E2E `logs.spec.ts` (filtro level aggiorna lista)
**Status:** Done ✅
**Completato:** 2026-05-19
**Priorità:** Alta
**Dettagli:**
- ✅ Creato `e2e/logs.spec.ts` con 13 scenari di test Playwright.
- ✅ Test caricamento pagina logs.
- ✅ Test visualizzazione lista log.
- ✅ Test filtro per level (BUY, SELL, SKIP, BLOCK, ERROR).
- ✅ Test reset filtro mostra tutti i log.
- ✅ Test paginazione (next/prev).
- ✅ Test disabilitazione bottone prev sulla prima pagina.
- ✅ Test visualizzazione tutte le opzioni di filtro.
- ✅ Test struttura log (timestamp, badge, reason, price).
- ⚠️ I test E2E richiedono backend su http://localhost:8008 e frontend su http://localhost:4208.

---

## 🎉 Fase 6B — Test Suite E2E Completata (2026-05-19)

**Test E2E Completati:**
- TASK-176: auth.spec.ts (6 test)
- TASK-177: strategies.spec.ts (8 test)
- TASK-178: logs.spec.ts (13 test)

**Totale Test E2E:** **27 test implementati** per questa fase.

**Coverage:**
- Autenticazione e autorizzazione completa
- Workflow strategie end-to-end (PENDING → APPROVED → ACTIVE → STOPPED)
- Gestione logs con filtri e paginazione

---

## 🔄 Modalità TEST/LIVE (v1.3.0)

## 🚀 TASK-431 — Modalità TEST/LIVE: separazione dati, API key, toggle UI

**Status:** Done ✅  
**Completato:** 2026-05-20
**Priorità:** Alta
**Dipende da:** Nessuno

**Dettagli:**
Implementare la separazione completa tra modalità TEST e LIVE nel sistema. Include:
- Separazione API key Binance (testnet vs produzione)
- Separazione dati DB (strategie, trade, log etichettati con modalità)
- ExchangeFactory centralizzato per reconnect dinamico
- Endpoint API per leggere/cambiare modalità a runtime
- Indicatore dinamico TEST/LIVE nella topbar frontend con toggle

### Piano di Attuazione:

**1. Config (`config.py`)**
- Aggiungere `TRADING_MODE: str = 'test'`
- Aggiungere `ALLOW_LIVE_MODE: bool = False`
- Aggiungere `BINANCE_API_KEY_LIVE: str = ''` e `BINANCE_SECRET_KEY_LIVE: str = ''`
- Proprietà dinamiche: `binance_api_key`, `binance_secret_key`, `BINANCE_TESTNET` derivate da `TRADING_MODE`

**2. `.env`**
- Aggiungere `TRADING_MODE=test`, `ALLOW_LIVE_MODE=false`
- Scommentare/rinominare le OLD key come `BINANCE_API_KEY_LIVE` / `BINANCE_SECRET_KEY_LIVE`

**3. ExchangeFactory (`app/core/exchange_factory.py` — nuovo)**
- Centralizza tutte le istanze `ccxt.binance()`
- `get_exchange()` → cache singleton
- `reconnect(mode)` → ricrea connessione con key/URL corretti
- Aggiornare `market_data.py`, `binance_balance.py`, `exchange.py`, `main.py` per usare ExchangeFactory

**4. Migrazioni DB**
- Colonna `mode TEXT DEFAULT 'test'` su `strategies`, `trades`, `operation_logs`
- Popolare dati esistenti: `paper=true` → `mode='test'`

**5. ModeFilterMixin (repository layer)**
- Aggiunge `.eq("mode", current_mode)` a ogni query nei repository
- Applicato a `StrategyRepository`, `TradeRepository`

**6. API endpoint `/api/config/mode`**
- `GET` → `{mode: "test"|"live", allow_live: bool}`
- `POST` → cambia modalità, chiama `ExchangeFactory.reconnect()`
- Richiede `ALLOW_LIVE_MODE=True` per passare a LIVE

**7. Frontend — Topbar**
- Mostra "TEST" (giallo/arancione) o "LIVE" (verde) dinamicamente
- Click sul pallino → dropdown con "Switch to LIVE/TEST"
- Conferma obbligatoria per LIVE

**Test:**
- `test_get_mode_returns_test`: GET → `mode="test"`
- `test_switch_to_live_blocked`: senza ALLOW_LIVE_MODE → 403
- `test_switch_to_test`: POST → 200
- `test_exchange_factory_reconnect`: reconnect cambia URL
- `test_filter_applies_to_repositories`: mode filter aggiunto alle query
- `test_topbar_shows_mode`: mock API → TEST/LIVE visibile


--- ARCHIVED ON 2026-05-22 ---

### TASK-800 — Setup Base & Configurazioni
**Status:** Done ✅
**Priorità:** Critica

**Dettagli:**
Aggiungere configurazioni scalping senza frammentare il sistema.

**Piano:**
1. ✅ In `app/config.py`, creare `ScalpingSettings` con 12 parametri scalping + property `settings.scalping`
2. ✅ Aggiunte variabili d'ambiente a `.env` (sezione `# Scalping Module v2.0`)
3. ✅ Test TDD: 30/30 test PASS (default, override via env, type coercion, access via settings)
4. ✅ Rimossa dipendenza da CryptoPanic API (a pagamento) — le news crypto useranno fonti free (CoinGecko News API, Messari, CryptoCompare, NewsAPI, RSS feed)

---

### TASK-801 — Estensione Moduli Core (Indicators, Risk, WS, Exchange)
**Status:** Done ✅
**Priorità:** Critica
**Dipende da:** TASK-800

**Dettagli:**
Estendere i moduli pre-esistenti invece di creare cloni scalping-only.

**Piano:**
1. **Indicatori:** Aggiungere in `app/core/indicators.py` il calcolo `vwap`, `adx` e filtri regime (trend, vola), usando la libreria Pandas esistente.
2. **WebSocket:** Estendere `ConnectionManager` in `app/api/ws.py` aggiungendo metodi `broadcast_scalping_tick`, `broadcast_intel_score`.
3. **Risk Manager:** In `app/execution/risk_manager.py`, aggiungere controlli intraday: `check_max_daily_loss` (soglia -3%) e `check_max_consecutive_losses` (soglia 5).
4. **Exchange:** In `app/execution/exchange.py` (`BinanceExchangeAdapter`), estendere il supporto per piazzare ordini combinati OCO/OTO (se applicabile all'API), o implementare un synthetic OCO usando websockets.

---

### TASK-802 — Database Migrations (Tabelle Separate) [📎 Dettaglio]
**Status:** Done ✅
**Priorità:** Alta

**📎 Dettaglio Piano — Schema DB completo:**
```sql
-- Sessioni di trading
CREATE TABLE scalping_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mode TEXT CHECK (mode IN ('PAPER', 'LIVE', 'BACKTEST')),
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    status TEXT CHECK (status IN ('running', 'paused', 'stopped')),
    started_at TIMESTAMPTZ NOT NULL,
    stopped_at TIMESTAMPTZ,
    total_pnl NUMERIC(12,6) DEFAULT 0,
    trade_count INTEGER DEFAULT 0,
    win_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trade eseguiti (con contesto intelligenza)
CREATE TABLE scalping_trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES scalping_sessions(id),
    symbol TEXT NOT NULL,
    side TEXT CHECK (side IN ('BUY', 'SELL')),
    entry_price NUMERIC(12,6) NOT NULL,
    exit_price NUMERIC(12,6),
    quantity NUMERIC(12,8) NOT NULL,
    pnl NUMERIC(12,6),
    pnl_pct NUMERIC(8,4),
    strategy_type TEXT NOT NULL,
    signal_reason TEXT,
    signal_score NUMERIC(6,2),
    funding_rate_at_entry NUMERIC(10,6),
    fear_greed_at_entry INTEGER,
    cvd_trend_at_entry TEXT,
    entry_time TIMESTAMPTZ NOT NULL,
    exit_time TIMESTAMPTZ,
    status TEXT CHECK (status IN ('open', 'closed', 'cancelled')),
    binance_order_id TEXT
);

-- Decisioni del supervisore AI
CREATE TABLE supervisor_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES scalping_sessions(id),
    action TEXT NOT NULL,
    reason TEXT NOT NULL,
    confidence NUMERIC(4,3),
    market_bias TEXT,
    primary_signal TEXT,
    previous_params JSONB,
    new_params JSONB,
    previous_strategy TEXT,
    new_strategy TEXT,
    decided_at TIMESTAMPTZ DEFAULT NOW()
);

-- Snapshot intelligenza di mercato (storico)
CREATE TABLE market_intel_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol TEXT NOT NULL,
    funding_rate NUMERIC(10,6),
    open_interest NUMERIC(20,2),
    long_pct NUMERIC(5,2),
    short_pct NUMERIC(5,2),
    cvd_trend TEXT,
    fear_greed_value INTEGER,
    fear_greed_label TEXT,
    signal_score NUMERIC(6,2),
    signal_bias TEXT,
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_intel_symbol_time ON market_intel_snapshots(symbol, recorded_at DESC);

-- Opportunità rilevate
CREATE TABLE opportunities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source TEXT NOT NULL,
    category TEXT NOT NULL,
    urgency TEXT NOT NULL,
    scalping_opportunity BOOLEAN DEFAULT FALSE,
    title TEXT NOT NULL,
    action TEXT,
    symbol TEXT,
    expected_volatility TEXT,
    time_sensitive BOOLEAN DEFAULT FALSE,
    url TEXT,
    raw_content TEXT,
    content_hash TEXT UNIQUE,
    classified_by_ai BOOLEAN DEFAULT FALSE,
    user_action TEXT CHECK (user_action IN ('watched', 'ignored', 'acted')),
    detected_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_opp_urgency_time ON opportunities(urgency, detected_at DESC);
CREATE INDEX idx_opp_symbol ON opportunities(symbol) WHERE symbol IS NOT NULL;
```

**⚠️ IMPORTANTE:** Non dimenticare di eseguire fisicamente le migrazioni Supabase (es. `supabase db push` o via UI SQL) per non far fallire le API in produzione!

**Dettagli:**
Creare le tabelle dedicate per non inquinare il logging swing.

**Piano:**
1. Nuova tabella `scalping_sessions` (id, status, start_time, end_time, daily_pnl).
2. Nuova tabella `scalping_trades` (id, session_id, pair, side, entry_price, exit_price, pnl, score_at_entry).
3. Tabelle metriche IA: `intel_snapshots`, `supervisor_decisions`.
4. Aggiornare `schemas.py` o creare `app/scalping/schemas.py` basandosi su questi campi.
5. Tabella `opportunities` per l'Opportunity Monitor (TASK-810).

---

### TASK-803 — Binance Live WS Client (Feed Dati) [📎 Dettaglio]
**Status:** Done ✅
**Priorità:** Alta

**📎 Dettaglio Piano:**
- Flussi WS Binance: `wss://stream.binance.com/ws/<symbol>@kline_1m` (candele), `<symbol>@trade` (trades per CVD)
- Emettere eventi asincroni consumati da `TickProcessor`
- Test su Testnet prima di Live

**Dettagli:**
L'engine swing usa REST. Lo scalping richiede uno stream in tempo reale.

**Piano:**
1. Creare `app/scalping/engine/ws_client.py`.
2. Implementare un client basato su `websockets` per ascoltare il kline stream (1s o 1m) e il trade stream di Binance Testnet/Live.
3. Emettere eventi asincroni che il `TickProcessor` potrà consumare.

---

### TASK-804 — Intelligence Layer & Signal Scoring [📎 Dettaglio]
**Status:** Done ✅
**Priorità:** Media

**📎 Fonti dati implementate:**

| Fonte | Dati | Endpoint | Frequenza | Costo |
|---|---|---|---|---|
| **Binance Futures** | Funding Rate | `/fapi/v1/fundingRate` | Ogni 8h | Gratuito |
| **Binance Futures** | Open Interest | `/fapi/v1/openInterest` | Real-time | Gratuito |
| **Binance Futures** | Long/Short Ratio | `/futures/data/globalLongShortAccountRatio` | 5min | Gratuito |
| **WS Binance** | CVD (da trade stream) | `<symbol>@trade` | Real-time | Gratuito |
| **Alternative.me** | Fear & Greed | `https://api.alternative.me/fng/` | 1/giorno | Gratuito |
| ✅ **Blockchain.com** | On-chain (active addr, exchange volume) | `https://api.blockchain.info/charts/n-unique-addresses`, `/charts/exchange-volume` | 1h | Gratuito (no key) |
| ✅ **Blockchair** | On-chain (stats, whale tx) | `https://api.blockchair.com/bitcoin/stats`, `/bitcoin/transactions?q=output_total(usd).gt(1000000)` | On demand | Gratuito (no key) |
| ✅ **Dune Analytics** | On-chain SQL custom | `POST /api/v1/query/{query_id}/execute`, `GET /api/v1/execution/{id}/results` | On demand | `DUNE_API_KEY` in env |
| ✅ **CryptoCompare** | News feed | `https://min-api.cryptocompare.com/data/v2/news/?lang=EN` | On demand | `CRYPTOCOMPARE_API_KEY` in env |
| ✅ **NewsAPI** | News mainstream (backup) | `https://newsapi.org/v2/everything?q=crypto+bitcoin` | 100 req/giorno | `NEWSAPI_API_KEY` in env |
| ✅ **Whale Alert RSS** | Whale movements real-time | `https://whale-alert.io/rss` | Real-time | Gratuito (no key) |

**Componenti implementati in `app/scalping/intelligence/collectors/`:**
| File | Classe | Descrizione |
|---|---|---|
| `funding_rate.py` | `FundingRateCollector` | Funding rate Binance Futures con interpretazione (±0.05%, ±0.10%) e score (-25 a +25) |
| `open_interest.py` | `OpenInterestCollector` | Open Interest Binance Futures con score (-15 a +15) |
| `long_short_ratio.py` | `LongShortRatioCollector` | Long/Short ratio Binance con score contrarian (-15 a +15) |
| `cvd_calculator.py` | `CVDCalculator` | Cumulative Volume Delta in tempo reale da trade stream WS con trend detection e score (-15 a +15) |
| `fear_greed.py` | `FearGreedCollector` | Fear & Greed Index da Alternative.me con classificazione e score (-10 a +10) |
| `onchain.py` | `OnChainCollector` | [COMPLETATO] Blockchain.com + Blockchair + Dune Analytics |
| `sentiment.py` | `SentimentCollector` | [COMPLETATO] CryptoCompare + NewsAPI news feed |
| `whale.py` | `WhaleCollector` | [COMPLETATO] Whale Alert RSS + Blockchair whale tx filter |

**📎 SignalScoreEngine (`app/scalping/intelligence/signal_score_engine.py`):**
- Pesi: `funding_rate` (0.25), `cvd` (0.25), `open_interest` (0.15), `long_short_ratio` (0.15), `fear_greed` (0.10), `onchain` (0.10)
- Score finale normalizzato -100 a +100 con bias (`bullish`/`bearish`/`neutral`)
- Breakdown dettagliato per categoria
- Tradeable solo se |score| ≥ 30

**📎 SignalAggregator (`app/scalping/engine/signal_aggregator.py`):**
- Blocca BUY se score bearish / overleveraged
- Blocca SELL se score bullish
- Blocca trade se score neutral o insufficiente
- Combined confidence calcolata come max tra confidence intelligence e confidence tecnica in caso di allineamento, 0 in caso di conflitto

**📎 Modelli Pydantic (`app/scalping/models/intelligence.py`):**
| Modello | Campi |
|---|---|
| `FundingRate` | symbol, rate (Decimal), timestamp, next_funding_time |
| `OpenInterest` | symbol, value_usd (Decimal), asset, timestamp |
| `LongShortRatio` | symbol, long_pct, short_pct, timestamp → ratio property |
| `CVDData` | symbol, cvd, buy_volume, sell_volume, trend, timestamp |
| `FearGreedData` | value (int), label, timestamp |
| `SignalScore` | total (float), bias, tradeable, confidence, breakdown (dict) |
| `MarketIntelSnapshot` | funding_rate, open_interest, long_short_ratio, cvd, fear_greed, signal_score |
| `ExecutionDecision` | execute (bool), reason (Optional[str]), confidence (float) |

**📎 Test implementati (`tests/scalping/`):**
| File | # Test | Copertura |
|---|---|---|
| `test_funding_rate.py` | 11 | collect success, negative rate, empty, HTTP error, interpret_rate (5 soglie), rate_to_score (5 casi) |
| `test_open_interest.py` | 7 | collect success, HTTP error, oi_to_score (5 casi) |
| `test_long_short_ratio.py` | 7 | collect success, empty, HTTP error, ratio_to_score (4 casi) |
| `test_cvd_calculator.py` | 13 | CVD zero, buy/sell trades, multiple, snapshot con trend, reset, score (4 casi) |
| `test_fear_greed.py` | 12 | collect success, extreme greed, empty, HTTP error, classify (5 bande), fng_to_score (5 casi) |
| `test_intelligence_models.py` | 17 | Tutti i modelli Pydantic: valid, frozen, missing, edge cases |
| `test_signal_score_engine.py` | 5 | Weights sum, all keys, all collectors fail, bullish/bearish scenario, with CVD |
| `test_signal_aggregator.py` | 11 | Block/allows buy/sell, neutral/none, low confidence, combined confidence |
| **Totale** | **83** | +33 test esistenti WS client = **116 totali** |

**Risultato finale:**
```
======================= 116 passed, 2 warnings in 9.64s =======================
```

---

### TASK-805 — Scalping Engine & TickProcessor [📎 Dettaglio]
**Status:** Done ✅  
**Completato:** 2026-05-22
**Priorità:** Critica
**Dipende da:** TASK-801, TASK-803, TASK-804

**📎 Dettaglio Piano — ExecutionLoop:**
```python
class ExecutionLoop:
    """Main loop scalping. Gira ogni 500ms-2s. Usa moduli core per order_executor e risk_manager."""
    
    async def _process_candle(self, candle):
        self.candle_buffer.add(candle)
        if not self.candle_buffer.is_ready():
            return
        
        candles = self.candle_buffer.get()
        indicators = self.indicators_core.calculate(candles)  # app/core/indicators.py
        
        # 1. Regime detection
        regime = self.regime_detector.detect(candles, indicators)
        
        # 2. Strategy selection
        strategy = self.strategy_selector.select(regime)
        
        # 3. Signal generation (tecnico = filtro timing)
        signal = strategy.evaluate(candles, indicators)
        
        # 4. Risk check (usa app/execution/risk_manager.py)
        risk_result = self.risk_manager_core.check_pre_trade(self.capital)
        if not risk_result.allowed:
            return
        
        # 5. Esegui se segnale valido + intelligence conferma
        if signal.type == 'BUY' and not self.position_manager.has_open():
            order = await self.exchange_core.buy(signal)  # app/execution/exchange.py
        
        elif signal.type in ('SELL', 'CLOSE'):
            if self.position_manager.has_open():
                order = await self.exchange_core.close()
                trade = await self.position_manager.close(order)
                self.risk_manager_core.on_trade_closed(trade)
        
        # 6. WS event verso frontend (app/api/ws.py)
        await self._emit_market_update(candle, signal, indicators)
```

**Dettagli:**
Il cuore del modulo scalping. Processa ogni tick live.

**Piano:**
1. Creare `TickProcessor` / `ExecutionLoop` in `app/scalping/engine/`: riceve dati da `ws_client.py`.
2. Ad ogni tick o chiusura candela 1m:
   - Chiama `SignalScoreEngine` (score intelligence).
   - Chiama `RegimeDetector` + `StrategySelector` + strategia (segnale tecnico).
   - Chiama `SignalAggregator` per combinare i due.
   - Se ok, chiama `RiskManager` core (`app/execution/risk_manager.py`).
   - Se ok, invia ordine via `BinanceExchangeAdapter` core (`app/execution/exchange.py`).
3. Broadcast immediato al frontend via `ConnectionManager` core (`app/api/ws.py`).

---

### TASK-806 — AI Supervisor (Integrazione moduli core esistenti)
**Status:** Done ✅
**Completato:** 2026-05-25
**Priorità:** Bassa

**Dettagli:**
Integrazione LLM per leggere news ed emettere bias correttivi a costo quasi zero.

**Implementazione completata:**
1. ✅ Esteso `app/ai/supervisor_context.py` per includere intelligence snapshot (funding rate, CVD, OI, Fear&Greed).
2. ✅ Arricchito `app/ai/eval_parser.py` per parsare i campi aggiuntivi (`market_bias`, `primary_signal`).
3. ✅ Creato `app/scalping/supervisor/supervisor_client.py` con system prompt gerarchia segnali v2.0.
4. ✅ Creato `app/scalping/supervisor/parameter_updater.py`: applica parametri aggiornati all'ExecutionLoop.
5. ✅ Creato `app/scalping/supervisor/supervisor_scheduler.py`: task periodico ogni 10 minuti.
6. ✅ Aggiornato `app/scalping/models/supervisor.py` con modello `SupervisorDecision`.
7. ✅ Test TDD: 20 nuovi test per supervisor (12 per scheduler/updater, 8 per parser).
8. ✅ Tutti i 163 test scalping passanti.

---

### TASK-807 — Scheduler Centralizzato
**Status:** Done ✅
**Completato:** 2026-05-25
**Priorità:** Alta
**Dipende da:** TASK-805 ✅

**Risultati:**
- 4 nuovi job scalping registrati in `app/scheduler/scalping_jobs.py`:
  - `intelligence_snapshot_job` (ogni 60s): snapshot SignalScoreEngine → Supabase
  - `funding_rate_update_job` (ogni 60min): funding rate BTCUSDT/ETHUSDT
  - `supervisor_check_job` (ogni 10min): `SupervisorScheduler.run_once()`
  - `session_health_job` (ogni 30s): heartbeat sessione
- 4 flag di abilitazione in `ScalpingSettings` (default: `True`)
- Registrazione condizionale in `setup_scheduler()` basata su `SCALPING_DEFAULT_MODE`
- Nuovo metodo pubblico `run_once()` su `SupervisorScheduler`
- 15 test: 14 verde + 1 con `importlib.reload`

---

### TASK-808 — Backtest Engine
**Status:** Done ✅
**Completato:** 2026-05-25
**Priorità:** Alta
**Dipende da:** TASK-804

**Dettagli:**
Motore di backtest per validare le strategie scalping su dati storici prima del go-live.

**Implementazione completata:**
1. `HistoricalLoader` in `app/scalping/data/historical_loader.py`: scarica OHLCV 1m, funding rate, OI storici da Binance REST API.
2. `BacktestEngine` in `app/scalping/backtest/backtest_engine.py`: itera candele storiche, esegue ciclo completo con flag `use_intelligence` per confronto intelligence vs tecnico-only.
3. `PerformanceCalculator` in `app/scalping/backtest/performance_calculator.py`: win rate, drawdown, Sharpe ratio, profit factor, correlazione signal_score → outcome.
4. `ReportGenerator` in `app/scalping/backtest/report_generator.py`: report JSON con confronto with/without intelligence.
5. Modelli Pydantic: `BacktestConfig`, `BacktestResult`, `SimulatedTrade`.
6. Endpoint `POST /scalping/backtest/run` e `GET /scalping/backtest/{id}/result`.
7. 10+ test su sequenze candele mock - tutti passanti.

---
