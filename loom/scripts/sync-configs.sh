#!/bin/bash
# sync-configs.sh - Sync IDE configurations with AGENT.md
#
# Usage:
#   bash sync-configs.sh              # Sync all IDE configs
#   bash sync-configs.sh windsurf     # Sync only Windsurf
#   bash sync-configs.sh --check      # Check if configs are in sync
#
# This script ensures all IDE configuration files are consistent with AGENT.md
# Run this after updating AGENT.md to propagate changes to all IDEs

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Check if AGENT.md exists
if [ ! -f "AGENT.md" ]; then
    print_error "AGENT.md not found in current directory"
    print_info "Run this script from project root"
    exit 1
fi

# Get last modified time of AGENT.md
AGENT_MD_TIME=$(stat -f %m "AGENT.md" 2>/dev/null || stat -c %Y "AGENT.md" 2>/dev/null)

print_header "Syncing IDE Configurations"

# Function to check if file needs update
needs_update() {
    local file=$1
    
    if [ ! -f "$file" ]; then
        return 0  # File doesn't exist, needs creation
    fi
    
    local file_time=$(stat -f %m "$file" 2>/dev/null || stat -c %Y "$file" 2>/dev/null)
    
    if [ "$file_time" -lt "$AGENT_MD_TIME" ]; then
        return 0  # File is older than AGENT.md
    fi
    
    return 1  # File is up to date
}

# Function to update IDE config
update_config() {
    local ide=$1
    local config_file=$2
    local template_file=$3
    
    if [ "$CHECK_ONLY" = true ]; then
        if needs_update "$config_file"; then
            print_warning "$config_file is out of sync"
            OUT_OF_SYNC=true
        else
            print_success "$config_file is in sync"
        fi
        return
    fi
    
    if needs_update "$config_file"; then
        if [ -f "$template_file" ]; then
            cp "$template_file" "$config_file"
            print_success "Updated $config_file"
        else
            print_warning "Template not found: $template_file"
        fi
    else
        print_info "$config_file is already up to date"
    fi
}

# Parse arguments
CHECK_ONLY=false
SPECIFIC_IDE=""
OUT_OF_SYNC=false

if [ "$1" = "--check" ]; then
    CHECK_ONLY=true
    print_info "Running in check mode (no changes will be made)"
elif [ -n "$1" ]; then
    SPECIFIC_IDE="$1"
    print_info "Syncing only: $SPECIFIC_IDE"
fi

# IDE configurations
declare -A IDE_CONFIGS=(
    ["windsurf"]=".windsurfrules|loom/ide-configs/windsurf/windsurfrules.template"
    ["claude"]="CLAUDE.md|loom/ide-configs/claude/CLAUDE.md.template"
    ["cursor"]=".cursorrules|loom/ide-configs/cursor/cursorrules.template"
    ["antigravity"]="GEMINI.md|loom/ide-configs/antigravity/GEMINI.md.template"
    ["agents"]="AGENTS.md|loom/ide-configs/antigravity/AGENTS.md.template"
    ["vscode"]=".github/copilot-instructions.md|loom/ide-configs/vscode/copilot-instructions.md.template"
    ["intellij"]=".aiassistant/rules/loom.md|loom/ide-configs/intellij/LOOM.md.template"
)

# Sync configurations
for ide in "${!IDE_CONFIGS[@]}"; do
    # Skip if specific IDE requested and this isn't it
    if [ -n "$SPECIFIC_IDE" ] && [ "$ide" != "$SPECIFIC_IDE" ]; then
        continue
    fi
    
    IFS='|' read -r config_file template_file <<< "${IDE_CONFIGS[$ide]}"
    
    update_config "$ide" "$config_file" "$template_file"
done

# Summary
if [ "$CHECK_ONLY" = true ]; then
    if [ "$OUT_OF_SYNC" = true ]; then
        print_header "Some configurations are out of sync"
        print_info "Run 'bash sync-configs.sh' to update them"
        exit 1
    else
        print_header "All configurations are in sync!"
        exit 0
    fi
else
    print_header "Sync Complete!"
    print_info "All IDE configurations are now in sync with AGENT.md"
fi
