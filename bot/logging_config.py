"""
Centralized logging configuration.

Logs go to both the console (INFO+) and a rotating log file (DEBUG+),
so the file contains full request/response detail while the console
stays readable.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE = LOG_DIR / "trading_bot.log"

_configured = False


def setup_logging(level: int = logging.DEBUG) -> logging.Logger:
    """Configure and return the root application logger.

    Safe to call multiple times; configuration is applied only once.
    """
    global _configured
    logger = logging.getLogger("trading_bot")

    if _configured:
        return logger

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger.setLevel(level)
    logger.propagate = False

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Rotating file handler: keeps full detail (requests, responses, errors)
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)

    # Console handler: keep it quieter/readable
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(fmt)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    _configured = True
    return logger


def get_logger() -> logging.Logger:
    """Return the configured application logger (configures it if needed)."""
    return setup_logging()
