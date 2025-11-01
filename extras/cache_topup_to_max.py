# fill_quick_cache_subset.py
from time import time
from modular.config import SuitVoiceConfig
from modular.quick_cache import _replacement_wrapper
from debug.logging_utils import debug_print

config = SuitVoiceConfig()

# === Paste your ID list here ===
wem_ids_raw = {
    76438123, 56102735, 968836370, 223423849, 497090550, 685057897, 1010781808, 27999850, 67834502, 272020218,
    394683190, 468585602, 691940593, 781094525, 871932351, 623058381, 774834164, 1032826641, 863051935, 105331281,
    792296351, 43830316, 117536789, 315361790, 425064686, 496984207, 589305615, 634281443, 639001585, 757274367,
    911633476, 1006934470, 976899439, 29330265, 152151960, 213575654, 489352730, 570428671, 653680659, 733521599,
    711767177, 160765928, 954591441, 278919221, 311554138, 48466939, 565386800, 597203928, 330331555, 543874217,
    580370729, 647699088, 303147008, 911201958, 980411923, 780959188, 383184645, 1023688906, 200893742, 682086836,
    769144390, 985789170, 28276028, 808789373, 825969836, 865668553, 1061736374, 449779025, 389592073, 241169623,
    672799524, 167092968, 4494640, 45779246, 695050944, 459254064, 245522736, 80959229, 776652442, 972765308, 756031301,
    126319994, 288672024, 436192208, 906332741, 64910055, 178898599, 205192151, 328948003, 599588736, 1003218333,
    1015651622, 228408571, 512212065, 768295468, 656990144, 240393094, 884631197, 386328035, 236472322, 583871976,
    72116738, 78601477, 90482995, 486861530, 540684729, 673620140, 247183138, 899320928, 951631813, 28697689, 124237937,
    696022064, 824368356, 899453751, 53870591, 54980060, 258814940, 472945351, 957514183, 330757140, 968718536,
    28199458, 49616634, 162710077, 310439562, 472197709, 510448383, 594696652, 797446331, 984473045, 396681446,
    50465612, 208814791, 490165063, 675954230, 151182894, 335483997, 498474774, 797567920, 973658086, 1063828486,
    531979220
    # … continue your list here
}
import os
print("CWD:", os.getcwd())

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
