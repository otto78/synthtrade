# Active Tasks — SynthTrade

> **Fonte di verità:** questo file contiene il lavoro in corso e programmato.
> I task completati sono spostati in [ARCHIVE_TASKS.md](file:///c:/Users/andrea.mazzarotto/myJobs/SynthTrade/docs/ARCHIVE_TASKS.md).
> Le idee generali e i piani a lungo termine sono in [BACKLOG.md](file:///c:/Users/andrea.mazzarotto/myJobs/SynthTrade/docs/BACKLOG.md).

---

## 🛠️ Fase 6A — Refactoring & Logica Applicativa

> **Obiettivo:** Risolvere il debito tecnico architetturale, configurazioni dinamiche e comunicazione in tempo reale.


### TASK-217 — 🔵 Refactor: `SignalResolver` iniettato nel costruttore
**Status:** Done ✅  
**Completato:** 2026-05-19
**Priorità:** Media

**Descrizione:**
Refactoring dell'architettura di gestione dei segnali per permettere l'iniezione del resolver. Attualmente i segnali vengono processati individualmente; il resolver permetterà di valutare un set di segnali collettivamente (es. per limitare posizioni simultanee o scegliere il segnale più forte).

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

---

### TASK-222 — 🔵 Refactor: intervalli configurabili da `Settings`
**Status:** In Progress  
**Priorità:** Media

**Descrizione:**
Rendere configurabili tutti gli intervalli di scheduler e loop periodici via `app.config.Settings`, eliminando valori hardcoded in `app/scheduler/jobs.py` e nelle parti del backend che gestiscono job ricorrenti.

**Piano di Attuazione:**
1.  **Audit del codice**:
    *   Identificare tutti gli intervalli hardcoded in backend, con attenzione a `app/scheduler/jobs.py` e a eventuali `asyncio.sleep(...)` usati in loop ricorrenti.
2.  **Definizione dei setting**:
    *   Verificare gli intervalli già presenti in `app/config.py`.
    *   Aggiungere o confermare i seguenti campi se mancanti:
        *   `SCHEDULER_PIPELINE_INTERVAL_MIN: int = 60`
        *   `SCHEDULER_SIGNAL_INTERVAL_MIN: int = 5`
        *   `SCHEDULER_MONITOR_INTERVAL_SEC: int = 30`
        *   `SCHEDULER_HEARTBEAT_INTERVAL_SEC: int = 10`
        *   `SCHEDULER_MONITOR_PNL_INTERVAL_SEC: int = 30`
        *   `EXECUTION_INTERVAL_SECONDS: int = 300` (se non già referenziato da altri moduli).
3.  **Refactor scheduler**:
    *   Aggiornare `setup_scheduler(...)` in `app/scheduler/jobs.py` per usare i valori da `settings`.
    *   Sostituire i valori hardcoded `seconds=30`, `seconds=10` e simili con i corrispondenti setting.
4.  **Documentazione e configurazione**:
    *   Aggiungere i nuovi valori al modello `.env` o ai commenti di `app/config.py`.
    *   Assicurarsi che il team sappia che tutti gli intervalli possono essere modificati da ambiente.
5.  **Verifica e test**:
    *   Scrivere test di configurazione che confermino i default dei nuovi setting.
    *   Se possibile, aggiungere un test su `setup_scheduler` che verifica che i job usino gli intervalli da `settings`.
    *   Eseguire `pytest` sui moduli interessati dopo il refactor.

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

### TASK-235 — 🔵 Refactor: template `.jinja2` separato da logica
**Status:** In Progress  
**Priorità:** Media

**Descrizione:**
Separare i template di prompt e i contenuti Jinja2 dalla logica Python, spostando il testo strutturato in file `.jinja2` dedicati e mantenendo il codice Python limitato alla sola preparazione dei dati e al rendering.

**Piano di Attuazione:**
1.  **Audit dei template attuali**:
    *   Individuare i template inline in `app/ai/prompt_builder.py` e ogni altro file Python che genera prompt o output HTML dinamico.
2.  **Creazione della struttura template**:
    *   Creare `app/ai/templates/` o `app/templates/` per contenere i file Jinja2.
    *   Spostare `SYSTEM_PROMPT` e `PROMPT_TEMPLATE` in file come `system_prompt.jinja2` e `evaluation_prompt.jinja2`.
3.  **Implementazione del renderer**:
    *   Aggiungere `app/ai/template_loader.py` o una funzione in `prompt_builder.py` che usa `jinja2.Environment` con `FileSystemLoader`.
    *   Se `jinja2` non è presente, aggiungere la dipendenza a `requirements.txt`.
4.  **Refactor `prompt_builder.py`**:
    *   Ridurre `build_system_prompt()` e `build_prompt()` a wrapper di rendering.
    *   Mantenere separata la logica dei dati (`EvalPromptInput`) dal layout del prompt.
5.  **Verifica e test**:
    *   Aggiungere test unitari di rendering template che controllano la sostituzione dei campi.
    *   Aggiungere test di integrazione che verificano i prompt generati da `build_prompt()` e `build_system_prompt()`.

### TASK-238 — 🔵 Refactor: `@async_retry` decorator in `ai/retry.py`
**Status:** In Progress  
**Priorità:** Media

**Descrizione:**
Estrarre la logica di retry asincrono attualmente implementata manualmente in `app/ai/model_client.py` in un decorator riutilizzabile `async_retry`. Questo migliora la chiarezza, riduce duplicazione e rende il backoff configurabile.

**Piano di Attuazione:**
1.  **Audit della logica di retry esistente**:
    *   Analizzare `app/ai/model_client.py` e verificare i percorsi di retry per 429/503 e timeout.
2.  **Creazione di `ai/retry.py`**:
    *   Implementare un decorator `async_retry(max_retries, backoff_base, retry_exceptions)`.
    *   Gestire sleep esponenziale e logging dei tentativi.
3.  **Refactor `ModelClient`**:
    *   Applicare il decorator a `_call_model` o incapsulare il loop di retry all'interno del decorator.
    *   Usare i valori `settings.AI_MAX_RETRIES` e `settings.AI_BACKOFF_BASE` per popolare il decorator.
4.  **Documentazione**:
    *   Aggiornare `app/config.py` con commenti esplicativi per ritardi e numero di retry.
5.  **Verifica e test**:
    *   Scrivere test per `async_retry` che simulano errori temporanei e verificano il numero di chiamate.
    *   Testare il comportamento del client in caso di `429`, `503` e `Timeout`.

### TASK-245 — 🔵 Refactor: `MAX_CONCURRENT_EVALS` da `Settings`
**Status:** In Progress  
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

---

### TASK-FE-001 — ✅ Migliora progress bar generazione con stepper a 3 fasi proporzionale
**Status:** Done ✅  
**Completato:** 2026-05-19  
**Priorità:** Media

**Descrizione:**
Sostituita la progress bar animata fittizia (che partiva al 100% in 30s) con uno stepper visivo a 3 fasi (Analisi Mercato → Ottimizzazione AI → Backtesting) con larghezza proporzionale allo stato backend.

**Modifiche:**
- `generation-progress.component.ts`: nuovo layout stepper con cerchi ✅/⏳/○, barra proporzionale (33/66/100%), indicatori visivi, step 3 "Backtesting" ora correttamente attivato su `completed`

---

## 🧪 Fase 6B — Test Suite & Stabilità Frontend

> **Obiettivo:** Garantire la massima stabilità della UI ed eliminare regressioni tramite test E2E e unitari.
> **Status E2E:** ✅ **SUITE E2E COMPLETATA** (27 test implementati - 2026-05-19)

---

## 📈 EPIC-400 — Pipeline di Esecuzione (Finalizzazione)

> **Obiettivo:** Completare l'integrazione del motore di trading reale e la visualizzazione avanzata dei trade.
> **Status:** ✅ **EPIC COMPLETATA** (2026-05-19)
