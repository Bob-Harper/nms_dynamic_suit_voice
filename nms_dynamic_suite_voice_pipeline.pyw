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
from TTS.api import TTS  # coqui-tts fork, pinned in requirements, uses TTS name for compatibility
import sys
import re
import requests
import random
from ollama import Client
from extras.prompting import CategoryPrompts
import json

# Load .env from the local subdirectory
load_dotenv(dotenv_path=Path(__file__).parent / "suit_voice.env")
CHECK_INTERVAL = float(os.getenv("CHECK_INTERVAL"))
MOD_DIR = Path(os.getenv("MOD_DIR").strip('"'))
CSV_PATH = Path(os.getenv("CSV_PATH"))
TEMP_WEM_DIR = Path(os.getenv("TEMP_WEM_DIR").strip('"'))
TEMP_WEM_DIR.mkdir(parents=True, exist_ok=True)
CMD_SCRIPT_PATH = Path(os.getenv("CMD_SCRIPT_PATH").strip('"'))
OLLAMA_SERVER = os.getenv("OLLAMA_SERVER")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
try:
    TTS_MODEL = os.getenv("TTS_MODEL")
    if not TTS_MODEL:
        raise ValueError("TTS_MODEL not set in environment")
    tts_model = TTS(model_name=TTS_MODEL)
    # tts_model.to("cuda")
except Exception as e0:
    raise SystemExit(f"Failed to load TTS model: {e0}")

ffmpeg_path = shutil.which("ffmpeg")
if not ffmpeg_path:
    ffmpeg_env = os.getenv("FFMPEG_PATH")
    if ffmpeg_env:
        ffmpeg_path = Path(ffmpeg_env.strip('"'))
        os.environ["PATH"] = str(ffmpeg_path.parent) + ";" + os.environ.get("PATH", "")
    else:
        raise SystemExit("ffmpeg not found on PATH and FFMPEG_PATH not set in .env")    
ICON_IMAGE = Path(os.getenv("ICON_IMAGE"))
LOGGING = os.getenv("LOGGING", "false").strip().lower() == "true"  # force boolean: true, anything else => False
GAME_OUTPUT_CSV = Path(os.getenv("GAME_OUTPUT_CSV"))
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0
SUIT_VOICE_PROMPT_PATH = Path(os.getenv("SUIT_VOICE_PROMPT_PATH"))
with open(SUIT_VOICE_PROMPT_PATH, encoding="utf-8") as f:
    SUIT_VOICE_PROMPT = f.read()
category_prompts = CategoryPrompts()
TOKENIZED_BANLIST_PATH = Path(os.getenv("TOKENIZED_BANLIST_PATH"))
with open(TOKENIZED_BANLIST_PATH, encoding="utf-8") as f:
    LOGIT_BANLIST = json.load(f)
RUNNING = True


def load_intent_map(csv_path: Path) -> dict:
    i_intent_map = {}
    try:
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                wem_number = (row.get('WEM_number') or '').strip()
                original_phrase = (row.get('Transcription') or '').strip()
                category = (row.get('Category') or '').strip()
                intent = (row.get('Intent') or '').strip()
                context = (row.get('Context') or '').strip()
                thinking = (row.get('No_Thinking') or '').strip()

                i_intent_map[wem_number] = {
                    "Transcription": original_phrase,
                    "Category": category,
                    "Intent": intent,
                    "Context": context,
                    "No_Thinking": thinking,
                    }
    except Exception as e1:
        print(f"Error loading intent map: {e1}")
    return i_intent_map

