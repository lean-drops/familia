"""
Structured, rotating log configuration for both development and production.

• dictConfig-based (officially recommended) – single point of truth
• Console + RotatingFile (10 MB × 5) handlers
• ISO-8601 timestamps, module context, line-numbers in verbose formatter
"""

import logging
import logging.config
from pathlib import Path
import os

def configure_logging() -> None:
    log_level = "DEBUG" if os.getenv("FLASK_ENV") == "development" else "INFO"
    logs_dir = Path(os.getenv("LOG_DIR", Path(__file__).resolve().parent / "logs"))
    logs_dir.mkdir(exist_ok=True)

    cfg = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            },
            "verbose": {
                "format": (
                    "%(asctime)s | %(levelname)-8s | %(name)s | "
                    "%(module)s:%(lineno)d | %(message)s"
                ),
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "level": log_level,
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "verbose",
                "level": log_level,
                "filename": str(logs_dir / "application.log"),
                "maxBytes": 10 * 1024 * 1024,  # 10 MiB
                "backupCount": 5,
            },
        },
        "root": {"handlers": ["console", "file"], "level": log_level},
    }

    logging.config.dictConfig(cfg)
    logging.getLogger(__name__).info("Logging configured (level=%s)", log_level)
