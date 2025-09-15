@echo off
setlocal enabledelayedexpansion

REM === User chooses auto vs guided ===
set "AUTOALL=N"
set "TESTMODE=N"

echo.
echo === NMS Dynamic Suit Voice Auto Setup ===
set /p AUTOALL="Do you want me to do EVERYTHING automatically? (Y/N): "
if /i "%AUTOALL%"=="Y" (
  echo Auto mode enabled.
) else (
  echo Guided mode enabled.
)

REM Optionally enable TEST mode (for devs)
if "%1"=="--test" (
  set "TESTMODE=Y"
  echo TEST MODE: Model download will be truncated to 1MB.
)

REM === Run all steps ===
call :step "Check Python" check_python
call :step "Setup virtual environment" setup_venv
call :step "Install Python dependencies" install_reqs
call :step "Download LLM model" download_model
call :step "Setup sound2wem" setup_sound2wem
call :step "Prepare .env file" copy_env
call :step "Initialize TTS model" warmup_tts

goto :done

::------------------------------------
:step
set "STEP=%~1"
set "FUNC=%~2"
echo.
echo === %STEP% ===

if /i "%AUTOALL%"=="Y" (
    call :%FUNC%
) else (
    set /p CHOICE="Run this step automatically? (Y/N): "
    if /i "!CHOICE!"=="Y" (
        call :%FUNC%
    ) else (
        echo Skipping: %STEP%
    )
)
exit /b

::------------------------------------
:check_python
python --version || (
  echo Python not found. Install 3.10+ and re-run.
  exit /b 1
)
exit /b

:setup_venv
if not exist venv python -m venv venv
call venv\Scripts\activate.bat
echo Virtual environment exists, ready for use.
exit /b

:install_reqs
echo Installing Python dependencies...

REM Ensure venv Python is used
if exist venv\Scripts\python.exe (
    set "PYTHON=venv\Scripts\python.exe"
) else (
    echo ERROR: venv not found
    exit /b 1
)

"%PYTHON%" -m pip install --upgrade pip
"%PYTHON%" -m pip install -r requirements.txt

exit /b

:download_model
echo --- Entering download_model ---
set "MODELURL=https://huggingface.co/lmstudio-community/Qwen3-0.6B-GGUF/resolve/main/Qwen3-0.6B-Q4_K_M.gguf"
set "MODELDIR=assets\qwen3_06b_q4"
REM inside setup.cmd :download_model
if not exist "%MODELDIR%" mkdir "%MODELDIR%"

REM Set target filename based on test mode
if /i "%TESTMODE%"=="Y" (
    set "TARGETFILE=%MODELDIR%\Qwen3_test.gguf"
) else (
    set "TARGETFILE=%MODELDIR%\Qwen3-0.6B-Q4_K_M.gguf"
)

REM Only download if the file doesn't already exist
if exist "%TARGETFILE%" (
    echo Model already exists at %TARGETFILE%, skipping download.
) else (
    call powershell -File download_model.ps1 -url "%MODELURL%" -outfile "%TARGETFILE%"
)
exit /b


:setup_sound2wem
echo.
echo === Setup Sound2WEM ===

:: Case 1: directory exists
if exist sound2wem (
    :: Check if the CMD file exists
    if not exist sound2wem\zSound2wem.cmd (
        echo Warning: sound2wem directory exists but zSound2wem.cmd is missing.
        set /p CHOICE="Delete existing folder and re-clone? (Y/N): "
        if /i "!CHOICE!"=="Y" (
            rmdir /s /q sound2wem
            echo Re-cloning repository...
            git clone https://github.com/EternalLeo/sound2wem sound2wem
        ) else (
            echo Cannot continue setup without CMD. Aborting.
            exit /b 1
        )
    ) else (
        echo Sound2WEM directory and CMD found. All good.
    )
) else (
    :: Case 2: folder does not exist
    echo Sound2WEM not found. Cloning repository...
    git clone https://github.com/EternalLeo/sound2wem sound2wem
)

:: At this point: folder exists and CMD exists
echo.
echo Please run Sound2WEM setup:
echo   1) Navigate to the folder: sound2wem
echo   2) Double-click zSound2wem.cmd
echo   3) Follow the on-screen instructions (install Wwise/FFmpeg)
echo   4) Come back to this window when you are done, and press the Space bar.
start "" "%CD%\sound2wem"
pause

exit /b

:copy_env
if not exist suit_voice.env copy suit_voice.env.example suit_voice.env
exit /b

:warmup_tts
:: activate virtual environment
call venv\Scripts\activate.bat

:: run warmup_tts.py
python modular\warmup_tts.py
    exit /b 0

:done
echo.
echo === Setup complete. ===
pause
exit /b
