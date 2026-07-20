from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings


LOGGER_NAME = "offersteady.backend"

SENSITIVE_LOG_FIELD_NAMES = {
    "api_key",
    "access_key",
    "access_key_id",
    "access_key_secret",
    "authorization",
    "document_text",
    "embedding",
    "object_key",
    "objectkey",
    "password",
    "provider_payload",
    "raw_document",
    "raw_text",
    "rendered_prompt",
    "screenshot",
    "secret",
    "system_prompt",
    "user_prompt",
}

SENSITIVE_LOG_FIELD_FRAGMENTS = (
    "api_key",
    "access_key",
    "authorization",
    "object_key",
    "objectkey",
    "password",
    "provider_payload",
    "rendered_prompt",
    "secret",
)

REDACTED = "[redacted]"


def configure_logging(settings: Settings) -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(settings.log_level)
    if logger.handlers:
        return logger
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _is_sensitive_key(key: str) -> bool:
    normalized = key.replace("-", "_").lower()
    if normalized in {"audio", "audio_base64", "audiobase64", "transcript", "transcript_text", "transcripttext", "text", "token", "access_token", "refresh_token"}:
        return True
    return normalized in SENSITIVE_LOG_FIELD_NAMES or any(fragment in normalized for fragment in SENSITIVE_LOG_FIELD_FRAGMENTS)


def redact_log_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: REDACTED if _is_sensitive_key(str(key)) else redact_log_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_log_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_log_value(item) for item in value)
    return value


def log_event(logger: logging.Logger, level: int, *, settings: Settings, event: str, **fields: Any) -> None:
    payload = {
        "timestamp": utc_now_iso(),
        "level": logging.getLevelName(level),
        "service": settings.app_name,
        "environment": settings.environment,
        "event": event,
        **redact_log_value(fields),
    }
    logger.log(level, json.dumps(payload, ensure_ascii=False, default=str))
