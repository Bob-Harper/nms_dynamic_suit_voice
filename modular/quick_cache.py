from time import time, sleep
import threading
from queue import Queue
from pathlib import Path
import json
from modular.cache_replenishment import generate_replacement_voice_line

_job_queue = Queue()
_worker_thread: threading.Thread | None = None

# (Change this path if it's located somewhere else on your filesystem)
INTENT_MAP_JSON_PATH = Path("config/intent_map.json")

def load_active_cache_registry_from_json() -> set:
    """Reads the master JSON config and returns a fast-lookup set of IDs marked 'Yes'."""
    active_ids = set()

    if not INTENT_MAP_JSON_PATH.exists():
        print(f"[Cache Registry] Warning: Missing data map file at {INTENT_MAP_JSON_PATH}")
        return active_ids

    try:
        with open(INTENT_MAP_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            for wem_id, details in data.items():
                # Isolate matching entries directly by checking the string metric
                if details.get("Used", "").strip().lower() == "yes":
                    active_ids.add(str(wem_id).strip())
    except Exception as e:
        print(f"[Cache Registry] Critical error reading target JSON: {e}")

    return active_ids

# Instantiate the active tracking set cleanly at initialization
ACTIVE_CACHE_WEM_IDS = load_active_cache_registry_from_json()

def enqueue_job(func, *args, **kwargs):
    """Add a job to the queue."""
    start_worker()  # ensure worker is running
    _job_queue.put((func, args, kwargs))

def _worker_loop():
    """Simple worker loop for queued tasks."""
    while True:
        func, args, kwargs = _job_queue.get()
        try:
            func(*args, **kwargs)
        finally:
            _job_queue.task_done()

def start_worker():
    global _worker_thread
    if _worker_thread is None or not _worker_thread.is_alive():
        _worker_thread = threading.Thread(target=_worker_loop, daemon=True)
        _worker_thread.start()

def _replacement_wrapper(config, wem_id: str, wem_dir: Path):
    """Generates a replacement WEM."""
    generate_replacement_voice_line(config, wem_id, wem_dir)


def move_cachedfile_to_mod_dir(src_path: Path, mod_dir: Path, wem_id: str):
    """
    Moves a cached WEM file to the mod_dir and renames it to wem_id.wem.
    Retries until successful or timeout.
    Returns the Path to the newly moved file, or None on timeout.
    """

    mod_dir.mkdir(parents=True, exist_ok=True)
    dst_path = mod_dir / f"{wem_id}.wem"  # THIS IS THE RENAME the game expects

    start_time = time()
    while True:
        try:
            src_path.replace(dst_path)
            return dst_path
        except (PermissionError, OSError):
            if time() - start_time > 120:  # 2-minute timeout
                # debug_print("[move_cachedfile_to_mod_dir] Could not move {} within 120s", src_path.name)
                return None
            sleep(0.1)

def update_access_time_to_match_newfile(file_path: Path, access_times: dict):
    """
    Updates the access_times dict with the atime of the given file.
    """

    access_times[file_path.stem] = file_path.stat().st_atime

def get_cached_wem(config, wem_id):
    """
    Return a usable WEM file path to watcher.
    - Immediately tells queue manager to replenish if needed.
    - If a file exists, return it immediately.
    - If not, wait until one exists, then return it.
    """
    wem_dir = config.quick_cache_dir / str(wem_id)
    wem_dir.mkdir(parents=True, exist_ok=True)

    # Convert ID to string to ensure reliable lookup mapping against our active hash set
    id_str = str(wem_id)
    should_pre_cache = id_str in ACTIVE_CACHE_WEM_IDS

    # Look for an existing file
    cached_files = sorted(wem_dir.glob("*.wem"))
    if cached_files:
        # Fire-and-forget: top-up remaining files ONLY if this ID is on the active list
        if should_pre_cache:
            missing_count = max(0, config.quick_cache_max - len(cached_files))
            for _ in range(missing_count):
                enqueue_job(_replacement_wrapper, config, wem_id, wem_dir)
        return cached_files[0]

    # If none exist, enqueue exactly ONE immediately as a live-demand fallback
    enqueue_job(_replacement_wrapper, config, wem_id, wem_dir)

    # Wait until a file is produced
    while True:
        sleep(0.1)  # polling interval
        cached_files = sorted(wem_dir.glob("*.wem"))
        if cached_files:
            # Fire-and-forget: top-up remaining cache buffers ONLY for confirmed active IDs
            if should_pre_cache:
                missing_count = max(0, config.quick_cache_max - len(cached_files))
                for _ in range(missing_count):
                    enqueue_job(_replacement_wrapper, config, wem_id, wem_dir)
            return cached_files[0]
