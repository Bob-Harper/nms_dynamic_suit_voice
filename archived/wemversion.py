import struct
import os

def scan_wem_version(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()

    # Sanity check it's a RIFF file
    if not data.startswith(b'RIFF'):
        print(f"{filepath}: Not a valid RIFF file")
        return

    pos = 12  # Skip RIFF header
    while pos < len(data):
        chunk_id = data[pos:pos+4]
        chunk_size = struct.unpack('<I', data[pos+4:pos+8])[0]
        chunk_data = data[pos+8:pos+8+chunk_size]

        # Look for the 'fmt ' chunk, which usually contains version info
        if chunk_id == b'fmt ':
            if len(chunk_data) >= 4:
                version_id = struct.unpack('<I', chunk_data[0:4])[0]
                print(f"{filepath}: Possible Wwise Version ID: {version_id}")
            else:
                print(f"{filepath}: fmt chunk too small")
            return

        pos += 8 + chunk_size

    print(f"{filepath}: No fmt chunk found")

# === CONFIG ===

# Point this to any folder where you have a few WEMs sitting
wem_folder = r"C:\PythonScripts\NMS_SUIT_VOICE\AUDIO\WINDOWS"

for filename in os.listdir(wem_folder):
    if filename.lower().endswith(".wem"):
        scan_wem_version(os.path.join(wem_folder, filename))
