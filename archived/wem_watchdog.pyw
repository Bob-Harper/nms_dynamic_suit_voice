import time
import csv
import subprocess
from pathlib import Path
from dotenv import load_dotenv
import os
import shutil

# Load .env from the local subdirectory
load_dotenv(dotenv_path=Path(__file__).parent / "suit_voice.env")
CHECK_INTERVAL = float(os.getenv("CHECK_INTERVAL"))
CSV_PATH = Path(os.getenv("CSV_PATH"))
WATCH_DIR = Path(os.getenv("WATCH_DIR").strip('"'))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR").strip('"'))
TEMP_WEM_DIR = Path(os.getenv("TEMP_WEM_DIR").strip('"'))
CMD_SCRIPT_PATH = Path(os.getenv("CMD_SCRIPT_PATH").strip('"'))
OLLAMA_SERVER = os.getenv("OLLAMA_SERVER")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
FLITE_VOICE_PATH = Path(os.getenv("FLITE_VOICE_PATH"))
FLITE_VOICE_PITCH = os.getenv("FLITE_VOICE_PITCH")
FLITE_VOICE_TEMPO = os.getenv("FLITE_VOICE_TEMPO")
TEMP_WEM_DIR.mkdir(parents=True, exist_ok=True)

# CONFIG
SYSTEM_PROMPT = (
    "You are writing voice lines for a futuristic space suit artificial intelligence."
    "For each input phrase, provide exactly one short sentence (max 30 words), "
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
    "Tone: amused, mildly concerned, sarcastic.\n"
    "Now reword the provided phrase so the suit can announce the results to the user:\n"
)

# Load CSV into memory
intent_map = {}
with open(CSV_PATH, newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        wem_number = (row.get('WEM number') or '').strip()
        seed_phrase = (row.get('Intent') or '').strip()
        if wem_number and seed_phrase:
            intent_map[wem_number] = seed_phrase


def is_file_locked(filepath: Path) -> bool:
    if not filepath.exists():
        return False
    try:
        with open(filepath, 'a'):
            return False
    except PermissionError:
        return True


def reword_phrase(phrase: str) -> str:
    import requests
    print(f"Input phrase: {phrase}")
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": phrase}
        ],
        "stream": False,
        "options": {
            "temperature": 0.95,
            "top_k": 20,
            "top_p": 0.9
        }
    }
    response = requests.post(f"{OLLAMA_SERVER}/api/chat", json=payload)
    response.raise_for_status()
    generated_response = response.json().get("message", {}).get("content", "").strip()
    print(f"New Phrase: {generated_response}")
    return generated_response


def run_flite_tts(text: str, wem_num: str):
    final_path = TEMP_WEM_DIR / f"{wem_num}.wav"
    temp_wav_path = TEMP_WEM_DIR / f"{wem_num}.temp.wav"
    raw_path = final_path.with_suffix(".raw.wav")

    # Run flite
    subprocess.run([
        str(FLITE_VOICE_PATH),
        "--setf", f"int_f0_target_mean={FLITE_VOICE_PITCH}",
        "--setf", f"duration_stretch={FLITE_VOICE_TEMPO}",
        "-t", text,
        "-o", str(raw_path)
    ], check=True)

    if not raw_path.exists():
        raise FileNotFoundError(f"Raw wav not created: {raw_path}")

    # Run ffmpeg to compress and adjust volume
    subprocess.run([
        "ffmpeg", "-hide_banner", "-y", "-i", str(raw_path),
        "-af", "acompressor=threshold=-25dB:ratio=6:attack=10:release=100,volume=5.0",
        str(temp_wav_path)
    ], check=True)

    if not temp_wav_path.exists():
        raise FileNotFoundError(f"Processed wav not created: {temp_wav_path}")

    # Clean up and rename final
    raw_path.unlink(missing_ok=True)
    temp_wav_path.replace(final_path)

    if not final_path.exists():
        raise FileNotFoundError(f"Final wav not found after rename: {final_path}")

    print(f"Generated WAV: {final_path}")
    return final_path


def convert_to_wem(wav_file_path: Path, output_dir: Path, conversion_quality="Vorbis Quality High"):
    subprocess.run([
        "cmd.exe", "/c",
        str(CMD_SCRIPT_PATH),
        f'--conversion:{conversion_quality}',
        f'--out:{str(output_dir)}',
        str(wav_file_path)
    ], check=True)

    print(f"Conversion attempt complete for {wav_file_path.name}")


# Initialize access times for all .wav files in the directory
access_times = {f: f.stat().st_atime for f in WATCH_DIR.glob("*.wem")}

print("Watching for file access...")

while True:
    for f in WATCH_DIR.glob("*.wem"):
        try:
            current_atime = f.stat().st_atime
            if current_atime != access_times.get(f, 0):
                wem_id = f.stem  # Extract ID from filename (without extension)
                print(f"Access detected: {f.name} (ID: {wem_id})")
                if wem_id in intent_map:
                    reworded = reword_phrase(intent_map[wem_id])
                    print("Calling run_flite_tts...")
                    try:
                        wav_path = run_flite_tts(reworded, wem_id)
                        print(f"WAV created at {wav_path}")
                    except Exception as e:
                        print(f"Error creating WAV: {e}")
                        continue

                    print("Calling convert_to_wem...")
                    try:
                        convert_to_wem(wav_path, TEMP_WEM_DIR)
                        print("Conversion to WEM complete")
                    except Exception as e:
                        print(f"Error converting to WEM: {e}")
                        continue
                    temp_wem_path = TEMP_WEM_DIR / f"{wem_id}.wem"
                    final_wem_path = OUTPUT_DIR / f"{wem_id}.wem"

                    for attempt in range(20):
                        try:
                            shutil.move(str(temp_wem_path), str(final_wem_path))
                            print(f"WEM moved successfully: {final_wem_path}")
                            break
                        except PermissionError:
                            print(f"WEM file still in use. Retry {attempt + 1}")
                            time.sleep(1)
                        except Exception as e:
                            print(f"Unexpected error while moving WEM: {e}")
                            break
                    else:
                        print(f"Failed to move WEM after 20 retries: {temp_wem_path}")

                    new_wem = WATCH_DIR / f"{wem_id}.wem"
                    if new_wem.exists():
                        access_times[new_wem] = new_wem.stat().st_atime
                else:
                    print(f"No intent found for WEM ID {wem_id}, skipping.")

        except Exception as e:
            print(f"Error handling {f.name}: {e}")

    time.sleep(CHECK_INTERVAL)
