@echo off
REM VIBE MODE - Windows Edition
REM One command to get hired

cls
echo.
echo ========================================
echo   VIBE JOB HUNTER - MAXIMUM AUTOMATION
echo ========================================
echo.
echo [1] AUTOPILOT - Auto-search jobs
echo [2] BATCH APPLY - Apply to jobs YOU find (RECOMMENDED)
echo.
set /p MODE="Choose mode (1 or 2): "
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH"
    pause
    exit /b 1
)

echo [OK] Python found

REM Check/install dependencies
if not exist ".deps_installed" (
    echo.
    echo Installing dependencies (one-time setup)...
    python -m pip install -r requirements.txt >nul 2>&1
    echo. > .deps_installed
    echo [OK] Dependencies installed
)

REM Check .env file
if not exist ".env" (
    echo.
    echo ========================================
    echo   API KEY SETUP
    echo ========================================
    echo.
    set /p API_KEY="Enter your Anthropic API key (sk-ant-...): "
    echo ANTHROPIC_API_KEY=!API_KEY! > .env
    echo [OK] API key saved
)

echo.
echo ========================================
echo   LAUNCHING AUTOPILOT...
echo ========================================
echo.
timeout /t 1 /nobreak >nul

REM Find resume
set RESUME=
for %%f in (*.pdf) do (
    echo %%f | findstr /i "resume" >nul
    if not errorlevel 1 (
        set RESUME=%%f
        goto :found_resume
    )
)

:found_resume
if "%RESUME%"=="" (
    echo [ERROR] No resume PDF found in current directory
    echo Please add your resume.pdf here and run again
    pause
    exit /b 1
)

echo [OK] Using resume: %RESUME%
echo.

REM Run autopilot
python -m src.main autopilot --resume "%RESUME%" --count 10

echo.
echo ========================================
echo   AUTOPILOT COMPLETE!
echo ========================================
echo.
echo Check stats: python -m src.main status
echo Run again tomorrow: vibe.bat
echo.
echo Your next role is coming! 🚀
echo.
pause