def reword_phrase(wem_id_r: str,
                  original_phrase_r: str,
                  intent_r: str,
                  category_r,
                  no_thinking_r,
                  ) -> str:

    prompt = ""
    if no_thinking_r:  # Only prepend /no_think if THERE IS A VALUE IN THE COLUMN
        prompt = "/no_think "
    category_context = category_prompts.get_prompt(category_r)
    logit_bias = {**LOGIT_BANLIST.get(category_r, {}), **LOGIT_BANLIST.get("default", {})}
    prompt += SUIT_VOICE_PROMPT.format(category_type=category_r.strip(), input_intent=intent_r.strip(),
                                       input_phrase=original_phrase_r.strip(), category_context=category_context.strip())
    # print(f"{prompt}")
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "max_tokens": 20,
            "temperature": 0.7,
            "top_k": 90,
            "top_p": 0.9,
            "seed": random.randint(1, 9999999),  # or pass as an argument
            "logit_bias": logit_bias
        }
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(f"{OLLAMA_SERVER}/api/generate", json=payload, timeout=30)
            response.raise_for_status()
            generated_response = response.json().get("response", "")
            if not generated_response:
                raise ValueError("Empty response from Ollama")
            # full_response = generated_response
            # print(f"\nWEM {wem_id_w} -- Full response with thinking tags if included: \n{full_response}")
            generated_response = re.sub(r"<think>.*?</think>", "", generated_response, flags=re.DOTALL).strip()

            generated_response = tts_llm_scrubber(generated_response)
            return generated_response
        except Exception as e2:
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                print(f"LLM ERROR on WEM {wem_id_r}: {e2}")
                return f"External Reality alert, {attempt} attempts made.  {original_phrase_r}"

    # Safety fallback
    return f"{original_phrase_r}. External Reality alert, error detected"


def run_tts(text: str, wem_num: str, gain_db: float = 5.0) -> Path:
    final_wav = TEMP_WEM_DIR / f"{wem_num}.wav"
    temp_wav = final_wav.with_suffix(".temp.wav")
    # embed_dir = r"C:\NMS_SUIT_VOICE\embeds"
    # ref_wav_dir = os.path.join(embed_dir, "reference")
    gain_db = 5
    # # atempo = 1.05
    # # rate = 0.5
    # # asetrate = int(44100 * rate)
    # speaker_wav = []  # "amused.wav",
    # speaker_wav_path = [os.path.join(ref_wav_dir, w) for w in speaker_wav]
    tts_model.tts_to_file(text=text,
                          file_path=str(final_wav)
                          )  # to clone voice add this and enable the speaker stuff speaker_wav=speaker_wav_path,
    if gain_db and gain_db != 0:
        subprocess.run([
            "ffmpeg", "-hide_banner", "-y",
            "-i", str(final_wav),
            "-af", f"volume={gain_db}dB",
            str(temp_wav)
        ], check=True, creationflags=CREATE_NO_WINDOW)
        # "-af", f"volume={gain_db}dB,atempo={atempo},asetrate={asetrate}",

        temp_wav.replace(final_wav)

    if not final_wav.exists():
        raise FileNotFoundError(f"TTS output WAV not found: {final_wav}")

    # print(f"Generated WAV: {final_wav}")
    return final_wav


def convert_to_wem(wav_file_path: Path, output_dir: Path, conversion_quality="Vorbis Quality High"):
    # Resolve both input and output paths to absolute
    wav_file_path = wav_file_path.resolve()
    output_dir = output_dir.resolve()

    subprocess.run([
        "cmd.exe", "/c",
        str(CMD_SCRIPT_PATH.resolve()),  # make sure the CMD script path is absolute too
        f'--conversion:{conversion_quality}',
        f'--out:{str(output_dir)}',
        str(wav_file_path)
    ], check=True, creationflags=CREATE_NO_WINDOW)

    print(f"Conversion attempt complete for {wav_file_path.name}")


def tts_llm_scrubber(text: str) -> str:
    """
    Normalize text for TTS:
    - lowercase everything
    - replace first-person/team pronouns with 'you' or 'your'
    - collapse spaces
    """
    text = text.lower()

    replacements = {
        r"\byou're\b": "you are",
        r"\bi\b": "you",
        r"\bmy\b": "your",
        r"\bwe\b": "you",
        r"\bours\b": "your",
        r"\bus\b": "you",
        r"\bme\b": "you",
        r"\bi'm\b": "you",
        r"\bi am\b": "you",
        r"\bi've\b": "you",
        r"\bi'll\b": "you",
        r"\bthe user's\b": "your",
        r"\bthe user\b": "you",
        r"\bthe pilot's\b": "your",
        r"\bthe pilot\b": "you",
        r"\bthe wearer's\b": "your",
        r"\bthe wearer\b": "you",
        r"\b—\b": ", ",
        r"\bheat\b": "heet",
        r"\byou's\b": "your",
    }

    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text)

    text = re.sub(r"\s+", " ", text).strip()
    return text


