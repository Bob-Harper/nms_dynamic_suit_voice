@echo off
title Exosuit Companion AI Dashboard
echo ====================================================
echo   Initializing Exosuit Vocal Diagnostic Interface...
echo ====================================================
echo.

set VENV_PYTHON="%~dp0venv\Scripts\python.exe"
set MANAGER_SCRIPT="%~dp0manager\dsv_manager.py"

REM 1. Verify that the virtual environment actually exists
if not exist %VENV_PYTHON% (
    echo [ERROR]: Virtual Environment matrix missing!
    echo Please execute 'setup.cmd' first to initialize the environment modules.
    echo.
    pause
    exit /b 1
)

REM 2. Verify that the primary manager file script is present
if not exist %MANAGER_SCRIPT% (
    echo [ERROR]: Core control script not found at manager/dsv_manager.py!
    echo Please verify your file installation extraction boundaries.
    echo.
    pause
    exit /b 1
)

REM 3. Launch the dashboard cleanly using the sandboxed interpreter environment
%VENV_PYTHON% %MANAGER_SCRIPT%

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [Warning]: Dashboard pipeline closed with an unexpected exit code.
    pause
)
