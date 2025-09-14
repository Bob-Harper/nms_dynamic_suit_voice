# Dynamic No Man’s Sky Suit AI Voice Mod Installation

Version: 1.0<br>
Author: [[Bob-Harper](https://github.com/Bob-Harper)]<br>
Repository: [[nms_dynamic_suit_voice](https://github.com/Bob-Harper/nms_dynamic_suit_voice)]


⚠️ WARNING
This has only been tested on my personal development machine. Yes this is mentioned on the first page.  I state it again
to ensure those with FIFO memory retention tendencies (I am one of them) recall this fact if they proceed.  I dont see why it wouldn't work on
most other configurations, but the two biggest factors are:
- for this to run at speed, it assumes a decent CPU and RAM quantity.
- Windows OS.
<br>If you are on a different OS and still want to try installing and running, I suggest reviewing the Advanced.md in the docs folder.

## Requirements

Tested setup:
-Windows 11 (likely works on any OS that runs NMS and Python 3.10, with the exception of the systray icon)
-64GB RAM (Less should still be fine but may affect speed and may also impact gameplay if not carefully balanced)
-NVIDIA GPU with 4GB VRAM minimum (1650 Ti or better recommended).  I leave this mentioned as I can and have run this with the GPU even if I am now running CPU inference only.
-Python 3.10
-Installed dependencies
-Sound2Wem https://github.com/EternalLeo/sound2wem (will prompt and walk you through installing required dependencies if needed, otherwise it just..  runs.)


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
This also installs llama-cpp-python automatically — you do not need to separately install llama.cpp.
(Optional but recommended) Update pip before installing requirements.  
This can help avoid compatibility issues.

```
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Prepare voice generation pipeline
- Download and configure the LLM model. The one I currently have is from here: https://huggingface.co/lmstudio-community/Qwen3-0.6B-GGUF though any model that uses Q4_K_M should be fine.  Just be sure the filename specifies Qwen3-0.6B-Q4_K_M.gguf.  Using a different quantization or different model entirely may require extensive testing to get the results you want.  Place the model file in assets/qwen3_06b_q4 - the tokenizer is already present.
- Git clone or Download and install sound2wem.  If you choose to git clone, do it in the root dir of this project for easiest results, otherwise you will need to update the paths in the suit_env file.  If you simply download the cmd file, create a sound2wem folder and you can place it in the new folder. At minimum you need the zsound2wem.cmd file. But you MUST run it once — it will walk you through fetching Wwise and ffmpeg if they’re not installed.
- Copy pregenerated .wem files from the "DYNAMIC_SUIT_VOICE" folder into your No Man’s Sky MODS folder (NOT PCBANKS). If your NMS dir does not have the MODS folder you can create it.  Once in place, the .wem files give the watchdog something to monitor, as their existence will override the in-game default voice files.  They're small. The directory structure is kept intact, if you copy the entire DYNAMIC_SUIT_VOICE folder and paste it as-is to the MODS folder it should be ready to go. If you feel the need to test, these CAN act as static suit voice files, just run the game once the .wem files are in place and you should be able to hear a completely different suit voice.
- TTS inference will automatically download the needed voice models the first time it is run. Yes, it could take a bit of time.  Yes it might seem like it hangs at first.  Check the terminal window and if you see no errors, it is downloading.  It is okay to keep playing  Eventally it will finish and start generating replacement lines on the fly.

### Configure your environment file

In the project folder you’ll see `suit_voice.env.example`.  

1. Rename it to `suit_voice.env` (remove the `.example` part).  
2. Open it in a text editor and update the paths and values to match your setup if needed.  I have saved with values that SHOULD work assuming you followed the above instrutions and installed Steam to it's default.  .  
   - Example: the location where you installed `sound2wem`  
   - Example: your No Man’s Sky MODS folder  

This file tells the pipeline where to find everything. If you skip this step and the pipeline errors when started - this is the most likely culprit.

### Run the generator. 
Curse because something didn't go right.  Read back through, recheck every step, doublecheck your .env file paths and options..
```
cd c:\NMS_SUIT_VOICE
.\venv\Scripts\activate
python nms_dynamic_suite_voice_pipeline.pyw
```
I recommend starting your first session in a terminal window with the above command so you can see what it is doing, and when. If you have a second monitor, even better, you can watch the pipeline do it's thing as you play.
I saved as a .pyw because I wanted to make a shortcut and eventually just run it directly without messing with .bat files and such.  It does not take any command line arguments so starting it through a simple shortcut (right click, create shortcut) on the desktop is quick and easy.
It will take a few moments to initialize the reources it needs and ensure the model is pre-loaded.
Once the tray icon is visible, it is actively monitoring. If you started through a shortcut, that will be the only indicator.  If you started in a terminal, you will see "Watching for file access..."

## IF CONFIGURED TO USE GPU, DO NOT START THE GAME UNTIL YOU SEE THE ICON
Using it on CPU inference should have no impact to startup, but i recommend waiting until it is done because general principles.
If you've modified to use your GPU, improper startup timing may lead to severe game stuttering and eyestrain caused by FPS rates of 1 or less.  Refer to Advanced FAQS for why it's essential to wait.

### Start No Man's Sky 
Play until your suit notifies you of something important. Keep playing until you get another notification for the same
thing.  Hey, it's a different phrase this time!

Win!

### To shut down the script when done

You can shut the script back down at any time, wether you are playing or not.  This will also free up the VRAM for the NMS though the game may not see it until restarted.

Four ways to shut down:
- Lawful Good: Right click the tray icon and choose "Quit".
- Lawful Neutral: (If you started using a terminal window) Use Ctrl-C
- Chaotic Neutral: (If you started using a terminal window) Close the terminal window
- Chaotic Evil: kill the process in task manager

## Uninstall

But why?

If you must, remove the install directory nms_dynamic_suit_voice.  Also remove the directory from the MODS directory.  You could remove/uninstall wwise from wherever you installed it.  sound2wem, if installed per instructions, will be inside the project folder and disappear when you delete the directory structure.
That's it.  
- Note: If you choose to leave the MODS directory alone, the game will continue to use any voice lines left behind.  This could complicate your setup if you have another suit voice mod, or could be an awesome result if you really like those specific generated phrases.  If for some reason you choose to remove the voice files but leave the pipeline, there will be nothing for the pipeline to watch for changes.

