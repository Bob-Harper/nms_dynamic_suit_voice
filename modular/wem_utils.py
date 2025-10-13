# wem_utils_debug.py
import subprocess
from pathlib import Path


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

        try:
            wem_file.replace(final_wem_file)
            # logger.success(f"WEM moved to final location: {final_wem_file}")
        except Exception as e:
            print(f"WEM unable to save to final location: {final_wem_file} -- {e}")
            pass

    except subprocess.CalledProcessError as e:
        print(f"Subprocess failed during WEM conversion: {e}")
        raise

    except Exception as e:
        print(f"Unexpected error in convert_to_wem: {e}")
        raise
