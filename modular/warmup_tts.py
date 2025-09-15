# warmup_tts.py
from modular.config import SuitVoiceConfig
from modular.tts_utils import run_tts

def main():
    config = SuitVoiceConfig()
    wem_num = "warmup"
    test_text = (
        "The required models and files for voice synthesis are now installed. "
        "If you are hearing this message, everything worked correctly."
    )
    wav_path = run_tts(config, test_text, wem_num, postprocess=False)
    print(f"TTS warmup complete. Test file generated: {wav_path}")

if __name__ == "__main__":
    main()
