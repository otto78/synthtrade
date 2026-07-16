# AGENT.md — {PROJECT_NAME}
# Source of Truth / Fonte di Verità

> This file is read by all AI agents (Claude, Cursor, Windsurf, loom, VS Code, GitHub Copilot).
> Do not duplicate these instructions in other files — they all reference here.
> Questo file è letto da tutti gli agenti AI. Non duplicare queste istruzioni in altri file.

---

## What is SynthTrade / Cos'è SynthTrade

SynthTrade è una piattaforma di trading algoritmico che utilizza AI per analizzare i mercati finanziari e eseguire strategie di scalping automatizzate. Il sistema integra LLM per valutazione di pipeline e decisioni di supervisione.

**Stack**: Python 3.11 / FastAPI / PostgreSQL / Supabase / Angular  
**Principle**: Service-oriented architecture con separazione chiara tra logica di business e presentation layer

---

## Tech Stack / Stack Tecnologico

### Backend / Frontend / Core
- **Language**: Python 3.11 (backend), TypeScript 5.0 (frontend)
- **Framework**: FastAPI (backend), Angular (frontend)
- **Database**: PostgreSQL via Supabase
- **Auth**: Supabase Auth
- **Validation**: Pydantic (backend), TypeScript interfaces (frontend)

### Testing
- **Framework**: pytest (backend), Jest (frontend)
- **Coverage**: Aim for 80%+

### Infrastructure
- **Hosting**: Supabase (database), Custom hosting (application)
- **CI/CD**: GitHub Actions
- **Secrets**: `.env` (never commit / mai committare)

### AI Layer
- **Orchestration**: Custom supervisor AI system
- **LLM Gateway**: OpenRouter
- **LLM Models**: Claude Haiku 4.5, Claude Sonnet 4.5, GPT-4o-mini
- **MCP**: Supabase MCP server integration

### Channels / Canali
- **Primary**: Web application
- **Secondary**: TBD

### Extended Infrastructure / Infrastruttura Estesa
- **Container**: Docker (planned)
- **Monitoring**: TBD
- **GPU**: Not required (cloud LLM inference)

---

## Project Structure / Struttura Progetto

```
synthtrade/
├── AGENT.md                    ← this file (source of truth / fonte di verità)
├── AGENTS.md                   ← cross-tool configuration
├── docs/
│   ├── TASKS.md                ← task tracking / tracciamento task
│   ├── BACKLOG.md              ← future ideas / idee future
│   ├── STORY.md                ← project history / storia progetto
│   ├── CHANGELOG.md            ← version changelog / changelog versioni
│   └── HANDOFF.md              ← agent handoff notes / note passaggio agente
│
├── backend/
│   ├── app/
│   │   ├── api/                ← API endpoints
│   │   ├── config.py           ← configuration and environment variables
│   │   ├── db/
│   │   │   └── repositories/   ← database repositories
│   │   ├── services/           ← business logic services
│   │   └── scalping/
│   │       └── supervisor/     ← supervisor AI implementation
│   └── init_supervisor_models.py ← initialization script
│
├── frontend/
│   └── synthtrade-ui/
│       └── src/
│           ├── app/
│           │   ├── core/
│           │   │   ├── models/ ← TypeScript models
│           │   │   └── services/ ← API services
│           │   └── pages/      ← Angular pages
│
├── _supabase_test_stub/        ← test stub (DO NOT RUN — shadows real supabase package)
│
└── .env                        ← secrets (never commit / mai committare)
```

---

## Framework Operativo: Loom 🧵

