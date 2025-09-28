from TTS.api import TTS
import time
import subprocess
import sys
from pathlib import Path

CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

# User-configurable values
gain_db = 5
atempo = 1.0
rate = 0.5
asetrate = int(44100 * rate)
# pauses in speech are difficult to control but this DOES work for a long pause:   .. .
# Never use 3 dotsin a row or it will truncate to end of sentence or line, whichever comes first.  \n has no effect.

text = (
    "If you are in a location where hostile Sentinels patrol, be prepared for potential trouble."
)

base_dir = Path("embeds")
base_dir.mkdir(exist_ok=True)
temp_wav_path = base_dir / "xx_temp.wav"
final_wav_path = base_dir / "xx_test_tts_output.wav"
speaker_wav = [r"C:\NMS_SUIT_VOICE\embeds\reference\amused.wav",
               r"C:\NMS_SUIT_VOICE\embeds\reference\base_extended.wav",
               r"C:\NMS_SUIT_VOICE\embeds\reference\concerned.wav",
               r"C:\NMS_SUIT_VOICE\embeds\reference\emphasis.wav",
               r"C:\NMS_SUIT_VOICE\embeds\reference\standard.wav",
               r"C:\NMS_SUIT_VOICE\embeds\reference\trimmed_emphasis.wav",
               r"C:\NMS_SUIT_VOICE\embeds\reference\whatever.wav",
               ]
# Initialize TTS
tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2")
tts.to("cpu")

# Generate WAV
start1 = time.time()
tts.tts_to_file(text=text, file_path=str(temp_wav_path), speaker_wav=speaker_wav, language="en")
end1 = time.time()
print(f"TTS generation took {end1 - start1:.2f} seconds")

# Optional FFmpeg postprocessing
start2 = time.time()
subprocess.run([
    "ffmpeg", "-hide_banner", "-y",
    "-i", str(temp_wav_path),
    "-af", f"volume={gain_db}dB,atempo={atempo},asetrate={asetrate}",
    str(final_wav_path)
], check=True, creationflags=CREATE_NO_WINDOW)
end2 = time.time()
print(f"FFmpeg postprocessing took {end2 - start2:.2f} seconds")
print(f"Total generation took {end2 - start1:.2f} seconds")
