import re
import time
from modular.config import SuitVoiceConfig
from modular.prompt_lab_ui import PromptLabUI
config = SuitVoiceConfig()


def create_logit_bias(category_l):
    logit_bias = {
        **extract_token_ids(config.logit_banlist.get(category_l, {})),
        **extract_token_ids(config.logit_banlist.get("Default", {})),
    }
    return logit_bias

def extract_token_ids(data: dict):
    """Flatten token dict and ignore non-integer keys like 'bias'."""
    return {int(k): v for k, v in data.get("tokens", {}).items()}


def build_suit_prompt(config, category, intent, phrase, wordiness_level=None, tone=None):
    # fallback to config's current values if not explicitly passed
    wordiness_level = wordiness_level or config.current_wordiness
    tone = tone or config.current_tone

    category_context = config.promptbuilder.get(category, config.promptbuilder.get("Default", ""))

    if category in config.mil_cat:
        system_prompt = config.suit_voice_combat
        wordiness_prompt = "Observer"
    else:
        system_prompt = config.suit_voice_base
        wordiness_prompt = config.promptbuilder.get("wordiness", {}).get(wordiness_level, "")

    tone_prompt = config.promptbuilder.get("tones", {}).get(tone, "")

    system_prompt += config.suit_voice_dynamic.format(
        category_type=category.strip(),
        input_intent=intent.strip(),
        input_phrase=phrase.strip(),
        category_context=category_context.strip(),
        wordiness_prompt=wordiness_prompt.strip(),
        tone_prompt=tone_prompt.strip()
    )
    return system_prompt


def reword_phrase(wem_id_r,
                  category_r,
                  original_phrase_r,
                  finalprompt):

    # enforce usage or avoidance of specific tokens using logits
    logit_bias_list = create_logit_bias(category_r)

    messages = [{"role": "system", "content": finalprompt}]
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # print(f"Raw Input:\n {messages}")
            output = config.llm.create_chat_completion(
                messages=messages,
                max_tokens=2048,  # less can be faster but can cut off thinking, breaking the result
                temperature=0.8,
                top_k=90,
                top_p=0.9,
                repeat_penalty=1.25,
                logit_bias=logit_bias_list,
                seed=-1  # must add this to randomize the results
            )
            # print(f"Raw Output:\n {output}")
            result = output["choices"][0]["message"]["content"].strip()
            result = postprocess_for_tts(result)
            return result

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                print(f"LLM ERROR on WEM {wem_id_r}: {e}")
                return f"WEM ERROR {wem_id_r}, {e}. {original_phrase_r}"
    print(f"ERROR on WEM {wem_id_r}")
    return f"External Reality Failure. {original_phrase_r}"

def postprocess_for_tts(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)  # Strip Thinking before sending to TTS
    text = re.sub(r"[—–]", ", ", text)  # convert em-dash and en-dash combo that the model likes to use
    return text.strip()


def process_entry(wem_id, entry, wordiness_level="Standard", tone="Standard"):
    """Shared processing of a single intent-map entry."""
    category = entry["Category"]
    original_phrase = entry["Transcription"]
    intent = entry["Intent"]

    # Build the structured prompt
    prompt = build_suit_prompt(config, category, intent, original_phrase, wordiness_level, tone)

    start_time = time.time()
    try:
        # Generate with LLM
        reworded = reword_phrase(wem_id, category, original_phrase, prompt)


        print(f"\nWEM: {wem_id} -- Original Game Wording: {original_phrase}")
        print(f"Tone: ({tone}) Verbosity: ({wordiness_level})")
        print(f"\033[92mFinal Output: {reworded}\033[0m")

    except Exception as e:
        print(f"LLM ERROR on WEM {wem_id}: {e}")
        reworded = f"WEM ERROR {wem_id}.  {original_phrase}"

    elapsed = time.time() - start_time
    print(f"Processing time for WEM {wem_id}: {elapsed:.2f} seconds")

    return wem_id, reworded


intent_map = config.intent_map


# ui = PromptLabUI(config, intent_map, process_entry)
# ui.run()


