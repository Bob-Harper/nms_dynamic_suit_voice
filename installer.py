# installer.py
import subprocess
import sys
import os
import shutil
import json
from pathlib import Path
import traceback

ROOT_DIR = Path(__file__).resolve().parent
AUTOALL = False
# ==============================================================================
# VENV SELF-BOOTSTRAPPER
# If running outside the local venv, automatically restart inside the venv.
# ==============================================================================
venv_python = Path("venv/Scripts/python.exe").absolute()
# Ensure no infinite loop by checking if sys.executable points to this venv
if venv_python.exists() and Path(sys.executable).absolute() != venv_python:
    if "--download-model" not in sys.argv:  # Don't interrupt explicit sub-flags
        print("[BOOTSTRAP] Handoff execution context over to local virtual environment...")
        # Restart the script using the venv's Python binary, passing along all args
        result = subprocess.run([str(venv_python)] + sys.argv)
        sys.exit(result.returncode)
# ==============================================================================


# -------------------------
# Utility: fail-fast runner
# -------------------------
def run(cmd, desc):
    print(f"\n=== {desc} ===")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as error:
        print(f"ERROR: {desc} failed.\n{error}")
        sys.exit(1)


# -------------------------
# Prompt: auto vs guided
# -------------------------
def choose_mode():
    global AUTOALL
    print(
        "\n--- Installation Mode ---\n"
        "Auto Mode   : Installs everything and skips already-completed steps. (Recommended)\n"
        "Guided Mode : Prompts before each step so you can manually skip assets or downloads.\n"
    )
    while True:
        choice = input("Run in Auto Mode? [Y/n]: ").strip().lower()
        if choice in ("", "y", "yes"):
            AUTOALL = True
            print("Auto mode enabled.\n")
            return
        if choice in ("n", "no"):
            AUTOALL = False
            print("Guided mode enabled.\n")
            return
        print("Invalid input. Please enter Y or N.")


def step(desc, func, status_label=None):
    print(f"\n=== {desc} ===")
    if AUTOALL:
        result = func()
        ok = True if result is None else bool(result)
        if ok and status_label:
            print(f"• {status_label}: OK")
        return ok

    while True:
        choice = input("Run this step? [Y/n]: ").strip().lower()
        if choice in ("", "y", "yes"):
            result = func()
            ok = True if result is None else bool(result)
            if ok and status_label:
                print(f"• {status_label}: OK")
            return ok
        if choice in ("n", "no"):
            print(f"Skipping: {desc}")
            if status_label:
                print(f"• {status_label}: SKIPPED")
            return True
        print("Invalid input. Please enter Y or N.")

# -------------------------
# Step: Check Python
# -------------------------
def check_python():
    out = subprocess.check_output([sys.executable, "--version"], text=True).strip()
    print(out)

    if not out.startswith("Python 3.11"):
        print(f"ERROR: Installer requires Python 3.11; found {out}.")
        sys.exit(1)

# -------------------------
# Step: Check Git
# -------------------------
def check_git():
    git_exe = shutil.which("git")
    if not git_exe:
        print("ERROR: Git is not installed or was not found on your system PATH.")
        print("The installer needs Git to fetch audio converter tools and support updates.")
        print("Download Git for Windows at: https://git-scm.com")
        print("After installing Git, close this terminal, open a new one, and run installer.py again.")
        sys.exit(1)

    out = subprocess.check_output([git_exe, "--version"], text=True).strip()
    print(out)

# -------------------------
# Step: Setup venv
# -------------------------
def setup_venv():
    venv_path = ROOT_DIR / "venv"
    python_exe = sys.executable

    if not venv_path.exists():
        run([python_exe, "-m", "venv", str(venv_path)], "Create virtual environment")

    print("Virtual environment ready.")


# -------------------------
# Step: Install requirements
# -------------------------
def install_reqs():
    print("\n[MOD SETUP] >>> Entering environment sync and dependency boundary.")

    current_dir = ROOT_DIR
    python_exe = current_dir / "venv" / "Scripts" / "python.exe"
    requirements_file = current_dir / "requirements.txt"

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
        "-r", str(requirements_file)
    ], "Install dependencies")

    if sys.platform == "win32":
        postinstall_script = current_dir / "venv" / "Scripts" / "pywin32_postinstall.py"
        if postinstall_script.exists():
            subprocess.run(
                [str(python_exe), str(postinstall_script), "-install", "-silent"],
                cwd=str(current_dir),
                check=False,
            )

    print("[MOD SETUP] <<< Environment synchronized successfully.\n")


