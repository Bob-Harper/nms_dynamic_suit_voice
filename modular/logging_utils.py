import csv
from pathlib import Path


def log_to_file(config, wem_id, category, intent, original_phrase, reworded):

    fieldnames = ["WEM number", "Category", "Original", "Intent Phrase", "Final Voice Line"]
    file_exists = Path(config.game_output_csv).exists()

    log_entry = {
        "WEM number": wem_id,
        "Category": category if wem_id in config.intent_map else "",
        "Original": original_phrase if wem_id in config.intent_map else "",
        "Intent Phrase": intent if wem_id in config.intent_map else "",
        "Final Voice Line": reworded
    }

    with open(config.game_output_csv, "a", newline='', encoding='utf-8') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(log_entry)

    return
