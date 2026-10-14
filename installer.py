import subprocess
import sys
import os
import shutil
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

    if not out.startswith("Python 3.12"):
        print("ERROR: Installer must be run using Python 3.12.")
        sys.exit(1)

# -------------------------
# Step: Setup venv
# -------------------------
def setup_venv():
    venv_path = Path("venv")
    python_exe = sys.executable  # FORCE the correct interpreter

    if not venv_path.exists():
        run([python_exe, "-m", "venv", "venv"], "Create virtual environment")

    print("Virtual environment ready.")

def validate_env():
    env_path = Path("suit_voice.env")
    if not env_path.exists():
        print("ERROR: suit_voice.env missing. Installer should have created it.")
        sys.exit(1)

    # Load env file
    values = {}
    with env_path.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                values[key.strip()] = val.strip().strip('"')

    # Required keys
    required = ["MOD_DIR", "CMD_SCRIPT_PATH", "LLM_MODEL"]

    for key in required:
        if key not in values:
            print(f"ERROR: Missing required key in env: {key}")
            sys.exit(1)

    # Validate MOD_DIR
    mod_dir = Path(values["MOD_DIR"])
    if not mod_dir.exists():
        print(f"ERROR: MOD_DIR does not exist:\n{mod_dir}")
        print("Fix suit_voice.env and run installer again.")
        sys.exit(1)

    # Validate Sound2WEM CMD script
    cmd_script = Path(values["CMD_SCRIPT_PATH"])
    if not cmd_script.exists():
        print(f"ERROR: CMD_SCRIPT_PATH does not exist:\n{cmd_script}")
        print("Sound2WEM setup incomplete. Fix suit_voice.env or rerun Sound2WEM setup.")
        sys.exit(1)

    # Validate LLM model path (installer will download if missing)
    llm_model = Path(values["LLM_MODEL"])
    if not llm_model.exists():
        print(f"LLM model not found at:\n{llm_model}")
        print("Installer will attempt to download it.")
        # Do not exit — download_model() handles this

    print("Environment file validated.")

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
def download_model():
    model_url = "https://huggingface.co/lmstudio-community/Qwen3-0.6B-GGUF/resolve/main/Qwen3-0.6B-Q4_K_M.gguf"
    model_dir = Path("assets/qwen3_06b_q4")
    target_file = model_dir / "Qwen3-0.6B-Q4_K_M.gguf"

    model_dir.mkdir(parents=True, exist_ok=True)

    if target_file.exists():
        print(f"Model already exists at {target_file}, skipping.")
        return

    run(["powershell", "-File", "download_model.ps1",
         "-url", model_url,
         "-outfile", str(target_file)], "Download LLM model")

# -------------------------
# Step: Setup Sound2WEM
# -------------------------
def setup_sound2wem():
    s2w = Path("sound2wem")
    cmd = s2w / "zSound2wem.cmd"

    if s2w.exists():
        if not cmd.exists():
            print("Warning: sound2wem exists but zSound2wem.cmd is missing.")
            choice = input("Delete and re-clone? (Y/N): ").strip().lower()
            if choice == "y":
                shutil.rmtree(s2w)
                run(["git", "clone", "https://github.com/EternalLeo/sound2wem", "sound2wem"],
                    "Clone Sound2WEM")
            else:
                print("Cannot continue without zSound2wem.cmd.")
                sys.exit(1)
        else:
            print("Sound2WEM directory OK.")
    else:
        run(["git", "clone", "https://github.com/EternalLeo/sound2wem", "sound2wem"],
            "Clone Sound2WEM")

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

    temp_dir = os.getenv("TEMP") or os.getenv("TMP") or str(Path.home())
    vbs = Path(temp_dir) / "create_shortcut.vbs"

    target = Path.cwd() / "venv/Scripts/python.exe"
    args = Path.cwd() / "nms_dynamic_suite_voice_pipeline.py"
    icon = Path.cwd() / "assets/nms_dsv_256.ico"

    visible = input("Should the terminal be visible? (Y/N): ").strip().lower() == "y"

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

    step("Download LLM model", download_model)
    step("Setup Sound2WEM", setup_sound2wem)
    step("Prepare MOD directory", copy_starter_wems)
    step("Initialize TTS model", warmup_tts)
    step("Validate environment file", validate_env)
    step("Create Desktop Shortcut", create_shortcut)

    print("\n=== Setup Complete ===")
    print("• LLM model: OK")
    print("• Sound2WEM: OK")
    print("• TTS models: OK")
    print("• WEMs updated: OK")
    print("• Config: OK")
    print("• Desktop Shortcut: OK")


if __name__ == "__main__":
    main()