# -------------------------
# Step: Validate Configuration
# -------------------------
def validate_configuration_layer():
    config_dir = ROOT_DIR / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    user_config_path = config_dir / "user_customization.json"
    default_user_path = config_dir / "default_user_customization.json"

    env_config_path = config_dir / "environment_config.json"
    default_env_path = config_dir / "default_environment_config.json"

    if not user_config_path.exists():
        if default_user_path.exists():
            shutil.copy2(default_user_path, user_config_path)
            print("Created user_customization.json from default template.")
        else:
            with open(user_config_path, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=4)
            print("WARNING: default_customization.json missing; created empty user_customization.json.")
    else:
        print(f"user_customization.json ALREADY EXISTS ({user_config_path.stat().st_size} bytes). Leaving untouched.")

    if not env_config_path.exists():
        if default_env_path.exists():
            shutil.copy2(default_env_path, env_config_path)
            print("Created environment_config.json from default template.")
        else:
            print(f"FATAL: {default_env_path.resolve()} does not provide useable data.\nPath values from default_environment_config are required for installation.")
            print(f"ERROR: Check to see if {env_config_path} is corrupted or failed to download.")
            sys.exit(1)
    else:
        print(f"environment_config.json ALREADY EXISTS ({env_config_path.stat().st_size} bytes). Leaving untouched.")

    for cfg_path in (user_config_path, env_config_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)
        except Exception as e:
            print(f"[DEBUG][CONFIG_VAL] JSON parse exception on {cfg_path.resolve()}: {type(e).__name__}: {e}")
            print(f"ERROR: Failed to parse {cfg_path}: {e}")
            sys.exit(1)


# -------------------------
# Step: Download LLM model (In-lined, no recursive subprocess calls)
# -------------------------
def download_model():
    project_root = ROOT_DIR

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
            print("Model verified. Skipping download.")
            return
        else:
            print("Warning: Found incomplete configuration file stub. Re-downloading...")
            target_file.unlink()

    print(f"Downloading model (approx 4.4 GB) to config location: {target_file}")

    # Use the local environment's requests library inside the main process loop
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

    print("\nModel download complete.")


# -------------------------
# Step: Copy Mod Assets (Audio & Global Configs)
# -------------------------
def copy_starter_wems():
    starter = ROOT_DIR / "DYNAMIC_SUIT_VOICE"
    steam = Path("C:/Program Files (x86)/Steam/steamapps/common/No Man's Sky/GAMEDATA/MODS/DYNAMIC_SUIT_VOICE")

    if not starter.exists():
        print(f"Error: Source directory {starter} not found.")
        return False

    copied = 0
    skipped = 0

    try:
        for src_file in starter.rglob("*"):
            if not src_file.is_file():
                continue
            if src_file.name.lower() == "desktop.ini" or src_file.suffix.lower() == ".tmp":
                continue

            rel_path = src_file.relative_to(starter)
            dest_file = steam / rel_path

            if dest_file.exists():
                skipped += 1
                continue

            dest_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dest_file)
            copied += 1

        print(f"Mod folder ready ({copied} files copied, {skipped} existing files preserved).")
        return True
    except Exception as e:
        print(f"Failed to copy WEM assets (is the game currently running?): {e}")
        return False

# -------------------------
# Step: Warmup TTS
# -------------------------
def warmup_tts():
    project_root = ROOT_DIR
    python_exe = project_root / "venv" / "Scripts" / "python.exe"

    if not python_exe.exists():
        python_exe = Path(sys.executable)

    # Force the subprocess execution pass to bypass capture pipes
    print("Warmup TTS: Initializing local audio synthesis arrays...")

    subprocess.run(
        [str(python_exe), "-m", "pipeline.warmup_tts"],
        cwd=str(project_root),
        stdout=sys.stdout,
        stderr=sys.stderr,
        check=True
    )


# -------------------------
# Step: Grab GithubAction compiled decoupled wav2wem and ogg encoder
# -------------------------
def automate_audio_compiler_provisioning() -> bool:
    """
    provisions decoupled wav2wem and ogg encoder by pulling
    open-source fork repository directly into the assets directory.
    """
    # Establish root variables relative to this script's execution path
    project_root = ROOT_DIR
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

    # Safely purge any corrupted folder stubs before pulling from the repository
    if target_fork_path.exists():
        try:
            shutil.rmtree(target_fork_path)
        except Exception as e:
            print(f"[INSTALLER WARNING]: Failed to clean temporary directory stubs: {e}")

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
        print("\n[INSTALL LINK FAULT]: Git client environment not found on this workstation.")
        print("Ensure Git is installed on your OS and registered in system environment paths.")
        return False
    except subprocess.CalledProcessError as e:
        print(f"\n[INSTALL LINK FAULT]: Automated repository synchronization aborted by server.")
        print(f"Error Diagnostic Tracking Output: {e.stderr.decode('utf-8', errors='ignore')}")
        return False


