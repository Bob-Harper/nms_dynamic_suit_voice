import csv
from loguru import logger
import sys
from pathlib import Path
from datetime import datetime
import platform
import psutil
import uuid
import os
# Redirect stdout/stderr to a file when running headless
if os.path.basename(sys.executable).lower() == "pythonw.exe":
    sys.stdout = open("debug/debug_logs/headless_stdout.log", "w")
    sys.stderr = open("debug/debug_logs/headless_stderr.log", "w")


# we do not log the logger.  only a maniac would log the logger.
# --- Loguru setup (console + file) ---
logger.remove()
print("CWD:", os.getcwd())
DEBUG_ENABLED = os.getenv("PROMPT_CONSOLE", "false").strip().lower() == "true"
log_format_console = (
    "<green>{time:MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "{message}"
)

if os.path.basename(sys.executable).lower() != "pythonw.exe":
    logger.add(
        sys.__stdout__,
        level="DEBUG",
        format=log_format_console,
        colorize=False,
        enqueue=True,
        backtrace=True,
        diagnose=False
    )

log_dir = Path("C:/NMS_SUIT_VOICE/debug/debug_logs")
log_dir.mkdir(parents=True, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = log_dir / f"debug_pipeline_{timestamp}.log"

# format = "{time:YYYY-MM-DD at HH:mm:ss} | {level} | {module}:{function}:{line} - {message}",
# what??  it's logging its own function and line.  log_config.debug_print:69  wtf man.
logger.add(
    str(log_file),
    level="TRACE",
    format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    rotation="100 MB",
    retention="30 days",
    compression="zip",
    enqueue=True,
    backtrace=True,
    diagnose=True
)

# --- Environment snapshot ---
def log_environment():
    logger.info(f"System: {platform.system()} {platform.release()} ({platform.version()})")
    logger.info(f"Python: {platform.python_version()}")
    logger.info(f"CPU: {platform.processor()}")
    logger.info(f"RAM: {psutil.virtual_memory().total / (1024 ** 3):.2f} GB")
    logger.info(f"Working Dir: {os.getcwd()}")
    logger.info(f"PID: {os.getpid()}")
    logger.info(f"Trace ID: {uuid.uuid4()}")
    logger.info(f"Log Dir: {log_dir}")
    logger.info(f"Log FIle: {log_file}")

log_environment()

# --- Drop-in debug_print replacement ---
def debug_print(msg, *args, **kwargs):
    """Conditional debug print based on PROMPT_CONSOLE env toggle."""
    if not DEBUG_ENABLED:
        return
    if args or kwargs:
        msg = msg.format(*args, **kwargs)
    logger.debug(msg)


def log_to_file(config, wem_id, category, intent, original_phrase, reworded):

    fieldnames = ["WEM number", "Category", "Original", "Intent Phrase", "Final Voice Line"]
    file_exists = Path(config.game_output_csv).exists()
    logger.info(f"File_exists: {file_exists}")
    log_entry = {
        "WEM number": wem_id,
        "Category": category if wem_id in config.intent_map else "",
        "Original": original_phrase if wem_id in config.intent_map else "",
        "Intent Phrase": intent if wem_id in config.intent_map else "",
        "Final Voice Line": reworded
    }

    with open(config.game_output_csv, "a", newline='', encoding='utf-8') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(log_entry)

    return
