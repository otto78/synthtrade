# run_synthtrade_backend.ps1
# Carica l'env dal .env del VPS, punta SUPABASE_URL al tunnel SSH locale,
# forza la modalita' paper-safe e avvia uvicorn (venv) con reload.
# Le chiavi vivono solo sul server: qui vengono usate in memoria e mai salvate su disco.
$ErrorActionPreference = 'Stop'

try {
    $root = Split-Path -Parent $MyInvocation.MyCommand.Path
    $backendDir = Join-Path $root 'synthtrade\backend'
    $tmpEnv = Join-Path $env:TEMP 'synthtrade_env_vps.env'

    Write-Host 'Scarico .env dal VPS...' -ForegroundColor Cyan
    scp netcup:/opt/vps/synthtrade/.env $tmpEnv
    if (-not $?) { throw 'scp fallito: tunnel non attivo? Controlla la finestra [1/3] e riavvia.' }

    Write-Host 'Applico override locali (paper-safe + tunnel)...' -ForegroundColor Cyan
    foreach ($line in Get-Content $tmpEnv) {
        if ([string]::IsNullOrWhiteSpace($line) -or $line.StartsWith('#')) { continue }
        $parts = $line -split '=', 2
        if ($parts.Count -ne 2) { continue }
        Set-Item -Path "env:$($parts[0].Trim())" -Value $parts[1]
    }

    # Sicurezza: mai trading live dal PC di sviluppo.
    $env:SUPABASE_URL = 'http://127.0.0.1:54000'      # gateway nginx via tunnel (come in prod: /rest/v1 -> PostgREST)
    $env:TRADING_MODE = 'test'
    $env:SCALPING_FORCE_PAPER = 'true'
    $env:ALLOW_LIVE_MODE = 'false'
    $env:CORS_ORIGINS = 'http://localhost:4200,http://localhost:4208'

    Remove-Item $tmpEnv -Force -ErrorAction SilentlyContinue

    $venvPython = Join-Path $root '.venv\Scripts\python.exe'
    if (-not (Test-Path $venvPython)) { throw "venv mancante: $venvPython" }

    # Fail-fast: verifica che il tunnel esponga davvero il gateway (SUPABASE_URL)
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $task = $client.ConnectAsync('127.0.0.1', 54000)
        if (-not $task.Wait(5000)) { throw 'Connessione a 127.0.0.1:54000 fallita: tunnel off. Controlla la finestra [1/3].' }
    } finally {
        $client.Close()
    }

    Write-Host "Backend su http://127.0.0.1:8888 (DB/PostgREST/gateway via tunnel VPS, paper-safe)" -ForegroundColor Green
    Set-Location $backendDir
    & $venvPython -m uvicorn app.main:app --host 127.0.0.1 --port 8888 --reload
}
catch {
    Write-Host "ERRORE: $($_.Exception.Message)" -ForegroundColor Red
    Read-Host 'Premi INVIO per chiudere'
    exit 1
}