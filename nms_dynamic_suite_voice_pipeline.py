import os
import re
import csv
import time
import shutil
import subprocess
from pathlib import Path
from modular.tray_ui import TrayUI
from modular.tts_utils import run_tts
from modular.config import SuitVoiceConfig
config = SuitVoiceConfig()


def create_logit_bias(category_l):
    logit_bias = {
        **extract_token_ids(config.logit_banlist.get(category_l, {})),
        **extract_token_ids(config.logit_banlist.get("Default", {})),
    }  # to add more categorys like Encouraged or Discouraged with different scores use Default as template
    return logit_bias


def extract_token_ids(data: dict):
    """Flatten token dict and ignore non-integer keys like 'bias'."""
    return {int(k): v for k, v in data.get("tokens", {}).items()}


# In your prompt builder module
def build_suit_prompt(config, category, intent, phrase, wordiness_level=None, tone=None):
    # fallback to config's current values if not explicitly passed
    wordiness_level = wordiness_level or config.current_wordiness
    tone = tone or config.current_tone

    category_context = config.promptbuilder.get(category, config.promptbuilder.get("Default", ""))

    if category in config.mil_cat:
        system_prompt = config.suit_voice_combat
        wordiness_prompt = "Observer"
    else:
        system_prompt = config.suit_voice_base
        wordiness_prompt = config.promptbuilder.get("wordiness", {}).get(wordiness_level, "")

    tone_prompt = config.promptbuilder.get("tones", {}).get(tone, "")

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

    # enforce usage or avoidance of specific tokens using logits
    logit_bias_list = create_logit_bias(category_r)

    messages = [{"role": "system", "content": finalprompt}]
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # print(f"Raw Input:\n {messages}")
            output = config.llm.create_chat_completion(
                messages=messages,
                max_tokens=2048,  # less can be faster but can cut off thinking, breaking the result
                temperature=0.8,
                top_k=90,
                top_p=0.9,
                repeat_penalty=1.25,
                logit_bias=logit_bias_list,
                seed=-1  # must add this to randomize the results
            )
            # print(f"Raw Output:\n {output}")
            result = output["choices"][0]["message"]["content"].strip()
            result = postprocess_for_tts(result)
            return result

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                print(f"LLM ERROR on WEM {wem_id_r}: {e}")
                return f"WEM ERROR {wem_id_r}, {e}. {original_phrase_r}"
    print(f"ERROR on WEM {wem_id_r}")
    return f"External Reality Failure. {original_phrase_r}"


def postprocess_for_tts(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)  # Strip Thinking before sending to TTS
    text = re.sub(r"[—–]", ", ", text)  # convert em-dash and en-dash combo that the model likes to use
    return text.strip()


def convert_to_wem(wav_file_path: Path, output_dir: Path, conversion_quality="Vorbis Quality High"):
    # Resolve both input and output paths to absolute to ensure sound2wem has no issues
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


def watch_wems(tray_ui):  # Main watchdog and pipeline
    access_times = {f3: f3.stat().st_atime for f3 in tray_ui.config.mod_dir.glob("*.wem")}
    print("Watching for file access...")
    while tray_ui.running:
        for f3 in config.mod_dir.glob("*.wem"):
            try:
                current_atime = f3.stat().st_atime
                if current_atime != access_times.get(f3, 0):
                    wem_id = f3.stem  # Extract ID from filename (without extension)
                    print(f"Access detected: {f3.name} (ID: {wem_id})")

                    if wem_id in config.intent_map:
                        intent_entry = config.intent_map[wem_id]
                        original_phrase_w = intent_entry["Transcription"]
                        category = intent_entry["Category"]
                        intent_w = intent_entry["Intent"]
                        context = intent_entry["Context"]

                        # pass the same config object the tray is updating
                        finalprompt = build_suit_prompt(config, category, intent_w, original_phrase_w)

                        reworded = reword_phrase(wem_id, original_phrase_w, intent_w, finalprompt)
                        if config.logging:
                            fieldnames = ["WEM number", "Category", "Original", "Intent Phrase", "Context",
                                          "Final Voice Line"]
                            file_exists = Path(config.game_output_csv).exists()

                            log_entry = {
                                "WEM number": wem_id,
                                "Category": category if wem_id in config.intent_map else "",
                                "Original": original_phrase_w if wem_id in config.intent_map else "",
                                "Intent Phrase": intent_w if wem_id in config.intent_map else "",
                                "Context": context if wem_id in config.intent_map else "",
                                "Final Voice Line": reworded
                            }

                            with open(config.game_output_csv, "a", newline='', encoding='utf-8') as outfile:
                                writer = csv.DictWriter(outfile, fieldnames=fieldnames)
                                if not file_exists:
                                    writer.writeheader()
                                writer.writerow(log_entry)
                        try:
                            wav_path = run_tts(config, reworded, wem_id)
                        except Exception as e3:
                            print(f"Error creating WAV: {e3}")
                            continue

                        try:
                            convert_to_wem(wav_path, config.temp_wem_dir)
                        except Exception as e3:
                            print(f"Error converting to WEM: {e3}")
                            continue

                        temp_wem_path = config.temp_wem_dir / f"{wem_id}.wem"
                        final_wem_path = config.mod_dir / f"{wem_id}.wem"

                        for attempt in range(40):
                            try:
                                shutil.move(str(temp_wem_path), str(final_wem_path))
                                break
                            except PermissionError:
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

if __name__ == "__main__":
    tray_ui = TrayUI(config, watch_wems)
    watch_wems(tray_ui)

