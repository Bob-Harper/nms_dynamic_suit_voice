import os
import subprocess
from pathlib import Path

SOURCE_DIR = Path(r"C:\PythonScripts\NMS_SUIT_VOICE\oldmods\213\ANALOGUE - BACON Update\audio\windows\media\english(us)")  # Change if needed
VGMSTREAM_CLI = r"C:\PythonScripts\NMS_SUIT_VOICE\vgmstream\vgmstream-cli.exe"

def wem_to_wav(wem_file):
    wav_file = wem_file.with_suffix(".wav")
    subprocess.run([VGMSTREAM_CLI, "-o", str(wav_file), str(wem_file)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if wav_file.exists():
        return wav_file
    return None

if __name__ == "__main__":
    for wem_file in SOURCE_DIR.rglob("*.wem"):
        result = wem_to_wav(wem_file)
        if result:
            print(f"Converted: {wem_file.name} -> {result.name}")
        else:
            print(f"Conversion failed for {wem_file.name}")

