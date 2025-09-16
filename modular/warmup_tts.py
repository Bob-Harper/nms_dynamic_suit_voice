# warmup_tts.py
import os
from pathlib import Path
from dotenv import load_dotenv
from TTS.api import TTS

def main():
    # Load only what we need
    env_path = Path(__file__).parent.parent / "suit_voice.env"
    load_dotenv(env_path)

    tts_model_name = os.getenv("TTS_MODEL")
    temp_wem_dir = Path(os.getenv("TEMP_WEM_DIR").strip('"'))
    temp_wem_dir.mkdir(parents=True, exist_ok=True)

    tts_model = TTS(model_name=tts_model_name)

    wem_num = "warmup"
    test_text = (
        "The required models and files for voice synthesis are now installed. "
        "If you are hearing this message, everything worked correctly."
    )
    final_wav = temp_wem_dir / f"{wem_num}.wav"
    tts_model.tts_to_file(text=test_text, file_path=str(final_wav))

    print(f"TTS warmup complete. Test file generated: {final_wav}")

if __name__ == "__main__":
    main()
