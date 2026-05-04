# IntelliJ AI Assistant Rules — loom

> Leggi sempre `AGENT.md` all'inizio di ogni sessione.
> Questo file contiene solo istruzioni specifiche per JetBrains AI Assistant.
> Per l'architettura DOE, task management, commit protocol e handoff: vedi `AGENT.md`.

---

## 🚀 Setup Automatico

**Trigger:** "setup loom" / "configura il framework" / "inizializza"

**Comando:**
```bash
python loom/scripts/setup.py
```

---

## 💬 Comandi Naturali

| Utente dice | Tu esegui |
|-------------|----------|
| "start task TASK-001 'feature X'" | `python loom/scripts/task.py start TASK-001 "feature X"` |
| "list tasks" | `python loom/scripts/task.py list` |
| "complete task TASK-001" | `python loom/scripts/task.py complete TASK-001 "done"` |
| "start TDD task TASK-001 'feature X'" | `python loom/scripts/task_tdd.py start TASK-001 "feature X"` |
| "run tests" | `python loom/scripts/task_tdd.py test` |
| "sync configs" | `bash loom/scripts/sync-configs.sh` |
| "update task status TASK-001 Done" | `python loom/execution/task_status.py --action set-status --task-id TASK-001 --status "Done"` |
| "check for loom updates" | `python loom/scripts/check_updates.py` |
| "update loom" | `python loom/scripts/check_updates.py --update` |
| "list plugins" | `python loom/scripts/plugins.py list` |
| "add plugin from URL" | `python loom/scripts/plugins.py add --source <url>` |

---

## Best Practices IntelliJ AI Assistant

- Usa AI Assistant inline per refactoring e generazione codice contestuale
- Crea Run Configurations per script task.py e test suite
- Usa Live Templates per boilerplate standard (docstring, error handling)
- Chiedi conferma prima di operazioni irreversibili
