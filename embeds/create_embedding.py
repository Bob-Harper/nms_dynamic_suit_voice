from embeds.api import SUIT_TTS
import numpy as np
from pathlib import Path

# --- User-configurable ---
reference_wav = "embeds/reference/amused.wav"
embedding_out = "embeds/reference/amused_embedding.npy"
model_path = r"C:\Users\msutt\AppData\Local\tts\tts_models--en--ljspeech--fast_pitch\model.pth"
config_path = r"C:\Users\msutt\AppData\Local\tts\tts_models--en--ljspeech--fast_pitch\config.json"
# -------------------------

tts = SUIT_TTS(model_path=model_path, config_path=config_path, gpu=True)
saved_path = tts.save_embedding(reference_wav, embedding_out)
print(f"Saved embedding to {saved_path}")
