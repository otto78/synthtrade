# loom Execution Scripts

This directory contains **deterministic execution scripts** — Level 3 of the loom DOE Architecture.

## What Goes Here

Each script handles **one specific task** that would be error-prone if delegated entirely to an LLM:
- API calls with authentication
- File manipulation with specific formats
- Git operations
- Data processing and transformation

## Rules for Execution Scripts

1. **Single responsibility** — one script, one job
2. **Always CLI-runnable** — use `argparse`, never `input()`
3. **Return structured output** — JSON to stdout preferred
4. **Exit codes matter** — `0` = success, `1` = failure
5. **Fully documented** — docstring, args, return values
6. **Tested** — each script should have a test in `tests/`

## Available Scripts

| Script | Purpose |
|--------|---------|
| `_template.py` | Template for new scripts |
| `git_commit.py` | Selective git commit and push |
| `task_status.py` | Read/write task status from TASKS.md |

## Usage Pattern

The AI agent calls scripts like this:

```bash
# Agent calls script directly
python loom/execution/git_commit.py --files "src/auth.py,tests/test_auth.py" --message "feat: add OAuth2 login [TASK-001]"

# Script returns JSON
{"success": true, "commit": "abc1234", "pushed": true}
```

## Adding a New Script

```bash
cp loom/execution/_template.py loom/execution/my_feature.py
# Edit my_feature.py
# Add tests in tests/test_my_feature.py
```