# -------------------------
# Step: Create Desktop Shortcuts
# -------------------------
def create_shortcuts():
    try:
        import site
        site.main()
        import winshell
        import win32com
        from win32com.client import Dispatch
    except ImportError as e:
        print(f"WARNING: Shortcut libraries unavailable ({e}).")
        print(f"You can still launch the mod manually using: {ROOT_DIR / 'launch_nms_dsv.py'}")
        return False

    try:
        desktop = Path(winshell.desktop())
        root_dir = ROOT_DIR
        python_exe = root_dir / "venv" / "Scripts" / "pythonw.exe"
        launcher_script = root_dir / "launch_nms_dsv.py"
        icon_path = root_dir / "assets" / "nms_dsv_256.ico"

        if not python_exe.exists():
            print(f"WARNING: Virtual environment executable missing at {python_exe}")
            return False

        shortcuts_to_build = [
            {
                "name": "NMS Exosuit Companion.lnk",
                "target": str(python_exe),
                "args": f'"{launcher_script}"',
                "icon": str(icon_path) if icon_path.exists() else "",
            },
        ]

        shell = Dispatch("WScript.Shell")

        for item in shortcuts_to_build:
            shortcut_path = desktop / item["name"]
            shortcut = shell.CreateShortCut(str(shortcut_path))
            shortcut.Targetpath = item["target"]
            shortcut.Arguments = item["args"]
            shortcut.WorkingDirectory = str(root_dir)
            if item["icon"]:
                shortcut.IconLocation = item["icon"]
            shortcut.Save()

        print(f"Desktop shortcut created at: {desktop}")
        return True

    except Exception as e:
        print(f"WARNING: Could not create desktop shortcut ({type(e).__name__}: {e}).")
        print("This is often caused by Windows Controlled Folder Access or OneDrive Desktop sync.")
        print(f"Setup is still complete—you can launch the app directly via: {ROOT_DIR / 'launch_nms_dsv.py'}")
        return False


def _restart_installer_in_venv(mode):
    project_root = ROOT_DIR
    python_exe = project_root / "venv" / "Scripts" / "python.exe"
    if not python_exe.is_file():
        return None
    if Path(sys.executable).resolve() == python_exe.resolve():
        return None

    print("[BOOTSTRAP] Continuing setup inside the project virtual environment...")
    return subprocess.run(
        [
            str(python_exe),
            str(Path(__file__).resolve()),
            "--resume-after-venv",
            mode,
        ],
        cwd=project_root,
    ).returncode


# -------------------------
# Main
# -------------------------
def main():
    global AUTOALL
    resume_mode = (
        sys.argv[2]
        if len(sys.argv) == 3 and sys.argv[1] == "--resume-after-venv"
        else None
    )
    if resume_mode not in (None, "auto", "guided"):
        raise ValueError(f"Unknown installer resume mode: {resume_mode}")

    if resume_mode is None:
        print("\n=== NMS Dynamic Suit Voice Auto Setup ===")
        print(f"[INIT] System Interpreter : {sys.executable}")
        choose_mode()
        step("Check Python", check_python, "Python 3.11 check")
        step("Check Git", check_git, "Git check")
        step("Setup virtual environment", setup_venv, "venv")

        handoff_status = _restart_installer_in_venv(
            "auto" if AUTOALL else "guided"
        )
        if handoff_status is not None:
            sys.exit(handoff_status)
        print(f"[VENV] Active Interpreter : {sys.executable}")
    else:
        AUTOALL = resume_mode == "auto"
        print(f"[VENV] Active Interpreter : {sys.executable}")
        check_python()


    step("Install Python dependencies", install_reqs, "Dependencies")
    step("Validate configuration matrix", validate_configuration_layer, "JSON Config")
    step("Download LLM model", download_model, "LLM model")
    step("Prepare MOD directory", copy_starter_wems, "WEMs updated")
    step("Initialize TTS model", warmup_tts, "TTS models")
    if not step("Retrieve Encoder", automate_audio_compiler_provisioning, "Encoder Retrieval"):
        sys.exit(1)
    step("Create Desktop Shortcut", create_shortcuts, "Desktop Fast-Boot Shortcut")
    print("\n=== Setup complete. Go play! ===")


if __name__ == "__main__":
    main()
