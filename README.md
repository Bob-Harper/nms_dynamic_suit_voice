# Dynamic No Man’s Sky Suit AI Voice Mod

Version: 1.0<br>
Author: [[Bob-Harper](https://github.com/Bob-Harper)]<br>
Repository: [[nms_dynamic_suit_voice](https://github.com/Bob-Harper/nms_dynamic_suit_voice)]

## Overview

This mod replaces static suit AI voice lines in No Man’s Sky with dynamically generated, non-repetitive lines, powered by a local AI model.<br>
Non-negotiable design philosophies guiding every decision made on this project:<br> - Local files ONLY.<br> - ENHANCE gameplay but NOT at the EXPENSE of gameplay

## Explanation

When the game makes a call to use a suit voice line, it will use the file it finds in the mod directory at the time it searches. The game does NOT preload mod voice files when it starts.  They do NOT stay in memory.  They load and play EACH TIME the game makes a call for that specific WEM file, then are unloaded until called from the file again.  This is why this pipeline works.  If we generate a new voice file fast enough, and save it before the game has a chance to call it again, every line will be completely new - even when selling items at a terminal.  No more repetitive "Units Received Units Received Units Received Units Received ".

## Key Features

No repetition – each line is freshly generated, so you rarely hear the same thing twice.

Drop-in replacement for default suit AI audio files.

Local-only – no cloud processing or internet connection required. Completely Offline game compatible.

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


## Limitations / Disclaimer

<br> - This mod is incompatible with other mods that change the suit voice.
<br> - This mod (and the notes regarding it's capabilities) assume minimizing VRAM occupation. If you have a high end Nvidia card, I would love to hear how it fares.
<br> - Larger LLM's give better dynamic results, at the expense of eating your VRAM and gpu cycles.  
<br> - Larger LLM's tend to take longer to process, meaning it will take longer to create a new voice line and save it, decreasing the chances of being able to create a new file fast enough if doing repetitive actions that call the same suit line (crafting or selling, typically)
<br> - Smaller LLM's are better for speed - The prompting used currently is very heavily optimized for qwen3:0.6b, if you choose to swap that out, you may need to take some time testing the output results.  A transcript test script is included to help with this.


⚠️ WARNING
This has only been tested on my personal development machine:
<br>Windows 11
<br>64GB RAM
<br>NVIDIA GTX 1650 Ti (4GB VRAM)
<br>Performance and results may vary wildly on other hardware.
<br>This is not tested on any other system, OS, or GPU configuration.

This should be started BEFORE NMS is started up, or there may be fights over your VRAM and GPU usage and the game will stutter to the point where a well tuned Powerpoint presentation would be smoother.  The model I use and recommend takes up 1GB of VRAm - on my machine that is a large hit to the amount available for the game, but honestly I dont notice a difference - unless I forget and load the game before I load the generator.
<img width="3274" height="286" alt="image" src="https://github.com/user-attachments/assets/d4c88904-f197-45f2-a0c3-ba0bc5c0b491" />

## Installation

For detailed instructions refer to the Setup.md in the docs folder.
<br>Short version:
<br>Clone this repository
<br>Install Python dependencies
<br>Install Ollama if you don't have it, download a model.
<br>Download and install sound2wem
<br>Copy pregenerated .wem files from the "DYNAMIC_SUIT_VOICE" folder into your No Man’s Sky MODS folder (NOT PCBANKS).
<br>Run the generator.
<br>Start NMS
<br>Play!

## Usage

The generator will watch for a suit voice trigger and produce a new audio file.

Output is sent directly to the mod folder, and overwrites the voice line that was just used in the game. The next time you
hear that same notification, the wording will be different.

## Future Plans (Version 2 Goals)
<br>Context-aware lines (react to in-game events with tailored responses).
<br>Expanded voice profiles and personalities.
<br>User Adjustable creativity and tone parameters.
<br>setup gui to help with configuring the .env paramaters and filepaths
<br>voice embeddings to clone your voice (or your kid's voices.  Use voice cloning technology responsibly.  Don't be evil.)

## License

MIT, see the license link for details.

# Thank you
<br> - [[EternalLeo](https://github.com/EternalLeo)] - [[sound2wem](https://github.com/EternalLeo/sound2wem)] is 50% of what allows this project to work at all. 
<br> - All the suit voice modders on Nexus Mods, without whom I would not know which directory to monitor or that the game looks for WEM files.  I downloaded every suit voice mod and examined every one of them.  I do not recall which one I was looking at when my suspicions were confirmed.  It may have been a comment on nexusmods from one of the feedback messages.  It may have been between 4am and 6am when I finally tested and saw the correct directory was working.  So thank you to every one of you, and the commenters as well.
<br> - Sean Murray and everyone at Hello Games for bringing to life the game I waited 25 years for.
