@echo off
REM run_synthtrade.cmd — avvia l'ambiente dev locale SynthTrade puntando al VPS.
REM Apre 3 finestre etichettate:
REM   [1/3] Tunnel SSH   -> deve restare FERMA/nera (ssh -N non stampa nulla: e' normale)
REM   [2/3] Frontend     -> ng serve su :4208
REM   [3/3] Backend      -> uvicorn su :8888 (env dal VPS, paper-safe)
setlocal
title SynthTrade Dev Launcher
echo.
echo ================================================
echo  SynthTrade - ambiente dev locale (tunnel + VPS)
echo ================================================
echo.

start "SynthTrade [1/3] Tunnel SSH VPS (finestra NERA = normale)" cmd /k "echo Tunnel SSH netcup: DB=:55432 PostgREST=:53000 Gateway=:54000 -- finestra deve restare ferma. & ssh -N -o ServerAliveInterval=60 -o ExitOnForwardFailure=yes netcup -L 127.0.0.1:55432:172.18.0.2:5432 -L 127.0.0.1:53000:172.20.0.2:3000 -L 127.0.0.1:54000:172.20.0.4:80"

start "SynthTrade [2/3] Frontend (ng serve :4208)" cmd /k "echo Avvio frontend su http://localhost:4208 ... & cd /d %~dp0synthtrade\frontend\synthtrade-ui & ng serve --port 4208"

start "SynthTrade [3/3] Backend (uvicorn :8888)" powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_synthtrade_backend.ps1"

timeout /t 2 /nobreak >nul
echo Tre finestre avviate:
echo   [1/3] Tunnel: resta nera (ok). Se si chiude, controlla `ssh netcup`.
echo   [2/3] Frontend: http://localhost:4208
echo   [3/3] Backend: http://127.0.0.1:8888  (log dentro la finestra)
echo.
pause