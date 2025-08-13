from pystray import Icon, Menu, MenuItem
from PIL import Image
import threading
import time
import csv
import subprocess
from pathlib import Path
from dotenv import load_dotenv
import os
import shutil
from TTS.api import TTS
import sys
import re
import requests
import random
from ollama import Client

# Load .env from the local subdirectory
load_dotenv(dotenv_path=Path(__file__).parent / "suit_voice.env")
CHECK_INTERVAL = float(os.getenv("CHECK_INTERVAL"))
WATCH_DIR = Path(os.getenv("WATCH_DIR").strip('"'))
CSV_PATH = Path(os.getenv("CSV_PATH"))
TEMP_WEM_DIR = Path(os.getenv("TEMP_WEM_DIR").strip('"'))
TEMP_WEM_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR").strip('"'))
CMD_SCRIPT_PATH = Path(os.getenv("CMD_SCRIPT_PATH").strip('"'))
OLLAMA_SERVER = os.getenv("OLLAMA_SERVER")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
try:
    TTS_MODEL = os.getenv("TTS_MODEL")
    if not TTS_MODEL:
        raise ValueError("TTS_MODEL not set in environment")
    tts_model = TTS(model_name=TTS_MODEL)
except Exception as e0:
    raise SystemExit(f"Failed to load TTS model: {e0}")
ICON_IMAGE = Path(os.getenv("ICON_IMAGE"))
LOGGING = os.getenv("LOGGING", "false").strip().lower() == "true"  # force boolean: true, anything else => False
GAME_OUTPUT_CSV = Path(os.getenv("GAME_OUTPUT_CSV"))
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0
with open("assets/suit_voice_prompt.txt", encoding="utf-8") as f:
    SUIT_VOICE_PROMPT = f.read()
RUNNING = True


def load_intent_map(csv_path: Path) -> dict:
    i_intent_map = {}
    try:
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                wem_number = (row.get('WEM number') or '').strip()
                original_phrase = (row.get('Transcription') or '').strip()
                seed_phrase = (row.get('Seed_Phrase') or '').strip()
                intent = (row.get('Intent') or '').strip()
                context = (row.get('Context') or '').strip()
                thinking = (row.get('Thinking') or '').strip()
                usage_count = (row.get('Count') or '').strip()

                if wem_number and seed_phrase:
                    seed_columns = [seed_phrase]  # start with primary phrase first
                    seed_columns += [row.get(f'seed{i}', '').strip() for i in range(1, 10) if
                                     row.get(f'seed{i}', '').strip()]

                    if not seed_columns:
                        seed_columns = [seed_phrase]
                    i_intent_map[wem_number] = {
                        "seed_phrases": seed_columns,
                        "original_phrase": original_phrase,
                        "intent": intent,
                        "context": context,
                        "thinking": thinking,
                        "count": int(usage_count) if usage_count.isdigit() else 0
                    }
    except Exception as e1:
        print(f"Error loading intent map: {e1}")
    return i_intent_map


def get_seed_prompt(intent_entry):
    seeds = intent_entry.get("seed_phrases", [])
    if not seeds:
        phrase = intent_entry.get("original_phrase", "External Reality alert, computer error detected")
        return phrase.strip() if isinstance(phrase, str) else str(phrase)

    if isinstance(seeds, str):
        seeds = [seeds]

    chosen = random.choice(seeds)
    return chosen.strip() if isinstance(chosen, str) else str(chosen)


def save_usage_counts():
    with open(CSV_PATH, encoding='utf-8', newline='') as f1:
        lines = list(csv.reader(f1))

    headers = lines[0]
    idx_wem = headers.index("WEM number")
    idx_count = headers.index("Count")

    for i in range(1, len(lines)):
        wem = lines[i][idx_wem].strip()
        if wem in intent_map:
            lines[i][idx_count] = str(intent_map[wem]["count"])

    with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f2:
        writer = csv.writer(f2)
        writer.writerows(lines)


