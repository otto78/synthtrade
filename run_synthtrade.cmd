@echo off
REM run_synthtrade.cmd — avvia l'ambiente dev locale puntando al VPS.
REM 1) Tunnel SSH (DB + PostgREST) in una finestra dedicata
REM 2) Frontend Angular (ng serve) in una finestra dedicata
REM 3) Backend FastAPI nel terminale corrente (env dal VPS, paper-safe)

start "SynthTrade SSH Tunnel (VPS)" cmd /k ssh -N -o ServerAliveInterval=60 -o ExitOnForwardFailure=yes netcup -L 127.0.0.1:55432:172.18.0.2:5432 -L 127.0.0.1:53000:172.20.0.2:3000

start "SynthTrade Frontend (ng serve)" cmd /k "cd /d %~dp0synthtrade\frontend\synthtrade-ui && ng serve"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_synthtrade_backend.ps1"