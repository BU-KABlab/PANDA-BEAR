@echo off
REM Standalone Slack Bot Runner for PANDA SDL
REM This script runs the PANDA Slack bot as a standalone process

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\..\.."

REM Change to project root
cd /d "%PROJECT_ROOT%"

REM Try to activate virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else if exist "%USERPROFILE%\anaconda3\Scripts\activate.bat" (
    REM Fallback to conda if available
    call "%USERPROFILE%\anaconda3\Scripts\activate.bat"
    call activate python310 2>nul || call activate python311 2>nul
)

REM Run the standalone Slack bot script
python scripts\panda-slack-bot.py %*

pause