#!/usr/bin/env python3
"""
LOOM Framework ZIP Builder

Generates a distributable ZIP file containing the LOOM framework.
This ZIP is meant to be downloaded by users and extracted into their projects.

Usage:
    python loom/scripts/build-zip.py [--version X.Y.Z] [--output path/to/output.zip]

Examples:
    python loom/scripts/build-zip.py
    python loom/scripts/build-zip.py --version 1.0.0
    python loom/scripts/build-zip.py --version 1.0.0 --output /tmp/loom-1.0.0.zip
"""

import os
import sys
import zipfile
import argparse
import re
from pathlib import Path
from typing import Set, List

# Patterns to exclude from ZIP
EXCLUDE_PATTERNS = {
    # Python cache and build
    "__pycache__",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    ".pytest_cache",
    ".coverage",
    "htmlcov",
    "dist",
    "build",
    "*.egg-info",
    ".eggs",
    
    # Version control
    ".git",
    ".gitignore",
    ".github",
    
    # Development
    ".venv",
    "venv",
    "env",
    ".idea",
    ".vscode",
    "*.swp",
    "*.swo",
    "*~",
    ".DS_Store",
    
    # Test directories (users don't need these)
    "tests",
    
    # Examples (for reference only, not in distribution)
    "examples",
    
    # CI/CD (not needed in user's download)
    ".github/workflows",
    
    # Documentation build artifacts
    "docs/_build",
    "site",
    
    # Logs
    "*.log",
    ".task-backups",
    
    # Environment files
    ".env",
    ".env.local",
    
    # Non-essential documentation for end users
    "CONTRIBUTING.md",
    "PUBLISH.md",
    "ABSTRACT.md",
    "guides",
    
    # Internal development files
    "internal",
}

# Files and directories to INCLUDE (override exclusions if needed)
# All files will be placed INSIDE the loom/ folder in the ZIP
INCLUDE_PATTERNS = {
    "loom/**/*",  # Entire framework (essential)
    "README.md",  # Main documentation -> goes to loom/README.md
    "QUICKSTART.md",  # Quick start guide -> goes to loom/QUICKSTART.md
    "LICENSE",  # License file -> goes to loom/LICENSE
    "pyproject.toml",  # Package metadata -> goes to loom/pyproject.toml
    "setup.py",  # Setup script -> goes to loom/setup.py
    "install.sh",  # Unix installer -> goes to loom/install.sh
    "install.ps1",  # Windows installer -> goes to loom/install.ps1
}


def should_exclude(path: str) -> bool:
    """Check if a path should be excluded from the ZIP."""
    path_lower = path.lower()
    
    # Check exclusion patterns
    for pattern in EXCLUDE_PATTERNS:
        # Exact directory name match
        if f"/{pattern}/" in f"/{path}/" or path.endswith(f"/{pattern}"):
            return True
        
        # Wildcard pattern (e.g., *.pyc)
        if pattern.startswith("*."):
            ext = pattern[1:]
            if path.endswith(ext):
                return True
    
    return False


def get_version_from_pyproject() -> str:
    """Extract version from pyproject.toml."""
    pyproject_path = Path("pyproject.toml")
    
    if not pyproject_path.exists():
        return "1.0.0"
    
    content = pyproject_path.read_text()
    match = re.search(r'version = "([^"]+)"', content)
    
    if match:
        return match.group(1)
    
    return "1.0.0"


def build_zip(output_path: str = None, version: str = None) -> str:
    """
    Build the LOOM framework ZIP file.
    
    Args:
        output_path: Path where to save the ZIP file
        version: Version string for the ZIP filename
    
    Returns:
        Path to the created ZIP file
    """
    if version is None:
        version = get_version_from_pyproject()
    
    if output_path is None:
        output_path = f"loom-framework-{version}.zip"
    
    output_path = Path(output_path)
    
    print(f"🗂️  Building LOOM framework ZIP v{version}")
    print(f"📍 Output: {output_path.absolute()}")
    print(f"🚀 Starting ZIP generation...\n")
    
    # Get all files in the project
    project_root = Path(".")
    all_files = list(project_root.rglob("*"))
    
    files_added = 0
    files_excluded = 0
    
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in all_files:
            if file_path.is_dir():
                continue
            
            # Get relative path
            rel_path = str(file_path.relative_to(project_root))
            
            # Skip excluded paths
            if should_exclude(rel_path):
                files_excluded += 1
                continue
            
            # Add file to ZIP with archive name (relative path)
            archive_name = rel_path.replace("\\", "/")
            
            # If it's a root-level meta file (not in loom/), put it inside loom/
            root_meta_files = [
                "README.md", "QUICKSTART.md", "LICENSE", 
                "pyproject.toml", "setup.py", "install.sh", "install.ps1"
            ]
            if archive_name in root_meta_files:
                archive_name = f"loom/{archive_name}"
                print(f"  ✓ {archive_name} (from root)")
            else:
                print(f"  ✓ {archive_name}")
            
            zf.write(file_path, arcname=archive_name)
            files_added += 1
    
    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    
    print(f"\n✅ ZIP created successfully!")
    print(f"   Files added: {files_added}")
    print(f"   Files excluded: {files_excluded}")
    print(f"   Size: {file_size_mb:.2f} MB")
    print(f"\n📦 ZIP file: {output_path.absolute()}")
    print(f"\n🎯 Users should:")
    print(f"   1. Download this ZIP")
    print(f"   2. Extract to get the loom/ folder")
    print(f"   3. Copy loom/ folder to their project")
    print(f"   4. Create PROJECT.md with their project details")
    print(f"   5. Tell their agent: 'read loom'")
    print(f"\n📁 ZIP Structure:")
    print(f"   loom/")
    print(f"   ├── README.md")
    print(f"   ├── QUICKSTART.md")
    print(f"   ├── LICENSE")
    print(f"   ├── install.sh / install.ps1")
    print(f"   ├── scripts/")
    print(f"   ├── templates/")
    print(f"   └── ...")
    
    return str(output_path)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Build LOOM framework distribution ZIP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python loom/scripts/build-zip.py
  python loom/scripts/build-zip.py --version 1.0.0
  python loom/scripts/build-zip.py --output /tmp/loom.zip
        """,
    )
    
    parser.add_argument(
        "--version",
        type=str,
        help="Version string (auto-detected from pyproject.toml if not provided)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output ZIP file path (default: loom-framework-VERSION.zip)",
    )
    
    args = parser.parse_args()
    
    try:
        output_file = build_zip(
            output_path=args.output,
            version=args.version,
        )
        print(f"\n✨ Done! Your ZIP is ready: {output_file}")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error building ZIP: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
