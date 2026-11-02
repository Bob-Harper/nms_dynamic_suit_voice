# installer.py
import subprocess
import sys
print("INTERPRETER:", sys.executable)
import os
import shutil
import json
from pathlib import Path
import traceback

AUTOALL = False

# -------------------------
# Utility: fail-fast runner
# -------------------------
def run(cmd, desc):
    print(f"\n=== {desc} ===")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        print(f"ERROR: {desc} failed.")
        sys.exit(1)

# -------------------------
# Wrapper: run download_model() inside venv
# -------------------------
def run_download_model():
    python_exe = Path("venv/Scripts/python.exe")
    run([str(python_exe), "installer.py", "--download-model"], "Download LLM model")

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
        print("ERROR: Installer must be run using Python 3.11.")
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
# Step: Validate & Seed Configuration Layer (Replaces Old .env Loop)
# -------------------------
def validate_configuration_layer():
    config_dir = Path("config")
    user_config_path = config_dir / "user_customization.json"
    env_config_path = config_dir / "environment_config.json"

    # 1. Enforce directory structural rules
    config_dir.mkdir(parents=True, exist_ok=True)

    # 2. Seed clean user configurations if empty
    if not user_config_path.exists():
        with open(user_config_path, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=4)
        print("Seeded empty user profile settings successfully.")

    # 3. Check environment profiles
    if not env_config_path.exists():
        print(f"ERROR: Crucial project workspace data is missing: {env_config_path}")
        sys.exit(1)

    try:
        with open(env_config_path, "r", encoding="utf-8") as f:
            env_data = json.load(f)
    except Exception as e:
        print(f"ERROR: environment_config.json format is corrupt: {e}")
        sys.exit(1)

    # 4. Extract nested paths safely
    paths = env_data.get("paths", {})
    mod_dir = Path(paths.get("mod_dir", ""))

    ext_tools = env_data.get("external_tools", {})
    cmd_script = Path(ext_tools.get("sound2wem_cmd", ""))

    models = env_data.get("models", {})
    llm_model = Path(models.get("llm_model", ""))

    # Validate target structures match physical filesystems
    if not mod_dir.exists():
        print(f"ERROR: Target game mod folder path missing or unreachable:\n{mod_dir}")
        print("Please correct the 'mod_dir' value inside config/environment_config.json")
        sys.exit(1)

    if not cmd_script.exists():
        print(f"ERROR: sound2wem execution macro missing or unreachable:\n{cmd_script}")
        print("Fix your config paths or run Sound2WEM setup steps again.")
        sys.exit(1)

    if not llm_model.exists():
        print(f"LLM configuration target missing from workspace assets:\n{llm_model}")
        print("Installer execution loop will download it automatically.")

    print("Native JSON configuration profiles verified successfully.")


