import csv
import requests
import subprocess
from pathlib import Path

# CONFIG
OLLAMA_SERVER = "http://localhost:11434"
OLLAMA_MODEL = "gemma3:1b"
INPUT_CSV = r"C:\PythonScripts\NMS_SUIT_VOICE\tscript_with_intent.csv"
OUTPUT_CSV = r"C:\PythonScripts\NMS_SUIT_VOICE\transcriptions_reworded.csv"
OUTPUT_DIR = Path(r"C:\PythonScripts\NMS_SUIT_VOICE\conversion_stygia")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

WSL_VOICE_PATH = "/home/msutt/flitevox/voices/cmu_us_slt.flitevox"

SYSTEM_PROMPT = (
    "You are writing voice lines for a futuristic space suit artificial intelligence."
    "For each input phrase, provide exactly one short sentence (max 25 words), "
    "For status or completion messages, restate briefly with personality but without prefixes.\n"
    "Avoid repeating words or bland phrasing.\n"
    "Never mention numbers, percentages, or details not present in the input.\n\n"
    "THE FOLLOWING ARE Examples and  style guides:\n"
    "Input: Food levels critical\n"
    "Output: You are hungry!  Find something to eat before you starve to death.\n\n"
    "Input: Alert: Civilian convoy under attack\n"
    "Output: Freindlies are in danger! We should help them!\n\n"
    "Input: Physical damage sustained, medical attention needed.\n"
    "Output: Ouch.  Looks like you need a bandaid.\n\n"
    "Keep the original intent of the input phrase, this is MANDATORY. never invent facts or numbers.\n\n"
    "DO not treat the input as a question to be answered or an observation to be commented on."
    "YOUR task is to RESTATE the input phrase, nothing more.  You are not a character responding to input, "
    "you are a scriptwriter who is tasked with making the dialogue more engaging."
    "Tone: Slightly amused, mildly concerned, a little sarcastic.\n"
    "Now reword the provided phrase so the suit can announce the results to the user:\n"
)


def reword_phrase(phrase: str) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": phrase}
        ],
        "stream": False,
        "options": {
            "temperature": 0.8,
            "top_k": 20,
            "top_p": 0.9
        }
    }
    response = requests.post(f"{OLLAMA_SERVER}/api/chat", json=payload)
    response.raise_for_status()
    response_json = response.json()
    return response_json.get("message", {}).get("content", "").strip()


def run_flite_tts(text: str, wem_designation: str) -> None:
    windows_output_path = OUTPUT_DIR / f"{wem_designation}.wav"
    temp_output_path = windows_output_path.with_suffix(".raw.wav")

    # Step 1: Generate TTS with Flite into a temp file
    cmd_flite = [
        "wsl",
        "flite",
        "-voice", WSL_VOICE_PATH,
        "--setf", "int_f0_target_mean=155",
        "--setf", "duration_stretch=0.88",
        "-t", text,
        "-o", f"/mnt/{temp_output_path.drive[0].lower()}{temp_output_path.as_posix()[2:]}"
    ]
    subprocess.run(cmd_flite, check=True)

    # Step 2: Apply compression + safe volume boost via ffmpeg
    cmd_ffmpeg = [
        "ffmpeg",
        "-y",  # overwrite output
        "-i", str(temp_output_path),
        "-af", "acompressor=threshold=-25dB:ratio=6:attack=10:release=100,volume=5.0",
        str(windows_output_path)
    ]
    subprocess.run(cmd_ffmpeg, check=True)

    # Step 3: Clean up raw temp file
    temp_output_path.unlink(missing_ok=True)

    print(f"Generated and boosted: {windows_output_path}")


output_rows = []

with open(INPUT_CSV, newline='', encoding='utf-8') as infile:
    reader = csv.DictReader(infile)
    for idx, row in enumerate(reader):
        wem_number = row['WEM number'].strip()
        original_phrase = row['Transcription'].strip()
        seed_phrase = row['Intent'].strip()

        try:
            reworded = reword_phrase(seed_phrase)
            print(f"\nWEM: {wem_number}")
            print(f"Original: {original_phrase}")
            print(f"Seed: {seed_phrase}")
            print(f"Reworded: {reworded}")

            # Immediately run TTS on the reworded phrase
            run_flite_tts(reworded, wem_number)

        except Exception as e:
            print(f"Error processing WEM {wem_number}: {e}")
            reworded = "<ERROR>"

        output_rows.append({
            "WEM number": wem_number,
            "Original": original_phrase,
            "Seed": seed_phrase,
            "Reworded": reworded
        })

fieldnames = ["WEM number", "Original", "Seed", "Reworded"]
with open(OUTPUT_CSV, "w", newline='', encoding='utf-8') as outfile:
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(output_rows)

print(f"\nALL DONE. Output written to: {OUTPUT_CSV}")
