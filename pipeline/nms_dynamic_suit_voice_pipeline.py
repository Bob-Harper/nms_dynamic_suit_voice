# nms_dynamic_suit_voice_pipeline.py (Streamlined Version)
import time
import os
from pathlib import Path
from pipeline.quick_cache import QuickCacheEngine
# from pipeline.quick_cache import get_cached_wem, move_cachedfile_to_mod_dir, update_access_time_to_match_newfile
from PIL import Image


def watch_wems(wtray_ui, config):
    """Main watchdog thread invoked after the launcher completes fast boot."""

    # --- PHASE 1: Initialize Coqui-TTS Engine Weights ---
    wtray_ui.icon.title = "Dynamic Suit Voice - Loading TTS Voice Models..."

    qce = QuickCacheEngine(config)

    # Prevent HuggingFace from attempting cloud updates on boot (this can be toggled elsewhere on demand as needed)
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    from TTS.api import TTS
    config.tts_model = TTS(model_name=config.tts_model_name)

    # --- PHASE 2: Initialize Llama-cpp Core Engine weights ---
    wtray_ui.icon.title = "Dynamic Suit Voice - Loading Local AI..."

    from llama_cpp import Llama
    config.llm = Llama(
        model_path=config.llm_model,
        n_ctx=40960,
        n_batch=1024,
        n_threads=4,
        verbose=False
    )

    # --- PHASE 3: Verify Filesystem Watches ---
    wtray_ui.icon.title = "Dynamic Suit Voice - Verifying Directories..."
    mod_dir = config.mod_dir
    if not mod_dir or not mod_dir.exists():
        wtray_ui.icon.title = "Dynamic Suit Voice - Error: Missing Dirs"
        return

    access_times = {f3.stem: f3.stat().st_atime for f3 in mod_dir.glob("*.wem")}

    # --- PHASE 4: Initialization Complete, Launch Active Watch ---
    # Restore native transparency by swapping the icon out directly
    root_dir = Path(__file__).parent
    if wtray_ui.ready_icon_path.exists():
        # Open a fresh copy and preserve the full RGBA alpha transparency channel
        wtray_ui.icon.icon = Image.open(wtray_ui.ready_icon_path).convert("RGBA")

    wtray_ui.icon.title = "Dynamic Suit Voice 1.2 - Ready"
    check_interval = config.check_interval

    while wtray_ui.running:
        for f3 in mod_dir.glob("*.wem"):
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
                print(f"DEBUG TOKEN = TRAYWATCHER_EXC >> Error handling {f3.name}: {w_e}")

        time.sleep(check_interval)
