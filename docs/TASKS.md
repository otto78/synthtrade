# Active Tasks — SynthTrade

> **Fonte di verità:** questo file contiene il lavoro in corso e programmato.
> I task completati sono spostati in [ARCHIVE_TASKS.md](file:///c:/Users/andrea.mazzarotto/myJobs/SynthTrade/docs/ARCHIVE_TASKS.md).
> Le idee generali e i piani a lungo termine sono in [BACKLOG.md](file:///c:/Users/andrea.mazzarotto/myJobs/SynthTrade/docs/BACKLOG.md).

---

## 🛠️ Fase 6A — Refactoring & Logica Applicativa

> **Obiettivo:** Risolvere il debito tecnico architetturale, configurazioni dinamiche e comunicazione in tempo reale.


### TASK-222 — 🔵 Refactor: intervalli configurabili da `Settings`
**Status:** Done ✅  
**Completato:** 2026-05-19
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

### TASK-235 — 🔵 Refactor: template `.jinja2` separato da logica
**Status:** Done ✅  
**Completato:** 2026-05-19
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

## 🧪 Fase 6B — Test Suite & Stabilità Frontend

> **Obiettivo:** Garantire la massima stabilità della UI ed eliminare regressioni tramite test E2E e unitari.
> **Status E2E:** ✅ **SUITE E2E COMPLETATA** (27 test implementati - 2026-05-19)

---

## 📈 EPIC-400 — Pipeline di Esecuzione (Finalizzazione)

> **Obiettivo:** Completare l'integrazione del motore di trading reale e la visualizzazione avanzata dei trade.
> **Status:** ✅ **EPIC COMPLETATA** (2026-05-19)
