import logging
import os
from pathlib import Path

# Ensure the logs directory exists in the workspace
LOGS_DIR = Path("/home/leehm/linux_project/Agent/runtime/logs")
LOGS_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOGS_DIR / "execution.log"

# Configure standard Python logger
logger = logging.getLogger("fractal_system")
logger.setLevel(logging.DEBUG)

# File handler with UTF-8 support
file_handler = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)

# Beautiful, detailed log formatter
formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
file_handler.setFormatter(formatter)

# Avoid adding duplicate handlers if the module is re-imported
if not logger.handlers:
    logger.addHandler(file_handler)

# Export a function to log high-visibility header breaks
def log_header(title: str):
    logger.info("=" * 80)
    logger.info(f" {title} ".center(80, "="))
    logger.info("=" * 80)
