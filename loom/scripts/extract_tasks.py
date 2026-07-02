import re
import sys
import os

# When run from loom/scripts/, resolve TASKS.md relative to project root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
TASKS_PATH = os.path.join(PROJECT_ROOT, "docs", "TASKS.md")

with open(TASKS_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# Find all task blocks
task_pattern = r'(### TASK-\d+[^\n]*\n.*?)(?=\n### TASK-|\Z)'
tasks = re.findall(task_pattern, content, re.DOTALL)

completed_tasks = []
active_tasks = []

for task in tasks:
    # Check if task has completion status
    if re.search(r'\*\*Status:\*\*( Complete ✅| Done ✅)', task):
        completed_tasks.append(task)
    else:
        active_tasks.append(task)

print(f'Total tasks: {len(tasks)}')
print(f'Completed tasks: {len(completed_tasks)}')
print(f'Active tasks: {len(active_tasks)}')

# Print completed task IDs
print('\nCompleted tasks:')
for task in completed_tasks:
    match = re.search(r'TASK-(\d+)', task)
    if match:
        print(f'  TASK-{match.group(1)}')

# Print active task IDs
print('\nActive tasks:')
for task in active_tasks:
    match = re.search(r'TASK-(\d+)', task)
    if match:
        print(f'  TASK-{match.group(1)}')
