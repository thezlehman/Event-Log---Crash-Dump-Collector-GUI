@echo off
REM Event Log & Crash Dump Collector GUI launcher

echo Starting Event Log and Crash Dump Collector...
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python from https://www.python.org/downloads/
    pause
    exit /b 1
)

python "%~dp0eventlog_collector_gui.py"

if errorlevel 1 (
    echo.
    echo An error occurred. Check the output above.
    pause
)
