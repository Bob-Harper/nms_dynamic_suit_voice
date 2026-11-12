# Dynamic No Man’s Sky Suit AI Voice Mod

Version: 1.4.2 (Nexus.QUEEG)
Author: [Bob-Harper](https://github.com)
Repository: [nms_dynamic_suit_voice](https://github.com)

## Overview

This mod replaces static exosuit AI voice lines in No Man’s Sky with dynamically generated, non-repetitive lines, powered by a local AI model and localized audio DSP filters.

### Non-Negotiable Core Mandates:
- **Local files ONLY.** No cloud processing, LLM and TTS models are downloaded then stored locally
- **Absolutely Free.** Absolutely no paid API subscription keys or associated costs.
- **100% Open Source.** Absolutely no proprietary software used or included.  All source code publically accessible with permissive licensing.  Fork the code over as you will with this author's blessing and support.
- **ENHANCE gameplay but NOT at the EXPENSE of gameplay.** Hardware footprints are stringently guarded, no GPU needed or used
- **Strict Single-Use Policy.** When pre-caching, generated audio files are completely overwritten after a single use, never reused.

## How the Tech Works

When No Man's Sky makes a sound call to play a suit voice line, it reads the physical file it finds inside your mod directory *at the exact moment it searches*. The game does NOT preload mod voice files into system memory when it launches. They load and play **EACH TIME** the game calls for that specific `.wem` file block, then are immediately unloaded until called again.

Because the local pipeline generates variations ahead of time into a background cache, the system watcher instantly swaps a fresh file into your game folder, and proceeds to replenish the cache while you are still playing. Every notification is completely new — even when mass-selling stacks of items at a space station terminal. No more repetitive *"Units Received. Units Received. Units Received."*

## Key Features (As of v1.4.0)
- **Fully converted to Kokoro ONNX** TTS processing is now faster, more efficient, and has both Male and Female base voices to choose from.
- **Centralized Control Dashboard:** A graphical config interface to launch and quit the tool, customize player name, adjust multi-threaded look-ahead queues, or fine-tune processing effects.
- **Standalone Architecture:** The Audiokinetic Wwise SDK requirement has been completely replaced by an included lightweight converter. No software accounts, corporate registration, or heavy background installations of programs or third party software are required. (LLM and TTS models still required)
- **Pure-Python DSP Matrix Engine:** ffmpeg requirement and sub-process loops have been removed. Volume gain, sentence tempo stretchings, and other adjustments are now handled entirely in-memory via single-pass NumPy matrix math.
- **Open-Source Audio Converter:** The installer retrieves the WEM converter from its separate project repository; its executable is not bundled in the Nexus source archive.
- **Dedicated Update Panel:** Update through a top level panel for immediate user-initiated version checks and file updates.
- **Stateful Quick Cache System:** Thread-isolated background queue managers to top up caches and intelligently handle file locks without interfering with Game.
- **Protected VRAM Performance:** Runs lightweight models on CPU thread inference, leaving your GPU completely free to push maximum frame rates to the game.
- **Integrated Token-based Debuggin system:**Most known possible issues generate a unique Debug Token which can quickly identify possible issues.  This can be used on the Debug panel within the main interface to access explanations, advice, and expose relevant settings for immediate resolution.  A direct link to the Issues page on the Github Repository is also provided for further discussion and assistance.  Log files are *NOT* transmitted automatically, to ensure user privacy.

### Persistent User Configuration Matrix
Profile and voice customizations are saved to `config/user_customization.json`. System settings such as paths, cache limits, and runtime attributes are saved in `config/environment_config.json`.  These settings will persist through updates.  The first time install ships with a set of default files for both to ensure values are included for initial startup, and as backups should the customized configuration files become unuseable for any reason.

- **First-Time Installation:** If the user configurated files do not exist on your drive, the automated setup script will initialize them with default values cleanly.
- **Upgrading the Mod:** If the custom settings files already exist, the engine boundaries will completely shield them from being touched.
- **Power-User Manipulation:** These files can be edited directly with a plain-text editor. Be careful.

## Examples of Dynamic Output Variations

- **Original Game Wording:** *Nearby toxins detected*
  - ↳ *Corrosive environmental toxins are causing damage to your suit's protective filters.*
  - ↳ *Corrosive environmental toxins are threatening the effectiveness of your suit's protective filters.*
  - ↳ *Corrosive environmental contaminants are debilitating your suit’s filtration system.*

- **Original Game Wording:** *Extreme Night Temperature Detected*
  - ↳ *Extreme night cold temperatures are reported, posing a threat to life support.*
  - ↳ *Extreme cold temperatures during the night cycle are detected, risking safety systems.*

## Current Verified Limitations

- **Mod Conflicts:** Completely incompatible with traditional static suit voice mods that drop pre-recorded audio `.wem` files directly into your standard game `MODS` folder. Remove and backup any previous files you may have in DYNAMIC_SUIT_VOICE\AUDIO\WINDOWS\MEDIA\ENGLISH(US) lest they be overwritten and lost forever.
- **VITS Architecture Block:** Advanced multi-speaker VITS models are intentionally excluded from the scan loader at this time to protect end-users from requiring installation of external C++ system binaries (such as eSpeak NG) onto their primary Windows environment paths.
- **Voice Clone Capability:** Unsupported at this time as I have an aversion to getting strongly worded letters from Morgan Freeman's lawyers.

## Installation & Deployment

### Install
*Please observe that the previous ONE CLICK INSTALL method has been removed for security and safety reasons, and to appease file saftey checkers.*<br>
*Notice that as of this time, due to specific requirements in use, 3.11 is the only Python version officially supported.*<br>
Install Python 3.11, extract the download, open a terminal in the extracted project folder, and run:
```powershell
py -3.11 installer.py
```
Choose **Automatic Mode** for a streamlined setup, or run the installer steps individually. The installer creates its isolated `venv`, installs dependencies, prepares the local assets, and creates desktop shortcuts.

### Launching the DSV Control Deck
Double-click the generated desktop shortcut to open the unified Qt control deck. Use **ENGAGE AI CORE** to start monitoring your game directory. Closing the window with X hides it in the system tray; choose **Show Control Deck** to reopen it, or click **CLOSE EVERYTHING** on the bottom left of the main interface to shut down all processes, clear handles, and kill the application cleanly. You can also cleanly close everything with a dedicated button within the opene interface window.

Configure your **Iteration Designation**, audio presets, and system settings across the layout slots without editing source code. **Save & Minimize** saves settings and hides the window in the tray; **Apply Changes** saves while leaving the control deck open.

### Enhanced Debug Support
Open the **Debug** panel and review recently logged events, or manually enter a Debug token to see its explanation, likely causes, and suggested repair steps. Pre-calibrated tokens will automatically render their associated repair widget (like Paths) right next to your text readout for immediate review and repair.

Unexpected exceptions receive a `DSV-...` incident token. The matching traceback is saved locally in `logs/debug_reports.jsonl` and can be viewed directly in the interface by selecting it in the dropdown list.

**QOL Automation:** The moment an exception popup or error signature is produced by the logging core, the issue is made accessible to the Debug panel. You do not need to write it down or screenshot it; navigate directly to the Debug panel and select it from the dropdown list of recently logged events. Review and redact details before sharing in a GitHub issue. The **Open GitHub issues** button only opens the website; it does not submit a report.

### Standalone Update Tab and Git Operations
The dedicated **Updates Tab** manages workflows out in the open without relying on third-party server approval delays:

- **Live Ecosystem Status Label:** The text reporter right above your actions panel changes continuously to show the step-by-step progress of your network actions (e.g. `Connecting to forge registry...`, `Fetching snapshot...`, etc.) so you always know the app is processing data.
- **Git-tracked install:** Check the configured GitHub branch, convert an extracted install to a tracked repository, and pull updates when local project files can be safely fast-forwarded. Conversion does not replace existing project files. Local project edits block a pull rather than being overwritten.

Update checks and downloads are user-initiated through the Updates panel; the application does not update itself automatically. The repository URL and branch are configuration values in `config/environment_config.json`.

## Future Framework Roadmap
- **Data-Driven Theme Engines:** Moving interface stylesheets, palettes, and typography metrics to a local `interface_theme.json` file for zero-code hot-swappable interface styles.
- **Interface Localization Support:** Transporting all user-facing panel text elements into unhardcoded `.json` localization dictionary matrices for instant regional multi-language translation packs.
- **Multiple Profiles:** Allow users to name and store their own created configurations and audio presets.
- **User Config Backup:** Define a storage location outside the project structure to ensure user-created files are safe even if extinction-level events occur.
- **Additional Voicees/TTM Support:** Consideration underway for expanding/overhauling current options available.  The visible "Load All Models" is a placeholder and intentionally nonfunctional at this time.

## Licensing & Third-Party Open Source Attributions

Distributed fully open-source under the MIT License. See `LICENSE` for details.

* **`wav2wem` Audio Converter:** The installer retrieves the converter from the separate project repository. Review its source, build instructions, and license at [Bob-Harper/wav2wem](https://github.com), originally based on [pas2k/wav2wem](https://github.com).

## Special Acknowledgments
- **[EternalLeo](https://github.com/EternalLeo):** The excellent [sound2wem](https://github.com/EternalLeo/sound2wem) utility which acted as the springboard to launch this project and provided the original proof of concept. This project would not exist without his research.
- **[Kilvoctu](https://github.com/Kilvoctu):** Excellent suggestions, thank you for giving me much to ponder and helping elevate the codebase.
- **The Nexus Mods Suit Audio Community:** Gratitude to all original voice modders and commenters whose forum feedback helped isolate the exact filesystem directories and behaviours that make this possible.
- **Sean Murray & Hello Games:** Deep thanks for crafting the definitive cosmic sandbox universe we waited all these years to explore.
