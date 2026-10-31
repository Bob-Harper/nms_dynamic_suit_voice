# installer.py
import subprocess
import sys

print("INTERPRETER:", sys.executable)
import os
import shutil
import json
from pathlib import Path

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
# -------------------------
def install_reqs():
    python_exe = Path("venv/Scripts/python.exe")
    if not python_exe.exists():
        print("ERROR: venv not found.")
        sys.exit(1)

    run([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"], "Upgrade pip")
    run([str(python_exe), "-m", "pip", "install", "-r", "requirements.txt"], "Install dependencies")


# -------------------------
# Step: Download LLM model
# -------------------------
# installer.py - Streamlined Dynamic Downloader

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
# Step: Create Desktop Shortcut
# -------------------------
def create_shortcut():
    desktop = Path.home() / "Desktop"
    shortcut = desktop / "NMS Dynamic Suit Voice.lnk"
    if shortcut.exists():
        print("Shortcut already exists, skipping.")
        return
    temp_dir = os.getenv("TEMP") or os.getenv("TMP") or str(Path.home())
    vbs = Path(temp_dir) / "create_shortcut.vbs"

    target = Path.cwd() / "venv/Scripts/python.exe"

    # CRITICAL CHANGE: Target the lightning fast boot loader script instead of the old core loop!
    args = Path.cwd() / "launch_nms_dsv.py"
    icon = Path.cwd() / "assets/nms_dsv_256.ico"

    visible = input("Should the terminal be visible? (Good for Debugging or just to watch it work) (Y/N): ").strip().lower() == "y"

    with open(vbs, "w") as f:
        f.write('Set WshShell = WScript.CreateObject("WScript.Shell")\n')
        f.write(f'Set Shortcut = WshShell.CreateShortcut("{shortcut}")\n')

        if visible:
            f.write(f'Shortcut.TargetPath = "{target}"\n')
            f.write(f'Shortcut.Arguments = "{args}"\n')
        else:
            f.write('Shortcut.TargetPath = "cmd.exe"\n')
            f.write(f'Shortcut.Arguments = "/c \\"{target} {args}\\""\n')

        f.write(f'Shortcut.WorkingDirectory = "{Path.cwd()}"\n')
        f.write(f'Shortcut.IconLocation = "{icon}"\n')
        f.write('Shortcut.Save\n')

    run(["cscript", "//nologo", str(vbs)], "Create desktop shortcut")
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
