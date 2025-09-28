import subprocess
import os
from pathlib import Path

input_dir = Path(r"C:\NMS_SUIT_VOICE\embeds\originalvoicefiles")
output_dir = Path(r"C:\NMS_SUIT_VOICE\embeds\originalvoicefiles")
output_dir.mkdir(parents=True, exist_ok=True)

for ogg_file in input_dir.glob("*.ogg"):
    wav_file = output_dir / (ogg_file.stem + ".wav")
    cmd = [
        "ffmpeg",
        "-y",  # overwrite if exists
        "-i", str(ogg_file),
        "-ac", "1",        # mono
        "-ar", "16000",    # 16 kHz
        "-c:a", "pcm_f32le",  # float32 wav
        str(wav_file),
    ]
    subprocess.run(cmd, check=True)
    print(f"Converted {ogg_file.name} -> {wav_file.name}")
