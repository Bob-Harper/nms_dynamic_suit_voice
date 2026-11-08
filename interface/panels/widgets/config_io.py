# interface\panels\widgets\config_io.py
import json
import os
from pathlib import Path


def write_json_atomic(path: Path, data: dict) -> None:
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)
        file.write("\n")
    os.replace(temporary_path, path)