def reword_phrase(input_phrase: str,
                  intent_data: str,
                  wem_id: str,
                  original_phrase_r: str
                  ) -> str:
    prompt = SUIT_VOICE_PROMPT.format(intent_data=intent_data.strip(), input_phrase=input_phrase.strip())

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "max_tokens": 120,
            "temperature": 0.3,
            "top_k": 10,
            "top_p": 0.9,
            "seed": random.randint(1, 9999999)  # or pass as an argument
        }
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(f"{OLLAMA_SERVER}/api/generate", json=payload, timeout=10)
            response.raise_for_status()
            generated_response = response.json().get("response", "").strip()
            if not generated_response:
                raise ValueError("Empty response from Ollama")
            generated_response = re.sub(r"<think>.*?</think>", "", generated_response, flags=re.DOTALL).strip()
            return generated_response
        except Exception as e2:
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                print(f"LLM ERROR on WEM {wem_id}: {e2}")
                return f"WEM ERROR {wem_id}, {e2}.  {original_phrase_r}"


def run_tts(text: str, wem_num: str, gain_db: float = 5.0) -> Path:
    final_wav = TEMP_WEM_DIR / f"{wem_num}.wav"
    temp_wav = final_wav.with_suffix(".temp.wav")

    tts_model.tts_to_file(text=text, file_path=str(final_wav))
    if gain_db and gain_db != 0:
        subprocess.run([
            "ffmpeg", "-hide_banner", "-y",
            "-i", str(final_wav),
            "-af", f"volume={gain_db}dB,atempo=1.55,asetrate=44100*0.44",
            str(temp_wav)
        ], check=True, creationflags=CREATE_NO_WINDOW)

        temp_wav.replace(final_wav)

    if not final_wav.exists():
        raise FileNotFoundError(f"TTS output WAV not found: {final_wav}")

    print(f"Generated WAV: {final_wav}")
    return final_wav


def convert_to_wem(wav_file_path: Path, output_dir: Path, conversion_quality="Vorbis Quality High"):
    subprocess.run([
        "cmd.exe", "/c",
        str(CMD_SCRIPT_PATH),
        f'--conversion:{conversion_quality}',
        f'--out:{str(output_dir)}',
        str(wav_file_path)
    ], check=True, creationflags=CREATE_NO_WINDOW)

    print(f"Conversion attempt complete for {wav_file_path.name}")


def watch_wems():
    # Initialize access times for all .wav files in the directory
    access_times = {f3: f3.stat().st_atime for f3 in WATCH_DIR.glob("*.wem")}
    print("Watching for file access...")
    while RUNNING:

        for f3 in WATCH_DIR.glob("*.wem"):
            try:
                current_atime = f3.stat().st_atime
                if current_atime != access_times.get(f3, 0):
                    wem_id = f3.stem  # Extract ID from filename (without extension)
                    print(f"Access detected: {f3.name} (ID: {wem_id})")

                    if wem_id in intent_map:
                        intent_entry = intent_map[wem_id]
                        intent_entry["count"] += 1
                        original_phrase_w = intent_entry["original_phrase"]
                        seed_phrase_w = get_seed_prompt(intent_entry)  # Pass whole dict
                        intent_w = intent_entry["intent"]
                        reworded = reword_phrase(seed_phrase_w, intent_w, wem_id, original_phrase_w)
                        if LOGGING:
                            fieldnames = ["WEM number", "Original", "Seed Phrase", "Final Voice Line"]
                            file_exists = Path(GAME_OUTPUT_CSV).exists()

                            log_entry = {
                                "WEM number": wem_id,
                                "Original": original_phrase_w if wem_id in intent_map else "",
                                "Seed Phrase": seed_phrase_w if wem_id in intent_map else "",
                                "Final Voice Line": reworded
                            }

                            with open(GAME_OUTPUT_CSV, "a", newline='', encoding='utf-8') as outfile:
                                writer = csv.DictWriter(outfile, fieldnames=fieldnames)
                                if not file_exists:
                                    writer.writeheader()
                                writer.writerow(log_entry)

                            print(f"Appended output for review in {GAME_OUTPUT_CSV}")

                        print("Calling run_tts...")
                        try:
                            wav_path = run_tts(reworded, wem_id)
                            print(f"WAV created at {wav_path}")
                        except Exception as e3:
                            print(f"Error creating WAV: {e3}")
                            continue

                        print("Calling convert_to_wem...")
                        try:
                            convert_to_wem(wav_path, TEMP_WEM_DIR)
                            print("Conversion to WEM complete")
                        except Exception as e3:
                            print(f"Error converting to WEM: {e3}")
                            continue
                        temp_wem_path = TEMP_WEM_DIR / f"{wem_id}.wem"
                        final_wem_path = OUTPUT_DIR / f"{wem_id}.wem"

                        for attempt in range(40):
                            try:
                                shutil.move(str(temp_wem_path), str(final_wem_path))
                                print(f"WEM moved successfully: {final_wem_path}")
                                break
                            except PermissionError:
                                # print(f"WEM file still in use. Retry {attempt + 1}")
                                time.sleep(0.5)
                            except Exception as e3:
                                print(f"Unexpected error while moving WEM: {e3}")
                                break
                        else:
                            print(f"Failed to move WEM after 20 seconds: {temp_wem_path}")

                        new_wem = WATCH_DIR / f"{wem_id}.wem"
                        if new_wem.exists():
                            access_times[new_wem] = new_wem.stat().st_atime
                    else:
                        print(f"No intent found for WEM ID {wem_id}, skipping.")

            except Exception as e3:
                print(f"Error handling {f3.name}: {e3}")

        time.sleep(CHECK_INTERVAL)


