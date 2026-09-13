@echo off
title JARVIS Autonomous Placement Hunter
color 0A
echo ================================================================
echo       JARVIS DUAL-ENGINE AUTONOMOUS JOB APPLIER (LINKEDIN)
echo ================================================================
echo.
echo [1] One-Time Setup: Export LinkedIn Session for Cloud Server
echo [2] Run Safe Dry-Run (Search, Auto-Fill, Snap Proof, Telegram Alert)
echo [3] Run Full Auto-Pilot Mode (Submit & Send Telegram Proof)
echo [4] Run Local PC Bridge Runner (Direct Residential IP)
echo.
set /p choice="Enter choice [1-4]: "

if "%choice%"=="1" (
    python "%~dp0tools\export_linkedin_session.py"
) else if "%choice%"=="2" (
    python "%~dp0tools\autonomous_job_applier.py" --mode dry-run
) else if "%choice%"=="3" (
    python "%~dp0tools\autonomous_job_applier.py" --mode auto
) else if "%choice%"=="4" (
    python "%~dp0tools\autonomous_job_applier.py" --runner secondary --mode dry-run
) else (
    echo Invalid choice.
)

echo.
pause
