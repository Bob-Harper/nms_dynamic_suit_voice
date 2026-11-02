import json
import os
import sys
from pathlib import Path

def main():
    print("Pipeline: Starting offline TTS compilation warmup...")

    # 1. Resolve project root absolute path structure
    project_root = Path(__file__).parent.parent.absolute()
    env_config_path = project_root / "config" / "environment_config.json"

    if not env_config_path.exists():
        print(f"ERROR: Cannot warm up engine. Configuration profile missing: {env_config_path}")
        sys.exit(1)

    # 2. Extract configuration fields dynamically out of the JSON profile
    try:
        with open(env_config_path, "r", encoding="utf-8") as f:
            env_data = json.load(f)
    except Exception as e:
        print(f"ERROR: environment_config.json format is corrupt: {e}")
        sys.exit(1)

    # Fetch data values cleanly out of their respective nested JSON objects
    models_cfg = env_data.get("models", {})
    tts_model_name = models_cfg.get("tts_model") # "tts_models/en/ljspeech/tacotron2-DDC_ph"

    paths_cfg = env_data.get("paths", {})
    temp_wem_setting = paths_cfg.get("temp_wem_dir") # "cache/tmp_wem_dir"

    if not tts_model_name or not temp_wem_setting:
        print("ERROR: Crucial keys ('tts_model' or 'temp_wem_dir') missing inside environment_config.json")
        sys.exit(1)

    # Ensure our workspace directory exists relative to the project root
    temp_wem_dir = project_root / Path(temp_wem_setting.strip('"'))
    temp_wem_dir.mkdir(parents=True, exist_ok=True)

    print(f"Pipeline: Verifying weights for voice signature -> {tts_model_name}")

    # 3. Locate the verified physical cache folder
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    safe_folder = tts_model_name.replace("/", "--")
    coqui_target_path = Path(local_appdata) / "tts" / safe_folder

    # 4. Fire the synthesis compilation warmup safely using structural path injection
    try:
        from TTS.api import TTS

        if coqui_target_path.exists() and (coqui_target_path / "model_file.pth").exists():
            print("Enforcing strict local path injection (Bypassing dead Coqui remote index repositories)...")
            # By passing explicit local file paths, we force Coqui to load standalone,
            # completely bypassing the broken .get() remote network loop.
            tts_model = TTS(
                model_path=str(coqui_target_path / "model_file.pth"),
                config_path=str(coqui_target_path / "config.json"),
                progress_bar=False,
                gpu=False
            )
        else:
            print("Warning: Local cache folder missing or incomplete. Attempting standard named fallback...")
            tts_model = TTS(model_name=tts_model_name, progress_bar=False)

        test_text = (
            "The required models and files for voice synthesis are now installed. "
            "If you are hearing this message, the models are downloaded and everything worked correctly."
        )
        final_wav = temp_wem_dir / "warmup.wav"
        tts_model.tts_to_file(text=test_text, file_path=str(final_wav))

        print(f"TTS warmup complete. Verification test file generated safely: {final_wav}")

    except Exception as e:
        print(f"ERROR: Local TTS compilation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
