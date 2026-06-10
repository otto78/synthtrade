# SynthTrade -- Dev Start Script
# Avvia backend e frontend in finestre separate

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root "synthtrade\backend"
$frontend = Join-Path $root "synthtrade\frontend\synthtrade-ui"
$venv = Join-Path $root ".venv\Scripts\Activate.ps1"

$BACKEND_PORT = 8888
$FRONTEND_PORT = 4208

Write-Host ""
Write-Host "╔══════════════════════════════════════╗" -ForegroundColor Yellow
Write-Host "║     SynthTrade -- Dev Start          ║" -ForegroundColor Yellow
Write-Host "╚══════════════════════════════════════╝" -ForegroundColor Yellow
Write-Host ""

chcp 65001 | Out-Null

# ── FUNZIONE: Kill tutti i processi Python sulla porta specificata ──────────
function Kill-PortProcesses {
    param([int]$Port)

    # Metodo 1: via netstat — trova il PID che ascolta sulla porta
    $netstatLines = netstat -ano | Select-String ":$Port\s"
    $pidsFromPort = @()
    foreach ($line in $netstatLines) {
        if ($line -match '\s+(\d+)$') {
            $portPid = [int]$Matches[1]
            if ($portPid -gt 0 -and $portPid -notin $pidsFromPort) {
                $pidsFromPort += $portPid
            }
        }
    }

    if ($pidsFromPort.Count -gt 0) {
        Write-Host "  Porta $Port occupata da PID: $($pidsFromPort -join ', ')" -ForegroundColor Yellow
        foreach ($portPid in $pidsFromPort) {
            try {
                $proc = Get-Process -Id $portPid -ErrorAction SilentlyContinue
                if ($proc) {
                    Write-Host "  Killing PID $portPid ($($proc.Name))..." -ForegroundColor Gray
                    Stop-Process -Id $portPid -Force -ErrorAction SilentlyContinue
                }
            } catch {}
        }
        Start-Sleep -Seconds 1
    }

    # Metodo 2: cerca tutti i python.exe con uvicorn o synthtrade nella cmdline
    $pythonProcs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object {
        $_.CommandLine -like "*uvicorn*" -or
        $_.CommandLine -like "*app.main*" -or
        $_.CommandLine -like "*synthtrade*"
    }
    foreach ($proc in $pythonProcs) {
        Write-Host "  Killing Python PID $($proc.ProcessId) (uvicorn/synthtrade)..." -ForegroundColor Gray
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
    }

    Start-Sleep -Seconds 2

    # Verifica finale
    $stillOccupied = netstat -ano | Select-String ":$Port\s" | Select-String "LISTEN"
    if ($stillOccupied) {
        Write-Host "  ⚠️  Porta $Port ancora occupata dopo cleanup!" -ForegroundColor Red
        Write-Host "  Prova a riavviare il terminale o riesegui lo script." -ForegroundColor Red
        return $false
    }
    return $true
}

# ── CLEANUP BACKEND PORT ────────────────────────────────────────────────────
$backendOccupied = netstat -ano | Select-String ":$BACKEND_PORT\s" | Select-String "LISTEN"
if ($backendOccupied) {
    Write-Host "Cleanup porta $BACKEND_PORT..." -ForegroundColor Yellow
    $ok = Kill-PortProcesses -Port $BACKEND_PORT
    if (-not $ok) {
        Write-Host "Impossibile liberare la porta. Uscita." -ForegroundColor Red
        exit 1
    }
    Write-Host "  ✓ Porta $BACKEND_PORT libera" -ForegroundColor Green
} else {
    Write-Host "  ✓ Porta $BACKEND_PORT libera" -ForegroundColor Green
}

# ── CLEANUP FRONTEND PORT ───────────────────────────────────────────────────
$frontendOccupied = netstat -ano | Select-String ":$FRONTEND_PORT\s" | Select-String "LISTEN"
if ($frontendOccupied) {
    Write-Host "Cleanup porta $FRONTEND_PORT..." -ForegroundColor Yellow
    Kill-PortProcesses -Port $FRONTEND_PORT | Out-Null
    Write-Host "  ✓ Porta $FRONTEND_PORT libera" -ForegroundColor Green
} else {
    Write-Host "  ✓ Porta $FRONTEND_PORT libera" -ForegroundColor Green
}

# ── VERIFICA VENV ───────────────────────────────────────────────────────────
if (-not (Test-Path $venv)) {
    Write-Host "  ✗ venv non trovato: $venv" -ForegroundColor Red
    Write-Host "  Crea il venv con: python -m venv .venv" -ForegroundColor Yellow
    exit 1
}
Write-Host "  ✓ venv trovato" -ForegroundColor Green

# ── VERIFICA BACKEND DIR ────────────────────────────────────────────────────
if (-not (Test-Path "$backend\app\main.py")) {
    Write-Host "  ✗ Backend non trovato in: $backend" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ Backend trovato" -ForegroundColor Green

# ── AVVIO BACKEND ───────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Avvio backend su porta $BACKEND_PORT..." -ForegroundColor Green
Start-Process pwsh -ArgumentList "-NoExit", "-Command", `
  "chcp 65001 | Out-Null; `
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force; `
   & '$venv'; `
   cd '$backend'; `
   Write-Host 'Backend SynthTrade avviato' -ForegroundColor Green; `
   uvicorn app.main:app --reload --port $BACKEND_PORT" `
  -WindowStyle Normal

# ── AVVIO FRONTEND ──────────────────────────────────────────────────────────
Write-Host "Avvio frontend su porta $FRONTEND_PORT..." -ForegroundColor Green
Start-Process pwsh -ArgumentList "-NoExit", "-Command", `
  "chcp 65001 | Out-Null; `
   cd '$frontend'; `
   Write-Host 'Frontend SynthTrade avviato' -ForegroundColor Green; `
   npx ng serve --port $FRONTEND_PORT --proxy-config proxy.conf.json" `
  -WindowStyle Normal

# ── RIEPILOGO ───────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "╔══════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Backend  -> http://localhost:$BACKEND_PORT   ║" -ForegroundColor Cyan
Write-Host "║  Frontend -> http://localhost:$FRONTEND_PORT   ║" -ForegroundColor Cyan
Write-Host "║  Password -> admin123                ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

Start-Sleep -Seconds 5
Start-Process "http://localhost:$FRONTEND_PORT"