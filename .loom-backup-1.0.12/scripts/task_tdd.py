#!/usr/bin/env python3
"""
task-tdd.py - Test-Driven Development Workflow for loom

This script implements a complete TDD workflow:
1. Create/verify tests exist
2. Run tests (should fail initially)
3. Develop feature
4. Run tests again
5. If pass: update docs, commit, push
6. If fail: document issues, return to step 3

Usage:
    python scripts/task-tdd.py start TASK-001 "Feature description"
    python scripts/task-tdd.py test                    # Run tests
    python scripts/task-tdd.py complete TASK-001       # Complete after tests pass
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

# Import from task.py
sys.path.insert(0, str(Path(__file__).parent))
from task import (
    TaskWorkflowError,
    backup_file,
    run_git_command,
    find_task_in_file,
    TASKS_FILE,
    STORY_FILE,
    DOCS_DIR,
    PROJECT_ROOT,
)

# TDD-specific paths
TESTS_DIR = PROJECT_ROOT / "tests"
TDD_LOG_FILE = DOCS_DIR / "TDD_LOG.md"


def run_tests(test_path: Optional[str] = None, verbose: bool = False) -> Tuple[bool, str]:
    """
    Run test suite.
    
    Args:
        test_path: Specific test file/directory to run (None = all tests)
        verbose: Enable verbose output
    
    Returns:
        (success, output) tuple
    """
    # Detect test framework
    if (PROJECT_ROOT / "pytest.ini").exists() or (PROJECT_ROOT / "pyproject.toml").exists():
        # pytest
        cmd = ["pytest"]
        if verbose:
            cmd.append("-v")
        if test_path:
            cmd.append(test_path)
        else:
            cmd.append("tests/")
    elif (PROJECT_ROOT / "package.json").exists():
        # npm test
        cmd = ["npm", "test"]
    else:
        # Generic python unittest
        cmd = ["python", "-m", "unittest", "discover", "-s", "tests"]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)


def log_tdd_cycle(task_id: str, phase: str, status: str, details: str):
    """Log TDD cycle to TDD_LOG.md."""
    if not TDD_LOG_FILE.exists():
        TDD_LOG_FILE.write_text("# TDD Log\n\n", encoding="utf-8")
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"\n## {task_id} — {phase}\n\n"
    entry += f"**Time:** {timestamp}  \n"
    entry += f"**Status:** {status}  \n"
    entry += f"**Details:**\n```\n{details}\n```\n\n"
    
    with open(TDD_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry)


def start_tdd_task(task_id: str, description: str, dry_run: bool = False):
    """
    Start TDD task workflow.
    
    Steps:
    1. Check if tests exist for this task
    2. If not, prompt to create them
    3. Run tests (should fail - Red phase)
    4. Update TASKS.md with TDD status
    5. Commit
    """
    print(f"🧪 Starting TDD workflow for {task_id}: {description}")
    
    # Check if tests directory exists
    if not TESTS_DIR.exists():
        print(f"⚠️  Tests directory not found: {TESTS_DIR}")
        create = input("Create tests/ directory? (y/n): ").strip().lower()
        if create == 'y':
            if not dry_run:
                TESTS_DIR.mkdir(parents=True)
            print(f"✅ Created {TESTS_DIR}")
        else:
            print("❌ Cannot proceed without tests directory")
            sys.exit(1)
    
    # Prompt for test file
    print(f"\n📝 Test file for {task_id}:")
    print(f"   Suggested: tests/test_{task_id.lower().replace('-', '_')}.py")
    test_file = input("   Test file path (or press Enter for suggestion): ").strip()
    
    if not test_file:
        test_file = f"tests/test_{task_id.lower().replace('-', '_')}.py"
    
    test_path = PROJECT_ROOT / test_file
    
    # Check if test file exists
    if not test_path.exists():
        print(f"\n⚠️  Test file not found: {test_file}")
        print("\n🔴 TDD Red Phase: Write tests first!")
        print(f"\nCreate {test_file} with:")
        print("  1. Test cases for the feature")
        print("  2. Expected behavior")
        print("  3. Edge cases")
        print("\nTests should FAIL initially (Red phase)")
        
        create = input(f"\nCreate empty test file {test_file}? (y/n): ").strip().lower()
        if create == 'y':
            if not dry_run:
                test_path.parent.mkdir(parents=True, exist_ok=True)
                test_path.write_text(
                    f'"""\nTests for {task_id}: {description}\n"""\n\n'
                    f'def test_{task_id.lower().replace("-", "_")}_placeholder():\n'
                    f'    """Placeholder test - replace with actual tests."""\n'
                    f'    assert False, "Write actual tests here"\n',
                    encoding="utf-8"
                )
            print(f"✅ Created {test_file}")
            print("⚠️  Edit the file to add real tests!")
        else:
            print("❌ Cannot proceed without tests")
            sys.exit(1)
    
    # Run tests (Red phase - should fail)
    print(f"\n🔴 Running tests (Red phase - should fail)...")
    success, output = run_tests(test_file, verbose=True)
    
    if success:
        print("⚠️  WARNING: Tests passed! This is unexpected in Red phase.")
        print("   Either:")
        print("   1. Tests are not strict enough")
        print("   2. Feature already exists")
        proceed = input("\nProceed anyway? (y/n): ").strip().lower()
        if proceed != 'y':
            sys.exit(1)
    else:
        print("✅ Tests failed as expected (Red phase)")
    
    # Log TDD cycle
    log_tdd_cycle(task_id, "RED (Start)", "Tests Failing", output[:500])
    
    # Update TASKS.md
    if not TASKS_FILE.exists():
        print(f"❌ {TASKS_FILE} not found. Run 'task.py init' first.")
        sys.exit(1)
    
    backup_file(TASKS_FILE)
    
    content = TASKS_FILE.read_text(encoding="utf-8")
    
    # Add task with TDD status
    new_task = f"\n### {task_id} — {description}\n\n"
    new_task += f"**Status:** In Progress (TDD Red Phase)  \n"
    new_task += f"**Test file:** `{test_file}`  \n"
    new_task += f"**Started:** {datetime.now().strftime('%Y-%m-%d')}\n\n"
    new_task += f"**TDD Workflow:**\n"
    new_task += f"- [x] 🔴 Red: Tests created and failing\n"
    new_task += f"- [ ] 🟢 Green: Implement feature to pass tests\n"
    new_task += f"- [ ] 🔵 Refactor: Clean up code\n"
    new_task += f"- [ ] ✅ Complete: All tests passing\n\n"
    
    updated_content = content.replace(
        "## 🚀 Lavoro in Corso\n",
        f"## 🚀 Lavoro in Corso\n{new_task}"
    )
    
    if not dry_run:
        TASKS_FILE.write_text(updated_content, encoding="utf-8")
    
    print(f"✅ Updated {TASKS_FILE}")
    
    # Git commit
    if not dry_run:
        run_git_command(["add", str(TASKS_FILE), str(test_path)])
        run_git_command(["commit", "-m", f"test: add tests for {task_id} (TDD Red phase)"])
        run_git_command(["push"])
    
    print(f"\n🎯 Next steps:")
    print(f"   1. Implement feature to make tests pass (Green phase)")
    print(f"   2. Run: python scripts/task-tdd.py test")
    print(f"   3. If tests pass: python scripts/task-tdd.py complete {task_id}")
    print(f"   4. If tests fail: fix code and repeat step 2")


def run_tdd_tests(verbose: bool = False):
    """Run tests and show TDD status."""
    print("🧪 Running test suite...")
    
    success, output = run_tests(verbose=verbose)
    
    print(output)
    
    if success:
        print("\n✅ All tests passed! (Green phase)")
        print("\n🎯 Next steps:")
        print("   1. Refactor code if needed (Refactor phase)")
        print("   2. Run tests again to ensure refactoring didn't break anything")
        print("   3. Complete task: python scripts/task-tdd.py complete TASK-XXX")
    else:
        print("\n❌ Tests failed! (Still in Red/Green phase)")
        print("\n🎯 Next steps:")
        print("   1. Fix the failing tests")
        print("   2. Run tests again: python scripts/task-tdd.py test")
        print("   3. Repeat until all tests pass")
    
    sys.exit(0 if success else 1)


def complete_tdd_task(task_id: str, dry_run: bool = False, no_push: bool = False):
    """
    Complete TDD task after tests pass.
    
    Steps:
    1. Run tests one final time
    2. If pass: update TASKS.md, STORY.md, commit, push
    3. If fail: abort and show error
    """
    print(f"🧪 Completing TDD task {task_id}")
    
    # Run tests one final time
    print("\n🧪 Running final test suite...")
    success, output = run_tests(verbose=True)
    
    if not success:
        print("\n❌ Tests are still failing!")
        print("\nCannot complete task with failing tests.")
        print("\n🎯 Fix the tests first:")
        print("   1. Review test output above")
        print("   2. Fix the code")
        print("   3. Run: python scripts/task-tdd.py test")
        print("   4. Try again: python scripts/task-tdd.py complete TASK-XXX")
        
        # Log failure
        log_tdd_cycle(task_id, "COMPLETE (Failed)", "Tests Still Failing", output[:500])
        sys.exit(1)
    
    print("✅ All tests passed!")
    
    # Log success
    log_tdd_cycle(task_id, "GREEN (Complete)", "All Tests Passing", output[:500])
    
    # Update TASKS.md
    backup_file(TASKS_FILE)
    
    content = TASKS_FILE.read_text(encoding="utf-8")
    task_pos = find_task_in_file(task_id, content)
    
    if task_pos is None:
        print(f"❌ Task {task_id} not found in TASKS.md")
        sys.exit(1)
    
    start, end = task_pos
    task_section = content[start:end]
    
    # Update TDD checklist
    task_section = task_section.replace(
        "- [ ] 🟢 Green: Implement feature to pass tests",
        "- [x] 🟢 Green: Implement feature to pass tests"
    )
    task_section = task_section.replace(
        "- [ ] 🔵 Refactor: Clean up code",
        "- [x] 🔵 Refactor: Clean up code"
    )
    task_section = task_section.replace(
        "- [ ] ✅ Complete: All tests passing",
        "- [x] ✅ Complete: All tests passing"
    )
    
    # Update status
    task_section = task_section.replace(
        "**Status:** In Progress (TDD Red Phase)",
        f"**Status:** Done ✅  \n**Completed:** {datetime.now().strftime('%Y-%m-%d')}"
    )
    task_section = task_section.replace(
        "**Status:** In Progress (TDD Green Phase)",
        f"**Status:** Done ✅  \n**Completed:** {datetime.now().strftime('%Y-%m-%d')}"
    )
    
    updated_content = content[:start] + task_section + content[end:]
    
    if not dry_run:
        TASKS_FILE.write_text(updated_content, encoding="utf-8")
    
    print(f"✅ Updated {TASKS_FILE}")
    
    # Git commit
    if not dry_run:
        run_git_command(["add", str(TASKS_FILE)])
        run_git_command(["commit", "-m", f"feat: complete {task_id} (TDD Green - all tests passing)"])
        
        if not no_push:
            success, output = run_git_command(["push"])
            if not success:
                print(f"⚠️  Git push failed: {output}")
                print("💡 Commit completed locally. Push manually with 'git push'")
            else:
                print("✅ Pushed to remote")
    
    print(f"\n🎉 Task {task_id} completed with TDD workflow!")
    print(f"   All tests passing ✅")


def main():
    parser = argparse.ArgumentParser(description="TDD Workflow Manager")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without executing")
    
    subparsers = parser.add_subparsers(dest="command", help="Command")
    
    # Start
    start_parser = subparsers.add_parser("start", help="Start TDD task")
    start_parser.add_argument("task_id", help="Task ID (e.g., TASK-001)")
    start_parser.add_argument("description", help="Task description")
    
    # Test
    test_parser = subparsers.add_parser("test", help="Run tests")
    test_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    
    # Complete
    complete_parser = subparsers.add_parser("complete", help="Complete TDD task")
    complete_parser.add_argument("task_id", help="Task ID")
    complete_parser.add_argument("--no-push", action="store_true", help="Don't push automatically")
    
    args = parser.parse_args()
    
    try:
        if args.command == "start":
            start_tdd_task(args.task_id, args.description, dry_run=args.dry_run)
        
        elif args.command == "test":
            run_tdd_tests(verbose=args.verbose)
        
        elif args.command == "complete":
            complete_tdd_task(args.task_id, dry_run=args.dry_run, no_push=args.no_push)
        
        else:
            parser.print_help()
    
    except TaskWorkflowError as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
