from pathlib import Path
import subprocess
from TTS.api import TTS

test_models = [
    ("tts_models/en/ljspeech/fast_pitch", "vocoder_models/en/ljspeech/hifigan_v2")
]

test_phrase = "Peter piper picked a peck of pickled peppers. How the fuck do you pick pickled peppers when you need to pick them forst then pickle them, this rhyme makes no sense."
output_dir = Path("../test_voices")
output_dir.mkdir(exist_ok=True)

for model_name, vocoder_name in test_models:
    print(f"Testing model: {model_name} + {vocoder_name}")
    tts_model = TTS(model_name=model_name, vocoder_name=vocoder_name)

    wav_file = output_dir / f"{model_name.replace('/', '_')}.wav"
    temp_wav = wav_file.with_suffix(".temp.wav")

    tts_model.tts_to_file(text=test_phrase, file_path=str(wav_file))

    subprocess.run([
        "ffmpeg", "-hide_banner", "-y",
        "-i", str(wav_file),
        "-af", "volume=5.0dB",
        str(temp_wav)
    ], check=True)

    temp_wav.replace(wav_file)

    print(f"Saved sample for {model_name} -> {wav_file}")

print("Done. Check the test_voices directory.")