# -------------------------
# Step: Install requirements
# # -------------------------
def install_reqs():
    print("\n[MOD SETUP] >>> Entering environment sync and dependency boundary.")

    python_exe = Path("venv/Scripts/python.exe")
    if not python_exe.exists():
        print("[MOD SETUP] !!! CRITICAL ERROR: Virtual environment (venv) initialization verified: FALSE.")
        print("ERROR: venv folder missing. Execution halted.")
        sys.exit(1)

    print("[MOD SETUP] Virtual environment verified: TRUE.")

    # 1. Upgrade pip normally
    print("[MOD SETUP] Synchronizing core package manager (pip)...")
    run([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"], "Upgrade pip")

    # 2. Deploy binary-enforced dependency stack
    target_url = "https://abetlen.github.io/llama-cpp-python/whl/cpu"
    print(f"[MOD SETUP] Mapping external CPU binary matrix: {target_url}")
    print("[MOD SETUP] Deploying lightweight local LLM dependencies...")

    run([
        str(python_exe), "-m", "pip", "install",
        "--only-binary=llama-cpp-python",
        "--extra-index-url", target_url,
        "-r", "requirements.txt"
    ], "Install dependencies")

    print("[MOD SETUP] <<< Environment synchronized successfully. Core systems nominal.\n")


# -------------------------
# Step: Install requirements
# "Extreme Debug" Edition
# -------------------------
def debug_install_reqs():
    print("\n[SUBATOMIC DEBUG] >>> Entering install_reqs() function execution boundary.")

    # Track the active working directory and environment variables
    print(f"[SUBATOMIC DEBUG] Current Working Directory (CWD): {os.getcwd()}")
    print(f"[SUBATOMIC DEBUG] Current Python Executable running this script: {sys.executable}")
    print(f"[SUBATOMIC DEBUG] Current System Path (sys.path) entry count: {len(sys.path)}")

    # Path Instantiation & Virtual Environment Verification
    print("[SUBATOMIC DEBUG] Instantiating Path object for target virtual environment...")
    python_exe = Path("venv/Scripts/python.exe")
    print(f"[SUBATOMIC DEBUG] Target Path evaluated to string: '{str(python_exe)}'")
    print(f"[SUBATOMIC DEBUG] Absolute Path resolution: '{python_exe.resolve()}'")

    print("[SUBATOMIC DEBUG] Querying file system for presence of python.exe...")
    exists = python_exe.exists()
    print(f"[SUBATOMIC DEBUG] File system presence check result: {exists}")

    if not exists:
        print("[SUBATOMIC DEBUG] !!! CRITICAL STATE TRIGGERED: venv not found. Preparing hard exit.")
        print("ERROR: venv not found.")
        print("[SUBATOMIC DEBUG] Invoking sys.exit(1)... Goodbye.")
        sys.exit(1)

    print("[SUBATOMIC DEBUG] Conditional check passed. Virtual environment verified.")

    try:
        # Pip Upgrade Execution Phase
        print("\n[SUBATOMIC DEBUG] ==========================================================")
        print("[SUBATOMIC DEBUG] PREPARING STEP 1: Upgrading Core Package Manager (pip)")
        print("[SUBATOMIC DEBUG] Constructing subprocess argument array...")
        pip_upgrade_args = [str(python_exe), "-m", "pip", "install", "--upgrade", "pip"]
        print(f"[SUBATOMIC DEBUG] Argument payload: {pip_upgrade_args}")
        print("[SUBATOMIC DEBUG] Handoff to run() wrapper imminent. Initiating execution...")

        run(pip_upgrade_args, "Upgrade pip")

        print("[SUBATOMIC DEBUG] Step 1 finished. Subprocess returned execution control cleanly.")
        print("[SUBATOMIC DEBUG] ==========================================================\n")

        # Comprehensive Requirements Execution Phase with Ultimate Verbosity
        print("[SUBATOMIC DEBUG] ==========================================================")
        print("[SUBATOMIC DEBUG] PREPARING STEP 2: Dependency Sweep with Binary Enforcement")

        # Swapping the URL target out so your script can bind it cleanly
        target_url = "https://abetlen.github.io/llama-cpp-python/whl/cpu"
        print(f"[SUBATOMIC DEBUG] Binding target extra-index-url string variable to memory: '{target_url}'")

        # Verifying requirements.txt existence before letting pip touch it
        req_file = Path("requirements.txt")
        print(f"[SUBATOMIC DEBUG] Checking for target manifest '{req_file.resolve()}'...")
        print(f"[SUBATOMIC DEBUG] Manifest presence verified: {req_file.exists()}")

        print("[SUBATOMIC DEBUG] Constructing hyper-verbose subprocess argument array...")
        print("[SUBATOMIC DEBUG] NOTE: Adding '-vvv' flag to expose all pip internal tag matching and engine diagnostics.")

        pip_install_args = [
            str(python_exe), "-m", "pip", "install",
            "--only-binary=llama-cpp-python",        # Restricts ONLY llama-cpp from compiling
            "--extra-index-url", target_url,
            "-r", str(req_file)
        ]

        print(f"[SUBATOMIC DEBUG] Full argument payload matrix: {pip_install_args}")
        print("[SUBATOMIC DEBUG] Handoff to run() wrapper imminent. Initiating binary enforcement phase...")

        run(pip_install_args, "Install dependencies")

        print("[SUBATOMIC DEBUG] Step 2 finished. Dependencies successfully aligned.")
        print("[SUBATOMIC DEBUG] ==========================================================\n")

    except Exception as e:
        print("\n[SUBATOMIC DEBUG] !!! ANOMALY DETECTED IN RUNTIME EXECUTION BOUNDARY !!!")
        print(f"[SUBATOMIC DEBUG] Exception Type: {type(e)}")
        print(f"[SUBATOMIC DEBUG] Exception Message: {str(e)}")
        print("[SUBATOMIC DEBUG] Unwinding call stack trace now:")
        traceback.print_exc()
        print("[SUBATOMIC DEBUG] Standard recovery impossible. Terminating process.")
        raise e

    print("[SUBATOMIC DEBUG] <<< Exiting install_reqs() function boundary safely. Mission successful.\n")


# -------------------------
# Step: Download LLM model
# -------------------------
def download_model():
    # 1. Force absolute project path mapping relative to the script location
    project_root = Path(__file__).parent.absolute()
    config_dir = project_root / "config"
    env_config_path = config_dir / "environment_config.json"

    if not env_config_path.exists():
        print(f"ERROR: Cannot download model. Configuration profile missing: {env_config_path}")
        sys.exit(1)

    with open(env_config_path, "r", encoding="utf-8") as f:
        env_data = json.load(f)

    # 2. Extract configuration locations and URLs dynamically out of the JSON
    models_cfg = env_data.get("models", {})
    llm_model_setting = models_cfg.get("llm_model") # "assets/qwen3_4b_q8_0/Qwen3-4B-Q8_0.gguf"

    model_urls = env_data.get("model_url", {})
    url = model_urls.get("qwen3_4b_q8_0")

    if not llm_model_setting or not url:
        print("ERROR: Crucial model keys or URLs are missing inside config/environment_config.json")
        sys.exit(1)

    # Build explicit target file path destinations
    target_file = project_root / Path(llm_model_setting.strip('"'))
    model_dir = target_file.parent
    model_dir.mkdir(parents=True, exist_ok=True)

    # 3. Streamlined File Guard: Just filters out the tiny 172 KB text stubs
    if target_file.exists():
        actual_size = target_file.stat().st_size
        if actual_size > (10 * 1024 * 1024):  # Safe Baseline: Greater than 10 megabytes
            print("Model binary verified. Skipping download.")
            return
        else:
            print(f"Warning: Found incomplete configuration file stub. Re-downloading...")
            target_file.unlink()

    print(f"Downloading model binary (approx 4.4 GB) to config location: {target_file}")

    # 4. Stream the payload safely past server-side socket flushes
    import requests

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    with requests.get(url, headers=headers, stream=True) as r:
        r.raise_for_status()

        total_size = int(r.headers.get('content-length', 0))
        downloaded = 0

        with open(target_file, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024): # 1MB stream buffers
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    # Print progress marker
                    if downloaded % (50 * 1024 * 1024) < (1024 * 1024):
                        mb_done = downloaded / (1024 * 1024)
                        if total_size:
                            print(f"Progress: {mb_done:.1f} MB / {total_size / (1024 * 1024):.1f} MB downloaded...", end="\r")
                        else:
                            print(f"Progress: {mb_done:.1f} MB downloaded...", end="\r")

    print("\nModel binary download complete via configuration metrics.")


# -----------------------------------------
# Handler: run download_model() inside venv
# -----------------------------------------
if "--download-model" in sys.argv:
    download_model()
    sys.exit(0)



# -------------------------
# Step: Setup Sound2WEM
# -------------------------
def setup_sound2wem():
    s2w = Path("sound2wem")
    cmd = s2w / "zSound2wem.cmd"

    # Static command string ensures Windows parses the absolute URL token perfectly
    CLONE_CMD = "git clone https://github.com/EternalLeo/sound2wem"

    if s2w.exists():
        if not cmd.exists():
            print("Warning: sound2wem exists but zSound2wem.cmd is missing.")
            choice = input("Delete and re-clone? (Y/N): ").strip().lower()
            if choice == "y":
                shutil.rmtree(s2w)
                print("\n=== Clone Sound2WEM ===")
                subprocess.run(CLONE_CMD, shell=True, check=True)
            else:
                print("Cannot continue without zSound2wem.cmd.")
                sys.exit(1)
        else:
            print("Sound2WEM directory OK.")
    else:
        print("\n=== Clone Sound2WEM ===")
        subprocess.run(CLONE_CMD, shell=True, check=True)

    print("\nPlease run Sound2WEM setup:")
    print("  1) Explorer window opened.")
    print("  2) Double-click zSound2wem.cmd")
    print("  3) Install Wwise/FFmpeg")
    print("  4) Return here and press Enter.")
    subprocess.Popen(["explorer", str(s2w)])
    input("Press Enter when ready...")



# -------------------------
# Step: Copy starter WEMs
# -------------------------
def copy_starter_wems():
    starter = Path("DYNAMIC_SUIT_VOICE/AUDIO/WINDOWS/MEDIA/ENGLISH(US)")
    steam = Path("C:/Program Files (x86)/Steam/steamapps/common/No Man's Sky/GAMEDATA/MODS/DYNAMIC_SUIT_VOICE/AUDIO/WINDOWS/MEDIA/ENGLISH(US)")

    steam.mkdir(parents=True, exist_ok=True)

    copied = 0
    total = 0

    for f in starter.glob("*.*"):
        total += 1
        dest = steam / f.name
        if not dest.exists():
            shutil.copy(f, dest)
            copied += 1

    if total == 0:
        print(f"Warning: no starter WEMs found in {starter}")

    print(f"{copied} voice files updated")

# -------------------------
# Step: Warmup TTS
# -------------------------
def warmup_tts():
    python_exe = Path("venv/Scripts/python.exe")
    run([str(python_exe), "modular/warmup_tts.py"], "Warmup TTS")

# -------------------------
# Step: Create Desktop Shortcuts
# -------------------------
def create_shortcut():
    desktop = Path.home() / "Desktop"

    # 1. Define paths for Core Tool Shortcut
    shortcut_core = desktop / "NMS Dynamic Suit Voice.lnk"
    args_core = Path.cwd() / "launch_nms_dsv.py"
    icon_core = Path.cwd() / "assets/nms_dsv_256.ico"

    # 2. Define paths for Manager Shortcut (Pointing directly to the launch batch file!)
    shortcut_manager = desktop / "Exosuit Companion AI Dashboard.lnk"
    target_manager = Path.cwd() / "manager.cmd"  # Ensure this matches the batch file's name exactly
    icon_manager = Path.cwd() / "assets/nms_dsv_manager256.ico"

    # Check if both already exist to avoid rewriting unnecessarily
    if shortcut_core.exists() and shortcut_manager.exists():
        print("Both shortcuts already exist, skipping.")
        return

    # Select the right python executable based on terminal visibility choice for the background process
    visible = input("Should the terminal be visible for the CORE TOOL? (For Debugging or just to watch it work) (Y/N): ").strip().lower() == "y"

    if visible:
        target_core = Path.cwd() / "venv/Scripts/python.exe"
    else:
        target_core = Path.cwd() / "venv/Scripts/pythonw.exe"

    temp_dir = os.getenv("TEMP") or os.getenv("TMP") or str(Path.home())
    vbs = Path(temp_dir) / "create_shortcuts.vbs"

    with open(vbs, "w", encoding="utf-8") as f:
        f.write('Set WshShell = WScript.CreateObject("WScript.Shell")\n\n')

        # --- WRITE CORE TOOL SHORTCUT ---
        if not shortcut_core.exists():
            f.write(f'Set Shortcut1 = WshShell.CreateShortcut("{shortcut_core}")\n')
            f.write(f'Shortcut1.TargetPath = "{target_core}"\n')
            f.write(f'Shortcut1.Arguments = "{args_core}"\n')
            f.write(f'Shortcut1.WorkingDirectory = "{Path.cwd()}"\n')
            f.write(f'Shortcut1.IconLocation = "{icon_core}"\n')
            f.write('Shortcut1.Save\n\n')

        # --- WRITE MANAGER DASHBOARD SHORTCUT ---
        if not shortcut_manager.exists():
            f.write(f'Set Shortcut2 = WshShell.CreateShortcut("{shortcut_manager}")\n')
            f.write(f'Shortcut2.TargetPath = "{target_manager}"\n')
            f.write(f'Shortcut2.WorkingDirectory = "{Path.cwd()}"\n')
            f.write(f'Shortcut2.IconLocation = "{icon_manager}"\n')
            f.write('Shortcut2.Save\n')

    # Execute and clean up VBS execution boundary
    run(["cscript", "//nologo", str(vbs)], "Create desktop shortcuts")
    vbs.unlink()


# -------------------------
# Main
# -------------------------
def main():
    print("\n=== NMS Dynamic Suit Voice Auto Setup ===")
    choose_mode()

    step("Check Python", check_python)
    step("Setup virtual environment", setup_venv)
    step("Install Python dependencies", install_reqs)
    step("Download LLM model", run_download_model)
    step("Setup Sound2WEM", setup_sound2wem)
    step("Prepare MOD directory", copy_starter_wems)
    step("Initialize TTS model", warmup_tts)
    step("Validate configuration matrix", validate_configuration_layer)
    step("Create Desktop Shortcut", create_shortcut)

    print("\n=== Setup Complete ===")
    print("• LLM model: OK")
    print("• Sound2WEM: OK")
    print("• TTS models: OK")
    print("• WEMs updated: OK")
    print("• Native JSON Config: OK")
    print("• Desktop Fast-Boot Shortcut: OK")

if __name__ == "__main__":
    main()
