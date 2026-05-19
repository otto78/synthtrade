# SynthTrade — Dev Start Script
# Avvia backend (porta 8008) e frontend (porta 4208) in finestre separate

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root "synthtrade\backend"
$frontend = Join-Path $root "synthtrade\frontend\synthtrade-ui"
$venv = Join-Path $root ".venv\Scripts\Activate.ps1"

Write-Host "⚡ SynthTrade — avvio in corso..." -ForegroundColor Yellow

# Backend
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
  "Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned; & '$venv'; cd '$backend'; uvicorn app.main:app --reload --port 8888" `
  -WindowStyle Normal

# Frontend
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
  "cd '$frontend'; npx ng serve --port 4208 --proxy-config proxy.conf.json" `
  -WindowStyle Normal

Write-Host ""
Write-Host "  Backend  → http://localhost:8888/health" -ForegroundColor Cyan
Write-Host "  Frontend → http://localhost:4208" -ForegroundColor Cyan
Write-Host "  Password → admin123" -ForegroundColor Green
Write-Host ""

# Apri il browser dopo 5 secondi
Start-Sleep -Seconds 5
Start-Process "http://localhost:4208"
