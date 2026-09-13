import json
import logging
import sys
from pathlib import Path
from typing import Any


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in (
            "request_id",
            "tenant_id",
            "user_id",
            "order_id",
            "payment_id",
            "worker_id",
            "notification_id",
            "count",
        ):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, separators=(",", ":"))


class ErrorFileFormatter(logging.Formatter):
    """
    Plain, human-readable formatter for the error log file.

    Unlike JsonFormatter, this does not JSON-escape the traceback into a
    single-line string — it prints a normal multi-line traceback, and only
    includes the request/tenant/order context that is actually present on
    the record, so the file stays readable and grep-able.
    """

    def format(self, record: logging.LogRecord) -> str:
        context_bits = []
        for key in ("request_id", "tenant_id", "user_id", "order_id", "payment_id"):
            value = getattr(record, key, None)
            if value is not None:
                context_bits.append(f"{key}={value}")
        context = f" ({', '.join(context_bits)})" if context_bits else ""

        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        line = f"{timestamp} [{record.levelname}] {record.name}: {record.getMessage()}{context}"

        if record.exc_info:
            line = f"{line}\n{self.formatException(record.exc_info)}"

        return line


def configure_logging(level: str, log_dir: str = "logs") -> None:
    root = logging.getLogger()
    root.handlers.clear()

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(JsonFormatter())
    root.addHandler(stdout_handler)

    # Separate, human-readable file with ERROR+ only — for scanning what
    # actually needs fixing, without wading through INFO noise or the
    # JSON-escaped traceback blobs in the stdout stream.
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    error_file_handler = logging.FileHandler(
        Path(log_dir) / "error_log", encoding="utf-8"
    )
    error_file_handler.setFormatter(ErrorFileFormatter())
    error_file_handler.setLevel(logging.ERROR)
    root.addHandler(error_file_handler)

    root.setLevel(level.upper())
    logging.getLogger("uvicorn.error").setLevel(logging.CRITICAL)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)