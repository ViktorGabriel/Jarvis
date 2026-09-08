@echo off
title J.A.R.V.I.S. Protocol Launcher
color 0b

echo =======================================================
echo          INICIALIZANDO SISTEMA J.A.R.V.I.S.
echo =======================================================
echo.

REM Inicia o Python Core Daemon em segundo plano
echo [1/2] Iniciando Python Core Daemon na porta 8765...
start "JARVIS Core Daemon" cmd /k ".\venv\Scripts\python.exe core\main.py"

REM Aguarda 2 segundos para o servidor WebSocket subir
timeout /t 2 /nobreak >nul

REM Inicia o HUD Desktop
echo [2/2] Abrindo HUD Holografico Desktop...
cd hud
npm run start
