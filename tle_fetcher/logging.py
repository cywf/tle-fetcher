"""Structured logging helpers for tle-fetcher."""

from __future__ import annotations

import contextlib
import contextvars
import datetime as _dt
import json
import logging
import os
import sys
from typing import Any, Dict, Iterable, Mapping, Optional

_LOGGER_NAME = "tle_fetcher"
_CONTEXT: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar(
    "tle_fetcher_log_context", default={}
)
_DEFAULT_SENSITIVE_KEYS = {
    "password",
    "pass",
    "passwd",
    "secret",
    "token",
    "api_key",
    "api-key",
    "apikey",
    "authorization",
    "auth",
    "spacetrack_pass",
    "spacetrack_user",
    "n2yo_api_key",
}
_REDACTED = "***REDACTED***"


def _resolve_level(level: Optional[str | int]) -> int:
    if isinstance(level, int):
        return level
    if level is None:
        level = os.getenv("TLE_LOG_LEVEL", "INFO")
    try:
        return int(level)
    except (TypeError, ValueError):
        numeric = logging.getLevelName(str(level).upper())
        if isinstance(numeric, int):
            return numeric
    return logging.INFO


class JSONFormatter(logging.Formatter):
    """Render log records as JSON with contextual metadata."""

    _SKIP_FIELDS: Iterable[str] = {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
    }

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        payload: Dict[str, Any] = {
            "timestamp": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": message,
        }

        context = _CONTEXT.get()
        if context:
            payload["context"] = _redact(context)

        extras: Dict[str, Any] = {}
        for key, value in record.__dict__.items():
            if key in self._SKIP_FIELDS:
                continue
            extras[key] = value
        if extras:
            payload["extra"] = _redact(extras)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=_json_fallback, sort_keys=False)


def _json_fallback(value: Any) -> Any:
    try:
        return repr(value)
    except Exception:  # pragma: no cover - defensive
        return "<unserializable>"


def _should_redact(key: Optional[str]) -> bool:
    if not key:
        return False
    key_lower = key.lower()
    return any(token in key_lower for token in _DEFAULT_SENSITIVE_KEYS)


def _redact(value: Any, key_hint: Optional[str] = None) -> Any:
    if isinstance(value, Mapping):
        return {k: _redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        redacted_items = [_redact(item, key_hint) for item in value]
        return list(redacted_items)
    if _should_redact(key_hint):
        return _REDACTED
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def configure_logging(
    level: Optional[str | int] = None,
    stream: Optional[Any] = None,
    force: bool = False,
) -> logging.Logger:
    """Configure the package logger with JSON output."""

    logger = logging.getLogger(_LOGGER_NAME)
    if force:
        logger.handlers.clear()
    if logger.handlers and not force:
        return logger

    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setFormatter(JSONFormatter())

    logger.addHandler(handler)
    logger.setLevel(_resolve_level(level))
    logger.propagate = False

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a child logger using the configured JSON handler."""

    base = _LOGGER_NAME
    if not name:
        return logging.getLogger(base)
    if name.startswith(base):
        return logging.getLogger(name)
    return logging.getLogger(f"{base}.{name}")


@contextlib.contextmanager
def log_context(**kwargs: Any):
    """Context manager to bind contextual metadata to emitted logs."""

    current = dict(_CONTEXT.get())
    current.update({k: v for k, v in kwargs.items() if v is not None})
    token = _CONTEXT.set(current)
    try:
        yield
    finally:
        _CONTEXT.reset(token)
