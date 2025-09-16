# warmup_tts.py
from config import SuitVoiceConfig
from tts_utils import test_tts

def main():
    config = SuitVoiceConfig()
    wem_num = "warmup"
    test_text = (
        "The required models and files for voice synthesis are now installed. "
        "If you are hearing this message, everything worked correctly."
    )
    wav_path = test_tts(config, test_text, wem_num)
    print(f"TTS warmup complete. Test file generated: {wav_path}")

if __name__ == "__main__":
    main()
