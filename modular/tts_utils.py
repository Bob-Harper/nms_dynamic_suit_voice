# modular/tts_utils.py
import subprocess
from pathlib import Path

def run_tts(config, text: str, wem_num: str, postprocess: bool = True) -> Path:
    final_wav = config.temp_wem_dir / f"{wem_num}.wav"
    temp_wav = final_wav.with_suffix(".temp.wav")

    # Generate base TTS wav
    config.tts_model.tts_to_file(
        text=text,
        file_path=str(final_wav)
    )

    if postprocess:  # gain_db is the only one required, or the sound is too quiet in game.  Recommend =5
        apply_ffmpeg_filters(final_wav, temp_wav, gain_db=5, atempo=1.05, rate=0.5)
        temp_wav.replace(final_wav)

    return final_wav


def apply_ffmpeg_filters(input_wav: Path, output_wav: Path, gain_db=5, atempo=1.0, rate=1.0):
    """Apply volume/tempo/sample-rate adjustments to a wav file."""
    asetrate = int(44100 * rate)
    subprocess.run([
        "ffmpeg", "-hide_banner", "-y",
        "-i", str(input_wav),
        "-af", f"volume={gain_db}dB,atempo={atempo},asetrate={asetrate}",
        str(output_wav)
    ], check=True)

def test_tts(config, text: str, wem_num: str) -> Path:
    final_wav = config.temp_wem_dir / f"{wem_num}.wav"
    # Generate base TTS wav
    config.tts_model.tts_to_file(
        text=text,
        file_path=str(final_wav)
    )

    return final_wav
