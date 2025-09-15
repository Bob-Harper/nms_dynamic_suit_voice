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

REM STEP: Check Python
call :step "Check Python" call :check_python

REM STEP: Create venv
call :step "Setup virtual environment" call :setup_venv

REM STEP: Install requirements
call :step "Install Python dependencies" call :install_reqs

REM STEP: Download Huggy model
call :step "Download LLM model" call :download_model

REM STEP: Clone/Setup sound2wem
call :step "Setup sound2wem" call :setup_sound2wem

REM STEP: Copy env file
call :step "Prepare .env file" call :copy_env

REM STEP: Warm up TTS model
call :step "Initialize TTS model" call :warmup_tts

goto :done

::------------------------------------
:step
set "STEP=%~1"
set "CMD=%~2"
echo.
echo === %STEP% ===

if /i "%AUTOALL%"=="Y" (
  %CMD%
) else (
  set /p CHOICE="Run this step automatically? (Y/N): "
  if /i "!CHOICE!"=="Y" (
    %CMD%
  ) else (
    echo Skipping: %STEP%
  )
)
exit /b

:check_python
python --version || (
  echo Python not found. Install 3.10+ and re-run.
  exit /b 1
)
exit /b

:setup_venv
if not exist venv python -m venv venv
call venv\Scripts\activate.bat
exit /b

:install_reqs
pip install --upgrade pip
pip install -r requirements.txt
exit /b

:download_model
set "MODELURL=https://huggingface.co/lmstudio-community/Qwen3-0.6B-GGUF/resolve/main/Qwen3-0.6B-Q4_K_M.gguf"
set "MODELDIR=assets\qwen3_06b_q4"
if not exist %MODELDIR% mkdir %MODELDIR%

if "%TESTMODE%"=="Y" (
  echo Simulating model download (first 1MB only)...
  powershell -Command "Invoke-WebRequest '%MODELURL%' -OutFile '%MODELDIR%\Qwen3_test.gguf' -Headers @{Range='bytes=0-1048575'}"
) else (
  echo Downloading full model (this may take a while)...
  powershell -Command "Invoke-WebRequest '%MODELURL%' -OutFile '%MODELDIR%\Qwen3-0.6B-Q4_K_M.gguf'"
)
exit /b

:setup_sound2wem
if not exist sound2wem (
  git clone https://github.com/EternalLeo/sound2wem sound2wem
)
cd sound2wem
call zsound2wem.cmd
cd ..
exit /b

:copy_env
if not exist suit_voice.env copy suit_voice.env.example suit_voice.env
exit /b

:warmup_tts
    %VENV%\python warmup_tts.py || exit /b 1
    exit /b 0

:done
echo.
echo === Setup complete. ===
pause
exit /b
