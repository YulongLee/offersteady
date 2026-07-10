from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

from app.material_formats import MaterialKind


InterviewSessionState = Literal["preparing", "live", "ended"]
SessionContinueTarget = Literal["preparing", "live", "history"]
ConversationRole = Literal["system", "interviewer", "candidate", "assistant", "manual-question", "screenshot", "event"]
ConversationVisibility = Literal["session", "ai", "review", "system-only"]
SessionUsageKind = Literal["prompt", "completion", "embedding", "retrieval", "total", "other"]


@dataclass(frozen=True)
class SessionBoundDocument:
    document_id: str
    document_kind: MaterialKind
    display_name: str
    status: str
    document_version_id: str | None = None
    index_state: str | None = None
    knowledge_collection_id: str | None = None
    summary: str | None = None
    active: bool = True


@dataclass(frozen=True)
class SessionMaterialBinding:
    session_id: str
    owner_user_id: str
    revision: int
    resume_document_id: str | None
    job_description_document_id: str | None
    knowledge_document_ids: list[str] = field(default_factory=list)
    bound_documents: list[SessionBoundDocument] = field(default_factory=list)
    confirmed_at_ms: int | None = None


@dataclass(frozen=True)
class SessionConfigSnapshot:
    model_config_ref: str
    prompt_config_ref: str
    retrieval_config_ref: str
    version_tag: str
    captured_at_ms: int


@dataclass(frozen=True)
class ConversationContextEntry:
    entry_id: str
    session_id: str
    owner_user_id: str
    role: ConversationRole
    source_kind: str
    content: str
    visibility: ConversationVisibility
    ordering: int
    related_task_id: str | None = None
    created_at_ms: int = 0


@dataclass(frozen=True)
class SessionUsageRecord:
    usage_id: str
    session_id: str
    owner_user_id: str
    usage_kind: SessionUsageKind
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    provider_name: str | None = None
    model_name: str | None = None
    related_task_id: str | None = None
    created_at_ms: int = 0


@dataclass(frozen=True)
class SessionUsageTotals:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    embedding_tokens: int = 0
    retrieval_tokens: int = 0
    record_count: int = 0


@dataclass(frozen=True)
class IntegrationReference:
    name: str
    session_id: str
    details: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class InterviewSessionRecord:
    session_id: str
    owner_user_id: str
    title: str
    status: InterviewSessionState
    continue_target: SessionContinueTarget
    material_binding: SessionMaterialBinding
    config_snapshot: SessionConfigSnapshot
    usage_totals: SessionUsageTotals
    integration_references: list[IntegrationReference] = field(default_factory=list)
    restart_of_session_id: str | None = None
    started_at_ms: int | None = None
    ended_at_ms: int | None = None
    created_at_ms: int = 0
    updated_at_ms: int = 0
    last_activity_at_ms: int = 0


class InterviewSessionRepository(Protocol):
    def save_session(self, session: InterviewSessionRecord) -> InterviewSessionRecord: ...

    def get_session(self, session_id: str) -> InterviewSessionRecord | None: ...

    def list_sessions_for_user(self, *, user_id: str, status: InterviewSessionState | None = None) -> list[InterviewSessionRecord]: ...

    def delete_session(self, *, user_id: str, session_id: str) -> bool: ...

    def append_context_entry(self, entry: ConversationContextEntry) -> ConversationContextEntry: ...

    def list_context_entries(self, *, session_id: str) -> list[ConversationContextEntry]: ...

    def save_usage_record(self, record: SessionUsageRecord) -> SessionUsageRecord: ...

    def list_usage_records(self, *, session_id: str) -> list[SessionUsageRecord]: ...
