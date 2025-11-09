@echo off
echo.
echo ========================================
echo   VIBE JOB HUNTER - AUTOPILOT MODE
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    pause
    exit /b 1
)
echo [OK] Python found

REM Install dependencies
if not exist ".deps_installed" (
    echo.
    echo Installing dependencies...
    python -m pip install -r requirements.txt
    type nul > .deps_installed
    echo [OK] Dependencies installed
)

REM Check .env file
if not exist ".env" (
    echo.
    echo ========================================
    echo   API KEY SETUP
    echo ========================================
    echo.
    set /p APIKEY="Enter your Anthropic API key: "
    echo ANTHROPIC_API_KEY=%APIKEY% > .env
    echo [OK] API key saved
)

echo.
echo ========================================
echo   LAUNCHING AUTOPILOT...
echo ========================================
echo.

REM Run autopilot with the resume file
python -m src.main autopilot --resume "../Elena Revicheva 03.11.2025 Resume.pdf" --count 10

echo.
echo ========================================
echo   AUTOPILOT COMPLETE!
echo ========================================
echo.
pause
