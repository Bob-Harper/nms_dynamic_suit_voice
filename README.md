Dynamic No Man’s Sky Suit AI Voice Mod

Version: 1.0
Author: [Your Name or Alias]
Repository: [GitHub Link Here]

Overview

This mod replaces static suit AI voice lines in No Man’s Sky with dynamically generated, non-repetitive lines, powered by a local AI model.

Key Features

No repetition – each line is freshly generated, so you won’t hear the same thing twice.

Drop-in replacement for default suit AI audio files.

Local-only – no cloud processing or internet connection required.

Works with any existing mod setup that allows voice line replacement.

Limitations / Disclaimer

⚠️ WARNING
This has only been tested on my personal development machine:

Windows 11

64GB RAM

NVIDIA GTX 1650 Ti (4GB VRAM)
Performance and results may vary wildly on other hardware.
This is not tested on any other system, OS, or GPU configuration.

Requirements

Minimum recommended setup:

Windows 11

64GB RAM

NVIDIA GPU with 4GB VRAM minimum (1650 Ti or better recommended)

Python 3.10 or higher

Installed dependencies (see Installation)

Installation

Clone this repository
CODE
git clone https://github.com/YOUR-USERNAME/YOUR-REPO.git
cd YOUR-REPO
/CODE

Install Python dependencies
CODE
pip install -r requirements.txt
/CODE

Prepare voice generation model
Follow included instructions in docs/MODEL_SETUP.md to download and configure the LLM/TTS model.

Run the generator
CODE
python generate_suit_lines.py
/CODE

Copy generated .wem files into your No Man’s Sky PCBANKS/MODS folder or merge with an existing mod that replaces suit lines.

Usage

The generator will watch for suit AI voice triggers and produce a new audio file on demand.

All output is stored in the output_wem folder until you manually move it into the game’s mod directory.

Future Plans (Version 2 Goals)

Context-aware lines (react to in-game events with tailored responses).

Expanded voice profiles and personalities.

Adjustable creativity and tone parameters.

License

Include your chosen license here (MIT, GPL, custom, etc.).