"""
start_row = 0  # inclusive.  starts at 0.
end_row = 6  # exclusive. going past the end effectively skips nonexistent lines.
target_wem = "56102735"
target_cat = "Monetary Transaction"
target_wordy = "Standard"
target_tone = "Questioning"
# PICK ONLY ONE OF THE FOLLOWING UNLESS YOU INTEND TO FLOOD YOUR TERMINAL WINDOW. In which case, go ahead. Have at it.
# output_rows = five_x__row_range(intent_map, start_row, end_row)

# output_rows = process_by_row_range(intent_map, start_row, end_row)

output_rows = process_by_category(intent_map,
                                  target_cat,
                                  target_wordy,
                                  target_tone
                                  )
"""
# process_single_wem_all_tones(intent_map, target_wem, target_wordy)
"""
Cold Temperature
Discovery
Energy Shield
Environmental Status
Equipment Status
Extreme Temperature
Freighter Combat
Missile Launch
Freighter Escape
Missile Destroyed
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

"""
  "wordiness": {
    "Minimal":     
    "Standard":
    "Verbose":
      },
  "tones": {
    "Standard": "State the obvious with the personality of a standard default fallback message in a computer program. ",
    "Casual": "Provide the notification in a casual laid back friendly manner. ",
    "Poetic": "Render the notification in vivid, metaphorical language. ",
    "Epic": "Frame the notification with grandeur, as if it were part of a fantasy trope saga. ",
    "Deadpan Wit": "State the notification in a flat, dry manner with irony. ",
    "Sardonic": "Deliver the notification with a biting, sarcastic undertone. ",
    "Lamentation": "Express the notification with mournful, tragic gravitas. ",
    "Clinical": "Convey the notification with detached technical precision. ",
    "Debug": "Curiosity overrides all else as a mystery unfolds. ",
    "Overly Enthusiastic": "State the notification as if you’re unreasonably excited. ",
    "Prophecy": "Render the notification as though it were part of an ancient prophecy. ",
	"Philosophical": "Provide a deeply profound philosophical interpretation of the notifaction and possible impact on the Interloper's world views. ",
	"Questioning": "The Interloper's every action and decision make you wonder how they've managed to last this long. "
  }

"""
def five_x__row_range(intent_mapr, start_row, end_row, repeats=5):
    output_rows_r = []
    for idx, (wem_id, entry) in enumerate(intent_mapr.items()):
        if idx < start_row:
            continue
        if idx >= end_row:
            break
        for r in range(repeats):  # hammer this row before moving on
            print(f"[Row {idx}, Repeat {r+1}] WEM {wem_id}")
            output_rows_r.append(process_entry(wem_id, entry))
    return output_rows_r


def process_by_category(intent_mapp, target_category, wordiness_level="Standard", tone="Standard"):
    output_rows_c = []
    for wem_id, entry in intent_mapp.items():
        if entry["Category"] != target_category:
            continue
        output_rows_c.append(process_entry(wem_id, entry, wordiness_level, tone))

    return output_rows_c


def process_single_wem_all_tones(intent_maps, wem_id, wordiness_level="Standard"):
    entry = intent_maps.get(wem_id)
    if not entry:
        print(f"WEM {wem_id} not found in intent map.")
        return []

    results = []
    for tone in config.promptbuilder.get("tones", {}).keys():
        print(f"\n=== Tone: {tone} === Length: {wordiness_level} ===")
        results.append(process_entry(
            wem_id, entry,
            wordiness_level=wordiness_level,
            tone=tone
        ))
    return results


def process_by_row_range(intent_mapr, start_row, end_row):
    output_rows_r = []
    for idx, (wem_id, entry) in enumerate(intent_mapr.items()):
        if idx < start_row:
            continue
        if idx >= end_row:
            break
        output_rows_r.append(process_entry(wem_id, entry))
    return output_rows_r

start_row = 0  # inclusive.  starts at 0.
end_row = 222  # exclusive. going past the end effectively skips nonexistent lines.
output_rows = process_by_row_range(intent_map, start_row, end_row)

