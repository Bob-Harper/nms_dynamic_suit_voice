# nms_dynamic_suit_voice_pipeline.py (Streamlined Version)
import os
from .quick_cache import QuickCacheEngine
from .debug_support import record_exception
# from pipeline.quick_cache import get_cached_wem, move_cachedfile_to_mod_dir, update_access_time_to_match_newfile


def watch_wems(engine, config):
    """Run the watcher on the control deck's engine thread."""

    # --- PHASE 1: Initialize Coqui-TTS Engine Weights ---
    if not engine.running:
        return
    engine.update_status("Loading TTS Voice Models...")

    qce = QuickCacheEngine(config)

    # Prevent HuggingFace from attempting cloud updates on boot (this can be toggled elsewhere on demand as needed)
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

    access_times = {f3.stem: f3.stat().st_atime for f3 in mod_dir.glob("*.wem")}

    # --- PHASE 4: Initialization Complete, Launch Active Watch ---
    engine.update_status("Ready", is_ready=True)
    check_interval = config.check_interval

    while engine.running:
        for f3 in mod_dir.glob("*.wem"):
            if not engine.running:
                break
            try:
                current_atime = f3.stat().st_atime
                wem_id = f3.stem
                if current_atime != access_times.get(wem_id, 0):

                    cached_file = qce.get_cached_wem(wem_id)
                    if cached_file is None:
                        continue

                    moved_file = qce.move_cachedfile_to_mod_dir(cached_file, mod_dir, wem_id)
                    if moved_file is None:
                        continue

                    qce.update_access_time_to_match_newfile(moved_file, access_times)

            except Exception as w_e:
                token = record_exception(
                    w_e,
                    f"Processing watched WEM file {f3.name}",
                    related_token="TRAYWATCHER_EXC",
                )
                print(
                    f"DEBUG TOKEN = TRAYWATCHER_EXC >> "
                    f"Error handling {f3.name}: {w_e}\n"
                    f"Incident: DEBUG TOKEN = {token}"
                )

        engine.stop_event.wait(check_interval)
