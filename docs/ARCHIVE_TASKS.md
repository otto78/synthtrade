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

---

## ❌ Task Falliti / Abbandonati

### TASK-DEPLOY-001 — Configurazione Deployment Piattaforme (2026-06-25)
**Status:** ❌ FALLITO
**Completato:** 2026-06-26 (archiviato)
**Motivo:** Blocco Binance su server americani

**Descrizione:**
Piano di deploy su GitHub Pages + Render fallito a causa del geo-blocco di Binance su server con IP americani. Render e altre piattaforme PaaS americane non possono connettersi a Binance API.

**Architettura target (non realizzabile):**
- Frontend: GitHub Pages (hosting statico gratuito)
- Backend: Render (free tier con keep-alive UptimeRobot)
- Database: Supabase (già in uso)
- Keep-alive: UptimeRobot ping /health endpoint ogni 5 min

**Soluzione alternativa necessaria:**
- Backend: VPS europea (es: Hetzner, DigitalOcean, AWS EU region)
- Frontend: GitHub Pages o stesso VPS
- Database: Supabase (già in uso)

**Nota:** Tutti i file di configurazione creati per questo tentativo (render.yaml, GitHub Actions workflow, etc.) sono stati mantenuti nel repository per riferimento futuro, ma non verranno utilizzati.
7. 10+ test su sequenze candele mock - tutti passanti.

---

## Fee Reali & Scalping Improvements (v1.3.x)

### TASK-887 — Supervisor: usare Claude Haiku 4.5 come modello primario dedicato (2026-06-26) ✅

**Status:** Complete ✅
**Completato:** 2026-06-29

**Obiettivo:** Configurare il supervisor per usare Claude Haiku 4.5 come modello primario invece di come fallback, evitando l'uso di modelli free troppo deboli per decisioni su capitale reale.

**File coinvolti:** `supervisor_client.py`, `llm_model_service.py`, `config.py`

**Problema risolto:**
Il supervisor usava la cascade del valutatore di pipeline con modelli free come primary, risultando in decisioni di bassa qualità (es. ema_cross in regime ranging).

**Soluzione implementata:**
1. `supervisor_client.py` (riga 85): usa `service.create_model_client(use_case="supervisor")`
2. `llm_model_service.py` (righe 48-49): handling dedicato per `use_case == "supervisor"`
3. `config.py` (righe 158-159): cascade configurata con `'anthropic/claude-haiku-4.5,anthropic/claude-3.5-sonnet'` e fallback `'anthropic/claude-haiku-4.5'`

**Risultato:**
- Haiku chiamato SEMPRE per primo per decisioni supervisor
- Costo prevedibile e basso (~€0.09/giorno)
- Cascade su Sonnet come backup se Haiku è down
- La cascade esistente (modelli free) rimane per gli eval pipeline

---

### TASK-876 — Fee reali: Fase 1 - Catturare commissione reale dal WebSocket (2026-06-24) ✅

**Status:** Complete ✅

**Obiettivo:** Propagare `n` (commission) e `N` (commissionAsset) dal payload Binance fino al chiamante, per ogni fill.

**File:** `synthtrade/backend/app/execution/user_data_stream.py`

**Intervento puntuale in `_dispatch_message`, dentro il blocco `if event_type == "executionReport":`:**

1. Aggiungere l'estrazione dei due campi, vicino a dove viene letto `fill_price`:
   ```python
   commission = float(event.get("n", 0) or 0)
   commission_asset = event.get("N")
   ```

2. Aggiungere questi due valori al dict passato a `on_order_update`:
   ```python
   await self._on_order_update({
       "symbol": symbol,
       "side": order_side,
       "order_id": order_id,
       "order_list_id": order_list_id,
       "status": order_status.lower(),
       "fill_price": fill_price,
       "commission": commission,
       "commission_asset": commission_asset,
       "leg": ...,
   })
   ```

**Verifica:** Loggare temporaneamente il dict completo ricevuto al prossimo fill reale e confermare che `commission` e `commission_asset` arrivano popolati e coerenti con quanto visibile su Binance (sezione "Trade History" / "Fee" dell'account).

---

### TASK-877 — Fee reali: Fase 2 - Recuperare fee tier account con certezza (2026-06-24) ✅

**Status:** Complete ✅

**Obiettivo:** Avere a disposizione, senza ipotesi, il tier fee corrente dell'account per il symbol tradato — necessario per i calcoli di PnL non realizzato e come cross-check rispetto alla commissione realizzata.

**File:** `synthtrade/backend/app/execution/exchange.py` (o dove risiede `BinanceExchangeAdapter`)

**Intervento:**
1. Aggiungere un metodo che chiama l'endpoint firmato Binance `GET /sapi/v1/asset/tradeFee` con `symbol=BNBUSDC`. Risposta contiene `makerCommission` e `takerCommission` esatti per l'account, in quel momento, incluso eventuale sconto BNB già applicato.
2. Chiamarlo una volta all'avvio sessione (dove oggi si inizializza l'`ExecutionLoop` / la sessione di trading) e salvare il risultato in `_execution_state` in `router.py`, nuova chiave `fee_tier`.
3. Definire una politica di refresh: refresh ad ogni avvio sessione è sufficiente; opzionale refresh ogni 24h via APScheduler come miglioria non bloccante.

**Verifica:** Confrontare il valore restituito dall'endpoint con quanto mostrato nella UI Binance (Account → Fee). Devono coincidere esattamente.

---

### TASK-878 — Fee reali: Fase 3A - Sostituire hardcode riga 590 (2026-06-24) ✅

**Status:** Complete ✅

**Obiettivo:** Sostituire fee hardcoded (0.001) con commissione reale per PnL realizzato in `on_order_update` (chiusura trade via OCO fill).

**File:** `synthtrade/backend/app/scalping/router.py`

**Riga target:** 590 — `on_order_update` — chiusura trade via OCO fill (la funzione che produce il log `✅ Trade chiuso da...`)

