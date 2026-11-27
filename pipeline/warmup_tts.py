# pipeline/warmup_tts.py
from pipeline.localization import t
import json
import os
import sys
import warnings
import hashlib
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from .debug_support import install_exception_hooks, record_exception


def verify_file_integrity(file_path: Path, expected_hash: str) -> bool:
    """Computes SHA256 of local file block to ensure integrity."""
    if not file_path.exists():
        return False
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(65536), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest().lower() == expected_hash.lower()
    except Exception:
        return False

def download_asset_stream(url: str, dest_path: Path):
    """Streams binary payloads in chunks to keep memory clean."""
    import requests
    print(t("PIPELINE_NOTIFICATION_010", url=url))
    with requests.get(url, stream=True, allow_redirects=True) as r:
        r.raise_for_status()
        with open(dest_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

def _load_json_with_fallback(primary_path: Path, fallback_path: Path, label: str) -> dict:
    target = primary_path if primary_path.exists() else fallback_path
    if not target.exists():
        raise FileNotFoundError(f"{label} missing at both {primary_path} and {fallback_path}")
    with open(target, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    install_exception_hooks()
    print(t("PIPELINE_NOTIFICATION_011"))

    project_root = Path(__file__).parent.parent.absolute()
    config_dir = project_root / "config"

    env_config_path = config_dir / "environment_config.json"
    default_env_config_path = config_dir / "default_environment_config.json"

    user_config_path = config_dir / "user_customization.json"
    default_user_config_path = config_dir / "default_customization.json"

    try:
        env_data = _load_json_with_fallback(
            env_config_path, default_env_config_path, t("PIPELINE_NOTIFICATION_012")
        )
        user_data = _load_json_with_fallback(
            user_config_path, default_user_config_path, t("PIPELINE_NOTIFICATION_013")
        )
    except Exception as e:
        token = record_exception(e, "Reading setup configuration for TTS warmup")
        print(f"ERROR: Configuration load failed: {e}\nDEBUG TOKEN = {token}")
        sys.exit(1)

    tts_model_name = user_data.get("tts_model")
    tts_voice_bin_name = user_data.get("tts_voice_bin")

    paths_cfg = env_data.get("paths", {})
    temp_wav_setting = paths_cfg.get("temp_wav_dir")
    tts_base_dir_setting = paths_cfg.get("tts_base_dir", "assets/weights")
    tts_base_url = env_data.get("model_url", {}).get(
        "tts_base_url",
        "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1",
    ).rstrip("/")

    if not tts_model_name or not tts_voice_bin_name or not temp_wav_setting:
        error = ValueError("Required tts_model, tts_voice_bin, or temp_wav_dir setting is missing.")
        token = record_exception(error, "Validating TTS warmup configuration")
        print(f"ERROR: {error}\nDEBUG TOKEN = {token}")
        sys.exit(1)

    temp_wav_dir = project_root / Path(temp_wav_setting.strip('"'))
    temp_wav_dir.mkdir(parents=True, exist_ok=True)

    weights_dir = project_root / Path(tts_base_dir_setting.strip('"'))
    weights_dir.mkdir(parents=True, exist_ok=True)

    print(t("PIPELINE_NOTIFICATION_014", tts_model_name=tts_model_name, tts_voice_bin_name=tts_voice_bin_name))

    model_path = weights_dir / tts_model_name
    voices_path = weights_dir / tts_voice_bin_name

    MODEL_SHA256 = "f3a290d384fbb27966d462905c71a46cef9e5fd00516b40df32a0b4afe77ac96"
    VOICES_SHA256 = "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d"

    model_url = f"{tts_base_url}/{tts_model_name}"
    voices_url = f"{tts_base_url}/{tts_voice_bin_name}"

    try:
        from kokoro_onnx import Kokoro
        import soundfile as sf
        import onnxruntime as ort

        if not verify_file_integrity(model_path, MODEL_SHA256):
            print(t("PIPELINE_NOTIFICATION_015"))
            download_asset_stream(model_url, model_path)
            if not verify_file_integrity(model_path, MODEL_SHA256):
                raise ValueError("Downloaded model failed SHA256 signature verification loop.")

        if not verify_file_integrity(voices_path, VOICES_SHA256):
            print(t("PIPELINE_NOTIFICATION_016"))
            download_asset_stream(voices_url, voices_path)
            if not verify_file_integrity(voices_path, VOICES_SHA256):
                raise ValueError("Downloaded voice binary failed SHA256 signature verification loop.")

        print(t("PIPELINE_NOTIFICATION_017"))

        ort.set_default_logger_severity(3)

        tts_model = Kokoro(str(model_path), str(voices_path))
        base_voice = user_data.get("voice_effects", {}).get("base_voice", "am_adam")
        test_text = t("PIPELINE_NOTIFICATION_018")
        final_wav = temp_wav_dir / "warmup.wav"

        samples, sample_rate = tts_model.create(test_text, voice=base_voice, speed=1.0)
        sf.write(str(final_wav), samples, sample_rate)

        print(t("PIPELINE_NOTIFICATION_020", final_wav=final_wav))

    except Exception as e:
        token = record_exception(e, "Downloading or compiling the TTS model during setup")
        print(f"ERROR: Local TTS compilation failed: {e}\nDEBUG TOKEN = {token}")
        sys.exit(1)


if __name__ == "__main__":
    main()
