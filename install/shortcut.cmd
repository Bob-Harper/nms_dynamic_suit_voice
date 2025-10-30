@echo off
echo Creating desktop shortcut...

:: Paths
set "DESKTOP=%USERPROFILE%\Desktop"
set "SCRIPT_DIR=%~dp0"
set "SHORTCUT_PATH=%DESKTOP%\NMS Dynamic Suit Voice.lnk"
set "TARGET_PY=%SCRIPT_DIR%nms_dynamic_suite_voice_pipeline.py"
set "PYTHON_EXE=%SCRIPT_DIR%venv\Scripts\python.exe"
set "ICON_FILE=%SCRIPT_DIR%assets\nms_dsv_256.ico"
set WINDOW_STYLE=1

:: Check icon
if not exist "%ICON_FILE%" (
    echo ERROR: Icon file not found at "%ICON_FILE%"
    pause
    exit /b
)

:: Run PowerShell script
powershell -ExecutionPolicy Bypass -File "%SCRIPT_DIR%create_shortcut.ps1" ^
    -ShortcutPath "%SHORTCUT_PATH%" ^
    -TargetPath "%PYTHON_EXE%" ^
    -Arguments "%TARGET_PY%"^
    -WorkingDir "%SCRIPT_DIR%" ^
    -IconPath "%ICON_FILE%" ^
    -WindowStyle "%WINDOW_STYLE%"

echo Shortcut created at "%SHORTCUT_PATH%"
pause
