import os
import win32con
import win32file
import win32event
from time import sleep
from pathlib import Path

from .quick_cache import QuickCacheEngine
from .debug_support import record_exception

def watch_wems(engine, config, console_pipe=None):

    # --- PHASE 1: Initialize Kokoro-TTS Engine ---
    if not engine.running:
        return
    engine.update_status("Loading Kokoro TTS Engine...")

    qce = QuickCacheEngine(config)

    if not engine.running:
        return
    from kokoro_onnx import Kokoro
    import onnxruntime as ort
    ort.set_default_logger_severity(3)  # 0:Verbose, 1:Info, 2:Warning, 3:Error

    model_path = config.tts_model
    voices_path = config.tts_voice_bin

    config.tts_model = Kokoro(str(model_path), str(voices_path))

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

    # --- PHASE 4: Initialization Complete, Launch Oplock Watch ---
    engine.update_status("Ready", is_ready=True)

    from .oplock_watch import OplockWatch
    watcher = OplockWatch()

    # CENTRALIZED ASSET FILTERING: Pull only the frequently used voice line IDs
    try:
        # config.intent_map holds loaded nms_suit_voice_transcripts.json data dictionary
        active_voice_profiles = config.intent_map

        # Filter the dictionary keys down to assets explicitly marked as Used == Yes
        frequently_used_ids = {
            wem_id for wem_id, metadata in active_voice_profiles.items()
            if metadata.get("Used") == "Yes"
        }
    except Exception as e:
        print(f"[WATCHER CORE WARNING]: Failed filtering via 'Used' flag, falling back to all keys: {e}")
        frequently_used_ids = set(config.intent_map.keys())

    # Map out the file list matching active intent tracking targets
    tracked_ids = [
        f3.stem for f3 in mod_dir.glob("*.wem")
        if f3.stem in frequently_used_ids
    ]

    watcher.set_target(mod_dir, tracked_ids)
    print(f"[WATCHER CORE]: Focused Level-1 Oplock tripwires across {len(tracked_ids)} high-frequency voice assets.")

    while engine.running:
        try:
            # Periodically re-arm broken lock handles or fresh files just swapped
            watcher.maintain(tries=12)

            # Passively listen for kernel lock break signals
            broken_ids = watcher.poll_ack(timeout=0.05)

            for wem_id in broken_ids:
                # Thread-safe log dispatch pipes kernel events straight onto the console tab view  ## BROKEN, TRYING AGAIN LATER
                if hasattr(config, "ui_console") and config.ui_console is not None:
                    config.ui_console.append_log_signal.emit(
                        f"[KERNEL INTERCEPT]: Oplock tripwire snapped on file track: {wem_id}.wem"
                    )

                cached_file = qce.get_cached_wem(wem_id)
                if cached_file is None:
                    continue

                watcher.suppress(wem_id, seconds=0.5)
                moved_file = qce.move_cachedfile_to_mod_dir(cached_file, mod_dir, wem_id)

                if moved_file is not None:
                    # Signal successful dynamic asset injection directly onto the text stream
                    if hasattr(config, "ui_console") and config.ui_console is not None:
                        config.ui_console.append_log_signal.emit(
                            f"[FILESYSTEM SWAP]: Seamlessly deployed fresh variation track for {wem_id}.wem"
                        )
                    watcher.rearm(wem_id)

        except Exception as w_e:
            token = record_exception(
                w_e,
                "Oplock watch event loop execution failure",
                related_token="OPLOCK_WATCH_ERR",
            )
            print(f"DEBUG TOKEN = OPLOCK_WATCH_ERR >> Oplock stream error: {w_e} | ID: {token}")
            sleep(0.1)

    # release when the engine stops
    watcher.close()
