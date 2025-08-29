import json
from transformers import AutoTokenizer

# Paths
BANNED_JSON = "data/editable_banned_words.json"        # your source JSON
TOKENIZER_DIR = "assets/qwen3_06b"  # folder with tokenizer.json & tokenizer_config.json
OUTPUT_JSON = "data/tokenized_banlist.json"  # where the processed output goes

# Load Qwen tokenizer
tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_DIR, use_fast=True)

# Load banned words JSON
with open(BANNED_JSON, encoding="utf-8") as f:
    banned_words = json.load(f)

tokenized_banned = {}

# Tokenize all phrases
for category, data in banned_words.items():
    tokenized_banned[category] = {}
    for phrase in data.get("banned", []):
        token_ids = tokenizer.encode(phrase, add_special_tokens=False)
        tokenized_banned[category][phrase] = token_ids
    # Preserve the bias
    tokenized_banned[category]["bias"] = data.get("bias", 0)

# Save tokenized output
with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    json.dump(tokenized_banned, f, indent=2, ensure_ascii=False)

print(f"Tokenization complete. Output saved to {OUTPUT_JSON}")


# Helper function to get Ollama-ready logit_bias for a category_for_logit
def get_logit_bias(category_for_logit: str) -> dict:
    """Return {token_id: bias_value, ...} for a given category_for_logit."""
    cat_data = tokenized_banned.get(category_for_logit)
    if not cat_data:
        cat_data = tokenized_banned.get("default", {})
    bias_value = cat_data.get("bias", 0)
    logit_dict = {tid: bias_value for logit_phrase, tids in cat_data.items() if logit_phrase != "bias" for tid in tids}
    return logit_dict

# Example usage:
# logit_bias = get_logit_bias("780959188")
# completion = client.chat.completions.create(
#     model="qwen3:0.6b",
#     messages=[{"role": "user", "content": "Once upon a"}],
#     logit_bias=logit_bias
# )


