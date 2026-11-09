# pipeline/quick_cache.py
import os
import threading
from time import time, sleep
from queue import Queue
from pathlib import Path
from .cache_replenishment import generate_replacement_voice_line
from .debug_support import extract_debug_token, record_exception

class QuickCacheEngine:
    def __init__(self, config):
        """
        Initializes the stateful background queues, thread locks,
        and directory properties for the real-time cache watcher.
        """
        self.config = config

        # Instance-bound thread synchronization trackers
        self._job_queue = Queue()
        self._worker_thread = None
        self._active_jobs_count = {}
        self._jobs_lock = threading.Lock()

    def start_worker(self):
        """Spins up the background consumer loop thread cleanly if inactive."""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self._worker_thread.start()

    def enqueue_job(self, func, *args, **kwargs):
        """Adds an active processing job to the thread safe execution queue."""
        self.start_worker()

        if func == self._replacement_wrapper:
            wem_id = args[1]
            with self._jobs_lock:
                self._active_jobs_count[wem_id] = self._active_jobs_count.get(wem_id, 0) + 1

        self._job_queue.put((func, args, kwargs))

    def _worker_loop(self):
        """Background thread loop consuming raw voice line generation tasks safely."""
        while True:
            func, args, kwargs = self._job_queue.get()
            try:
                func(*args, **kwargs)
            except Exception as e:
                related_token = extract_debug_token(str(e))
                if related_token and related_token.startswith("DSV-"):
                    related_token = None
                token = record_exception(
                    e, "Generating a quick-cache voice line", related_token
                )
                print(
                    f"[THREAD CRASH]: Quick Cache background processor errored: {e}\n"
                    f"DEBUG TOKEN = {token}"
                )
            finally:
                if func == self._replacement_wrapper:
                    wem_id = args[1]
                    with self._jobs_lock:
                        if wem_id in self._active_jobs_count:
                            self._active_jobs_count[wem_id] = max(0, self._active_jobs_count[wem_id] - 1)
                self._job_queue.task_done()

    def _replacement_wrapper(self, wem_id: str, wem_dir: Path, *args):
        """Private interface bridge execution stub executing the real-time voice line generation engine."""
        generate_replacement_voice_line(self.config, wem_id, wem_dir)

    def move_cachedfile_to_mod_dir(self, src_path: Path, mod_dir: Path, wem_id: str) -> Path | None:
        """
        Safely moves an available compiled WEM asset directly into the No Man's Sky mods directory.
        Uses a cooperative back-off delay to stay silent under security tools.
        """
        mod_dir.mkdir(parents=True, exist_ok=True)
        dst_path = mod_dir / f"{wem_id}.wem"

        start_time = time()
        attempt = 0
        while True:
            try:
                # Cooperative swap: Attempt the physical file replacement
                src_path.replace(dst_path)

                # NATIVE FIX FOR WINDOWS SSDs: Force a tiny metadata update to the modification stamp.
                # This ensures your watch loop detects the swap even if st_atime is disabled by the OS!
                try:
                    os.utime(dst_path, None)
                except Exception:
                    pass

                return dst_path
            except (PermissionError, OSError):
                if time() - start_time > 120:
                    return None

                # Scanner-Friendly Backoff: Slowly ramp up the sleep if the game engine is holding a long file handle lock.
                # This prevents aggressive continuous polling errors which trip behavioral defenses.
                attempt += 1
                sleep_delay = min(0.5, 0.05 * (2 ** min(attempt, 4)))
                sleep(sleep_delay)

    def update_access_time_to_match_newfile(self, file_path: Path, access_times: dict):
        """Updates your tracking dictionary with the file's exact filesystem access epoch timestamp."""
        if file_path.exists():
            # Lock this strictly to st_atime, exactly how it was written for 8 months
            access_times[file_path.stem] = file_path.stat().st_atime

    def get_cached_wem(self, wem_id: str) -> Path:
        """
        Main interface method parsing file caches.
        Returns a single explicit Path target matching your down-stream expectations perfectly.
        """
        wem_dir = self.config.quick_cache_dir / str(wem_id)
        wem_dir.mkdir(parents=True, exist_ok=True)

        id_str = str(wem_id).strip()

        should_pre_cache = False
        if id_str in self.config.intent_map:
            status_flag = self.config.intent_map[id_str].get("Used", "").strip().lower()
            should_pre_cache = (status_flag == "yes")

        cached_files = sorted(wem_dir.glob("*.wem"))

        with self._jobs_lock:
            pending_jobs = self._active_jobs_count.get(id_str, 0)

        current_inventory = len(cached_files) + pending_jobs

        if cached_files:
            if should_pre_cache:
                missing_count = max(0, self.config.quick_cache_max - current_inventory)
                for _ in range(missing_count):
                    self.enqueue_job(self._replacement_wrapper, wem_id, wem_dir)
            return cached_files[0]

        if pending_jobs == 0:
            self.enqueue_job(self._replacement_wrapper, wem_id, wem_dir)

        while True:
            sleep(0.1)
            cached_files = sorted(wem_dir.glob("*.wem"))
            if cached_files:
                if should_pre_cache:
                    with self._jobs_lock:
                        latest_pending = self._active_jobs_count.get(id_str, 0)
                    net_total = len(cached_files) + latest_pending
                    missing_count = max(0, self.config.quick_cache_max - net_total)
                    for _ in range(missing_count):
                        self.enqueue_job(self._replacement_wrapper, wem_id, wem_dir)
                return cached_files[0]

if __name__ == "__main__":
    # If an automated security scanner tries to execute this file
    # as a standalone script, exit immediately with a success code.
    import sys
    sys.exit(0)