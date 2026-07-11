@echo off
setlocal enabledelayedexpansion

REM Resolve script directory and change working directory to it
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Default options
set "NGROK_PORT=8000"
set "NO_NGROK=0"
set "NO_FRONTEND=0"
set "NO_MCP=0"
set "NO_API=0"

:parse_args
if "%~1"=="" goto after_args
if "%~1"=="--ngrok-port" (
    set "NGROK_PORT=%~2"
    shift
    shift
    goto parse_args
)
if "%~1"=="--ngrok-domain" (
    set "NGROK_DOMAIN=%~2"
    shift
    shift
    goto parse_args
)
if "%~1"=="--no-ngrok" (
    set "NO_NGROK=1"
    shift
    goto parse_args
)
if "%~1"=="--no-frontend" (
    set "NO_FRONTEND=1"
    shift
    goto parse_args
)
if "%~1"=="--no-mcp" (
    set "NO_MCP=1"
    shift
    goto parse_args
)
if "%~1"=="--no-api" (
    set "NO_API=1"
    shift
    goto parse_args
)
REM Unknown argument, shift and continue
shift
goto parse_args

:after_args

REM Find the virtual environment python executable
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=%SCRIPT_DIR%.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
    
    REM Check if system python is available in PATH
    where python >nul 2>nul
    if errorlevel 1 (
        echo [System] Error: Python was not found in PATH or in a local .venv folder.
        echo Please install Python 3 and add it to your system environment variables.
        pause
        exit /b 1
    )
)

echo Starting Guardian Developer Environment in separate windows...

REM 1. Start Backend REST API
if !NO_API! equ 0 (
    echo [1] Launching Backend REST API on port 8001...
    start "Guardian REST API (Port 8001)" cmd /k "cd /d "%SCRIPT_DIR%ai-security-gateway" && set "AUTH_ENABLED=false" && set "PYTHONPATH=%SCRIPT_DIR%ai-security-gateway" && set "POLICY_FILE_PATH=%SCRIPT_DIR%ai-security-gateway\policy\policies.yaml" && "%PYTHON_EXE%" -m uvicorn api.app:app --host 127.0.0.1 --port 8001"
)

REM 2. Start MCP Server
if !NO_MCP! equ 0 (
    echo [2] Launching MCP Server on port 8000...
    start "Guardian MCP Server (Port 8000)" cmd /k "cd /d "%SCRIPT_DIR%ai-security-gateway" && set "AUTH_ENABLED=false" && set "PYTHONPATH=%SCRIPT_DIR%ai-security-gateway" && set "POLICY_FILE_PATH=%SCRIPT_DIR%ai-security-gateway\policy\policies.yaml" && "%PYTHON_EXE%" -m uvicorn mcp_server.app:app --host 0.0.0.0 --port 8000"
)

REM 3. Start Frontend
if !NO_FRONTEND! equ 0 (
    where npm >nul 2>nul
    if errorlevel 1 (
        echo [3] [Warning] npm was not found. Skipping Frontend dev server.
    ) else (
        echo [3] Launching Frontend dev server on port 5173...
        start "Guardian Frontend (Port 5173)" cmd /k "cd /d "%SCRIPT_DIR%frontend" && npm run dev"
    )
)

REM 4. Start Ngrok
if !NO_NGROK! equ 0 (
    where ngrok >nul 2>nul
    if errorlevel 1 (
        echo [4] [Warning] ngrok was not found in PATH. Skipping Ngrok tunnel.
    ) else (
        if defined NGROK_DOMAIN (
            echo [4] Launching Ngrok tunnel on port !NGROK_PORT! with domain !NGROK_DOMAIN!...
            start "Guardian Ngrok (Port !NGROK_PORT!)" cmd /k "ngrok http !NGROK_PORT! --domain !NGROK_DOMAIN!"
        ) else (
            echo [4] Launching Ngrok tunnel on port !NGROK_PORT!...
            start "Guardian Ngrok (Port !NGROK_PORT!)" cmd /k "ngrok http !NGROK_PORT!"
        )
    )
)

echo.
echo All requested services have been spawned!
echo You can monitor their logs in the respective Command Prompt windows.
echo.
