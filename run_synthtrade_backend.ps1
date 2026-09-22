# run_synthtrade_backend.ps1
# Carica l'env dal .env del VPS, punta SUPABASE_URL al tunnel SSH locale,
# forza la modalita' paper-safe e avvia uvicorn (venv) con reload.
# Le chiavi ONCE risiedono solo sul server: qui vengono usate in memoria e mai salvate su disco.

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $root 'synthtrade\backend'
$tmpEnv = Join-Path $env:TEMP 'synthtrade_env_vps.env'

Write-Host 'Scarico .env dal VPS...' -ForegroundColor Cyan
scp netcup:/opt/vps/synthtrade/.env $tmpEnv
if (-not $?) { throw 'scp fallito: avvio il tunnel e riprova.' }

Write-Host 'Applico override locali (paper-safe + tunnel)...' -ForegroundColor Cyan
foreach ($line in Get-Content $tmpEnv) {
    if ([string]::IsNullOrWhiteSpace($line) -or $line.StartsWith('#')) { continue }
    $parts = $line -split '=', 2
    if ($parts.Count -ne 2) { continue }
    Set-Item -Path "env:$($parts[0].Trim())" -Value $parts[1]
}

# Sicurezza: mai trading live dal PC di sviluppo.
$env:SUPABASE_URL = 'http://127.0.0.1:53000'      # PostgREST via tunnel
$env:TRADING_MODE = 'test'
$env:SCALPING_FORCE_PAPER = 'true'
$env:ALLOW_LIVE_MODE = 'false'
$env:CORS_ORIGINS = 'http://localhost:4200,http://localhost:4208'

Remove-Item $tmpEnv -Force

Write-Host "Backend su http://127.0.0.1:8888 (DB + PostgREST via tunnel sul VPS, paper-safe)" -ForegroundColor Green
Set-Location $backendDir
& (Join-Path $root '.venv\Scripts\uvicorn.exe') app.main:app --host 127.0.0.1 --port 8888 --reload