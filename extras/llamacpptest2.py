# from extras.prompt_lab_ui import PromptLabUI
import time
from modular.config import SuitVoiceConfig
from modular.llm_utils import reword_phrase
from modular.prompt_utils import build_suit_prompt
config = SuitVoiceConfig()


def process_entry(wem_id, entry, wordiness_level="Standard", tone="Deadpan"):
    """Shared processing of a single intent-map entry."""
    category = entry["Category"]
    original_phrase = entry["Transcription"]
    intent = entry["Intent"]

    # Build the structured prompt
    finalprompt = build_suit_prompt(config, category, intent, original_phrase)
    # convert Player Name Placeholder
    finalprompt = finalprompt.format(
        name=config.player_name.strip(),
    )
    finalprompt += " /nothink"
    # print(f"final prompt: {finalprompt}")
    start_time = time.time()
    try:
        # Generate with LLM
        reworded = reword_phrase(config, wem_id, original_phrase, intent, finalprompt)

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
    for tone in config.promptdata.get("tones", {}).keys():
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

# wordiness_level = "Standard"
# tone = "Questioning"
# start_row = 20  # inclusive.  starts at 0.
# end_row = 25  # exclusive. going past the end effectively skips nonexistent lines.
# output_rows = process_by_row_range(intent_map, start_row, end_row, wordiness_level, tone)

# ui = PromptLabUI(config, intent_map, process_entry)
# ui.run()

target_wem = "911201958"
target_wordy = "Default"
process_single_wem_all_tones(intent_map, target_wem, target_wordy)


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
