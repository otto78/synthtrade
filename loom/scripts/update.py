#!/usr/bin/env python3
"""
loom update — Check and apply framework updates from GitHub.

Usage:
  python loom/scripts/update.py --check      # Check if updates are available
  python loom/scripts/update.py --apply      # Download and apply update
  python loom/scripts/update.py --status     # Show current version only
  python loom/scripts/update.py --rollback   # Restore the previous backup

Natural language triggers (say this to your AI agent):
  EN: "check for loom updates"  →  python loom/scripts/update.py --check
  EN: "update loom"             →  python loom/scripts/update.py --apply
  EN: "loom version"            →  python loom/scripts/update.py --status
  IT: "controlla aggiornamenti loom"
  IT: "aggiorna loom"
  IT: "versione loom"

What is SAFE during an update:
  ✅ Updated: loom/scripts/, loom/templates/, loom/directives/, loom/ide-configs/
  🔒 Protected (never touched): AGENT.md, PROJECT.md, CLAUDE.md, GEMINI.md,
     AGENTS.md, .cursorrules, .windsurfrules, all IDE config files,
     docs/TASKS.md, docs/STORY.md, docs/BACKLOG.md, docs/CHANGELOG.md
"""

import sys
import os
import shutil
import tempfile
import urllib.request
import urllib.error
import zipfile
from pathlib import Path

# Fix encoding on Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass  # Python < 3.7


# ─── Config ───────────────────────────────────────────────────────────────────

GITHUB_REPO       = "otto78/loom-framework"
GITHUB_RAW_INIT   = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/loom/__init__.py"
GITHUB_ZIP_URL    = f"https://github.com/{GITHUB_REPO}/archive/refs/heads/main.zip"

# Files/dirs that live OUTSIDE loom/ and belong to the user project.
# update.py never touches these — they are only created once during setup.
PROTECTED_ROOT_FILES = [
    "AGENT.md", "PROJECT.md",
    "CLAUDE.md", "GEMINI.md", "AGENTS.md",
    ".cursorrules", ".windsurfrules",
    ".cursor", ".windsurf", ".github",
    ".aiassistant", ".clinerules", ".trae",
    "docs/TASKS.md", "docs/BACKLOG.md",
    "docs/STORY.md", "docs/CHANGELOG.md", "docs/HANDOFF.md",
]

# ─── Terminal helpers ──────────────────────────────────────────────────────────

class C:
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    BLUE   = "\033[94m"
    CYAN   = "\033[96m"
    BOLD   = "\033[1m"
    RESET  = "\033[0m"

def ok(msg):    print(f"{C.GREEN}✅  {msg}{C.RESET}")
def info(msg):  print(f"{C.CYAN}ℹ️   {msg}{C.RESET}")
def warn(msg):  print(f"{C.YELLOW}⚠️   {msg}{C.RESET}")
def err(msg):   print(f"{C.RED}❌  {msg}{C.RESET}")
def head(msg):  print(f"\n{C.BOLD}{C.BLUE}{'─'*52}\n  {msg}\n{'─'*52}{C.RESET}\n")

# ─── Version helpers ───────────────────────────────────────────────────────────

def _parse_version(init_text: str) -> str:
    for line in init_text.splitlines():
        if "__version__" in line and "=" in line:
            return line.split("=", 1)[1].strip().strip("\"'")
    return "unknown"

def get_local_version(loom_dir: Path) -> str:
    init = loom_dir / "__init__.py"
    if not init.exists():
        return "unknown"
    return _parse_version(init.read_text(encoding="utf-8"))

def fetch_remote_version() -> str | None:
    try:
        with urllib.request.urlopen(GITHUB_RAW_INIT, timeout=10) as r:
            return _parse_version(r.read().decode("utf-8"))
    except Exception:
        return None

def version_tuple(v: str):
    try:
        return tuple(int(x) for x in v.split("."))
    except Exception:
        return (0, 0, 0)

