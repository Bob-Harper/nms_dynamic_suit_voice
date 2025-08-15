# Dynamic No Man’s Sky Suit AI Voice Mod

Version: 1.0<br>
Author: [[Bob-Harper](https://github.com/Bob-Harper)]<br>
Repository: [[nms_dynamic_suit_voice](https://github.com/Bob-Harper/nms_dynamic_suit_voice)]

## Overview

This mod replaces static suit AI voice lines in No Man’s Sky with dynamically generated, non-repetitive lines, powered by a local AI model.<br>
Non-negotiable design philosophies guiding every decision made on this project:<br> - Local files ONLY.<br> - ENHANCE gameplay but NOT at the EXPENSE of gameplay

## Explanation

When the game makes a call to use a suit voice line, it will use the file it finds in the mod directory at the time it searches. The game does NOT preload mod voice files when it starts.  They do NOT stay in memory.  They load and play EACH TIME the game makes a call for that specific WEM file.  This is why this pipeline works.  If we generate a new voice file fast enough, and save it before the game has a chance to call it again, every line will be completely new - even when selling items at a terminal.  No more repetitive "Units Received Units Received Units Received Units Received ".

## Key Features

No repetition – each line is freshly generated, so you won’t hear the same thing twice.

Drop-in replacement for default suit AI audio files.

Local-only – no cloud processing or internet connection required. Completely Offline game compatible.



## Limitations / Disclaimer

This mod is incompatible with other mods that change the suit voice.

⚠️ WARNING
This has only been tested on my personal development machine:
<br>Windows 11
<br>64GB RAM
<br>NVIDIA GTX 1650 Ti (4GB VRAM)
<br>Performance and results may vary wildly on other hardware.
<br>This is not tested on any other system, OS, or GPU configuration.

This should be started BEFORE NMS is started up, or there will be fights over your VRAM and GPU usage and the game will stutter to the point where a well tuned Powerpoint presentation would be smoother.  The model I use and recommend takes up under 2GB of VRAm - on my machine that is a large hit to the amount available for the game, but honestly I dont notice a difference - unless I forget and load the game before I load the generator (Probably because of the system RAM).

## Requirements

Recommended (tested) setup:
<br>Windows 11
<br>64GB RAM
<br>NVIDIA GPU with 4GB VRAM minimum (1650 Ti or better recommended)
<br>Python 3.10 or higher
<br>Installed dependencies (see Installation)
<br>Ollama
<br>Sound2Wem
<br>Minimum specs suggestions have not been explored nor tested.

## Installation

Clone this repository
```
git clone https://github.com/Bob-Harper/nms_dynamic_suit_voice.git
cd nms_dynamic_suit_voice
```

Install Python dependencies
```
pip install -r requirements.txt
```

Prepare voice generation model
<br>Follow included instructions in docs/MODEL_SETUP.md to download and configure the LLM model.
<br>(TL;DR - Install Ollama, pull the qwen2.5:0.5b, make sure ollama is running)
<br>Download and install sound2wem converter with the default project supplied inside this project's sound2wem folder.
<br>Copy pregenerated .wem files from the "starter-wems" folder into your No Man’s Sky [ insert actual GAME/MODS path ] folder.

Run the generator.
```
python generate_suit_lines.py  (update to correct .pyw file/command here)
```

Start No Man's Sky and play until your suit notifies you of something important.

## Usage

The generator will watch for suit AI voice triggers and produce a new audio file on demand.

Output is sent directly to the output_wem folder, and overwrites the previous file. (The suit voice line that was just used in game).  

## Future Plans (Version 2 Goals)

Context-aware lines (react to in-game events with tailored responses).
<br>Expanded voice profiles and personalities.
<br>User Adjustable creativity and tone parameters.

## License

MIT, see the license link for details.

# Thank you
<br> - sound2wem
<br> - suit voice modders on Nexus Mods, without whom I would not know which directory to monitor or that the game looks for WEM files
<br> - Sean Murray and everyone at Hello Games for bringing to life the game I waited 25 years for.
