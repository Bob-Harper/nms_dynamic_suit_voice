# cache_topup_to_max.py
from time import time
from modular.config import SuitVoiceConfig
from modular.quick_cache import _replacement_wrapper
from debug.logging_utils import debug_print
import csv

config = SuitVoiceConfig()

# === Paste your ID list here ===
wem_ids_raw = []
with open(config.csv_path, newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        if row.get("Used", "").strip().lower() == "yes":
            wem_number = row.get("WEM_number")
            if wem_number:
                wem_ids_raw.append(str(wem_number))


def fill_cache_for_ids(wem_ids, max_count=None):
    if max_count is None:
        max_count = config.quick_cache_max
    wem_ids = [str(w) for w in wem_ids]
    total_ids = len(wem_ids)
    debug_print("Starting cache fill for {} WEM IDs", total_ids)

    for idx, wem_id in enumerate(wem_ids, start=1):
        wem_id = str(wem_id)  # force to string

        start_time = time()
        wem_dir = config.quick_cache_dir / str(wem_id)
        wem_dir.mkdir(parents=True, exist_ok=True)

        existing_files = list(wem_dir.glob("*.wem"))
        existing_count = len(existing_files)
        debug_print("({}/{}) [{}] Current count: {} / {}", idx, total_ids, wem_id, existing_count, max_count)

        missing_count = max_count - existing_count
        if missing_count <= 0:
            debug_print("({}/{}) [{}] Already full, skipping", idx, total_ids, wem_id)
            continue

        for i in range(missing_count):
            t0 = time()
            debug_print("({}/{}) [{}] Generating {}/{} missing WEM", idx, total_ids, wem_id, i+1, missing_count)
            _replacement_wrapper(config, wem_id, wem_dir)
            debug_print("({}/{}) [{}] Done generating {} in {:.3f}s", idx, total_ids, wem_id, i+1, time()-t0)

        debug_print("({}/{}) [{}] Total time for this ID: {:.3f}s", idx, total_ids, wem_id, time()-start_time)

    debug_print("Cache fill complete for all IDs!")

if __name__ == "__main__":
    fill_cache_for_ids(wem_ids_raw)
