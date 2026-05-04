#!/bin/bash
# init-project.sh - Initialize new project with loom
#
# Usage:
#   bash init-project.sh "ProjectName"
#   bash init-project.sh "ProjectName" --ide windsurf,cursor
#
# This script:
# 1. Creates project directory
# 2. Initializes git repository
# 3. Copies loom
# 4. Runs setup wizard
# 5. Creates initial commit

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# Check arguments
if [ -z "$1" ]; then
    print_error "Project name required"
    echo "Usage: bash init-project.sh \"ProjectName\""
    exit 1
fi

PROJECT_NAME="$1"
IDE_ARG="${2:-}"

# Get framework root (where this script is located)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRAMEWORK_ROOT="$(dirname "$SCRIPT_DIR")"

print_header "Initializing Project: $PROJECT_NAME"

# Create project directory
if [ -d "$PROJECT_NAME" ]; then
    print_error "Directory $PROJECT_NAME already exists"
    exit 1
fi

mkdir "$PROJECT_NAME"
cd "$PROJECT_NAME"
print_success "Created project directory"

# Initialize git
git init
print_success "Initialized git repository"

# Create .gitignore
cat > .gitignore << 'EOF'
# Environment
.env
.env.local
.env.*.local

# Dependencies
node_modules/
venv/
__pycache__/
*.pyc

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Task backups
.task-backups/

# Build
dist/
build/
*.egg-info/
EOF
print_success "Created .gitignore"

# Copy framework
cp -r "$FRAMEWORK_ROOT" ./loom
print_success "Copied loom"

# Run setup
print_header "Running Setup Wizard"

if [ -n "$IDE_ARG" ]; then
    # Auto setup with IDE argument
    python3 loom/scripts/setup.py --auto --project-name "$PROJECT_NAME" $IDE_ARG
else
    # Interactive setup
    python3 loom/scripts/setup.py
fi

# Create initial commit
print_header "Creating Initial Commit"

git add .
git commit -m "chore: initialize project with loom v1.0"
print_success "Created initial commit"

# Success
print_header "Project Initialized Successfully!"
print_info "Project: $PROJECT_NAME"
print_info "Location: $(pwd)"
print_info ""
print_info "Next steps:"
print_info "  1. cd $PROJECT_NAME"
print_info "  2. Review AGENT.md"
print_info "  3. python loom/scripts/task.py start TASK-001 'First task'"
print_info ""
print_info "Read QUICKSTART.md for more information"
