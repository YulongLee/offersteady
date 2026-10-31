"""Fixed-field CN mock timings; never accept user or provider content as log data."""
from __future__ import annotations

from contextvars import ContextVar, Token
import logging
from math import isfinite
from time import monotonic
from uuid import uuid4

from app.core.logging import LOGGER_NAME, log_event


STAGES = ("resume_read", "context_validation", "slot_wait", "provider_request",
          "response_parse", "output_validation", "generation_total")
OUTCOMES = ("success", "failed", "cancelled", "fallback", "skipped")
ERROR_CATEGORIES = (
    "internal_error", "context_invalid", "provider_not_configured", "resume_unavailable",
    "slot_wait_timeout", "provider_timeout", "provider_http_error", "provider_transport_error",
    "response_too_large", "response_json_invalid", "response_envelope_invalid",
    "incomplete_response", "structured_output_invalid", "question_schema_invalid",
    "repeated_question", "report_schema_invalid", "report_evidence_invalid",
    "generation_timeout", "commit_rejected",
)
_active: ContextVar[MockGenerationDiagnostics | None] = ContextVar("cn_mock_diagnostics", default=None)


def safe_error_category(value: object) -> str:
    return value if isinstance(value, str) and value in ERROR_CATEGORIES else "internal_error"


class MockGenerationDiagnostics:
    def __init__(self, settings, kind: str):
        self.settings = settings
        self.kind = kind if kind in ("question", "report") else "unknown"
        self.diagnostic_id = uuid4().hex
        self.enabled = getattr(settings, "product_edition", None) == "cn"

    @classmethod
    def current_or_new(cls, settings, kind: str):
        current = _active.get()
        if (current is not None and current.enabled and current.kind == kind
                and getattr(settings, "product_edition", None) == "cn"):
            return current
        return cls(settings, kind)

    def activate(self) -> Token:
        return _active.set(self)

    @staticmethod
    def reset(token: Token) -> None:
        _active.reset(token)

    def record(self, stage: str, started_at: float, *, outcome: str = "success",
               error_category: object = None, http_status: object = None, **_ignored: object) -> None:
        if not self.enabled or stage not in STAGES:
            return
        try:
            if outcome not in OUTCOMES:
                outcome, error_category = "failed", "internal_error"
            elapsed = (monotonic() - started_at) * 1000
            duration_ms = round(min(3_600_000, max(0, elapsed)), 3) if isfinite(elapsed) else 0
            fields = {"feature": "mock-interview", "action": "generate", "kind": self.kind,
                      "diagnostic_id": self.diagnostic_id, "stage": stage, "outcome": outcome,
                      "duration_ms": duration_ms}
            if error_category is not None:
                fields["error_code"] = safe_error_category(error_category)
            if type(http_status) is int and 100 <= http_status <= 599:
                fields["http_status"] = http_status
            log_event(logging.getLogger(LOGGER_NAME), logging.INFO, settings=self.settings,
                      event="mock_interview.generation_stage", **fields)
        except Exception:
            # Observability must not change model calls, output, claim cleanup or
            # cancellation; do not log a second error containing the first one.
            pass
