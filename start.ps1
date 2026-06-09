# SynthTrade -- Dev Start Script
# Avvia backend e frontend in finestre separate

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root "synthtrade\backend"
$frontend = Join-Path $root "synthtrade\frontend\synthtrade-ui"
$venv = Join-Path $root ".venv\Scripts\Activate.ps1"

Write-Host "SynthTrade -- avvio in corso..." -ForegroundColor Yellow

chcp 65001 | Out-Null

$existing = Get-NetTCPConnection -LocalPort 8888 -State Listen -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Porta 8888 occupata, terminazione processi uvicorn esistenti..." -ForegroundColor Yellow
    $uvicornProcs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object {
        $_.CommandLine -like "*uvicorn*app.main*"
    }
    foreach ($proc in $uvicornProcs) {
        Write-Host "  Uccisione PID $($proc.ProcessId) (StartTime: $($proc.CreationDate))" -ForegroundColor Gray
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2

    if (Test-NetConnection -ComputerName 127.0.0.1 -Port 8888 -WarningAction SilentlyContinue -InformationLevel Quiet) {
        Write-Host "  ATTENZIONE: porta ancora occupata, tentativo finale..." -ForegroundColor Red
        Stop-Process -Name python -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
    }
}

Write-Host "Avvio backend..." -ForegroundColor Green
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
