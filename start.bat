@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title J.A.R.V.I.S. Protocol Launcher
color 0b

echo =======================================================
echo          INICIALIZANDO SISTEMA J.A.R.V.I.S.
echo =======================================================
echo.

REM 1. Validacao de pre-requisitos
if not exist "venv\Scripts\python.exe" (
    color 0c
    echo [ERRO CRITICO] Ambiente virtual Python nao encontrado em .\venv!
    echo Execute: python -m venv venv ^&^& .\venv\Scripts\pip install -r requirements.txt
    goto erro
)

where node >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    color 0c
    echo [ERRO CRITICO] Node.js nao foi encontrado no PATH do sistema.
    goto erro
)

where npm >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    color 0c
    echo [ERRO CRITICO] NPM nao foi encontrado no PATH do sistema.
    goto erro
)

REM 2. Verifica se o Python Core Daemon esta OUVINDO na porta 8765
netstat -ano | findstr /R /C:":8765 .*LISTENING" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [1/2] Python Core Daemon ja esta ativo e ouvindo na porta 8765.
) else (
    echo [1/2] Iniciando Python Core Daemon na porta 8765...
    start "JARVIS Core Daemon" cmd /k "cd /d "%~dp0" && .\venv\Scripts\python.exe core\main.py"
    timeout /t 3 /nobreak >nul
)

REM 3. Inicia o HUD Holografico
echo [2/2] Abrindo HUD Holografico Desktop...
if not exist "hud\node_modules" (
    echo Instalando dependencias do HUD...
    cd /d "%~dp0hud"
    call npm install
)

cd /d "%~dp0hud"
call npm run start

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [AVISO] O HUD encerrou com codigo de saida %ERRORLEVEL%.
)
goto fim

:erro
echo.
echo Ocorreu uma falha na inicializacao.

:fim
echo.
echo Pressione qualquer tecla para fechar esta janela...
pause >nul
