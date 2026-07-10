from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol


MaterialArtifactKind = Literal["original", "normalized_markdown", "chunk_manifest", "deletion_marker", "inline_source"]
MaterialArtifactSyncStatus = Literal["synced", "processing", "missing", "failed", "deleted"]
CommercialJobKind = Literal["processing", "deletion", "reconcile"]
CommercialJobStatus = Literal["queued", "running", "retrying", "succeeded", "failed", "cancelled"]
AiOperationKind = Literal["parser", "vision", "embedding", "rerank", "chat"]


@dataclass(frozen=True)
class MaterialArtifactRecord:
    artifact_id: str
    owner_user_id: str
    document_id: str
    document_version_id: str
    document_kind: str
    artifact_kind: MaterialArtifactKind
    object_key: str
    sync_status: MaterialArtifactSyncStatus
    required: bool
    content_type: str | None = None
    size_bytes: int | None = None
    sha256: str | None = None
    verified_at_ms: int | None = None
    created_at_ms: int = 0
    updated_at_ms: int = 0
    safe_error_code: str | None = None


@dataclass(frozen=True)
class CommercialJobRecord:
    job_id: str
    owner_user_id: str
    job_kind: CommercialJobKind
    status: CommercialJobStatus
    stage: str
    document_id: str | None = None
    document_version_id: str | None = None
    related_task_id: str | None = None
    retry_count: int = 0
    max_retries: int = 3
    safe_error_code: str | None = None
    payload: dict[str, object] = field(default_factory=dict)
    created_at_ms: int = 0
    updated_at_ms: int = 0
    scheduled_after_ms: int = 0
    started_at_ms: int | None = None
    completed_at_ms: int | None = None


@dataclass(frozen=True)
class AiUsageRecord:
    usage_id: str
    owner_user_id: str
    operation_kind: AiOperationKind
    provider: str
    model: str
    status: Literal["succeeded", "failed"]
    related_job_id: str | None = None
    related_task_id: str | None = None
    session_id: str | None = None
    document_id: str | None = None
    document_version_id: str | None = None
    trace_id: str | None = None
    input_units: int | None = None
    output_units: int | None = None
    total_units: int | None = None
    point_cost: int | None = None
    duration_ms: int | None = None
    safe_error_code: str | None = None
    created_at_ms: int = 0


@dataclass(frozen=True)
class RagRetrievalTraceRecord:
    trace_id: str
    owner_user_id: str
    session_id: str | None
    query_hash: str
    strategy: str
    filter_document_ids: tuple[str, ...]
    filter_document_version_ids: tuple[str, ...]
    candidate_count: int
    reranked_count: int
    returned_count: int
    returned_source_ids: tuple[str, ...]
    safe_error_code: str | None = None
    created_at_ms: int = 0


class CommercialHardeningRepository(Protocol):
    def save_artifact(self, artifact: MaterialArtifactRecord) -> MaterialArtifactRecord: ...
    def list_artifacts_for_version(self, *, owner_user_id: str, document_version_id: str) -> list[MaterialArtifactRecord]: ...
    def enqueue_processing_job(self, job: CommercialJobRecord) -> CommercialJobRecord: ...
    def enqueue_deletion_job(self, job: CommercialJobRecord) -> CommercialJobRecord: ...
    def claim_next_job(self, *, job_kind: CommercialJobKind, now_ms: int) -> CommercialJobRecord | None: ...
    def mark_job_running(self, *, job_id: str, now_ms: int) -> CommercialJobRecord | None: ...
    def mark_job_succeeded(self, *, job_id: str, now_ms: int, stage: str | None = None) -> CommercialJobRecord | None: ...
    def mark_job_failed(self, *, job_id: str, now_ms: int, safe_error_code: str, retryable: bool) -> CommercialJobRecord | None: ...
    def complete_processing_job_for_task(self, *, related_task_id: str, now_ms: int, stage: str = "COMPLETED") -> CommercialJobRecord | None: ...
    def fail_processing_job_for_task(self, *, related_task_id: str, now_ms: int, safe_error_code: str, retryable: bool) -> CommercialJobRecord | None: ...
    def record_ai_usage(self, usage: AiUsageRecord) -> AiUsageRecord: ...
    def record_rag_trace(self, trace: RagRetrievalTraceRecord) -> RagRetrievalTraceRecord: ...
