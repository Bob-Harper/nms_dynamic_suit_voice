import threading
from math import gcd
from pathlib import Path
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

_tts_init_lock = threading.Lock()
MIN_SAMPLES = 1024
CONTAINER_SR = 48000
DEFAULT_CARRIER_HZ = 300.0


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
    target_lufs = float(np.clip(target_lufs, -22.0, -8.0))
    true_peak_db = float(np.clip(true_peak_db, 2.0, 8.0))
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


def _wsola_time_stretch(y: np.ndarray, sr: int, speed_factor: float) -> np.ndarray:
    y = np.asarray(y, dtype=np.float32).reshape(-1)
    if abs(speed_factor - 1.0) < 1e-4 or len(y) < MIN_SAMPLES:
        return y

    win_len = max(256, int(round(0.032 * sr)))
    if win_len % 2 != 0:
        win_len += 1
    hop_out = win_len // 2
    hop_in = max(1, int(round(hop_out * speed_factor)))
    search_rad = max(8, hop_out // 2)

    window = np.hanning(win_len).astype(np.float32)
    est_frames = int(np.ceil(len(y) / hop_in)) + 4
    out = np.zeros(est_frames * hop_out + win_len, dtype=np.float32)
    norm = np.zeros_like(out)

    first = y[:win_len] if len(y) >= win_len else np.pad(y, (0, win_len - len(y)))
    out[:win_len] += first * window
    norm[:win_len] += window

    in_pos = hop_in
    out_pos = hop_out

    while in_pos + win_len <= len(y):
        lo = max(0, in_pos - search_rad)
        hi = min(len(y) - win_len, in_pos + search_rad)
        best_offset = in_pos

        if hi > lo and out_pos >= hop_out:
            ref = out[out_pos:out_pos + hop_out]
            ref_norm = float(np.linalg.norm(ref))
            if ref_norm > 1e-6:
                best_score = -1e18
                for cand in range(lo, hi + 1, 2):
                    seg = y[cand:cand + hop_out]
                    seg_norm = float(np.linalg.norm(seg))
                    if seg_norm > 1e-6:
                        score = float(np.dot(ref, seg)) / (ref_norm * seg_norm)
                        if score > best_score:
                            best_score = score
                            best_offset = cand

        frame = y[best_offset:best_offset + win_len]
        if out_pos + win_len > len(out):
            pad_extra = out_pos + win_len - len(out) + win_len
            out = np.pad(out, (0, pad_extra))
            norm = np.pad(norm, (0, pad_extra))

        out[out_pos:out_pos + win_len] += frame * window
        norm[out_pos:out_pos + win_len] += window
        in_pos += hop_in
        out_pos += hop_out

    end_idx = min(len(out), out_pos + hop_out)
    out = out[:end_idx]
    norm = norm[:end_idx]
    valid = norm > 1e-4
    out[valid] /= norm[valid]
    return out


def _resample_ratio(y: np.ndarray, ratio: float) -> np.ndarray:
    if abs(ratio - 1.0) < 1e-4 or len(y) < 16:
        return y
    up = max(1, int(round(ratio * 1000)))
    down = 1000
    g = gcd(up, down)
    return resample_poly(y, up // g, down // g).astype(np.float32)


def _pitch_shift_preserve_duration(y: np.ndarray, sr: int, semitones: float) -> np.ndarray:
    if abs(semitones) < 1e-3 or len(y) < MIN_SAMPLES:
        return y
    factor = 2.0 ** (semitones / 12.0)
    stretched = _wsola_time_stretch(y, sr, speed_factor=1.0 / factor)
    shifted = _resample_ratio(stretched, ratio=1.0 / factor)
    if len(shifted) > len(y):
        return shifted[:len(y)]
    if len(shifted) < len(y):
        return np.pad(shifted, (0, len(y) - len(shifted)))
    return shifted


def _formant_throat_shift(y: np.ndarray, sr: int, formant_percent: float) -> np.ndarray:
    if abs(formant_percent - 100.0) < 0.5 or len(y) < MIN_SAMPLES:
        return y
    ratio = float(np.clip(formant_percent, 25.0, 200.0)) / 100.0
    warped = _resample_ratio(y, ratio=1.0 / ratio)
    return _wsola_time_stretch(warped, sr, speed_factor=1.0 / ratio)


def apply_vocal_dsp_chain_matrix(
    audio: np.ndarray,
    source_sr: int,
    pitch_semitones: float = 0.0,
    tempo: float = 1.0,
    rate: float = 1.0,
    ring_freq: float = DEFAULT_CARRIER_HZ,
    ring_mix: float = 10.0,
    formant_percent: float = 100.0,
    target_sr: int = CONTAINER_SR,
    **kwargs,
) -> np.ndarray:
    y = np.asarray(audio, dtype=np.float32).reshape(-1)
    if len(y) < MIN_SAMPLES:
        y = np.pad(y, (0, MIN_SAMPLES - len(y)))

    sr = int(source_sr)
    if sr != int(target_sr):
        g = gcd(int(target_sr), sr)
        y = resample_poly(y, int(target_sr) // g, sr // g).astype(np.float32)
        sr = int(target_sr)

    if abs(float(tempo) - 1.0) >= 0.01:
        y = _wsola_time_stretch(y, sr, speed_factor=float(tempo))

    if abs(float(pitch_semitones)) >= 0.1:
        y = _pitch_shift_preserve_duration(y, sr, float(pitch_semitones))

    if abs(float(formant_percent) - 100.0) >= 1.0:
        y = _formant_throat_shift(y, sr, float(formant_percent))

    if abs(float(rate) - 1.0) >= 0.01:
        y = _resample_ratio(y, ratio=1.0 / float(rate))

    mix = float(np.clip(ring_mix, 0.0, 100.0)) / 100.0
    if mix > 0.0:
        t = np.arange(len(y), dtype=np.float32) / float(sr)
        carrier = np.sin(2.0 * np.pi * float(ring_freq) * t)
        y = (y * (1.0 - mix)) + ((y * carrier) * mix)

    if len(y) < MIN_SAMPLES:
        y = np.pad(y, (0, MIN_SAMPLES - len(y)))
    return np.asarray(y, dtype=np.float32)


def finalize_broadcast_audio(
    audio: np.ndarray,
    loudness_target: float = -11.0,
    loudness_true_peak: float = 6.0,
    sr: int = CONTAINER_SR,
) -> bytes:
    mastered = _normalize_loudness(audio, sr, target_lufs=loudness_target, true_peak_db=loudness_true_peak)
    clamped = np.clip(mastered, -1.0, 1.0)
    return (clamped * 32767.0).astype(np.int16).tobytes()


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

    if postprocess:
        tempo = float(fx.get("tempo", 1.0)) if fx.get("enable_tempo", True) else 1.0
        pitch_st = float(fx.get("pitch_semitones", 0)) if fx.get("enable_pitch", True) else 0.0
        ring_mix = float(fx.get("ring_mix", 10)) if fx.get("enable_ring", True) else 0.0
        rate = float(fx.get("rate", 1.0)) if fx.get("enable_rate", True) else 1.0
        formant = float(fx.get("formant_percent", 100)) if fx.get("enable_formant", True) else 100.0
        ring_freq = float(fx.get("ring_freq", DEFAULT_CARRIER_HZ))

        audio = apply_vocal_dsp_chain_matrix(
            audio=audio,
            source_sr=int(sample_rate),
            pitch_semitones=pitch_st,
            tempo=tempo,
            rate=rate,
            ring_freq=ring_freq,
            ring_mix=ring_mix,
            formant_percent=formant,
            target_sr=CONTAINER_SR,
        )
    else:
        sr = int(sample_rate)
        if sr != CONTAINER_SR:
            g = gcd(CONTAINER_SR, sr)
            audio = resample_poly(audio, CONTAINER_SR // g, sr // g).astype(np.float32)

    if fx.get("enable_loudness", True):
        if "loudness_target" in fx:
            target_lufs = float(fx.get("loudness_target", -11.0))
        else:
            target_lufs = -11.0 + float(fx.get("gain_db", 0.0))
        true_peak = float(fx.get("loudness_true_peak", 6.0))
        audio = _normalize_loudness(audio, CONTAINER_SR, target_lufs=target_lufs, true_peak_db=true_peak)

    stereo = np.ascontiguousarray(np.stack([audio, audio], axis=1), dtype=np.float32)
    wavfile.write(str(final_wav), CONTAINER_SR, stereo)

    return final_wav
