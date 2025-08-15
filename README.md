#Dynamic No Man’s Sky Suit AI Voice Mod

Version: 1.0
Author: [Bob-Harper] (NMS In-Game name - Steam platform, Bob Harper)
Repository: [[nms_dynamic_suit_voice](https://github.com/Bob-Harper/nms_dynamic_suit_voice)]

##Overview

This mod replaces static suit AI voice lines in No Man’s Sky with dynamically generated, non-repetitive lines, powered by a local AI model.

#Explanation

When the game makes a call to use a suit voice line, it will use the file it finds in the mod directory at the time it searches. The game does NOT preload mod voice files when it starts.  They do NOT stay in memory.  They load and play EACH TIME the game makes a call for that specific WEM file.  This is why this pipeline works.  If we generate a new voice file fast enough, and save it before the game has a chance to call it again, every line will be completely new - even when selling items at a terminal.  No more repetitive "Units Received Units Received Units Received Units Received ".

##Key Features

No repetition – each line is freshly generated, so you won’t hear the same thing twice.

Drop-in replacement for default suit AI audio files.

Local-only – no cloud processing or internet connection required.

Works with any existing mod setup that allows voice line replacement.

##Limitations / Disclaimer

⚠️ WARNING
This has only been tested on my personal development machine:

Windows 11

64GB RAM

NVIDIA GTX 1650 Ti (4GB VRAM)
Performance and results may vary wildly on other hardware.
This is not tested on any other system, OS, or GPU configuration.

##Requirements

Minimum recommended setup:

Windows 11

64GB RAM

NVIDIA GPU with 4GB VRAM minimum (1650 Ti or better recommended)

Python 3.10 or higher

Installed dependencies (see Installation)

Ollama

Sound2Wem

##Installation

Clone this repository
```
git clone https://github.com/YOUR-USERNAME/YOUR-REPO.git
cd YOUR-REPO
```

Install Python dependencies
```
pip install -r requirements.txt
```

Prepare voice generation model
Follow included instructions in docs/MODEL_SETUP.md to download and configure the LLM/TTS model.

Run the generator
```
python generate_suit_lines.py
```

Copy pregenerated .wem files from the "starter-wems" folder into your No Man’s Sky [ insert actual GAME/MODS path ] folder or merge with an existing mod that replaces suit lines.

Usage

The generator will watch for suit AI voice triggers and produce a new audio file on demand.

Output is sent directly to the output_wem folder, and overwrites the previous file. (The suit voice line that was just used in game).  

Future Plans (Version 2 Goals)

Context-aware lines (react to in-game events with tailored responses).

Expanded voice profiles and personalities.

Adjustable creativity and tone parameters.

License

Include your chosen license here (MIT, GPL, custom, etc.).
