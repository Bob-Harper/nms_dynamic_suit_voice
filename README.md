# Dynamic No Man’s Sky Suit AI Voice Mod

Version: 1.0<br>
Author: [[Bob-Harper](https://github.com/Bob-Harper)]<br>
Repository: [[nms_dynamic_suit_voice](https://github.com/Bob-Harper/nms_dynamic_suit_voice)]

## Overview

This mod replaces static suit AI voice lines in No Man’s Sky with dynamically generated, non-repetitive lines, powered by a local AI model.<br>
Non-negotiable design philosophies guiding every decision made on this project:
- Local files ONLY.
- ENHANCE gameplay but NOT at the EXPENSE of gameplay

## Explanation

When the game makes a call to use a suit voice line, it will use the file it finds in the mod directory at the time it searches. The game does NOT preload mod voice files when it starts.  They do NOT stay in memory.  They load and play EACH TIME the game makes a call for that specific WEM file, then are unloaded until called from the file again.  This is why this pipeline works.  If we generate a new voice file fast enough, and save it before the game has a chance to call it again, every line will be completely new - even when selling items at a terminal.  No more repetitive "Units Received Units Received Units Received Units Received ".

## Key Features

- No repetition – each line is freshly generated, so you rarely/never hear the same thing twice. *depends on inference speed
- Drop-in replacement for default suit AI audio files.
- Local-only – no cloud processing or internet connection required. Completely Offline game compatible.
- no fees, no subscriptions, no paid API
- Current implementation uses CPU inference, leaving the GPU free for the game

## Examples:
<br>Original Game Wording: Nearby toxins detected
<br> Final Output: Corrosive environmental toxins are causing damage to your suit's protective filters.
<br> Final Output: Corrosive environmental toxins are threatening the effectiveness of your suit's protective filters.
<br> Final Output: Corrosive environmental toxins are harming Your suit’s protective filters.
<br> Final Output: Corrosive environmental toxins are impacting Your suit's protective filters, leading to damage and potential filter failure.
<br> Final Output: Corrosive environmental contaminants are debilitating your suit’s filtration system.

Original Game Wording: Extreme Night Temperature Detected
<br> Final Output: Extreme night cold weather noted. Alerting of potential severe consequences for life support and safety.
<br> Final Output: Extreme night temperature detected poses a severe risk to life support and your well-being.
<br> Final Output: Extreme night cold temperatures are reported. This is concerning as it could lead to reduced life support and potential danger for You.
<br> Final Output: Extreme cold temperatures during the night cycle are detected, posing a significant threat to life support and your safety.

## Demo Video

[![Dynamic Suit Voice Demo](https://img.youtube.com/vi/L1BsYxOSzSk/0.jpg)](https://youtu.be/L1BsYxOSzSk)


## Limitations / Disclaimer

- This is incompatible with mods that change the suit voice by placing sound files in the MODS folder.
- This project (and the notes regarding it's capabilities) assume minimizing VRAM and GPU necessity. It is not currently enabled to take advantage of a GPU so as not to impact actual gameplay. (See Advanced/FAQ for the long version)


⚠️ WARNING
This has only been tested on my personal development machine:
- Windows 11
- 64GB RAM
- NVIDIA GTX 1650 Ti (4GB VRAM)
- Performance and results may vary wildly on other hardware.
- This is not tested on any other system, OS, or GPU configuration.

I recommend starting this BEFORE NMS is started up (Essential if GPU enabled).  The model I use and recommend takes up 1.6 GB of memory.

## Installation
Automatic/Guided Mode: run setup.cmd
<br>This will offer 2 modes - Automatic (as close to 1 click install as I could make it) and Guided.  Both follow the same steps but the Guided mode will ask you for confirmation of paths and installation of items before proceeding.  Auto will assume defaults as provided in the example env file and proceed accordingly.

~~Masochist~~ Manual Mode:
[For detailed instructions refer to the Setup.md in the docs folder](docs/Setup.md)
<br>Short version:
- Clone this repository
- Install Python venv and requirements (Includes llama-cpp-python - no separate llama.cpp install required).
- Download the LLM model file
- Clone/Download sound2wem (which will separately ensure wwise plus ffmpeg)
- Copy pre-generated .wem files from the "DYNAMIC_SUIT_VOICE" folder into your No Man’s Sky MODS folder (NOT PCBANKS).
- Review and modify the supplied .env example
- run the TTS warmup to pre-download necessary models
- Run the generator.
- Start NMS
- Play!

## Usage
Once installed, no user interaction required other than starting it up before you play the game and stopping it when you are done.
The generator will watch for a suit voice trigger and produce a new audio file.

Output is sent directly to the mod folder, and overwrites the voice line that was just used in the game. The next time you
hear that same notification, the wording will be different.  It's that simple.

## Future Plans (Version 2 Goals)
- Context-aware lines (react to in-game events with tailored responses).
- Persistent memory, keeping track of events that have taken place over the current play session (perhaps saving the data and reload at the start of the next session)
- Expanded voice profiles and personalities with on-the-fly changes through the systray icon.
- User Adjustable creativity and tone parameters, either as .

## License

MIT, see the license link for details.

# Thank you
- [[EternalLeo](https://github.com/EternalLeo)] - [[sound2wem](https://github.com/EternalLeo/sound2wem)] is 50% of what allows this project to work at all. 
- All the suit voice modders on Nexus Mods, without whom I would not know which directory to monitor or that the game looks for WEM files.  I downloaded every suit voice mod and examined every one of them.  I do not recall which one I was looking at when my suspicions were confirmed.  It may have been a comment on nexusmods from one of the feedback messages.  It may have been between 4am and 6am when I finally tested and saw the correct directory was working.  So thank you to every one of you, and the commenters as well.
- Sean Murray and everyone at Hello Games for bringing to life the game I waited 25 years for.
