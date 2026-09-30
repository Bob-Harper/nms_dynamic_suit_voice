import csv
import requests
import subprocess
from pathlib import Path
import sys

# CONFIG
OLLAMA_SERVER = "http://localhost:11434"
OLLAMA_MODEL = "gemma3:1b"
INPUT_CSV = r"C:\PythonScripts\NMS_SUIT_VOICE\tscript_with_intent.csv"
OUTPUT_DIR = Path(r"C:\PythonScripts\NMS_SUIT_VOICE\conversion_stygia")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
WEM_CONVERTER_CMD = Path(r"C:\PythonScripts\NMS_SUIT_VOICE\zSound2wem.cmd")


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


def convert_to_wem(wav_path: Path, output_dir: Path, conversion_quality="Vorbis Quality Low"):
    cmd_path = Path(r"C:\PythonScripts\NMS_SUIT_VOICE\sound2wem\zSound2wem.cmd")
    args = [
        str(cmd_path),
        f'--conversion:{conversion_quality}',
        f'--out:{str(output_dir)}',
        str(wav_path)
    ]
    subprocess.run(args, check=True)


target_wem = sys.argv[1] if len(sys.argv) > 1 else None

with open(INPUT_CSV, newline='', encoding='utf-8') as infile:
    reader = csv.DictReader(infile)
    for idx, row in enumerate(reader):
        wem_number = row.get('WEM number', '').strip()
        seed_phrase = row.get('Intent', '').strip()
        if target_wem and wem_number != target_wem:
            continue  # Skip if we're filtering and this row isn't it

        try:
            reworded = reword_phrase(seed_phrase)
            run_flite_tts(reworded, wem_number)
            convert_to_wem(OUTPUT_DIR / f"{wem_number}.wav", OUTPUT_DIR)

        except Exception as e:
            print(f"Error processing WEM {wem_number}: {e}")
