from __future__ import annotations

from app.adapters.oss_storage import AliyunOssStorageAdapter
from app.core.config import Settings
from app.ports.document_repository import DocumentRecord
from app.services.material_deletion import InMemoryMaterialDeletionScheduler


def test_material_deletion_scheduler_records_raw_processed_marker_and_vector_filter() -> None:
    settings = Settings(app_name="test", environment="test", material_deletion_grace_seconds=60)
    storage = AliyunOssStorageAdapter(settings)
    scheduler = InMemoryMaterialDeletionScheduler(settings=settings, storage=storage)
    record = DocumentRecord(
        document_id="document-1",
        owner_user_id="user-1",
        document_kind="resume",
        display_name="Resume",
        file_kind="pdf",
        content_type="application/pdf",
        size_bytes=123,
        object_key="materials/test/users/hash/documents/resume/document-1/versions/version-1/original/object-1.pdf",
        status="deleted",
        knowledge_collection_id=None,
        processing_requested_at_ms=1,
        deleted_at_ms=1000,
        created_at_ms=1,
        updated_at_ms=1000,
        summary=None,
        object_id="object-1",
        document_version_id="version-1",
        version=1,
        content_fingerprint="etag",
        original_filename="resume.pdf",
        index_state="deleted",
    )

    job = scheduler.schedule_document_deletion(document=record, deleted_at_ms=1000)

    assert job.status == "queued"
    assert job.scheduled_after_ms == 61000
    assert record.object_key in job.object_keys
    assert any(key.endswith("/processed/normalized.md") for key in job.object_keys)
    assert any(key.endswith("/processed/chunks.jsonl") for key in job.object_keys)
    assert any(key.endswith("/deleted/1000.json") for key in job.object_keys)
    assert job.vector_filter == {
        "owner_user_id": "user-1",
        "document_id": "document-1",
        "document_version_id": "version-1",
    }
