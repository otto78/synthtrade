# Cline Agent Rules — loom

> Read `AGENT.md` at the start of every session.
> This file contains Cline-specific instructions only.
> For DOE architecture, task management, commit protocol and handoff: see `AGENT.md`.

---

## 🚀 Auto Setup

**Trigger:** "setup loom" / "configure the framework" / "initialize" / "read loom"

**Command:**
```bash
python loom/scripts/setup.py
```

---

## 💬 Natural Language Commands

| User says | You execute |
|-----------|-------------|
| "start task TASK-001 'feature X'" | `python loom/scripts/task.py start TASK-001 "feature X"` |
| "list tasks" | `python loom/scripts/task.py list` |
| "complete task TASK-001 'done'" | `python loom/scripts/task.py complete TASK-001 "done"` |
| "start TDD task TASK-001 'feature X'" | `python loom/scripts/task_tdd.py start TASK-001 "feature X"` |
| "run tests" | `python loom/scripts/task_tdd.py test` |
| "sync configs" | `bash loom/scripts/sync-configs.sh` |
| "update task status TASK-001 Done" | `python loom/execution/task_status.py --action set-status --task-id TASK-001 --status "Done"` |
| "check for loom updates" | `python loom/scripts/check_updates.py` |
| "update loom" | `python loom/scripts/check_updates.py --update` |
| "list plugins" | `python loom/scripts/plugins.py list` |
| "add plugin from URL" | `python loom/scripts/plugins.py add --source <url>` |
| "parse tasks" | `python loom/scripts/parse_tasks.py` |
| "extract tasks" | `python loom/scripts/extract_tasks.py` |

---

## 📝 Documentation Update — MANDATORY

After completing ANY task or making changes, you MUST update ALL of these:

| File | When |
|------|------|
| `docs/TASKS.md` | Before ending — update task status, add completion notes |
| `docs/STORY.md` | Add entry with version, changes, key decisions |
| `docs/HANDOFF.md` | At session end — summary for next agent |

**Never end a session without updating these three files.**

---

## Best Practices — Cline

- **Always read `AGENT.md` first** — before any work, read it to understand the current project state.
- **Use MCP tools** — leverage Cline's built-in tool use (file system, terminal, browser) for deterministic execution.
- **Ask before irreversible ops** — confirm before production deployments, deletions, or paid API calls.
- **Prefer loom execution scripts** — use `loom/execution/*.py` for git commits, status updates, and file ops.
- **Never use `git add -A`** — commit only specific, intentional files.
- **Update TASKS.md and STORY.md** after each completed task.
- **Handoff** — update `docs/HANDOFF.md` at end of session so next agent can resume seamlessly.