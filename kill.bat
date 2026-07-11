@echo off
setlocal enabledelayedexpansion

REM kill.bat - stops everything run.bat / run.py starts, so you can rerun cleanly.
REM Ports: 8001 (REST API), 8000 (MCP server), 5173 (frontend dev), 4040 (ngrok web UI).

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo Stopping Guardian dev processes...
echo.

REM 1. Close the cmd windows run.bat spawns (kills each window's whole process tree)
taskkill /F /T /FI "WINDOWTITLE eq Guardian REST API (Port 8001)" >nul 2>&1
taskkill /F /T /FI "WINDOWTITLE eq Guardian MCP Server (Port 8000)" >nul 2>&1
taskkill /F /T /FI "WINDOWTITLE eq Guardian Frontend (Port 5173)" >nul 2>&1
taskkill /F /T /FI "WINDOWTITLE eq Guardian Ngrok*" >nul 2>&1

REM 2. Fallback: kill by port, in case things were started another way (run.py, IDE, manual)
call :kill_port 8001
call :kill_port 8000
call :kill_port 5173
call :kill_port 4040

REM 3. ngrok.exe is single-purpose for this project - safe to clear out entirely
taskkill /F /IM ngrok.exe >nul 2>&1

echo.
echo Done. Re-run run.bat (or run.py) when ready.
pause
goto :eof

:kill_port
set "PORT=%~1"
set "FOUND=0"
for /f "tokens=5" %%A in ('netstat -ano ^| findstr /R /C:":%PORT% .*LISTENING"') do (
    set "FOUND=1"
    echo Killing process on port %PORT% ^(PID %%A^)...
    taskkill /F /PID %%A >nul 2>&1
)
if "!FOUND!"=="0" echo No process found listening on port %PORT%.
goto :eof
