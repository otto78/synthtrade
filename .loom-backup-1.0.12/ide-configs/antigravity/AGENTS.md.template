# loom Rules — Cross-Tool Configuration

> Questo file è letto da: **Antigravity**, **Windsurf**, **VS Code**, **VS Code Insider**.
> Per regole IDE-specific vedi: `GEMINI.md` (Antigravity), `CLAUDE.md` (Claude Code),
> `.cursor/rules/loom.mdc` (Cursor), `.aiassistant/rules/loom.md` (IntelliJ).
> **Fonte di verità progetto:** `AGENT.md`

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

## 🏗️ Architettura DOE (sintesi)

**D** — **Directives**: `loom/directives/*.md` per le regole operative.
**O** — **Orchestration**: Tu (l'AI) pianifichi e coordini.
**E** — **Execution**: Script in `loom/scripts/` e `loom/execution/`.

Fonte di verità: `AGENT.md` nella root del progetto.
