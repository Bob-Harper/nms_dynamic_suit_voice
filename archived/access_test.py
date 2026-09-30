import time
from pathlib import Path
import os

WATCH_DIR = Path(r"C:\Program Files (x86)\Steam\steamapps\common\No Man's Sky\GAMEDATA\MODS\DYNAMIC_SUIT_VOICE\AUDIO\WINDOWS\MEDIA\ENGLISH(US)")
CHECK_INTERVAL = 0.5  # seconds

# Load initial access times
access_times = {
    f: f.stat().st_atime for f in WATCH_DIR.glob("*.wav")
}

print("Watching for file access...")

while True:
    for f in WATCH_DIR.glob("*.wav"):
        try:
            current_atime = f.stat().st_atime
            if current_atime != access_times.get(f, 0):
                print(f"Access detected: {f.name}")
                access_times[f] = current_atime
                # Insert call to regenerate pipeline here if desired
        except FileNotFoundError:
            access_times.pop(f, None)

    time.sleep(CHECK_INTERVAL)
