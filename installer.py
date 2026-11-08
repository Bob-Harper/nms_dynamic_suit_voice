# installer.py
import subprocess
import sys
print("INTERPRETER:", sys.executable)
import os
import shutil
import json
from pathlib import Path
import traceback
from pipeline.debug_support import (
    debug_error_message,
    install_exception_hooks,
    record_exception,
)

install_exception_hooks()

# ==============================================================================
# VENV SELF-BOOTSTRAPPER
# If running outside the local venv, automatically restart inside the venv.
# ==============================================================================
venv_python = Path("venv/Scripts/python.exe").absolute()
# Ensure we don't loop endlessly by checking if sys.executable points to our venv
if venv_python.exists() and Path(sys.executable).absolute() != venv_python:
    if "--download-model" not in sys.argv:  # Don't interrupt explicit sub-flags
        print("[BOOTSTRAP] Handoff execution context over to local virtual environment...")
        # Restart the script using the venv's Python binary, passing along all args
        result = subprocess.run([str(venv_python)] + sys.argv)
        sys.exit(result.returncode)
# ==============================================================================

print("INTERPRETER:", sys.executable)
AUTOALL = False

AUTOALL = False

# -------------------------
# Utility: fail-fast runner
# -------------------------
def run(cmd, desc):
    print(f"\n=== {desc} ===")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as error:
        message = debug_error_message(error, f"Installer step: {desc}")
        print(f"ERROR: {desc} failed.\n{message}")
        sys.exit(1)

# -------------------------
# Prompt: auto vs guided
# -------------------------
def choose_mode():
    global AUTOALL
    choice = input("Do you want EVERYTHING automatically? (Y/N): ").strip().lower()
    AUTOALL = (choice == "y")
    print("Auto mode enabled." if AUTOALL else "Guided mode enabled.")

def step(desc, func):
    print(f"\n=== {desc} ===")
    if AUTOALL:
        func()
    else:
        choice = input("Run this step automatically? (Y/N): ").strip().lower()
        if choice == "y":
            func()
        else:
            print(f"Skipping: {desc}")

# -------------------------
# Step: Check Python
# -------------------------
def check_python():
    out = subprocess.check_output([sys.executable, "--version"], text=True).strip()
    print(out)

    if not out.startswith("Python 3.11"):
        error = RuntimeError(f"Installer requires Python 3.11; found {out}.")
        token = record_exception(error, "Checking the installer Python version")
        print(f"ERROR: {error}\nDEBUG TOKEN = {token}")
        sys.exit(1)

# -------------------------
# Step: Setup venv
# -------------------------
def setup_venv():
    venv_path = Path("venv")
    python_exe = sys.executable

    if not venv_path.exists():
        run([python_exe, "-m", "venv", "venv"], "Create virtual environment")

    print("Virtual environment ready.")

# -------------------------
# Step: Validate Configuration
# -------------------------
def validate_configuration_layer():
    config_dir = Path("config")
    user_config_path = config_dir / "user_customization.json"
    env_config_path = config_dir / "environment_config.json"

    config_dir.mkdir(parents=True, exist_ok=True)

    if not user_config_path.exists():
        with open(user_config_path, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=4)
        print("Seeded empty user profile settings successfully.")

    if not env_config_path.exists():
        error = FileNotFoundError(
            f"Crucial project workspace data is missing: {env_config_path}"
        )
        token = record_exception(error, "Validating installer configuration files")
        print(f"ERROR: {error}\nDEBUG TOKEN = {token}")
        sys.exit(1)

    try:
        with open(env_config_path, "r", encoding="utf-8") as f:
            env_data = json.load(f)
    except Exception as e:
        message = debug_error_message(e, "Reading installer configuration")
        print(f"ERROR: environment_config.json format is corrupt: {message}")
        sys.exit(1)

    paths = env_data.get("paths", {})
    mod_dir = Path(paths.get("mod_dir", ""))

    models = env_data.get("models", {})
    llm_model = Path(models.get("llm_model", ""))

    if not mod_dir.exists():
        error = FileNotFoundError(
            f"Target game mod folder path missing or unreachable: {mod_dir}"
        )
        token = record_exception(error, "Validating the configured game mod folder")
        print(f"ERROR: {error}\nDEBUG TOKEN = {token}")
        print("Please correct the 'mod_dir' value inside config/environment_config.json")
        sys.exit(1)

    if not llm_model.exists():
        print("LLM configuration target missing from workspace assets. Ready to download.")

    print("Native JSON configuration profiles verified successfully.")

