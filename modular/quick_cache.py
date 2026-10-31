from time import time, sleep
import threading
from queue import Queue
from pathlib import Path
from modular.cache_replenishment import generate_replacement_voice_line

_job_queue = Queue()
_worker_thread: threading.Thread | None = None

# Track how many active background tasks are currently scheduled per WEM ID
_active_jobs_count = {}
_jobs_lock = threading.Lock()

def enqueue_job(func, *args, **kwargs):
    """Add a job to the queue and track its allocation."""
    start_worker()  # ensure worker is running

    # If it's a replacement job, increment the tracking counter for this WEM ID
    if func == _replacement_wrapper:
        wem_id = args[1]
        with _jobs_lock:
            _active_jobs_count[wem_id] = _active_jobs_count.get(wem_id, 0) + 1

    _job_queue.put((func, args, kwargs))

def _worker_loop():
    """Simple worker loop for queued tasks."""
    while True:
        func, args, kwargs = _job_queue.get()
        try:
            func(*args, **kwargs)
        finally:
            # Decrement the tracking counter when the background generation pass completes
            if func == _replacement_wrapper:
                wem_id = args[1]
                with _jobs_lock:
                    if wem_id in _active_jobs_count:
                        _active_jobs_count[wem_id] = max(0, _active_jobs_count[wem_id] - 1)
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
    """Moves a cached WEM file to the mod_dir and renames it."""
    mod_dir.mkdir(parents=True, exist_ok=True)
    dst_path = mod_dir / f"{wem_id}.wem"

    start_time = time()
    while True:
        try:
            src_path.replace(dst_path)
            return dst_path
        except (PermissionError, OSError):
            if time() - start_time > 120:
                return None
            sleep(0.1)

def update_access_time_to_match_newfile(file_path: Path, access_times: dict):
    """Updates the access_times dict with the atime of the given file."""
    access_times[file_path.stem] = file_path.stat().st_atime


def get_cached_wem(config, wem_id):
    """
    Return a usable WEM file path to watcher.
    - Active lines: Maintained automatically up to config.quick_cache_max.
    - Obsolete lines: Generated purely on-demand, bypassing look-ahead logic completely.
    """
    wem_dir = config.quick_cache_dir / str(wem_id)
    wem_dir.mkdir(parents=True, exist_ok=True)

    # Clean target lookup ID
    id_str = str(wem_id).strip()

    # Extract cache status natively from the pre-loaded configuration layout instance
    should_pre_cache = False
    if id_str in config.intent_map:
        status_flag = config.intent_map[id_str].get("Used", "").strip().lower()
        should_pre_cache = (status_flag == "yes")

    # Check how many files are currently sitting on the hard drive
    cached_files = sorted(wem_dir.glob("*.wem"))

    # Calculate how many generation tasks are already pending in the queue pipeline
    with _jobs_lock:
        pending_jobs = _active_jobs_count.get(id_str, 0)

    # Net inventory represents physical files PLUS files currently processing in the background
    current_inventory = len(cached_files) + pending_jobs

    if cached_files:
        if should_pre_cache:
            # Top up based on expected net inventory, preventing double-queuing triggers
            missing_count = max(0, config.quick_cache_max - current_inventory)
            for _ in range(missing_count):
                enqueue_job(_replacement_wrapper, config, wem_id, wem_dir)
        return cached_files[0]

    # FALLBACK GATE: If an inactive file is missing, enqueue ONE immediately if none are pending
    if pending_jobs == 0:
        enqueue_job(_replacement_wrapper, config, wem_id, wem_dir)

    # Wait until the fallback file finishes rendering
    while True:
        sleep(0.1)  # polling interval
        cached_files = sorted(wem_dir.glob("*.wem"))
        if cached_files:
            if should_pre_cache:
                with _jobs_lock:
                    latest_pending = _active_jobs_count.get(id_str, 0)
                net_total = len(cached_files) + latest_pending
                missing_count = max(0, config.quick_cache_max - net_total)
                for _ in range(missing_count):
                    enqueue_job(_replacement_wrapper, config, wem_id, wem_dir)
            return cached_files[0]
