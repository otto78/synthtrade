# init-project.ps1 - Initialize new project with loom
#
# Usage:
#   .\init-project.ps1 -ProjectName "MyProject"
#   .\init-project.ps1 -ProjectName "MyProject" -IDE "windsurf,cursor"
#
# This script:
# 1. Creates project directory
# 2. Initializes git repository
# 3. Copies loom
# 4. Runs setup wizard
# 5. Creates initial commit

param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectName,
    
    [Parameter(Mandatory=$false)]
    [string]$IDE = ""
)

# Functions
function Write-Header {
    param([string]$Message)
    Write-Host "`n========================================" -ForegroundColor Blue
    Write-Host $Message -ForegroundColor Blue
    Write-Host "========================================`n" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor Green
}

function Write-ErrorMsg {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor Red
}

function Write-InfoMsg {
    param([string]$Message)
    Write-Host "ℹ️  $Message" -ForegroundColor Yellow
}

# Get framework root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$FrameworkRoot = Split-Path -Parent $ScriptDir

Write-Header "Initializing Project: $ProjectName"

# Create project directory
if (Test-Path $ProjectName) {
    Write-ErrorMsg "Directory $ProjectName already exists"
    exit 1
}

New-Item -ItemType Directory -Path $ProjectName | Out-Null
Set-Location $ProjectName
Write-Success "Created project directory"

# Initialize git
git init
Write-Success "Initialized git repository"

# Create .gitignore
@"
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
"@ | Out-File -FilePath ".gitignore" -Encoding UTF8
Write-Success "Created .gitignore"

# Copy framework
Copy-Item -Path $FrameworkRoot -Destination ".\loom" -Recurse
Write-Success "Copied loom"

# Run setup
Write-Header "Running Setup Wizard"

if ($IDE -ne "") {
    # Auto setup with IDE argument
    python loom\scripts\setup.py --auto --project-name $ProjectName --ide $IDE
} else {
    # Interactive setup
    python loom\scripts\setup.py
}

# Create initial commit
Write-Header "Creating Initial Commit"

git add .
git commit -m "chore: initialize project with loom v1.0"
Write-Success "Created initial commit"

# Success
Write-Header "Project Initialized Successfully!"
Write-InfoMsg "Project: $ProjectName"
Write-InfoMsg "Location: $(Get-Location)"
Write-InfoMsg ""
Write-InfoMsg "Next steps:"
Write-InfoMsg "  1. cd $ProjectName"
Write-InfoMsg "  2. Review AGENT.md"
Write-InfoMsg "  3. python loom\scripts\task.py start TASK-001 'First task'"
Write-InfoMsg ""
Write-InfoMsg "Read QUICKSTART.md for more information"
