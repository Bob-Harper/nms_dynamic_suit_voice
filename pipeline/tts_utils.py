# pipeline/tts_utils.py
import wave
from pathlib import Path
import numpy as np

MIN_SAMPLES = 1024

def complex_vocal_engine_matrix(audio: np.ndarray, speed_factor: float, pitch_factor: float, formant_factor: float, hop_length: int = 256, fft_size: int = 1024) -> np.ndarray:
    """Advanced Phase Vocoder engine that independently shifts tempo, pitch, and formants in a single phase-coherent pass."""
    if len(audio) < fft_size:
        return audio

    # 1. Compute STFT (Short-Time Fourier Transform) via NumPy windowing matrices
    window = np.hanning(fft_size)
    stft_frames = []
    for i in range(0, len(audio) - fft_size, hop_length):
        stft_frames.append(np.fft.rfft(audio[i:i+fft_size] * window))
    stft = np.array(stft_frames)

    num_frames = len(stft)
    num_bins = stft.shape[1]  # FIXED: Explicitly target the frequency bin dimension size

    # Calculate new frame count based purely on the requested sentence pacing speed factor
    new_num_frames = int(num_frames / speed_factor)
    if new_num_frames < 2:
        return audio

    # Pre-allocate phase coherent complex spectrum matrices
    output_stft = np.zeros((new_num_frames, num_bins), dtype=np.complex64)

    # Phase vocoder transformation variables
    phase_accum = np.zeros(num_bins)
    omega = 2 * np.pi * hop_length * np.arange(num_bins) / fft_size

    for i in range(new_num_frames):
        # Calculate cross-frame interpolation position adjusted by pitch factor rules
        pos = i * speed_factor * pitch_factor
        idx = int(pos)
        alpha = pos - idx

        if idx >= num_frames - 1:
            break

        # Extract magnitude profiles across temporal frame boundaries
        mag_source = (1 - alpha) * np.abs(stft[idx]) + alpha * np.abs(stft[idx+1])

        # --- ADVANCED SLIDER RE-COUPLED: Vocal Resonator Bandwidth (Formant Shift) ---
        mag = np.zeros(num_bins)
        for b in range(num_bins):
            src_bin = int(b / formant_factor)
            if src_bin < num_bins:
                mag[b] = mag_source[src_bin]

        # Compute precise phase delta increments to preserve spatial timing properties
        phase_diff = np.angle(stft[idx+1]) - np.angle(stft[idx]) - (omega * pitch_factor)
        phase_diff = (phase_diff + np.pi) % (2 * np.pi) - np.pi  # Normalize to [-PI, PI]

        # Synthesize phase coherent frequency targets
        phase_accum += (omega * pitch_factor) + phase_diff
        output_stft[i] = mag * np.exp(1j * phase_accum)

    # 2. Inverse STFT (Overlap-Add Synthesis Pass) back into pristine time-series float samples
    synthesis_hop = int(hop_length * pitch_factor)
    output_len = new_num_frames * synthesis_hop + fft_size
    output_audio = np.zeros(output_len, dtype=np.float32)
    window_sum = np.zeros(output_len, dtype=np.float32)

    for i in range(new_num_frames):
        start = i * synthesis_hop
        frame_time = np.fft.irfft(output_stft[i])
        output_audio[start:start+fft_size] += frame_time * window
        window_sum[start:start+fft_size] += window ** 2

    # Smooth normalization prevent clipping drops
    safe_mask = window_sum > 1e-4
    output_audio[safe_mask] /= window_sum[safe_mask]
    return output_audio

