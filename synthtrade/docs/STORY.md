# STORY.md — Project History

> Storia del progetto SynthTrade, versioni, decisioni chiave ed evoluzioni

---

## Version 1.0.0 (Initial Release)

**Data**: TBD  
**Descrizione**: Versione iniziale di SynthTrade

---

## Version 1.1.0 — TASK-887

**Data**: 2026-06-26  
**Descrizione**: Introduzione configurazione multi-use_case per modelli LLM

### Modifiche Principali

#### Database Schema
- Aggiunta colonna `use_case` alla tabella `llm_models`
- Supporto per use_case distinti: `pipeline_eval` e `supervisor`
- Migrazione `20240626_add_use_case_to_llm_models.sql`

#### Architettura Backend
- Estensione del sistema di configurazione LLM per supportare use_case
- Separazione delle configurazioni per pipeline evaluation e supervisor AI
- Implementazione di fallback models per il supervisor

#### Frontend
- UI migliorata con tabs per gestione separata dei modelli per use_case
- Filtraggio automatico per categoria di utilizzo

### Decisioni Chiave

1. **Usare OpenRouter IDs completi**: Invece di nomi corti (es: `haiku-4.5`), usiamo ID completi OpenRouter (es: `anthropic/claude-haiku-4.5`) per evitare ambiguità e compatibilità con il gateway LLM.

2. **Default pipeline_eval**: Per retrocompatibilità, tutti i modelli esistenti sono stati migrati a `use_case='pipeline_eval'`.

3. **Fallback model per supervisor**: Il supervisor ha sia un default che un fallback per garantire continuità operativa se il primary model non è disponibile.

### Modelli Configurati

#### Pipeline Eval (default esistente)
- Varie configurazioni LLM per evaluation pipeline

#### Supervisor AI (nuovo)
- **Primary**: `anthropic/claude-haiku-4.5` (veloce, economico)
- **Fallback**: `anthropic/claude-sonnet-4.5` (più capace)
- **Alternative**: `openai/gpt-4o-mini`

---

## Prossimi Passi

- Monitoraggio performance del supervisor con Haiku 4.5
- Possibile ottimizzazione del system prompt del supervisor
- Valutazione integrazione di modelli aggiuntivi per use_case specifici
