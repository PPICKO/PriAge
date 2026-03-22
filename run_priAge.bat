@echo off
REM PriAge GUI Application Launcher (Windows)
REM Quick start script for Windows users

echo ========================================
echo PriAge - Age Verification System
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

echo Starting PriAge GUI...
echo.
python priAge_gui.py

pause
