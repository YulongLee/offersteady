from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from typing import Literal

from app.ports.chat import AnswerTaskStatus
from app.schemas.retrieval import RetrievalResponse


class LiveAnswerQuestionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    user_id: str = Field(min_length=1, alias="userId")
    session_id: str = Field(min_length=1, alias="sessionId")
    question: str = Field(min_length=1)
    stream: bool = True


class LiveAnswerChunkResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    sequence: int
    text: str
    is_final: bool = Field(alias="isFinal")


class LiveAnswerTaskResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    task_id: str = Field(alias="taskId")
    session_id: str = Field(alias="sessionId")
    owner_user_id: str = Field(alias="ownerUserId")
    question: str
    answer_text: str = Field(alias="answerText")
    status: AnswerTaskStatus
    stream_mode: bool = Field(alias="streamMode")
    provider_name: str | None = Field(default=None, alias="providerName")
    model_name: str | None = Field(default=None, alias="modelName")
    prompt_template_id: str | None = Field(default=None, alias="promptTemplateId")
    prompt_version: str | None = Field(default=None, alias="promptVersion")
    retrieval_excerpt_count: int = Field(alias="retrievalExcerptCount")
    material_context_status: str = Field(default="not-assembled", alias="materialContextStatus")
    fixed_source_count: int = Field(default=0, alias="fixedSourceCount")
    retrieved_source_count: int = Field(default=0, alias="retrievedSourceCount")
    material_provenance: dict[str, object] = Field(default_factory=dict, alias="materialProvenance")
    unavailable_material_sources: list[dict[str, object]] = Field(default_factory=list, alias="unavailableMaterialSources")
    retry_count: int = Field(alias="retryCount")
    error_code: str | None = Field(default=None, alias="errorCode")
    error_message: str | None = Field(default=None, alias="errorMessage")
    created_at_ms: int = Field(alias="createdAtMs")
    updated_at_ms: int = Field(alias="updatedAtMs")
    completed_at_ms: int | None = Field(default=None, alias="completedAtMs")
    chunks: list[LiveAnswerChunkResponse] = Field(default_factory=list)


class LiveAnswerResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    task: LiveAnswerTaskResponse
    retrieval: RetrievalResponse


LiveAnswerStreamEventType = Literal["task-started", "chunk", "completed", "failed", "cancelled"]


class LiveAnswerStreamEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    type: LiveAnswerStreamEventType
    task: LiveAnswerTaskResponse | None = None
    chunk: LiveAnswerChunkResponse | None = None
    retrieval: RetrievalResponse | None = None
    error_code: str | None = Field(default=None, alias="errorCode")
    error_message: str | None = Field(default=None, alias="errorMessage")
    partial_text: str | None = Field(default=None, alias="partialText")


class CancelLiveAnswerRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    user_id: str = Field(min_length=1, alias="userId")
    expected_revision: int | None = Field(default=None, alias="expectedRevision")
    idempotency_key: str | None = Field(default=None, alias="idempotencyKey")


class CancelLiveAnswerResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    outcome: str
    task: LiveAnswerTaskResponse
    billing_released: bool = Field(alias="billingReleased")
