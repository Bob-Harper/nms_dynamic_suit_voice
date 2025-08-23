# Dynamic No Man’s Sky Suit AI Voice Mod Installation

Version: 1.0<br>
Author: [[Bob-Harper](https://github.com/Bob-Harper)]<br>
Repository: [[nms_dynamic_suit_voice](https://github.com/Bob-Harper/nms_dynamic_suit_voice)]


⚠️ WARNING
This has only been tested on my personal development machine. Yes this is mentioned on the first page.  I state it again
to ensure those with FIFO memory retention tendencies (I am one of them) recall this fact if they proceed.  I dont see why it wouldn't work on
most other configurations, but the two biggest factors are:
<br>1) for this to run at speed, it assumes a Nvidia GPU of at least 4GB and
<br>2) Windows OS.
<br>If you are on a different OS or have different (or no) dedicated graphics hardware and still want to try installing
and running, I suggest reviewing the Advanced.md in the docs folder.

## Requirements

Tested setup:
<br>Windows 11 (likely works on any OS that runs NMS and Python 3.10, with the exception of the systray icon)
<br>64GB RAM (Less should still be fine but may affect speed and may also impact gameplay if not carefully balanced)
<br>NVIDIA GPU with 4GB VRAM minimum (1650 Ti or better recommended) (Local LLM Inference can cause a huge hit. I've minimized
as much as I can while still getting coherent output from the LLM)
<br>Python 3.10 or higher
<br>Installed dependencies
<br>Ollama - https://ollama.com/download
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
