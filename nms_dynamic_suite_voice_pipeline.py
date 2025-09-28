import time
from modular.tray_ui import TrayUI
from modular.tts_utils import run_tts
from modular.config import SuitVoiceConfig
from modular.llm_utils import reword_phrase
from modular.wem_utils import convert_to_wem
from modular.logging_utils import log_to_file
from modular.prompt_utils import build_suit_prompt
config = SuitVoiceConfig()


def watch_wems(tray_ui):  # Main watchdog and pipeline
    access_times = {f3: f3.stat().st_atime for f3 in tray_ui.config.mod_dir.glob("*.wem")}
    print("Watching for file access...")
    while tray_ui.running:
        for f3 in config.mod_dir.glob("*.wem"):
            try:
                current_atime = f3.stat().st_atime
                if current_atime != access_times.get(f3, 0):
                    wem_id = f3.stem  # Extract ID from filename (without extension)
                    print(f"Access detected: {f3.name} (ID: {wem_id})")

                    if wem_id in config.intent_map:
                        intent_entry = config.intent_map[wem_id]
                        original_phrase_w = intent_entry["Transcription"]
                        category = intent_entry["Category"]
                        intent_w = intent_entry["Intent"]

                        finalprompt = build_suit_prompt(config, category, intent_w, original_phrase_w)

                        reworded = reword_phrase(config, wem_id, original_phrase_w, intent_w, finalprompt)
                        if config.logging:
                            log_to_file(config, wem_id, category, intent_w, original_phrase_w, reworded)
                        print(original_phrase_w)

                        try:
                            temp_wav_path = run_tts(config, reworded, wem_id)
                        except Exception as e3:
                            print(f"Error creating WAV: {e3}")
                            continue

                        try:
                            convert_to_wem(config, temp_wav_path)
                        except Exception as e3:
                            print(f"Error converting to WEM: {e3}")
                            continue

                        # WEM goes straight into mod_dir now
                        final_wem_path = config.mod_dir / f"{wem_id}.wem"

                        if final_wem_path.exists():
                            access_times[final_wem_path] = final_wem_path.stat().st_atime
                        else:
                            print(f"WEM file not found after conversion: {final_wem_path}")

                        new_wem = config.mod_dir / f"{wem_id}.wem"
                        if new_wem.exists():
                            access_times[new_wem] = new_wem.stat().st_atime

                    else:
                        print(f"No intent found for WEM ID {wem_id}, skipping.")
                    print("Watching for file access...")
            except Exception as e3:
                print(f"Error handling {f3.name}: {e3}")

        time.sleep(config.check_interval)

if __name__ == "__main__":
    tray_ui = TrayUI(config, watch_wems)
    watch_wems(tray_ui)

