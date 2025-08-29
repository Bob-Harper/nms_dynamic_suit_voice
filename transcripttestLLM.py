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
END_ROW = 22   # exclusive. going past the end effectively skips nonexistent lines.
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
                wem_number = (row.get('WEM number') or '').strip()
                original_phrase_loaded = (row.get('Transcription') or '').strip()
                category_loaded = (row.get('Category') or '').strip()
                intent_loaded = (row.get('Intent') or '').strip()
                context = (row.get('Context') or '').strip()
                thinking_loaded = (row.get('NO_THINKING') or '').strip()
                usage_count = (row.get('Count') or '').strip()

                i_intent_map[wem_number] = {
                    "original_phrase": original_phrase_loaded,
                    "category": category_loaded,
                    "intent": intent_loaded,
                    "context": context,
                    "thinking": thinking_loaded,
                    "count": int(usage_count) if usage_count.isdigit() else 0
                    }
    except Exception as e1:
        print(f"Error loading intent_loaded map: {e1}")
    return i_intent_map


def reword_phrase(intent_data: str,
                  wem_id_w: str,
                  original_phrase_r: str,
                  no_thinking,
                  category_w,
                  ) -> str:

    prompt = ""
    if no_thinking:  # Only prepend /no_think if THERE IS A VALUE IN THE COLUMN
        prompt = "/no_think "
    context = category_prompts.get_prompt(category_w)
    logit_bias = {**LOGIT_BANLIST.get(category_w, {}), **LOGIT_BANLIST.get("default", {})}
    # print(f"\n\n{context}")
    prompt += SUIT_VOICE_PROMPT.format(category=category_w.strip(), intent_data=intent_data.strip(),
                                       context=context.strip(), input_phrase=original_phrase_r.strip())
    # print(f"\n\n{prompt}")
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "max_tokens": 25,
            "temperature": 0.7,
            "top_k": 90,
            "top_p": 0.9,
            "seed": random.randint(1, 9999999),  # or pass as an argument
            "logit_bias": logit_bias
        }
    }
    # print(f"\n\nPayload: {payload}\n")
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(f"{OLLAMA_SERVER}/api/generate", json=payload, timeout=10)
            response.raise_for_status()
            generated_response = response.json().get("response", "").strip()
            if not generated_response:
                raise ValueError("Empty response from Ollama")
            # full_response = generated_response
            # print(f"\nWEM {wem_id_w} -- Full response with thinking tags if included: \n{full_response}")
            generated_response = re.sub(r"<think>.*?</think>",
                                        "",
                                        generated_response,
                                        flags=re.DOTALL
                                        ).strip()
            generated_response = re.sub(r"—",
                                        " - ",
                                        generated_response,
                                        flags=re.DOTALL
                                        ).strip()
            # Postprocess to enforce 'You'
            generated_response = enforce_user_pronouns(generated_response)
            return generated_response
        except Exception as e2:
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                print(f"LLM ERROR on WEM {wem_id_w}: {e2}")
                return f"WEM ERROR {wem_id_w}, {e2}.  {original_phrase_r}"

    # Safety fallback
    return f"{original_phrase_r}. External Reality alert, error detected"


def enforce_user_pronouns(text: str) -> str:
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
    }

    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text)

    text = re.sub(r"\s+", " ", text).strip()
    return text


""" To test individual rows or ranges from csv, uncomment this section and comment out the category test.

# Read intent map (already cleaned and ready)
intent_map = load_intent_map(CSV_PATH)
output_rows = []

for idx, (wem_id, entry) in enumerate(intent_map.items()):
    if idx < START_ROW:
        continue
    if idx >= END_ROW:
        break
"""
"""
 
,  Vehicle Readiness,  Vehicle Status
"""
# Pick a category to process
TARGET_CATEGORY = "Vehicle Readiness"  # replace with your desired category

# Read intent map (already cleaned and ready)
intent_map = load_intent_map(CSV_PATH)
output_rows = []

for idx, (wem_id, entry) in enumerate(intent_map.items()):
    # Skip rows that don't match the target category
    if entry["category"] != TARGET_CATEGORY:
        continue

    original_phrase = entry["original_phrase"]
    intent = entry["intent"]
    thinking = entry["thinking"]
    category = entry["category"]  # now using the CSV field correctly

    try:
        reworded = reword_phrase(intent, wem_id, original_phrase, thinking, category)
        GREEN = "\033[92m"
        RESET = "\033[0m"
        print(f"\nWEM: {wem_id} -- Original Game Wording: {original_phrase}")
        # print(f"Intent: {intent}")
        print(f"{GREEN}Final Output: {reworded}{RESET}")
    except Exception as e:
        print(f"LLM ERROR on WEM {wem_id}: {e}")
        reworded = f"WEM ERROR {wem_id}.  {original_phrase}"
