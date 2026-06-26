# CHANGELOG.md — Version Changelog

> Registro delle modifiche versionate di SynthTrade

---

## [1.1.0] - 2026-06-26

### Added
- Supporto multi-use_case per configurazione modelli LLM
- Colonna `use_case` nella tabella `llm_models` (pipeline_eval, supervisor)
- Configurazione separata per Supervisor AI con fallback model
- UI frontend con tabs per gestione modelli per use_case
- Script di inizializzazione per modelli supervisor (`init_supervisor_models.py`)
- Variabili d'ambiente `SUPERVISOR_DEFAULT_MODEL` e `SUPERVISOR_FALLBACK_MODEL`

### Changed
- `llm_model_repository.py`: Aggiunti metodi per filtraggio per use_case
- `llm_model_service.py`: Esteso supporto use_case in tutti i metodi
- `supervisor_client.py`: Recupera modello configurato da database invece di hardcoded
- `llm_models_api.py`: Esteso endpoint per supportare use_case
- Frontend models, service e page aggiornati per supportare use_case

### Database
- Migration `20240626_add_use_case_to_llm_models.sql`
- Aggiunta constraint CHECK per use_case
- Aggiornamento record esistenti a 'pipeline_eval'
- Ricreazione indici con use_case
- Creazione constraint unique su (use_case, model)

---

## [1.0.0] - TBD

### Added
- Versione iniziale di SynthTrade
