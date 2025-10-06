import random


def build_suit_prompt(config, category, intent, phrase):
    wordiness_level = determine_wordiness(config)
    tone = determine_tone(config)

    category_context = config.promptdata.get(category, config.promptdata.get("Default", ""))

    if category in config.mil_cat:
        system_prompt = config.suit_voice_combat
        wordiness_prompt = "Observer"
    else:
        system_prompt = config.suit_voice_base
        wordiness_prompt = config.promptdata.get("wordiness", {}).get(wordiness_level, "")

    tone_prompt = config.promptdata.get("tones", {}).get(tone, "")

    system_prompt += config.suit_voice_dynamic.format(
        category_type=category.strip(),
        input_intent=intent.strip(),
        input_phrase=phrase.strip(),
        category_context=category_context.strip(),
        wordiness_prompt=wordiness_prompt.strip(),
        tone_prompt=tone_prompt.strip()
    )

    system_prompt = system_prompt.format(
        name=config.player_name.strip(),
    )
    system_prompt += " /nothink"

    return system_prompt



def determine_tone(config):
    tones = list(config.promptdata.get("tones", {}).keys())
    current_tone = config.current_tone

    # If current_tone is explicitly set as Military, never override it
    if current_tone == "Military":
        return current_tone

    # 90% chance stick with default
    if random.random() < 0.9 or not tones:
        return current_tone

    # 10% chance pick another from the configured tones
    return random.choice([t for t in tones if t != current_tone])


def determine_wordiness(config):
    current = config.current_wordiness

    # If observer is explicitly set, never override it
    if current == "observer":
        return current

    # 95% chance stick with whatever's configured
    if random.random() < 0.95:
        return current

    # 5% chance: override with verbose
    return "verbose"

