import json
import sys
import time
from pathlib import Path
from llama_cpp import Llama
import os

# Ensure project root is on sys.path so pipeline imports resolve from extras/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.config import SuitVoiceConfig
from pipeline.prompt_utils import build_suit_prompt

# --- MODEL & TEST SETTINGS ---
MODEL_PATH = PROJECT_ROOT / "assets" / "gemma" / "gemma-4-12b-it-Q4_0.gguf"
TRANSCRIPTS_PATH = PROJECT_ROOT / "data" / "nms_suit_voice_transcripts.json"

ONLY_USED = True
START_ROW = 0
END_ROW = 7

# Load SuitVoiceConfig without loading the default Qwen LLM
config = SuitVoiceConfig(init_llm=False)

# --- INITIALIZE GEMMA 4 VIA LLAMA.CPP (CPU) ---
print(f"Loading GGUF model from: {MODEL_PATH}")
load_start = time.time()
llm = Llama(
    model_path=str(MODEL_PATH),
    n_ctx=2048,
    n_gpu_layers=0,
    verbose=False,
    n_threads=6,
    flash_attn=True
)
print(f"Model loaded in {time.time() - load_start:.2f} seconds.\n")


def reword_phrase(wem_id_r: str,
                  original_phrase_r: str,
                  intent_r: str,
                  category_r: str) -> str:

    # Use actual production prompt builder, removing Qwen-specific /nothink tag
    system_prompt = build_suit_prompt(
        config=config,
        category=category_r,
        intent=intent_r,
        phrase=original_phrase_r,
        wem_id=wem_id_r
    ).replace(" /nothink").strip()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Reword this line: {original_phrase_r.strip()}"}
    ]

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = llm.create_chat_completion(
                messages=messages,
                temperature=0.6,
                max_tokens=250,
                stream=False
            )
            if isinstance(response, dict):
                content = response["choices"][0]["message"].get("content") or ""
                return content.strip()
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                print(f"LLM ERROR on WEM {wem_id_r}: {e}")
                return f"WEM ERROR {wem_id_r}, {e}. {original_phrase_r}"
    return original_phrase_r


def process_entry(wem_id, entry):
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
        reworded = f"WEM ERROR {wem_id}. {original_phrase}"

    elapsed = time.time() - start_time
    print(f"Processing time for WEM {wem_id}: {elapsed:.2f} seconds")

    return wem_id, reworded


def load_intent_map(json_path: Path) -> dict:
    with open(json_path, encoding="utf-8") as f:
        return json.load(f)


def process_by_row_range(intent_mapr, start_row, end_row):
    output_rows_r = []
    for idx, (wem_id, entry) in enumerate(intent_mapr.items()):
        if idx < start_row:
            continue
        if idx >= end_row:
            break
        if ONLY_USED and entry.get("Used") != "Yes":
            continue
        output_rows_r.append(process_entry(wem_id, entry))
    return output_rows_r


def process_by_category(intent_mapp, target_category):
    output_rows_c = []
    for wem_id, entry in intent_mapp.items():
        if entry.get("Category") != target_category:
            continue
        if ONLY_USED and entry.get("Used") != "Yes":
            continue
        output_rows_c.append(process_entry(wem_id, entry))
    return output_rows_c


if __name__ == "__main__":
    intent_map = load_intent_map(TRANSCRIPTS_PATH)
    output_rows = process_by_row_range(intent_map, START_ROW, END_ROW)
    # output_rows = process_by_category(intent_map, "Personal Protection")
