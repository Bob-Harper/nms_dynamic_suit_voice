import numpy as np
import pandas as pd
import soundfile as sf

def match_spectrum(input_wav, spectrum_csv, output_wav=None):
    if output_wav is None:
        output_wav = input_wav.replace(".wav", "_matched.wav")

    # Load audio
    y, sr = sf.read(input_wav)
    if y.ndim > 1:  # take first channel if stereo
        y = y[:, 0]

    # FFT
    fft = np.fft.rfft(y)
    magnitude = np.abs(fft)
    phase = np.angle(fft)

    # Load reference spectrum
    spec_df = pd.read_csv(spectrum_csv, sep="\t")
    freqs = spec_df.iloc[:, 0].values
    levels_db = spec_df.iloc[:, 1].values
    ref_magnitude = 10 ** (levels_db / 20)

    # Interpolate reference magnitude to match FFT bins
    fft_freqs = np.fft.rfftfreq(len(y), 1/sr)
    interp_ref = np.interp(fft_freqs, freqs, ref_magnitude)

    # Apply scaling
    new_fft = fft * (interp_ref / (magnitude + 1e-8))

    # Inverse FFT
    y_matched = np.fft.irfft(new_fft)
    y_matched = np.clip(y_matched, -1.0, 1.0)

    # Save output
    sf.write(output_wav, y_matched, sr)
    print(f"Saved matched WAV to: {output_wav}")


input_file = r"C:\Users\msutt\Downloads\tesvoice\tacotron__tts_output.wav"
spectrum_csv = r"C:\Users\msutt\Downloads\tesvoice\reference_spectrum.csv"
match_spectrum(input_file, spectrum_csv)
