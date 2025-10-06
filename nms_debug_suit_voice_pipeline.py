# nms_debug_suit_voice_pipeline_debug.py

import time
from modular.tray_ui import TrayUI
from modular.tts_utils import run_tts
from modular.config import SuitVoiceConfig
from modular.llm_utils import reword_phrase
from debug.wem_utils import convert_to_wem
from modular.logging_utils import log_to_file
from modular.prompt_utils import build_suit_prompt
from debug.log_config import logger  # <-- Loguru setup

config = SuitVoiceConfig()

def watch_wems(tray_ui):  # Main watchdog and pipeline
    access_times = {f3: f3.stat().st_atime for f3 in tray_ui.config.mod_dir.glob("*.wem")}
    logger.info("Initialized access_times for existing WEM files.")
    print("Watching for file access...")
    logger.info("Started WEM file access watcher loop.")
    while tray_ui.running:
        for f3 in config.mod_dir.glob("*.wem"):
            try:
                current_atime = f3.stat().st_atime
                if current_atime != access_times.get(f3, 0):
                    wem_id = f3.stem
                    logger.debug(f"Access detected: {f3.name} (ID: {wem_id})")
                    print(f"Access detected: {f3.name} (ID: {wem_id})")
                    start_time = time.time()

                    # Review cache dir for unmoved wem left by a previous pass error
                    cached_wem = config.temp_wem_dir / f"{wem_id}.wem"
                    if cached_wem.exists():
                        final_wem_file = config.mod_dir / cached_wem.name
                        try:
                            final_wem_file = config.mod_dir / cached_wem.name
                            cached_wem.replace(final_wem_file)
                            logger.success(f"Used prior cached WEM from holding pen: {final_wem_file}")
                            print(f"Pipeline done for {wem_id} (cache hit).")
                            continue  # no conversion needed, cached file movd, resume watcher
                        except Exception as e:
                            logger.warning(f"Could not move cached WEM {cached_wem} -> {final_wem_file}: {e}")
                            # Multiple unsucessful moves attempted, generate a new wem.

                    # Determination made to generate a new wem file.
                    if wem_id in config.intent_map:
                        intent_entry = config.intent_map[wem_id]
                        original_phrase_w = intent_entry["Transcription"]
                        category = intent_entry["Category"]
                        intent_w = intent_entry["Intent"]

                        logger.trace(f"Intent match found for {wem_id}: {intent_entry}")
                        finalprompt = build_suit_prompt(config, category, intent_w, original_phrase_w)
                        logger.debug(f"Prompt built for {wem_id}")

                        reworded = reword_phrase(config, wem_id, original_phrase_w, intent_w, finalprompt)
                        logger.debug(f"Reworded phrase for {wem_id}")

                        if config.logging:
                            log_to_file(config, wem_id, category, intent_w, original_phrase_w, reworded)
                            logger.trace(f"Logged to file for {wem_id}")

                        print(f"\033[92m{original_phrase_w}\033[0m")
                        logger.info(f"Original phrase: {original_phrase_w}")

                        try:
                            temp_wav_path = run_tts(config, reworded, wem_id)
                            logger.debug(f"WAV generated for {wem_id}: {temp_wav_path}")
                        except Exception as e3:
                            logger.exception(f"Error creating WAV for {wem_id}: {e3}")
                            print(f"Error creating WAV: {e3}")
                            continue

                        try:
                            convert_to_wem(config, temp_wav_path)
                            logger.debug(f"WEM conversion complete for {wem_id}")
                        except Exception as e3:
                            logger.exception(f"Error converting to WEM for {wem_id}: {e3}")
                            print(f"Error converting to WEM: {e3}")
                            continue

                        final_wem_path = config.mod_dir / f"{wem_id}.wem"
                        if final_wem_path.exists():
                            access_times[final_wem_path] = final_wem_path.stat().st_atime
                            logger.trace(f"Updated access time for {final_wem_path}")
                        else:
                            logger.warning(f"WEM file not found after conversion: {final_wem_path}")
                            print(f"WEM file not found after conversion: {final_wem_path}")

                        new_wem = config.mod_dir / f"{wem_id}.wem"
                        if new_wem.exists():
                            access_times[new_wem] = new_wem.stat().st_atime
                            logger.trace(f"Confirmed existence of new WEM: {new_wem}")
                    else:
                        logger.warning(f"No intent found for WEM ID {wem_id}, skipping.")
                        print(f"No intent found for WEM ID {wem_id}, skipping.")

                    elapsed = time.time() - start_time
                    logger.info(f"Elapsed time for {wem_id}: {elapsed:.2f} seconds")
                    print(f"Elapsed time: {elapsed:.2f} seconds")
                    print("Watching for file access...")
            except Exception as e3:
                logger.exception(f"Error handling {f3.name}: {e3}")
                print(f"Error handling {f3.name}: {e3}")

        time.sleep(config.check_interval)
        # logger.trace(f"Slept for {config.check_interval} seconds.")

if __name__ == "__main__":
    logger.info("Launching TrayUI with watch_wems.")
    tray_ui = TrayUI(config, watch_wems)
    tray_ui.run()
