# modular/tts_utils.py
import subprocess
from pathlib import Path
import sys
import wave
import numpy as np
from scipy.signal import resample

MIN_SAMPLES = 1024  # absolute minimum number of samples per channel

def run_tts(config, text: str, wem_num: str, postprocess: bool = True) -> Path:
    final_wav = config.temp_wav_dir / f"{wem_num}.wav"
    temp_wav = final_wav.with_suffix(".temp.wav")
    speaker_wav = [
        r"C:\NMS_SUIT_VOICE\embeds\onna\amused.wav",
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

    if postprocess:
        apply_ffmpeg_filters(final_wav, temp_wav, atempo=1.02, rate=0.51)
        temp_wav.replace(final_wav)

    return final_wav


def apply_ffmpeg_filters(input_wav: Path, output_wav: Path,
                         gain_db=5, atempo=1.0, rate=1.0,
                         ring_freq=300, pitch_semitones=4, formant_percent=80,
                         target_sr=22050):
    # Step 1: FFmpeg gain/tempo/asetrate
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
        stderr=subprocess.DEVNULL
    )

    # Step 2: Load WAV
    with wave.open(str(output_wav), "rb") as wf:
        sr = wf.getframerate()
        audio = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32)
        if wf.getnchannels() > 1:
            audio = audio[::wf.getnchannels()]  # mono

    # --- ENSURE MINIMUM SAMPLES ---
    if len(audio) < MIN_SAMPLES:
        pad_amount = MIN_SAMPLES - len(audio)
        audio = np.pad(audio, (0, pad_amount))

    # Step 3: Robotic effects
    t = np.arange(len(audio)) / sr
    audio *= np.sin(2 * np.pi * ring_freq * t)  # ring modulation

    factor_pitch = 2 ** (pitch_semitones / 12)
    n_samples_pitch = max(int(len(audio) / factor_pitch), MIN_SAMPLES)
    audio = resample(audio, n_samples_pitch)

    factor_formant = formant_percent / 100
    n_samples_formant = max(int(len(audio) / factor_formant), MIN_SAMPLES)
    audio = resample(audio, n_samples_formant)

    # Step 4: Resample to target sample rate
    if sr != target_sr:
        n_samples = max(int(len(audio) * target_sr / sr), MIN_SAMPLES)
        audio = resample(audio, n_samples)
        sr = target_sr

    # Step 5: Normalize and save
    if np.max(np.abs(audio)) > 0:
        audio = audio / np.max(np.abs(audio)) * 32767
    audio = audio.astype(np.int16)

    with wave.open(str(output_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(audio.tobytes())
