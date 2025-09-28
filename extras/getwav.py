import csv
from pathlib import Path

# Folder containing your WAV files
wav_folder = Path(r"C:\NMS_SUIT_VOICE\embeds\originalvoicefiles")
# Output CSV path
csv_file = wav_folder.parent / "metadata.csv"

# Scan for WAV files
wav_files = sorted(wav_folder.glob("*.wav"))

# Write CSV
with open(csv_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f, delimiter="|")  # LJSpeech-style pipe delimiter
    for wav in wav_files:
        writer.writerow([wav.name, "TRANSCRIPT_GOES_HERE"])

print(f"Generated CSV with {len(wav_files)} entries at {csv_file}")
