# loom - One-liner installer for Windows
# Usage: irm https://raw.githubusercontent.com/otto78/loom-framework/main/install.ps1 | iex

$ErrorActionPreference = "Stop"

$loom_REPO = "https://github.com/otto78/loom-framework.git"
$loom_DIR = "$env:USERPROFILE\.loom-framework"

Write-Host "🧵 loom Installer" -ForegroundColor Cyan
Write-Host "============================" -ForegroundColor Cyan
Write-Host ""

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ $pythonVersion detected" -ForegroundColor Green
} catch {
    Write-Host "❌ Python not found. Please install Python 3.8 or higher." -ForegroundColor Red
    exit 1
}

# Check Git
try {
    $gitVersion = git --version 2>&1
    Write-Host "✅ Git detected" -ForegroundColor Green
} catch {
    Write-Host "❌ Git not found. Please install Git first." -ForegroundColor Red
    exit 1
}

# Clone or update loom
if (Test-Path $loom_DIR) {
    Write-Host "📦 Updating existing loom installation..." -ForegroundColor Yellow
    Set-Location $loom_DIR
    git pull --quiet
} else {
    Write-Host "📦 Cloning loom..." -ForegroundColor Yellow
    git clone --quiet $loom_REPO $loom_DIR
}

Write-Host "✅ loom installed to $loom_DIR" -ForegroundColor Green
Write-Host ""

# Detect project
$projectDetected = $false
if ((Test-Path "pyproject.toml") -or (Test-Path "package.json") -or (Test-Path "pom.xml")) {
    $projectDetected = $true
    Write-Host "🔍 Project detected in current directory: $(Get-Location)" -ForegroundColor Cyan
    Write-Host ""
    $response = Read-Host "Setup loom in this project? (y/n)"
    if ($response -eq "y" -or $response -eq "Y") {
        python "$loom_DIR\loom\scripts\setup.py"
    } else {
        Write-Host "ℹ️  To setup loom later, run:" -ForegroundColor Blue
        Write-Host "   python $loom_DIR\loom\scripts\setup.py"
    }
} else {
    Write-Host "ℹ️  No project detected in current directory." -ForegroundColor Blue
    Write-Host "   Navigate to your project and run:"
    Write-Host "   python $loom_DIR\loom\scripts\setup.py"
}

Write-Host ""
Write-Host "✨ Installation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📚 Documentation: https://otto78.github.io/loom-framework/docs.html"
Write-Host "🐙 GitHub: https://github.com/otto78/loom-framework"
