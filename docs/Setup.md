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
<br>Sound2Wem https://github.com/EternalLeo/sound2wem (will prompt and walk you through installing required dependencies if needed, otherwise it just..  runs.)


## Installation

### Clone this repository
```
git clone https://github.com/Bob-Harper/nms_dynamic_suit_voice.git
cd nms_dynamic_suit_voice
```

(Optional but highly recommended) Create a virtual environment.
This keeps the dependencies isolated from the rest of your system.
Assumption: you’re on Windows 11, you installed Python 3.10+ with defaults unchanged.
```
python --version       # should print 3.10.x or higher
python -m venv venv    # create a virtual environment in the "venv" folder
.\venv\Scripts\activate
```
You’ll know it worked if your prompt now starts with (venv).

### Install Python dependencies

Installing dependencies may take some time for a new venv — great time for a sandwich break.  
If it looks like it is frozen after listing 80+ dependencies that are going to be installed all at once, don’t believe it. Just let it run.

(Optional but recommended) Update pip before installing requirements.  
This can help avoid compatibility issues.

```
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Prepare voice generation pipeline
<br>Download and configure the LLM model. If you already have Ollama, adjust your process accordingly.
<br>- Short version: Install Ollama, "ollama pull qwen3:0.6b", set your model timeout to 30 mins (default is 5) and make sure ollama is running.
<br>Git clone or Download and install sound2wem.  If you choose to git clone, delete the sound2wem directory first.  If you simply download the cmd file, you can immediately place it in the existing sound2wem dir.  My own process was to git clone sound2wem into my dynamic_suit_voice directory alongside data, docs, assets, etc.  If you prefer a different location, you will need to adjust the paths in the .env folder accordingly.
<br>Copy pregenerated .wem files from the "DYNAMIC_SUIT_VOICE" folder into your No Man’s Sky MODS folder (NOT PCBANKS). These can act as replacement suit lines as-is on their own but then you would miss out on the fun of different lines every time.  Without the pre-generated WEMs there's nothing for the watchdog to monitor.  They're small. The directory structure is kept intact, if you copy the entire DYNAMIC_SUIT_VOICE folder and paste it as-is to the MODS folder it should be ready to go.  To test, start up the game and sell something.  if you get a different voice telling you something other than Units Received, they are in the correct place.
<br>TTS inference will automatically download the needed voice models the first time it is run. Yes, it could take a bit of time.

### Configure your environment file

In the project folder you’ll see `suit_voice.env.example`.  

1. Rename it to `suit_voice.env` (remove the `.example` part).  
2. Open it in a text editor and update the paths and values to match your setup.  
   - Example: the location where you installed `sound2wem`  
   - Example: your No Man’s Sky MODS folder  

This file tells the pipeline where to find everything. If you skip this step, it will fail to run.

### Run the generator. 
Curse because something didn't go right.  Read back through, recheck every step, doublecheck your .env file paths and options..
```
python nms_dynamic_suite_voice_pipeline.pyw
```
I recommend starting your first session in a terminal so you can see what it is doing, and when. If you have a second monitor, even better, you can watch the pipeline do it's thing as you play.
I saved as a .pyw because I wanted to make a shortcut and just run it directly.  It does not take any command line arguments
so starting it through a simple shortcut (right click, create shortcut) on the desktop is my preferred method.
It will take a few moments to initialize the reources it needs and ensure ollama is connected and the model pre-loaded.
Once the tray icon is visible, it is actively monitoring. If you started through a shortcut, that will be the only indicator.  If you started in a terminal, you will see "Watching for file access..."

## DO NOT START THE GAME UNTIL YOU SEE THE ICON
<br>Starting NMS before the pipeline will result in an avoidable unpleasant gaming experience.
But why?  Think of it this way: NMS will see the GPU VRAM during startup and say "That's mine!  Awesome" and Ollama will promptly take
the space over with what it requires - and NMS will stutter horribly as half it's expected resources are suddenly occupied.
However - Start the monitor first and Ollama will load it's model and there will be no arguing as NMS will now see the remaining VRAM
and only claim the amount available.  Everyone will be happy at that point.

### Start No Man's Sky 
Play until your suit notifies you of something important. Keep playing until you get another notification for the same
thing.  Hey, it's a different phrase this time!

Win!

For the terminal jockeys out there - when a voice file is accessed,you should see something like the following:
```
Watching for file access...
Access detected: 236472322.wem (ID: 236472322)
Calling run_tts...
Generated WAV: tmp_wem_dir\236472322.wav
WAV created at tmp_wem_dir\236472322.wav
Calling convert_to_wem...
Conversion attempt complete for 236472322.wav
Conversion to WEM complete
WEM moved successfully: C:\Program Files (x86)\Steam\steamapps\common\No Man's Sky\GAMEDATA\MODS\DYNAMIC_SUIT_VOICE\AUDIO\WINDOWS\MEDIA\ENGLISH(US)\236472322.wem
```

### Shut down the script

You can shut the script back down at any time, wether you are playing or not.  This will also free up the VRAM for the NMS though the game may not see it until restarted.
Two ways to shut down 
<br> - rudely, by closing the terminal window or using Ctrl-C
<br> - gracefully, by right clicking the tray icon and choosing "Quit".