Questo progetto utilizza **[Loom Framework](https://github.com/otto78/loom-framework)** per la gestione operativa.

Loom fornisce:
- Task management automatizzato
- TDD workflow integrato
- Supporto multi-IDE
- Comandi in linguaggio naturale

**Configurazione**: Vedi `AGENT.md` (questo file) e la cartella `loom/`

---

## DOE Architecture / Architettura DOE

### Level 1 — Directives (`loom/directives/`)
SOPs for each domain: how to add features, coding standards, conventions.
SOP per ogni dominio: come aggiungere feature, standard di codice, convenzioni.

### Level 2 — Orchestration (this agent)
Read directives → choose right approach → call execution scripts → handle errors → update TASKS.md.
Legge direttive → sceglie approccio → chiama script esecuzione → gestisce errori → aggiorna TASKS.md.

### Level 3 — Execution (`loom/execution/`)
Deterministic scripts for: git commits, task management, deployments.
Script deterministici per: commit git, gestione task, deploy.

---

## Agent Operating Principles / Principi Operativi Agente

### 1. {Your core principle / Il tuo principio core}
```
Routes thin, Services fat / Route leggere, Servizi pesanti
```

### 2. Always use existing libraries / Usa sempre librerie esistenti
```
Quando scrivi codice Python, SEMPRE considera le librerie già installate nel progetto.
- Verifica le dipendenze in pyproject.toml, requirements.txt, o poetry.lock
- Usa librerie già disponibili invece di aggiungerne nuove
- Evita di fixare errori Pylance/Type checkers dovuti a librerie mancanti se la funzionalità è disponibile in librerie esistenti
- Se un errore Pylance sembra strano, verifica prima se la libreria è già installata ma il type checker non la vede
```

### 3. Always write tests for critical features / Sempre test per feature critiche
```
"start TDD task TASK-XXX 'description'"
```

### 4. Use loom scripts for task management / Usa script loom per task
```bash
python loom/scripts/task.py start TASK-XXX "Description"
python loom/scripts/task.py complete TASK-XXX "Done" --bump minor
python loom/scripts/task.py list
```

### 5. Update task status programmatically / Aggiorna stato task via script
```bash
python loom/execution/task_status.py --action set-status --task-id TASK-XXX --status "Done"
python loom/execution/task_status.py --action list
python loom/execution/task_status.py --action get --task-id TASK-XXX
```
**You MUST update task status** after completing or starting a task. / **DEVI aggiornare lo stato dei task** dopo aver completato o avviato un task.

### 6. Check and apply framework updates / Controlla e applica aggiornamenti framework
```bash
python loom/scripts/update.py --status     # current version / versione attuale
python loom/scripts/update.py --check      # check for updates / controlla aggiornamenti
python loom/scripts/update.py --apply      # download and apply / scarica e applica
python loom/scripts/update.py --rollback   # restore previous / ripristina precedente
```

**Natural language triggers / Trigger in linguaggio naturale:**
- `"check for loom updates"` / `"ci sono aggiornamenti di loom?"` / `"controlla aggiornamenti loom"` → `--check`
- `"update loom"` / `"aggiorna loom"` / `"scarica aggiornamenti loom"` → `--apply`
- `"loom version"` / `"versione loom"` / `"che versione di loom ho?"` → `--status`
- `"rollback loom"` / `"ripristina loom"` → `--rollback`

When running `--check`: inform the user of the result and suggest `--apply` if an update is available.
During `--apply`: the `loom/` directory is replaced; project files (AGENT.md, IDE configs, docs/) are **never touched**.


### 7. Manage custom directive plugins / Gestisci plugin direttive custom
```bash
python loom/scripts/plugins.py list
python loom/scripts/plugins.py add --source https://github.com/user/directives
python loom/scripts/plugins.py remove --name directives
```

### 8. Commit only worked files / Committa solo file modificati
```bash
python loom/execution/git_commit.py --files "file1,file2" --message "feat: description [TASK-XXX]"
```

### 9. Always update TASKS.md before ending / Aggiorna sempre TASKS.md prima di terminare

### 10. Ask before irreversible operations / Chiedi prima di operazioni irreversibili

### 11. Versioning and Changelog / Versioning e Changelog (Mandatorio)

Ogni modifica che altera il comportamento del sistema deve:
1. Incrementare la versione semantica (es: `version` in `pyproject.toml`)
2. Aggiungere entry in `directives/changelog.md` con messaggio per l'utente
3. Questo garantisce che gli utenti ricevano notifiche delle nuove capacità

### 12. Commit and Push after every fix / Commit e Push dopo ogni fix

Dopo ogni modifica richiesta dall'utente:
1. **Commit selettivo**: `git add <file1> <file2>` — SOLO file modificati direttamente
2. Commit con messaggio coerente: `git commit -m "feat: descrizione [TASK-XXX]"`
3. Push sul branch remoto

**IMPORTANTE**: In ambiente concorrente, NON usare `git add -A` o `git add .` per evitare di committare file incompleti di altri agenti.

Prima del push, aggiorna SEMPRE:
- `docs/STORY.md` — versione, fix, evoluzioni
- `docs/TASKS.md` — stato lavoro

### 13. DB ↔ Local Files Alignment / Allineamento DB ↔ File Locali (Mandatorio)

Se una direttiva o configurazione è usata sia da file locali (`directives/*.md`) sia dal database (`agent_prompts`):
1. Aggiorna il file locale richiesto
2. Verifica lo stato corrente su DB
3. Applica la sincronizzazione su DB nella stessa sessione
4. Verifica il risultato (versione, contenuti)

---

## Project-Specific Rules / Regole Specifiche Progetto

### LLM Model Configuration
- **OpenRouter IDs**: Usare sempre ID completi OpenRouter (es: `anthropic/claude-haiku-4.5`), non nomi corti
- **Use_case**: Configurare modelli per use_case specifici (`pipeline_eval`, `supervisor`)
- **Default behavior**: Se use_case non specificato, default a 'pipeline_eval' per retrocompatibilità
- **Supervisor models**: Il supervisor deve avere sempre un primary e un fallback model configurati

### Database Migrations
- Eseguire le migrations via Supabase dashboard o CLI
- Verificare sempre le migrations in ambiente di test prima di produzione
- DROP INDEX è accettabile se immediatamente ricreato

### API Design
- Tutte le API devono supportare use_case come parametro opzionale
- Seguire il pattern Repository → Service → API
- Validare input con Pydantic models

### Frontend
- Usare TypeScript interfaces per tipi complessi
- Seguire il pattern Model → Service → Page
- Filtrare automaticamente per use_case nella UI

---

## File Organization / Organizzazione File

- `.tmp/` — file intermedi temporanei, rigenerabili. **Mai committare.**
- `execution/` — script Python deterministici (i tool)
- `directives/` — SOP in Markdown (le istruzioni operative)
- `.env` — variabili d'ambiente e chiavi API (**mai committare**)
- `docs/` — documentazione progetto (TASKS.md, STORY.md, etc.)
- `loom/` — framework Loom (non modificare)
- `AGENT.md` — configurazione progetto (questo file)

---

## Bootstrap — First Run / Prima Esecuzione

**When you read this file for the first time, check if the `docs/` folder exists and contains all required files. If any are missing, create them immediately using the templates below.**

**Quando leggi questo file per la prima volta, verifica che la cartella `docs/` esista e contenga tutti i file richiesti. Se mancano, creali subito usando i template qui sotto.**

### Required files in `docs/` / File richiesti in `docs/`

| File | Purpose |
|------|---------|
| `docs/TASKS.md` | Task tracking — active and completed tasks |
| `docs/BACKLOG.md` | Future ideas and experiments |
| `docs/STORY.md` | Project history, versions, key decisions |
| `docs/CHANGELOG.md` | Version changelog |
| `docs/HANDOFF.md` | Agent handoff notes |

If `docs/` or any of these files is missing, run:

```bash
python loom/scripts/setup.py --auto
```

Or create them manually from the templates in `loom/templates/docs/`.

---

## Current Status / Stato Attuale

Read `docs/TASKS.md` for active tasks. / Leggi `docs/TASKS.md` per task attivi.  
Read `docs/STORY.md` for project history. / Leggi `docs/STORY.md` per storia progetto.  
Read `docs/HANDOFF.md` for last session notes. / Leggi `docs/HANDOFF.md` per note ultima sessione.

---

**Version**: 1.1.0  
**Last updated**: 2026-06-26  
**Framework**: loom v1.0
