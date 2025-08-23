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
<br> - Smaller LLM's are better for speed - The prompting used currently is very heavily optimized for qwen2.5:0.5b, if you choose to swap that out, you may need to take some time testing the output results.  A transcript test script is included to help with this.


⚠️ WARNING
This has only been tested on my personal development machine: yes this is mentioned on the first page.  I state it again
to ensure those with a FIFO cortex processing unit recall that if they proceed.  I dont see why it wouldn't work on
most other configurations but the two big ones are for this to run at speed, it assumes a Nvidia GPU of at least 4GB and
Windows OS.  If you are on a different OS and still want to try installing and running, I suggest reviewing the Advanced.md
in the docs folder.

## Requirements

Tested setup:
<br>Windows 11 (OS required, likely works on any OS that runs NMS and Python 3.10)
<br>64GB RAM (Less should still be fine but may affect speed and may also impact gameplay if not carefully balanced)
<br>NVIDIA GPU with 4GB VRAM minimum (1650 Ti or better recommended) (Local LLM Inference can cause a huge hit. I've minimized
as much as I can will still getting coherent output from the LLM)
<br>Python 3.10 or higher
<br>Installed dependencies (see Installation)
<br>Ollama https://ollama.com/download
<br>Ollama model - recommended "ollama pull qwen3:0.6b" https://ollama.com/library/qwen3:0.6b
<br>Sound2Wem https://github.com/EternalLeo/sound2wem (will prompt and walk you through installing itself and required dependencies)


## Installation

Clone this repository
```
git clone https://github.com/Bob-Harper/nms_dynamic_suit_voice.git
cd nms_dynamic_suit_voice
```

Install Python dependencies (may take some time).  Using a virtual environment is recommended.
```
pip install -r requirements.txt
```

Prepare voice generation pipeline
<br>Download and configure the LLM model.
<br>- Short version: Install Ollama, "ollama pull qwen2.5:0.5b", set your model timeout to 30 mins (default is 5) and make sure ollama is running.
<br>Download and install sound2wem.  My own process was to git clone sound2wem into my dynamic_suit_voice directory alongside data, docs, assets, etc.  If you prefer a different location, you will need to adjust the paths in the .env folder accordingly.
<br>Copy pregenerated .wem files from the "DYNAMIC_SUIT_VOICE" folder into your No Man’s Sky MODS folder (NOT PCBANKS). These can act as replacement suit lines as-is on their own but then you would miss out on the fin of different lines every time.  Without the pre-generated WEMs there's nothing for the watchdog to monitor.  They're small. The directory structure is kept intact, if you copy the entire DYNAMIC_SUIT_VOICE folder and paste it as-is to the MODS folder it should be ready to go.  To test, start up the game and sell something.  if you get a different voice telling you something other than Units Received, they are in the correct place.
<br>TTS inference will automatically download the needed voice models the first time it is run.

Run the generator. Curse because something didn't go right.  Read back through, recheck every step, try again until it runs.
```
python generate_suit_lines.pyw
```
I saved as a .pyw because I wanted to make a shortcut and just run it directly.  It does not take any command line arguments
so starting it through a simple shortcut (right click, create shortcut) on the desktop is my preferred method.
It will take a few moments to initialize the models it needs and ensure ollama is connected and the model loaded.
Once the tray icon is visible, it is actively monitoring.
<br>##DO NOT START THE GAME UNTIL YOU SEE THE ICON
<br>Starting NMS before the pipeline will result in an avoidable unpleasant gaming experience.
But why?  Think of it this way: NMS will see the GPU VRAM during startup and say "That's mine!  Awesome" and Ollama will promptly take
the space over with what it requires - and NMS will stutter horribly as half it's expected resources are suddenly occupied.
However - Start the monitor first and Ollama will load it's model and there will be no arguing as NMS will now see the remaining VRAM
and only claim the amount available.  Everyone will be happy at that point.

Start No Man's Sky and play until your suit notifies you of something important. Keep playing until you get another notification for the same
thing.  Hey, it's a different phrase this time!

Profit.
