@echo off
:: ============================================================
::  OceanPulse — STOP ALL SERVERS
::  Kills backend (uvicorn) and frontend (node/vite) processes.
:: ============================================================

echo.
echo  Stopping OceanPulse servers...
echo.

:: Kill by window title
taskkill /FI "WINDOWTITLE eq OceanPulse-Backend*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq OceanPulse-Frontend*" /F >nul 2>&1

:: Also kill by port as a fallback
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":8000.*LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":5173.*LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)

echo  All OceanPulse servers stopped.
echo.
pause
