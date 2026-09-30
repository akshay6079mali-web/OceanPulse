@echo off
setlocal enabledelayedexpansion

:: ============================================================
::  OceanPulse — RESET DATABASE
::  Wipes and recreates the database + seeds fresh history data.
::  Use this if login stops working or data looks corrupted.
:: ============================================================

echo.
echo  ============================================================
echo   OceanPulse — DATABASE RESET
echo  ============================================================
echo.

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
pushd "%PROJECT_ROOT%"
set "PROJECT_ROOT=%CD%"
popd

:: Delete old database
if exist "%PROJECT_ROOT%\data\ais_buffer.sqlite3" (
    echo  Removing old database...
    del /f /q "%PROJECT_ROOT%\data\ais_buffer.sqlite3"
)

:: Recreate
echo  Creating fresh database...
set "PYTHONPATH=%PROJECT_ROOT%"
"%PROJECT_ROOT%\venv\Scripts\python.exe" "%PROJECT_ROOT%\scripts\setup_db.py"

echo  Seeding 24h historical data...
"%PROJECT_ROOT%\venv\Scripts\python.exe" "%PROJECT_ROOT%\scripts\seed_history.py"

echo.
echo  Done! Database reset complete.
echo  Default login:  admin / password123
echo.
pause
