@echo off
echo ============================================
echo   Dynamic Suit Voice Installer
echo ============================================
echo.

REM Try local python first
py -3.12 "%~dp0installer.py"
IF %ERRORLEVEL% EQU 0 GOTO :end

REM If python isn't in PATH, try the Windows Store python launcher
py "%~dp0installer.py"
IF %ERRORLEVEL% EQU 0 GOTO :end

echo.
echo ERROR: Python is not installed or not found.
echo Please install Python 3.10+ from https://www.python.org/downloads/
echo.
pause
exit /b

:end
echo.
echo Installer finished.
pause
