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
                    wem_id = f3.stem
                    print(f"Access detected: {f3.name} (ID: {wem_id})")
                    start_time = time.time()

                    # Review cache dir for unmoved wem left by a previous pass error
                    cached_wem = config.temp_wem_dir / f"{wem_id}.wem"
                    if cached_wem.exists():
                        final_wem_file = config.mod_dir / cached_wem.name
                        try:
                            final_wem_file = config.mod_dir / cached_wem.name
                            cached_wem.replace(final_wem_file)
                            print(f"Used prior cached WEM from holding pen: {final_wem_file}")
                            continue  # no conversion needed, cached file movd, resume watcher
                        except Exception as e:
                            print(f"Could not move cached WEM {cached_wem} -> {final_wem_file}: {e}")
                            # Multiple unsucessful moves attempted, generate a new wem.

                    # Determination made to generate a new wem file.
                    if wem_id in config.intent_map:
                        intent_entry = config.intent_map[wem_id]
                        original_phrase_w = intent_entry["Transcription"]
                        category = intent_entry["Category"]
                        intent_w = intent_entry["Intent"]

                        finalprompt = build_suit_prompt(config, category, intent_w, original_phrase_w)

                        reworded = reword_phrase(config, wem_id, original_phrase_w, intent_w, finalprompt)

                        if config.logging:
                            log_to_file(config, wem_id, category, intent_w, original_phrase_w, reworded)

                        print(f"\033[92m{original_phrase_w}\033[0m")

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

                    elapsed = time.time() - start_time
                    print(f"Elapsed time: {elapsed:.2f} seconds")
                    print("Watching for file access...")
            except Exception as e3:
                print(f"Error handling {f3.name}: {e3}")

        time.sleep(config.check_interval)

if __name__ == "__main__":
    tray_ui = TrayUI(config, watch_wems)
    tray_ui.run()

"""
thoughts, notes, to do list, ideas

rebase the prompts around Standard -  emotionally stunted Vulcan reading from a technical datasheet persona is effective, wording gives consistent (i think) results.

update console output to show the final output?  or leave it a surprise.

New tone idea:  Fortune Cookie, complete with Your Lucky Numbers are 

turn off Thinking output and see how it does with the new prompting setup now that we can see what it's thinking and why it ignores instruction.

csv fixed the units/money issue.  the prompt_data.json STILL has older references, we need to bring them inline with the csv.

what was i thinking this needs serious rewording:
"Poetic": "Render the notification in a 2-sentence Romantic Era rhyming couplet, using vivid metaphorical language in the style of Shelley, Byron, and Keats. Address {name} directly as 'you', describing the experience only as it affects you. Do not place {name} or {name} as a subject; use strict second-person throughout.",
same with epic.  Speak directly to {name} in present tense as 'you', showing events only as they affect you
. Focus on how this experience relates to {name} and possible absurd outcome where the outcome will eventually be futile; nothing should be narrated in third person.",
Speak directly to {name} in present tense as 'you', describing the prophecy only in terms of how it affects you.
"Philosophical": "Provide a deeply profound philosophical interpretation of the possible impact on {name}. Address {name} directly in present tense as 'you', reflecting only on your experience










"""
