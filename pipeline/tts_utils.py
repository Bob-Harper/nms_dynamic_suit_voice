# pipeline/tts_utils.py
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

    # Generate the raw voice line out of Coqui-TTS
    config.tts_model.tts_to_file(
        text=text,
        file_path=str(final_wav),
    )

    if postprocess:
        # Pull the live, active user-customized options from your config layer
        fx = config.voice_effects

        apply_vocal_dsp_chain(
            config=config,
            input_wav=final_wav,
            output_wav=temp_wav,
            gain_db=fx.get("gain_db", 5),
            pitch_semitones=fx.get("pitch_semitones", 4),
            tempo=fx.get("tempo", 1.02),
            rate=fx.get("rate", 0.51),
            ring_freq=fx.get("ring_freq", 300),
            ring_mix=fx.get("ring_mix", 100),
            formant_percent=fx.get("formant_percent", 80)
        )
        # Shift the fully processed file to its final location
        temp_wav.replace(final_wav)

    return final_wav

def apply_vocal_dsp_chain(config, input_wav: Path, output_wav: Path,
                          gain_db, pitch_semitones, tempo, rate,
                          ring_freq, ring_mix, formant_percent,
                          target_sr=44100):

    # 1. LOAD RAW BYTES NATIVELY INTO NUMPY ARRAY
    with wave.open(str(input_wav), "rb") as wf:
        sr = wf.getframerate()
        audio = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32)
        if wf.getnchannels() > 1:
            audio = audio[::wf.getnchannels()]  # Enforce structural mono

    if len(audio) < MIN_SAMPLES:
        audio = np.pad(audio, (0, MIN_SAMPLES - len(audio)))

    # ====================================================
    # SINGLE-PASS UNIFORM RESAMPLING MATRIX
    # ====================================================

    # Calculate the individual factor modifiers from user customization profiles
    factor_tempo = float(tempo)
    factor_pitch = 2 ** (pitch_semitones / 12)
    factor_formant = formant_percent / 100.0
    factor_rate = float(rate)

    # COMBINE ALL RATIOS INTO A SINGLE UNIFIED SCALING COEFFICIENT
    # This prevents compounding arithmetic errors from over-stretching the array track length
    combined_resample_ratio = factor_pitch * factor_formant * factor_rate * factor_tempo

    # Run the structural length transformation EXACTLY ONCE
    if combined_resample_ratio != 1.0:
        n_samples_target = max(int(len(audio) / combined_resample_ratio), MIN_SAMPLES)
        audio = resample(audio, n_samples_target)

    # 2. CYBERNETIC OVERLAY BLENDING (DRY/WET MATRIX)
    wet_factor = ring_mix / 100.0
    dry_factor = 1.0 - wet_factor

    dry_signal = audio.copy()
    t = np.arange(len(audio)) / target_sr  # Reference directly against target game engine frequency
    wet_signal = audio * np.sin(2 * np.pi * ring_freq * t)

    audio = (dry_signal * dry_factor) + (wet_signal * wet_factor)

    # 3. GAIN SCALE NORMALIZATION
    amplitude_multiplier = 10 ** (gain_db / 20.0)
    audio = audio * amplitude_multiplier

    if np.max(np.abs(audio)) > 0:
        audio = audio / np.max(np.abs(audio)) * 32767
    final_bytes = audio.astype(np.int16).tobytes()

    # Write the tightly compiled WAV asset straight to disk
    with wave.open(str(output_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(target_sr)  # Lock the final frequency to game engine standards (22050Hz)
        wf.writeframes(final_bytes)
