from pathlib import Path
from datetime import datetime
from modular.llm_utils import reword_phrase
from modular.prompt_utils import build_suit_prompt
from modular.tts_utils import run_tts
from modular.wem_utils import convert_to_wem
from debug.logging_utils import log_to_file, debug_print


def generate_replacement_voice_line(config, wem_id, output_path: Path):
    """
    Generate a new WEM for either cache or immediate use.
    - output_path: directory where WEM should be saved (cache dir or mod_dir)
    """
    debug_print("cache_replacement.py: generate_replacement_voice_line")   # works, just seeing it get called during the trail

    if wem_id not in config.intent_map:
        print(f"[cache_replacement.py] No intent entry for WEM ID {wem_id}")
        return None

    intent_entry = config.intent_map[wem_id]
    original_phrase = intent_entry["Transcription"]
    category = intent_entry["Category"]
    intent = intent_entry["Intent"]

    final_prompt = build_suit_prompt(config, category, intent, original_phrase, wem_id)
    reworded = reword_phrase(config, wem_id, original_phrase, intent, final_prompt)

    if config.logging:
        log_to_file(config, wem_id, category, intent, original_phrase, reworded)

    temp_wav_path = run_tts(config, reworded, wem_id)

    # Ensure output path exists
    output_path.mkdir(parents=True, exist_ok=True)

    # Determine final WEM filename
    if output_path == config.mod_dir:
        final_wem_path = output_path / f"{wem_id}.wem"
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_wem_path = output_path / f"{wem_id}_{timestamp}.wem"

    # Convert WAV to WEM
    convert_to_wem(config, temp_wav_path, output_path=final_wem_path)
    debug_print(f"[cache_replacement.py] Saved wem to {final_wem_path}")
    return final_wem_path
