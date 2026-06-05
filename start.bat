@echo off
chcp 65001 >nul 2>&1

echo SynthTrade -- avvio in corso...

:backend
start "SynthTrade Backend" pwsh -NoExit -Command "chcp 65001 | Out-Null; Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force; & '%~dp0.venv\Scripts\Activate.ps1'; cd /d '%~dp0synthtrade\backend'; uvicorn app.main:app --reload --port 8888"

timeout /t 3 /nobreak >nul

:frontend
start "SynthTrade Frontend" pwsh -NoExit -Command "chcp 65001 | Out-Null; cd /d '%~dp0synthtrade\frontend\synthtrade-ui'; npx ng serve --port 4208 --proxy-config proxy.conf.json"

echo.
echo   Backend  -> http://localhost:8008/health
echo   Frontend -> http://localhost:4208
echo   Password -> admin123
echo.

timeout /t 5 /nobreak >nul
start http://localhost:4208
