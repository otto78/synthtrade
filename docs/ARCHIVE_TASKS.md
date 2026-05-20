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
