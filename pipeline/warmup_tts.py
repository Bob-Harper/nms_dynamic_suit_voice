# pipeline/warmup_tts.py
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

# Force Python's warnings system to ignore the deprecated pkg_resources warning
if not sys.warnoptions:
    warnings.filterwarnings("ignore", category=UserWarning, module="jieba")

def verify_file_integrity(file_path: Path, expected_hash: str) -> bool:
    """Computes SHA256 of local file block to ensure absolute integrity."""
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
    print(f"Pipeline: Streaming remote asset from: {url}")
    with requests.get(url, stream=True, allow_redirects=True) as r:
        r.raise_for_status()
        with open(dest_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

def main():
    install_exception_hooks()
    print("Pipeline: Starting offline TTS compilation warmup...")

    # 1. Resolve project root absolute path structure
    project_root = Path(__file__).parent.parent.absolute()
    env_config_path = project_root / "config" / "environment_config.json"

    if not env_config_path.exists():
        error = FileNotFoundError(f"Configuration profile missing: {env_config_path}")
        token = record_exception(error, "Checking setup configuration for TTS warmup")
        print(f"ERROR: {error}\nDEBUG TOKEN = {token}")
        sys.exit(1)

    # 2. Extract configuration fields dynamically out of the JSON profile
    try:
        with open(env_config_path, "r", encoding="utf-8") as f:
            env_data = json.load(f)
    except Exception as e:
        token = record_exception(e, "Reading setup configuration for TTS warmup")
        print(f"ERROR: environment_config.json format is corrupt: {e}\nDEBUG TOKEN = {token}")
        sys.exit(1)

    models_cfg = env_data.get("models", {})
    tts_model_name = models_cfg.get("tts_model")

    paths_cfg = env_data.get("paths", {})
    temp_wav_setting = paths_cfg.get("temp_wav_dir")

    if not tts_model_name or not temp_wav_setting:
        error = ValueError("Required tts_model or temp_wav_dir setting is missing.")
        token = record_exception(error, "Validating TTS warmup configuration")
        print(f"ERROR: {error}\nDEBUG TOKEN = {token}")
        sys.exit(1)

    # Ensure our workspace directory exists relative to the project root
    temp_wav_dir = project_root / Path(temp_wav_setting.strip('"'))
    temp_wav_dir.mkdir(parents=True, exist_ok=True)

    print(f"Pipeline: Verifying weights for voice signature -> {tts_model_name}")

    # 3. Locate or automatically acquire the physical local weight assets
    weights_dir = project_root / "assets" / "weights"
    weights_dir.mkdir(parents=True, exist_ok=True)

    model_path = weights_dir / "kokoro-v1.0.fp16.onnx"
    voices_path = weights_dir / "voices-v1.0.bin"

    # TRUE MANIFEST SPECIFICATIONS: Cryptographic targets extracted directly from the release deck
    MODEL_SHA256 = "f3a290d384fbb27966d462905c71a46cef9e5fd00516b40df32a0b4afe77ac96"
    VOICES_SHA256 = "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d"  #

    model_url = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/kokoro-v1.0.fp16.onnx"
    voices_url = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/voices-v1.0.bin"

    # 4. Fire the synthesis compilation warmup safely using the modern Kokoro engine
    try:
        from kokoro_onnx import Kokoro
        import soundfile as sf
        import onnxruntime as ort

        # 1. Verify or acquire the int8 ONNX model graph structure
        if not verify_file_integrity(model_path, MODEL_SHA256):
            print("Pipeline: Local voice model files missing or corrupt. Acquiring model graph weights automatically...")
            download_asset_stream(model_url, model_path)
            if not verify_file_integrity(model_path, MODEL_SHA256):
                raise ValueError("Downloaded model graph failed cryptographic SHA256 signature verification loop.")

        # 2. Verify or acquire the multi-language voice map array binary
        if not verify_file_integrity(voices_path, VOICES_SHA256):
            print("Pipeline: Voice library profiles missing or corrupt. Acquiring array assets automatically...")
            download_asset_stream(voices_url, voices_path)
            if not verify_file_integrity(voices_path, VOICES_SHA256):
                raise ValueError("Downloaded voice profile database failed cryptographic SHA256 signature verification loop.")

        print("Enforcing strict local path injection...")

        ort.set_default_logger_severity(3)  # 0:Verbose, 1:Info, 2:Warning, 3:Error

        tts_model = Kokoro(str(model_path), str(voices_path))
        test_text = (
            "The required models and files for voice synthesis are now installed. "
            "If you are hearing this message, the models are downloaded and everything worked correctly."
        )
        final_wav = temp_wav_dir / "warmup.wav"

        # Generate the raw audio floats array instantly out of the local ONNX model
        samples, sample_rate = tts_model.create(test_text, voice="am_adam", speed=1.0)

        # Write the audio output array straight to disk as a clean WAV asset
        sf.write(str(final_wav), samples, sample_rate)

        print(f"TTS warmup complete. Verification test file generated safely: {final_wav}")

    except Exception as e:
        token = record_exception(e, "Downloading or compiling the TTS model during setup")
        print(f"ERROR: Local TTS compilation failed: {e}\nDEBUG TOKEN = {token}")
        sys.exit(1)

if __name__ == "__main__":
    main()
