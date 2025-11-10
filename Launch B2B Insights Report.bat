@echo off
title B2B Insights Report Generator

echo ============================================================
echo B2B Insights - Report Generator
echo ============================================================
echo.
echo Starting application...

REM Get the directory where this script is located
cd /d "%~dp0"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://python.org
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

REM Check if app.py exists in the current directory
if not exist "app.py" (
    echo ERROR: app.py not found in the same directory as this launcher
    echo Please ensure all files are in the same folder
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

REM Run the main application
python app.py

echo.
echo Application closed.
echo Press any key to exit...
pause >nul
