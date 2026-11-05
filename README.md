# Dynamic No Man’s Sky Suit AI Voice Mod

Version: 1.2.1 (Unchained.SecFix)<br>
Author: [[Bob-Harper](https://github.com)]<br>
Repository: [[nms_dynamic_suit_voice](https://github.com)]

## Overview

This mod replaces static exosuit AI voice lines in No Man’s Sky with dynamically generated, non-repetitive lines, powered by a local AI model and localized audio DSP filters.

### Non-Negotiable Core Mandates:
- **Local files ONLY.** No cloud processing, zero internet connection required beyond installation, and absolutely no paid API subscription keys.
- **ENHANCE gameplay but NOT at the EXPENSE of gameplay.** Hardware footprints are stringently guarded.
- **Strict Single-Use Cache Vectors.** When pre-caching, generated audio files are completely overwritten after a single use, never reused.

## How the Tech Works

When No Man's Sky makes a sound call to play a suit voice line, it reads the physical file it finds inside your mod directory *at the exact moment it searches*. The game does NOT preload mod voice files into system memory when it launches. They load and play **EACH TIME** the game calls for that specific `.wem` file block, then are immediately unloaded until called again.

Because your local pipeline generates variations ahead of time into a protected background cache buffer, the system watcher instantly swaps a fresh file into your game folder the moment a line is loaded and played by the game, and proceeds to replenish the cache while you are still playing. Every notification is completely new — even when mass-selling stacks of items at a space station terminal. No more repetitive *"Units Received. Units Received. Units Received."*

## Key Features (As of v1.2.1)

- **Standalone Architecture:** The Audiokinetic Wwise SDK requirement has been completely eradicated. No software accounts, corporate registration, or heavy background installations of programs or third party software are required.  (LLM and TTS models still required)
- **Pure-Python DSP Matrix Engine:** FFmpeg requirement and sub-process loop has been removed. Volume gain, sentence tempo stretchings, and pitch adjustments are handled entirely in-memory via single-pass NumPy/SciPy matrix math.
- **Micro-Sized Asset Footprint:** Bundles an embedded, native `.wem` bitstream re-packetizer right inside your repository pull.
- **Centralized Control Dashboard:** A graphical config interface to customize iteration names, swap engines, adjust multi-threaded look-ahead queues, or fine-tune processing effects.
- **Stateful Quick Cache System:** Thread-isolated background queue managers monitor inventory states, look ahead to generate upcoming lines, and intelligently handle file locks without breaking game focus.
- **Protected VRAM Performance:** Run fully on optimized CPU thread inference layouts, leaving your GPU completely free to push maximum frame rates to the game.

### Persistent User Configuration Matrix
Customizations are securely saved directly to `config/user_customization.json`. This architecture ensures your personalized variables will **never be overwritten or wiped out** during future mod updates or repository git pulls.

- **First-Time Installation:** If this configuration file does not exist on your drive, the automated setup script will initialize it cleanly for you.
- **Upgrading the Mod:** If the file already exists with your custom settings, the engine boundaries will completely shield it from being touched.
- **Power-User Manipulation:** While changes can be made manually via any plain-text editor, the graphical **DSV Manager** interface reads natively from this profile map and saves your slider adjustments straight back to it when applying or saving changes.

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

### 1-Click Execution Setup
Launch the primary command wrapper script from your extracted mod directory:
```bash
DOUBLECLICK_To_Install_Dynamic_Suit_Voice.cmd
```
Choose **Automatic Mode** for a streamlined, single-click deployment that sets up your isolated Python `venv` environment, upgrades core libraries, builds your asset pointers, and creates space-safe desktop shortcuts completely in the background.

### Launching the DSV
Double-click your newly generated desktop shortcut: NMS Dynamic Suit Voice
Check your system tray - if the icon is Red, it is still warming up.  When the red disappears, the DSV is actively monitoring your game directory and ready to step up.  Launch No Man's Sky, and head out into the stars!

### Launching the DSV Manager
To customize your Exosuit experience, double-click your newly generated desktop shortcut: Exosuit Companion
This launches separately from the main DSV, and can be run at any time.  It opens your graphical configuration utility, allowing you to specify your **Iteration Designation**, swap active vocal models, or test-play custom presets and fine-tune your modifications inside the sandbox before starting your game session.
Click **Save & Close** when you are done (or **Apply Changes** and leave it open to tweak metrics while playing).

## Future Framework Roadmap
- **Multiple Profiles:** Allow users to to users to name and store their own created configurations and audio presets.
- **Easy Updates & Cache Management:** Manager enhancements such as the ability to check for and download updates, manage local storage and temporary files.
- **Support Tab:** Instead of cryptic error messages written in Nerdspeak, a human readable summary plus a Debug Token that can be entered into the support tab to display instant advice or steps to follow for common issues.  Direct support will remain an option as always.
- **Additional TTS Models:** Adding an Advanced button to the model management tab in DSV Manager to show the full list of available models regardless of requirements or capabilities.

## Licensing & Third-Party Open Source Attributions

Distributed fully open-source under the MIT License. See `LICENSE` for details.

* **`wav2wem` Assembly Tool:** This project bundles an embedded static binary of `wav2wem` to handle bit-exact audio re-packetization. Licensed under the GPLv2.
    * Original Repository: [pas2k/wav2wem](https://github.com/pas2k/wav2wem)
    * Project Fork Source: [Bob-Harper/wav2wem](https://github.com/Bob-Harper/wav2wem)

## Special Acknowledgments
- **[EternalLeo](https://github.com/EternalLeo):** The excellent [sound2wem](https://github.com/EternalLeo/sound2wem) utility which acted as the springboard to launch this project and provided the original proof of concept. This project would not exist without his research.
- **[Kilvoctu](https://github.com/Kilvoctu):** Excellent suggestions, thank you for giving me much to ponder and helping elevate the codebase.
- **The Nexus Mods Suit Audio Community:** Gratitude to all original voice modders and commenters whose forum feedback helped isolate the exact filesystem directories the game monitors.
- **Sean Murray & Hello Games:** Deep thanks for crafting the definitive cosmic sandbox universe we waited all these years to explore.
