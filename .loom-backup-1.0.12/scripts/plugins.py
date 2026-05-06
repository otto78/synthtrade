#!/usr/bin/env python3
"""
Plugin System — Loom Framework

Allows users to add custom directives from external sources.
Plugins are directories containing .md directive files that get
loaded alongside the built-in loom directives.

Usage (natural language):
    "add plugin from https://github.com/user/my-directives"
    "add plugin from /path/to/local/directives"
    "list plugins"
    "remove plugin my-directives"

Usage (CLI):
    python loom/scripts/plugins.py add --source https://github.com/user/my-directives
    python loom/scripts/plugins.py add --source /path/to/local/directives --name my-directives
    python loom/scripts/plugins.py list
    python loom/scripts/plugins.py remove --name my-directives
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path.cwd()
PLUGINS_DIR = PROJECT_ROOT / "loom" / "plugins"
PLUGINS_REGISTRY = PLUGINS_DIR / "plugins.json"


def ensure_plugins_dir():
    """Create plugins directory if it doesn't exist."""
    PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
    if not PLUGINS_REGISTRY.exists():
        PLUGINS_REGISTRY.write_text("[]", encoding="utf-8")


def load_registry() -> list:
    """Load the plugins registry."""
    ensure_plugins_dir()
    return json.loads(PLUGINS_REGISTRY.read_text(encoding="utf-8"))


def save_registry(plugins: list):
    """Save the plugins registry."""
    PLUGINS_REGISTRY.write_text(
        json.dumps(plugins, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def add_plugin(source: str, name: Optional[str] = None):
    """Add a plugin from a git repo URL or local path."""
    source_path = Path(source)
    
    # Determine plugin name
    if name is None:
        if source.startswith("http"):
            name = source.rstrip("/").split("/")[-1].replace(".git", "")
        else:
            name = source_path.name
    
    plugin_dir = PLUGINS_DIR / name
    
    if plugin_dir.exists():
        print(f"Plugin '{name}' already exists. Use 'remove' first to reinstall.")
        sys.exit(1)
    
    ensure_plugins_dir()
    
    # Clone or copy
    if source.startswith("http") or source.startswith("git@"):
        print(f"Cloning plugin '{name}' from {source}...")
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", source, str(plugin_dir)],
                check=True, capture_output=True, text=True
            )
            # Remove .git from cloned plugin
            git_dir = plugin_dir / ".git"
            if git_dir.exists():
                shutil.rmtree(git_dir)
        except subprocess.CalledProcessError as e:
            print(f"Failed to clone: {e.stderr}")
            sys.exit(1)
    elif source_path.is_dir():
        print(f"Copying plugin '{name}' from {source}...")
        shutil.copytree(source_path, plugin_dir)
    else:
        print(f"Source not found: {source}")
        sys.exit(1)
    
    # Count directives
    md_files = list(plugin_dir.glob("**/*.md"))
    directive_count = len([f for f in md_files if not f.name.startswith("_") and f.name != "README.md"])
    
    # Update registry
    plugins = load_registry()
    plugins.append({
        "name": name,
        "source": source,
        "directives": directive_count
    })
    save_registry(plugins)
    
    print(f"Plugin '{name}' added successfully ({directive_count} directives)")
    
    # List the directives
    for f in sorted(md_files):
        if not f.name.startswith("_") and f.name != "README.md":
            print(f"  - {f.name}")


def list_plugins():
    """List all installed plugins."""
    plugins = load_registry()
    
    if not plugins:
        print("No plugins installed.")
        print("\nTo add a plugin:")
        print("  python loom/scripts/plugins.py add --source https://github.com/user/directives")
        print("  python loom/scripts/plugins.py add --source /path/to/local/directives")
        return
    
    print(f"\nInstalled plugins ({len(plugins)}):\n")
    for p in plugins:
        print(f"  {p['name']} — {p['directives']} directives")
        print(f"    Source: {p['source']}")
        
        # List directive files
        plugin_dir = PLUGINS_DIR / p["name"]
        if plugin_dir.exists():
            md_files = sorted(plugin_dir.glob("**/*.md"))
            for f in md_files:
                if not f.name.startswith("_") and f.name != "README.md":
                    print(f"    - {f.name}")
        print()


def remove_plugin(name: str):
    """Remove an installed plugin."""
    plugins = load_registry()
    
    plugin = next((p for p in plugins if p["name"] == name), None)
    if plugin is None:
        print(f"Plugin '{name}' not found.")
        sys.exit(1)
    
    plugin_dir = PLUGINS_DIR / name
    if plugin_dir.exists():
        shutil.rmtree(plugin_dir)
    
    plugins = [p for p in plugins if p["name"] != name]
    save_registry(plugins)
    
    print(f"Plugin '{name}' removed successfully.")


def main():
    parser = argparse.ArgumentParser(description="Loom Plugin Manager")
    subparsers = parser.add_subparsers(dest="command", help="Command")
    
    # Add
    add_parser = subparsers.add_parser("add", help="Add a plugin")
    add_parser.add_argument("--source", required=True, help="Git URL or local path")
    add_parser.add_argument("--name", help="Plugin name (auto-detected if omitted)")
    
    # List
    subparsers.add_parser("list", help="List installed plugins")
    
    # Remove
    remove_parser = subparsers.add_parser("remove", help="Remove a plugin")
    remove_parser.add_argument("--name", required=True, help="Plugin name")
    
    args = parser.parse_args()
    
    if args.command == "add":
        add_plugin(args.source, args.name)
    elif args.command == "list":
        list_plugins()
    elif args.command == "remove":
        remove_plugin(args.name)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
