import os
import csv
import requests
import re
import random
from ollama import Client
from pathlib import Path
from dotenv import load_dotenv
import time
from prompting import CategoryPrompts
import json

# CONFIG
load_dotenv(dotenv_path=Path(__file__).parent / "suit_voice.env")
CSV_PATH = Path(os.getenv("CSV_PATH"))
OLLAMA_SERVER = os.getenv("OLLAMA_SERVER")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
TEST_OUTPUT_CSV = Path(os.getenv("TEST_OUTPUT_CSV"))
START_ROW = 0  # inclusive.  yes I know it starts at 0.
END_ROW = 220    # exclusive. 211 lines, max value 212
client = Client(OLLAMA_SERVER)
with open("data/suit_voice_prompt.txt", encoding="utf-8") as f:
    SUIT_VOICE_PROMPT = f.read()
category_prompts = CategoryPrompts()
TOKENIZED_BANLIST_PATH = Path("data/tokenized_banlist.json")
with open(TOKENIZED_BANLIST_PATH, encoding="utf-8") as f:
    LOGIT_BANLIST = json.load(f)


def load_intent_map(csv_path: Path) -> dict:
    i_intent_map = {}
    try:
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                wem_number_1 = (row.get('WEM number') or '').strip()
                original_phrase_1 = (row.get('Transcription') or '').strip()
                intent_1 = (row.get('Intent') or '').strip()
                no_thinking_1 = (row.get('NO_THINK') or '').strip()
                category_1 = (row.get('Category') or '').strip()
                usage_count = (row.get('Count') or '').strip()
                i_intent_map[wem_number_1] = {
                    "original_phrase": original_phrase_1,
                    "intent": intent_1,
                    "no_thinking": no_thinking_1,
                    "category": category_1,
                    "count": int(usage_count) if usage_count.isdigit() else 0
                }
    except Exception as e1:
        print(f"Error loading intent map: {e1}")
    return i_intent_map


# Call Ollama using python module
def reword_phrase(intent_data: str,
                  wem_id: str,
                  original_phrase_r: str,
                  no_thinking,
                  category,
                  ) -> str:

    prompt = ""
    if no_thinking:  # Only prepend /no_think if THERE IS A VALUE IN THE COLUMN
        prompt = "/no_think "
    context = category_prompts.get_prompt(category)
    logit_bias = {**LOGIT_BANLIST.get("default", {}), **LOGIT_BANLIST.get(category, {})}
    # print(f"\n\n{context}")
    prompt += SUIT_VOICE_PROMPT.format(category=category.strip(), intent_data=intent_data.strip(),
                                       input_phrase=original_phrase_r.strip(), context=context.strip())
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
    print(f"\n\nPayload: {payload}\n")
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(f"{OLLAMA_SERVER}/api/generate", json=payload, timeout=10)
            response.raise_for_status()
            generated_response = response.json().get("response", "").strip()
            if not generated_response:
                raise ValueError("Empty response from Ollama")
            full_response = generated_response
            print(f"\nWEM {wem_id} -- Full response with thinking tags if included: \n{full_response}")
            generated_response = re.sub(r"<think>.*?</think>",
                                        "",
                                        generated_response,
                                        flags=re.DOTALL
                                        ).strip()
            # Postprocess to enforce 'You'
            return generated_response
        except Exception as e2:
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                print(f"LLM ERROR on WEM {wem_id}: {e2}")
                return f"WEM ERROR {wem_id}, {e2}.  {original_phrase_r}"

    # Safety fallback
    return "External Reality alert, computer error detected"


# Read intent map (already cleaned and ready)
intent_map = load_intent_map(CSV_PATH)
output_rows = []

for idx, (wem_id, entry) in enumerate(intent_map.items()):
    if idx < START_ROW:
        continue
    if idx >= END_ROW:
        break

    original_phrase = entry["original_phrase"]
    intent = entry["intent"]
    no_thinking = entry["no_thinking"]
    category = entry["category"]
    model_seed = random.randint(1, 9999999)

    try:
        reworded = reword_phrase(intent, wem_id, original_phrase, no_thinking, category)
        GREEN = "\033[92m"
        RESET = "\033[0m"
        print(f"\nWEM: {wem_id} -- Original Game Wording: {original_phrase}")
        print(f"Intent: {intent}")
        print(f"{GREEN}Final Output: {reworded}{RESET}")
    except Exception as e:
        print(f"LLM ERROR on WEM {wem_id}: {e}")
        reworded = f"WEM ERROR {wem_id}.  {original_phrase}"
