# pipeline/tts_utils.py
import threading
import numpy as np
from pathlib import Path
from scipy.io import wavfile
from scipy.signal import resample_poly

_tts_init_lock = threading.Lock()
MIN_SAMPLES = 1024
CONTAINER_SR = 48000


def _soft_clip(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=np.float32)
    out = np.copy(x)
    mask = np.abs(out) > 0.7
    out[mask] = np.sign(out[mask]) * (0.7 + 0.3 * np.tanh((np.abs(out[mask]) - 0.7) / 0.3))
    return out


def _measure_lufs(y: np.ndarray, sr: int) -> float:
    y = np.asarray(y, dtype=np.float32).reshape(-1)
    min_samples = max(1, int(0.4 * sr))
    if 0 < len(y) < min_samples:
        y = np.tile(y, int(np.ceil(min_samples / len(y))))[:min_samples]
    try:
        import pyloudnorm as pyln
        val = pyln.Meter(sr).integrated_loudness(y)
        return float(val) if np.isfinite(val) else -70.0
    except ImportError:
        rms = float(np.sqrt(np.mean(y ** 2)))
        return 20.0 * np.log10(max(rms, 1e-9)) - 0.691


def _normalize_loudness(y: np.ndarray, sr: int, target_lufs: float = -11.0, true_peak_db: float = 6.0) -> np.ndarray:
    sample_ceiling = max(abs(true_peak_db) - 2.0, 0.0)
    down = 10.0 ** (-sample_ceiling / 20.0)
    up = 10.0 ** (sample_ceiling / 20.0)
    for _ in range(5):
        gain_db = target_lufs - _measure_lufs(y, sr) + 0.4
        if abs(gain_db) <= 0.4:
            break
        gain_db = float(np.clip(gain_db, -12.0, 12.0))
        y = _soft_clip(y * down * (10.0 ** (gain_db / 20.0))) * up
    return np.asarray(y, dtype=np.float32)


def run_tts(config, text: str, wem_num: str, postprocess: bool = True) -> Path:
    final_wav = config.temp_wav_dir / f"{wem_num}.wav"

    if getattr(config, "kokoro_pipeline", None) is None:
        with _tts_init_lock:
            if getattr(config, "kokoro_pipeline", None) is None:
                from kokoro_onnx import Kokoro
                if isinstance(config.tts_model, Kokoro):
                    config.kokoro_pipeline = config.tts_model
                else:
                    print("[TTS ENGINE]: Initializing Kokoro ONNX pipeline...")
                    config.kokoro_pipeline = Kokoro(
                        str(config.tts_model),
                        str(config.tts_voice_bin),
                    )

    fx = config.voice_effects
    voice_name = fx.get("base_voice")

    with _tts_init_lock:
        samples, sample_rate = config.kokoro_pipeline.create(text, voice=voice_name, speed=1.0)

    audio = np.asarray(samples, dtype=np.float32).reshape(-1)
    if len(audio) < MIN_SAMPLES:
        audio = np.pad(audio, (0, MIN_SAMPLES - len(audio)))

    # Polyphase resample to 48kHz cleanly (24kHz -> 48kHz is exact 2x upsample, zero FFT ringing)
    sr = int(sample_rate)
    if sr != CONTAINER_SR:
        from math import gcd
        g = gcd(CONTAINER_SR, sr)
        audio = resample_poly(audio, CONTAINER_SR // g, sr // g).astype(np.float32)

    # Match original WEM's -14.5 dBFS RMS / -0.4 dBFS Peak using float32 headroom
    target_lufs = float(fx.get("loudness_target", -11.0))
    true_peak = float(fx.get("loudness_true_peak", 6.0))
    audio = _normalize_loudness(audio, CONTAINER_SR, target_lufs=target_lufs, true_peak_db=true_peak)

    stereo = np.ascontiguousarray(np.stack([audio, audio], axis=1), dtype=np.float32)
    wavfile.write(str(final_wav), CONTAINER_SR, stereo)

    return final_wav
