from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator


class StrictMockOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class MockQuestion(StrictMockOutput):
    question: str = Field(min_length=1, max_length=800)
    focus: str = Field(min_length=1, max_length=120)


class MockDimensions(StrictMockOutput):
    relevance: int = Field(ge=0, le=100, strict=True)
    clarity: int = Field(ge=0, le=100, strict=True)
    depth: int = Field(ge=0, le=100, strict=True)
    evidence: int = Field(ge=0, le=100, strict=True)


class MockFeedback(StrictMockOutput):
    question_id: str = Field(min_length=1, max_length=128)
    answer_quote: str = Field(min_length=1, max_length=300)
    strength: str = Field(min_length=1, max_length=600)
    improvement: str = Field(min_length=1, max_length=600)
    suggestion: str = Field(min_length=1, max_length=1200)


class MockReport(StrictMockOutput):
    summary: str = Field(min_length=1, max_length=1600)
    dimensions: MockDimensions | None = None
    feedback: list[MockFeedback] = Field(default_factory=list, max_length=10)
    practice_priorities: list[str] = Field(default_factory=list, max_length=5)

    @computed_field
    @property
    def overall_score(self) -> int | None:
        if self.dimensions is None:
            return None
        return round(sum(self.dimensions.model_dump().values()) / 4)


class MockCommand(BaseModel):
    # No ownerId/userId accepted: public commands must use bearer ownership.
    model_config = ConfigDict(extra="forbid", populate_by_name=True, serialize_by_alias=True,
                              str_strip_whitespace=True)


class CreateMockInterviewRequest(MockCommand):
    idempotency_key: str = Field(min_length=1, max_length=128, alias="idempotencyKey")
    title: str = Field(min_length=1, max_length=120)
    target_role: str = Field(default="", max_length=120, alias="targetRole")
    expected_billing_class: Literal["daily_pass_free", "points"] = Field(alias="expectedBillingClass")


class MockVersionCommand(MockCommand):
    version: int = Field(ge=0, strict=True)


class SelectMockResumeRequest(MockVersionCommand):
    document_id: str = Field(min_length=1, max_length=128, alias="documentId")
    document_version_id: str = Field(min_length=1, max_length=128, alias="documentVersionId")


class MockQuestionCommand(MockVersionCommand):
    question_id: str = Field(min_length=1, max_length=128, alias="questionId")


class SubmitMockAnswerRequest(MockQuestionCommand):
    submission_id: str = Field(min_length=1, max_length=128, alias="submissionId")
    answer: str = Field(min_length=1, max_length=8000)


class MockWireCommand(MockVersionCommand):
    action: Literal["start", "retry", "speak", "playback_started", "playback_waiting", "listen", "replay", "pause", "resume", "submit", "end"]
    question_id: str | None = Field(default=None, alias="questionId", min_length=1, max_length=128)
    answer: str | None = Field(default=None, min_length=1, max_length=8000)
    submission_id: str | None = Field(default=None, alias="submissionId", min_length=1, max_length=128)

    @model_validator(mode="after")
    def action_fields(self):
        if self.action in ("speak", "playback_started", "playback_waiting", "listen", "replay", "submit") and not self.question_id:
            raise ValueError("question required")
        if self.action == "submit" and (not self.answer or not self.submission_id):
            raise ValueError("answer and submission required")
        return self
