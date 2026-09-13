@echo off
title JARVIS LinkedIn AI Agent
color 0B
echo ========================================================
echo       JARVIS COMMIT-TO-LINKEDIN AUTONOMOUS AGENT
echo ========================================================
echo.
echo Select an option:
echo   [1] Generate & Preview Post (Dry Run)
echo   [2] Generate & Interactive Post (Review before posting)
echo   [3] Instant Auto-Post Latest Commit
echo   [4] Install Git Post-Commit Hook to a Repo
echo.
set /p opt="Enter choice [1-4]: "

if "%opt%"=="1" (
    python "%~dp0tools\linkedin_agent.py" --dry-run
) else if "%opt%"=="2" (
    python "%~dp0tools\linkedin_agent.py"
) else if "%opt%"=="3" (
    python "%~dp0tools\linkedin_agent.py" --auto
) else if "%opt%"=="4" (
    set /p repopath="Enter repository full path (or press Enter for current): "
    if "%repopath%"=="" (
        python "%~dp0tools\install_git_hook.py" --mode auto
    ) else (
        python "%~dp0tools\install_git_hook.py" --repo "%repopath%" --mode auto
    )
) else (
    echo Invalid choice.
)

echo.
pause
