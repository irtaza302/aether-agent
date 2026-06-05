"""
Structured logging configuration for Aether.

Provides a rotating file logger at ~/.aether_logs/aether.log plus
an optional console handler controlled by --verbose.
"""

import os
import logging
from logging.handlers import RotatingFileHandler

# ─── Constants ──────────────────────────────────────────────────────────────────

LOG_DIR = os.path.expanduser("~/.aether_logs")
LOG_FILE = os.path.join(LOG_DIR, "aether.log")
MAX_LOG_BYTES = 5 * 1024 * 1024  # 5 MB per file
BACKUP_COUNT = 3  # Keep 3 rotated log files

# Module-level logger used throughout the application
logger = logging.getLogger("aether")


def setup_logging(verbose: bool = False) -> logging.Logger:
    """
    Configure logging for the application.

    - Always logs to ~/.aether_logs/aether.log (DEBUG level, rotating).
    - When verbose=True, also logs DEBUG to stderr.
    - When verbose=False, only WARNING+ goes to stderr.

    Returns the configured root "aether" logger.
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    logger.setLevel(logging.DEBUG)

    # Clear any existing handlers (e.g. on re-init)
    logger.handlers.clear()

    # ── File handler (always DEBUG) ──
    file_fmt = logging.Formatter(
        fmt="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_LOG_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_fmt)
    logger.addHandler(file_handler)

    # ── Console handler (level depends on --verbose) ──
    console_fmt = logging.Formatter(
        fmt="%(levelname)-8s │ %(message)s",
    )
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if verbose else logging.WARNING)
    console_handler.setFormatter(console_fmt)
    logger.addHandler(console_handler)

    logger.debug("Aether logging initialized (verbose=%s)", verbose)
    return logger
