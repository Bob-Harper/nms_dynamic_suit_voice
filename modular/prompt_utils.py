import random
from debug.logging_utils import debug_print


def build_suit_prompt(config, category, intent, phrase, wem_id):
    debug_print("prompt_utils.py: build_suit_prompt")   # works, just seeing it get called during the trail
    if category in config.mil_cat:  # requires special prompting for best results
        system_prompt = construct_milcat_prompt(config, category, intent, phrase, wem_id)

    # elif category in config.some_other_cat:  # Example for futureproofing if we add more category handling
    #     system_prompt =  construct_other_prompt(config, category, intent, phrase, wem_id)

    else:  # default for all categories not explicitly handled
        system_prompt = construct_standard_prompt(config, category, intent, phrase, wem_id)

    system_prompt = system_prompt.encode("ascii", "ignore").decode()
    return system_prompt

def construct_standard_prompt(config, category, intent, phrase, wem_id):
    # Retrieve prompt components
    system_prompt = config.suit_voice_base
    tone = determine_tone(config)
    wordiness_level = determine_wordiness(config)
    category_context = config.promptdata.get(category, config.promptdata.get("Standard", ""))
    wordiness_prompt = config.promptdata.get("wordiness", {}).get(wordiness_level, "")
    tone_prompt = config.promptdata.get("tones", {}).get(tone, "")
    recent_lines = retrieve_recent_lines(config, wem_id)

    # Assemble dynamic prompt
    system_prompt += config.suit_voice_dynamic.format(
        category_type=category.strip(),
        input_intent=intent.strip(),
        input_phrase=phrase.strip(),
        category_context=category_context.strip(),
        wordiness_prompt=wordiness_prompt.strip(),
        tone_prompt=tone_prompt.strip(),
        recent_lines=recent_lines.strip(),
        name = config.player_name.strip()
    )

    system_prompt = system_prompt.format(name=config.player_name.strip())
    system_prompt += " /nothink"
    return system_prompt

def construct_milcat_prompt(config, category, intent, phrase, wem_id):
    # Base system instructions for combat telemetry
    recent_lines = retrieve_recent_lines(config, wem_id)
    system_prompt = config.suit_voice_combat.format(
        name=config.player_name.strip(),
        category_type=category.strip(),
        input_intent=intent.strip(),
        input_phrase=phrase.strip(),
        category_context=config.promptdata.get(category, ""),
        recent_lines = recent_lines.strip(),
    )

    # Append reasoning mode toggle only if non-milcat logic wants it off
    if getattr(config, "milcat_enable_reasoning", "False") == "False":
        system_prompt += " /nothink"

    return system_prompt


def determine_tone(config):
    tones = list(config.promptdata.get("tones", {}).keys())
    current_tone = config.current_tone

    # 90% chance stick with default
    if random.random() < 0.9 or not tones:
        return current_tone

    # 10% chance pick another from the configured tones
    return random.choice([t for t in tones if t != current_tone])


def determine_wordiness(config):
    current = config.current_wordiness

    # If observer is explicitly set, never override it
    if current == "Observer":
        return current

    # 95% chance stick with whatever's configured
    if random.random() < 0.95:
        return current

    # 5% chance: override with verbose
    return "Verbose"

def retrieve_recent_lines(config, wem_number):
    """Return recent lines for this WEM ID as a single string, ready for prompt insertion."""
    lines = config.recent_lines_text.get(wem_number, [])
    return "\n".join(lines) if lines else ""
