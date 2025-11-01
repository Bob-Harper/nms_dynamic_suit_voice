# wem_utils.py (fixed)
import subprocess
from pathlib import Path
import time
from debug.logging_utils import debug_print


def convert_to_wem(config, temp_wav_path, output_path: Path):
    debug_print("wem_utils.py:  convert_to_wem")  # works, just seeing it get called during the trail
    """
    Convert WAV to WEM and save it directly to output_path.
    Retries if the file is temporarily in use.
    """
    temp_wav_path = Path(temp_wav_path).resolve()
    output_path = Path(output_path).resolve()  # Final WEM location
    script_path = config.cmd_script_path.resolve()
    temp_dir = config.temp_wem_dir.resolve()   # temporary folder for conversion

    # Run Wwise conversion into temp_dir
    cmd = [
        "cmd.exe", "/c",
        str(script_path),
        f'--out:{str(temp_dir)}',
        str(temp_wav_path)
    ]

    try:
        subprocess.run(cmd, check=True, creationflags=config.create_no_window)
    except subprocess.CalledProcessError as e:
        print(f"Subprocess failed during WEM conversion: {e}")
        raise

    # The Wwise script will output temp_wav_name.wem in temp_dir
    wem_file = temp_dir / temp_wav_path.with_suffix(".wem").name

    # Move/rename to final output_path with retries
    max_attempts = 10
    for attempt in range(1, max_attempts + 1):
        try:
            wem_file.replace(output_path)
            break
        except PermissionError:
            time.sleep(0.5 * attempt)
        except Exception as e:
            time.sleep(0.5 * attempt)
    else:
        raise FileExistsError(f"Could not move WEM to {output_path}")
