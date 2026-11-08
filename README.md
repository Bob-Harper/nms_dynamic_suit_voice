# Dynamic No Man’s Sky Suit AI Voice Mod

Version: 1.3.3 (Unchained.DBG)<br>
Author: [[Bob-Harper](https://github.com)]<br>
Repository: [[nms_dynamic_suit_voice](https://github.com)]

## Overview

This mod replaces static exosuit AI voice lines in No Man’s Sky with dynamically generated, non-repetitive lines, powered by a local AI model and localized audio DSP filters.

### Non-Negotiable Core Mandates:
- **Local files ONLY.** No cloud processing, LLM and TTS odels are downloaded then stored locally, and absolutely no paid API subscription keys.
- **ENHANCE gameplay but NOT at the EXPENSE of gameplay.** Hardware footprints are stringently guarded.
- **Strict Single-Use Policy.** When pre-caching, generated audio files are completely overwritten after a single use, never reused.

## How the Tech Works

When No Man's Sky makes a sound call to play a suit voice line, it reads the physical file it finds inside your mod directory *at the exact moment it searches*. The game does NOT preload mod voice files into system memory when it launches. They load and play **EACH TIME** the game calls for that specific `.wem` file block, then are immediately unloaded until called again.

Because the local pipeline generates variations ahead of time into a background cache, the system watcher instantly swaps a fresh file into your game folder, and proceeds to replenish the cache while you are still playing. Every notification is completely new — even when mass-selling stacks of items at a space station terminal. No more repetitive *"Units Received. Units Received. Units Received."*

## Key Features (As of v1.2.1)

- **Standalone Architecture:** The Audiokinetic Wwise SDK requirement has been completely replaced by an included lightweight converter. No software accounts, corporate registration, or heavy background installations of programs or third party software are required.  (LLM and TTS models still required)
- **Pure-Python DSP Matrix Engine:** FFmpeg requirement and sub-process loop has been removed. Volume gain, sentence tempo stretchings, and pitch adjustments are now handled entirely in-memory via single-pass NumPy/SciPy matrix math.
- **Open-Source Audio Converter:** The installer retrieves the WEM converter from its separate project repository; its executable is not bundled in the Nexus source archive.
- **Centralized Control Dashboard:** A graphical config interface to customize iteration names, swap engines, adjust multi-threaded look-ahead queues, or fine-tune processing effects.
- **Stateful Quick Cache System:** Thread-isolated background queue managers top up caches and intelligently handle file locks without breaking game focus.
- **Protected VRAM Performance:** Runs lightweight models on CPU thread inference layouts, leaving your GPU completely free to push maximum frame rates to the game.

### Persistent User Configuration Matrix
Profile and voice customizations are saved to `config/user_customization.json`, which is kept separate from project updates. System settings such as paths, watcher timing, cache limits, and update preferences are saved in `config/environment_config.json`.

- **First-Time Installation:** If this configuration file does not exist on your drive, the automated setup script will initialize it cleanly.
- **Upgrading the Mod:** If the custom settings file already exists, the engine boundaries will completely shield it from being touched.
- **Power-User Manipulation:** The Qt control deck reads this profile and saves changes when applying or saving settings. Power users can also edit these files with a plain-text editor.

## Examples of Dynamic Output Variations

- **Original Game Wording:** *Nearby toxins detected*
  - ↳ *Corrosive environmental toxins are causing damage to your suit's protective filters.*
  - ↳ *Corrosive environmental toxins are threatening the effectiveness of your suit's protective filters.*
  - ↳ *Corrosive environmental contaminants are debilitating your suit’s filtration system.*

- **Original Game Wording:** *Extreme Night Temperature Detected*
  - ↳ *Extreme night cold temperatures are reported, posing a threat to life support.*
  - ↳ *Extreme cold temperatures during the night cycle are detected, risking safety systems.*

## Current Verified Limitations

- **Mod Conflicts:** Completely incompatible with traditional static suit voice mods that drop pre-recorded audio `.wem` files directly into your standard game `MODS` folder.  Remove and backup any previous files you may have in DYNAMIC_SUIT_VOICE\AUDIO\WINDOWS\MEDIA\ENGLISH(US) lest they be overwritten and lost forever.<br><br>
- **VITS Architecture Block:** Advanced multi-speaker VITS models are intentionally excluded from the scan loader at this time to protect end-users from requiring installation of external C++ system binaries (such as eSpeak NG) onto their primary Windows environment paths.<br><br>
- **Voice Clone capability:** Unsupported at this time as I have an aversion to getting strongly worded letters from Morgan Freeman's lawyers.


## Installation & Deployment

### Install
Install Python 3.11, extract the download, open a terminal in the extracted project folder, and run:
```powershell
py -3.11 installer.py
```
Choose **Automatic Mode** for a streamlined setup, or run the installer steps individually. The installer creates its isolated `venv`, installs dependencies, prepares the local assets, and creates desktop shortcuts. No `.cmd` launcher is required.

### Launching the DSV
Double-click either generated desktop shortcut to open the unified Qt control deck. Use **ENGAGE AI CORE** to start monitoring your game directory. Closing the window hides it in the system tray; choose **Show Control Deck** to reopen it, or **Close everything completely** to stop the watcher and exit.

The **NMS Dynamic Suit Voice** and **Exosuit Companion** shortcuts now open the same control deck. Configure your **Iteration Designation**, voice model, audio presets, and system settings there without editing source code. **Save & Minimize** saves settings and hides the window in the tray; **Apply Changes** saves while leaving the control deck open.

### Enhanced Debug and Support
Open the **Debug** panel and enter a token from an error message to see its explanation, likely causes, and suggested repair steps. Some entries can take you to the relevant settings panel; System Settings will still require its acknowledgement.

Unexpected exceptions receive a `DSV-...` incident token. The matching traceback is saved locally in `logs/debug_reports.jsonl` and can be retrieved by entering that token on the same installation. Diagnostic reports may include local file paths and error details, are not uploaded automatically, and are excluded from Git. Review and redact details before sharing them in a GitHub issue. The **Open GitHub issues** button only opens the website; it does not submit a report.

### System Settings and Optional Updates
The System page starts with an acknowledgement because most users should not need to change its settings. It contains separate Update, Cache, Runtime, and Paths panels. Changes are saved to the configuration files; path changes require an application restart.

Update management supports two optional workflows:

- **Git-tracked install:** Check the configured GitHub branch, convert an extracted install to a tracked repository, and pull updates when local project files can be safely fast-forwarded. Conversion does not replace existing project files. Local project edits block a pull rather than being overwritten.
- **ZIP install:** Download the configured branch ZIP, back up your configuration, extract the ZIP over the existing installation, then run `py -3.11 installer.py` from the project folder again.

Update checks and downloads are always user-initiated through the System > Updates panel; the application does not update itself automatically. The repository URL and branch are configuration values in `config/environment_config.json`.

## Future Framework Roadmap
- **Multiple Profiles:** Allow users to to users to name and store their own created configurations and audio presets.
- **User Config Backup:** define a storage location outside the project structure to ensure user-created files are safe even if extinction level events occur.
- **Expanded Cache Management:** Add further cache policy controls after the current storage and purge workflow has been validated.
- **Additional TTS Models:** Adding an Advanced button to the model tab in the Qt control deck to show the full list of available models regardless of requirements or capabilities.

## Licensing & Third-Party Open Source Attributions

Distributed fully open-source under the MIT License. See `LICENSE` for details.

* **`wav2wem` Audio Converter:** The installer retrieves the converter from the separate project repository. Review its source, build instructions, and license at [Bob-Harper/wav2wem](https://github.com/Bob-Harper/wav2wem), originally based on [pas2k/wav2wem](https://github.com/pas2k/wav2wem).

## Special Acknowledgments
- **[EternalLeo](https://github.com/EternalLeo):** The excellent [sound2wem](https://github.com/EternalLeo/sound2wem) utility which acted as the springboard to launch this project and provided the original proof of concept. This project would not exist without his research.
- **[Kilvoctu](https://github.com/Kilvoctu):** Excellent suggestions, thank you for giving me much to ponder and helping elevate the codebase.
- **The Nexus Mods Suit Audio Community:** Gratitude to all original voice modders and commenters whose forum feedback helped isolate the exact filesystem directories the game monitors.
- **Sean Murray & Hello Games:** Deep thanks for crafting the definitive cosmic sandbox universe we waited all these years to explore.
