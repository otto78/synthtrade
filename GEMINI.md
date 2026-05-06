# Antigravity Rules — loom

> Leggi sempre `AGENT.md` all'inizio di ogni sessione.
> Questo file contiene istruzioni specifiche per Antigravity (priorità su `AGENTS.md`).
> Per regole condivise con altri tool vedi `AGENTS.md`.

---

## 🚀 Setup Automatico

**Trigger:** "setup loom" / "configura il framework" / "read loom"

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

## Best Practices Antigravity

- Usa Agent Manager per task multi-step complessi e paralleli
- Ogni agente produce Artifacts (piani, diff, risultati) — rivedili prima di approvare
- Spawna agenti separati per task indipendenti (es. refactor auth + test E2E contemporaneamente)
- Chiedi conferma prima di operazioni irreversibili

---

> **⚠️ Nota Gemini CLI:** `~/.gemini/GEMINI.md` è condiviso con Gemini CLI (conflitto noto #16058).
> Usa `AGENTS.md` per regole progetto, questo file solo per override Antigravity-specific,
> per evitare conflitti con Gemini CLI.
