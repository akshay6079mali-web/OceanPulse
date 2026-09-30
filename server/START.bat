@echo off
setlocal enabledelayedexpansion

:: ============================================================
::  OceanPulse — START SERVER
::  Launches both backend (FastAPI) and frontend (Vite).
::  Works on any Windows PC regardless of install path.
:: ============================================================

echo.
echo  ============================================================
echo   OceanPulse — Starting Servers
echo  ============================================================
echo.

:: Get the directory where THIS script lives (server\)
:: Then go one level up to get the project root
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."

:: Resolve to absolute path
pushd "%PROJECT_ROOT%"
set "PROJECT_ROOT=%CD%"
popd

:: -----------------------------------------------------------
:: Verify setup was done
:: -----------------------------------------------------------
if not exist "%PROJECT_ROOT%\venv\Scripts\python.exe" (
    echo  ERROR: Python venv not found.
    echo  Run setup\INSTALL.bat first!
    echo.
    pause
    exit /b 1
)

if not exist "%PROJECT_ROOT%\frontend\node_modules" (
    echo  ERROR: Frontend dependencies not installed.
    echo  Run setup\INSTALL.bat first!
    echo.
    pause
    exit /b 1
)

if not exist "%PROJECT_ROOT%\data\ais_buffer.sqlite3" (
    echo  WARNING: Database not found. Creating it now...
    set "PYTHONPATH=%PROJECT_ROOT%"
    "%PROJECT_ROOT%\venv\Scripts\python.exe" "%PROJECT_ROOT%\scripts\setup_db.py"
    "%PROJECT_ROOT%\venv\Scripts\python.exe" "%PROJECT_ROOT%\scripts\seed_history.py"
    echo  Database created.
    echo.
)

:: -----------------------------------------------------------
:: Kill any existing processes on our ports
:: -----------------------------------------------------------
echo  Clearing ports 8000 and 5173...
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":8000.*LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":5173.*LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)
timeout /t 1 /nobreak >nul

:: -----------------------------------------------------------
:: Start Backend (FastAPI + Uvicorn) in a new window
:: -----------------------------------------------------------
echo  Starting API server on http://127.0.0.1:8000 ...
start "OceanPulse-Backend" cmd /k "cd /d "%PROJECT_ROOT%" && set PYTHONPATH=%PROJECT_ROOT% && "%PROJECT_ROOT%\venv\Scripts\python.exe" -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload"

:: Give backend a moment to boot
timeout /t 3 /nobreak >nul

:: -----------------------------------------------------------
:: Start Frontend (Vite) in a new window
:: -----------------------------------------------------------
echo  Starting frontend on http://localhost:5173 ...
start "OceanPulse-Frontend" cmd /k "cd /d "%PROJECT_ROOT%\frontend" && npx vite --port 5173"

:: -----------------------------------------------------------
:: Done
:: -----------------------------------------------------------
echo.
echo  ============================================================
echo   OCEANPULSE IS RUNNING!
echo.
echo   Frontend:  http://localhost:5173
echo   API:       http://127.0.0.1:8000
echo   Login:     admin / password123
echo.
echo   Two new terminal windows have been opened.
echo   Close them to stop the servers, or run server\STOP.bat
echo  ============================================================
echo.
pause