# -------------------------
# Step: Install requirements
# -------------------------
def install_reqs():
    print("\n[MOD SETUP] >>> Entering environment sync and dependency boundary.")

    python_exe = Path("venv/Scripts/python.exe")
    if not python_exe.exists():
        print("[MOD SETUP] !!! CRITICAL ERROR: Virtual environment initialization failed.")
        sys.exit(1)

    print("[MOD SETUP] Upgrading core package manager (pip)...")
    run([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"], "Upgrade pip")

    # Install utilities used to create Windows desktop shortcuts.
    print("[MOD SETUP] Fetching specialized local environment tools...")
    run([str(python_exe), "-m", "pip", "install", "winshell", "comtypes"], "Install shortcut utilities")

    target_url = "https://abetlen.github.io/llama-cpp-python/whl/cpu"
    print("[MOD SETUP] Deploying lightweight local LLM dependencies...")

    run([
        str(python_exe), "-m", "pip", "install",
        "--only-binary=llama-cpp-python",
        "--extra-index-url", target_url,
        "-r", "requirements.txt"
    ], "Install dependencies")

    print("[MOD SETUP] <<< Environment synchronized successfully.\n")

# -------------------------
# Step: Download LLM model (In-lined, no recursive subprocess calls)
# -------------------------
def download_model():
    project_root = Path(__file__).parent.absolute()
    config_dir = project_root / "config"
    env_config_path = config_dir / "environment_config.json"

    if not env_config_path.exists():
        print(f"ERROR: Cannot download model. Configuration profile missing: {env_config_path}")
        sys.exit(1)

    with open(env_config_path, "r", encoding="utf-8") as f:
        env_data = json.load(f)

    models_cfg = env_data.get("models", {})
    llm_model_setting = models_cfg.get("llm_model")

    model_urls = env_data.get("model_url", {})
    url = model_urls.get("qwen3_4b_q8_0")

    if not llm_model_setting or not url:
        print("ERROR: Crucial model keys or URLs are missing inside config/environment_config.json")
        sys.exit(1)

    target_file = project_root / Path(llm_model_setting.strip('"'))
    model_dir = target_file.parent
    model_dir.mkdir(parents=True, exist_ok=True)

    if target_file.exists():
        actual_size = target_file.stat().st_size
        if actual_size > (10 * 1024 * 1024):
            print("Model binary verified. Skipping download.")
            return
        else:
            print("Warning: Found incomplete configuration file stub. Re-downloading...")
            target_file.unlink()

    print(f"Downloading model binary (approx 4.4 GB) to config location: {target_file}")

    # Use the local environment's requests library cleanly inside the main process loop
    import requests
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    with requests.get(url, headers=headers, stream=True) as r:
        r.raise_for_status()
        total_size = int(r.headers.get('content-length', 0))
        downloaded = 0

        with open(target_file, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if downloaded % (50 * 1024 * 1024) < (1024 * 1024):
                        mb_done = downloaded / (1024 * 1024)
                        if total_size:
                            print(f"Progress: {mb_done:.1f} MB / {total_size / (1024 * 1024):.1f} MB downloaded...", end="\r")
                        else:
                            print(f"Progress: {mb_done:.1f} MB downloaded...", end="\r")

    print("\nModel binary download complete via configuration metrics.")

# -------------------------
# Step: Copy Mod Assets (Audio & Global Configs)
# -------------------------
def copy_starter_wems(): # also copies GCDEBUGOPTIONS.GLOBAL.EXML to ensure hotswap is enabled
    starter = Path("DYNAMIC_SUIT_VOICE/")
    steam = Path("C:/Program Files (x86)/Steam/steamapps/common/No Man's Sky/GAMEDATA/MODS/DYNAMIC_SUIT_VOICE/")

    if not starter.exists():
        print(f"Error: Source directory {starter} not found.")
        return

    # copytree with dirs_exist_ok=True cleanly merges/updates the entire tree
    try:
        shutil.copytree(starter, steam, dirs_exist_ok=True, ignore=shutil.ignore_patterns('desktop.ini', '*.tmp'))
        print("Mod folder assets and global configurations updated successfully.")
    except Exception as e:
        message = debug_error_message(e, "Copying starter mod assets")
        print(f"Failed to copy assets: {message}")

# -------------------------
# Step: Warmup TTS
# -------------------------
def warmup_tts():
    project_root = Path(__file__).parent.absolute()
    python_exe = project_root / "venv" / "Scripts" / "python.exe"

    if not python_exe.exists():
        python_exe = Path(sys.executable)

    run([str(python_exe), "pipeline/warmup_tts.py"], "Warmup TTS")


# -------------------------
# Step: Grab GithubAction compiled decoupled wav2wem and ogg encoder
# -------------------------

def automate_audio_compiler_provisioning() -> bool:
    """
    provisions decoupled wav2wem and ogg encoder by pulling
    open-source fork repository directly into the assets directory.
    """
    # Establish root variables relative to this script's execution path
    project_root = Path(__file__).parent.absolute()
    assets_dir = project_root / "assets"
    target_fork_path = assets_dir / "wav2wem"

    # Define the nested execution paths matching the forked asset structure
    expected_exe = target_fork_path / "assets" / "wav2wem.exe"

    # Verification Guard: If the fresh tools are already active locally, skip entirely
    if expected_exe.exists():
        print("[INSTALLER]: Audio compiler tools verified locally. Skipping.")
        return True

    print("\n")
    print("[INSTALLER]: PROVISIONING AUDIO UTILITIES")
    print(f"Pulling components to Target Destination: {target_fork_path}")
    print("\n")

    # Safely purge any corrupted folder stubs before pulling into the repository
    if target_fork_path.exists():
        try:
            shutil.rmtree(target_fork_path)
        except Exception as e:
            message = debug_error_message(e, "Cleaning an incomplete converter download")
            print(f"[INSTALLER WARNING]: Failed to clean temporary directory stubs: {message}")

    assets_dir.mkdir(parents=True, exist_ok=True)

    try:
        # This grabs the latest commit snapshot
        repo_url = "https://github.com/Bob-Harper/wav2wem.git"

        subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, str(target_fork_path)],
            check=True,
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW  # Prevents cmd console windows from flashing
        )

        # 3. Post-Clone Validation Check: Ensure the binaries actually materialized on disk
        if expected_exe.exists():
            print("\n[INSTALLER SUCCESS]: Audio processing tools successfully synchronized!")
            print(f"-> Verified: {expected_exe.name}")
            print(f"-> Verified: {expected_exe.parent / 'oggenc2.exe'}")
            print(f"-> Verified: {expected_exe.parent / 'libFLAC.dll'}")
            return True
        else:
            print("\n[INSTALLER CRITICAL]: Repository sync completed, but binaries were missing from the branch path.")
            return False

    except FileNotFoundError as error:
        message = debug_error_message(error, "Locating Git while downloading the converter")
        print("\n[INSTALL LINK FAULT]: Git client environment not found on this workstation.")
        print("Ensure Git is installed natively on your OS and registered in system environment paths.")
        print(message)
        return False
    except subprocess.CalledProcessError as e:
        message = debug_error_message(e, "Downloading the WEM converter repository")
        print(f"\n[INSTALL LINK FAULT]: Automated repository synchronization aborted by server.")
        print(f"Error Diagnostic Tracking Output: {e.stderr.decode('utf-8', errors='ignore')}")
        print(message)
        return False

# -------------------------
# Step: Create Desktop Shortcuts (Pure Python via winshell - NO VBSCRIPT!)
# -------------------------
def create_shortcuts():
    import winshell
    import win32com
    from win32com.client import Dispatch

    desktop = Path(winshell.desktop())
    root_dir = Path.cwd().absolute()

    # CHANGE THIS LINE: Use pythonw.exe for windowless apps!
    python_exe = root_dir / "venv/Scripts/pythonw.exe"

    shortcuts_to_build = [
        {
            "name": "NMS Dynamic Suit Voice.lnk",
            "target": str(python_exe),
            "args": f'"{root_dir / "launch_nms_dsv.py"}"',
            "icon": str(root_dir / "assets/nms_dsv_256.ico")
        },
        {
            "name": "Exosuit Companion.lnk",
            "target": str(python_exe),
            "args": f'"{root_dir / "launch_nms_dsv.py"}"',
            "icon": str(root_dir / "assets/nms_dsv_manager_256.ico")
        }
    ]
    shell = Dispatch('WScript.Shell')

    for item in shortcuts_to_build:
        shortcut_path = os.path.join(desktop, item["name"])
        shortcut = shell.CreateShortCut(shortcut_path)

        # Launch the application directly through the virtual-environment Python.
        shortcut.Targetpath = item["target"]
        shortcut.Arguments = item["args"]
        shortcut.WorkingDirectory = str(root_dir)
        shortcut.IconLocation = item["icon"]
        shortcut.Save()

    print("Desktop Shortcuts created successfully via pure memory allocations.")

# -------------------------
# Main
# -------------------------
def main():
    print("\n=== NMS Dynamic Suit Voice Auto Setup ===")
    choose_mode()

    step("Check Python", check_python)
    print("• Python 3.11 check: OK")

    step("Setup virtual environment", setup_venv)
    print("• venv: OK")

    step("Install Python dependencies", install_reqs)
    print("• Dependencies: OK")

    # Download the model directly in the installer process.
    step("Download LLM model", download_model)
    print("• LLM model: OK")
    step("Prepare MOD directory", copy_starter_wems)
    print("• WEMs updated: OK")
    step("Initialize TTS model", warmup_tts)
    print("• TTS models: OK")
    step("Validate configuration matrix", validate_configuration_layer)
    print("• Native JSON Config: OK")
    step("Retrieve Encoder", automate_audio_compiler_provisioning)
    print("• Encoder Retrieval: OK")
    step("Create Desktop Shortcut", create_shortcuts)
    print("• Desktop Fast-Boot Shortcut: OK")
    print("\n=== Setup complete. Go play! ===")

if __name__ == "__main__":
    main()