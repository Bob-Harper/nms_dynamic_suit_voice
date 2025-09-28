# modular/tts_utils.py
import subprocess
from pathlib import Path
import sys

def run_tts(config, text: str, wem_num: str, postprocess: bool = True) -> Path:
    final_wav = config.temp_wem_dir / f"{wem_num}.wav"
    temp_wav = final_wav.with_suffix(".temp.wav")
    speaker_wav = [r"C:\NMS_SUIT_VOICE\embeds\onna\amused.wav",
                   r"C:\NMS_SUIT_VOICE\embeds\onna\base_extended.wav",
                   r"C:\NMS_SUIT_VOICE\embeds\onna\concerned.wav",
                   r"C:\NMS_SUIT_VOICE\embeds\onna\emphasis.wav",
                   r"C:\NMS_SUIT_VOICE\embeds\onna\standard.wav",
                   r"C:\NMS_SUIT_VOICE\embeds\onna\trimmed_emphasis.wav",
                   r"C:\NMS_SUIT_VOICE\embeds\onna\whatever.wav",
                   ]
    # Generate base TTS wav
    if "xtts" in config.tts_model_name.lower():
        config.tts_model.tts_to_file(
            text=text,
            file_path=str(final_wav),
            speaker_wav=speaker_wav,
            language="en"
        )
    else:
        config.tts_model.tts_to_file(
            text=text,
            file_path=str(final_wav),
        )

    if postprocess:  # gain_db is the only one required, or the sound is too quiet in game.  Recommend =5
        apply_ffmpeg_filters(final_wav, temp_wav, gain_db=5, atempo=1.02, rate=0.51)
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
    ],
    check=True,
    creationflags=0x08000000 if sys.platform == "win32" else 0,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL  # suppress all output
    )

def test_tts(config, text: str, wem_num: str) -> Path:
    final_wav = config.temp_wem_dir / f"{wem_num}.wav"
    # Generate base TTS wav
    config.tts_model.tts_to_file(
        text=text,
        file_path=str(final_wav)
    )

    return final_wav
