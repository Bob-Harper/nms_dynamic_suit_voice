# debug/log_config.py
from loguru import logger
import sys
import os
from pathlib import Path
from datetime import datetime
import platform
import psutil
import uuid

# we do not log the logger.
# --- Loguru setup (console + file) ---
logger.remove()

log_format_console = (
    "<green>{time:MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "{message}"
)

logger.add(
    sys.__stdout__,
    level="DEBUG",
    format=log_format_console,
    colorize=False,
    enqueue=True,
    backtrace=True,
    diagnose=False
)

log_dir = Path("debug_logs")
log_dir.mkdir(exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = log_dir / f"debug_pipeline_{timestamp}.log"

# format = "{time:YYYY-MM-DD at HH:mm:ss} | {level} | {module}:{function}:{line} - {message}",
# what??  it's logging it's onw function and line.  log_config.debug_print:69  wtf man.
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

log_environment()

# --- Drop-in debug_print replacement ---
def debug_print(msg, *args, **kwargs):
    """
    Replacement for print(). Sends message to logger.debug().
    Includes function name and line number automatically.
    """
    if args or kwargs:
        msg = msg.format(*args, **kwargs)
    logger.debug(msg)
