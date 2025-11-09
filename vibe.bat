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

if "%MODE%"=="1" (
    REM AUTOPILOT MODE
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
    
) else if "%MODE%"=="2" (
    REM BATCH APPLY MODE
    echo ========================================
    echo   BATCH APPLY MODE
    echo ========================================
    echo.
    echo Step 1: Find 5-10 jobs on LinkedIn/Indeed
    echo Step 2: Copy job URLs
    echo Step 3: Paste them into jobs.txt (opening now...)
    echo.
    pause
    
    REM Create template if doesn't exist
    if not exist "jobs.txt" (
        echo # Paste job URLs here (one per line)> jobs.txt
        echo # Example: https://www.linkedin.com/jobs/view/123456/>> jobs.txt
        echo https://www.linkedin.com/jobs/view/>> jobs.txt
    )
    
    REM Open notepad
    notepad jobs.txt
    
    echo.
    echo [OK] Processing jobs...
    echo.
    
    REM Check if profile exists
    if not exist "data\profile.json" (
        echo Creating profile from resume...
        
        set RESUME=
        for %%f in (*.pdf) do (
            echo %%f | findstr /i "resume" >nul
            if not errorlevel 1 (
                set RESUME=%%f
                goto :found_resume_batch
            )
        )
        
        :found_resume_batch
        if "%RESUME%"=="" (
            echo [ERROR] No resume PDF found
            pause
            exit /b 1
        )
        
        echo [OK] Using resume: %RESUME%
        python -m src.main setup --resume "%RESUME%"
    )
    
    REM Run batch apply
    python -m src.main batch --file jobs.txt
    
    echo.
    echo ========================================
    echo   BATCH APPLY COMPLETE!
    echo ========================================
    echo.
    echo Your materials are in:
    echo   - tailored_resumes\
    echo   - cover_letters\
    echo.
    echo Check stats: python -m src.main status
    echo Add more jobs: Edit jobs.txt and run again
    echo.
    echo Keep applying! 🚀
    
) else (
    echo [ERROR] Invalid choice
    pause
    exit /b 1
)

echo.
pause
