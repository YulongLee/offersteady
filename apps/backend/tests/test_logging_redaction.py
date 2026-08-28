from __future__ import annotations

import json
import logging

from app.core.config import Settings
from app.core.logging import log_event, redact_log_value
from app.ports.chat import PromptBuildResult, PromptConfig
from app.services.chat_service import ChatService


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


def test_language_route_telemetry_keeps_dimensions_but_redacts_all_user_content(caplog) -> None:
    logger = logging.getLogger("offersteady.test.language-route-redaction")
    logger.handlers = []
    logger.propagate = True
    logger.setLevel(logging.INFO)

    with caplog.at_level(logging.INFO, logger=logger.name):
        log_event(
            logger,
            logging.INFO,
            settings=Settings(app_name="test", environment="test"),
            event="chat.language_route",
            interview_language="en-US",
            stage="detail",
            prompt_template_id="interview-chat-en-detail",
            prompt_version="v4",
            transcript="synthetic private transcript",
            screenshot="synthetic private pixels",
            document_text="synthetic private resume",
            question_hash="0123456789ab",
            question_length=31,
        )

    record = json.loads(caplog.records[-1].message)
    assert record["interview_language"] == "en-US"
    assert record["stage"] == "detail"
    assert record["prompt_template_id"] == "interview-chat-en-detail"
    assert record["prompt_version"] == "v4"
    assert record["question_hash"] == "0123456789ab"
    assert record["question_length"] == 31
    assert record["transcript"] == "[redacted]"
    assert record["screenshot"] == "[redacted]"
    assert record["document_text"] == "[redacted]"


def test_output_language_violation_telemetry_is_content_free(caplog) -> None:
    logger = logging.getLogger("offersteady.test.output-language-redaction")
    logger.handlers = []
    logger.propagate = True
    logger.setLevel(logging.WARNING)
    service = ChatService.__new__(ChatService)
    service.logger = logger
    service.settings = Settings(_env_file=None, app_name="test", environment="test")
    prompt = PromptBuildResult(
        system_prompt="private system prompt",
        user_prompt="介绍自己并引用秘密简历",
        rendered_prompt="private rendered prompt",
        prompt_config=PromptConfig(
            template_id="interview-chat-en-quick",
            version="v4",
            max_history_entries=6,
        ),
        retrieval_excerpt_count=1,
    )

    with caplog.at_level(logging.WARNING, logger=logger.name):
        service._log_language_violation(
            session_id="session-safe-id",
            task_id="task-safe-id",
            stage="quick",
            prompt=prompt,
            attempt=0,
        )

    serialized = caplog.records[-1].message
    record = json.loads(serialized)
    assert record["event"] == "chat.output_language_violation"
    assert record["interview_language"] == "en-US"
    assert record["stage"] == "quick"
    assert record["prompt_template_id"] == "interview-chat-en-quick"
    assert record["prompt_version"] == "v4"
    assert record["provider_attempt"] == 0
    assert record["error_code"] == "chat_output_language_violation"
    assert "介绍自己" not in serialized
    assert "秘密简历" not in serialized
    assert "private" not in serialized
