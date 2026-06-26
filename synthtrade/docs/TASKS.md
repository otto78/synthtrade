# TASKS.md — Task Tracking

> Tracciamento dei task attivi e completati per SynthTrade

---

## Active Tasks / Task Attivi

*Nessun task attivo al momento.*

---

## Completed Tasks / Task Completati

### TASK-887: Configurazione Claude Haiku 4.5 per Supervisor AI

**Status**: ✅ Completato  
**Data**: 2026-06-26  
**Descrizione**: Configurare Claude Haiku 4.5 come modello principale dedicato per il supervisor AI, con Claude Sonnet come fallback. Il sistema deve supportare configurazioni separate per `use_case` (pipeline_eval, supervisor) con storage nel database, variabili d'ambiente e UI frontend.

**Modifiche implementate**:

#### Database
- **Migration**: `supabase/migrations/20240626_add_use_case_to_llm_models.sql`
  - Aggiunta colonna `use_case` (TEXT) con constraint CHECK per 'pipeline_eval' o 'supervisor'
  - Aggiornamento dei record esistenti a 'pipeline_eval'
  - Ricreazione degli indici per includere `use_case`
  - Creazione di constraint unique su `(use_case, model)`

#### Backend
- **Repository**: `backend/app/db/repositories/llm_model_repository.py`
  - Aggiunto metodo `get_active_model_by_use_case()` per recuperare il modello attivo per un use_case specifico
  - Aggiunto metodo `get_models_by_use_case()` per filtrare per use_case

- **Service**: `backend/app/services/llm_model_service.py`
  - Aggiunto supporto per `use_case` in tutti i metodi CRUD
  - Logica di default a 'pipeline_eval' se non specificato

- **Config**: `backend/app/config.py`
  - Aggiunte variabili d'ambiente:
    - `SUPERVISOR_DEFAULT_MODEL` (default: "anthropic/claude-haiku-4.5")
    - `SUPERVISOR_FALLBACK_MODEL` (default: "anthropic/claude-sonnet-4.5")

- **Supervisor Client**: `backend/app/scalping/supervisor/supervisor_client.py`
  - Modificato per recuperare modello configurato da database invece di usare hardcoded
  - Implementato fallback al fallback_model se il default non è attivo

- **API**: `backend/app/api/llm_models_api.py`
  - Esteso endpoint per supportare parametro `use_case` opzionale
  - Endpoint di attivazione ora attiva per un use_case specifico

#### Frontend
- **Model**: `frontend/synthtrade-ui/src/app/core/models/llm-models.model.ts`
  - Aggiunta proprietà `use_case` alle interfacce

- **Service**: `frontend/synthtrade-ui/src/app/core/services/llm-models.service.ts`
  - Aggiunto supporto per `use_case` in tutte le chiamate API

- **Page**: `frontend/synthtrade-ui/src/app/pages/llm-models/llm-models.page.ts`
  - Implementata UI con tabs per "Pipeline Eval" e "Supervisor AI"
  - Filtraggio automatico per use_case selezionato

#### Scripts
- **Init Script**: `backend/init_supervisor_models.py`
  - Script per inizializzare i modelli supervisor nel database
  - Usa OpenRouter IDs completi (es: `anthropic/claude-haiku-4.5`)
  - Popula 3 modelli: Haiku 4.5 (default), Sonnet 4.5 (fallback), GPT-4o-mini

**Verifica**:
- ✅ Migration applicata con successo
- ✅ Modelli supervisor inizializzati nel database
- ✅ Backend configurato correttamente
- ✅ Frontend con tabs funzionante
- ✅ Supervisor client recupera modello da database

---

## Task Archive / Archivio Task

*Task archiviati completati in precedenza.*
