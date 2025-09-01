import json
from transformers import AutoTokenizer

# Paths
BANNED_JSON = "data/editable_banned_words.json"
TOKENIZER_DIR = "assets/qwen3_06b"
OUTPUT_JSON = "data/tokenized_banlist.json"

# Load tokenizer
tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_DIR, use_fast=True)

# Load banned words JSON
with open(BANNED_JSON, encoding="utf-8") as f:
    banned_words = json.load(f)

tokenized_banned = {}

def generate_variants(phrase: str):
    """Generate common variants for a phrase."""
    variants = set()
    variants.add(phrase)                     # original
    variants.add(phrase.lower())             # lowercase
    variants.add(phrase.capitalize())        # capitalized
    variants.add(phrase.upper())             # uppercase
    variants.add(f" {phrase}")               # leading space
    variants.add(f"{phrase} ")               # trailing space
    variants.add(f" {phrase} ")              # leading + trailing space

    # possessive variant if it ends with a word (simple heuristic)
    if not phrase.endswith("'s"):
        variants.add(f"{phrase}'s")
        variants.add(f" {phrase}'s")
        variants.add(f"{phrase}'s ")
        variants.add(f" {phrase}'s ")

    return variants

for category, data in banned_words.items():
    tokenized_banned[category] = {}
    bias_value = data.get("bias", 0)
    token_ids_set = set()

    for phrase in data.get("banned", []):
        for variant in generate_variants(phrase):
            token_ids = tokenizer.encode(variant, add_special_tokens=False)
            token_ids_set.update(token_ids)

    # store all unique token IDs with bias
    for tid in token_ids_set:
        tokenized_banned[category][str(tid)] = bias_value

# Save output
with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    json.dump(tokenized_banned, f, indent=2, ensure_ascii=False)

print(f"Tokenization complete. Output saved to {OUTPUT_JSON}")


# Helper function to get Ollama-ready logit_bias for a category_for_logit
def get_logit_bias(category_for_logit: str) -> dict:
    """Return Ollama-ready logit_bias {token_id: bias_value}."""
    cat_data = tokenized_banned.get(category_for_logit, tokenized_banned.get("default", {}))
    bias_value = cat_data.get("bias", 0)

    logit_dict = {}
    for phrase, token_ids in cat_data.items():
        if phrase == "bias":
            continue
        for tid in token_ids:
            logit_dict[int(tid)] = bias_value  # token ID as key, bias as value

    return logit_dict
# Example usage:
# logit_bias = get_logit_bias("780959188")
# completion = client.chat.completions.create(
#     model="qwen3:0.6b",
#     messages=[{"role": "user", "content": "Once upon a"}],
#     logit_bias=logit_bias
# )


