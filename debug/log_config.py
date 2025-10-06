# debug/log_config.py
from loguru import logger
import os
import sys
import platform
import psutil
import uuid
from datetime import datetime
from pathlib import Path

# === Setup ===
log_dir = Path("debug_logs")
log_dir.mkdir(exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = log_dir / f"debug_pipeline_{timestamp}.log"

logger.remove()
logger.add(
    str(log_file),
    level="TRACE",
    format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {name}:{function}:{line} - {message}",
    rotation="100 MB",
    retention="30 days",
    compression="zip",
    enqueue=True,
    backtrace=True,
    diagnose=True
)

# === Environment Snapshot ===
def log_environment():
    logger.info(f"System: {platform.system()} {platform.release()} ({platform.version()})")
    logger.info(f"Python: {platform.python_version()}")
    logger.info(f"CPU: {platform.processor()}")
    logger.info(f"RAM: {psutil.virtual_memory().total / (1024 ** 3):.2f} GB")
    logger.info(f"Working Dir: {os.getcwd()}")
    logger.info(f"PID: {os.getpid()}")
    logger.info(f"Trace ID: {uuid.uuid4()}")

log_environment()
