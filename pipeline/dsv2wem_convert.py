# pipeline\dsv2wem_convert.py
from pathlib import Path
import struct
import subprocess

WWISE_STEREO_CHANNEL_MASK = 0x00003102


def apply_wwise_channel_mask(wem_path: Path) -> None:
    """Sets the 4-byte Wwise channel configuration mask at fmt+20 for 2-channel exosuit routing."""
    raw = bytearray(wem_path.read_bytes())
    fmt_offset = raw.find(b"fmt ")
    if fmt_offset == -1:
        return

    chunk_size = struct.unpack_from("<I", raw, fmt_offset + 4)[0]
    if chunk_size != 0x42:
        return

    struct.pack_into("<I", raw, fmt_offset + 8 + 20, WWISE_STEREO_CHANNEL_MASK)
    wem_path.write_bytes(raw)


def convert_to_wem(config, input_wav: Path, output_path: Path) -> Path:
    """
    encodes raw voice WAV outputs into game-compliant
    Wwise Vorbis streams via the local project assets.
    """
    wav2wem_binary = getattr(config, "wav2wem_binary_path", None)

    if not wav2wem_binary or not wav2wem_binary.exists():
        raise RuntimeError(
            f"DEBUG TOKEN = DSV2WEMN_FND >> Standalone conversion asset missing at target location: {wav2wem_binary}. "
        )

    cmd = [
        str(wav2wem_binary),
        str(input_wav),
        "-o", str(output_path),
        "-q", "4"
    ]

    try:
        subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            creationflags=getattr(config, "create_no_window", 0)
        )
        apply_wwise_channel_mask(output_path)
        return output_path

    except subprocess.CalledProcessError as err:
        raise RuntimeError(f"DEBUG TOKEN = WAV2WEM_FAIL >> Standalone audio encoder conversion failed: {err.stderr}")
