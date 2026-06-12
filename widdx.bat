@echo off
REM WIDDX — Terminal AI Chat Tool
REM Auto-detects Python (tries Python launcher, then python, then python3)

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    py "%~dp0main.py" %*
    exit /b %ERRORLEVEL%
)

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python "%~dp0main.py" %*
    exit /b %ERRORLEVEL%
)

where python3 >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python3 "%~dp0main.py" %*
    exit /b %ERRORLEVEL%
)

echo Error: Python not found. Install Python 3.10+ from python.org
pause
