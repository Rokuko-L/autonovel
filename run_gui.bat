@echo off
title Autonovel GUI Launcher
cd /d "%~dp0"
echo Starting Autonovel GUI Client...
uv run python gui.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] GUI application failed to start or exited with an error.
    pause
)
