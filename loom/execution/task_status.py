#!/usr/bin/env python3
"""
task_status.py - Read and update task status in docs/TASKS.md

Provides a simple interface for agents to check and update task status
without having to parse TASKS.md manually.

Usage:
    python loom/execution/task_status.py --action list
    python loom/execution/task_status.py --action get --task-id TASK-001
    python loom/execution/task_status.py --action set-status --task-id TASK-001 --status "Done"

Returns (JSON to stdout):
    {"tasks": [...]}
    {"task": {"id": "TASK-001", "title": "...", "status": "In Progress"}}
    {"success": true, "task_id": "TASK-001", "old_status": "In Progress", "new_status": "Done"}
"""

import argparse
import json
import re
import sys
from pathlib import Path


TASKS_FILE = Path("docs/TASKS.md")


def find_tasks_file() -> Path:
    """Find TASKS.md searching from cwd upward."""
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        candidate = parent / "docs" / "TASKS.md"
        if candidate.exists():
            return candidate
    return TASKS_FILE  # fallback


def parse_tasks(content: str) -> list[dict]:
    """Parse TASKS.md and return list of task dicts."""
    tasks = []
    current_section = "unknown"
    
    for line in content.splitlines():
        # Detect section
        if "## 🔄" in line or "## In Progress" in line:
            current_section = "In Progress"
        elif "## ✅" in line or "## Completed" in line:
            current_section = "Completed"
        elif "## ⏸️" in line or "## Not Started" in line or "## 📋" in line:
            current_section = "Not Started"
        
        # Detect task header
        match = re.match(r"^### (TASK-\d+)\s*[—-]\s*(.+)$", line)
        if match:
            tasks.append({
                "id": match.group(1),
                "title": match.group(2).strip(),
                "status": current_section
            })
    
    return tasks


def list_tasks() -> dict:
    """List all tasks from TASKS.md."""
    tasks_file = find_tasks_file()
    if not tasks_file.exists():
        return {"tasks": [], "warning": f"{tasks_file} not found"}
    
    content = tasks_file.read_text(encoding="utf-8")
    tasks = parse_tasks(content)
    return {"tasks": tasks, "file": str(tasks_file)}


def get_task(task_id: str) -> dict:
    """Get a specific task by ID."""
    result = list_tasks()
    for task in result.get("tasks", []):
        if task["id"] == task_id:
            return {"task": task}
    return {"task": None, "error": f"{task_id} not found"}


def set_status(task_id: str, new_status: str) -> dict:
    """Update the status of a task in TASKS.md."""
    tasks_file = find_tasks_file()
    if not tasks_file.exists():
        return {"error": f"{tasks_file} not found"}
    
    content = tasks_file.read_text(encoding="utf-8")
    
    # Find the task
    task_pattern = re.compile(
        rf"^(### {re.escape(task_id)}\s*[—-]\s*.+\n)",
        re.MULTILINE
    )
    task_match = task_pattern.search(content)
    if not task_match:
        return {"error": f"{task_id} not found in {tasks_file}"}
    
    # Find the Status line after the task header
    task_start = task_match.start()
    rest = content[task_start:]
    
    # Find next task or end of file
    next_task = re.search(r"\n### TASK-", rest[len(task_match.group(0)):])
    if next_task:
        task_end = task_start + len(task_match.group(0)) + next_task.start()
    else:
        task_end = len(content)
    
    task_section = content[task_start:task_end]
    
    # Find and replace Status line
    old_status = "unknown"
    status_match = re.search(r"\*\*Status:\*\*\s*([^\n]+)", task_section)
    if status_match:
        old_status = status_match.group(1).strip()
        updated_section = task_section[:status_match.start()] + \
            f"**Status:** {new_status}" + \
            task_section[status_match.end():]
    else:
        # No Status line found, add one after the header
        header_end = task_section.find("\n") + 1
        updated_section = task_section[:header_end] + \
            f"\n**Status:** {new_status}\n" + \
            task_section[header_end:]
        old_status = "(none)"
    
    updated_content = content[:task_start] + updated_section + content[task_end:]
    tasks_file.write_text(updated_content, encoding="utf-8")
    
    return {
        "success": True,
        "task_id": task_id,
        "old_status": old_status,
        "new_status": new_status,
        "file": str(tasks_file)
    }


def main():
    parser = argparse.ArgumentParser(
        description="Read and update task status in TASKS.md"
    )
    parser.add_argument(
        "--action",
        required=True,
        choices=["list", "get", "set-status"],
        help="Action to perform"
    )
    parser.add_argument("--task-id", help="Task ID (e.g. TASK-001)")
    parser.add_argument("--status", help="New status (for set-status action)")
    args = parser.parse_args()

    if args.action == "list":
        result = list_tasks()
    elif args.action == "get":
        if not args.task_id:
            result = {"error": "--task-id required for 'get' action"}
        else:
            result = get_task(args.task_id)
    elif args.action == "set-status":
        if not args.task_id:
            result = {"error": "--task-id required for 'set-status' action"}
        elif not args.status:
            result = {"error": "--status required for 'set-status' action"}
        else:
            result = set_status(args.task_id, args.status)
    else:
        result = {"error": f"Unknown action: {args.action}"}

    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if "error" not in result else 1)


if __name__ == "__main__":
    main()
