from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.material_formats import MaterialKind
from app.ports.interview_session import ConversationRole, ConversationVisibility, InterviewSessionState, SessionContinueTarget, SessionUsageKind


class SessionDocumentSnapshotResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    document_id: str = Field(alias="documentId")
    document_kind: MaterialKind = Field(alias="documentKind")
    display_name: str = Field(alias="displayName")
    status: str
    document_version_id: str | None = Field(default=None, alias="documentVersionId")
    index_state: str | None = Field(default=None, alias="indexState")
    knowledge_collection_id: str | None = Field(default=None, alias="knowledgeCollectionId")
    summary: str | None = None
    active: bool


class SessionMaterialBindingResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    revision: int
    resume_document_id: str | None = Field(default=None, alias="resumeDocumentId")
    job_description_document_id: str | None = Field(default=None, alias="jobDescriptionDocumentId")
    knowledge_document_ids: list[str] = Field(default_factory=list, alias="knowledgeDocumentIds")
    bound_documents: list[SessionDocumentSnapshotResponse] = Field(default_factory=list, alias="boundDocuments")
    confirmed_at_ms: int | None = Field(default=None, alias="confirmedAtMs")


class SessionConfigSnapshotResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    model_config_ref: str = Field(alias="modelConfigRef")
    prompt_config_ref: str = Field(alias="promptConfigRef")
    retrieval_config_ref: str = Field(alias="retrievalConfigRef")
    version_tag: str = Field(alias="versionTag")
    captured_at_ms: int = Field(alias="capturedAtMs")


class SessionUsageTotalsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    prompt_tokens: int = Field(alias="promptTokens")
    completion_tokens: int = Field(alias="completionTokens")
    total_tokens: int = Field(alias="totalTokens")
    embedding_tokens: int = Field(alias="embeddingTokens")
    retrieval_tokens: int = Field(alias="retrievalTokens")
    record_count: int = Field(alias="recordCount")


class SessionIntegrationReferenceResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    name: str
    session_id: str = Field(alias="sessionId")
    details: dict[str, object] = Field(default_factory=dict)


class ConversationContextEntryResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    entry_id: str = Field(alias="entryId")
    role: ConversationRole
    source_kind: str = Field(alias="sourceKind")
    content: str
    visibility: ConversationVisibility
    ordering: int
    related_task_id: str | None = Field(default=None, alias="relatedTaskId")
    created_at_ms: int = Field(alias="createdAtMs")


class SessionUsageRecordResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    usage_id: str = Field(alias="usageId")
    usage_kind: SessionUsageKind = Field(alias="usageKind")
    prompt_tokens: int = Field(alias="promptTokens")
    completion_tokens: int = Field(alias="completionTokens")
    total_tokens: int = Field(alias="totalTokens")
    provider_name: str | None = Field(default=None, alias="providerName")
    model_name: str | None = Field(default=None, alias="modelName")
    related_task_id: str | None = Field(default=None, alias="relatedTaskId")
    created_at_ms: int = Field(alias="createdAtMs")


class InterviewSessionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    session_id: str = Field(alias="sessionId")
    owner_user_id: str = Field(alias="ownerUserId")
    title: str
    status: InterviewSessionState
    continue_target: SessionContinueTarget = Field(alias="continueTarget")
    material_binding: SessionMaterialBindingResponse = Field(alias="materialBinding")
    config_snapshot: SessionConfigSnapshotResponse = Field(alias="configSnapshot")
    usage_totals: SessionUsageTotalsResponse = Field(alias="usageTotals")
    integration_references: list[SessionIntegrationReferenceResponse] = Field(default_factory=list, alias="integrationReferences")
    restart_of_session_id: str | None = Field(default=None, alias="restartOfSessionId")
    started_at_ms: int | None = Field(default=None, alias="startedAtMs")
    ended_at_ms: int | None = Field(default=None, alias="endedAtMs")
    created_at_ms: int = Field(alias="createdAtMs")
    updated_at_ms: int = Field(alias="updatedAtMs")
    last_activity_at_ms: int = Field(alias="lastActivityAtMs")


class CreateInterviewSessionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    user_id: str = Field(min_length=1, alias="userId")
    title: str = Field(min_length=1, max_length=120)


class ListInterviewSessionsRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    user_id: str = Field(min_length=1, alias="userId")
    status: InterviewSessionState | None = None


class SessionCommandRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    user_id: str = Field(min_length=1, alias="userId")


class ConfirmSessionMaterialsRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    user_id: str = Field(min_length=1, alias="userId")
    resume_document_id: str | None = Field(default=None, alias="resumeDocumentId")
    job_description_document_id: str | None = Field(default=None, alias="jobDescriptionDocumentId")
    knowledge_document_ids: list[str] = Field(default_factory=list, alias="knowledgeDocumentIds")


class SessionContextAppendRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    user_id: str = Field(min_length=1, alias="userId")
    role: ConversationRole
    source_kind: str = Field(min_length=1, alias="sourceKind")
    content: str = Field(min_length=1)
    visibility: ConversationVisibility = "session"
    related_task_id: str | None = Field(default=None, alias="relatedTaskId")


class SessionContextWindowResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    session_id: str = Field(alias="sessionId")
    entries: list[ConversationContextEntryResponse] = Field(default_factory=list)
    total_count: int = Field(alias="totalCount")


class RecordSessionUsageRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    user_id: str = Field(min_length=1, alias="userId")
    usage_kind: SessionUsageKind = Field(alias="usageKind")
    prompt_tokens: int = Field(default=0, ge=0, alias="promptTokens")
    completion_tokens: int = Field(default=0, ge=0, alias="completionTokens")
    total_tokens: int = Field(default=0, ge=0, alias="totalTokens")
    provider_name: str | None = Field(default=None, alias="providerName")
    model_name: str | None = Field(default=None, alias="modelName")
    related_task_id: str | None = Field(default=None, alias="relatedTaskId")


class SessionUsageResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    session_id: str = Field(alias="sessionId")
    totals: SessionUsageTotalsResponse
    records: list[SessionUsageRecordResponse] = Field(default_factory=list)


class ContinueInterviewSessionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    target: Literal["preparing", "live", "history"]
    session: InterviewSessionResponse
