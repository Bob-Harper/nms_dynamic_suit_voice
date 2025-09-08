import csv
import re
from pathlib import Path
import time
from modular.load_env import SuitVoiceConfig
import random

# Load .env vars from load_env.py
config = SuitVoiceConfig()
START_ROW = 0  # inclusive.  starts at 0.
END_ROW = 220   # exclusive. going past the end effectively skips nonexistent lines.


def reword_phrase(wem_id_r: str,
                  original_phrase_r: str,
                  intent_r: str,
                  category_r):

    category_context = config.category_prompts.get_prompt(category_r)

    system_prompt = config.suit_voice_prompt.format(
        category_type=category_r.strip(),
        input_intent=intent_r.strip(),
        input_phrase=original_phrase_r.strip(),
        category_context=category_context.strip()
    )
    # print(f"Composed System Prompt:\n {system_prompt}")
    logit_bias = {**config.logit_banlist.get(category_r, {})
                  , **config.logit_banlist.get("Default", {})
                  , **config.logit_banlist.get("Thinking", {})}
    max_retries = 3
    for attempt in range(max_retries):
        try:
            output = config.llm.create_chat_completion(
                messages=[  # type: ignore
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": original_phrase_r},
                ],
                max_tokens=768,
                temperature=0.8,
                top_k=90,
                top_p=0.9,
                logit_bias=logit_bias,
                seed=-1
            )

            result = output["choices"][0]["message"]["content"].strip()
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
    text = re.sub(r"[—–]", " - ", text)  # handle em-dash and en-dash
    return text.strip()


def process_entry(wem_id, entry):
    """Shared processing of a single intent-map entry."""
    category = entry["Category"]
    original_phrase = entry["Transcription"]
    intent = entry["Intent"]

    start_time = time.time()

    try:
        reworded = reword_phrase(
            wem_id,
            original_phrase,
            intent,
            category,
        )
        print(f"\nWEM: {wem_id} -- Original Game Wording: {original_phrase}")
        print(f"\033[92mFinal Output: {reworded}\033[0m")
    except Exception as e:
        print(f"LLM ERROR on WEM {wem_id}: {e}")
        reworded = f"WEM ERROR {wem_id}.  {original_phrase}"

    end_time = time.time()
    elapsed = end_time - start_time
    print(f"Processing time for WEM {wem_id}: {elapsed:.2f} seconds")

    return wem_id, reworded


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


def process_by_row_range(intent_mapr, start_row, end_row):
    output_rows_r = []
    for idx, (wem_id, entry) in enumerate(intent_mapr.items()):
        if idx < start_row:
            continue
        if idx >= end_row:
            break
        output_rows_r.append(process_entry(wem_id, entry))
    return output_rows_r


def process_by_category(intent_mapp, target_category):
    output_rows_c = []
    for wem_id, entry in intent_mapp.items():
        if entry["Category"] != target_category:
            continue
        output_rows_c.append(process_entry(wem_id, entry))
    return output_rows_c


intent_map = load_intent_map(config.csv_path)
# output_rows = process_by_row_range(intent_map, START_ROW, END_ROW)
output_rows = process_by_category(intent_map, "Freighter Escapethat")

"""
Cold Temperature
Discovery
Energy Shield
Environmental Status
Equipment Status
Extreme Temperature
Freighter Combat
Missile Launch
Freighter Escape
Missile Destroyed
Hot Temperature
Inventory
Life Support
Monetary Transaction
Navigation
Notification
Oxygen Level
Personal Combat
Personal Protection
Protection from Environment
Radiation Exposure
REFERENCE
Starship Combat
Starship Movement
Toxic Environment
Vehicle Readiness
Vehicle Status
Debugging
"""

"""
model
prompt
best_of


"""
