import os
import win32con
import win32file
import win32event
from time import sleep
from pathlib import Path

# Bring in your explicit project dependencies cleanly
from .quick_cache import QuickCacheEngine
from .debug_support import record_exception

def watch_wems(engine, config):
    """Run the native win32 filesystem listener cleanly with absolute type alignment."""

    # --- PHASE 1: Initialize Coqui-TTS Engine Weights ---
    if not engine.running:
        return
    engine.update_status("Loading TTS Voice Models...")

    qce = QuickCacheEngine(config)

    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    from TTS.api import TTS
    if not engine.running:
        return
    config.tts_model = TTS(model_name=config.tts_model_name)

    # --- PHASE 2: Initialize Llama-cpp Core Engine weights ---
    if not engine.running:
        return
    engine.update_status("Loading Local AI...")

    from llama_cpp import Llama
    if not engine.running:
        return
    config.llm = Llama(
        model_path=config.llm_model,
        n_ctx=40960,
        n_batch=1024,
        n_threads=4,
        verbose=False
    )

    # --- PHASE 3: Verify Filesystem Watches ---
    if not engine.running:
        return
    engine.update_status("Verifying Directories...")
    mod_dir = config.mod_dir
    if not mod_dir or not mod_dir.exists():
        raise FileNotFoundError(f"Mod directory does not exist: {mod_dir}")

    # --- PHASE 4: Initialization Complete, Launch Active Oplock Watch ---
    engine.update_status("Ready", is_ready=True)

    from .oplock_watch import OplockWatch

    # Instantiate the low-overhead native Win32 tripwire engine
    watcher = OplockWatch()

    # Map out the exact list of 220 active track target ids from your game directory
    tracked_ids = [f3.stem for f3 in mod_dir.glob("*.wem")]
    watcher.set_target(mod_dir, tracked_ids)

    print(f"[WATCHER CORE]: Armed Level-1 Oplock tripwires across {len(tracked_ids)} assets natively.")

    while engine.running:
        try:
            # 1. Periodically re-arm broken lock handles or fresh files we just swapped
            watcher.maintain(tries=12)

            # 2. Passively listen for kernel lock break signals with zero CPU load
            broken_ids = watcher.poll_ack(timeout=0.05)

            for wem_id in broken_ids:
                print(f"[KERNEL INTERCEPT]: Oplock tripwire snapped on file track: {wem_id}.wem")

                # Fetch the corresponding variation asset out of your cache engine queue
                cached_file = qce.get_cached_wem(wem_id)
                if cached_file is None:
                    continue

                # Tell the watcher to ignore our upcoming file-move operation write event
                watcher.suppress(wem_id, seconds=0.5)

                # Swap the target file seamlessly in place
                moved_file = qce.move_cachedfile_to_mod_dir(cached_file, mod_dir, wem_id)

                # Tell the watcher to immediately re-arm the tripwire loop on the fresh asset file handle
                if moved_file is not None:
                    watcher.rearm(wem_id)

        except Exception as w_e:
            token = record_exception(
                w_e,
                "Oplock watch event loop execution failure",
                related_token="OPLOCK_WATCH_ERR",
            )
            print(f"DEBUG TOKEN = OPLOCK_WATCH_ERR >> Oplock stream error: {w_e} | ID: {token}")
            sleep(0.1)

    # Clean release pass when the engine drops out
    watcher.close()
