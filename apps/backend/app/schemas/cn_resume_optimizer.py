"""Strict optimizer wire/provider types; document text is untrusted plain data."""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictBool, model_validator
from pydantic_core import PydanticCustomError


class WireModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True, extra="forbid")


class CreateResumeOptimization(WireModel):
    idempotency_key: str = Field(min_length=1, max_length=128, alias="idempotencyKey")
    source_document_id: str = Field(min_length=1, max_length=160, alias="sourceDocumentId")
    source_version_id: str = Field(min_length=1, max_length=160, alias="sourceVersionId")
    target_role: str = Field(default="", max_length=120, alias="targetRole")
    jd_document_id: str | None = Field(default=None, min_length=1, max_length=160, alias="jdDocumentId")
    jd_version_id: str | None = Field(default=None, min_length=1, max_length=160, alias="jdVersionId")
    jd_text: str = Field(default="", max_length=12000, alias="jdText")
    quoted_quota_day: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$", alias="quotedQuotaDay")
    quoted_billing_class: Literal["daily_pass_free", "points"] = Field(alias="quotedBillingClass")
    quoted_points: StrictInt = Field(alias="quotedPoints")
    confirm_points_charge: StrictBool = Field(default=False, alias="confirmPointsCharge")
    confirm_processing: Literal[True] = Field(alias="confirmProcessing")

    @model_validator(mode="after")
    def validate_inputs(self):
        if self.quoted_points not in (0, 100):
            raise PydanticCustomError("resume_quote_points", "本次报价只支持免费或 100 积分。")
        if bool(self.jd_document_id) != bool(self.jd_version_id):
            raise PydanticCustomError("resume_jd_pair", "请同时提供岗位资料及其版本。")
        if self.jd_document_id and self.jd_text.strip():
            raise PydanticCustomError("resume_jd_exclusive", "请选择岗位资料或粘贴岗位描述，不能同时提供。")
        if not self.idempotency_key.strip():
            raise PydanticCustomError("resume_idempotency_empty", "请求标识不能为空。")
        self.target_role = self.target_role.strip()
        self.jd_text = self.jd_text.strip()
        return self


class UpdateResumeDraft(WireModel):
    expected_revision: int = Field(ge=1, alias="expectedRevision")
    markdown: str = Field(min_length=1, max_length=60000)


class SaveOptimizedResume(WireModel):
    expected_revision: int = Field(ge=1, alias="expectedRevision")
    confirm_independent_copy: Literal[True] = Field(alias="confirmIndependentCopy")
    facts_confirmed: Literal[True] = Field(alias="factsConfirmed")


class Evidence(WireModel):
    source: Literal["resume", "jd"]
    quote: str = Field(min_length=1, max_length=600)


class Dimension(WireModel):
    key: Literal["completeness", "impact", "clarity", "structure", "roleMatch"]
    score: StrictInt = Field(ge=0, le=100)
    reason: str = Field(min_length=1, max_length=600)
    evidence: list[Evidence] = Field(min_length=1, max_length=4)


class ResumeSuggestion(WireModel):
    priority: Literal["high", "medium", "low"]
    title: str = Field(min_length=1, max_length=160)
    explanation: str = Field(min_length=1, max_length=1200)
    recommendation: str = Field(min_length=1, max_length=1200)
    evidence: list[Evidence] = Field(min_length=1, max_length=4)


class ResumeEdit(WireModel):
    source_quote: str = Field(min_length=1, max_length=2000, alias="sourceQuote")
    replacement: str = Field(min_length=1, max_length=2500)


class ProviderResumeReview(WireModel):
    dimensions: list[Dimension] = Field(min_length=4, max_length=5)
    suggestions: list[ResumeSuggestion] = Field(min_length=1, max_length=12)
    missing_facts: list[str] = Field(default_factory=list, max_length=12, alias="missingFacts")
    edits: list[ResumeEdit] = Field(default_factory=list, max_length=24)