def run_tts(config, text: str, wem_num: str, postprocess: bool = True) -> Path:
    final_wav = config.temp_wav_dir / f"{wem_num}.wav"

    if not hasattr(config, "kokoro_pipeline") or config.kokoro_pipeline is None:
        from kokoro_onnx import Kokoro
        print("[TTS ENGINE]: Initializing ultra-lightweight Kokoro ONNX pipeline...")
        model_path = config.project_root / "assets" / "weights" / "kokoro-v1.0.fp16.onnx"
        voices_path = config.project_root / "assets" / "weights" / "voices-v1.0.bin"
        config.kokoro_pipeline = Kokoro(str(model_path), str(voices_path))

    voice_name = config.voice_effects.get("base_voice", "am_adam")
    samples, sample_rate = config.kokoro_pipeline.create(text, voice=voice_name, speed=1.0)
    audio = np.array(samples, dtype=np.float32)

    if postprocess:
        fx = config.voice_effects
        audio = apply_vocal_dsp_chain_matrix(
            audio=audio,
            source_sr=sample_rate,
            gain_db=fx.get("gain_db", 5),
            pitch_semitones=fx.get("pitch_semitones", 4),
            tempo=fx.get("tempo", 1.02),
            rate=fx.get("rate", 0.51),
            ring_freq=fx.get("ring_freq", 300),
            ring_mix=fx.get("ring_mix", 100),
            formant_percent=fx.get("formant_percent", 80),
            target_sr=44100,
            apply_gain_stage=False  # Defer volume scaling until AFTER normalization pass!
        )

    # 1. Perform safe baseline peak normalization first to keep sentences uniform
    if np.max(np.abs(audio)) > 0:
        audio = audio / np.max(np.abs(audio))

    # 2. FIXED GAIN STAGE POSITION: Apply user volume boost directly to normalized spectrum
    gain_db = config.voice_effects.get("gain_db", 5)
    amplitude_multiplier = 10 ** (gain_db / 20.0)
    audio = audio * amplitude_multiplier * 32767

    # Prevent clipping distortion hard ceiling overflows
    audio = np.clip(audio, -32768, 32767)
    final_bytes = audio.astype(np.int16).tobytes()

    with wave.open(str(final_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        wf.writeframes(final_bytes)

    return final_wav

def apply_vocal_dsp_chain_matrix(audio, source_sr, gain_db, pitch_semitones, tempo, rate,
                                 ring_freq, ring_mix, formant_percent, target_sr=44100, apply_gain_stage=True):
    """Decoupled digital audio signal processing pipeline."""
    if len(audio) < MIN_SAMPLES:
        audio = np.pad(audio, (0, MIN_SAMPLES - len(audio)))

    speed_factor = float(tempo)
    pitch_factor = 2 ** (pitch_semitones / 12)
    formant_factor = float(formant_percent / 100.0)

    # Execute complex multi-variable phase vocoder matrix
    audio = complex_vocal_engine_matrix(
        audio=audio,
        speed_factor=speed_factor,
        pitch_factor=pitch_factor,
        formant_factor=formant_factor
    )

    # --- PRIMARY SLIDER FIXED: Audio Frequency Warp (Chipmunk Scalar) ---
    factor_rate = float(rate)
    if factor_rate != 1.0:
        n_samples_target = max(int(len(audio) / factor_rate), MIN_SAMPLES)
        audio = np.interp(np.linspace(0, len(audio)-1, n_samples_target), np.arange(len(audio)), audio).astype(np.float32)

    # --- SYSTEM RESOLUTION: Enforce standard game output frequency (44.1kHz) ---
    if source_sr != target_sr:
        n_samples_final = max(int(len(audio) * (target_sr / source_sr)), MIN_SAMPLES)
        audio = np.interp(np.linspace(0, len(audio)-1, n_samples_final), np.arange(len(audio)), audio).astype(np.float32)

    # --- ADVANCED SLIDER FIXED: Cybernetic Ring Modulator Blending Matrix ---
    wet_factor = ring_mix / 100.0
    dry_factor = 1.0 - wet_factor

    dry_signal = audio.copy()
    t = np.arange(len(audio)) / target_sr
    wet_signal = audio * np.sin(2 * np.pi * ring_freq * t)

    audio = (dry_signal * dry_factor) + (wet_signal * wet_factor)

    # Optional internal volume stage (used primarily by the off-thread preview workers)
    if apply_gain_stage:
        amplitude_multiplier = 10 ** (gain_db / 20.0)
        audio = audio * amplitude_multiplier

    return audio
