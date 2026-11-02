"""
Installer responsibilities:
- Detect Wwise
- Install Wwise if missing
- Detect FFmpeg
- Install FFmpeg if missing
- Create project
- Save config
"""
# dsv2wem_install.py
import os
import sys
import json
import shutil
import urllib.request
import zipfile
from pathlib import Path

def setup_audio_tools():
    print("\n[AUDIO SETUP] Checking local game audio processing tools...")

    # 1. DETECT WWISE CONSOLE
    wwise_exe = None

    # Check official environment variable
    if "WWISEROOT" in os.environ:
        target = Path(os.environ["WWISEROOT"]) / "Authoring" / "x64" / "Release" / "bin" / "WwiseConsole.exe"
        if target.exists():
            wwise_exe = target

    # Fallback: Scan standard system drives if environment variable is missing
    if not wwise_exe:
        drives = ["C:", "D:", "E:", "F:"]
        for drive in drives:
            prog_files = Path(f"{drive}/Program Files (x86)")
            if prog_files.exists():
                for wwise_folder in prog_files.glob("*Wwise*"):
                    target = wwise_folder / "Authoring" / "x64" / "Release" / "bin" / "WwiseConsole.exe"
                    if target.exists():
                        wwise_exe = target
                        break
            if wwise_exe:
                break

    if wwise_exe:
        print(f"[AUDIO SETUP] Wwise Console discovered: {wwise_exe}")
    else:
        print("\n=====================================================================")
        print("CRITICAL REQUIREMENT MISSING: Wwise Authoring Engine Not Found!")
        print("=====================================================================")
        print("Due to corporate copyright limits, this tool cannot bundle Wwise.")
        print("Please install the Wwise Launcher and add the Authoring component.")
        print("URL: https://audiokinetic.com")
        print("=====================================================================")
        input("\nPress Enter to exit and rerun this setup after Wwise is installed...")
        sys.exit(1)

    # 2. DETECT OR AUTOMATICALLY INSTALL FFMPEG
    ffmpeg_exe = None

    # Check system PATH first
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        ffmpeg_exe = Path(system_ffmpeg)

    # Check if a local downloaded instance already exists from a previous run
    local_ffmpeg_dir = Path("tools/ffmpeg")
    if not ffmpeg_exe and local_ffmpeg_dir.exists():
        for target in local_ffmpeg_dir.glob("**/ffmpeg.exe"):
            if target.exists():
                ffmpeg_exe = target
                break

    if ffmpeg_exe:
        print(f"[AUDIO SETUP] FFmpeg discovered: {ffmpeg_exe}")
    else:
        print("[AUDIO SETUP] FFmpeg not found. Initiating native background deployment...")
        local_ffmpeg_dir.mkdir(parents=True, exist_ok=True)

        # Stable, reliable zipped release link
        url = "https://github.com"
        zip_target = local_ffmpeg_dir / "ffmpeg.zip"

        try:
            print("Downloading FFmpeg binaries (this may take a moment)...")
            headers = {"User-Agent": "Mozilla/5.0"}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as response, open(zip_target, "wb") as out_file:
                shutil.copyfileobj(response, out_file)

            print("Extracting archive cleanly using native zip engine...")
            with zipfile.ZipFile(zip_target, 'r') as zip_ref:
                zip_ref.extractall(local_ffmpeg_dir)

            # Clean up the downloaded temporary zip file immediately
            zip_target.unlink()

            # Locate the newly extracted executable to bind the path configuration
            for target in local_ffmpeg_dir.glob("**/ffmpeg.exe"):
                if target.exists():
                    ffmpeg_exe = target
                    break

            if ffmpeg_exe:
                print(f"[AUDIO SETUP] FFmpeg deployed successfully: {ffmpeg_exe}")
            else:
                print("ERROR: FFmpeg downloaded but the 'ffmpeg.exe' file could not be located inside the archive.")
                sys.exit(1)

        except Exception as e:
            print(f"ERROR: Native FFmpeg auto-deployment failed: {e}")
            sys.exit(1)

    # 3. WRITE DIRECTLY TO YOUR APP CONFIGURATION LAYER
    env_config_path = Path("config/environment_config.json")
    if env_config_path.exists():
        try:
            with open(env_config_path, "r", encoding="utf-8") as f:
                env_data = json.load(f)

            if "external_tools" not in env_data:
                env_data["external_tools"] = {}

            # Safe assignment: Only stringify and save if the Path objects were verified successfully
            if wwise_exe:
                env_data["external_tools"]["wwise_console"] = str(wwise_exe.resolve())
            if ffmpeg_exe:
                env_data["external_tools"]["ffmpeg_path"] = str(ffmpeg_exe.resolve())

            with open(env_config_path, "w", encoding="utf-8") as f:
                json.dump(env_data, f, indent=4)
            print("[AUDIO SETUP] System tool paths mapped to environment_config.json successfully.")
        except Exception as e:
            print(f"Warning: Configuration layer updates skipped due to formatting anomalies: {e}")
