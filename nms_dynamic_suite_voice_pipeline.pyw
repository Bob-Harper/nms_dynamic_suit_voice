from pystray import Icon, Menu, MenuItem
from PIL import Image
import threading
import time
import csv
import subprocess
from pathlib import Path
from dotenv import load_dotenv
import os
import json
import shutil
from TTS.api import TTS  # coqui-tts fork, pinned in requirements, uses TTS name for compatibility
import sys
from extras.prompting import CategoryPrompts
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers import LogitsProcessor, LogitsProcessorList

# Setup once globally at start.  pick an HF model name or point it at a local model file if you already have one.
MODEL_NAME = "Qwen/Qwen3-0.6B"  # base model no quantizing etc.  quants happen at runtime for now.

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype="auto",
    device_map="auto",
)
# Load .env from the local subdirectorylogits_bias
load_dotenv(dotenv_path=Path(__file__).parent / "suit_voice.env")
CHECK_INTERVAL = float(os.getenv("CHECK_INTERVAL"))
MOD_DIR = Path(os.getenv("MOD_DIR").strip('"'))
CSV_PATH = Path(os.getenv("CSV_PATH"))
TEMP_WEM_DIR = Path(os.getenv("TEMP_WEM_DIR").strip('"'))
TEMP_WEM_DIR.mkdir(parents=True, exist_ok=True)
CMD_SCRIPT_PATH = Path(os.getenv("CMD_SCRIPT_PATH").strip('"'))
try:
    TTS_MODEL = os.getenv("TTS_MODEL")
    if not TTS_MODEL:
        raise ValueError("TTS_MODEL not set in environment")
    tts_model = TTS(model_name=TTS_MODEL)
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
TOKENIZED_BANLIST_PATH = Path(os.getenv("TOKENIZED_BANLIST_PATH"))  # re-implementing. DO NOT REMOVE
with open(TOKENIZED_BANLIST_PATH, encoding="utf-8") as f:
    raw_bias = json.load(f)
LOGIT_BANLIST = {k: {int(tid): v for tid, v in d.items()} for k, d in raw_bias.items()}

RUNNING = True


class LogitBiasProcessor(LogitsProcessor):
    def __init__(self, bias_map: dict):
        self.bias_map = bias_map

    def __call__(self, input_ids, scores):
        for token_id, bias in self.bias_map.items():
            scores[0, token_id] += bias
        return scores


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

                i_intent_map[wem_number] = {
                    "Transcription": original_phrase,
                    "Category": category,
                    "Intent": intent,
                    "Context": context,
                    }
    except Exception as e1:
        print(f"Error loading intent map: {e1}")
    return i_intent_map


def reword_phrase(original_phrase_r, intent_r, category_r):
    category_context = category_prompts.get_prompt(category_r)

    # retrieve logits for this category + defaults
    logit_bias = {**LOGIT_BANLIST.get(category_r, {}), **LOGIT_BANLIST.get("default", {})}

    prompt = SUIT_VOICE_PROMPT.format(
        category_type=category_r.strip(),
        input_intent=intent_r.strip(),
        input_phrase=original_phrase_r.strip(),
        category_context=category_context.strip()
    )
    messages = [{"role": "user", "content": prompt}]
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=True
    )
    model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

    # add the logits processor here
    logits_processor = LogitsProcessorList([
        LogitBiasProcessor(logit_bias)
    ])

    generated_ids = model.generate(
        **model_inputs,
        max_new_tokens=1024,
        temperature=0.7,
        top_k=90,
        top_p=0.9,
        logits_processor=logits_processor,   # <--- THIS IS NEW
    )
    output_ids = generated_ids[0][len(model_inputs.input_ids[0]):].tolist()

    try:
        index = len(output_ids) - output_ids[::-1].index(151668)
    except ValueError:
        index = 0

    thinking_content = tokenizer.decode(output_ids[:index], skip_special_tokens=True).strip("\n")
    final_output = tokenizer.decode(output_ids[index:], skip_special_tokens=True).strip("\n")

    return thinking_content, final_output


def run_tts(text: str, wem_num: str, gain_db: float = 5.0) -> Path:
    final_wav = TEMP_WEM_DIR / f"{wem_num}.wav"
    temp_wav = final_wav.with_suffix(".temp.wav")
    embed_dir = r"C:\NMS_SUIT_VOICE\embeds"
    ref_wav_dir = os.path.join(embed_dir, "reference")
    gain_db = 5
    atempo = 1.05
    rate = 0.5
    asetrate = int(44100 * rate)
    speaker_wav = ["amused.wav"]  # "amused.wav",
    speaker_wav_path = [os.path.join(ref_wav_dir, w) for w in speaker_wav]
    tts_model.tts_to_file(text=text,
                          speaker_wav=speaker_wav_path,
                          file_path=str(final_wav)
                          )  # to clone voice add this and enable the speaker stuff speaker_wav=speaker_wav_path,
    if gain_db and gain_db != 0:
        subprocess.run([
            "ffmpeg", "-hide_banner", "-y",
            "-i", str(final_wav),
            "-af", f"volume={gain_db}dB,atempo={atempo},asetrate={asetrate}",
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
                        intent_w = intent_entry["Intent"]
                        context = intent_entry["Context"]
                        cot, reworded = reword_phrase(original_phrase_w, intent_w, category)
                        if LOGGING:
                            fieldnames = ["WEM number", "Category", "Original", "Intent Phrase", "Context", "Chain Of Thought", "Final Voice Line"]
                            file_exists = Path(GAME_OUTPUT_CSV).exists()

                            log_entry = {
                                "WEM number": wem_id,
                                "Category": category if wem_id in intent_map else "",
                                "Original": original_phrase_w if wem_id in intent_map else "",
                                "Intent Phrase": intent_w if wem_id in intent_map else "",
                                "Context": context if wem_id in intent_map else "",
                                "Chain Of Thought": cot,
                                "Final Voice Line": reworded
                            }

                            with open(GAME_OUTPUT_CSV, "a", newline='', encoding='utf-8') as outfile:
                                writer = csv.DictWriter(outfile, fieldnames=fieldnames)
                                if not file_exists:
                                    writer.writeheader()
                                writer.writerow(log_entry)

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

tooltip_text = ["NMS DynamicSuitVoice"]

tray_icon = Icon("NMS_DynamicSuitVoice", img, tooltip_text, menu)

# Start your watcher
watcher = threading.Thread(target=watch_wems, daemon=True)
watcher.start()

# Run the icon (blocks until user chooses Quit).
tray_icon.run()

# to do: break up into classes/files.  more modulare.  postprocessing.py, generate.py
# tray_icon.py and leave the watchdog in here. modular, easier to maintain, futureproof, add on.
