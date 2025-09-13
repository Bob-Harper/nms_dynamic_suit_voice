import os
import re
import csv
import time
import shutil
import threading
import subprocess
from PIL import Image
from pathlib import Path
from pystray import Icon, Menu, MenuItem
from modular.load_env import SuitVoiceConfig
# Load .env vars from load_env.py
config = SuitVoiceConfig()

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

                i_intent_map[wem_number] = {
                    "Transcription": original_phrase,
                    "Category": category,
                    "Intent": intent,
                    "Context": context,
                    }
    except Exception as e1:
        print(f"Error loading intent map: {e1}")
    return i_intent_map


def create_logit_bias(category_l):
    logit_bias = {
        **extract_token_ids(config.logit_banlist.get(category_l, {})),
        **extract_token_ids(config.logit_banlist.get("Default", {})),
    }  # add more categorys like Encoraged or Discouraged if needed, use Default as template
    return logit_bias


def extract_token_ids(data: dict):
    """Flatten token dict and ignore non-integer keys like 'bias'."""
    return {int(k): v for k, v in data.get("tokens", {}).items()}


def build_suit_prompt(category, intent, phrase, wordiness_level="Standard", tone="Standard"):
    # Get base category context (Default fallback)
    category_context = config.promptbuilder.get(category, config.promptbuilder.get("Default", ""))

    # Get wordiness instruction
    wordiness_prompt = config.promptbuilder.get("wordiness", {}).get(wordiness_level, "")

    # Get tone instruction
    tone_prompt = config.promptbuilder.get("tones", {}).get(tone, "")
    # print(f"category_context:\n{category_context}\n\nwordiness_prompt\n{wordiness_prompt}\n\ntone_prompt:\n {tone_prompt}")

    # Specific categories require very different prompting to prevent breaking imersion
    mil_cat = ["Missile Launch", "Missile Destroyed", "Freighter Escape", "Freighter Combat"]
    if category in mil_cat:
        system_prompt = config.suit_voice_combat
    else:
        system_prompt = config.suit_voice_base

    # Compose system prompt from the base text file and inject wordiness + tone
    system_prompt += config.suit_voice_dynamic.format(
        category_type=category.strip(),
        input_intent=intent.strip(),
        input_phrase=phrase.strip(),
        category_context=category_context.strip(),
        wordiness_prompt=wordiness_prompt.strip(),
        tone_prompt=tone_prompt.strip()
    )

    return system_prompt


def reword_phrase(wem_id_r,
                  category_r,
                  original_phrase_r,
                  finalprompt):

    logit_bias_list = create_logit_bias(category_r)

    # Build the full messages payload
    messages = [{"role": "system", "content": finalprompt}]
    # print(f"Output:\n {messages}")
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"Raw Input:\n {messages}")
            output = config.llm.create_chat_completion(
                messages=messages,
                max_tokens=2048,
                temperature=0.8,
                top_k=90,
                top_p=0.9,
                repeat_penalty=1.25,
                logit_bias=logit_bias_list,
                seed=-1
            )
            print(f"Raw Output:\n {output}")
            result = output["choices"][0]["message"]["content"].strip()
            # print(f"Output:\n {result}")
            result = postprocess_for_tts(result)

            return result

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                print(f"LLM ERROR on WEM {wem_id_r}: {e}")
                return f"WEM ERROR {wem_id_r}, {e}. {original_phrase_r}"

    return original_phrase_r


def postprocess_for_tts(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"[—–]", ", ", text)  # handle em-dash and en-dash
    text = re.sub(r"interlooper", "Interloper", text, flags=re.IGNORECASE)
    text = re.sub(r"interlopper", "Interloper", text, flags=re.IGNORECASE)
    return text.strip()


