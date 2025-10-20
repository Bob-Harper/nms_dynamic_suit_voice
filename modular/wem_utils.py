# wem_utils_debug.py
import subprocess
from pathlib import Path
import time

def convert_to_wem(config, temp_wav_path):
    try:
        temp_wav_path = Path(temp_wav_path).resolve()
        output_dir = config.temp_wem_dir.resolve()
        final_dir = config.mod_dir.resolve()
        script_path = config.cmd_script_path.resolve()

        cmd = [
            "cmd.exe", "/c",
            str(script_path),
            f'--out:{str(output_dir)}',
            str(temp_wav_path)
        ]

        subprocess.run(cmd, check=True, creationflags=config.create_no_window)
        wem_file = output_dir / temp_wav_path.with_suffix(".wem").name
        final_wem_file = final_dir / wem_file.name

        max_attempts = 10
        for attempt in range(1, max_attempts + 1):
            try:
                wem_file.replace(final_wem_file)
                print(f"WEM moved to final location: {final_wem_file}")
                break
            except PermissionError as e:
                wait_time = 0.5 * attempt  # increasing delay: 0.5s, 1s, 1.5s, ...
                print(f"Attempt {attempt}: File in use, waiting {wait_time:.1f}s before retry...")
                time.sleep(wait_time)
            except Exception as e:
                wait_time = 0.5 * attempt
                print(f"Attempt {attempt}: Unexpected error: {e} — retrying in {wait_time:.1f}s...")
                time.sleep(wait_time)
        else:
            print(f"Final attempt failed: Could not move WEM to {final_wem_file}")

    except subprocess.CalledProcessError as e:
        print(f"Subprocess failed during WEM conversion: {e}")
        raise

    except Exception as e:
        print(f"Unexpected error in convert_to_wem: {e}")
        raise
