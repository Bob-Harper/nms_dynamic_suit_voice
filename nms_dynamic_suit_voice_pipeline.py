import time
from modular.tray_ui import TrayUI
from modular.config import SuitVoiceConfig
from modular.quick_cache import get_cached_wem, move_cachedfile_to_mod_dir, update_access_time_to_match_newfile
from debug.logging_utils import debug_print

config = SuitVoiceConfig()


def watch_wems(tray_ui):
    """Main watchdog loop for WEM files."""

    # Build initial access time mapping
    access_times = {f3.stem: f3.stat().st_atime for f3 in tray_ui.config.mod_dir.glob("*.wem")}
    debug_print("nms_dynamic_suit_voice_pipeline.py: Watching for file access...")

    while tray_ui.running:
        for f3 in config.mod_dir.glob("*.wem"):
            try:
                current_atime = f3.stat().st_atime
                wem_id = f3.stem
                if current_atime != access_times.get(wem_id, 0):
                    debug_print(f"nms_dynamic_suit_voice_pipeline.py: Access detected for {f3.name} (ID: {wem_id})")

                    cached_file = get_cached_wem(config, wem_id)
                    debug_print(f"nms_dynamic_suit_voice_pipeline.py: Cached file obtained for ID {wem_id}: {cached_file.name}")

                    moved_file = move_cachedfile_to_mod_dir(cached_file, config.mod_dir, wem_id)
                    debug_print(f"nms_dynamic_suit_voice_pipeline.py: File moved to mod_dir for ID {wem_id}: {moved_file.name}")

                    update_access_time_to_match_newfile(moved_file, access_times)
                    debug_print(f"nms_dynamic_suit_voice_pipeline.py: {wem_id} access time updated. Returning to Watching.")

            except Exception as e:
                debug_print(f"nms_dynamic_suit_voice_pipeline.py:  Error handling {f3.name}: {e}")

        time.sleep(config.check_interval)


if __name__ == "__main__":
    tray_ui = TrayUI(config, watch_wems)
    debug_print("nms_dynamic_suit_voice_pipeline.py: Watcher Started...")
    tray_ui.run()
