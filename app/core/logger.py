# -*- coding: utf-8 -*-
"""
SINAX Logging System
Configures robust file and console logging without leaking technical stack traces to the end user.
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_logger_initialized = False

def get_log_dir() -> Path:
    """Returns directory path where logs should be stored."""
    # Portable or AppData fallback
    local_log_dir = Path("logs")
    try:
        local_log_dir.mkdir(parents=True, exist_ok=True)
        return local_log_dir
    except Exception:
        app_data = Path(os.environ.get('APPDATA', str(Path.home()))) / "SINAX" / "logs"
        app_data.mkdir(parents=True, exist_ok=True)
        return app_data

def setup_logging(level=logging.INFO) -> None:
    """Configures root logger with rotating file handler and console handler."""
    global _logger_initialized
    if _logger_initialized:
        return

    log_dir = get_log_dir()
    log_file = log_dir / "sinax.log"

    root_logger = logging.getLogger("SINAX")
    root_logger.setLevel(level)

    # Formatters
    file_formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_formatter = logging.Formatter(
        fmt="[%(levelname)s] %(name)s: %(message)s"
    )

    # Rotating File Handler (Max 5MB per file, up to 3 backups)
    try:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Could not setup log file: {e}", file=sys.stderr)

    # Console Handler (UTF-8 safe on Windows)
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    _logger_initialized = True
    root_logger.info("SINAX Logging Initialized.")

def get_logger(name: str) -> logging.Logger:
    """Returns a namespaced child logger."""
    if not _logger_initialized:
        setup_logging()
    return logging.getLogger(f"SINAX.{name}")