# ─── Download helper ───────────────────────────────────────────────────────────

def _download(url: str, dest: Path):
    print(f"  Downloading from GitHub...", end="", flush=True)
    try:
        with urllib.request.urlopen(url, timeout=120) as r:
            size = 0
            with open(dest, "wb") as f:
                while chunk := r.read(65536):
                    f.write(chunk)
                    size += len(chunk)
        print(f" {C.GREEN}done{C.RESET} ({size // 1024} KB)")
    except Exception as e:
        print()
        raise RuntimeError(f"Download failed: {e}")

# ─── Commands ─────────────────────────────────────────────────────────────────

def cmd_status(loom_dir: Path):
    head("📦  loom — version info")
    local = get_local_version(loom_dir)
    info(f"Installed version : {C.BOLD}{local}{C.RESET}")
    info(f"Framework dir     : {loom_dir}")
    info(f"Repository        : https://github.com/{GITHUB_REPO}")
    print()
    print(f"  Run {C.CYAN}python loom/scripts/update.py --check{C.RESET} to check for updates.")


def cmd_check(loom_dir: Path):
    head("🔍  loom — checking for updates")
    local = get_local_version(loom_dir)
    info(f"Installed version : {C.BOLD}{local}{C.RESET}")
    print(f"  Fetching latest version from GitHub...", end="", flush=True)
    remote = fetch_remote_version()
    if remote is None:
        print()
        err("Cannot reach GitHub. Check your internet connection.")
        sys.exit(1)
    print(f" {C.GREEN}done{C.RESET}")
    info(f"Latest version    : {C.BOLD}{remote}{C.RESET}")

    if version_tuple(remote) > version_tuple(local):
        print(f"\n  {C.YELLOW}{C.BOLD}🚀  Update available: {local} → {remote}{C.RESET}")
        print(f"\n  {C.BOLD}What will be updated:{C.RESET}")
        print(f"    • loom/scripts/          (task.py, setup.py, update.py, ...)")
        print(f"    • loom/templates/        (AGENT.md.template, ...)")
        print(f"    • loom/directives/       (SOPs)")
        print(f"    • loom/ide-configs/      (Cline, Trae, Cursor, ...)")
        print(f"    • loom/__init__.py")
        print(f"\n  {C.BOLD}What will NOT be touched:{C.RESET}")
        print(f"    🔒  AGENT.md, PROJECT.md")
        print(f"    🔒  CLAUDE.md, GEMINI.md, AGENTS.md")
        print(f"    🔒  .cursorrules, .windsurfrules, all IDE/agent config files")
        print(f"    🔒  docs/TASKS.md, STORY.md, BACKLOG.md, CHANGELOG.md")
        print(f"\n  To apply the update run:")
        print(f"    {C.CYAN}python loom/scripts/update.py --apply{C.RESET}\n")
    elif version_tuple(local) > version_tuple(remote):
        ok(f"You are ahead of the remote ({local} > {remote}). Nothing to update.")
    else:
        ok(f"Already up to date  (version {local}).")


