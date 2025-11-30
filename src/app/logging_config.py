from __future__ import annotations

import json
import logging
import sys
from typing import Any, Dict


class JsonLogFormatter(logging.Formatter):
    """
    Simple JSON formatter so our logs are structured in CloudWatch.

    Every log line becomes a single JSON object with consistent fields.
    """

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        payload: Dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "time": self.formatTime(record, self.datefmt),
        }

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        # Add any extra fields passed via logger(..., extra={...})
        for key, value in record.__dict__.items():
            if key.startswith("_") or key in payload:
                continue
            try:
                json.dumps(value)
                payload[key] = value
            except TypeError:
                payload[key] = repr(value)

        return json.dumps(payload)


def configure_logging(app_name: str, level: str = "INFO") -> None:
    """
    Configure the root logger once for the whole process.

    Idempotent: calling it multiple times will not duplicate handlers.
    """
    root = logging.getLogger()
    if getattr(root, "_xyz_configured", False):
        return

    root.setLevel(level.upper())
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(JsonLogFormatter())

    root.handlers.clear()
    root.addHandler(handler)
    root._xyz_configured = True  # type: ignore[attr-defined]

    logging.getLogger(__name__).info("Logging configured", extra={"app_name": app_name})
