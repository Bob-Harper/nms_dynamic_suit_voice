import json
from transformers import AutoTokenizer

# Paths
BANNED_JSON = "data/editable_banned_words.json"
TOKENIZER_DIR = "assets/qwen3_06b"
# TOKENIZER_DIR = "assets/qwen3_06b_q4"
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


def get_logit_bias(category_for_logit: str) -> dict:
    cat_data = tokenized_banned.get(category_for_logit, tokenized_banned.get("default", {}))
    return {int(tid): bias for tid, bias in cat_data.items() if tid != "bias"}

"""

{
  "default": {
    "banned": [
      "player",
      "user",
      "wearer",
      "the player",
      "The user's",
      "The user",
      "the user",
      "the user’s",
      "the wearer",
      "wearer's",
      "the wearer's",
      "all personell",
      "our systems",
      "a warning",
      "sci-fi",
      "twist",
      "alert",
      "the pilot",
      "alerting",
      "shared",
      "car",
      "Earth",
      "I",
      "I am",
      "me",
      "my",
      "My",
      "we",
      "let's",
      "we're",
      "our",
      "ours",
      "ourselves",
      "us",
      "game",
      "system",
      "the AI",
      "the game",
      "the system",
      "planet name",
      "Planet Name",
      "the explorers",
      "Stay alert",
      "Stay vigilant",
      "everyone",
      "seconds",
      "minutes",
      "Fahrenheit",
      "together",
      "Celsius",
      "Kelvin",
      "team",
      "our team",
      "your team",
      "the team",
      "preserving the original intent",
      "original intent",
      "the AI"
    ],
    "bias": -100
  },
  "Inventory": {
    "banned": [
      "empty",
      "running low",
      "space available",
      "my inventory",
      "my space",
      "your system",
      "room left"
    ],
    "bias": -100
  },
  "Monetary Transaction": {
    "banned": [
      "paid",
      "payment sent",
      "our system",
      "spent",
      "deducted",
      "sci-fi",
      "twist",
      "trillion",
      "currency",
      "sci-fi-themed",
      "trillion-dollar",
      "dollar",
      "poetic",
      " poetic",
      "poetic ",
      "withdrawn"
    ],
    "bias": -100
  },
  "Notification": {
    "banned": [
      "a warning",
      "Alert:",
      "siren",
      "siren's",
      "as a warning",
      "A warning",
      "the warning",
      "The warning",
      "Stay alert",
      "Stay alert,",
      "we encourage",
      "alert"
    ],
    "bias": -100
  },
  "Discovery": {
    "banned": [
      "planet name",
      "Planet Name",
      "the explorers",
      "Earth",
      "[planet name]",
      "[Planet Name]",
      "[planet]",
      "we"
    ],
    "bias": -100
  },
  "Environmental Status": {
    "banned": [
      "specific values",
      "environmental concern",
      "fragile balance",
      "delicate balance",
      "worry about",
      "specific data",
      "underground environment",
      "underground environment's",
      "environment",
      "environmental health",
      "environment's health",
      "no need",
      "natural world",
      "nature's balance",
      "natural balance",
      "degrees"
    ],
    "bias": -100
  },
  "Freighter Combat": {
    "banned": [
      "under our protection",
      "Freighter Combat",
      "Freighter Combat battle",
      "your vessel",
      "your freighter",
      "your freighter",
      "\uD83D\uDEA8",
      "our freighter"
    ],
    "bias": -100
  },
  "Personal Combat": {
    "banned": [
      "vital",
      "Personal Combat",
      "shadow",
      "shadowy",
      "Vital",
      "alers",
      "Squad's",
      "Squad",
      "squad's",
      "squad",
      "alert"
    ],
    "bias": -100
  },
  "Personal Protection": {
    "banned": [
      "we",
      "%",
      "guardian",
      "Guardian",
      "our"
    ],
    "bias": -100
  },
  "Starship Combat": {
    "banned": [
      "aircraft",
      "airborne",
      "our"
    ],
    "bias": -100
  },
  "Starship Movement": {
    "banned": [
      "I",
      "My",
      "pilot",
      "the pilot",
      "The pilot",
      "the pilot's",
      "The pilot's",
      "a pilot"
    ],
    "bias": -100
  },
  "Radiation Exposure": {
    "banned": [
      "the user",
      "the wearer",
      "our"
    ],
    "bias": -100
  },
  "Debugging": {
    "banned": [
      "wait",
      "alternatively",
      "hmm",
      "but",
      "however",
      "alternative",
      "another",
      "check",
      "double-check",
      "oh",
      "maybe",
      "verify",
      "other",
      "again",
      "now",
      "ah",
      "any"
    ],
    "encouraged": [
      "the user",
      "the wearer",
      "our"
    ],
    "required": [
      "the user",
      "the wearer",
      "our"
    ],
    "bias": {
      "banned": -100,
      "encouraged": 50,
      "required": 100
    }
  }
}
"""
