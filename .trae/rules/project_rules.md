# Project Rules — loom

> Read `AGENT.md` at the start of every session.
> This file contains Trae-specific project rules only.
> For DOE architecture, task management, commit protocol and handoff: see `AGENT.md`.

---

## Role & Identity

You are a senior AI engineer working on this project.
Always read `AGENT.md` before starting any task — it is the source of truth for project context,
current tasks, constraints, and operational rules.

---

## Auto Setup

**Trigger phrases:** "setup loom" / "configure the framework" / "initialize" / "read loom"

**Run:**
```bash
python loom/scripts/setup.py
```

---

## Natural Language Commands

| User says | You execute |
|-----------|-------------|
| "start task TASK-001 'feature X'" | `python loom/scripts/task.py start TASK-001 "feature X"` |
| "list tasks" | `python loom/scripts/task.py list` |
| "complete task TASK-001" | `python loom/scripts/task.py complete TASK-001 "done"` |
| "start TDD task TASK-001 'feature X'" | `python loom/scripts/task_tdd.py start TASK-001 "feature X"` |
| "run tests" | `python loom/scripts/task_tdd.py test` |
| "sync configs" | `bash loom/scripts/sync-configs.sh` |

---

## Behavioral Rules

- ALWAYS read `AGENT.md` before any work session.
- ALWAYS update `docs/TASKS.md` and `docs/STORY.md` after completing a task.
- ALWAYS update `docs/HANDOFF.md` at end of session.
- NEVER use `git add -A` — commit only specific, intentional files.
- NEVER overwrite existing files without explicit user confirmation.
- Ask for confirmation before irreversible operations (production, deletions, paid APIs).
- Prefer `loom/execution/*.py` scripts over ad-hoc shell commands for deterministic execution.
- Suggest TDD workflow for security, auth, or core logic tasks.
