from __future__ import annotations

import json
import logging

from app.core.config import Settings
from app.core.logging import log_event, redact_log_value


def test_log_redaction_removes_material_and_provider_sensitive_fields() -> None:
    payload = {
        "objectKey": "materials/development/users/u/documents/resume/d/versions/v/original/o.pdf",
        "rendered_prompt": "system prompt\n\nuser prompt",
        "provider_payload": {"choices": [{"message": "raw provider response"}]},
        "embedding": [0.1, 0.2],
        "nested": {"api_key": "sk-test", "safe_count": 2},
        "prompt_tokens": 42,
        "audioBase64": "raw-pcm",
        "transcriptText": "private interview content",
        "token": "rt-secret",
    }

    redacted = redact_log_value(payload)

    assert redacted["objectKey"] == "[redacted]"
    assert redacted["rendered_prompt"] == "[redacted]"
    assert redacted["provider_payload"] == "[redacted]"
    assert redacted["embedding"] == "[redacted]"
    assert redacted["nested"]["api_key"] == "[redacted]"
    assert redacted["nested"]["safe_count"] == 2
    assert redacted["prompt_tokens"] == 42
    assert redacted["audioBase64"] == "[redacted]"
    assert redacted["transcriptText"] == "[redacted]"
    assert redacted["token"] == "[redacted]"


def test_log_event_serializes_redacted_payload(caplog) -> None:
    logger = logging.getLogger("offersteady.test.redaction")
    logger.handlers = []
    logger.propagate = True
    logger.setLevel(logging.INFO)

    with caplog.at_level(logging.INFO, logger="offersteady.test.redaction"):
        log_event(
            logger,
            logging.INFO,
            settings=Settings(app_name="test", environment="test"),
            event="material.rag",
            object_key="materials/production/users/private/documents/doc.pdf",
            system_prompt="hidden",
            source_count=1,
        )

    record = json.loads(caplog.records[-1].message)
    assert record["object_key"] == "[redacted]"
    assert record["system_prompt"] == "[redacted]"
    assert record["source_count"] == 1
