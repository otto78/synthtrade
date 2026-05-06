#!/bin/bash
# loom - One-liner installer
# Usage: curl -fsSL https://raw.githubusercontent.com/otto78/loom-framework/main/install.sh | bash

set -e

loom_REPO="https://github.com/otto78/loom-framework.git"
loom_DIR="$HOME/.loom-framework"
PYTHON_MIN_VERSION="3.8"

echo "🧵 loom Installer"
echo "============================"
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python $PYTHON_MIN_VERSION or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Python $PYTHON_VERSION detected"

# Check git
if ! command -v git &> /dev/null; then
    echo "❌ Git not found. Please install git first."
    exit 1
fi

echo "✅ Git detected"

# Clone or update loom
if [ -d "$loom_DIR" ]; then
    echo "📦 Updating existing loom installation..."
    cd "$loom_DIR"
    git pull --quiet
else
    echo "📦 Cloning loom..."
    git clone --quiet "$loom_REPO" "$loom_DIR"
fi

echo "✅ loom installed to $loom_DIR"
echo ""

# Detect project directory
if [ -f "pyproject.toml" ] || [ -f "package.json" ] || [ -f "pom.xml" ]; then
    echo "🔍 Project detected in current directory: $(pwd)"
    echo ""
    read -p "Setup loom in this project? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        python3 "$loom_DIR/loom/scripts/setup.py"
    else
        echo "ℹ️  To setup loom later, run:"
        echo "   python3 $loom_DIR/loom/scripts/setup.py"
    fi
else
    echo "ℹ️  No project detected in current directory."
    echo "   Navigate to your project and run:"
    echo "   python3 $loom_DIR/loom/scripts/setup.py"
fi

echo ""
echo "✨ Installation complete!"
echo ""
echo "📚 Documentation: https://otto78.github.io/loom-framework/docs.html"
echo "🐙 GitHub: https://github.com/otto78/loom-framework"
