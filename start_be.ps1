# SynthTrade -- Dev Start Backend Only (non tocca il frontend)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root "synthtrade\backend"
$venv = Join-Path $root ".venv\Scripts\Activate.ps1"

$BACKEND_PORT = 8888

Write-Host ""
Write-Host "SynthTrade -- Dev Start (Backend Only)" -ForegroundColor Yellow
Write-Host ""

chcp 65001 | Out-Null

function Stop-ProcessOnPort {
    param([int]$Port)

    $listener = netstat -ano | Select-String ":$Port\s" | Select-String "LISTEN"
    if (-not $listener) {
        return $true
    }

    Write-Host "  Porta $Port occupata" -ForegroundColor Yellow
    foreach ($line in $listener) {
        if ($line -match '\s+(\d+)$') {
            $procId = [int]$Matches[1]
            try {
                $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
                if ($proc) {
                    Write-Host "  Killing PID $procId ($($proc.Name))..." -ForegroundColor Gray
                    Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
                }
            } catch {}
        }
    }

    Start-Sleep -Seconds 2

    $still = netstat -ano | Select-String ":$Port\s" | Select-String "LISTEN"
    if ($still) {
        Write-Host "  Porta $Port ancora occupata dopo cleanup!" -ForegroundColor Red
        return $false
    }

    Write-Host "  Porta $Port libera" -ForegroundColor Green
    return $true
}

# --- Pulizia solo porta backend ---
$ok = Stop-ProcessOnPort -Port $BACKEND_PORT
if (-not $ok) {
    Write-Host "Impossibile liberare la porta $BACKEND_PORT. Uscita." -ForegroundColor Red
    exit 1
}

# --- Verifiche ---
if (-not (Test-Path $venv)) {
    Write-Host "  venv non trovato: $venv" -ForegroundColor Red
    exit 1
}
Write-Host "  venv trovato" -ForegroundColor Green

if (-not (Test-Path "$backend\app\main.py")) {
    Write-Host "  Backend non trovato in: $backend" -ForegroundColor Red
    exit 1
}
Write-Host "  Backend trovato" -ForegroundColor Green

# --- Avvio backend ---
Write-Host ""
Write-Host "Avvio backend su porta $BACKEND_PORT..." -ForegroundColor Green
Start-Process pwsh -ArgumentList "-NoExit", "-Command", `
  "chcp 65001 | Out-Null; ``
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force; ``
   & '$venv'; ``
   cd '$backend'; ``
   Write-Host 'Backend SynthTrade avviato' -ForegroundColor Green; ``
   uvicorn app.main:app --port $BACKEND_PORT --ws-ping-interval 60 --ws-ping-timeout 30" `
  -WindowStyle Normal

Write-Host ""
Write-Host "Backend -> http://localhost:$BACKEND_PORT" -ForegroundColor Cyan
Write-Host "  Il frontend Angular NON viene toccato, resta in esecuzione." -ForegroundColor Green
Write-Host ""