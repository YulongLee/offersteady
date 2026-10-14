"""Fixed operational fields only; interview content never enters these events."""
from __future__ import annotations

import logging
from contextlib import contextmanager
from contextvars import ContextVar
from time import monotonic
from uuid import uuid4

from app.core.config import Settings
from app.core.logging import LOGGER_NAME, log_event


STAGES = frozenset({"resume_read", "context_validation", "slot_wait", "provider_request", "response_parse",
                    "output_validation", "generation_total"})
ERROR_CATEGORIES = frozenset({
    "generation_unavailable", "context_limit", "provider_unconfigured", "invalid_round_state",
    "slot_wait_timeout", "provider_timeout", "provider_http_error", "provider_transport_error",
    "response_too_large", "response_envelope_invalid", "response_json_invalid", "incomplete_response",
    "structured_output_invalid", "question_schema_invalid", "repeated_question",
    "report_schema_invalid", "report_evidence_invalid", "resume_unavailable", "resume_read_error",
    "selected_resume_missing", "generation_timeout", "commit_rejected", "internal_error", "cancelled",
})


def safe_error_category(value: str) -> str:
    return value if isinstance(value, str) and value in ERROR_CATEGORIES else "internal_error"


class MockGenerationDiagnostics:
    def __init__(self, settings: Settings, kind: str):
        self.settings = settings
        self.kind = kind if kind in ("question", "report") else "unknown"
        # A fresh operation-local ID permits joining stages without recording
        # owner/session/document/device IDs or any submitted content.
        self.diagnostic_id = uuid4().hex

    def record(self, stage: str, started_at: float, *, outcome: str = "success",
               error_category: str | None = None, http_status: int | None = None) -> None:
        if not isinstance(stage, str) or stage not in STAGES:
            return
        outcome = outcome if outcome in ("success", "failed", "cancelled", "fallback") else "failed"
        fields = dict(feature="mock-interview", action="generate", kind=self.kind,
                      diagnostic_id=self.diagnostic_id, stage=stage, outcome=outcome,
                      duration_ms=round(max(0, monotonic() - started_at) * 1000, 3),
                      error_code=safe_error_category(error_category) if error_category else None)
        if isinstance(http_status, int) and not isinstance(http_status, bool) and 100 <= http_status <= 599:
            fields["http_status"] = http_status
        log_event(logging.getLogger(LOGGER_NAME), logging.WARNING if outcome == "failed" else logging.INFO,
                  settings=self.settings, event="mock_interview.generation_stage", **fields)


_active: ContextVar[MockGenerationDiagnostics | None] = ContextVar("mock_generation_diagnostics", default=None)


@contextmanager
def generation_diagnostics(settings: Settings, kind: str):
    """Reuse a job's trace across async generation; reset after success or failure."""
    current = _active.get()
    if current is not None and current.kind == kind:
        yield current
        return
    diagnostics = MockGenerationDiagnostics(settings, kind)
    token = _active.set(diagnostics)
    try:
        yield diagnostics
    finally:
        _active.reset(token)
