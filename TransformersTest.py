import os
import csv
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from transformers import LogitsProcessor, LogitsProcessorList
from extras.prompting import CategoryPrompts
from transformers import AutoModelForCausalLM, AutoTokenizer
# Setup once globally at start.  pick an HF model name or point it at a local model file if you already have one.
MODEL_NAME = "Qwen/Qwen3-0.6B"  # base model no quantizing etc.  quants happen at runtime for now.

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype="auto",
    device_map="auto",
)
# Load .env from the local subdirectory
load_dotenv(dotenv_path=Path(__file__).parent / "suit_voice.env")
CSV_PATH = Path(os.getenv("CSV_PATH"))
TEST_OUTPUT_CSV = Path(os.getenv("TEST_OUTPUT_CSV"))
START_ROW = 0  # inclusive.  starts at 0.
END_ROW = 220   # exclusive. going past the end effectively skips nonexistent lines.
SUIT_VOICE_PROMPT_PATH = Path(os.getenv("SUIT_VOICE_PROMPT_PATH"))
with open(SUIT_VOICE_PROMPT_PATH, encoding="utf-8") as f:
    SUIT_VOICE_PROMPT = f.read()
category_prompts = CategoryPrompts()
# THIS IS HOW WE LOAD THE LOGITS LIST.
TOKENIZED_BANLIST_PATH = Path(os.getenv("TOKENIZED_BANLIST_PATH"))  # re-implementing. DO NOT REMOVE
with open(TOKENIZED_BANLIST_PATH, encoding="utf-8") as f:
    raw_bias = json.load(f)
LOGIT_BANLIST = {k: {int(tid): v for tid, v in d.items()} for k, d in raw_bias.items()}


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

def process_entry(wem_id, entry):
    """Shared processing of a single intent-map entry."""
    category = entry["Category"]
    original_phrase = entry["Transcription"]
    intent = entry["Intent"]

    start_time = time.perf_counter()
    cot, output = reword_phrase(original_phrase, intent, category)
    elapsed = time.perf_counter() - start_time

    print(f"WEM: {wem_id} -- Original Game Wording: {original_phrase}")
    print(f"Chain of Thought: {cot}")
    print(f"Final Output: {output}")
    print(f"Processing time: {elapsed:.3f} seconds\n\n")

    return wem_id, output  # return the file id with actual final output


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
Debugging
"""
intent_map = load_intent_map(CSV_PATH)
#  output_rows = process_by_row_range(intent_map, START_ROW, END_ROW)
output_rows = process_by_category(intent_map, "Vehicle Status")
