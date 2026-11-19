"""
Logging configuration for tracking Agent reasoning, token usage, and execution stream.
"""

from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys
from typing import Optional

from .settings import settings


class AgentLogFormatter(logging.Formatter):
    """Custom formatter with distinct prefixes for agent telemetry."""

    GREY = "\x1b[38;20m"
    BLUE = "\x1b[34;20m"
    CYAN = "\x1b[36;20m"
    GREEN = "\x1b[32;20m"
    YELLOW = "\x1b[33;20m"
    RED = "\x1b[31;20m"
    BOLD_RED = "\x1b[31;1m"
    RESET = "\x1b[0m"

    FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

    LEVEL_COLORS = {
        logging.DEBUG: GREY,
        logging.INFO: CYAN,
        logging.WARNING: YELLOW,
        logging.ERROR: RED,
        logging.CRITICAL: BOLD_RED,
    }

    def format(self, record: logging.LogRecord) -> str:
        color = self.LEVEL_COLORS.get(record.levelno, self.RESET)
        formatter = logging.Formatter(f"{color}{self.FORMAT}{self.RESET}", datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


def setup_logging(
    level: Optional[str] = None,
    log_level: Optional[str] = None,
    log_to_file: bool = True,
    log_file_name: Optional[str] = None,
) -> logging.Logger:
    """Configures root and application loggers."""
    effective_level = level or log_level or settings.LOG_LEVEL
    log_level_val = getattr(logging, effective_level.upper() if effective_level else "INFO", logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level_val)

    # Clear existing handlers to prevent duplicate lines
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(AgentLogFormatter())
    root_logger.addHandler(console_handler)

    # File Handler
    if log_to_file:
        settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        if not log_file_name:
            timestamp = datetime.now().strftime("%Y%m%d")
            log_file_name = f"job_orchestrator_{timestamp}.log"

        file_path = settings.LOGS_DIR / log_file_name
        file_handler = RotatingFileHandler(
            file_path,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | [%(filename)s:%(lineno)d] | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    app_logger = logging.getLogger("JobOrchestrator")
    app_logger.setLevel(log_level)
    return app_logger


def get_logger(name: str = "JobOrchestrator") -> logging.Logger:
    """Helper to get a named logger."""
    return logging.getLogger(name)
