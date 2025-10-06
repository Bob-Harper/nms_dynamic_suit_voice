# wem_utils_debug.py

import subprocess
from pathlib import Path
from debug.log_config import logger  # Loguru setup

def convert_to_wem(config, temp_wav_path, conversion_quality="Vorbis Quality High"):
    try:
        logger.trace(f"Starting WEM conversion for: {temp_wav_path} with quality: {conversion_quality}")

        temp_wav_path = Path(temp_wav_path).resolve()

        output_dir = config.temp_wem_dir.resolve()
        final_dir = config.mod_dir.resolve()
        script_path = config.cmd_script_path.resolve()

        logger.debug(f"Resolved paths: WAV: {temp_wav_path} -- Output Dir: {output_dir} -- Script: {script_path}")

        cmd = [
            "cmd.exe", "/c",
            str(script_path),
            f'--conversion:{conversion_quality}',
            f'--out:{str(output_dir)}',
            str(temp_wav_path)
        ]

        logger.debug(f"Executing subprocess: {' '.join(cmd)}")
        subprocess.run(cmd, check=True, creationflags=config.create_no_window)
        logger.success(f"WEM conversion completed for: {temp_wav_path.name}")

        wem_file = output_dir / temp_wav_path.with_suffix(".wem").name
        logger.debug(f"Temp WEM generated at: {wem_file}")
        final_wem_file = final_dir / wem_file.name

        try:
            wem_file.replace(final_wem_file)
            logger.success(f"WEM moved to final location: {final_wem_file}")
        except Exception as e:
            logger.exception(f"WEM unable to save to final location: {final_wem_file} -- {e}")
            pass

    except subprocess.CalledProcessError as e:
        logger.exception(f"Subprocess failed during WEM conversion: {e}")
        raise

    except Exception as e:
        logger.exception(f"Unexpected error in convert_to_wem: {e}")
        raise
