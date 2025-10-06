import subprocess
from pathlib import Path


def convert_to_wem(config, temp_wav_path, conversion_quality="Vorbis Quality High"):
    # Ensure absolute paths
    temp_wav_path = Path(temp_wav_path).resolve()
    output_dir = config.mod_dir.resolve()
    script_path = config.cmd_script_path.resolve()

    subprocess.run([
        "cmd.exe", "/c",
        str(script_path),
        f'--conversion:{conversion_quality}',
        f'--out:{str(output_dir)}',
        str(temp_wav_path)
    ], check=True, creationflags=config.create_no_window)
