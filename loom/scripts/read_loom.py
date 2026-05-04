#!/usr/bin/env python3
"""
read_loom.py - Zero-Friction Entry Point for loom

This script is triggered by phrases like "read loom" or "leggi loom".
It performs auto-discovery and ensures the project is properly configured.
"""

import os
import sys
from pathlib import Path
import subprocess
import shutil

# Handle encoding for Windows terminals
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.END}\n")

def print_success(text: str):
    try:
        print(f"{Colors.GREEN}✅ {text}{Colors.END}")
    except:
        print(f"{Colors.GREEN}[OK] {text}{Colors.END}")

def print_info(text: str):
    try:
        print(f"{Colors.CYAN}\u2139\ufe0f  {text}{Colors.END}")
    except:
        print(f"{Colors.CYAN}[INFO] {text}{Colors.END}")

def print_warning(text: str):
    try:
        print(f"{Colors.YELLOW}\u26a0\ufe0f  {text}{Colors.END}")
    except:
        print(f"{Colors.YELLOW}[WARN] {text}{Colors.END}")

def main():
    print_header("loom Discovery")
    
    project_root = Path.cwd()
    loom_dir = project_root / "loom"
    
    if not loom_dir.exists():
        # Maybe we are inside loom/scripts?
        if (project_root.parent / "loom").exists():
            project_root = project_root.parent
            loom_dir = project_root / "loom"
        else:
            print(f"{Colors.RED}Error: 'loom/' folder not found in {project_root}{Colors.END}")
            sys.exit(1)

    # 1. Search for PROJECT.md / PROGETTO.md
    meta_file = None
    for name in ["PROJECT.md", "PROGETTO.md"]:
        path = project_root / name
        if path.exists():
            meta_file = path
            break
            
    if meta_file:
        print_success(f"Found project meta-file: {meta_file.name}")
    else:
        print_warning("No PROJECT.md or PROGETTO.md found in root.")
        create = input(f"{Colors.CYAN}Would you like me to create a PROJECT.md template for you? (y/n): {Colors.END}").lower()
        if create == 'y':
            template_path = loom_dir / "templates" / "PROJECT.md.template"
            target_path = project_root / "PROJECT.md"
            if template_path.exists():
                shutil.copy2(template_path, target_path)
                print_success("Created PROJECT.md template. Please fill it and run 'read loom' again.")
                sys.exit(0)
            else:
                target_path.write_text("# New Project\n\nGoal: Describe your project here.\n", encoding="utf-8")
                print_success("Created basic PROJECT.md. Please fill it and run 'read loom' again.")
                sys.exit(0)
        else:
            print_info("Proceeding without project meta-file...")

    # 2. Check for AGENT.md
    agent_md = project_root / "AGENT.md"
    if not agent_md.exists():
        print_info("AGENT.md not found. Initializing auto-setup...")
        setup_script = loom_dir / "scripts" / "setup.py"
        cmd = [sys.executable, str(setup_script), "--auto"]
        if meta_file:
            cmd.extend(["--from-project-file", str(meta_file)])
            
        subprocess.run(cmd, check=True)
    else:
        print_success("AGENT.md already exists.")
        # Optional: Sync configs if needed
        print_info("Refreshing IDE configurations...")
        setup_script = loom_dir / "scripts" / "setup.py"
        subprocess.run([sys.executable, str(setup_script), "--auto"], check=True)

    # 3. Final Report
    print_header("loom Ready")
    print_info(f"Project: {project_root.name}")
    print_info(f"Tasks: docs/TASKS.md")
    print_info(f"Directives: loom/directives/")
    
    print(f"\n{Colors.BOLD}You can now start working. Try:{Colors.END}")
    print(f"  - 'start task TASK-001 \"description\"'")
    print(f"  - 'list tasks'")

if __name__ == "__main__":
    main()
