import os
import csv
from pathlib import Path
from dotenv import load_dotenv
import time
from extras.prompting import CategoryPrompts
import lmstudio as lms
from openai import OpenAI
import json
import re

SERVER_API_HOST = "localhost:1234"
lms.configure_default_client(SERVER_API_HOST)
# Load model (do this once at startup)
xmodel = lms.llm("lmstudio-community/qwen3-0.6b")
xclient = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")
# Load .env from the local subdirectory
load_dotenv(dotenv_path=Path(__file__).parent / "suit_voice.env")
CSV_PATH = Path(os.getenv("CSV_PATH"))
TEST_OUTPUT_CSV = Path(os.getenv("TEST_OUTPUT_CSV"))
START_ROW = 0  # inclusive.  starts at 0.
END_ROW = 220   # exclusive. going past the end effectively skips nonexistent lines.
SUIT_VOICE_PROMPT_PATH = Path(os.getenv("TEST_VOICE_PROMPT_PATH"))
with open(SUIT_VOICE_PROMPT_PATH, encoding="utf-8") as f:
    SUIT_VOICE_PROMPT = f.read()
category_prompts = CategoryPrompts()
TOKENIZED_BANLIST_PATH = Path(os.getenv("TOKENIZED_BANLIST_PATH"))
with open(TOKENIZED_BANLIST_PATH, encoding="utf-8") as f:
    LOGIT_BANLIST = json.load(f)


def reword_phrase(wem_id_r: str,
                  original_phrase_r: str,
                  intent_r: str,
                  category_r):

    category_context = category_prompts.get_prompt(category_r)

    system_prompt = SUIT_VOICE_PROMPT.format(
        category_type=category_r.strip(),
        input_intent=intent_r.strip(),
        input_phrase=original_phrase_r.strip(),
        category_context=category_context.strip()
    )
    # system_prompt += "Output the reworded phrase only, then write <END> to signal completion."
    # print(f"Composed System Prompt:\n {system_prompt}")
    logit_bias = {**LOGIT_BANLIST.get(category_r, {}), **LOGIT_BANLIST.get("default", {})}
    chat = lms.Chat(system_prompt)
    max_retries = 3
    for attempt in range(max_retries):
        try:

            with lms.Client() as client:
                model = client.llm.model()
                result = model.respond(chat, config={
                    "temperature": 0.6,
                    "maxTokens": 50,
                })
            print(f"ChatResult:\n{result}")

            return result

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                print(f"LLM ERROR on WEM {wem_id_r}: {e}")
                return f"WEM ERROR {wem_id_r}, {e}. {original_phrase_r}"
    return original_phrase_r



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


intent_map = load_intent_map(CSV_PATH)
# output_rows = process_by_row_range(intent_map, START_ROW, END_ROW)
output_rows = process_by_category(intent_map, "Monetary Transaction")

"""
Cold Temperature
Discovery
Energy Shield
Environmental Status
Equipment Status
Extreme Temperature
Freighter Combat
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