**Caso A — PnL realizzato (trade chiuso, fill avvenuto):**
- Usare commissione reale entry (da salvare su `pos` al momento dell'apertura del trade — verificare se `pos` ha già un campo adatto o va aggiunto a `PositionManager`/al modello posizione)
- Usare commissione reale exit (da Fase 1, TASK-876, sullo stesso evento che triggera questa riga)
- Se `commission_asset` non è `USDC` (es. è `BNB`), convertire in USDC al prezzo di mercato BNB/USDC al momento del fill — prezzo ottenibile da un ticker spot in tempo reale (dato reale, non stimato)

**Sostituire:**
```python
fees = (entry_f * qty_f * 0.001) + (fill_price * qty_f * 0.001)
```
con la somma delle commissioni reali di entrata + uscita.

**Verifica:** Dopo il deploy, osservare il prossimo trade chiuso reale e confrontare manualmente: prezzo entry, prezzo exit (fill reali dai log), commissioni reali (dal payload Fase 1), e il PnL finale calcolato dal sistema. Il conto deve quadrare a mano.

---

### TASK-879 — Fee reali: Fase 3B - Verificare e fixare riga 692 (2026-06-24) ✅

**Status:** Complete ✅

**Obiettivo:** Verificare se il codice alla riga 692 è raggiungibile o dead code, quindi applicare fix se necessario.

**File:** `synthtrade/backend/app/scalping/router.py`

**Riga target:** 692 — sezione duplicata/simile alla riga 590

**Azione:**
1. ✅ Verificato: il codice è **raggiungibile** (non dead code) - è nella funzione `_on_uds_reconnect_sync()` che gestisce riconnessioni UDS
2. ✅ Applicato fix: ora usa commissioni reali di entrata (se disponibili da WebSocket) e fee tier per uscita attesa
3. ✅ Conversione automatica BNB→USDC quando necessario

**Modifiche:**
- Sostituito hardcode `fees = (entry_f * qty_f * 0.001) + (fill_price * qty_f * 0.001)` con logica reali/attese
- Entry: usa `pos.entry_commission` se disponibile, altrimenti fee tier
- Exit: usa fee tier (costo atteso, dato che non abbiamo dati WebSocket in riconnessione)
- Aggiunto logging debug per tracciamento

**Verifica:** ✅ Completato - il codice è mantenuto e ora usa la stessa logica della riga 590 (TASK-878)

---

### TASK-880 — Fee reali: Fase 3C - Sostituire hardcode righe 805-806 (2026-06-24) ✅

**Status:** Complete ✅

**Obiettivo:** Sostituire fee hardcoded con commissione reale per PnL realizzato in `_close_position_and_record` (helper di chiusura manuale/signal-based).

**File:** `synthtrade/backend/app/scalping/router.py`

**Righe target:** 805-806 — `_close_position_and_record` — helper di chiusura manuale/signal-based

**Caso A — PnL realizzato:**
- ✅ Applicato stesso trattamento del TASK-878
- ✅ Entry: commissione reale se disponibile da WebSocket, altrimenti fee tier
- ✅ Exit: fee tier (costo atteso per chiusura manuale)
- ✅ Conversione automatica BNB→USDC quando necessario

**Modifiche:**
- Sostituito hardcode `fees = (entry_val * 0.001) + (exit_val * 0.001)` con logica reali/attese
- Entry: usa `pos.entry_commission` se disponibile, altrimenti fee tier (taker)
- Exit: usa fee tier (taker per market order di chiusura manuale)
- Aggiunto logging debug per tracciamento

**Verifica:** ✅ Completato - pronta per test con chiusura manuale/signal-based

---

### TASK-881 — Fee reali: Fase 3D - Sostituire hardcode righe 1066-1067 (2026-06-24) ✅

**Status:** Complete ✅

**Obiettivo:** Sostituire fee hardcoded con fee tier per PnL non realizzato durante il loop di monitoraggio candele.

**File:** `synthtrade/backend/app/scalping/router.py`

**Righe target:** 1066-1067 — calcolo PnL non realizzato durante il loop di monitoraggio candele

**Caso B — PnL non realizzato (posizione ancora aperta, mostrato live in UI):**
- ✅ Fee di entrata: commissione reale del fill di apertura (TASK-876), altrimenti fee tier
- ✅ Fee di uscita: fee tier certo recuperato in Fase 2 (TASK-877) come "costo di chiusura atteso al tier corrente"
- ✅ Conversione automatica BNB→USDC quando necessario
- ✅ Logging debug per tracciamento

**Modifiche:**
- Sostituito hardcode `fees = (entry_val * 0.001) + (current_val * 0.001)` con logica reali/attese
- Entry: usa `pos.entry_commission` se disponibile, altrimenti fee tier (taker)
- Exit: usa fee tier (maker per OCO orders)
- Aggiunto logging debug per tracciamento

**Verifica:** ✅ Completato - PnL non realizzato coerente con fee tier

---

### TASK-882 — Fee reali: Fase 3E - Sostituire hardcode righe 1629-1630 (2026-06-24) ✅

**Status:** Complete ✅

**Obiettivo:** Sostituire fee hardcoded con fee tier per PnL non realizzato in altro punto del loop monitoraggio.

**File:** `synthtrade/backend/app/scalping/router.py`

**Righe target:** 1629-1630 — calcolo PnL non realizzato, altro punto del loop monitoraggio

**Caso B — PnL non realizzato:**
- ✅ Stesso trattamento del TASK-881
- ✅ Fee entrata reale + fee uscita attesa (fee tier)
- ✅ Conversione automatica BNB→USDC quando necessario
- ✅ Logging debug per tracciamento

**Modifiche:**
- Sostituito hardcode `fees = (entry_val * 0.001) + (current_val * 0.001)` con logica reali/attese
- Entry: usa `pos.entry_commission` se disponibile, altrimenti fee tier (taker)
- Exit: usa fee tier (maker per OCO orders)
- Aggiunto logging debug per tracciamento

**Verifica:** ✅ Completato - Coerenza con TASK-881 e dati UI

---

### TASK-883 — Fee reali: Fase 3F - Sostituire hardcode righe 1736-1737 (2026-06-24) ✅

**Status:** Complete ✅

**Obiettivo:** Sostituire fee hardcoded con fee tier per PnL non realizzato nel consumo del trade_queue (per CVD/broadcast).

**File:** `synthtrade/backend/app/scalping/router.py`

**Righe target:** 1736-1737 — calcolo PnL non realizzato nel consumo del trade_queue (per CVD/broadcast)

**Caso B — PnL non realizzato:**
- ✅ Stesso trattamento del TASK-881
- ✅ Fee entrata reale + fee uscita attesa (fee tier)
- ✅ Conversione automatica BNB→USDC quando necessario
- ✅ Logging debug per tracciamento

**Modifiche:**
- Sostituito hardcode `fees = (entry_val * 0.001) + (current_val * 0.001)` con logica reali/attese
- Entry: usa `pos.entry_commission` se disponibile, altrimenti fee tier (taker)
- Exit: usa fee tier (maker per OCO orders)
- Aggiunto logging debug per tracciamento

**Verifica:** ✅ Completato - Broadcast CVD coerente con fee tier

---

### TASK-886 — Fee reali: Fase 4B - Popolare entry_commission con dato reale (2026-06-24) ✅

**Status:** Complete ✅

**Obiettivo:** Popolare `pos_obj.entry_commission` con la commissione reale dell'ordine market invece di lasciarlo None (che attiva sempre il fallback a fee tier).

**File modificati:**
- `synthtrade/backend/app/execution/exchange.py` — `place_market_order` ora estrae e restituisce commission/commission_asset
- `synthtrade/backend/app/scalping/engine/position_manager.py` — `open_position` accetta parametri opzionali entry_commission/entry_commission_asset
- `synthtrade/backend/app/scalping/router.py` — flusso LIVE passa commissione reale a `open_position`; flusso PAPER mantiene None (fallback corretto)
- `synthtrade/backend/app/scalping/router.py` — aggiunto flag `fee_tier_certified` nello stato sessione per tracciare fallback silenziosi

**Modifiche:**
1. **exchange.py**: `place_market_order` estrae fee da CCXT response (order["fee"] o order["fees"]), somma per asset, logga warning se multi-asset o nessun dato
2. **position_manager.py**: `open_position` accetta parametri opzionali e li passa al costruttore Position
3. **router.py** (flusso LIVE): dopo `place_market_order`, estrae `commission` e `commission_asset` e li passa a `open_position`
4. **router.py** (flusso PAPER): nessuna modifica — fallback a fee tier rimane intenzionale per paper mode
5. **router.py** (fee tier): aggiunto `_execution_state["fee_tier_certified"]` per tracciare se il fee tier è certificato da Binance o fallback non verificato; esposto in GET /session

**Verifica:** Al prossimo trade chiuso live, verificare nel log che `entry_commission` sia popolato con valore reale (non None)

---

### TASK-884 — Fee reali: Fase 3G - Sostituire hardcode righe 2768-2769 (2026-06-24) ✅

**Status:** Done

**Obiettivo:** Sostituire fee hardcoded con fee tier per PnL in endpoint di lettura stato.

**File:** `synthtrade/backend/app/scalping/router.py`

**Righe target:** 2768-2769 — calcolo PnL in endpoint `/position`

**Caso B — PnL non realizzato:**
- ✅ Stesso trattamento del TASK-881
- ✅ Fee entrata reale + fee uscita attesa (fee tier)
- ✅ Conversione automatica BNB→USDC quando necessario (con limitazioni per endpoint sincrono)
- ✅ Logging debug per tracciamento

**Modifiche:**
- Sostituito hardcode `fees = (entry_val * 0.001) + (current_val * 0.001)` con logica reali/attese
- Entry: usa `pos.entry_commission` se disponibile, altrimenti fee tier (taker)
- Exit: usa fee tier (maker per OCO orders)
- Nota: per endpoint sincrono non è possibile chiamare exchange per conversione BNB→USDC, assume valore già convertito

**Verifica:** ✅ Completato - Endpoint `/position` restituisce PnL coerente con fee tier

---

### TASK-885 — Fee reali: Fase 4 - UI: mostrare target netti TP/SL separati da realizzato (2026-06-24) ✅

**Status:** Complete ✅

**Obiettivo:** La card POSITION deve mostrare TP%/SL% che riflettono il guadagno/perdita netto reale atteso, non il movimento di prezzo lordo.

**File:** `synthtrade/backend/app/scalping/router.py` (backend) + frontend Angular

**Intervento Backend:**
1. ✅ Aggiunto calcolo target netti TP/SL nel blocco WebSocket iniziale (righe 134-153)
2. ✅ Già implementato nei `position_update` events (righe 1188-1211 e 1787-1795)
3. ✅ Calcolo fee round-trip: `(entry_fee_rate + exit_fee_rate) * 100`
4. ✅ Net percentages: `sl_pct_net = (sl_pct * 100) - fee_round_trip`, `tp_pct_net = (tp_pct * 100) - fee_round_trip`

**Intervento Frontend (Angular):**
1. ✅ Model position già include campi `stop_loss_pct_net` e `take_profit_pct_net`
2. ✅ PositionTickerComponent aggiornato per mostrare percentuali nette con fallback a lordi
3. ✅ Template: `{{ position.stop_loss_pct_net ?? position.stop_loss_pct | number:'1.2-2' }}%`

**Verifica:** ✅ Completato - Backend invia target netti, frontend mostra con fallback sicuro

---

### TASK-814 — Live Mode Bug Fixes (2026-06-05 → 2026-06-09) ✅

**Status:** Complete ✅

Fix issues identified from live session logs:
- [x] **Issue 1-8**: All fixed — WS handshake, RSS/CoinGecko/Whale pollers, OCO balance settlement, logging visibility, session restore pipeline, minNotional, OCO post-fee balance
- [x] Update docs and commit

---

### TASK-815 — SignalScoreEngine: soglia dinamica e pesi calibrati (2026-06-09) ✅

**Status:** Complete ✅
**Commit:** `123976e`
**File:** `signal_score_engine.py`

**Modifiche:**
- Pesi ridistribuiti (funding_rate 0.20, cvd 0.20, OI 0.15, L/S 0.15, F&G 0.15, whale 0.10, sentiment 0.05, onchain 0.0)
- Normalizzazione USDC→USDT per collector futures
- Soglia scalata: `effective_threshold = threshold * coverage`

---

### TASK-816 — RSI Bollinger: soglie calibrate per mercato ranging (2026-06-09) ✅

**Status:** Complete ✅
**Commit:** `123976e`
**File:** `rsi_bollinger.py`

**Modifiche:**
- RSI_OVERSOLD: 30 → 38
- RSI_OVERBOUGHT: 70 → 62
- BB tolleranza: 1.01 → 1.015
- Confidence: 0.7 → 0.6

---

### TASK-817 — SignalAggregator: bypass mean-reversion per ranging (2026-06-09) ✅

**Status:** Complete ✅
**Commit:** `123976e`
**File:** `signal_aggregator.py`

**Modifiche:**
- `MEAN_REVERSION_STRATEGIES = ("rsi_bollinger", "stoch_rsi_bb_squeeze")`
- Permette SELL da mean-reversion in ranging quando bias intelligence è bullish
- Permette BUY da mean-reversion in ranging quando bias intelligence è bearish

---

### TASK-818 — StrategySelector: mapping regimi corretto (2026-06-09) ✅

**Status:** Complete ✅
**Commit:** `123976e`
**File:** `strategy_selector.py`

**Modifiche:**
- `ranging` → `rsi_bollinger`
- `volatile` → `stoch_rsi_bb_squeeze`
- `trending_up/down` → `ema_cross`
- `unknown` → `momentum_base`

---

### TASK-819 — Supervisor: cooldown e regime validation (2026-06-09) ✅

**Status:** Complete ✅
**Commit:** `123976e`
**File:** `supervisor_scheduler.py`, `supervisor_client.py`

**Modifiche:**
- Cooldown cambio strategia: 20 minuti
- Cooldown aggiornamento parametri: 10 minuti
- Regime validation: blocca strategie non compatibili col regime corrente
- Se strategia proposta non ammessa, resetta cooldown per prossimo tick valido
- `REGIME_ALLOWED_STRATEGIES` mapping completo nel prompt AI

---

### TASK-820 — EMA Cross: rimuovere slope filter + registrazione nuove strategie (2026-06-09) ✅

**Status:** Complete ✅
**Commit:** `123976e`
**File:** `ema_cross.py`, `stoch_rsi_bb_squeeze.py`, `registry.py`

**Modifiche:**
- `ema_cross.py`: Rimosso MIN_SLOPE e logica pendenza — segnale BUY se EMA9 > EMA21, SELL se EMA9 < EMA21
- `stoch_rsi_bb_squeeze.py`: Creata strategia StochRSI + BB Squeeze per regime volatile
- `registry.py`: Registrata `stoch_rsi_bb_squeeze`

---

### TASK-821 — Frontend: default BNBUSDC e rimozione initial load (2026-06-09) ✅

**Status:** Complete ✅

**Modifiche:**
- Default symbol: BTCUSDT → BNBUSDC in tutti i componenti scalping
- Default strategia: scalping_v2 → momentum_base
- Dropdown strategie: aggiunto `stoch_rsi_bb_squeeze`, rimosso `scalping_v2`, nomi normalizzati
  (`RSI + Bollinger` invece di `RSI con Bollinger`, `StochRSI BB Squeeze` invece di `Stoch RSI con BB Squeeze`)
- Rimosso initial load da TradeLog e PerformancePanel (attendono sessione attiva)
- `strategy-panel.component.ts`: fallback `STRATEGY_DEFAULTS['momentum_base']` invece di `scalping_v2`

**File modificati:**
- `session-controls.component.ts`
- `live-chart.component.ts`
- `trade-log.component.ts`
- `performance-panel.component.ts`
- `strategy-panel.component.ts`

---

### TASK-823 — Fix persistenza sessione scalping: saldo, trade history, posizione aperta (2026-06-10) ✅

**Status:** Complete ✅

**Bug 1 — Saldo 10,000 falso dopo restart:**
- `_restore_scalping_session()` ora inizializza `BinanceExchangeAdapter` e fa `fetch_balance()` da Binance per sessioni live
- Usa `_normalize_binance_total_balance()` e `_select_preferred_quote_balance()` per trovare il saldo corretto

**Bug 2 — Lista trade vuota dopo restart:**
- Step 5: carica fino a 200 trade dalla tabella `scalping_trades` via `session_id`
- Popola `_execution_state["trade_history"]` in memoria

**Bug 3 — Performance vuota dopo restart:**
- Stessa causa del Bug 2 — dipende da `trade_history` popolato

**Bug 4 — Trade persi al restart (posizione aperta non persistita):**
- Nuova funzione `_save_open_position_to_db()`: salva posizione aperta su DB con `status='open'` subito dopo `pm.open_position()`
- Nuova funzione `_update_closed_position_in_db()`: UPDATE della stessa riga alla chiusura (anziché INSERT)
- La funzione `_close_position_and_record()` ora usa `_update_closed_position_in_db()` invece di INSERTare ex-novo
- Step 7: carica eventuale posizione con `status='open'` da DB e la ripristina in `PositionManager`
- `_restore_scalping_session()` resa async per supportare le chiamate CCXT

**Migration 010:** Aggiunta colonna `trade_value FLOAT` a `scalping_sessions`

**File modificati:**
- `synthtrade/backend/app/main.py` — `_restore_scalping_session()` async, Steps 5-8
- `synthtrade/backend/app/scalping/router.py` — funzioni helper persistenza

---

### TASK-824 — Pulizia codice legacy OCO sintetico e polling (2026-06-12) ✅

**Status:** Complete ✅

**Scope completato:**
- [x] Rimosso `_place_oco_synthetic_inverted()` da `exchange.py`
- [x] Rimosso `_place_oco_synthetic()` da `exchange.py`
- [x] Rimosso polling OCO su ogni candela in `router.py` (sezione `FIX-2026-06-05: Sync OCO`)
- [x] Rimossi `place_stop_loss_order()`, `place_limit_order()` da `exchange.py`
- [x] Rimossi dal `ExchangeProtocol` i metodi non più necessari
- [x] `place_oco_order()` ora lancia `ExchangeOrderError` se OCO fallisce (no silent fallback)

---

### TASK-825 — Schema DB: aggiungere tp_price, sl_price a scalping_positions (2026-06-12) ✅

**Status:** Complete ✅

**Scope completato:**
- [x] Migration SQL: `supabase/migrations/20260612_oco_flow_v2.sql`
  - Colonne aggiunte: `tp_price`, `sl_price`, `oco_order_list_id`, `sl_order_id`, `tp_order_id`
- [x] `_save_open_position_to_db()` aggiornata con nuovi parametri `tp_price`, `sl_price` e OCO IDs

---

### TASK-826 — Implementare `_on_order_update` in router.py (2026-06-12) ✅

**Status:** Complete ✅

**Scope completato:**
- [x] Definito `_on_order_update(event)` in `router.py`
- [x] Gestione `status == "filled"`: determina TP/SL da orderId, calcola PnL, aggiorna DB, chiude posizione, broadcast UI
- [x] Gestione `status == "expired"`: log informativo, nessuna azione
- [x] Guard: se `pos` è None o `oco_order_list_id` non corrisponde → return silenzioso

---

### TASK-827 — UDS singleton check + avvio post OCO riuscito (2026-06-12) ✅

**Status:** Complete ✅

**Scope completato:**
- [x] Rimosso avvio UDS immediato da `action == "start"` in `control_session()`
- [x] Aggiunta funzione `_start_uds_if_needed()` con singleton check
- [x] UDS avviato SOLO dopo OCO confermato (Caso A) nel `_candle_processor()`
- [x] UDS avviato in restore sessione se posizione aperta trovata
- [x] `on_reconnect_sync=_on_uds_reconnect_sync` passato a `uds.start()`
- [x] UDS stoppato correttamente in `action == "stop"`

---

### TASK-828 — Market sell emergenza con `_get_available_base_balance()` (2026-06-12) ✅

**Status:** Complete ✅

**Scope completato:**
- [x] Funzione `_handle_oco_failed(exchange, symbol)` implementata in `router.py`
- [x] Cancella ordini orfani via `get_open_orders` + `cancel_order`
- [x] Market sell con `_get_available_base_balance()` (qty reale post-fee)
- [x] Broadcast UI `error` con `code: "OCO_FAILED"`
- [x] Nessun salvataggio DB — `continue` nel flusso live

---

### TASK-829 — Stop sessione: wait conferma cancellazione OCO prima di market sell (2026-06-12) ✅

**Status:** Complete ✅

**Scope completato:**
- [x] Dopo `cancel_open_orders()` in stop sessione: `asyncio.sleep(0.5)`
- [x] Loop di verifica max 3 retry × 0.3s che `get_open_orders()` sia vuoto
- [x] Solo dopo conferma → prosegue con `_close_position_and_record()`

---

### TASK-830 — UDS reconnect sync: parametro `on_reconnect_sync` (2026-06-12) ✅

**Status:** Complete ✅

**Scope completato:**
- [x] `self._on_reconnect_sync: Optional[Callable] = None` in `UserDataStreamManager.__init__`
- [x] Parametro `on_reconnect_sync` aggiunto a `uds.start()`
- [x] Dopo `_reconnect()` in `_listen_loop()`: chiamata `await self._on_reconnect_sync()` se impostato
- [x] Implementata `_on_uds_reconnect_sync()` in `router.py`:
  - Query specifica per `tp_order_id` / `sl_order_id` via `_fetch_fill_price_by_order_id()`
  - Fallback a `fetch_closed_orders` se IDs non disponibili
  - Chiude posizione, aggiorna DB, broadcast UI

---

### TASK-831 — Restore sessione: query specifica per sl_order_id/tp_order_id (2026-06-12) ✅

**Status:** Complete ✅

**Scope completato:**
- [x] In `_restore_scalping_session()`: ripristina `oco_order_list_id`, `sl_order_id`, `tp_order_id` dal DB sul position object
- [x] `exchange._fetch_fill_price_by_order_id()` implementato in `exchange.py`
- [x] Restore usa `_fetch_fill_price_by_order_id()` invece di `fetch_my_trades` generico
- [x] Fallback a `fetch_closed_orders` filtrato per side se IDs non trovano match
- [x] UDS riavviato post-restore se posizione aperta trovata

---

### TASK-832 — Session Load Guard: bloccare trade durante avvio/restore sessione (2026-06-15) ✅

**Status:** Complete ✅

**Scope completato:**
- [x] Aggiunta `SessionLoadGuard` in `_execution_state["session_load_guard"]`
- [x] Fasi richieste: `db_phase`, `exchange_phase`, `position_phase`, `buffer_phase`, `pipeline_phase`
- [x] Timeout 30s con log periodici ogni 5s e stato `failed` se una fase non completa
- [x] `_restore_scalping_session()` marca `loading` all'avvio e completa DB/exchange/position
- [x] `control_session(action="start")` resetta il guard, completa exchange/position e DB dopo insert
- [x] `_start_ws_broadcast()` completa `buffer_phase` dopo warmup e `pipeline_phase` dopo `BinanceWSClient.start()`
- [x] Gate in `_candle_processor`, `_trade_processor` e trade live inline: nessun trade finché `guard.is_ready()` è false
- [x] WebSocket `session_loading` e endpoint `GET /scalping/debug/session-load` per osservabilità
- [x] Tentativi trade bloccati salvati in `deque(maxlen=100)` per evitare crescita illimitata

**File modificati:**
- `synthtrade/backend/app/scalping/session_load_guard.py`
- `synthtrade/backend/app/scalping/router.py`
- `synthtrade/backend/app/main.py`
- `docs/TASKS.md`
- `docs/OCO_FLOW.md`

---

### TASK-833 — FASE A1: Rimuovere force_execute hardcoded (2026-06-15) ✅

**Status:** Done ✅
**Completato:** 2026-06-15
**Priorità:** CRITICA — bypassa SignalAggregator, RiskManager e tutti i filtri
**Fase:** A (prerequisito per tutto il resto)
**Stima:** 0.5h
**File coinvolti:** `router.py`, `signal_aggregator.py`

**Scope:**
- [x] Rimuovere `execution_loop.force_execute = True` da `router.py`
- [x] Rimuovere attributo `self.force_execute` dalla classe `ExecutionLoop`
- [x] Rimuovere il "Caso 0: FORCE_EXECUTE" da `signal_aggregator.py`
- [x] Verifica: avviare sessione paper e controllare che non appaia `LIVE MODE: ... (intelligence bypassed)`

---

### TASK-834 — FASE A2: Supervisor interval da .env (2026-06-15) ✅

**Status:** Done ✅
**Completato:** 2026-06-15
**Priorità:** CRITICA — supervisor gira ogni 45s invece di 10min, spreca API
**Fase:** A (prerequisito per tutto il resto)
**Stima:** 0.5h
**File coinvolti:** `router.py`, `supervisor_scheduler.py`, `.env`, `config.py`

**Scope:**
- [x] Aggiungere `SCALPING_SUPERVISOR_INTERVAL_SEC=600` a `.env`
- [x] Aggiungere `SCALPING_SUPERVISOR_INTERVAL_SEC`, `SCALPING_STRATEGY_COOLDOWN_SEC`, `SCALPING_PARAM_UPDATE_COOLDOWN_SEC` a `config.py`
- [x] Sostituire `interval_seconds=45` con `settings.SCALPING_SUPERVISOR_INTERVAL_SEC` nei 2 punti di istanziazione `SupervisorScheduler` in `router.py`
- [x] Sostituire costanti hardcoded `STRATEGY_CHANGE_COOLDOWN = 1200` e `PARAM_UPDATE_COOLDOWN = 600` in `supervisor_scheduler.py` con valori da `settings`
- [x] Verifica: log supervisor ogni ~600 secondi, missed jobs APScheduler spariti

---

### TASK-835 — FASE B1-B2: .env completo e config.py aggiornato (2026-06-15) ✅

**Status:** Done ✅
**Completato:** 2026-06-15
**Priorità:** Alta — prerequisito per B3-B5
**Fase:** B (dopo Fase A)
**Stima:** 1h
**File coinvolti:** `.env`, `config.py`

**Scope:**
- [x] Sostituire sezione scalping in `.env` con versione completa e commentata (da piano §B1)
- [x] Aggiungere/sostituire sezione scalping in `config.py` con tutti i campi tipizzati (da piano §B2)
- [x] Verificare compatibilità con pattern `settings.scalping.*` se usato nel codice esistente

---

### TASK-836 — FASE B3: Migration DB tabella `scalping_runtime_config` (2026-06-15) ✅

**Status:** Done ✅
**Completato:** 2026-06-15
**Priorità:** Alta
**Fase:** B
**Stima:** 0.5h
**File coinvolti:** nuova migration Supabase

**Scope:**
- [x] Creare migration SQL con `CREATE TABLE scalping_runtime_config (key, value, value_type, description, updated_at)`
- [x] Inserire valori di default (specchio del .env) per tutti i 15 parametri `[RUNTIME]`
- [x] Applicare migration su Supabase

---

### TASK-837 — FASE B4: Nuovo `ScalpingConfigLoader` (2026-06-15) ✅

**Status:** Done ✅
**Completato:** 2026-06-15
**Priorità:** Alta
**Fase:** B
**Stima:** 1h
**File coinvolti:** nuovo `app/scalping/config_loader.py`

**Scope:**
- [x] Creare `app/scalping/config_loader.py` con classe `ScalpingConfigLoader`
- [x] Implementare `_load()`: step 1 da settings, step 2 override da DB con type-casting
- [x] Implementare `reload()` per aggiornamento runtime senza restart
- [x] Implementare proprietà typed per tutti i parametri configurabili
- [x] Esporre singleton `get_scalping_config()`

---

### TASK-838 — FASE B5: Endpoint API config scalping (2026-06-15) ✅

**Status:** Done ✅
**Completato:** 2026-06-15
**Priorità:** Media
**Fase:** B
**Stima:** 0.5h
**File coinvolti:** `router.py` o nuovo `config_scalping_api.py`

**Scope:**
- [x] `GET /api/scalping/config` — ritorna config corrente merge .env+DB
- [x] `POST /api/scalping/config/{key}` — aggiorna valore nel DB e ricarica
- [x] `POST /api/scalping/config/reload` — ricarica senza restart
- [x] Test: modificare un valore via POST e verificare che il reload abbia effetto

---

### TASK-839 — FASE C1: Sostituire Fear & Greed con alternative.me (2026-06-15) ✅

**Status:** Done ✅
**Completato:** 2026-06-15
**Priorità:** Alta — F&G congelato a 8, dato falso guida tutte le decisioni AI
**Fase:** C (dopo Fase B)
**Stima:** 1h
**File coinvolti:** `app/scalping/intelligence/collectors/fear_greed.py`

**Scope:**
- [x] Riscrivere `FearGreedCollector` per usare `https://api.alternative.me/fng/?limit=1` (gratuita, no API key)
- [x] Implementare cache intraday con TTL 4h
- [x] Implementare `value_to_score(value)` con logica contrarian (-100..+100)
- [x] Impostare `SCALPING_FEAR_GREED_SOURCE=alternative_me` in `.env`
- [x] Verifica log: `FearGreed aggiornato: XX (Fear/Greed)` con valore reale, non 8

---

### TASK-840 — FASE C2: Fix copertura whale collector disabilitato (2026-06-15) ✅

**Status:** Done ✅
**Completato:** 2026-06-15
**Priorità:** Alta — peso 0.10 fantasma riduce coverage artificialmente
**Fase:** C
**Stima:** 0.5h
**File coinvolti:** `signal_score_engine.py`

**Scope:**
- [x] Escludere whale da `active_collectors` se `settings.SCALPING_WHALE_ENABLED=False`
- [x] Correggere formula coverage: `total_weight_configured` calcolato solo sui collector attivi con peso > 0
- [x] Aggiungere `SCALPING_WHALE_ENABLED=false` a `.env`
- [x] Verifica: coverage non più penalizzata dal whale assente

---

### TASK-841 — FASE D1: Log diagnostica score engine (2026-06-15) ✅

**Status:** Done ✅
**Completato:** 2026-06-15
**Priorità:** Alta — senza diagnosi non si sa se i score sono in [-1,+1] o [-100,+100]
**Fase:** D (dopo Fase C)
**Stima:** 0.5h
**File coinvolti:** `signal_score_engine.py`

**Scope:**
- [x] Aggiungere log DEBUG in `compute()` con breakdown raw score per collector
- [x] Log deve mostrare: `breakdown raw`, `weighted_avg`, `total_weight`, `coverage`
- [x] Avviare sessione paper e analizzare 2-3 cicli di output
- [x] Determinare Scenario A (scala già -100..+100) o Scenario B (scala -1..+1)

---

### TASK-842 — FASE D2-D3: Fix normalizzazione score e soglie (2026-06-15) ✅

**Status:** Done ✅
**Completato:** 2026-06-15
**Priorità:** Alta — score mai supera 1.0 con soglia a 15, nessun trade passa il gate
**Fase:** D (dopo TASK-841)
**Stima:** 2h
**File coinvolti:** `signal_score_engine.py`, `.env`

**Scope:**
- [x] In base alla diagnosi D1: se Scenario B, scalare ogni `*_to_score()` da [-1,+1] a [-100,+100]
- [x] Verificare che `weighted_avg` non venga diviso per 100 prima di confronto soglia
- [x] Aggiornare `SCALPING_SIGNAL_STRENGTH_THRESHOLD=15.0` in `.env` con commenti di interpretazione
- [x] Verifica log: score appare in range [-100,+100]

---

### TASK-843 — FASE D4: SignalAggregator min_collectors da config (2026-06-15) ✅

**Status:** Done ✅
**Completato:** 2026-06-15
**Priorità:** Media
**Fase:** D
**Stima:** 0.25h
**File coinvolti:** `signal_aggregator.py`

**Scope:**
- [x] Sostituire `num_collectors_responded <= 3` hardcoded con `get_scalping_config().min_collectors`
- [x] Importare `get_scalping_config` da `app.scalping.config_loader`

---

### TASK-844 — FASE E1-E2: Supervisor — contesto arricchito con performance sessione (2026-06-15) ✅

**Status:** Complete ✅
**Completato:** 2026-06-19 (implementato come TASK-860)

Implementato in TASK-860: `build_scalping_context()` calcola `session_performance` da `trade_history` in-memory, con fallback DB. Sezione `=== PERFORMANCE SESSIONE ===` nel prompt supervisor.

---

### TASK-845 — FASE E3: Aggiornare system prompt supervisor (2026-06-15) ✅

**Status:** Complete ✅
**Completato:** 2026-06-19 (implementato come TASK-861)

Implementato in TASK-861: `_SUPERVISOR_SYSTEM_PROMPT` aggiornato con sezione `⚠️ REGOLA QUANDO NON AGIRE` (< 5 trade, win_rate > 60%, coverage < 50%, loop decisioni, score neutrale).

---

### TASK-846 — FASE F1: Migration DB tabella `supervisor_memory` (2026-06-15) ✅

**Status:** Complete ✅
**Completato:** 2026-06-16

Migration `supabase/migrations/20260616_supervisor_memory.sql` applicata. Tabella presente su Supabase con tutti i campi pianificati.

---

### TASK-847 — FASE F2-F3: Persistenza e caricamento memoria supervisor (2026-06-15) ✅

**Status:** Complete ✅
**Completato:** 2026-06-19 (implementato come TASK-862)

Implementato in TASK-862: `_save_decision_to_memory()` popola `session_perf` reale. `build_scalping_context()` carica ultimi 10 record da `supervisor_memory` e li mostra nel prompt come `=== DECISIONI PRECEDENTI ===`.

---

### TASK-848 — FASE F4: Job APScheduler verifica outcome decisioni (2026-06-15) ✅

**Status:** Complete ✅
**Completato:** 2026-06-19 (implementato come TASK-863)

Implementato in TASK-863: `verify_supervisor_outcomes_job()` in `scalping_jobs.py`, registrato ogni 5 minuti. Query decisioni applicate 25-35 min fa, classifica `positive/negative/neutral`.

---

### TASK-849 — Fix log soglia in SignalAggregator (2026-06-16) ✅

**Status:** Complete ✅

**Problema:** Il log mostrava `🔴 BLOCK: score -9.5 < soglia 9.5` usando `signal_strength` (valore assoluto dello score) come soglia, facendo sembrare che la soglia fosse ancora scalata dynamicamente. In realtà la soglia era già fissa a 15.0.

**Fix:** Sostituito `market_score.signal_strength` con `settings.scalping.SCALPING_SIGNAL_STRENGTH_THRESHOLD` nel messaggio di log.

**Log dopo il fix:** `🔴 BLOCK: score -9.4 < threshold 15.0 (|score|=9.4) (bias=neutral)` ✅

---

### TASK-850 — Threshold dinamico da ConfigLoader in SignalScoreEngine (2026-06-16) ✅

**Status:** Complete ✅

**Problema:** `SignalScoreEngine` leggeva la soglia da `settings.__init__()` e non si aggiornava a runtime. Il Supervisor non poteva modificarla.

**Fix:** `get_snapshot()` ora legge la soglia da `ScalpingConfigLoader` a ogni ciclo:
```python
config_loader = get_scalping_config()
runtime_threshold = config_loader.signal_strength_threshold
```
Un cambio su DB (via `POST /api/scalping/config/signal_strength_threshold`) ha effetto immediato, senza restart.

---

### TASK-851 — Azione update_threshold nel Supervisor AI (2026-06-16) ✅

**Status:** Complete ✅

**Nuova azione** `update_threshold` nel repertorio del Supervisor.

**File modificati:**
- `app/scalping/models/supervisor.py` — regex action include `update_threshold`
- `app/scalping/supervisor/parameter_updater.py` — nuovo metodo `_update_threshold()`: upsert su `scalping_runtime_config` + reload config loader
- `app/scalping/supervisor/supervisor_scheduler.py` — broadcast mapping per nuova azione
- `app/ai/supervisor_context.py` — `current_threshold` aggiunto al contesto del Supervisor
- `app/scalping/supervisor/supervisor_client.py` — prompt aggiornato con regole per update_threshold, threshold mostrato nel context formattato
- `app/ai/eval_parser.py` — `update_threshold` aggiunto a `_VALID_ACTIONS`

**Regole nel prompt:**
- Se score sempre sotto soglia ma segnale tecnico forte → abbassa (10.0 consigliato)
- Se molti falsi segnali → alza (18.0 consigliato)
- Se coverage < 60% → non abbassare (dati inaffidabili)
- Usa update_threshold prima di change_strategy come alternativa conservativa

---

### TASK-852 — Fase 0: Context arricchito threshold per Supervisor (2026-06-16) ✅

**Status:** Complete ✅

**Problema:** Il Supervisor non conosceva il valore corrente della soglia quando prendeva decisioni. Senza vedere score, gap, collector attivi/assenti, non poteva ragionare in modo informato.

**Cosa aggiunto al prompt utente:**
```
=== CONFIGURAZIONE INTELLIGENCE ===
Soglia score minima (threshold): 15.0
Score attuale: -9.5 (|score|=9.5)
Gap per passare il gate: -5.5 punti
Bias: neutral
Collector attivi: 5/7 (funding_rate, cvd, open_interest, fear_greed, sentiment)
Collector assenti: whale
Coverage: 71%
✅ Coverage buono — modifiche soglia consentite
```

**File modificati:**
- `app/ai/supervisor_context.py` — `threshold_gap`, `active_collectors`, `missing_collectors` nel context
- `app/scalping/supervisor/supervisor_client.py` — `_format_context()` sezione `=== CONFIGURAZIONE INTELLIGENCE ===`

---

### TASK-853 — Limiti sicurezza e cooldown per update_threshold (2026-06-16) ✅

**Status:** Complete ✅

**Problema:** Il Supervisor poteva azzerare la soglia (trade senza filtro) o impostarla a valori irraggiungibili (nessun trade). Poteva anche cambiarla a ogni tick, causando instabilità.

**Aggiunte:**
1. **Limiti di sicurezza** in `parameter_updater._update_threshold()`: soglia clampata tra [5.0, 30.0]
2. **Cooldown 30 minuti** in `supervisor_scheduler.py`: `THRESHOLD_CHANGE_COOLDOWN = 1800` + tracking `_last_threshold_change`
3. **Prompt aggiornato** con regole aggiuntive:
   - Score stabile tra -5 e +5 per 10+ candele in ranging → abbassa a 8-10
   - Trade in perdita consecutiva → alza di 2-3 punti
   - Non modificare più di una volta ogni 30 minuti
   - Limiti: min 5.0, max 30.0

**File modificati:**
- `app/scalping/supervisor/parameter_updater.py` — clamp [5.0, 30.0]
- `app/scalping/supervisor/supervisor_scheduler.py` — cooldown 30min
- `app/scalping/supervisor/supervisor_client.py` — prompt esteso


---

### TASK-854: Fix dust residue on live trades ✅

**Status:** Complete ✅

- math.floor per qty calculation pre-buy
- exec_qty = _qty_precise invece di market_res.quantity
- Verificare: BUY qty == OCO qty su prossimo trade live


---

### TASK-855 — BUG CRITICO: Rimuovere SL/TP software da _trade_processor in live mode (2026-06-19) ✅

**Status:** Complete ✅

- [x] In `_trade_processor()`: aggiunto guard `if _mode_trade != "live"` attorno al blocco `hit_sl`/`hit_tp`
- [x] In live mode SL/TP sono gestiti esclusivamente da OCO Binance via UDS (`_on_order_update`)
- [x] Previene doppia vendita: software close + OCO close su stesso asset

**File:** `synthtrade/backend/app/scalping/router.py`

---

### TASK-856 — BUG: Fix broadcast signal type (sempre BUY) (2026-06-19) ✅

**Status:** Complete ✅

- [x] Sostituito `"BUY" if decision.confidence > 0 else "SELL"` con `decision.signal_type`
- [x] Il frontend ora riceve il tipo segnale corretto (BUY/SELL/CLOSE)

**File:** `synthtrade/backend/app/scalping/router.py`

---

### TASK-857 — BUG: Fix `get_holdings()` in BinanceExchangeAdapter (2026-06-19) ✅

**Status:** Complete ✅

- [x] Corretto accesso a `balance["free"]` invece di `balance["total"][asset]["free"]`
- [x] Previene `TypeError: float object is not subscriptable`

**File:** `synthtrade/backend/app/execution/exchange.py`

---

### TASK-858 — BUG: Fix session_perf in supervisor_memory (2026-06-19) ✅

**Status:** Complete ✅

- [x] `_save_decision_to_memory()` ora accetta parametro `trade_history: list`
- [x] `_tick()` recupera `trade_history` da `_execution_state` del router e la passa esplicitamente
- [x] `session_perf` non è più sempre vuoto nel DB

**File:** `synthtrade/backend/app/scalping/supervisor/supervisor_scheduler.py`

---

### TASK-859 — BUG: Fix SupervisorScheduler score_engine per simbolo corretto (2026-06-19) ✅

**Status:** Complete ✅

- [x] `SupervisorScheduler.__init__`: `score_engine or SignalScoreEngine(symbol=symbol)` (era default BTCUSDT)
- [x] In `router.py`: entrambe le istanziazioni del supervisor passano `score_engine=_execution_state.get("signal_engine")`

**File:** `synthtrade/backend/app/scalping/supervisor/supervisor_scheduler.py`, `router.py`

---

### TASK-860 — Supervisor context arricchito con performance sessione (2026-06-19) ✅

**Status:** Complete ✅

- [x] `supervisor_scheduler._tick()` recupera `trade_history` e la passa a `client.decide()`
- [x] `supervisor_client.decide()` accetta `trade_history` e la passa a `build_scalping_context()`
- [x] `build_scalping_context()` calcola `session_performance` in-memory (total_trades, win_rate, pnl, last_5)
- [x] `_format_context()` mostra sezione `=== PERFORMANCE SESSIONE ===`

**File:** `supervisor_scheduler.py`, `supervisor_client.py`, `supervisor_context.py`

---

### TASK-861 — Aggiornare system prompt supervisor: regole "quando NON agire" (2026-06-19) ✅

**Status:** Complete ✅

- [x] Aggiunta sezione `⚠️ REGOLA QUANDO NON AGIRE` nel `_SUPERVISOR_SYSTEM_PROMPT`
- [x] Regole: < 5 trade → no_action, win_rate > 60% → no_action, coverage < 50% → no_action, loop decisioni → no_action

**File:** `synthtrade/backend/app/scalping/supervisor/supervisor_client.py`

---

### TASK-862 — Caricamento storico decisioni supervisor nel context (2026-06-19) ✅

**Status:** Complete ✅

- [x] `build_scalping_context()` carica ultimi 10 record da `supervisor_memory` per symbol/session
- [x] `_format_context()` mostra sezione `=== DECISIONI PRECEDENTI (ultime 10) ===`
- [x] Tabella `supervisor_memory` già presente (migration 20260616 applicata)

**File:** `supervisor_context.py`, `supervisor_client.py`

---

### TASK-863 — Job APScheduler verifica outcome decisioni supervisor (2026-06-19) ✅

**Status:** Complete ✅

- [x] `verify_supervisor_outcomes_job()` aggiunto in `scalping_jobs.py`
- [x] Query decisioni applicate 25-35 min fa senza outcome, classifica positive/negative/neutral
- [x] Registrato in `setup_scheduler()` con `interval_minutes=5`

**File:** `synthtrade/backend/app/scheduler/scalping_jobs.py`, `jobs.py`

---

### TASK-864 — Circuit breaker per collector HTTP (2026-06-19) ✅

**Status:** Complete ✅

- [x] Creato `circuit_breaker.py` con `CollectorCircuitBreaker` (closed→open→half_open, 3 failures, 5min reset)
- [x] Integrato in tutti i 6 collector HTTP: `funding_rate`, `open_interest`, `long_short_ratio`, `fear_greed`, `sentiment`, `whale`, `onchain`
- [x] Ogni collector controlla `is_available()` prima di fare HTTP call

**File:** `collectors/circuit_breaker.py` + tutti i collector

---

### TASK-865 — Health check endpoint modulo scalping (2026-06-19) ✅

**Status:** Complete ✅

- [x] Aggiunto `GET /scalping/health` in `router.py`
- [x] Restituisce stato di: ws_client, UDS, supervisor, candle_buffer, signal_engine, session_guard

**File:** `synthtrade/backend/app/scalping/router.py`

---

### TASK-866 — Rate limit budget giornaliero chiamate AI supervisor (2026-06-19) ✅

**Status:** Complete ✅

- [x] Aggiunto `SCALPING_SUPERVISOR_MAX_DAILY_CALLS=100` in `.env` e `config.py`
- [x] `SupervisorScheduler._tick()` controlla e incrementa `_daily_ai_calls`, reset a mezzanotte

**File:** `supervisor_scheduler.py`, `config.py`, `.env`

---

### TASK-867 — PositionManager: aggiungere exit_price e closed_at (2026-06-19) ✅

**Status:** Complete ✅

- [x] Aggiunti campi `exit_price: Optional[Decimal]` e `closed_at: Optional[datetime]` al dataclass `Position`
- [x] `close_position()` popola entrambi i campi al momento della chiusura

**File:** `synthtrade/backend/app/scalping/engine/position_manager.py`

---

### TASK-868 — Test suite per componenti core scalping (2026-06-19) ✅

**Status:** Complete ✅

- [x] Creato `tests/test_scalping_core.py` con 13 test
- [x] Coverage: `SessionLoadGuard` (4 test), `PositionManager` (2 test), `SignalAggregator` (5 test), `CircuitBreaker` (2 test)
- [x] **Tutti i test passano: 13/13 PASSED** (verificato `pytest tests/test_scalping_core.py -v`)
- [x] Fix collaterale: rimossi frammenti di docstring orfani in `long_short_ratio.py`, `sentiment.py`, `onchain.py`, `whale.py` (causa: patch circuit breaker aveva lasciato resti di docstring originale dopo `return None`)

**File:** `synthtrade/backend/tests/test_scalping_core.py`

---

### TASK-822 — Config panel: rimuovere sub-tab "Strategy" e aggiungere titolo "Session" con ID (2026-06-09) ✅

**Status:** Complete ✅

**Problema:** Nel pannello di configurazione principale è presente una sub-scheda "Strategy" che mostra la strategia selezionata inizialmente ma non si aggiorna quando la strategia corrente cambia (es. dopo una decisione del supervisor AI). Esiste già una sezione più completa e aggiornata nel pannello Strategy dedicato.

**Soluzione:**
1. Rimuovere la sub-scheda "Strategy" dal pannello di configurazione principale
2. Aggiungere un titolo principale "Session" al pannello di configurazione
3. Mostrare l'ID della sessione in testo più piccolo sotto il titolo
4. Mantenere visibili le impostazioni di configurazione del trade già esistenti nel sistema

**Modifiche:**
- Rimuovere sub-tab "Strategy" dal componente del pannello configurazione sessione
- Aggiungere header con titolo "Session" + session ID
- Lasciare al loro posto le impostazioni esistenti (symbol, strategy selector, trade value)

**Rischio:** Basso — rimozione UI senza impatto su logica backend.

---

### TASK-880 — Backend: Nuovo endpoint `GET /scalping/sessions` (lista sessioni storiche) ✅

**Status:** Complete ✅
**Completato:** 2026-06-19
**Priorità:** Alta — prerequisito per la UI delle sessioni
**Stima:** 30 min
**File coinvolti:** `synthtrade/backend/app/scalping/router.py`

**Scope:**
- [x] Aggiungere nuovo endpoint:
  ```python
  @router.get("/sessions")
  async def list_scalping_sessions(limit: int = 50, offset: int = 0) -> List[Dict]:
  ```
- [x] Query `scalping_sessions` in Supabase ordinata per `started_at DESC`
- [x] Campi nel response JSON:
  ```json
  {
    "id": "uuid",
    "symbol": "BNBUSDC",
    "mode": "LIVE",
    "status": "stopped",
    "started_at": "2026-06-19T09:30:00Z",
    "stopped_at": "2026-06-19T12:15:00Z",
    "duration_seconds": 9900,
    "total_pnl": 3.45,
    "trade_count": 12,
    "win_count": 8,
    "strategy": "momentum_base",
    "trade_value": 100.0
  }
  ```
- [x] `duration_seconds` = differenza tra `stopped_at` e `started_at` se status è `stopped`, altrimenti `null`
- [x] Supporto paginazione via `limit` e `offset`
- [x] Se non ci sono sessioni, ritornare lista vuota `[]` (non errore)
- [x] Verifica: chiamare `GET /scalping/sessions` e leggere output

---

### TASK-881 — Backend: Aggiungere filtro `session_id` + campi `entry_time`/`exit_time` a `GET /scalping/trade-history` ✅

**Status:** Complete ✅
**Completato:** 2026-06-19
**Priorità:** Alta — prerequisito per mostrare i trade di una singola sessione
**Stima:** 15 min
**File coinvolti:** `synthtrade/backend/app/scalping/router.py`

**Scope:**
- [x] Modificare firma endpoint:
  ```python
  @router.get("/trade-history")
  async def get_trade_history(session_id: Optional[str] = None, limit: int = 50) -> List[Dict]:
  ```
- [x] Se `session_id` è fornito:
  - Query `scalping_trades` filtrata per `session_id`
  - Ordinata per `entry_time DESC`
  - Response con campi: `symbol`, `side`, `entry_price`, `exit_price`, `quantity`, `pnl`, `pnl_pct`, `entry_time`, `exit_time`, `signal_reason`, `status`
- [x] Se `session_id` non è fornito:
  - Comportamento attuale: ritorna `trade_history` dalla memoria `_execution_state`
  - **Inoltre**: aggiungere `entry_time` e `exit_time` ai trade in memoria:
    - `entry_time` = `timestamp` del trade (già presente)
    - `exit_time` = `timestamp` del trade (stesso valore, perché in memoria il trade è già chiuso)
- [x] Retrocompatibilità garantita: chi chiama senza `session_id` continua a funzionare
- [x] Verifica: chiamare `GET /scalping/trade-history?session_id=<uuid>` e ottenere lista trade filtrata

---

### TASK-882 — Frontend: Modelli + Servizio per le sessioni scalping nella pagina logs ✅

**Status:** Complete ✅
**Completato:** 2026-06-19
**Priorità:** Alta — strato dati per la UI
**Stima:** 15 min
**File coinvolti:**
  - Nuovo `synthtrade/frontend/synthtrade-ui/src/app/pages/logs/logs.model.ts`
  - Nuovo `synthtrade/frontend/synthtrade-ui/src/app/pages/logs/logs.service.ts`

**Scope:**

**File: `logs.model.ts`**
- [x] Interfaccia `ScalpingSessionLog`:
  ```typescript
  export interface ScalpingSessionLog {
    id: string;
    symbol: string;
    mode: 'PAPER' | 'LIVE';
    status: 'running' | 'paused' | 'stopped';
    started_at: string;
    stopped_at?: string;
    duration_seconds?: number;
    total_pnl: number;
    trade_count: number;
    win_count: number;
    strategy?: string;
    trade_value?: number;
  }
  ```
- [x] Interfaccia `SessionTradeLog`:
  ```typescript
  export interface SessionTradeLog {
    symbol: string;
    side: 'BUY' | 'SELL';
    entry_price: number;
    exit_price?: number;
    quantity: number;
    pnl?: number;
    pnl_pct?: number;
    entry_time: string;
    exit_time?: string;
    signal_reason?: string;
    status?: string;
  }
  ```

**File: `logs.service.ts`**
- [x] Servizio injectable `ScalpingSessionLogsService`:
  ```typescript
  @Injectable({ providedIn: 'root' })
  export class ScalpingSessionLogsService {
    private http = inject(HttpClient);
    private base = '/api/scalping';

    getSessions(limit = 50, offset = 0): Observable<ScalpingSessionLog[]>
    getSessionTrades(sessionId: string): Observable<SessionTradeLog[]>
  }
  ```
- [x] `getSessions()`: GET `${this.base}/sessions?limit=${limit}&offset=${offset}`
- [x] `getSessionTrades()`: GET `${this.base}/trade-history?session_id=${sessionId}`
- [x] Gestione errori base (log warning, return array vuoto)

---

### TASK-883 — Frontend: Tab "Scalping" con accordion sessioni e trade annidati ✅

**Status:** Complete ✅
**Completato:** 2026-06-19

**Fix post-screenshot (2026-06-19):**
- [x] Aggiunta header row con label colonne (Simbolo, Modo, Inizio, Fine, Durata, Trade, Wins, P&L €, Win%)
- [x] Layout a grid CSS con colonne a larghezza fissa (non più flex → tutto a sinistra)
- [x] Paginazione sessioni: 10 sessioni per pagina con Prev/Next
- [x] Backend fix: al stop sessione ora salva `trade_count`, `win_count`, `total_pnl` su `scalping_sessions`
**Priorità:** Alta — UI finale
**Stima:** 2h
**File coinvolti:** `synthtrade/frontend/synthtrade-ui/src/app/pages/logs/logs.page.ts`

**Scope — Template:**

**1. Aggiungere terzo tab:**
```html
<button class="tab-btn" [class.active]="activeTab() === 'scalping'" (click)="switchTab('scalping')">🧵 Scalping</button>
```
- Aggiornare il tipo `activeTab` a `'logs' | 'trades' | 'scalping'`

**2. Nuova sezione `@if (activeTab() === 'scalping')`:**
- Se `sessions().length === 0` → mostra `<div class="empty-state">Nessuna sessione di scalping trovata.</div>`
- Altrimenti → container accordion

**3. Riga header accordion** per ogni sessione (cliccabile → `toggleSession(s.id)`):
```html
<div class="session-row" [class.expanded]="expandedSessionId() === s.id" (click)="toggleSession(s.id)">
  <!-- Pallino stato -->
  <span class="status-dot" [class.running]="s.status === 'running'" [class.stopped]="s.status === 'stopped'"></span>

  <!-- Symbol + Mode badge -->
  <span class="session-symbol">{{ s.symbol }}</span>
  <span class="mode-badge" [class.live]="s.mode === 'LIVE'" [class.paper]="s.mode === 'PAPER'">{{ s.mode }}</span>

  <!-- Data inizio -->
  <span class="session-start">{{ s.started_at | date:'dd/MM/yy HH:mm' }}</span>

  <!-- Data fine / "In corso" -->
  @if (s.status === 'running') {
    <span class="session-end">In corso</span>
  } @else {
    <span class="session-end">{{ s.stopped_at | date:'dd/MM/yy HH:mm' }}</span>
  }

  <!-- Durata sessione (calcolata in frontend) -->
  <span class="session-duration">{{ calcDuration(s.started_at, s.stopped_at) }}</span>

  <!-- Trade count -->
  <span class="session-trades">📊 {{ s.trade_count }}</span>

  <!-- Win count / total -->
  @if (s.trade_count > 0) {
    <span class="session-wins">✅ {{ s.win_count }}/{{ s.trade_count }}</span>
  }

  <!-- P&L total (colorato) -->
  <span class="session-pnl" [ngClass]="{ positive: s.total_pnl >= 0, negative: s.total_pnl < 0 }">
    {{ s.total_pnl >= 0 ? '+' : '' }}{{ s.total_pnl | number:'1.2-2' }} €
  </span>

  <!-- Win rate -->
  @if (s.trade_count > 0) {
    <span class="session-winrate" [ngClass]="{ positive: winRate(s) >= 50, negative: winRate(s) < 50 }">
      {{ winRate(s) | number:'1.1-1' }}%
    </span>
  }

  <!-- Freccia espansione -->
  <span class="expand-arrow">{{ expandedSessionId() === s.id ? '🔼' : '🔽' }}</span>
</div>
```

**4. Body accordion** (dopo header, visibile solo se espanso):
```html
@if (expandedSessionId() === s.id) {
  <div class="session-detail">
    @if (sessionTrades().length === 0) {
      <div class="empty-state">Nessun trade in questa sessione.</div>
    } @else {
      <div class="trades-table-wrapper">
        <table class="trades-table">
          <thead>
            <tr>
              <th>Ora</th>
              <th>Pair</th>
              <th>Tipo</th>
              <th>Entry</th>
              <th>Exit</th>
              <th>Q.tà</th>
              <th>Durata</th>
              <th>P&L €</th>
              <th>P&L %</th>
              <th>Motivo</th>
            </tr>
          </thead>
          <tbody>
            @for (t of sessionTrades(); track trackByTrade(i, t)) {
              <tr>
                <td class="cell-date">{{ t.entry_time | date:'HH:mm' }}</td>
                <td class="cell-pair">{{ t.symbol }}</td>
                <td class="cell-side" [ngClass]="{ buy: t.side === 'BUY', sell: t.side === 'SELL' }">{{ t.side }}</td>
                <td class="cell-price">{{ t.entry_price | number:'1.2-6' }}</td>
                <td class="cell-exit">{{ t.exit_price != null ? (t.exit_price | number:'1.2-6') : '—' }}</td>
                <td class="cell-qty">{{ t.quantity | number:'1.4-8' }}</td>
                <td class="cell-duration">{{ tradeDuration(t.entry_time, t.exit_time) }}</td>
                <td class="cell-pnl-eur" [ngClass]="{ positive: (t.pnl ?? 0) >= 0, negative: (t.pnl ?? 0) < 0 }">
                  {{ t.pnl != null ? ((t.pnl >= 0 ? '+' : '') + (t.pnl | number:'1.2-2') + ' €') : '—' }}
                </td>
                <td class="cell-pnl" [ngClass]="{ positive: (t.pnl_pct ?? 0) >= 0, negative: (t.pnl_pct ?? 0) < 0 }">
                  {{ t.pnl_pct != null ? ((t.pnl_pct >= 0 ? '+' : '') + (t.pnl_pct | number:'1.2-2') + '%') : '—' }}
                </td>
                <td class="cell-reason">{{ t.signal_reason ?? '—' }}</td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    }
  </div>
}
```

**5. Helper functions (metodi del component):**

- **`calcDuration(startIso: string, endIso?: string): string`**
  - Calcola `endIso ? new Date(endIso) - new Date(startIso) : Date.now() - new Date(startIso)`
  - Formatta output:
    - `>= 86400s` → `Xg Yh`
    - `>= 3600s` → `Xh Ym`
    - `>= 60s` → `Xm Ys`
    - `< 60s` → `Xs`
  - Se sessione ancora running, mostra durata progressiva

- **`winRate(s: ScalpingSessionLog): number`**
  - Se `s.trade_count > 0` → `(s.win_count / s.trade_count) * 100`
  - Altrimenti → `0`

- **`tradeDuration(entryIso: string, exitIso?: string): string`**
  - Calcola `exitIso ? new Date(exitIso) - new Date(entryIso) : Date.now() - new Date(entryIso)`
  - Se trade ancora aperto (`exitIso == null`) → mostra "aperto"
  - Formatta:
    - `>= 3600s` → `Xh Ym`
    - `>= 60s` → `Ym Zs`
    - `< 60s` → `Xs`
  - Esempi: "12m", "1h 30m", "3s", "45m 20s"

- **`trackByTrade(index: number, trade: SessionTradeLog): string`**
  - `trade.entry_time + trade.symbol + trade.side` — per track by univoco

**Scope — Class:**

**6. Nuovi signal e stato:**
```typescript
sessions = signal<ScalpingSessionLog[]>([]);
expandedSessionId = signal<string | null>(null);
sessionTrades = signal<SessionTradeLog[]>([]);
private sessionsOffset = signal(0);
private sessionsLoaded = signal(false);
```

**7. Inject servizio:**
```typescript
private scalpingSessionLogsService = inject(ScalpingSessionLogsService);
```

**8. Nuovi metodi:**
- `loadSessions()` — chiama `getSessions(50, 0)`, setta `sessions` e `sessionsLoaded`
- `toggleSession(sessionId)` — se già espansa → collassa; altrimenti → espande e carica trade
- `loadSessionTrades(sessionId)` — chiama `getSessionTrades(sessionId)`, setta `sessionTrades`

**9. Modifica `switchTab()`:**
```typescript
switchTab(tab: 'logs' | 'trades' | 'scalping'): void {
  this.activeTab.set(tab);
  if (tab === 'scalping') {
    if (!this.sessionsLoaded()) this.loadSessions();
    this.expandedSessionId.set(null);
    this.sessionTrades.set([]);
  } else if (tab === 'trades') { ... }
  else { ... }
}
```

**Scope — Styles:**

**10. Stili aggiuntivi:**
```scss
/* Accordion session row */
.session-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 6px;
  margin-bottom: 4px;
  cursor: pointer;
  font-size: 13px;
  transition: background 0.15s;
  &:hover { background: rgba(255,255,255,0.03); }
  &.expanded {
    border-color: var(--accent-primary);
    border-bottom-left-radius: 0;
    border-bottom-right-radius: 0;
    margin-bottom: 0;
  }
}

/* Stato pallino */
.status-dot {
  width: 10px; height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
  &.running { background: #26a69a; box-shadow: 0 0 6px rgba(38,166,154,0.5); }
  &.stopped { background: #555; }
}

/* Symbol */
.session-symbol {
  font-family: monospace;
  font-weight: 700;
  color: var(--text-primary);
  min-width: 80px;
}

/* Badge mode */
.mode-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 3px;
  text-transform: uppercase;
  &.live { background: rgba(239,83,80,0.2); color: #ef5350; }
  &.paper { background: rgba(38,166,154,0.2); color: #26a69a; }
}

/* Date colonne */
.session-start,
.session-end,
.session-duration {
  font-family: monospace;
  font-size: 11px;
  color: var(--text-muted);
  min-width: 80px;
}

/* Durata */
.session-duration { color: var(--text-secondary); min-width: 60px; }

/* Trade count */
.session-trades { color: var(--text-secondary); min-width: 50px; text-align: center; }

/* Win count */
.session-wins { color: var(--text-secondary); font-size: 12px; min-width: 60px; }

/* P&L */
.session-pnl { font-family: monospace; font-weight: 700; min-width: 80px; text-align: right; }

/* Win rate */
.session-winrate { font-family: monospace; font-weight: 600; font-size: 12px; min-width: 50px; text-align: right; }

/* Expand arrow */
.expand-arrow { margin-left: auto; font-size: 12px; }

/* Detail panel (body accordion) */
.session-detail {
  background: var(--bg-elevated);
  border: 1px solid var(--accent-primary);
  border-top: none;
  border-bottom-left-radius: 6px;
  border-bottom-right-radius: 6px;
  padding: 8px;
  margin-bottom: 4px;
}

/* Durata trade nella tabella */
.cell-duration { font-family: monospace; font-size: 11px; color: var(--text-muted); white-space: nowrap; }

/* Reason cell */
.cell-reason { font-size: 11px; color: var(--text-secondary); max-width: 80px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
```

**11. Verifica finale (checklist):**
- [x] Tre tab funzionanti: Log, Storico Trade, Scalping
- [x] Click su tab "Scalping" carica lista sessioni
- [x] Ogni riga mostra: stato, symbol, mode, inizio, fine, durata, trade count, win/total, P&L €, win rate %, freccia
- [x] Click su riga espande accordion con tabella trade
- [x] Tabella trade mostra: ora, pair, tipo, entry, exit, q.tà, durata trade, P&L €, P&L %, motivo
- [x] Click su altra riga cambia espansione (collassa precedente, espande nuova)
- [x] Durata sessione in formato leggibile (es: "2h 15m")
- [x] Durata trade in formato leggibile (es: "12m", "45s")
- [x] Empty state se nessuna sessione
- [x] Empty state nella tabella se sessione senza trade
- [x] P&L colorato verde/rosso
- [x] Win rate colorato verde (≥50%) / rosso (<50%)
- [x] Performance decente con molte sessioni (OnPush change detection)

---

---

## ✅ Epica Persistenza Log Decisionale — Livello 1 (2026-06-29)

### TASK-892 ✅ — Decision Context Extractor
`synthtrade/backend/app/core/decision_context.py` — dataclass `DecisionContext` + `extract_decision_context()`

### TASK-893 ✅ — Schema DB `session_signal_log`
`synthtrade/supabase/migrations/20260629000000_create_session_signal_log.sql` — tabella + 3 indici, applicata su Supabase

### TASK-894 ✅ — Scrittura decisioni ai 4 punti del router
- `router.py`: log execute / hold_existing_position / rejected_other+block_conflict / execution_error
- `execution_loop.py`: aggiunto `_last_market_score` per accesso al contesto intelligence
- `signal_log_writer.py`: creato con helpers tipizzati, ritorna UUID dell'insert
- `tests/unit/test_signal_log_writer.py`: test unitari

### TASK-895 ✅ — Collegamento signal_log_id su scalping_trades
- `synthtrade/supabase/migrations/20260629000001_add_signal_log_id_to_scalping_trades.sql`
- `router.py`: `_save_open_position_to_db` accetta e salva `signal_log_id`
- `signal_log_writer.py`: `log_signal_decision` ora ritorna `Optional[str]` (UUID)

### TASK-896 ✅ — Fix logging eccezioni Binance (body completo)
`router.py`: `Live trade failed` ora logga `type + message + args` dell'eccezione ccxt

### TASK-897 ✅ — Vista aggregata win rate per (strategy, regime)
`synthtrade/supabase/migrations/20260629000002_create_signal_outcome_view.sql` — `CREATE OR REPLACE VIEW signal_outcome_by_strategy_regime`

### TASK-899 ✅ — Log Persistence Layer
`synthtrade/backend/app/core/log_persistence.py` — classi `LogStorage` e `LogParser`

### TASK-900 ✅ — Fix drawdown check in produzione
`router.py`: aggiunta `_check_drawdown()` con calcolo peak equity reale. Check in 2 punti (live + paper). Broadcast `MAX_DRAWDOWN` error al frontend (toast rosso 8s).

---

### TASK-907 — Fix Falso positivo `tasks_alive` e watchdog WS (2026-06-30) ✅

**Status:** Complete ✅

- [x] Non sostituire il `client` a caldo dentro un singolo task
- [x] Il watchdog deve segnalare alla sessione di fare un restart completo della connessione WebSocket
- [x] La logica di restart deve cancellare esplicitamente tutti i vecchi task, istanziare il nuovo client, e ri-spawnare tutti i task di ricezione

**File:** `synthtrade/backend/app/scalping/router.py`

---

### TASK-910 — Arricchimento contesto in `supervisor_memory.market_context` (2026-06-30) ✅

**Status:** Complete ✅

- [x] Modificare la firma della funzione `_save_decision_to_memory` in `supervisor_scheduler.py` per accettare gli argomenti opzionali `snapshot`, `score`, `ta_patterns` e `vol_anomaly`
- [x] Aggiornare le chiamate a questa funzione all'interno del metodo `_tick()`, passandole variabili che vengono già calcolate un attimo prima di chiamare il client AI
- [x] Arricchire il dizionario `market_context` prima di inviarlo al database

**File:** `synthtrade/backend/app/scalping/supervisor/supervisor_scheduler.py`

---

### TASK-908 — Fix troncamento log eccezioni CCXT in ExchangeOrderError (2026-06-30) ✅

**Status:** Complete ✅

- [x] Esteso `ExchangeOrderError` con `original_exception` e `original_details`
- [x] Modificati tutti i punti di `raise ExchangeOrderError` in `exchange.py` per preservare dettagli originali
- [x] Aggiornato `router.py` per estrarre `original_details` da `ExchangeOrderError`
- [x] Sostituito controllo `isinstance(live_e, ccxt.BaseError)` con `isinstance(live_e, ExchangeOrderError)`

**File:** `synthtrade/backend/app/execution/exchange.py`, `synthtrade/backend/app/scalping/router.py`

---

### TASK-909 — Isolamento chiamate AI sincrone per evitare blocco APScheduler (2026-06-30) ✅

**Status:** Complete ✅

- [x] Modificato `supervisor_client.py` per usare `asyncio.to_thread()` per le chiamate AI
- [x] Creato wrapper sincrono con event loop separato per ogni chiamata AI
- [x] Questo permette ad APScheduler di continuare a processare altri job durante le chiamate AI
- [x] Aggiunto import `asyncio` per l'esecuzione in thread pool

**File:** `synthtrade/backend/app/scalping/supervisor/supervisor_client.py`


---

## ✅ Task Completati (Archiviati il 2026-07-13)

### TASK-1129 - Fix type errors in okx_exchange.py

**Status:** Done
**Priorità:** ALTA - Pylance type errors bloccano type checking
**File:** synthtrade/backend/app/execution/okx_exchange.py

**Problema:** Pylance segnalava 30+ errori di tipo nel file okx_exchange.py, principalmente:
- Duplicate method definitions (get_trade_fee, _direct_place_market_order)
- None handling in float() conversions (TypeError: float() argument must be convertible to float)
- Type mismatches between CCXT Order objects and dict[str, Any]
- Missing _get_ccxt_symbol method
- Unbound variables in exception handlers (qty, tp_price, sl_price)

**Fix applicato:**
- Rimosso metodo duplicato get_trade_fee (seconda definizione senza logica TASK-1127)
- Rimosso metodo duplicato _direct_place_market_order
- Aggiunto `or 0` a tutte le conversioni float() per gestire valori None
- Aggiunto `cast(dict[str, Any], ...)` per convertire oggetti CCXT in dict dove richiesto
- Sostituito chiamata `_get_ccxt_symbol(sym_ref.okx)` con `sym_ref.ccxt` diretto
- Inizializzato qty, tp_price, sl_price prima del try-catch in place_exit_bracket
- Aggiunto tipi di ritorno specifici per dict methods (dict[str, Any])

**Effetto:** Tutti gli errori Pylance risolti, type checking ora passa senza errori.
### TASK-1128 - Fix Bracket qty 51008 insufficient balance

**Status:** Done
**Priorita:** CRITICA - order-algo falliva per via della fee OKX sottratta prima del bracket
**File:** synthtrade/backend/app/scalping/router.py

**Problema:** OKX preleva la fee di ingresso per ordini BUY in asset base (es. OKB). Noi inviavamo il bracket con la qty lorda dell'entry (exec_qty = 0.28425) ma in pancia avevamo 0.28425 - fee = 0.28325. Mentre per market order OKX esegue l'importo massimo disponibile anche se superiore, per \order-algo\ rifiuta con 51008 \Order failed. Your available OKB balance is insufficient\.

**Fix:** Se side=BUY e l'asset di commissione e' l'asset base (o sconosciuto, assumendo standard crypto OKX), sottrarre la commissione prima di piazzare l'exit bracket.

**Note per l'utente (posizione rimasta aperta):** Il fatto che ci fosse una posizione aperta su OKB che non si e' chiusa allo stop della sessione alle 11:10 e' dovuto al fatto che il bot e' stato fermato nel brevissimo istante (1 secondo) in cui l'ordine BUY era stato completato ma il Bracket TP/SL non era ancora stato mandato. Questo ha fatto si che il bot considerasse la posizione non ancora formalmente 'aperta' nel suo registro. Fixato il bracket (non fallira piu con 51008), queste edge case non si verificheranno piu (il bracket entrera liscio).
### TASK-1127 - Fix SL price SOPRA entry per BUY: OKX error 51280

**Status:** Done
**Priorita:** CRITICA - il bracket TP/SL falliva sempre con 51280 SL trigger price must be less than the last price
**File:** synthtrade/backend/app/scalping/router.py (riga 1656-1676)

**Root cause:** _net_to_gross_pct(-0.3, 0.0035, 0.002) restituisce +0.2507% (POSITIVO) per via delle fee OKX alte.
La formula: gross = (1 + net) / ((1 - entry_fee) * (1 - exit_fee)) - 1
Con net=-0.003, entry=0.0035, exit=0.002: gross = 0.997 / 0.99451 - 1 = +0.002507 (positivo!)
Il codice poi calcolava: sl_price = exec_price * (1 + 0.002507) = entry + 0.25% -> SL SOPRA entry per BUY.
OKX rifiutava con 51280 perche il SL deve essere SOTTO il prezzo corrente.

**Fix:**
- sl_gross_pct ora calcolato con input POSITIVO e abs(): abs(_net_to_gross_pct(sl_pct_net_cfg, ...))
- sl_price per BUY usa (1 - sl_gross_pct) invece di (1 + sl_gross_pct)
- Logica esplicita: BUY: SL sotto (1-sl), TP sopra (1+tp) / SELL: SL sopra (1+sl), TP sotto (1-tp)
- Log aggiornato per mostrare sl_price e tp_price effettivi

**Verifica matematica con entry=70.36, SL=0.3%, fee taker=0.0035, maker=0.002:**
  sl_gross_pct = abs(_net_to_gross_pct(0.3, 0.0035, 0.002)) / 100 = 0.002507
  sl_price = 70.36 * (1 - 0.002507) = 70.36 * 0.997493 = 70.18 (SOTTO entry, corretto)
### TASK-1126 - Fix OKX bracket 50014: Parameter ordType can not be empty

**Status:** Done
**Priorita:** CRITICA - ogni trade live veniva eseguito ma il bracket TP/SL falliva, generando market sell emergenza
**File:** synthtrade/backend/app/execution/okx_exchange.py

**Problema:** _direct_place_exit_bracket() costruiva il body per POST /api/v5/trade/order-algo senza il campo ordType. OKX restituiva errore 50014: Parameter ordType can not be empty. Il CASO B veniva attivato: emergency market sell immediata.

**Log osservato:**
OKX order-algo POST failed [400]: {code:50014, msg:Parameter ordType can not be empty.}
BRACKET_FLOW CASO B: bracket fallito per OKB-EUR -> eseguo market sell emergenza

**Fix:** Aggiunto campo ordType: oco nel body della chiamata REST diretta a /api/v5/trade/order-algo.

**Effetto:** I trade buy vengono eseguiti correttamente (confermato su OKX), ora il bracket OCO con TP/SL dovrebbe essere creato correttamente dopo il buy.
### TASK-1125 - Fix NameError: cannot access free variable settings in _start_ws_broadcast

**Status:** Done
**Priorita:** CRITICA - blocca ogni trade live (non solo restore_mode)
**File:** synthtrade/backend/app/scalping/router.py

**Problema:** NameError in _trade_processor (inner function di _start_ws_broadcast). La funzione conteneva un import locale 'from app.config import settings' dentro un blocco 'if restore_mode:'. Python lo trattava come variabile locale per l'intera funzione, incluse le inner function come _trade_processor. Quando restore_mode=False, il blocco non eseguiva e settings rimaneva non associato.

**Fix:** Rimosso import locale ridondante. Le inner function ora risolvono settings dall'import module-level (riga 46 di router.py).
### TASK-1125 — Fix NameError: cannot access free variable 'settings' in _start_ws_broadcast

**Status:** Done ✅
**Priorità:** CRITICA — blocca ogni trade live (non solo restore_mode)
**File:** synthtrade/backend/app/scalping/router.py

**Problema:** NameError: cannot access free variable 'settings' where it is not associated with a value in enclosing scope in _trade_processor (inner function di _start_ws_broadcast).

**Root cause:** La funzione _start_ws_broadcast conteneva un import locale rom app.config import settings dentro un blocco if restore_mode:. Python lo tratta come variabile locale per l'intera funzione, incluse le inner function come _trade_processor. Quando 
estore_mode=False, il blocco non esegue e settings rimane non associato.

**Fix:** Rimosso rom app.config import settings locale. Le inner function ora risolvono settings dall'import module-level (riga 46).

**File:** `synthtrade/backend/app/execution/okx_exchange.py`

**Problema:** Pylance segnala `Object of type "None" is not subscriptable` alla riga 90 quando si accede a `self.client.urls["api"]`. CCXT può restituire `None` per `urls` in certe modalità operative.

**Fix applicato:**
- Aggiunto guard `self.client.urls is not None` per evitare subscript su `None`
- Sostituito `.get("api", {})` con `(self.client.urls.get("api") or {})` per gestire `None` values nel dict
- isinstance guard già presente per saltare valori `None` nel dict comprehension
### TASK-1123 — CCXT create_order fallisce con 50119 su OKX EU, fallback REST diretto per market order

**Status:** Done ✅
**Priorità:** CRITICA — blocca trading live su OKX EU accounts

**File:** `synthtrade/backend/app/execution/okx_exchange.py`

**Problema:** `place_market_order()` chiama `self.client.create_order()` via CCXT, che fallisce con errore `50119 API key doesn't exist` su OKX EU live accounts perché `load_markets()` non si autentica correttamente con le chiavi EU. Il balance (che usa REST diretto) funzionava già, ma gli ordini erano bloccati.

**Log osservato:**
```
ERROR: Live trade failed: OKX market order failed: okx {"msg":"API key doesn't exist","code":"50119"}
```

**Fix applicato:**
- Aggiunto metodo `_direct_place_market_order()` che usa POST `/api/v5/trade/order` con firma HMAC-SHA256 diretta, bypassando CCXT
- Modificata `place_market_order()`: se CCXT fallisce con `50119` o `"API key doesn't exist"`, usa il fallback REST diretto
- Il fallback supporta sia quantità base che `tgtCcy=quote_ccy` per buy con importo in valuta quota

**Verifica:** Syntax check passato, logica speculare a `_direct_fetch_balance()` già funzionante.
### TASK-1122 — Add missing SymbolRef.from_any() method

**Status:** Done ✅
**Priorità:** ALTA — blocca live trading OKX

**File:** `synthtrade/backend/app/execution/exchange_models.py`

**Problema:** `OkxExchangeAdapter.get_symbol_filters()` chiama `SymbolRef.from_any(symbol)` ma il metodo non esiste. Solo `from_compact()`, `from_ccxt()` e `from_okx()` sono implementati. Causa `AttributeError: type object 'SymbolRef' has no attribute 'from_any'` quando il router tenta di aprire un trade live.

**Log osservato:**
```
Live trade failed: OKX get_symbol_filters failed for OKB-EUR: type object 'SymbolRef' has no attribute 'from_any'
```

**Fix applicato:**
- Aggiunto `SymbolRef.from_any(symbol: str) -> SymbolRef` in `exchange_models.py`
- Supporta tre formati: OKX (`BTC-EUR`), CCXT (`BTC/EUR`), Compact (`BTCEUR`)
- Usa `from_compact()` come fallback con quote_assets predefinite
### TASK-1124 — Fix firma HMAC-SHA256 per POST /api/v5/trade/order (errore 401)

**Status:** Done ✅
**Priorità:** CRITICA — blocca trading live su OKX EU accounts (fallback REST)
**File:** `synthtrade/backend/app/execution/okx_exchange.py`

**Problema:** `_direct_place_market_order()` falliva con `Client error '401 Unauthorized' for url 'https://eea.okx.com/api/v5/trade/order'`. Il metodo `_sign_headers()` includeva sempre `body` nella prehash anche se vuoto, ma per le richieste GET (es. balance) veniva passata stringa vuota, quindi funzionava. Il problema era che per POST il body veniva incluso sempre senza distinzione — la specifica OKX richiede esplicitamente che per POST con body la prehash sia `timestamp + method + path + body`, mentre per GET senza body sia solo `timestamp + method + path`.

**Fix applicato:**
- `_sign_headers()`: aggiunto controllo esplicito `if body:` per costruire prehash condizionale (con o senza body)
- `_direct_place_market_order()`: passa `json.dumps(body)` come body stringa a `_sign_headers("POST", path, body_str)`
- Rimosso `import json` duplicato e inline import obsoleto

**Verifica:** Firma ora corrisponde alla specifica OKX HMAC-SHA256 sia per GET che per POST.
### TASK-1124 — Direct REST fallback per place_exit_bracket + fix double emergency close

**Status:** Done ✅
**Priorità:** CRITICA — blocca ogni bracket server-side su OKX EU accounts
**File:** `synthtrade/backend/app/execution/okx_exchange.py`

**Problema:** Due bug distinti:

1. **place_exit_bracket non ha fallback REST diretto:** a differenza di `place_market_order`, che ora prova ccxt e cade sul fallback `_direct_place_market_order` via POST `/api/v5/trade/order`, il metodo `place_exit_bracket` provava solo `self.client.create_order(type="oco", ...)` via ccxt. Se falliva con 50119 (lo stesso routing quirk EU di sempre), andava direttamente all'emergency close senza mai provare il REST diretto per POST `/api/v5/trade/order-algo`. Risultato: in sessione EU oggi nessun bracket TP/SL viene mai effettivamente piazzato — ogni entry finisce sempre in emergency close immediato.

2. **Doppio tentativo di emergency close:** l'adapter interno (`place_exit_bracket` nel suo blocco `except`) tentava un `close_position()` di emergenza, mentre il router in `BRACKET_FLOW CASO B` tentava anch'esso un `_handle_bracket_failed()` con un altro `close_position()`. Questo causava race condition e l'errore 51008 ("margin borrowing") sulla prima chiusura, mentre la seconda riusciva — rischio concreto di doppio ordine se entrambe avessero successo.

**Log osservato:**
```
[OKX BRACKET FAILED] OKB-EUR: okx {"msg":"API key doesn't exist","code":"50119"} — executing emergency market close
[OKX EMERGENCY CLOSE FAILED] ... sCode=51008 "Order failed. Your available EUR balance is insufficient..."
```

**Fix applicato:**
- ✅ Aggiunto metodo `_direct_place_exit_bracket()` che chiama direttamente POST `/api/v5/trade/order-algo` con firma HMAC-SHA256, body speculare a quello passato via ccxt, e stessa gestione errori di `_direct_place_market_order()` (sCode, sMsg, full_data)
- ✅ Modificato `place_exit_bracket()`: se CCXT fallisce con `50119` o `"API key doesn't exist"`, prova il fallback REST diretto prima di arrendersi
- ✅ Se il fallback REST diretto fallisce anch'esso, solleva `ExitProtectionError` **senza** tentare emergency close interno — il router (`BRACKET_FLOW CASO B`) è l'unico proprietario della procedura di chiusura d'emergenza, eliminando la race condition del doppio tentativo
- ✅ Se l'errore CCXT NON è 50119 (es. parametri invalidi), solleva direttamente `ExitProtectionError` senza fallback REST

**Verifica:** Il prossimo bracket su OKX EU non deve più produrre `[OKX BRACKET FAILED]` per 50119 — deve passare tramite REST diretto e piazzare correttamente il TP/SL server-side.

---
### TASK-1101 — Config provider OKX e credenziali demo/live

**Status:** ✅ DONE — implementato 2026-07-03 (verificato 2026-07-08)
**Priorità:** ALTA
**Dipendenze:** TASK-1100 per conferma header demo

**Obiettivo:** aggiungere `EXCHANGE_PROVIDER=okx`, credenziali OKX demo/live e computed field generici senza rompere Binance legacy.

**Completato:**
- ✅ **1101.A — Settings**: `EXCHANGE_PROVIDER`, `OKX_API_KEY`, `OKX_SECRET_KEY`, `OKX_PASSPHRASE`, `OKX_BASE_URL` in `config.py` (linee 107-120)
- ✅ **1101.B — Computed fields**: `exchange_api_key`, `exchange_secret_key`, `exchange_passphrase`, `exchange_demo`, `exchange_display_name` (linee 135-167)
- ✅ **1101.C — Sicurezza live**: `ALLOW_LIVE_MODE=false` blocca live, nessun log di secret/passphrase
- ✅ **1101.D — Env example**: `.env.example` documenta OKX demo/live, passphrase obbligatoria, differenza URL EU vs global
- ✅ **1101.E — Test**: Default provider okx, override env OKX, Binance legacy backward compat

**File coinvolti:**
- `synthtrade/backend/app/config.py` — Settings class con campi OKX
- `synthtrade/backend/.env.example` — documentazione setup OKX
### TASK-1102 — ExchangeProtocol v2 provider-neutral

**Status:** ✅ DONE — implementato 2026-07-03 (verificato 2026-07-08)
**Priorità:** ALTA
**Dipendenze:** TASK-1101

**File coinvolti:**
- `synthtrade/backend/app/execution/exchange_models.py`

**Obiettivo:** sostituire semantiche Binance-specifiche (`place_oco_order`, symbol compact-only, filtri Binance) con richieste di dominio SynthTrade: market order, close position, symbol rules, exit bracket, fee tier certificato.

**Completato:**
- ✅ **1102.A — Modelli dominio**: `SymbolRef`, `SymbolRules`, `MarketOrderRequest`, `ClosePositionRequest`, `ExitBracketRequest`, `ExchangeOrder`, `ExitBracketOrder`, `FeeTier` tutti in `exchange_models.py`
- ✅ **1102.B — Protocollo**: `ExchangeAdapterProtocol` in `exchange_models.py` (linee 212-237) con `place_exit_bracket` (non `place_oco_order`)
- ✅ **1102.C — Compat Binance**: `BinanceExchangeAdapter` preservato, `place_oco_order` come wrapper deprecato
- ✅ **1102.D — Errori comuni**: `ExitProtectionError`, `ExchangeAuthError`, `ExchangeNetworkError`, `UnsupportedInstrumentError`
- ✅ **1102.E — Test**: FakeOkxAdapter implementa protocollo, testato in test_okx_integration.py (12/12 PASS)
### TASK-1103 — OkxExchangeAdapter REST base

**Status:** ✅ DONE — implementato 2026-07-03
**Priorità:** ALTA
**Dipendenze:** TASK-1102

**Obiettivo:** implementare balance, holdings, ticker, symbol rules, instrument discovery, market order e fee tier per OKX via ccxt/nativo, usando Demo Trading in test manuale.

**Completato 2026-07-03:**
- ✅ `synthtrade/backend/app/execution/okx_exchange.py` implementa `ExchangeAdapterProtocol`
- ✅ `get_balance(asset)`, `get_holdings()`, `get_ticker_price(symbol)` con cache 15s
- ✅ `get_symbol_rules(SymbolRef)` con cache 5min (lotSz/minSz/tickSz/maxMktSz/maxMktAmt)
- ✅ `get_trade_fee(SymbolRef)` — fee OKX sono rebate negativi (maker=-0.002, taker=-0.0035)
- ✅ `place_market_order(MarketOrderRequest)` — spot cash, supporta `tgtCcy=quote_ccy`
- ✅ `close_position(ClosePositionRequest)`, `place_exit_bracket(ExitBracketRequest)`
- ✅ `get_open_exit_orders()`, `cancel_open_exit_orders()`
- ✅ `from_settings()` classmethod costruisce da `app.config.settings`
### TASK-1104 — OKX Exit Bracket server-side

**Status:** ✅ DONE — implementato 2026-07-03 (verificato 2026-07-08)
**Priorità:** CRITICA
**Dipendenze:** TASK-1100, TASK-1103

**Obiettivo:** implementare `place_exit_bracket()` per OKX con TP/SL server-side e emergency close se la protezione fallisce.

**Completato:**
- ✅ **1104.A — Decisione tecnica**: Confermato uso `order-algo` (POST `/api/v5/trade/order-algo`) con `tpTriggerPx`/`slTriggerPx` e `tpOrdPx="-1"`/`slOrdPx="-1"` per market order al trigger. Documentato in `okx-demo-spike-results.md`.
- ✅ **1104.B — Request model**: `ExitBracketRequest(symbol, side, quantity, tp_price, sl_price, entry_order_id, fee_tier)` in `exchange_models.py`
- ✅ **1104.C — Price validation**: `rules.round_price()` e `rules.round_qty()` applicati. Long close sell: TP sopra last, SL sotto last.
- ✅ **1104.D — Place bracket**: `place_exit_bracket()` in `okx_exchange.py` (righe 279-359) parametri OKX mappati, `algoId` parsato da risposta, raw payload preservato.
- ✅ **1104.E — Emergency close**: Se bracket fallisce → market close immediato + `ExitProtectionError` sollevato. Se emergency close fallisce → log error ma eccezione propagata comunque.
- ✅ **1104.F — Test**: TASK-1111 test 1111.B copre bracket reject → emergency close → no DB open. Test 1111.A copre happy path bracket success.

**File coinvolti:**
- `synthtrade/backend/app/execution/okx_exchange.py` — `place_exit_bracket()`
- `synthtrade/backend/app/execution/exchange_models.py` — `ExitBracketRequest`, `ExitBracketOrder`, `ExitProtectionError`
- `synthtrade/backend/tests/integration/test_okx_integration.py` — test 1111.A e 1111.B
- `synthtrade/backend/tests/integration/fake_okx_adapter.py` — `simulate_tp_fill()`, `bracket_fails`

**Verifica:** Nessuna posizione salvata su DB senza bracket confermato o close di emergenza (testato in 1111.B).
### TASK-1105 — OkxWSClient market data

**Status:** ✅ DONE — completato 2026-07-08 con fix end-to-end grafico live
**Priorità:** ALTA
**Dipendenze:** TASK-1100

**Obiettivo:** sostituire `BinanceWSClient` nel path scalping con un client provider-neutral e parser OKX per candle/trade.

**Completato 2026-07-08:**
- ✅ Market data (candele/trade) sempre su endpoint live, non condizionato da `demo`
- ✅ Canale `candle1m` spostato su WS business (`wss://ws.okx.com:8443/ws/v5/business`), `trades` resta su WS public
- ✅ Rimosso logica EU-specific per WS pubblico (causava DNS loop su `wsaws.okx.com`)
- ✅ Frontend `_normalizeSymbol()` aggiunto per risolvere mismatch `BTCEUR` vs `BTC-EUR`
- ✅ `router.py`: corretto return path in `GET /candles/{symbol}` per `past_candles` vuoto

**File:**
- `synthtrade/backend/app/scalping/engine/okx_ws_client.py`
- `synthtrade/backend/app/scalping/router.py`
- `synthtrade/frontend/synthtrade-ui/src/app/scalping/components/live-chart.component.ts`
### TASK-1106 — OkxOrderEventStream per fill TP/SL

**Status:** ✅ DONE — implementato 2026-07-03
**Priorità:** CRITICA
**Dipendenze:** TASK-1100, TASK-1104

**Obiettivo:** normalizzare gli eventi OKX di fill bracket nello stesso formato consumato da `_on_order_update`.

**Completato 2026-07-03:**
- ✅ `synthtrade/backend/app/execution/okx_order_event_stream.py` implementa stessa interfaccia di `UserDataStreamManager`
- ✅ Login WS OKX con firma HMAC-SHA256 + base64
- ✅ Sottoscrizione canali `orders` e `algo-orders`
- ✅ `_normalize_order` e `_normalize_algo_order` mappano stati OKX → dict contratto router
- ✅ Fee OKX negative (rebate) → `commission = abs(fee)` per compatibilità router
- ✅ `from_settings()` classmethod
- ✅ `exchange_factory.py` aggiornato con `get_order_event_stream()` provider-aware
### TASK-1107 — Router scalping provider-neutral

**Status:** ✅ DONE (100%) — provider-neutral completo incluso `_live_close_position`
**Priorità:** CRITICA
**Dipendenze:** TASK-1102, TASK-1105, TASK-1106

**Obiettivo:** rimuovere assunzioni Binance da start/stop/restore sessione, costruendo exchange, market WS e order stream via factory.

**Completato 2026-07-03:**
- ✅ Entry flow: `place_exit_bracket(ExitBracketRequest)` provider-neutral
- ✅ Bracket failure handler: `_handle_bracket_failed` usa `cancel_open_exit_orders` + `ClosePositionRequest`
- ✅ `_on_order_update`: usa `bracket_id` e campo `leg` (OKX: take_profit/stop_loss diretto)
- ✅ `_live_close_position`: convertito a provider-neutral (`cancel_open_exit_orders`, `get_holdings`, `get_symbol_rules.round_qty`, `close_position(ClosePositionRequest)`)
- ✅ Session start/DB/WS/order stream provider-neutral
- ✅ 12/12 integration tests passano (TASK-1111)
### TASK-1108 — DB migration provider e order ids generici

**Status:** ✅ DONE — Migration applicata a Supabase
**Priorità:** ALTA
**Dipendenze:** TASK-1107

**Obiettivo:** aggiungere provider, account mode, order ids e raw payload a sessioni/trade mantenendo compatibilita' con lo storico Binance.

**File:** `synthtrade/supabase/migrations/20260703000000_task1108_okx_provider_columns.sql`

**Colonne aggiunte e verificate:**
- `scalping_sessions`: exchange_provider, exchange_account_mode, exchange_demo, fee_tier_*
- `scalping_trades`: exchange_provider, exchange_order_id, exchange_bracket_id, exchange_tp/sl_order_id, exchange_raw
- Index: idx_scalping_trades_exchange_order_id/bracket_id
- Backfill: oco_order_list_id → exchange_bracket_id
### TASK-1109 — Frontend exchange-neutral

**Status:** ✅ DONE — label "Saldo Binance" dinamica (OKX/Binance/Exchange)
**Priorità:** MEDIA
**Dipendenze:** TASK-1107, TASK-1108

**Completato 2026-07-03:**
- ✅ `dashboard.model.ts`: aggiunto `exchange_provider?: string` a `DashboardStats`
- ✅ `dashboard.page.ts`: `balanceLabel()` computed signal → "Saldo OKX" / "Saldo Binance" / "Saldo Exchange"
- ✅ `dashboard.py`: aggiunto `exchange_provider` nel return dict
### TASK-1110 — Market data/backtest factory cleanup

**Status:** ✅ DONE — HistoricalLoader OKX via ccxt, Binance come fallback
**Priorità:** MEDIA
**Dipendenze:** TASK-1101, TASK-1103

**Obiettivo:** rimuovere `ccxt.binance()` diretto da market data, generator/backtest e servizi condivisi; usare factory provider-aware.

**Completato 2026-07-03:**
- ✅ `_load_from_okx()` via ccxt async `fetch_ohlcv`, EU URL override con guard `if v`
- ✅ `_load_from_binance()` come metodo separato
- ✅ `load_ohlcv()` dispatch su `settings.EXCHANGE_PROVIDER`
- ✅ Fallback a Binance solo per simboli non-EUR se OKX fallisce
- ✅ Fix NoneType in ccxt URL dict comprehension (`if v else v`)

**File:** `synthtrade/backend/app/scalping/backtest/historical_loader.py`
### TASK-1111 — Test integration con fake OKX adapter

**Status:** ✅ DONE — 12/12 test passano
**Priorità:** ALTA
**Dipendenze:** TASK-1107

**Obiettivo:** coprire start -> entry -> bracket -> fill -> DB/UI close senza chiamate reali, con fake adapter e fake order stream.

**Completato 2026-07-03:**
- ✅ `fake_okx_adapter.py` — FakeOkxAdapter + FakeOrderStream senza rete
- ✅ **1111.A** — Happy path: entry → bracket → TP fill → position closed
- ✅ **1111.B** — Bracket failure: entry OK → bracket reject → emergency close → no DB open
- ✅ **1111.C** — Stop session: cancel bracket → market close → DB reason=session_stop
- ✅ **1111.D** — Restore open: bracket attivo → order stream restart → TP fill ricevuto
- ✅ **1111.E** — Restore closed: no bracket su exchange → DB reconciled
- ✅ **1111.F** — Fee/net pricing: OKX rebate abs() corretto

**Bug trovato e fixato:** router usava fee OKX negative raw (`-0.0035`) in `_net_to_gross_pct`, producendo TP/SL invertiti. Fix: `abs(fee)` su `entry_fee_pricing` e `exit_fee_pricing` in `router.py`.

**File:**
- `synthtrade/backend/tests/integration/fake_okx_adapter.py`
- `synthtrade/backend/tests/integration/test_okx_integration.py`
- `synthtrade/backend/app/scalping/router.py` (bug fix fee abs)
### TASK-1113 — Cutover OKX live readiness

**Status:** ✅ DONE — 2026-07-08
**Priorità:** CRITICA
**Dipendenze:** TASK-1112

**Obiettivo:** rendere OKX provider primario, aggiornare setup operativo, checklist go-live e primo test live minimo solo dopo conferma manuale.

**Completato 2026-07-08:**
- ✅ **1113.A — Default config**: `.env.example` già configurato con `EXCHANGE_PROVIDER=okx` e `TRADING_MODE=test`. Binance legacy documentato come fallback.
- ✅ **1113.B — Safety gates**: `ALLOW_LIVE_MODE=false`, `TRADING_MODE=test`, `SCALPING_FORCE_PAPER=true` già attivi. Trade value minimo consigliato: Paper 10€, Demo 10€, Live iniziale 20€.
- ✅ **1113.C — Smoke tests**: Health check OK (`{"status":"ok"}`), Instruments OKX caricati (1INCH-EUR, BTC-EUR, ecc.), Candele OKX verificabili via `/candles/btceur`.
- ✅ **1113.D — Runbook**: Creato `docs/analysis/okx-live-runbook.md` con setup API key, safety gates, smoke test checklist, emergency stop procedure, go-live checklist, rischi e mitigazioni.
- ✅ **1113.E — Decisione go-live**: Documentata in runbook §7. Primo trade live minimo (20€) richiede conferma manuale esplicita.

**Decisioni chiave:**
- OKX è default operativo dal 2026-07-03 (TASK-1101), confermato da sessioni paper di luglio
- Live trading non può partire accidentalmente (ALLOW_LIVE_MODE=false, SCALPING_FORCE_PAPER=true)
- Runbook disponibile per agenti futuri in `docs/analysis/okx-live-runbook.md`
- Prima del go-live live reale, serve validazione bracket in demo reale (TASK-1100.G pendente)
### TASK-1114 — OKX fee tier e net pricing parity

**Status:** ✅ DONE — 2026-07-08
**Priorità:** CRITICA
**Dipendenze:** TASK-1100, TASK-1103, TASK-1104

**Obiettivo:** preservare su OKX la logica attuale di fee reali: recupero fee tier a inizio sessione, `fee_tier_certified`, calcolo TP/SL lordo da target netto, log `[NET_PRICING]`, PnL/trade log coerenti e commissioni reali da fill.

**Completato 2026-07-08:**
- ✅ **1114.A — Fee model**: `FeeTier(maker, taker, certified, raw, source)` già in `exchange_models.py` (linee 96-102). Persistenza su sessione via `_execution_state["fee_tier"]` e `fee_tier_certified`.
- ✅ **1114.B — Quote-aware commission conversion**: Già implementata in `router.py` — se `exit_commission_asset != quote_asset`, usa `exchange.get_ticker_price(f"{asset}/{quote}")` per conversione generica (es. OKB/EUR, BNB/USDT). Non più hardcoded BNB→USDC.
- ✅ **1114.C — Net to gross**: `_net_to_gross_pct()` parametrizzata con `entry_fee_pricing` e `exit_fee_pricing`. OKX rebate negativi gestiti con `abs()` (fix TASK-1111).
- ✅ **1114.D — Log `[NET_PRICING]` arricchito**: Ora include `provider`, `symbol`, `maker`, `taker`, `certified` in aggiunta ai target netti/lordi esistenti.
- ✅ **1114.E — Position/trade updates**: Position update mostra target netti (TASK-885). Trade log salva fee reali via WebSocket e fee tier attese. Commissioni negative OKX (rebate) normalizzate con `abs()`.
- ✅ **1114.F — Tests**: Coperto dal test `test_1111f_net_to_gross_pricing_okx_fees()` in `test_okx_integration.py` — verifica fee OKX rebate + net pricing con `abs()` corretto.

**File coinvolti:**
- `synthtrade/backend/app/scalping/router.py` — `[NET_PRICING]` log arricchito, `abs()` su fee OKX rebate
- `synthtrade/backend/app/execution/exchange_models.py` — `FeeTier` dataclass
- `synthtrade/backend/app/execution/okx_exchange.py` — `get_trade_fee()` con OKX rebate
- `synthtrade/backend/tests/integration/test_okx_integration.py` — test 1111f fee/net pricing

**Verifica:** log sessione paper 2026-07-08 mostra `[NET_PRICING] provider=okx symbol=BTCEUR maker=... taker=... certified=...` con target netti e lordi coerenti.
### TASK-1115 — Dashboard balance provider-neutral

**Status:** ✅ DONE — okx_balance.py + dispatch provider in dashboard API
**Priorità:** ALTA
**Dipendenze:** TASK-1101, TASK-1103

**Completato 2026-07-03:**
- ✅ `okx_balance.py`: fetch funding + trading wallet OKX, conversione EUR via tickers REST
- ✅ `dashboard.py`: dispatch dinamico `okx_balance` vs `binance_balance` su `EXCHANGE_PROVIDER`
- ✅ Smoke test: 112k€ saldo demo OKX (BTC, XRP, EUR, USDC, ETH) ✅
### TASK-1116 — Audit collector Binance/Futures per migrazione OKX

**Status:** ✅ DONE — EUR symbols graceful skip implementato su tutti i collector Binance Futures
**Priorità:** ALTA
**Dipendenze:** TASK-1105

**Obiettivo:** identificare e gestire tutte le fonti Binance usate dai segnali e opportunity: funding rate, open interest, long/short ratio, CVD trade stream, Binance announcements, market data/backtest.

**Completato 2026-07-03:**
- ✅ `open_interest.py`: EUR symbols → `None` in `FUTURES_SYMBOL_MAP` + `logger.debug` + `return None`
- ✅ `funding_rate.py`: idem
- ✅ `long_short_ratio.py`: idem
- ✅ Nessun WARNING 400 Bad Request su BTC-EUR, ETH-EUR, SOL-EUR ecc.
- ⚠️ **Bug scoperto 2026-07-09**: OKB-EUR non è nella mappa `FUTURES_SYMBOL_MAP` → tenta chiamata Binance Futures e fallisce con 400. Vedi TASK-1116.B.
### TASK-1116.D — DB migration: aggiungere mode='TEST' al CHECK constraint

**Status:** ✅ DONE — migration creata e committata (commit d5ef9c3)
**Priorità:** CRITICA
**Dipendenze:** TASK-1116

**Problema:** Sessione avviata con `mode='test'` (OKX Demo Trading) fallisce l'INSERT in `scalping_sessions` perché il CHECK constraint `scalping_sessions_mode_check` ammette solo `'PAPER', 'LIVE', 'BACKTEST'`.

**Log osservato:**
```
Failed to insert session in DB: {'code': '23514', 'message': "new row for relation 'scalping_sessions' violates check constraint 'scalping_sessions_mode_check'"}
```

**File coinvolti:**
- `synthtrade/supabase/migrations/20260709000000_task1116d_add_test_mode_check.sql` (nuovo)

**Fix:**
```sql
ALTER TABLE scalping_sessions DROP CONSTRAINT scalping_sessions_mode_check;
ALTER TABLE scalping_sessions ADD CONSTRAINT scalping_sessions_mode_check
  CHECK (mode IN ('PAPER', 'LIVE', 'BACKTEST', 'TEST'));
```

**Verifica:** Migration creata, da applicare a Supabase.

---
### TASK-1116.E — Fallback REST diretto per get_trade_fee() OKX

**Status:** ✅ DONE — fallback implementato (commit d5ef9c3)
**Priorità:** ALTA
**Dipendenze:** TASK-1103

**Problema:** `get_trade_fee()` fallisce con errore `50119 API key doesn't exist` su account EU OKX. La chiave è valida (il balance viene letto), ma ccxt routing interno punta a `www.okx.com` invece che a `eea.okx.com`.

**Log osservato:**
```
OKX get_trade_fee failed for OKB/EUR: okx {"msg":"API key doesn't exist","code":"50119"} — using fallback
Fee tier [okx]: maker=0.001, taker=0.001 certified=False
```

**File coinvolti:**
- `synthtrade/backend/app/execution/okx_exchange.py`

**Fix:**
- Aggiungere fallback REST diretto in `get_trade_fee()` analogo a quello esistente per `fetch_balance()`
- Endpoint: `GET /api/v5/account/trade-fee?instType=SPOT&instId={symbol}`

**Verifica:** Fee tier OKX Demo (rebate negativi) viene letto correttamente, `certified=True`.

---
### TASK-1116.F — Fix `mode_valid` sempre FAILED nel session health check

**Status:** ✅ DONE — commit 14d5af2
**Priorità:** MEDIA — non blocca la sessione (resta `running`), ma inquina i log ogni ~30-90s e nasconde altri problemi reali nel rumore

**Dipendenze:** TASK-1116.D (ha introdotto `mode='TEST'` come valore valido a livello DB, ma non a livello di health check applicativo)

**Problema:** `session_health_job` in `app/scheduler/scalping_jobs.py` valida `mode` contro `("paper", "live")` senza includere `"test"`.

**File coinvolto:**
- `synthtrade/backend/app/scheduler/scalping_jobs.py` — linea 226

**Impatto:** Warning falso-positivo ogni ~60-90s, rumore log, rischio azioni indesiderate future.

**Fix:** Aggiornare `mode_valid` per accettare anche `"test"` (case-insensitive).

**Verifica:** Sessione `mode=test` mostra `mode_valid=True` nei log health check.
### TASK-1117 — Fix DB constraint `session_signal_log_decision_type_check`

**Status:** ✅ DONE — 2026-07-08
**Priorità:** MEDIA
**Dipendenze:** TASK-1100

**Problema:** nel log compare `decision_type='rejected_short_unsupported'`, valore non incluso nel CHECK constraint della tabella `session_signal_log` (che ammette solo `execute`, `block_conflict`, `mean_reversion_override`, `hold_existing_position`, `rejected_other`). Coerente con il gap noto sullo short selling (nessuna implementazione ancora), ma comporta la perdita silenziosa di questi log specifici.

**Obiettivo:** aggiungere `rejected_short_unsupported` (o valore equivalente) al CHECK constraint, oppure mappare esplicitamente su `rejected_other` nel writer finché lo short non è implementato.

**Completato 2026-07-08:**
- ✅ **1117.A — Audit writer**: `log_rejected_short_unsupported()` si trova in `app/core/signal_log_writer.py` (linee 197-222). Usa `decision_type="rejected_short_unsupported"` dentro `log_signal_decision()`. Il valore non era incluso nel CHECK constraint DB.
- ✅ **1117.B — Migration**: Creata `synthtrade/supabase/migrations/20260708000000_task1117_fix_decision_type_check.sql`. DROP + ADD del constraint con valori aggiuntivi: `rejected_short_unsupported`, `execution_error` (già usato da `log_execution_error` ma assente dal constraint).
- ✅ **1117.C — Verifica**: Log nei log della sessione paper 2026-07-08 mostrano 5 occorrenze di `error 23514` per `rejected_short_unsupported` — confermato che il problema era attivo. Con la migration applicata, questi insert non produrranno più violazioni.

**Nota:** La migration va applicata su Supabase tramite psql o Supabase MCP. Il backend in esecuzione usa `_DummyClient` (test/dev), non il client Supabase reale.

**File coinvolti:**
- `synthtrade/supabase/migrations/20260708000000_task1117_fix_decision_type_check.sql` — migration creata
- `synthtrade/backend/app/core/signal_log_writer.py` — writer già corretto (usa `rejected_short_unsupported`)
### TASK-1118 — Audit symbol normalization in frontend Angular

**Status:** ✅ DONE — 2026-07-08
**Priorità:** MEDIA
**Dipendenze:** TASK-1105

**Problema:** il mismatch simbolo `BTCEUR` (stato sessione) vs `BTC-EUR` (instId OKX) causava scarto silenzioso di ogni candela real-time nel `LiveChartComponent`. Lo stesso tipo di mismatch potrebbe presentarsi in altri componenti Angular che consumano il WS scalping.

**Obiettivo:** auditare tutti i componenti che confrontano simboli provenienti da fonti diverse (stato sessione vs eventi WS provider-specific) e applicare `_normalizeSymbol()` dove serve.

**Completato 2026-07-08:**
- ✅ **1118.A — grep confronti:** Trovati 3 componenti con confronto simbolo non normalizzato:
  - `live-chart.component.ts` — già fixato (usava `_normalizeSymbol()` privato)
  - `market-intel-panel.component.ts` (linea 200) — `data.symbol.toUpperCase() !== this.symbol.toUpperCase()` → scartava eventi `BTC-EUR` se la sessione riportava `BTCEUR`
  - `performance-panel.component.ts` — solo analisi quote asset (safe)
  - `session-controls.component.ts` — solo analisi quote asset (safe)
- ✅ **1118.B — Fix componenti:** `market-intel-panel.component.ts` fixato con `SymbolUtils.equals()`
- ✅ **1118.C — Refactor:** Creato `synthtrade/frontend/synthtrade-ui/src/app/scalping/utils/symbol-utils.ts` con `SymbolUtils.normalize()` e `SymbolUtils.equals()`. `live-chart.component.ts` refattorizzato per usare `SymbolUtils.equals()` invece del metodo privato.
- ✅ **1118.D — Verifica:** I componenti `trade-log/`, `position-ticker/` e `supervisor-log/` NON hanno confronti simbolo diretti — ricevono eventi WS già corretti dal backend. Il bug era limitato ai componenti che filtrano eventi per simbolo lato frontend.

**File creati/modificati:**
- `synthtrade/frontend/synthtrade-ui/src/app/scalping/utils/symbol-utils.ts` (NUOVO)
- `synthtrade/frontend/synthtrade-ui/src/app/scalping/components/live-chart.component.ts` — refactor a SymbolUtils
- `synthtrade/frontend/synthtrade-ui/src/app/scalping/components/market-intel-panel.component.ts` — fix confronto simbolo
### TASK-1119 — CRITICO: `OkxExchangeAdapter` manca metodi usati dal path LIVE, trade reale fallito

**Status:** ✅ DONE — commit 6d3b52b
**Priorità:** CRITICA — blocca ogni trade LIVE reale su OKX

**Dipendenze:** TASK-1103 (OkxExchangeAdapter), TASK-1107 (router provider-neutral)

**Problema:** `AttributeError: 'OkxExchangeAdapter' object has no attribute 'get_symbol_filters'` e `'get_btc_macro_context'` durante tentativo trade LIVE su OKB-EUR.

**File coinvolti:**
- `synthtrade/backend/app/execution/okx_exchange.py`

**Completato:**
- ✅ **1119.B** — `get_symbol_filters()` aggiunto come wrapper su `get_symbol_rules()` (fix import)
- ✅ **1119.C** — `get_btc_macro_context()` implementato con fallback REST diretto per EU accounts

**Verifica:** Sessione live completa ciclo senza AttributeError.
### TASK-1120 — CRITICO: saldo "Starting balance" sessione LIVE ~2x rispetto al saldo reale OKX

**Status:** ✅ DONE — commit 16b26f2
**Priorità:** CRITICA — impatta risk management/position sizing su capitale reale

**Dipendenza:** nessuna

**Problema:** Sessione LIVE logga "Starting balance: 45.99 EUR" mentre OKX reale mostra €28,87. Dashboard okx_balance.py è corretto (28,88 EUR).

**Ipotesi:** Due funzioni di calcolo balance distinte e non allineate.

**File coinvolti:**
- `synthtrade/backend/app/core/okx_balance.py` — versione corretta (dashboard)
- `synthtrade/backend/app/scalping/router.py` — punto log "✓ Starting balance"
- `synthtrade/backend/app/execution/okx_exchange.py` — se `get_balance()` ha logica diversa

**Completato:**
- ✅ **1120.C** — `get_balance()` ora usa solo `availBal` via REST diretto, allineato a okx_balance.py

**Verifica:** Dashboard, log avvio sessione, e interfaccia OKX reale mostrano lo stesso totale EUR.

---
### TASK-1125 — Collector Intelligence: Diagnostica Coverage Reale per Simbolo

**Status:** Done ✅
**Priorità:** ALTA — prerequisito per qualsiasi fix successivo dei collector intelligence
**Fase:** 1a (diagnostica pura, zero rischio, nessun cambio di comportamento)
**Commit:** `1263803`

**Problema:** Il coverage/bypass del `SignalAggregator` confronta "quanti collector hanno risposto" contro un `min_collectors` fisso pensato per 8 collector totali. Per simboli come OKB-EUR, 3 collector (funding_rate, open_interest, long_short_ratio) sono strutturalmente impossibili da ottenere su OKX per uno spot EUR senza perpetual. Il denominatore attuale non distingue collector che non hanno ancora risposto (transitorio) da collector che non risponderanno mai (strutturale).

**Modifiche:**
1. **`is_symbol_supported()`** in `FundingRateCollector`, `OpenInterestCollector`, `LongShortRatioCollector` — ogni collector ora può indicare se un simbolo supporta strutturalmente quel dato, usando la stessa `FUTURES_SYMBOL_MAP` già presente
2. **`get_configurable_weight_total(symbol)`** in `SignalScoreEngine` — calcola il peso configurabile totale ESCLUDENDO i collector strutturalmente impossibili per quel simbolo
3. **Log `[COVERAGE_REAL]`** in `_build_snapshot()` — mostra `real_coverage`, `structurally_unavailable`, `no_response_transient`, `old_coverage_field` per ogni ciclo di scoring, senza modificare alcun comportamento

**File modificati:**
- `synthtrade/backend/app/scalping/intelligence/collectors/funding_rate.py`
- `synthtrade/backend/app/scalping/intelligence/collectors/open_interest.py`
- `synthtrade/backend/app/scalping/intelligence/collectors/long_short_ratio.py`
- `synthtrade/backend/app/scalping/intelligence/signal_score_engine.py`

**Verifica:** Syntax check passato su tutti e 4 i file. I test esistenti (collector empty response, http error, interpret_rate, rate_to_score) passano. I test `test_collect_success` e `test_rate_to_score_clamped` falliscono pre-esistenti (bug mock asincrono nei test, non correlato).

**Esplicitamente fuori scope per questo task:**
- Nessuna modifica a `min_collectors`, `signal_strength_threshold`, o bypass in `signal_aggregator.py`
- Nessuna redistribuzione pesi tra collector
- Nessun nuovo collector OKX-specifico

**Decisioni chiave:**
- Coverage reale = peso risposto / peso configurabile (esclude collector che non risponderanno MAI per quel simbolo)
- `old_coverage_field` loggato accanto per confronto — nessun comportamento di trading cambiato

---
### FIX-2026-07-10 — Router passa quantity invece di quote_amount per BUY market order su OKX (sCode=51020)

**Status:** Done ✅
**Priorità:** CRITICA — blocca trading live su OKX per simboli con minSz più alta

**File:** `synthtrade/backend/app/scalping/router.py`

**Problema:** Il router costruiva `MarketOrderRequest(quantity=_qty_precise, ...)` per i BUY market in live mode, passando la quantità in base currency (0.2851 OKB) invece dell'importo in quote currency (20.0 EUR). Questo impediva a OKX di usare `tgtCcy=quote_ccy`, causando l'errore `sCode=51020: "Your order should meet or exceed the minimum order amount."` perché OKX interpretava `sz=0.2851` come quantità base OKB — che poteva essere sotto il minimo consentito per il symbol.

**Log osservato:**
```
qty_raw=0.285, step_size=1e-05, qty_precise=0.2851
→ OKX API error 1: sCode=51020 "Your order should meet or exceed the minimum order amount."
```

**Fix applicato:**
- Il `MarketOrderRequest` ora passa `quote_amount=_trade_val` (20.0 EUR) invece di `quantity=_qty_precise` (0.2851 OKB)
- OKX riceve `tgtCcy=quote_ccy` e calcola autonomamente la quantità base nel rispetto dei propri vincoli `minSz`
- `exec_qty` ora prende la quantità filled dalla risposta OKX (`market_res.filled` o `market_res.quantity`) invece di usare la quantità precalcolata
- Il calcolo di `_qty_precise` rimane come guardia per il balance check e il controllo `minQty`, ma non viene più passato all'exchange

**Dettaglio modifiche (righe 1634-1645):**
```python
MarketOrderRequest(
    symbol=symbol,
    side="buy",
    quantity=None,
    quote_amount=_trade_val,
    ...
)
```
OKX riceve `tgtCcy=quote_ccy` e calcola la quantità autonomamente.

---

## EPICA OKX — Migrazione Binance → OKX (Completata)

**Status:** ✅ Completata (luglio 2026)
**Nota:** Archiviata da TASKS.md il 15/07/2026. I task attivi post-migrazione vivono in EPICA AUDIT POST-OKX.

### TASK-1100 — OKX Demo Spike: auth, market order, exit bracket, WS fill

**Status:** ✅ DONE — tutti i sottotask A–H completati (14/07/2026)
**Priorità:** CRITICA
**Dipendenze:** API key OKX Demo Trading ✅

**Obiettivo:** verificare empiricamente OKX Demo Trading prima di modificare il runtime live.

**Stato 2026-07-03 10:45:**
- ✅ **1100.A** — Auth REST: risolto blocco `50119` con URL `eea.okx.com` per EU accounts
- ✅ **1100.B** — Server time: OK
- ✅ **1100.C** — Instrument discovery: 527 spot, 16 EUR live (`BTC-EUR` default confermato)
- ✅ **1100.D** — Fee tier: maker -0.2%, taker -0.35% (rebate!)
- ✅ **1100.E** — Market order: 10€ → 0.00022883 BTC @ 43700€, fee rebate OK
- ✅ **1100.F** — Exit bracket: algoId piazzato con successo, metodo `order-algo` confermato
- ✅ **1100.H** — WS public trades: subscription OK, parser implementato, CVD mapping verificato
- ✅ **1100.G** — WS private EEA bloccato (errore 60032) → REST polling fallback

**Stato 2026-07-08 (Fix grafico OKX end-to-end):**
- ✅ Frontend: `_normalizeSymbol()` per mismatch `BTCEUR` vs `BTC-EUR`
- ✅ Backend: candle1m su WS business, trades su WS public
- ✅ Backend: market data sempre live (rimosso branch EU-specific)
- ✅ Backend: router.py type guard e percorso ritorno candles

**Stato 2026-07-09 (Fix regressione chart):**
- ✅ Indentazione endpoint `@router.get("/candles/{symbol}")` corretta

### TASK-1112 — Validazione Demo Trading end-to-end

**Status:** ✅ DONE (paper mode) — sessione BTC-EUR con OKX Demo WS funzionante, 9 bug fixati
**Completato:** 2026-07-03

**Bug fixati durante validazione:**
1. `set_sandbox_mode()` crash NoneType → rimosso
2. ccxt URL override fragile → httpx diretto
3. Mock generator mancava `_save_open_position_to_db`
4. Strategy 2 lookup entry_time mismatch
5. Paper session_stop usava prezzo reale OKX → entry_price
6. OkxWSClient symbol normalization

### TASK-1126 — Fix: TP/SL fill detection su OKX EU accounts

**Status:** ✅ DONE (2026-07-13)
**Priorità:** CRITICA

**Problema:** OKX EU accounts → `orders-algo-history?ordType=oco` ritorna 400.
**Fix:** Usare `orders-history?state=filled` + seed iniziale con algo orders.

### TASK-1116.B — Bug: OKB-EUR mancante in FUTURES_SYMBOL_MAP collector

**Status:** ✅ Done (corretto in lavorazione TASK-1153)

**Fix:** `"OKBEUR": None, "OKB-EUR": None` aggiunti a `FUTURES_SYMBOL_MAP` + graceful skip OKX.

### TASK-1116.C — Collector adapter provider-aware (OKX derivatives)

**Status:** ⚠️ Superseded — consolidato in TASK-1153

---

## EPICA COLLECTOR INTELLIGENCE — Task completati

### TASK-1150 — Abilitare whale collector + verificare sentiment su OKX

**Status:** ✅ Done (14/07/2026)

**Modifiche:** `SCALPING_WHALE_ENABLED=true` in `.env`, verifica log whale/sentiment.

### TASK-1151 — OrderBookImbalanceCollector

**Status:** ✅ Done (14/07/2026)
**File:** `collectors/order_book_imbalance.py`
**Endpoint:** `GET https://eea.okx.com/api/v5/market/books?instId={instId}&sz=20`

### TASK-1152 — SpreadCollector

**Status:** ✅ Done (14/07/2026) — wiring INTENZIONALMENTE DISATTIVATO
**File:** `collectors/spread.py`
**Endpoint:** `GET https://eea.okx.com/api/v5/market/ticker?instId={instId}`

### TASK-1153 — CollectorAdapter provider-aware per funding_rate / open_interest / long_short_ratio

**Status:** ✅ Done (14/07/2026) — supersede TASK-1116.C, TASK-COLLECTOR-001

**Modifiche:**
- `_provider_maps.py`: `OKX_PERPETUAL_MAP` (BTC/ETH/OKB → SWAP)
- `okx_exchange.py`: adapter methods `get_open_interest`/`get_funding_rate`/`get_long_short_ratio`
- 3 collector: provider-aware OKX con graceful skip
- `signal_score_engine.py`: parametro `adapter`
- `fake_okx_adapter.py`: per test
- **Test:** `test_collector_provider_aware.py` (14 test, verdi)

### TASK-1154 — Sentiment collector: fallback affidabile

**Status:** ✅ Done (14/07/2026) — supersede TASK-COLLECTOR-002

**File:** `collectors/sentiment.py` — 3 fonti: CryptoCompare, NewsAPI, RSS (fallback).

### TASK-1155 — Whale collector: fix parsing + API key + structurally_unavailable

**Status:** ✅ Done (2026-07-15)

**Bug risolti:**
1. Parsing errato `-EUR` suffix → strip completo suffissi quote
2. CryptoCompare senza API key → header `Apikey` aggiunto
3. OKB strutturalmente assente → `is_symbol_supported()` esclude OKB/BNB

### TASK-1156 — On-chain collector: fallback Blockchair

**Status:** ✅ Done (2026-07-15) — *supersede TASK-COLLECTOR-004*

**File:** `signal_score_engine.py`: peso onchain 0.0→0.05

### TASK-1157 — Verifica CVD grace period

**Status:** ✅ Done (verificato 15/07/2026) — *supersede TASK-COLLECTOR-005*

Grace period già implementato in `signal_score_engine.py:426-436`: CVD escluso dallo score se `_trades_since_reset < 100`. CVD calculator wired con peso 0.20, window reset ogni 1000 trades. Nessun lavoro aggiuntivo richiesto.

### TASK-1158 — Spike: equivalente OKX per Long/Short Ratio

**Status:** ✅ Done (2026-07-14)

**Risultato:** OKX ha l'endpoint rubik `long-short-account-ratio`. Ratio → long/short%: `ratio/(1+ratio)*100`. Bug `OKX_PERPETUAL_MAP["OKB"]=None` corretto.

---

## Migrazione Bybit — CHIUSA

**Status:** Chiusa (2026-07-14)

**Motivazione:** Account Bybit EU non permette API key HMAC per trading automatizzato custom. Si resta su OKX come unico exchange operativo.

**Riferimenti tecnici (non attivi):**
- `docs/analysis/bybit-api-reference-analysis.md`
- `docs/plans/bybit-migration-architecture-and-plan.md`
- `docs/plans/bybit-migration-plan-v2.md`

---

## TASK-OKX-RECAL — Ricalibrazione SL/TP su fee OKX reali

**Status:** ✅ Done (14/07/2026)
**Priorità:** CRITICA (completata)

**Fee OKX reali:** maker=0.20%, taker=0.35%, round-trip=0.70%
**Target ricalibrati:** SL=1.05% (net 0.35%), TP=1.55% (net 0.85%), R:R=1.48:1

---

## Task da Investigare — Risultati (2026-07-01)

> Bug identificati in `MASTER_RECAP.md` del 26/06/2026.

| Task | Status | Note |
|------|--------|------|
| TASK-INVEST-001 — sync strategy_selected vs strategy_executed | ✅ FATTO | Corretto in frontend |
| TASK-INVEST-002 — Regressione doppio avvio WS | ✅ FATTO | Risolta |
| TASK-INVEST-003 — Buffer mismatch warmup/ExecutionLoop | ✅ FATTO | Allineamento confermato |
| TASK-INVEST-004 — pause_trading permanente su regime unknown | ✅ FATTO | Ripresa automatica implementata |
| TASK-INVEST-005 — Position.entry_commission non popolato | ✅ FATTO | Popolato via WS (TASK-876) |
| TASK-INVEST-006 — get_trade_fee() fallback silenzioso | ✅ FATTO | `fee_tier_certified` implementato |
| TASK-INVEST-007 — GET /position non converte BNB→USDC | ✅ FATTO | Fix applicato in router.py |
| TASK-INVEST-008 — SELL mean-reversion bloccato da bias bullish | ✅ FATTO | Sblocco confermato |
| TASK-INVEST-009 — Insufficient funds per minNotional | ✅ FATTO | Fix minNotional applicato |
| TASK-INVEST-010 — Assenza cooldown dopo consecutive losses | ✅ FATTO | Pausa automatica implementata |
| TASK-INVEST-011 — Regime misclassification (volume-confirmed) | 🟡 APERTO | Nessuna logica volume-confirmed |
| TASK-INVEST-012 — Falling Knife Protection non implementata | 🟡 APERTO | Allineata a TASK-906 |
| TASK-INVEST-013 — trend_direction troppo sensibile | ⚠️ PARZIALE | Soglia troppo sensibile |
| TASK-INVEST-014 — Supervisor non ha visibilità blocco SHORT | ✅ FATTO | System prompt menziona blocco |
| TASK-INVEST-015 — APScheduler job missed ripetuti | ✅ FATTO | Log puliti |
| TASK-INVEST-016 — CryptoCompare/RSS feed intermittenti | ✅ FATTO | Feed stabili |
| TASK-INVEST-017 — Bias outcome_label Supervisor | ⚠️ PARZIALE | Usa solo PnL |
| TASK-INVEST-018 — Soglia dinamica senza decadimento | ⚠️ PARZIALE | Decay non implementato |
| TASK-INVEST-019 — 5/8 collector non funzionanti | ⚠️ PARZIALE | CVD/OI/LSR dipendono da futures |
| TASK-INVEST-020 — Slope filter EMA Cross | 🟡 APERTO | Nessuno slope filter |

**Nota:** I task INVEST aperti/parziali (011, 012, 013, 017, 018, 019, 020) sono stati parzialmente affrontati dai task collector intelligence (TASK-1150→1159). TASK-INVEST-019 è ora risolto con i provider-aware collectors.

---

## EPICA AUDIT POST-OKX — Fix critici + semplificazione + refactor

### TASK-1160 — Fix 5 NameErrors in router.py live trade path
**Status:** ✅ Done (16/07/2026)

### TASK-1161 — Fix circuit breaker on_success() mai chiamato
**Status:** ✅ Done (16/07/2026)

### TASK-1162 — Fix _sign_headers credenziali instance vs settings
**Status:** ✅ Done (16/07/2026)

### TASK-1163 — Fix OCO leg detection in order event stream
**Status:** ✅ Done (16/07/2026)

### TASK-1164 — OKX adapter: rimuovere strato CCXT, REST-only (httpx)
**Status:** ✅ Done (16/07/2026)

### TASK-1165 — Fix sl_pct_net inconsistente (WS initial state vs candle processor)
**Status:** ✅ Done (16/07/2026)

### TASK-1116.G — Instrument discovery environment-aware (Demo vs Live)
**Status:** ✅ Done (16/07/2026)

**Problema:** OKB-EUR è tradeable in live ma non esiste in Demo Trading (errore 51001). Il sistema non distingue i due cataloghi. L'endpoint `/exchange/instruments` non filtra per ambiente. Il frontend carica gli strumenti una volta sola senza re-fetch al cambio modalità. Nessuna validazione pre-sessione.

**Root cause:** `_direct_fetch_symbol_rules()` e l'endpoint `/exchange/instruments` chiamavano OKX senza header `x-simulated-trading: 1`, restituendo sempre il catalogo live. La cache non era environment-aware. Il frontend non passava mode al backend.

**Fix applicati:**
- Cache `(symbol, demo_flag)` tupla in `okx_exchange.py`
- Header `x-simulated-trading` in `_direct_fetch_symbol_rules()` e `list_instruments()`
- Endpoint `/exchange/instruments` accetta `?mode=test|live`, passa header demo
- Validazione pre-sessione con `UnsupportedInstrumentError` → errore `SYMBOL_NOT_AVAILABLE`
- Frontend: `getInstruments(mode?)` passa mode come query param
- Mode badge con tooltip nei session controls
- 8 nuovi test unit

**File:** `okx_exchange.py`, `router.py`, `exchange-symbols.service.ts`, `session-controls.component.ts`, `test_task_1116g.py`

---

### TASK-1170 — Fix log diagnostico COLLECTORS
**Status:** ✅ Done (16/07/2026)

### TASK-1171 — Elimina istanze fantasma SignalScoreEngine (BTCUSDT + OKBEUR)
**Status:** ✅ Done (16/07/2026)
**Fix multipli:**
1. `supervisor_check_job()` creava `SupervisorScheduler()` senza symbol → default BTCUSDT → engine phantom ogni 10min
2. `get_intel_snapshot` endpoint creava engine on-the-fly per ogni symbol richiesto → OKBEUR phantom dal frontend
3. Health check considerava `paused` come fallimento (fix in commit separato)

**File:** `scalping_jobs.py`, `router.py`, `market-intel-panel.component.ts`

### TASK-1172 — Fix chart preview symbol blocked by stale session status
**Status:** ✅ Done (15/07/2026)

### TASK-1173 — LiveChartComponent: prezzo non si aggiorna
**Status:** ✅ Done (15/07/2026)

### TASK-1174 — Fix get_symbol_rules failure silently skips restore
**Status:** ✅ Done (16/07/2026)

### TASK-1175 — Fix algo history retry si blocca su risultati vuoti
**Status:** ✅ Done (16/07/2026)

### TASK-1176 — Fix adapter init failure log level
**Status:** ✅ Done (16/07/2026)

### TASK-1177 — Reconcile fill reali + fix critico supabase stub
**Status:** ✅ Done (16/07/2026)

### TASK-907 — Bug Frontend: dati mancanti su reload con sessione PAUSED
**Status:** ✅ Done (16/07/2026)

### TASK-908 — Resume Guard: blocca resume in regime bearish senza short
**Status:** ✅ Done (16/07/2026)
**Fix:** Guard in supervisor_scheduler.py, defense-in-depth in parameter_updater, context enhancement, 6 test.

### TASK-906 — Falling Knife Protection: blocca mean-reversion BUY durante crash
**Status:** ✅ Done (16/07/2026)
**Fix:** Guard in signal_aggregator.py: trend_direction=diverging + trend_5m < -20 → blocca. 12 test.

### TASK-898 — Trend Analysis da dati persistiti
**Status:** ✅ Done (16/07/2026)
**Risultato:** 19 trade analizzati, nessuna correlazione (r=0.004). Report: `docs/trend_analysis_report.md`.

### TASK-903 — RegimeDetector: isteresi K candele
**Status:** ✅ Done (16/07/2026)
**Fix:** Aggiunta isteresi K=3 in regime_detector.py. Il regime committed cambia solo se lo stesso candidato si osserva per 3 candele consecutive. Proprietà `pending_regime`/`pending_count` per debug. 15 test.

---

## Ordine di esecuzione consigliato (storico, pre-audit)

1. ~~**TASK-1100**~~ ✅ — spike OKX Demo Trading
2. ~~**TASK-1101 → TASK-1116**~~ ✅ — config, adapter REST, WS, order stream, etc.
3. ~~**TASK-1113**~~ — Cutover OKX live readiness
4. ~~**TASK-1114**~~ — OKX fee tier e net pricing parity
5. ~~**TASK-1117 → TASK-1118**~~ — Bug da recap 2026-07-08
6. ~~**TASK-OKX-RECAL**~~ ✅ — Ricalibrazione SL/TP
7. ~~**TASK-907 / TASK-908**~~ ✅ — bug non OKX (completati 16/07)