def cmd_apply(loom_dir: Path, project_root: Path):
    head("⬆️   loom — applying update")
    local = get_local_version(loom_dir)
    info(f"Installed version : {C.BOLD}{local}{C.RESET}")
    print(f"  Fetching latest version from GitHub...", end="", flush=True)
    remote = fetch_remote_version()
    if remote is None:
        print()
        err("Cannot reach GitHub. Check your internet connection.")
        sys.exit(1)
    print(f" {C.GREEN}done{C.RESET}")
    info(f"Latest version    : {C.BOLD}{remote}{C.RESET}")

    if version_tuple(remote) <= version_tuple(local):
        ok(f"Already up to date (version {local}). Nothing to do.")
        return

    print(f"\n  {C.YELLOW}⚠️   Only the loom/ directory will be replaced.")
    print(f"      Your project files (AGENT.md, IDE configs, docs/) are SAFE.{C.RESET}\n")
    answer = input("  Proceed with update? [y/N] ").strip().lower()
    if answer != "y":
        warn("Update cancelled.")
        return

    with tempfile.TemporaryDirectory() as _tmp:
        tmp = Path(_tmp)
        zip_path = tmp / "loom-update.zip"
        _download(GITHUB_ZIP_URL, zip_path)

        # Extract archive
        print(f"  Extracting archive...", end="", flush=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp)
        print(f" {C.GREEN}done{C.RESET}")

        # Locate the extracted loom/ dir
        extracted_root = next(tmp.glob("loom-framework-*/"), None)
        if not extracted_root:
            err("Unexpected archive structure — cannot find loom-framework-*/")
            sys.exit(1)
        new_loom = extracted_root / "loom"
        if not new_loom.exists():
            err(f"Unexpected archive structure — 'loom/' not found inside {extracted_root.name}")
            sys.exit(1)

        # Backup current loom/ BEFORE replacing it
        backup_dir = project_root / f".loom-backup-{local}"
        print(f"  Backing up loom/ → {backup_dir.name}...", end="", flush=True)
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        shutil.copytree(loom_dir, backup_dir)
        print(f" {C.GREEN}done{C.RESET}")

        # Replace loom/
        print(f"  Installing loom {remote}...", end="", flush=True)
        shutil.rmtree(loom_dir)
        shutil.copytree(new_loom, loom_dir)
        print(f" {C.GREEN}done{C.RESET}")

    new_version = get_local_version(loom_dir)
    print()
    ok(f"loom updated successfully:  {local} → {new_version}")
    info(f"Backup of previous version saved as: {backup_dir.name}")
    print(f"\n  {C.BOLD}Next steps:{C.RESET}")
    print(f"    1. Run  {C.CYAN}python loom/scripts/setup.py{C.RESET}  to configure new IDE/Agent support")
    print(f"    2. Tell your AI agent: {C.CYAN}\"read loom\"{C.RESET}  to reload the updated configuration")
    print(f"    3. Delete {backup_dir.name} once you've verified everything works\n")


def cmd_rollback(loom_dir: Path, project_root: Path):
    head("⏪  loom — rollback to previous version")

    # Find backups
    backups = sorted(project_root.glob(".loom-backup-*"), reverse=True)
    if not backups:
        err("No backup found. Cannot rollback.")
        sys.exit(1)

    backup = backups[0]
    current = get_local_version(loom_dir)
    backup_version = backup.name.replace(".loom-backup-", "")
    info(f"Current version : {C.BOLD}{current}{C.RESET}")
    info(f"Restoring from  : {backup.name}  (version {backup_version})")
    answer = input("\n  Proceed with rollback? [y/N] ").strip().lower()
    if answer != "y":
        warn("Rollback cancelled.")
        return

    shutil.rmtree(loom_dir)
    shutil.copytree(backup, loom_dir)
    shutil.rmtree(backup)
    ok(f"Rollback complete: {current} → {backup_version}")
    info("Backup removed after successful rollback.")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    script_dir   = Path(__file__).resolve().parent   # loom/scripts/
    loom_dir     = script_dir.parent                  # loom/
    project_root = loom_dir.parent                    # your project root

    if not (loom_dir / "__init__.py").exists():
        err("Cannot find loom/__init__.py. Run this script from inside a project that has loom installed.")
        sys.exit(1)

    flag = sys.argv[1] if len(sys.argv) > 1 else "--status"

    if flag in ("--status", "-s"):
        cmd_status(loom_dir)
    elif flag in ("--check", "-c"):
        cmd_check(loom_dir)
    elif flag in ("--apply", "--update", "-u"):
        cmd_apply(loom_dir, project_root)
    elif flag in ("--rollback", "-r"):
        cmd_rollback(loom_dir, project_root)
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
