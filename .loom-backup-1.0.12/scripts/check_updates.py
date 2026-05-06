#!/usr/bin/env python3
"""
Loom Update Checker

Checks if a newer version of Loom Framework is available on GitHub.
Designed to be called by AI agents at the start of a session to inform the user.

Usage (natural language):
    "check for loom updates"
    "is there a new version of loom?"
    "update loom"

Usage (CLI):
    python loom/scripts/check_updates.py           # Check for updates
    python loom/scripts/check_updates.py --update   # Download and apply update
    python loom/scripts/check_updates.py --quiet    # Machine-readable output (JSON)

Returns (JSON to stdout with --quiet):
    {"update_available": true, "current": "1.0.4", "latest": "1.0.8", "url": "..."}
    {"update_available": false, "current": "1.0.8", "latest": "1.0.8"}
"""

import json
import re
import subprocess
import sys
import shutil
from pathlib import Path
from typing import Optional, Tuple
from urllib.request import urlopen
from urllib.error import URLError

REPO_URL = "https://github.com/otto78/loom-framework"
API_URL = "https://api.github.com/repos/otto78/loom-framework/releases/latest"
RAW_URL = "https://raw.githubusercontent.com/otto78/loom-framework/main/pyproject.toml"

# Find loom root relative to this script
LOOM_ROOT = Path(__file__).parent.parent
PROJECT_ROOT = Path.cwd()


def get_local_version() -> Optional[str]:
    """Get the locally installed loom version."""
    # Try loom/__init__.py first
    init_file = LOOM_ROOT / "__init__.py"
    if init_file.exists():
        content = init_file.read_text(encoding="utf-8")
        match = re.search(r'__version__\s*=\s*"([^"]+)"', content)
        if match:
            return match.group(1)
    
    # Try pyproject.toml in project root
    pyproject = PROJECT_ROOT / "pyproject.toml"
    if pyproject.exists():
        content = pyproject.read_text(encoding="utf-8")
        match = re.search(r'version\s*=\s*"([^"]+)"', content)
        if match:
            return match.group(1)
    
    return None


def get_remote_version() -> Optional[str]:
    """Get the latest version from GitHub."""
    try:
        # Try GitHub API for releases first
        response = urlopen(API_URL, timeout=5)
        data = json.loads(response.read().decode("utf-8"))
        tag = data.get("tag_name", "")
        return tag.lstrip("v")
    except (URLError, json.JSONDecodeError, KeyError):
        pass
    
    try:
        # Fallback: read pyproject.toml from main branch
        response = urlopen(RAW_URL, timeout=5)
        content = response.read().decode("utf-8")
        match = re.search(r'version\s*=\s*"([^"]+)"', content)
        if match:
            return match.group(1)
    except URLError:
        pass
    
    return None


def compare_versions(local: str, remote: str) -> int:
    """Compare two semver strings. Returns: -1 if local<remote, 0 if equal, 1 if local>remote."""
    def parse(v):
        return tuple(int(x) for x in v.split(".")[:3])
    
    l, r = parse(local), parse(remote)
    if l < r:
        return -1
    elif l > r:
        return 1
    return 0


def check_updates(quiet: bool = False) -> Tuple[bool, str, str]:
    """Check if updates are available."""
    local = get_local_version()
    if local is None:
        if not quiet:
            print("Could not determine local loom version.")
        return False, "unknown", "unknown"
    
    remote = get_remote_version()
    if remote is None:
        if not quiet:
            print("Could not check for updates (network error).")
        return False, local, "unknown"
    
    update_available = compare_versions(local, remote) < 0
    
    if quiet:
        print(json.dumps({
            "update_available": update_available,
            "current": local,
            "latest": remote,
            "url": f"{REPO_URL}/releases/latest" if update_available else None
        }))
    else:
        if update_available:
            print(f"\nLoom Framework update available: v{local} → v{remote}")
            print(f"\nTo update, tell your agent:")
            print(f'  "update loom to {remote}"')
            print(f"\nOr manually:")
            print(f"  git -C loom pull origin main")
            print(f"\nRelease notes: {REPO_URL}/releases/latest")
        else:
            print(f"\nLoom Framework v{local} is up to date.")
    
    return update_available, local, remote


def apply_update():
    """Download and apply the latest version."""
    local = get_local_version()
    remote = get_remote_version()
    
    if remote is None:
        print("Could not fetch latest version.")
        sys.exit(1)
    
    if local and compare_versions(local, remote) >= 0:
        print(f"Already up to date (v{local}).")
        return
    
    print(f"Updating Loom Framework: v{local or '?'} → v{remote}")
    
    loom_dir = PROJECT_ROOT / "loom"
    
    # Check if loom/ is a git submodule or standalone
    if (loom_dir / ".git").exists() or (PROJECT_ROOT / ".gitmodules").exists():
        print("Updating via git pull...")
        try:
            subprocess.run(
                ["git", "-C", str(loom_dir), "pull", "origin", "main"],
                check=True
            )
            print(f"Updated to v{remote}")
        except subprocess.CalledProcessError:
            print("Git pull failed. Try manually: git -C loom pull origin main")
            sys.exit(1)
    else:
        # Download latest ZIP and extract loom/ folder
        print("Downloading latest version...")
        zip_url = f"{REPO_URL}/archive/refs/heads/main.zip"
        try:
            import tempfile
            import zipfile
            from urllib.request import urlretrieve
            
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
                urlretrieve(zip_url, tmp.name)
                
                with zipfile.ZipFile(tmp.name, "r") as zf:
                    # Extract only loom/ files
                    for member in zf.namelist():
                        if member.startswith("loom-framework-main/loom/"):
                            # Calculate target path
                            rel_path = member.replace("loom-framework-main/", "", 1)
                            if rel_path and not member.endswith("/"):
                                target = PROJECT_ROOT / rel_path
                                target.parent.mkdir(parents=True, exist_ok=True)
                                with zf.open(member) as src, open(target, "wb") as dst:
                                    dst.write(src.read())
                
                Path(tmp.name).unlink()
            
            print(f"Updated to v{remote}")
        except Exception as e:
            print(f"Update failed: {e}")
            print(f"Download manually from: {REPO_URL}/releases/latest")
            sys.exit(1)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Loom Update Checker")
    parser.add_argument("--quiet", "-q", action="store_true", help="Machine-readable JSON output")
    parser.add_argument("--update", "-u", action="store_true", help="Download and apply update")
    args = parser.parse_args()
    
    if args.update:
        apply_update()
    else:
        check_updates(quiet=args.quiet)


if __name__ == "__main__":
    main()
