from time import time, sleep
import threading
from queue import Queue
from pathlib import Path
from modular.cache_replenishment import generate_replacement_voice_line
from debug.log_config import debug_print

_job_queue = Queue()
_worker_thread: threading.Thread | None = None

def enqueue_job(func, *args, **kwargs):
    debug_print("quick_cache.py: enqueue_job")
    """Add a job to the queue."""
    start_worker()  # ensure worker is running
    _job_queue.put((func, args, kwargs))

def _worker_loop():
    debug_print("quick_cache.py: _worker_loop")
    """Simple worker loop for queued tasks."""
    while True:
        func, args, kwargs = _job_queue.get()
        try:
            func(*args, **kwargs)
        finally:
            _job_queue.task_done()

def start_worker():
    debug_print("quick_cache.py:  start_worker")
    global _worker_thread
    if _worker_thread is None or not _worker_thread.is_alive():
        _worker_thread = threading.Thread(target=_worker_loop, daemon=True)
        _worker_thread.start()
        debug_print("quick_cache.py: Worker thread started.")

def _replacement_wrapper(config, wem_id: str, wem_dir: Path):
    """Generates a replacement WEM."""
    debug_print(f"quick_cache.py: _replacement_wrapper for {wem_id}")
    generate_replacement_voice_line(config, wem_id, wem_dir)


def move_cachedfile_to_mod_dir(src_path: Path, mod_dir: Path, wem_id: str):
    """
    Moves a cached WEM file to the mod_dir and renames it to wem_id.wem.
    Retries until successful or timeout.
    Returns the Path to the newly moved file, or None on timeout.
    """
    debug_print("quick_cache.py: move_cachedfile_to_mod_dir")

    mod_dir.mkdir(parents=True, exist_ok=True)
    dst_path = mod_dir / f"{wem_id}.wem"  # THIS IS THE RENAME the game expects

    start_time = time()
    while True:
        try:
            src_path.replace(dst_path)
            return dst_path
        except (PermissionError, OSError):
            if time() - start_time > 120:  # 2-minute timeout
                debug_print("[move_cachedfile_to_mod_dir] Could not move {} within 120s", src_path.name)
                return None
            sleep(0.1)

def update_access_time_to_match_newfile(file_path: Path, access_times: dict):
    """
    Updates the access_times dict with the atime of the given file.
    """
    debug_print("quick_cache.py: update_access_time_to_match_newfile")

    access_times[file_path.stem] = file_path.stat().st_atime

def get_cached_wem(config, wem_id):
    debug_print("quick_cache.py: get_cached_wem")
    """
    Return a usable WEM file path to watcher.
    - Immediately tells queue manager to replenish if needed.
    - If a file exists, return it immediately.
    - If not, wait until one exists, then return it.
    """
    wem_dir = config.quick_cache_dir / str(wem_id)
    wem_dir.mkdir(parents=True, exist_ok=True)

    # Look for an existing file
    cached_files = sorted(wem_dir.glob("*.wem"))
    if cached_files:
        # Fire-and-forget: top-up remaining files
        missing_count = max(0, config.quick_cache_max - len(cached_files))
        for _ in range(missing_count):
            enqueue_job(_replacement_wrapper, config, wem_id, wem_dir)
        return cached_files[0]

    # If none exist, enqueue one immediately
    enqueue_job(_replacement_wrapper, config, wem_id, wem_dir)

    # Wait until a file is produced
    while True:
        sleep(0.1)  # polling interval
        cached_files = sorted(wem_dir.glob("*.wem"))
        if cached_files:
            # Fire-and-forget: top-up remaining files
            missing_count = max(0, config.quick_cache_max - len(cached_files))
            for _ in range(missing_count):
                enqueue_job(_replacement_wrapper, config, wem_id, wem_dir)
            return cached_files[0]
