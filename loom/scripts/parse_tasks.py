import re
import os

# Resolve TASKS.md relative to project root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
TASKS_PATH = os.path.join(PROJECT_ROOT, "docs", "TASKS.md")

with open(TASKS_PATH, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Parse tasks
tasks = []
current_task = []
current_task_id = None

for i, line in enumerate(lines):
    # Check if this is a task header
    match = re.match(r'^### TASK-(\d+)', line)
    if match:
        # Save previous task if exists
        if current_task_id and current_task:
            tasks.append({
                'id': current_task_id,
                'content': ''.join(current_task)
            })
        # Start new task
        current_task_id = match.group(1)
        current_task = [line]
    else:
        if current_task_id:
            current_task.append(line)

# Don't forget the last task
if current_task_id and current_task:
    tasks.append({
        'id': current_task_id,
        'content': ''.join(current_task)
    })

# Separate completed and active tasks
completed_tasks = []
active_tasks = []

for task in tasks:
    content = task['content']
    # Check for completion indicators
    if re.search(r'\*\*Status:\*\*( Complete ✅| Done ✅)', content):
        completed_tasks.append(task)
    else:
        active_tasks.append(task)

print(f'Total tasks: {len(tasks)}')
print(f'Completed tasks: {len(completed_tasks)}')
print(f'Active tasks: {len(active_tasks)}')

print('\nCompleted task IDs:')
for task in completed_tasks:
    print(f'  TASK-{task["id"]}')

print('\nActive task IDs:')
for task in active_tasks:
    print(f'  TASK-{task["id"]}')

# Write completed tasks to a file
with open('completed_tasks.txt', 'w', encoding='utf-8') as f:
    for task in completed_tasks:
        f.write(task['content'])
        f.write('\n---\n\n')

# Write active tasks to a file
with open('active_tasks.txt', 'w', encoding='utf-8') as f:
    f.write('# TASKS.md — SynthTrade Task Tracking\n\n')
    f.write('## Active Tasks\n\n')
    for task in active_tasks:
        f.write(task['content'])
        f.write('\n---\n\n')

print('\nFiles written: completed_tasks.txt, active_tasks.txt')
