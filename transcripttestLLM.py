import os
import csv
import requests
import re
import random
from ollama import Client
from pathlib import Path
from dotenv import load_dotenv
import time
from extras.prompting import CategoryPrompts
import json

# CONFIG
# Load .env from the local subdirectory
load_dotenv(dotenv_path=Path(__file__).parent / "suit_voice.env")
CSV_PATH = Path(os.getenv("CSV_PATH"))
OLLAMA_SERVER = os.getenv("OLLAMA_SERVER")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
TEST_OUTPUT_CSV = Path(os.getenv("TEST_OUTPUT_CSV"))
START_ROW = 0  # inclusive.  starts at 0.
END_ROW = 220   # exclusive. going past the end effectively skips nonexistent lines.
client = Client(OLLAMA_SERVER)
SUIT_VOICE_PROMPT_PATH = Path(os.getenv("SUIT_VOICE_PROMPT_PATH"))
with open(SUIT_VOICE_PROMPT_PATH, encoding="utf-8") as f:
    SUIT_VOICE_PROMPT = f.read()
category_prompts = CategoryPrompts()
TOKENIZED_BANLIST_PATH = Path(os.getenv("TOKENIZED_BANLIST_PATH"))
with open(TOKENIZED_BANLIST_PATH, encoding="utf-8") as f:
    LOGIT_BANLIST = json.load(f)


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
    # print(f"{payload}")
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(f"{OLLAMA_SERVER}/api/generate", json=payload, timeout=10)
            response.raise_for_status()
            generated_response = response.json().get("response", "")
            if not generated_response:
                raise ValueError("Empty response from Ollama")
            # full_response = generated_response
            # print(f"\nWEM {wem_id_r} -- Full response with thinking tags if included: \n{full_response}")
            generated_response = re.sub(r"<think>.*?</think>", "", generated_response, flags=re.DOTALL).strip()

            generated_response = tts_llm_scrubber(generated_response)
            return generated_response
        except Exception as e2:
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                print(f"LLM ERROR on WEM {wem_id_r}: {e2}")
                return f"WEM ERROR {wem_id_r}, {e2}.  {original_phrase_r}"

    # Safety fallback
    return f"{original_phrase_r}. External Reality alert, error detected"


def tts_llm_scrubber(text: str) -> str:
    """
    Normalize text for TTS:
    - lowercase everything
    - replace first-person/team pronouns with 'you' or 'your'
    - other text corretions so the TTS pronounces things correctly.
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


def process_entry(wem_id, entry):
    """Shared processing of a single intent-map entry."""
    category = entry["Category"]
    original_phrase = entry["Transcription"]
    intent = entry["Intent"]
    thinking = entry["No_Thinking"]

    try:
        reworded = reword_phrase(
            wem_id,
            original_phrase,
            intent,
            category,
            thinking
        )
        print(f"\nWEM: {wem_id} -- Original Game Wording: {original_phrase}")
        print(f"\033[92mFinal Output: {reworded}\033[0m")
    except Exception as e:
        print(f"LLM ERROR on WEM {wem_id}: {e}")
        reworded = f"WEM ERROR {wem_id}.  {original_phrase}"

    return wem_id, reworded


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
"""
intent_map = load_intent_map(CSV_PATH)
# output_rows = process_by_row_range(intent_map, START_ROW, END_ROW)
output_rows = process_by_category(intent_map, "Monetary Transaction")
