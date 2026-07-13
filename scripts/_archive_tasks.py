"""
Script: _archive_tasks.py
Sposta tutti i task completati da TASKS.md all'archivio in ARCHIVE_TASKS.md.

Criteri di completamento:
- **Status:** Done / DONE / Complete / FATTO / Finita (MA non Partial/Parziale/Pending/APERTO/etc)
"""

import re
import shutil
from pathlib import Path

DOCS_DIR = Path("docs")
TASKS_PATH = DOCS_DIR / "TASKS.md"
ARCHIVE_PATH = DOCS_DIR / "ARCHIVE_TASKS.md"
BACKUP_PATH = DOCS_DIR / "TASKS.md.bak"

# ---- PARSE TASKS.MD ----

with open(TASKS_PATH, "r", encoding="utf-8") as f:
    lines = f.readlines()

def is_completed_status(status_text: str) -> bool:
    """Return True if the status indicates a completed task."""
    s = status_text.strip()
    # Must contain a positive completion keyword
    has_done = bool(re.search(r'(Done|DONE|Complete|FATTO|Finita|✅|✔)', s))
    # Must NOT contain a pending/partial/failure keyword
    has_negative = bool(re.search(
        r'(Pending|Partial|Parziale|WIP|APERTO|APERTA|In corso|Fail|Fallito|Superseded|SOSPESA|Bug)',
        s, re.IGNORECASE
    ))
    return has_done and not has_negative


def is_task_header(stripped: str) -> bool:
    """Check if a line is a task header (### TASK-, ### FIX-, or #### with sub-status)."""
    if stripped.startswith("### TASK-") or stripped.startswith("### FIX-"):
        return True
    if stripped.startswith("#### ") and not stripped.startswith("#### Red", 0) and not stripped.startswith("#### Green", 0) and not stripped.startswith("#### Refactor", 0):
        return True
    return False


# Parse into blocks
blocks = []  # list of (start_line, end_line_inclusive, header_text)
current_start = None
current_header = None

for i, line in enumerate(lines):
    stripped = line.strip()
    
    if is_task_header(stripped):
        # Save previous block
        if current_start is not None:
            blocks.append((current_start, i - 1, current_header))
        current_start = i
        current_header = stripped
    elif stripped.startswith("## ") or stripped.startswith("# "):
        # Section header ends current block
        if current_start is not None:
            blocks.append((current_start, i - 1, current_header))
            current_start = None
            current_header = None

# Last block
if current_start is not None:
    blocks.append((current_start, len(lines) - 1, current_header))

# Separate completed from active
# We'll work with line indices - build lists of line ranges to keep/remove
completed_ranges = []
active_ranges = []

for start, end, header in blocks:
    if start is None:
        continue
    
    # Extract status from the block
    block_text = "\n".join(lines[start:end+1])
    status_match = re.search(r'\*\*Status:\*\*(.*?)(?:\n|$)', block_text)
    
    if status_match:
        status_text = status_match.group(1).strip()
        if is_completed_status(status_text):
            completed_ranges.append((start, end))
        else:
            active_ranges.append((start, end))
    else:
        # Lines with no task header (section headers, intro text, etc.) - keep them
        if not is_task_header(header or ""):
            pass  # non-task blocks are kept

print(f"Found {len(completed_ranges)} completed task blocks")
print(f"Found {len(active_ranges)} active task blocks")

# ---- BUILD NEW TASKS.MD (only active tasks) ----

# First, find all lines that belong to non-task sections (headers, intro text, "Task Archiviati" link)
# We want to preserve: document header, section headers, non-task blocks, active tasks

# The approach: mark all lines that are part of completed tasks
completed_lines = set()
for c_start, c_end in completed_ranges:
    for li in range(c_start, c_end + 1):
        completed_lines.add(li)

# Also mark the "## Task Archiviati" section and everything after it in the original file as completed
# (since they just point to ARCHIVE_TASKS.md)
for i, line in enumerate(lines):
    if line.strip() == "## Task Archiviati":
        for li in range(i, len(lines)):
            completed_lines.add(li)
        break

# Build new content: keep only non-completed lines
new_tasks_lines = []
for i, line in enumerate(lines):
    if i not in completed_lines:
        new_tasks_lines.append(line)

new_tasks_content = "".join(new_tasks_lines)

# Clean up: remove trailing empty lines
new_tasks_content = new_tasks_content.rstrip() + "\n"

# ---- BUILD ARCHIVE CONTENT TO APPEND ----

# Collect all completed task blocks as text
completed_texts = []
for c_start, c_end in completed_ranges:
    # Skip the "## Task Archiviati" section itself
    if lines[c_start].strip() == "## Task Archiviati":
        continue
    block = "".join(lines[c_start:c_end+1])
    # Clean trailing empty lines
    block = block.rstrip()
    completed_texts.append(block)

# Build archive separator and content
archive_new_section = f"""

---

## ✅ Task Completati (Archiviati il {__import__('datetime').datetime.now().strftime('%Y-%m-%d')})

{chr(10).join(completed_texts)}

"""

# ---- WRITE FILES ----

# Backup original
shutil.copy(TASKS_PATH, BACKUP_PATH)
print(f"Backup created: {BACKUP_PATH}")

# Write new TASKS.md
with open(TASKS_PATH, "w", encoding="utf-8") as f:
    f.write(new_tasks_content)
print(f"New TASKS.md written ({len(new_tasks_lines)} lines)")

# Append to ARCHIVE_TASKS.md
with open(ARCHIVE_PATH, "a", encoding="utf-8") as f:
    f.write(archive_new_section)
print(f"ARCHIVE_TASKS.md updated")

print("\nDone! Summary:")
print(f"  Archived: {len(completed_texts)} completed task blocks")