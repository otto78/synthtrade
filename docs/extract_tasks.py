import re

with open('TASKS.md', 'r', encoding='utf-8') as f:
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
