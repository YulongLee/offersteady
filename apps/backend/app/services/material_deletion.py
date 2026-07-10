from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from uuid import uuid4

from app.core.config import Settings
from app.ports.document_repository import DocumentRecord
from app.ports.storage import FileStoragePort
from app.services.material_object_keys import MaterialObjectKeyFactory


def _now_ms() -> int:
    return int(time() * 1000)


@dataclass(frozen=True)
class MaterialDeletionJob:
    deletion_job_id: str
    owner_user_id: str
    document_id: str
    document_version_id: str | None
    object_keys: tuple[str, ...]
    vector_filter: dict[str, str]
    status: str
    requested_at_ms: int
    scheduled_after_ms: int
    completed_at_ms: int | None = None
    error_message: str | None = None


@dataclass
class InMemoryMaterialDeletionScheduler:
    settings: Settings
    storage: FileStoragePort
    jobs: dict[str, MaterialDeletionJob] = field(default_factory=dict)

    def schedule_document_deletion(self, *, document: DocumentRecord, deleted_at_ms: int) -> MaterialDeletionJob:
        object_keys = [document.object_key]
        if document.document_version_id:
            key_factory = MaterialObjectKeyFactory(self.settings)
            object_keys.extend([
                key_factory.processed_artifact_key(
                    owner_user_id=document.owner_user_id,
                    document_kind=document.document_kind,
                    document_id=document.document_id,
                    document_version_id=document.document_version_id,
                    artifact_kind="normalized_markdown",
                ),
                key_factory.processed_artifact_key(
                    owner_user_id=document.owner_user_id,
                    document_kind=document.document_kind,
                    document_id=document.document_id,
                    document_version_id=document.document_version_id,
                    artifact_kind="chunk_manifest",
                ),
                key_factory.deletion_marker_key(
                    owner_user_id=document.owner_user_id,
                    document_kind=document.document_kind,
                    document_id=document.document_id,
                    document_version_id=document.document_version_id,
                    deleted_at_ms=deleted_at_ms,
                ),
            ])
        vector_filter = {
            "owner_user_id": document.owner_user_id,
            "document_id": document.document_id,
        }
        if document.document_version_id:
            vector_filter["document_version_id"] = document.document_version_id
        scheduled_after_ms = deleted_at_ms + self.settings.material_deletion_grace_seconds * 1000
        job = MaterialDeletionJob(
            deletion_job_id=f"deletion-{uuid4().hex}",
            owner_user_id=document.owner_user_id,
            document_id=document.document_id,
            document_version_id=document.document_version_id,
            object_keys=tuple(dict.fromkeys(object_keys)),
            vector_filter=vector_filter,
            status="queued",
            requested_at_ms=deleted_at_ms,
            scheduled_after_ms=scheduled_after_ms,
        )
        self.jobs[job.deletion_job_id] = job
        return job

    def run_due_jobs(self, *, now_ms: int | None = None) -> list[MaterialDeletionJob]:
        current_ms = now_ms or _now_ms()
        completed: list[MaterialDeletionJob] = []
        for job in list(self.jobs.values()):
            if job.status != "queued" or job.scheduled_after_ms > current_ms:
                continue
            try:
                for object_key in job.object_keys:
                    self.storage.delete_object(object_key=object_key)
                settled = MaterialDeletionJob(
                    **{**job.__dict__, "status": "succeeded", "completed_at_ms": current_ms}
                )
            except Exception as exc:  # pragma: no cover - defensive boundary for future OSS adapter failures.
                settled = MaterialDeletionJob(
                    **{**job.__dict__, "status": "failed", "completed_at_ms": current_ms, "error_message": str(exc)}
                )
            self.jobs[settled.deletion_job_id] = settled
            completed.append(settled)
        return completed