def watch_wems():
    # Initialize access times for all .wav files in the directory
    access_times = {f3: f3.stat().st_atime for f3 in MOD_DIR.glob("*.wem")}
    print("Watching for file access...")
    while RUNNING:

        for f3 in MOD_DIR.glob("*.wem"):
            try:
                current_atime = f3.stat().st_atime
                if current_atime != access_times.get(f3, 0):
                    wem_id = f3.stem  # Extract ID from filename (without extension)
                    print(f"Access detected: {f3.name} (ID: {wem_id})")

                    if wem_id in intent_map:
                        intent_entry = intent_map[wem_id]
                        original_phrase_w = intent_entry["Transcription"]
                        category = intent_entry["Category"]
                        no_thinking_w = intent_entry["No_Thinking"]
                        intent_w = intent_entry["Intent"]
                        context = intent_entry["Context"]
                        reworded = reword_phrase(wem_id, original_phrase_w, intent_w, category, no_thinking_w)
                        if LOGGING:
                            fieldnames = ["WEM number", "Category", "Original", "Intent Phrase", "Context", "Final Voice Line"]
                            file_exists = Path(GAME_OUTPUT_CSV).exists()

                            log_entry = {
                                "WEM number": wem_id,
                                "Category": category if wem_id in intent_map else "",
                                "Original": original_phrase_w if wem_id in intent_map else "",
                                "Intent Phrase": intent_w if wem_id in intent_map else "",
                                "Context": context if wem_id in intent_map else "",
                                "Final Voice Line": reworded
                            }

                            with open(GAME_OUTPUT_CSV, "a", newline='', encoding='utf-8') as outfile:
                                writer = csv.DictWriter(outfile, fieldnames=fieldnames)
                                if not file_exists:
                                    writer.writeheader()
                                writer.writerow(log_entry)

                            # print(f"Appended output for review in {GAME_OUTPUT_CSV}")

                        # print("Calling run_tts...")
                        try:
                            wav_path = run_tts(reworded, wem_id)
                            # print(f"WAV created at {wav_path}")
                        except Exception as e3:
                            print(f"Error creating WAV: {e3}")
                            continue

                        # print("Calling convert_to_wem...")
                        try:
                            convert_to_wem(wav_path, TEMP_WEM_DIR)
                            # print("Conversion to WEM complete")
                        except Exception as e3:
                            print(f"Error converting to WEM: {e3}")
                            continue
                        temp_wem_path = TEMP_WEM_DIR / f"{wem_id}.wem"
                        final_wem_path = MOD_DIR / f"{wem_id}.wem"

                        for attempt in range(40):
                            try:
                                shutil.move(str(temp_wem_path), str(final_wem_path))
                                # print(f"WEM moved successfully: {final_wem_path}")
                                break
                            except PermissionError:
                                # print(f"WEM file still in use. Retry {attempt + 1}")
                                time.sleep(0.5)
                            except Exception as e3:
                                print(f"Unexpected error while moving WEM: {e3}")
                                break
                        else:
                            print(f"Failed to move WEM after 20 seconds: {temp_wem_path}")

                        new_wem = MOD_DIR / f"{wem_id}.wem"
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
    try:
        subprocess.run(["ollama", "stop", OLLAMA_MODEL])
    except Exception as e:
        print(f"Warning stopping Ollama model: {e}")
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

# to do: break up into classes/files.  more modulare.  prompting.py, postprocessing.py, generate.py
# tray_icon.py and leave the watchdog in here. modular, easier to maintain, futureproof, add on.
