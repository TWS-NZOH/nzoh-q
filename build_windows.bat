@echo off
REM Windows Build Script for Quantitative Sales
REM This script should be run on a Windows machine

echo ======================================================================
echo Quantitative Sales - Windows Executable Builder
echo ======================================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or later
    pause
    exit /b 1
)

REM Install PyInstaller if needed
python -m pip install pyinstaller --quiet

REM Run the build
python scripts\build_executable.py

if errorlevel 1 (
    echo.
    echo Build failed!
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo Build complete! Check the dist folder for Quantitative Sales.exe
echo ======================================================================
pause
