from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.material_formats import MaterialKind


ProcessingStage = Literal["UPLOADED", "QUEUED", "PARSING", "CHUNKING", "EMBEDDING", "VECTOR_WRITING", "COMPLETED", "FAILED"]


class ProcessingTaskResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    task_id: str = Field(alias="taskId")
    document_id: str = Field(alias="documentId")
    owner_user_id: str = Field(alias="ownerUserId")
    document_kind: MaterialKind = Field(alias="documentKind")
    current_stage: ProcessingStage = Field(alias="currentStage")
    retry_count: int = Field(alias="retryCount")
    max_retries: int = Field(alias="maxRetries")
    parser_provider: str = Field(alias="parserProvider")
    embedding_provider: str = Field(alias="embeddingProvider")
    chunk_count: int = Field(alias="chunkCount")
    error_code: str | None = Field(default=None, alias="errorCode")
    error_message: str | None = Field(default=None, alias="errorMessage")
    created_at_ms: int = Field(alias="createdAtMs")
    updated_at_ms: int = Field(alias="updatedAtMs")
    queued_at_ms: int | None = Field(default=None, alias="queuedAtMs")
    started_at_ms: int | None = Field(default=None, alias="startedAtMs")
    completed_at_ms: int | None = Field(default=None, alias="completedAtMs")
    last_retry_at_ms: int | None = Field(default=None, alias="lastRetryAtMs")
    ready_for_ai: bool = Field(alias="readyForAi")


class ProcessingTaskEventResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    event_id: str = Field(alias="eventId")
    task_id: str = Field(alias="taskId")
    stage: ProcessingStage
    retry_count: int = Field(alias="retryCount")
    event_name: str = Field(alias="eventName")
    duration_ms: int | None = Field(default=None, alias="durationMs")
    error_code: str | None = Field(default=None, alias="errorCode")
    created_at_ms: int = Field(alias="createdAtMs")


class DocumentProcessingStatusResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    document_id: str = Field(alias="documentId")
    document_kind: MaterialKind = Field(alias="documentKind")
    latest_task: ProcessingTaskResponse | None = Field(default=None, alias="latestTask")
    events: list[ProcessingTaskEventResponse] = Field(default_factory=list)
    ready_for_ai: bool = Field(alias="readyForAi")


class RetryProcessingTaskRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    user_id: str = Field(min_length=1, alias="userId")
