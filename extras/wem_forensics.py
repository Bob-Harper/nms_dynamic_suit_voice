#!/usr/bin/env python3
"""
WEM FORENSICS
When "it's a WEM" is not a sufficient answer.
"""

from pathlib import Path
import subprocess
import json
import hashlib
import struct
import math
import tempfile

FFPROBE = Path(r"C:\ffmpeg\bin\ffprobe.exe")
VGMSTREAM = Path(r"C:\ffmpeg\vgmstream\vgmstream-cli.exe")
for tool in (FFPROBE, VGMSTREAM):
    if not tool.exists():
        raise RuntimeError(f"Missing required tool: {tool}")

authenticated_wem  = r"C:\NMS_SUIT_VOICE\extras\330331555.wem"

print("Using:")
print(" FFPROBE  :", FFPROBE)
print(" VGMSTREAM:", VGMSTREAM)
# -------------------------------------------------------
# Helpers
# -------------------------------------------------------

def section(title):
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)


def run(cmd):
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.stdout, result.stderr
    except Exception as e:
        return "", str(e)


def md5_file(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


# -------------------------------------------------------
# Raw File
# -------------------------------------------------------

def analyze_raw(path):
    section("RAW FILE")

    data = path.read_bytes()

    print("File:", path)
    print("Size:", len(data))
    print("MD5 :", md5_file(path))

    unique = len(set(data))
    print("Unique Byte Values:", unique)

    freq = [0] * 256

    for b in data:
        freq[b] += 1

    entropy = 0

    for c in freq:
        if c:
            p = c / len(data)
            entropy -= p * math.log2(p)

    print(f"Entropy: {entropy:.4f}")


# -------------------------------------------------------
# RIFF CHUNKS
# -------------------------------------------------------

def analyze_riff(path):
    section("RIFF CHUNKS")

    data = path.read_bytes()

    if data[:4] not in (b"RIFF", b"RIFX"):
        print("Not RIFF based")
        return

    riff_size = struct.unpack_from("<I", data, 4)[0]

    print("Container :", data[:4].decode(errors="ignore"))
    print("RIFF Size :", riff_size)

    pos = 12

    while pos + 8 <= len(data):

        chunk_id = data[pos:pos+4]
        chunk_size = struct.unpack_from("<I", data, pos + 4)[0]

        cid = chunk_id.decode(errors="replace")

        print(
            f"{cid:>8} "
            f"offset={pos:<10} "
            f"size={chunk_size}"
        )

        pos += 8 + chunk_size

        if chunk_size % 2:
            pos += 1


# -------------------------------------------------------
# FMT INSPECTION
# -------------------------------------------------------

def analyze_fmt(path):
    section("FMT CHUNK")

    data = path.read_bytes()

    fmt = data.find(b"fmt ")

    if fmt < 0:
        print("No fmt chunk found")
        return

    chunk_size = struct.unpack_from("<I", data, fmt + 4)[0]

    print("Offset     :", fmt)
    print("Chunk Size :", chunk_size)

    blob = data[fmt+8:fmt+8+chunk_size]

    print()

    for i in range(0, len(blob), 16):

        row = blob[i:i+16]

        hexs = " ".join(f"{x:02X}" for x in row)

        print(f"{i:04X}: {hexs}")

    try:
        codec      = struct.unpack_from("<H", blob, 0)[0]
        channels   = struct.unpack_from("<H", blob, 2)[0]
        rate       = struct.unpack_from("<I", blob, 4)[0]
        avg_bytes  = struct.unpack_from("<I", blob, 8)[0]
        blockalign = struct.unpack_from("<H", blob, 12)[0]
        bits       = struct.unpack_from("<H", blob, 14)[0]

        print()
        print("Codec ID     :", codec)
        print("Channels     :", channels)
        print("Sample Rate  :", rate)
        print("Avg Bytes/s  :", avg_bytes)
        print("Block Align  :", blockalign)
        print("Bits/Sample  :", bits)

    except Exception as e:
        print(e)


# -------------------------------------------------------
# FFMPEG
# -------------------------------------------------------

def analyze_ffprobe(path):
    section("FFPROBE")

    out, err = run([
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path)
    ])

    try:
        parsed = json.loads(out)
        print(json.dumps(parsed, indent=2))
    except Exception:
        print(out)
        print(err)


# -------------------------------------------------------
# VGMSTREAM
# -------------------------------------------------------

def analyze_vgmstream(path):
    section("VGMSTREAM")

    out, err = run([
        VGMSTREAM,
        "-m",
        str(path)
    ])

    print(out)

    if err:
        print("\nSTDERR:")
        print(err)


# -------------------------------------------------------
# CONVERT TO WAV
# -------------------------------------------------------

def convert_to_wav(path):

    d = tempfile.gettempdir()

    output = Path(d) / "wem_forensics_temp.wav"

    subprocess.run(
        [
            VGMSTREAM,
            "-o",
            str(output),
            str(path)
        ],
        capture_output=True
    )

    if output.exists():
        return output

    return None


# -------------------------------------------------------
# AUDIO ANALYSIS
# -------------------------------------------------------

def analyze_audio(path):
    section("AUDIO ANALYSIS")

    try:
        import soundfile as sf
        import numpy as np
    except ImportError:
        print("pip install soundfile numpy")
        return

    data, sr = sf.read(path)

    if data.ndim > 1:
        mono = data.mean(axis=1)
    else:
        mono = data

    peak = np.max(np.abs(mono))
    rms = np.sqrt(np.mean(mono**2))

    peak_db = 20 * np.log10(max(peak, 1e-12))
    rms_db = 20 * np.log10(max(rms, 1e-12))

    crest = peak_db - rms_db

    print("Sample Rate :", sr)
    print("Samples     :", len(mono))
    print("Duration    :", len(mono)/sr)
    print("Peak dBFS   :", peak_db)
    print("RMS dBFS    :", rms_db)
    print("Crest Factor:", crest)


# -------------------------------------------------------
# MAIN
# -------------------------------------------------------

def inspect(path):

    path = Path(path)

    analyze_raw(path)
    analyze_riff(path)
    analyze_fmt(path)
    analyze_ffprobe(path)
    analyze_vgmstream(path)

    wav = convert_to_wav(path)

    if wav:
        analyze_audio(wav)


if __name__ == "__main__":

    new_wem = r"C:\NMS_SUIT_VOICE\cache\tmp_quick_dir\330331555\330331555_20261122_055533.wem"

    inspect(new_wem)