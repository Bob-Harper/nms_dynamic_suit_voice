@echo off
echo ============================================
echo   Dynamic Suit Voice Installer
echo ============================================
echo.

REM Force the Windows Python Launcher to isolate and execute via 3.11 environment
py -3.11 "%~dp0installer.py"
IF %ERRORLEVEL% EQU 0 GOTO :end

echo.
echo ERROR: Python 3.11 runtime missing or unreachable.
echo.
echo WHY IS THIS HAPPENING?
echo This mod relies on complex machine learning, audio, and TTS dependencies
echo that use pre-compiled binaries explicitly built for Python 3.11. These
echo libraries are structurally incompatible and will fail to compile or run
echo on newer versions like Python 3.15.
echo.
echo WHAT YOU NEED TO DO:
echo You DO NOT need to uninstall your newer Python versions. Windows natively
echo supports running multiple versions side-by-side. You just need to download
echo and install Python 3.11 alongside your current setup.
echo.
echo Download Link: https://python.org
echo.
pause
exit /b

:end
echo.
echo Installer finished.
pause
