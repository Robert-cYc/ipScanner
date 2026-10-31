@echo off
setlocal
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "%~dp0"
title Local Network IP Scanner

set PORT=63210

echo ========================================================
echo       Starting Local Network IP Scanner (LAN Radar)
echo ========================================================
echo.
echo Directory: %~dp0
echo Web Server: http://localhost:%PORT%
echo.

:: Terminate any stale process currently occupying the port
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":%PORT% "') do (
    echo Terminating stale process PID %%a on port %PORT%...
    taskkill /F /PID %%a >nul 2>&1
)

:: Verify if Python is accessible
where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] Python detected. Starting server.py on port %PORT%...
    start "" "http://localhost:%PORT%"
    python server.py
    goto :end
)

:: Fallback to Node.js / npx serve if Python is not found
where node >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] Node.js detected. Launching via npx serve on port %PORT%...
    start "" "http://localhost:%PORT%"
    npx -y serve . -p %PORT%
    goto :end
)

:: Fallback: Direct file open
echo [!] Neither Python nor Node.js found in PATH.
echo Launching index.html directly via file protocol...
start "" "%~dp0index.html"

:end
pause
