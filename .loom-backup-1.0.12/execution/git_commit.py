#!/usr/bin/env python3
"""
git_commit.py - Selective Git Commit and Push

Performs a selective git add, commit, and optional push.
Safer than 'git add -A' in concurrent multi-agent environments.

Usage:
    python loom/execution/git_commit.py --files "file1.py,file2.md" --message "feat: description [TASK-001]"
    python loom/execution/git_commit.py --files "src/auth.py" --message "fix: login bug" --no-push

Returns (JSON to stdout):
    {"success": true, "commit": "abc1234", "pushed": true}
    {"success": false, "error": "nothing to commit"}
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def run_git(args: list, cwd: Path = None) -> tuple[int, str, str]:
    """Run a git command. Returns (returncode, stdout, stderr)."""
    result = subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        cwd=cwd or Path.cwd()
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def selective_commit(files: list[str], message: str, push: bool = True) -> dict:
    """
    Perform selective git add, commit, and optional push.
    
    Args:
        files: List of file paths to add
        message: Commit message
        push: Whether to push after commit
        
    Returns:
        dict with success, commit hash, and pushed status
    """
    # Validate files exist
    missing = [f for f in files if not Path(f).exists()]
    if missing:
        return {"success": False, "error": f"Files not found: {missing}"}

    # Stage files
    code, _, err = run_git(["add"] + files)
    if code != 0:
        return {"success": False, "error": f"git add failed: {err}"}

    # Check if there's anything to commit
    code, status, _ = run_git(["diff", "--cached", "--stat"])
    if not status:
        return {"success": False, "error": "nothing to commit — no staged changes"}

    # Commit
    code, out, err = run_git(["commit", "-m", message])
    if code != 0:
        return {"success": False, "error": f"git commit failed: {err}"}

    # Get commit hash
    _, commit_hash, _ = run_git(["rev-parse", "--short", "HEAD"])

    result = {"success": True, "commit": commit_hash, "pushed": False}

    # Push
    if push:
        code, _, err = run_git(["push"])
        if code != 0:
            result["push_warning"] = f"Push failed: {err}"
        else:
            result["pushed"] = True

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Selective git commit and push for loom"
    )
    parser.add_argument(
        "--files",
        required=True,
        help="Comma-separated list of files to commit"
    )
    parser.add_argument(
        "--message",
        required=True,
        help="Commit message (include [TASK-ID] for traceability)"
    )
    parser.add_argument(
        "--no-push",
        action="store_true",
        help="Commit without pushing"
    )
    args = parser.parse_args()

    files = [f.strip() for f in args.files.split(",") if f.strip()]
    result = selective_commit(files, args.message, push=not args.no_push)

    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
