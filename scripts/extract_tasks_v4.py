import re

with open('docs/TASKS.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Split by task headers
task_pattern = r'(### TASK-\d+.*?)(?=### TASK-\d+|\Z|$)'
tasks = re.findall(task_pattern, content, re.DOTALL)

completed_tasks = []
pending_tasks = []

for task in tasks:
    # Check if task is completed
    if '**Status:** Complete' in task or '**Status:** Done' in task:
        completed_tasks.append(task)
    else:
        pending_tasks.append(task)

print(f"Total tasks found: {len(tasks)}")
print(f"Completed tasks: {len(completed_tasks)}")
print(f"Pending tasks: {len(pending_tasks)}")

# List completed task IDs
completed_ids = re.findall(r'### TASK-(\d+)', '\n'.join(completed_tasks))
print(f"\nCompleted task IDs: {completed_ids}")

# List pending task IDs
pending_ids = re.findall(r'### TASK-(\d+)', '\n'.join(pending_tasks))
print(f"Pending task IDs: {pending_ids}")

# Save completed tasks to file
with open('completed_tasks.txt', 'w', encoding='utf-8') as f:
    f.write('\n\n'.join(completed_tasks))

# Save pending tasks to file
with open('pending_tasks.txt', 'w', encoding='utf-8') as f:
    f.write('\n\n'.join(pending_tasks))

print("\nSaved completed tasks to completed_tasks.txt")
print("Saved pending tasks to pending_tasks.txt")
