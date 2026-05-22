#!/usr/bin/env python3
"""Convert existing TASKS.md bullet list items into Loom task format.

This version is improved to:
1. Preserve file structure (headers, notes, structure).
2. Use safe backup (shutil.copy2).
3. Handle encoding properly.
4. Maintain integrity of non-task information.
"""

import re
import shutil
from pathlib import Path
from datetime import datetime

DOCS_DIR = Path("docs")
TASKS_FILE = DOCS_DIR / "TASKS.md"
BACKUP_FILE = DOCS_DIR / "TASKS.md.bak"

def convert_task_line(line: str, task_id_counter: list) -> str:
    """
    Converts a single task line into Loom format if it matches the pattern.
    Otherwise returns the line unchanged.
    """
    # Pattern for standard markdown checkboxes: - [ ] or - [x]
    # Captures indentation, checkbox state, and description
    pattern = r"^(\s*)- \[(x| )\] (.*)$"
    match = re.match(pattern, line)
    
    if match:
        indent = match.group(1)
        is_done = match.group(2) == 'x'
        description = match.group(3).strip()
        
        # Remove any trailing checkmarks or status emojis from description to avoid duplication
        description = re.sub(r"\s*[✅❌🔄].*$", "", description).strip()
        
        status = "Done ✅" if is_done else "In Progress"
        date_str = datetime.now().strftime("%Y-%m-%d")
        
        task_id = f"TASK-{task_id_counter[0]:03d}"
        task_id_counter[0] += 1
        
        # Format following loom/scripts/task.py conventions
        # We use headers for tasks to allow easy navigation and status tracking
        new_task_block = [
            f"### {task_id} — {description}",
            "",
            f"**Status:** {status}  ",
            f"**Data:** {date_str}" if not is_done else f"**Completato:** {date_str}",
            ""
        ]
        
        # Re-apply indentation if needed (though loom usually prefers flat structure for tasks)
        # For now, we keep it flat to be compatible with task.py's regex
        return "\n".join(new_task_block)
    
    return line

def main() -> None:
    if not TASKS_FILE.exists():
        print(f"❌ Errore: {TASKS_FILE} non trovato.")
        return

    try:
        # Create a safe backup before any modification
        shutil.copy2(TASKS_FILE, BACKUP_FILE)
        print(f"✅ Backup di sicurezza creato in {BACKUP_FILE}")

        # Read original content
        content = BACKUP_FILE.read_text(encoding="utf-8")
        lines = content.splitlines()

        converted_lines = []
        task_id_counter = [1] # Use list for mutability in closure
        
        print("🔄 Inizio conversione task...")
        
        for line in lines:
            converted_lines.append(convert_task_line(line, task_id_counter))

        # Join lines and write back to original file
        new_content = "\n".join(converted_lines)
        TASKS_FILE.write_text(new_content, encoding="utf-8")
        
        num_tasks = task_id_counter[0] - 1
        print(f"✨ Conversione completata con successo!")
        print(f"📊 Task convertiti: {num_tasks}")
        print(f"📝 File aggiornato: {TASKS_FILE}")
        print(f"💡 La struttura originale, le intestazioni e le note sono state preservate.")

    except Exception as e:
        print(f"❌ Si è verificato un errore durante la conversione: {e}")
        # If possible, restore from backup if we were in the middle of writing
        if BACKUP_FILE.exists() and not TASKS_FILE.exists():
            shutil.copy2(BACKUP_FILE, TASKS_FILE)
            print("ℹ️  Ripristinato TASKS.md dal backup.")

if __name__ == "__main__":
    main()