def run_tts(text: str, wem_num: str, gain_db: float = 5.0) -> Path:
    final_wav = config.temp_wem_dir / f"{wem_num}.wav"
    temp_wav = final_wav.with_suffix(".temp.wav")
    embed_dir = r"C:\NMS_SUIT_VOICE\embeds"
    ref_wav_dir = os.path.join(embed_dir, "reference")
    gain_db = 5
    atempo = 1.05
    rate = 0.5
    asetrate = int(44100 * rate)
    speaker_wav = ["base_extended.wav"]  # "amused.wav",
    speaker_wav_path = [os.path.join(ref_wav_dir, w) for w in speaker_wav]
    config.tts_model.tts_to_file(text=text,
                          speaker_wav=speaker_wav_path,
                          file_path=str(final_wav)
                          )  # to clone voice add this and enable the speaker stuff speaker_wav=speaker_wav_path,
    if gain_db and gain_db != 0:
        subprocess.run([
            "ffmpeg", "-hide_banner", "-y",
            "-i", str(final_wav),
            "-af", f"volume={gain_db}dB,atempo={atempo},asetrate={asetrate}",
            str(temp_wav)
        ], check=True, creationflags=config.create_no_window)
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
        str(config.cmd_script_path.resolve()),  # make sure the CMD script path is absolute too
        f'--conversion:{conversion_quality}',
        f'--out:{str(output_dir)}',
        str(wav_file_path)
    ], check=True, creationflags=config.create_no_window)

    print(f"Conversion attempt complete for {wav_file_path.name}")


def watch_wems():
    # Initialize access times for all .wav files in the directory
    access_times = {f3: f3.stat().st_atime for f3 in config.mod_dir.glob("*.wem")}
    print("Watching for file access...")
    while RUNNING:

        for f3 in config.mod_dir.glob("*.wem"):
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
                        wordiness_level = "Default"
                        tone = "Philosophical"
                        finalprompt = build_suit_prompt(category, intent_w, original_phrase_w, wordiness_level, tone)

                        reworded = reword_phrase(wem_id, original_phrase_w, intent_w, finalprompt)
                        if config.logging:
                            fieldnames = ["WEM number", "Category", "Original", "Intent Phrase", "Context",
                                          "Final Voice Line"]
                            file_exists = Path(config.game_output_csv).exists()

                            log_entry = {
                                "WEM number": wem_id,
                                "Category": category if wem_id in intent_map else "",
                                "Original": original_phrase_w if wem_id in intent_map else "",
                                "Intent Phrase": intent_w if wem_id in intent_map else "",
                                "Context": context if wem_id in intent_map else "",
                                "Final Voice Line": reworded
                            }

                            with open(config.game_output_csv, "a", newline='', encoding='utf-8') as outfile:
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
                            convert_to_wem(wav_path, config.temp_wem_dir)
                            # print("Conversion to WEM complete")
                        except Exception as e3:
                            print(f"Error converting to WEM: {e3}")
                            continue
                        temp_wem_path = config.temp_wem_dir / f"{wem_id}.wem"
                        final_wem_path = config.mod_dir / f"{wem_id}.wem"

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

                        new_wem = config.mod_dir / f"{wem_id}.wem"
                        if new_wem.exists():
                            access_times[new_wem] = new_wem.stat().st_atime
                    else:
                        print(f"No intent found for WEM ID {wem_id}, skipping.")

            except Exception as e3:
                print(f"Error handling {f3.name}: {e3}")

        time.sleep(config.check_interval)


def shutdown():
    global RUNNING
    RUNNING = False
    tray_icon.stop()


def on_quit(_icon, _item):
    shutdown()


intent_map = load_intent_map(config.csv_path)

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

tooltip_text = "NMS DynamicSuitVoice"

tray_icon = Icon("NMS_DynamicSuitVoice", img, tooltip_text, menu)

# Start your watcher
watcher = threading.Thread(target=watch_wems, daemon=True)
watcher.start()

# Run the icon (blocks until user chooses Quit).
tray_icon.run()

# to do: break up into classes/files.  more modular.  postprocessing.py, generate.py
# tray_icon.py and leave the watchdog in here. modular, easier to maintain, futureproof, add on.
