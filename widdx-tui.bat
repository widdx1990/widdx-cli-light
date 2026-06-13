@echo off
REM WIDDX Cortex — Terminal AI Assistant (TUI Mode)
REM تشغيل الواجهة المحسنة — Run enhanced TUI interface
REM Usage: widdx-tui  or  widdx-tui C:\project

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    py "%~dp0run_textual.py" %*
    exit /b %ERRORLEVEL%
)

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python "%~dp0run_textual.py" %*
    exit /b %ERRORLEVEL%
)

where python3 >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python3 "%~dp0run_textual.py" %*
    exit /b %ERRORLEVEL%
)

echo Error: Python not found. Install Python 3.10+ from python.org
pause