def shutdown():
    global RUNNING
    RUNNING = False
    save_usage_counts()
    try:
        subprocess.run(["ollama", "stop", OLLAMA_MODEL])
    except Exception as e4:
        print(f"Warning stopping Ollama model: {e4}")

    tray_icon.stop()


def on_quit(_icon, _item):
    shutdown()


intent_map = load_intent_map(CSV_PATH)


# Create a tray icon (point to any .png, or use PIL to make a blank one. 64x64px).
menu = Menu(MenuItem('Quit', on_quit))

try:
    ICON_IMAGE = Path(os.getenv("ICON_IMAGE"))
    if ICON_IMAGE.exists():
        img = Image.open(ICON_IMAGE)
    else:
        raise FileNotFoundError(f"Icon not found at {ICON_IMAGE}")
except Exception as e5:
    print(f"Warning: Could not load icon: {e5}. Falling back to blank icon.")
    img = Image.new('RGB', (64, 64), color='black')

# client = Client(OLLAMA_SERVER) -- DO NOT CHANGE THIS CALL.  You will not pass Go.  You will not collect $200.
client = Client(OLLAMA_SERVER)

# preload designated model by giving it a minimal inference task
client.chat(model=OLLAMA_MODEL, messages=[{"role": "user", "content": " "}])

try:
    models = client.ps()
    models_list = models.models  # This is the actual list of Model objects
    # Extract the model names from the returned Model objects
    model_names = [m.model for m in models_list]  # 'model' attribute holds the model name like 'smollm2:latest'
except Exception as e6:
    print(f"Warning: Could not query models from Ollama: {e6}")
    model_names = []
# Compose dynamic tooltip
# Base tooltip lines
tooltip_lines = ["NMS DynamicSuitVoice"]

# Estimate the static character count (excluding the model name)
base_len = len("\n".join(tooltip_lines))
warning_lines = []
if len(model_names) == 1:
    prefix = "Loaded: "
    suffix = ""
else:
    prefix = f"Loaded: "
    suffix = f" +{len(model_names) - 1} more"
    warning_lines = [
        "Warning: Multiple ollama models loaded",
        "Game performance may be compromised"
    ]

# Remaining space for the model name (including newline and prefix/suffix) because 128 max chars
reserved = len("\n".join(tooltip_lines + warning_lines)) + len(prefix) + len(suffix) + 1  # +1 for newline
max_model_len = 128 - reserved
model_name = model_names[0]
if len(model_name) > max_model_len:
    model_name = model_name[:max_model_len - 3] + "..."

tooltip_lines.append(f"{prefix}{model_name}{suffix}")
tooltip_lines += warning_lines

tooltip_text = "\n".join(tooltip_lines)

tray_icon = Icon("NMS_DynamicSuitVoice", img, tooltip_text, menu)

# Start your watcher
watcher = threading.Thread(target=watch_wems, daemon=True)
watcher.start()

# Run the icon (blocks until user chooses Quit).
tray_icon.run()
