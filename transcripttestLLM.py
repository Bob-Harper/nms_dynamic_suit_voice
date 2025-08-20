import os
import csv
import requests
import re
import random
from ollama import Client
from pathlib import Path
from dotenv import load_dotenv
import time
import json

# CONFIG
load_dotenv(dotenv_path=Path(__file__).parent / "suit_voice.env")
CSV_PATH = Path(os.getenv("CSV_PATH"))
OLLAMA_SERVER = os.getenv("OLLAMA_SERVER")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
TEST_OUTPUT_CSV = Path(os.getenv("TEST_OUTPUT_CSV"))
START_ROW = 0  # inclusive.  yes I know it starts at 0.  this is a test script.
END_ROW = 220    # exclusive
client = Client(OLLAMA_SERVER)
with open("data/suit_voice_prompt.txt", encoding="utf-8") as f:
    SUIT_VOICE_PROMPT = f.read()

def load_banlist(path: str) -> dict:
    with open(path, encoding="utf-8") as f_ban:
        return json.load(f_ban)

BAN = load_banlist("data/wem_banlist.json")


def build_logit_bias(wem_id, ban_map, default_bias=-50):
    """
    Return a dict of token -> bias for Ollama.

    - Uses the WEM-specific banned list if available.
    - Falls back to the default banned list for all other words.
    - Applies the WEM-specific bias if provided; otherwise uses default bias.
    """
    bias_dict = {}

    # Add default banned words
    default_words = ban_map.get("default", {}).get("banned", [])
    default_value = ban_map.get("default", {}).get("bias", default_bias)
    for word in default_words:
        bias_dict[word] = default_value
        bias_dict[f" {word}"] = default_value  # also add variant with leading space

    # Add WEM-specific banned words if any
    if wem_id in ban_map:
        wem_entry = ban_map[wem_id]
        wem_words = wem_entry.get("banned", [])
        wem_value = wem_entry.get("bias", default_value)
        for word in wem_words:
            bias_dict[word] = wem_value
            bias_dict[f" {word}"] = wem_value

    return bias_dict


def phrase_variants(phrase):
    variants = [phrase, " " + phrase]
    if phrase.isalpha():
        variants.append(phrase.lower())
        variants.append(" " + phrase.lower())
    return variants


def enforce_user_pronouns(text: str) -> str:
    """
    Replace any first-person or team pronouns with 'You' in the context
    of the suit AI notifications. Leaves everything else intact.
    """
    # Replace exact words or contractions
    replacements = {
        r"\bI\b": "You",
        r"\bmy\b": "your",
        r"\bwe\b": "You",
        r"\bours\b": "your",
        r"\bus\b": "You",
        r"\bme\b": "You",
        r"\bI'm\b": "You are",
        r"\bI am\b": "You are",
        r"\bI've\b": "You have",
        r"\bI'll\b": "You will",
        r"\bWe\b": "You",
        r"\bMy\b": "Your",
        r"\bOur\b": "Your",
        r"\bUs\b": "You",
        r"\bThe user's\b": "Your",
        r"\bThe user\b": "You",
    }

    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text)
    return text

def load_intent_map(csv_path: Path) -> dict:
    i_intent_map = {}
    try:
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                wem_number_1 = (row.get('WEM number') or '').strip()
                original_phrase_1 = (row.get('Transcription') or '').strip()
                seed_phrase_1 = (row.get('Seed_Phrase') or '').strip()
                intent_1 = (row.get('Intent') or '').strip()
                context_1 = (row.get('Context') or '').strip()
                thinking_1 = (row.get('Thinking') or '').strip()
                usage_count = (row.get('Count') or '').strip()

                if wem_number_1 and seed_phrase_1:
                    seed_columns = [seed_phrase_1]  # start with primary phrase first
                    seed_columns += [row.get(f'seed{i}', '').strip() for i in range(1, 10) if
                                     row.get(f'seed{i}', '').strip()]

                    if not seed_columns:
                        seed_columns = [seed_phrase_1]
                    i_intent_map[wem_number_1] = {
                        "seed_phrases": seed_columns,
                        "original_phrase": original_phrase_1,
                        "intent": intent_1,
                        "context": context_1,
                        "thinking": thinking_1,
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


# Call Ollama using python module
def reword_phrase(input_phrase: str,
                  intent_data: str,
                  wem_id: str,
                  original_phrase_r: str
                  ) -> str:
    logit_bias = build_logit_bias(wem_id, BAN)
    prompt = SUIT_VOICE_PROMPT.format(intent_data=intent_data.strip(), input_phrase=input_phrase.strip())
    # temporary, per-call no-think
    # prompt = "/no_think\n" + prompt
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "max_tokens": 15,
            "temperature": 0.4,
            "top_k": 10,
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
            generated_response = re.sub(r"<think>.*?</think>", "", generated_response, flags=re.DOTALL).strip()
            # Postprocess to enforce 'You'
            generated_response = enforce_user_pronouns(generated_response)
            return generated_response
        except Exception as e2:
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                print(f"LLM ERROR on WEM {wem_id}: {e2}")
                return f"WEM ERROR {wem_id}, {e2}.  {original_phrase_r}"

    # Safety fallback
    return enforce_user_pronouns(str(original_phrase_r))


# Read intent map (already cleaned and ready)
intent_map = load_intent_map(CSV_PATH)
output_rows = []

for idx, (wem_number, entry) in enumerate(intent_map.items()):
    if idx < START_ROW:
        continue
    if idx >= END_ROW:
        break

    original_phrase = entry["original_phrase"]
    seed_phrase = get_seed_prompt(entry)
    intent = entry["intent"]
    context = entry["context"]
    thinking = entry["thinking"]
    model_seed = random.randint(1, 9999999)

    try:
        reworded = reword_phrase(seed_phrase, intent, wem_number, original_phrase)
        print(f"\nWEM: {wem_number} -- Original Game Wording: {original_phrase}")
        print(f"Context: {context}")
        print(f"Intent: {intent}")
        print(f"Adjusted Seed phrase: {seed_phrase}")
        print(f"Final Output: {reworded}")
    except Exception as e:
        print(f"LLM ERROR on WEM {wem_number}: {e}")
        reworded = f"WEM ERROR {wem_number}.  {original_phrase}"

    output_rows.append({
        "WEM number": wem_number,
        "Original": original_phrase,
        "Seed": seed_phrase,
        "Reworded": reworded,
        "Model_Seed": model_seed,
        "Model": OLLAMA_MODEL
    })

# Write output CSV for review
fieldnames = ["WEM number", "Original", "Seed", "Reworded", "Model_Seed", "Model"]
with open(TEST_OUTPUT_CSV, "w", newline='', encoding='utf-8') as outfile:
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(output_rows)

print(f"\nALL DONE. Output written to: {TEST_OUTPUT_CSV}")
