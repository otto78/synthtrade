# SynthTrade -- Dev Start Script
# Avvia backend e frontend in finestre separate

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root "synthtrade\backend"
$frontend = Join-Path $root "synthtrade\frontend\synthtrade-ui"
$venv = Join-Path $root ".venv\Scripts\Activate.ps1"

Write-Host "SynthTrade -- avvio in corso..." -ForegroundColor Yellow

chcp 65001 | Out-Null
Start-Process pwsh -ArgumentList "-NoExit", "-Command", `
  "chcp 65001 | Out-Null; Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force; & '$venv'; cd '$backend'; uvicorn app.main:app --reload --port 8888" `
  -WindowStyle Normal

Start-Process pwsh -ArgumentList "-NoExit", "-Command", `
  "chcp 65001 | Out-Null; cd '$frontend'; npx ng serve --port 4208 --proxy-config proxy.conf.json" `
  -WindowStyle Normal

Write-Host ""
Write-Host "  Backend  -> http://localhost:8008/health" -ForegroundColor Cyan
Write-Host "  Frontend -> http://localhost:4208" -ForegroundColor Cyan
Write-Host "  Password -> admin123" -ForegroundColor Green
Write-Host ""

Start-Sleep -Seconds 5
Start-Process "http://localhost:4208"
