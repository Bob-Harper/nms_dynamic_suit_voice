from pathlib import Path
import subprocess

def convert_to_wem(config, input_wav: Path, output_path: Path) -> Path:
    """
    Natively encodes raw voice WAV outputs into true game-compliant
    0xFFFF Wwise Vorbis streams via the local project assets.
    Extracted completely out of Wwise Console SDK dependency limits.
    """
    # Grab the absolutely resolved tool path tracked by the configuration module
    wav2wem_binary = getattr(config, "wav2wem_binary_path", None)

    if not wav2wem_binary or not wav2wem_binary.exists():
        raise RuntimeError(
            f"DEBUG TOKEN = DSV2WEM_NF >> Standalone conversion asset missing at target location: {wav2wem_binary}. "
        )

    # Build the direct, clean CLI argument array
    # -q 4 maps variable bitrate parameters cleanly (~57kbps)
    cmd = [
        str(wav2wem_binary),
        str(input_wav),
        "-o", str(output_path),
        "-q", "4"
    ]

    try:
        # Trigger the clean standalone execution loop in memory
        subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            creationflags=getattr(config, "create_no_window", 0)
        )
        return output_path

    except subprocess.CalledProcessError as err:
        raise RuntimeError(f"DEBUG TOKEN = WAV2WEM_FAIL >> Standalone audio encoder conversion failed: {err.stderr}")
