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

    config.tts_model.tts_to_file(
        text=text,
        file_path=str(final_wav),
    )

    if postprocess:
        # Pull your customized voice options directly out of the verified config layer!
        fx = config.voice_effects  # Native user configuration dictionary

        apply_vocal_dsp_chain(
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
        temp_wav.replace(final_wav)

    return final_wav

def apply_vocal_dsp_chain(input_wav: Path, output_wav: Path,
                          gain_db, pitch_semitones, tempo, rate,
                          ring_freq, ring_mix, formant_percent,
                          target_sr=22050):

    # 1. LOAD RAW BYTES NATIVELY INTO NUMPY ARRAY
    with wave.open(str(input_wav), "rb") as wf:
        sr = wf.getframerate()
        audio = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32)
        if wf.getnchannels() > 1:
            audio = audio[::wf.getnchannels()]  # Enforce structural mono

    if len(audio) < MIN_SAMPLES:
        audio = np.pad(audio, (0, MIN_SAMPLES - len(audio)))

    # 2. RUN MATRIX RESAMPLING IN THE CORRECT PASSED SANDBOX SEQUENCE
    # A. Pitch Frequency Shift
    factor_pitch = 2 ** (pitch_semitones / 12)
    n_samples_pitch = max(int(len(audio) / factor_pitch), MIN_SAMPLES)
    audio = resample(audio, n_samples_pitch)

    # B. Throat Resonator Formant Shift
    factor_formant = formant_percent / 100
    n_samples_formant = max(int(len(audio) / factor_formant), MIN_SAMPLES)
    audio = resample(audio, n_samples_formant)

    # C. Cybernetic Overlay Blending (Dry/Wet Matrix)
    wet_factor = ring_mix / 100.0
    dry_factor = 1.0 - wet_factor

    dry_signal = audio.copy()
    t = np.arange(len(audio)) / sr
    wet_signal = audio * np.sin(2 * np.pi * ring_freq * t)

    audio = (dry_signal * dry_factor) + (wet_signal * wet_factor)

    # Write processed array steps back to a temporary disk target
    if np.max(np.abs(audio)) > 0:
        audio = audio / np.max(np.abs(audio)) * 32767
    audio_bytes = audio.astype(np.int16).tobytes()

    with wave.open(str(output_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(audio_bytes)

    # 3. RUN FFMPEG PASSTHROUGH TO APPLY VOLUME & SENTENCE SPEED SEAMLESSLY
    CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0
    setrate_val = int(44100 * rate)

    # We strip input_wav out and stream directly onto output_wav
    subprocess.run([
        "ffmpeg", "-hide_banner", "-y",
        "-i", str(output_wav),
        "-af", f"volume={gain_db}dB,atempo={tempo},asetrate={setrate_val}",
        str(input_wav)  # Overwrite temporary tracking target
    ],
        check=True,
        creationflags=CREATE_NO_WINDOW,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    # Final downsample filter match step to lock target frequencies to the game engine
    with wave.open(str(input_wav), "rb") as wf:
        sr = wf.getframerate()
        audio = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32)

    if sr != target_sr:
        n_samples = max(int(len(audio) * target_sr / sr), MIN_SAMPLES)
        audio = resample(audio, n_samples)
        sr = target_sr

    if np.max(np.abs(audio)) > 0:
        audio = audio / np.max(np.abs(audio)) * 32767
    final_bytes = audio.astype(np.int16).tobytes()

    with wave.open(str(output_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(final_bytes)
