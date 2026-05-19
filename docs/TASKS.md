# Active Tasks — SynthTrade

> **Fonte di verità:** questo file contiene il lavoro in corso e programmato.
> I task completati sono spostati in [ARCHIVE_TASKS.md](file:///c:/Users/andrea.mazzarotto/myJobs/SynthTrade/docs/ARCHIVE_TASKS.md).
> Le idee generali e i piani a lungo termine sono in [BACKLOG.md](file:///c:/Users/andrea.mazzarotto/myJobs/SynthTrade/docs/BACKLOG.md).

---

## 🛠️ Fase 6A — Refactoring & Logica Applicativa

> **Obiettivo:** Risolvere il debito tecnico architetturale, configurazioni dinamiche e comunicazione in tempo reale.


### TASK-217 — 🔵 Refactor: `SignalResolver` iniettato nel costruttore
**Status:** In Progress  
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

### TASK-232 — 🔵 Refactor: `MarketRegimeDetector` con soglie configurabili
**Status:** In Progress  
**Priorità:** Media

### TASK-235 — 🔵 Refactor: template `.jinja2` separato da logica
**Status:** In Progress  
**Priorità:** Media

### TASK-238 — 🔵 Refactor: `@async_retry` decorator in `ai/retry.py`
**Status:** In Progress  
**Priorità:** Media

### TASK-245 — 🔵 Refactor: `MAX_CONCURRENT_EVALS` da `Settings`
**Status:** In Progress  
**Priorità:** Media

---

## 🧪 Fase 6B — Test Suite & Stabilità Frontend

> **Obiettivo:** Garantire la massima stabilità della UI ed eliminare regressioni tramite test E2E e unitari.
> **Status E2E:** ✅ **SUITE E2E COMPLETATA** (27 test implementati - 2026-05-19)

### TASK-186 — Unit Test `dashboard.page.spec.ts`
**Status:** To Do
**Priorità:** Media

### TASK-421 — Unit Test `active-trade.page.spec.ts`
**Status:** To Do
**Priorità:** Media

---

## 📈 EPIC-400 — Pipeline di Esecuzione (Finalizzazione)

> **Obiettivo:** Completare l'integrazione del motore di trading reale e la visualizzazione avanzata dei trade.
> **Status:** ✅ **EPIC COMPLETATA** (2026-05-19)
