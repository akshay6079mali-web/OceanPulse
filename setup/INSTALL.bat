@echo off
setlocal enabledelayedexpansion

:: ============================================================
::  OceanPulse — FIRST-TIME SETUP
::  Run this ONCE on a fresh machine to install everything.
::  After this, use server\START.bat to run the app.
:: ============================================================

echo.
echo  ============================================================
echo   OceanPulse — FIRST-TIME SETUP
echo  ============================================================
echo.

:: Get the directory where THIS script lives (setup\)
:: Then go one level up to get the project root
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."

:: Resolve to absolute path (handles any location on any PC)
pushd "%PROJECT_ROOT%"
set "PROJECT_ROOT=%CD%"
popd

echo  Project root: %PROJECT_ROOT%
echo.

:: -----------------------------------------------------------
:: STEP 1: Check Python
:: -----------------------------------------------------------
echo  [1/6] Checking Python installation...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  ERROR: Python is not installed or not in PATH.
    echo  Please install Python 3.10+ from https://python.org
    echo  Make sure to check "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo  Found: %PYVER%
echo.

:: -----------------------------------------------------------
:: STEP 2: Check Node.js
:: -----------------------------------------------------------
echo  [2/6] Checking Node.js installation...
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  ERROR: Node.js is not installed or not in PATH.
    echo  Please install Node.js 18+ from https://nodejs.org
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('node --version 2^>^&1') do set NODEVER=%%i
echo  Found: Node %NODEVER%
echo.

:: -----------------------------------------------------------
:: STEP 3: Create Python virtual environment
:: -----------------------------------------------------------
echo  [3/6] Creating Python virtual environment...
if exist "%PROJECT_ROOT%\venv" (
    echo  venv already exists, skipping creation.
) else (
    python -m venv "%PROJECT_ROOT%\venv"
    if %errorlevel% neq 0 (
        echo  ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo  venv created.
)
echo.

:: -----------------------------------------------------------
:: STEP 4: Install Python dependencies
:: -----------------------------------------------------------
echo  [4/6] Installing Python dependencies...
call "%PROJECT_ROOT%\venv\Scripts\activate.bat"
pip install -r "%PROJECT_ROOT%\requirements.txt" --quiet
if %errorlevel% neq 0 (
    echo  ERROR: pip install failed. Check requirements.txt
    pause
    exit /b 1
)
echo  Python dependencies installed.
echo.

:: -----------------------------------------------------------
:: STEP 5: Install frontend dependencies
:: -----------------------------------------------------------
echo  [5/6] Installing frontend dependencies...
pushd "%PROJECT_ROOT%\frontend"
call npm install --silent
if %errorlevel% neq 0 (
    echo  ERROR: npm install failed. Check frontend/package.json
    popd
    pause
    exit /b 1
)
popd
echo  Frontend dependencies installed.
echo.

:: -----------------------------------------------------------
:: STEP 6: Initialize database
:: -----------------------------------------------------------
echo  [6/6] Setting up database...
if not exist "%PROJECT_ROOT%\data" mkdir "%PROJECT_ROOT%\data"

pushd "%PROJECT_ROOT%"
set "PYTHONPATH=%PROJECT_ROOT%"
"%PROJECT_ROOT%\venv\Scripts\python.exe" scripts\setup_db.py
if %errorlevel% neq 0 (
    echo  ERROR: Database setup failed.
    popd
    pause
    exit /b 1
)

echo.
echo  Seeding historical data for DVR playback...
"%PROJECT_ROOT%\venv\Scripts\python.exe" scripts\seed_history.py
popd
echo.

echo  ============================================================
echo   SETUP COMPLETE!
echo.
echo   Default login:  admin / password123
echo.
echo   To start the app, run:
echo     server\START.bat
echo.
echo   To stop the app, run:
echo     server\STOP.bat
echo  ============================================================
echo.
pause
