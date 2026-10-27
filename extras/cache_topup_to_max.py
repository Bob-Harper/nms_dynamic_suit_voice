# cache_topup_to_max.py
from time import time
from modular.config import SuitVoiceConfig
from modular.quick_cache import _replacement_wrapper
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

    for idx, wem_id in enumerate(wem_ids, start=1):
        wem_id = str(wem_id)  # force to string

        start_time = time()
        wem_dir = config.quick_cache_dir / str(wem_id)
        wem_dir.mkdir(parents=True, exist_ok=True)

        existing_files = list(wem_dir.glob("*.wem"))
        existing_count = len(existing_files)

        missing_count = max_count - existing_count
        if missing_count <= 0:
            continue

        for i in range(missing_count):
            t0 = time()
            _replacement_wrapper(config, wem_id, wem_dir)



if __name__ == "__main__":
    fill_cache_for_ids(wem_ids_raw)
