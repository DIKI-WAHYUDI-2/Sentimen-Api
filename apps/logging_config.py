import json
import logging
import logging.config
import os
from pathlib import Path


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
        }

        for field in ("request_id", "user_id", "query", "news_id", "path", "method", "status_code"):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


def setup_logging():
    environment = os.environ.get("FLASK_ENV", "development").lower()
    default_level = "DEBUG" if environment == "development" else "INFO"
    log_level = os.environ.get("LOG_LEVEL", default_level).upper()
    use_json_logs = os.environ.get("LOG_JSON", "false").lower() == "true"

    log_dir = Path(os.environ.get("LOG_DIR", Path.cwd() / "logs"))
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"

    formatter_config = {
        "standard": {
            "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            "datefmt": "%Y-%m-%dT%H:%M:%S",
        },
        "json": {
            "()": "apps.logging_config.JsonFormatter",
            "datefmt": "%Y-%m-%dT%H:%M:%S",
        },
    }
    selected_formatter = "json" if use_json_logs else "standard"

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": formatter_config,
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": log_level,
                    "formatter": selected_formatter,
                    "stream": "ext://sys.stdout",
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": log_level,
                    "formatter": selected_formatter,
                    "filename": str(log_file),
                    "maxBytes": 5 * 1024 * 1024,
                    "backupCount": 5,
                    "encoding": "utf-8",
                },
            },
            "loggers": {
                "": {
                    "handlers": ["console", "file"],
                    "level": log_level,
                }
            },
        }
    )

    logging.getLogger(__name__).info("Logging configured")
