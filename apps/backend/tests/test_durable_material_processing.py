from __future__ import annotations

from dataclasses import replace
import os
from time import time
from uuid import uuid4

import httpx
import pytest

from app.adapters.oss_storage import AliyunOssStorageAdapter
from app.core.config import Settings
from app.core.logging import configure_logging
from app.ports.commercial_hardening import CommercialJobRecord
from app.ports.document_processing import ProcessingTaskEvent, ProcessingTaskRecord
from app.ports.document_repository import DocumentRecord
from app.ports.storage import UploadIntentReservation
from app.services.commercial_hardening import InMemoryCommercialHardeningRepository, PostgresCommercialHardeningRepository
from app.services.commercial_worker import CommercialWorkerService
from app.services.document_parser import DocumentParserService, ProcessingTaskParserStatusReporter
from app.services.document_processing import DocumentProcessingService
from app.services.document_processing_adapters import (
    ChunkMetadataBuilderAdapter,
    InMemoryPgvectorStore,
    MarkdownCleanerAdapter,
    MarkdownChunkSplitterAdapter,
    MarkdownNormalizerAdapter,
    MineruDocumentParserAdapter,
    SyntheticEmbeddingAdapter,
)
from app.services.document_processing_repository import InMemoryProcessingTaskRepository, PostgresProcessingTaskRepository
from app.services.document_repository import InMemoryDocumentRepository
from app.services.embedding_pipeline import EmbeddingPipelineService, ProcessingTaskEmbeddingStatusReporter
from app.services.upload_intent_repository import InMemoryUploadIntentRepository, PostgresUploadIntentRepository


DATABASE_URL = os.getenv("OFFERSTEADY_TEST_DATABASE_URL")


def _now_ms() -> int:
    return int(time() * 1000)


def _service(
    *,
    settings: Settings,
    storage: AliyunOssStorageAdapter,
    documents: InMemoryDocumentRepository,
    tasks: InMemoryProcessingTaskRepository,
    jobs: InMemoryCommercialHardeningRepository,
) -> DocumentProcessingService:
    logger = configure_logging(settings)
    parser = DocumentParserService(
        settings=settings,
        logger=logger,
        object_storage=storage,
        binary_parser=MineruDocumentParserAdapter(settings),
        markdown_normalizer=MarkdownNormalizerAdapter(),
        status_reporter=ProcessingTaskParserStatusReporter(settings=settings, logger=logger, task_repository=tasks),
        commercial_repository=jobs,
    )
    embedding = EmbeddingPipelineService(
        settings=settings,
        logger=logger,
        cleaner=MarkdownCleanerAdapter(),
        splitter=MarkdownChunkSplitterAdapter(),
        metadata_builder=ChunkMetadataBuilderAdapter(),
        embedding=SyntheticEmbeddingAdapter(settings),
        vector_store=InMemoryPgvectorStore(),
        status_reporter=ProcessingTaskEmbeddingStatusReporter(settings=settings, logger=logger, task_repository=tasks),
        artifact_storage=storage,
        commercial_repository=jobs,
    )
    return DocumentProcessingService(
        settings=settings,
        logger=logger,
        document_repository=documents,
        task_repository=tasks,
        parser_service=parser,
        embedding_pipeline=embedding,
        commercial_repository=jobs,
    )


def test_upload_intent_survives_storage_adapter_recreation() -> None:
    settings = Settings(_env_file=None, environment="test")
    repository = InMemoryUploadIntentRepository()
    first = AliyunOssStorageAdapter(settings, intent_repository=repository)
    intent = first.create_upload_intent(
        user_id="persistent-upload-user",
        material_kind="resume",
        filename="resume.md",
        file_kind="md",
        content_type="text/markdown",
    )

    restarted = AliyunOssStorageAdapter(settings, intent_repository=repository)
    confirmed = restarted.confirm_uploaded_object(
        user_id="persistent-upload-user",
        intent_id=intent.intent_id,
        object_key=intent.object_key,
        content_type=intent.content_type,
        size_bytes=128,
    )

    assert confirmed.document_id == intent.document_id
    assert confirmed.document_version_id == intent.document_version_id
    assert confirmed.object_key == intent.object_key


def test_external_worker_completes_durable_task_after_service_recreation() -> None:
    settings = Settings(
        _env_file=None,
        environment="test",
        document_processing_inline_worker_enabled=False,
    )
    storage = AliyunOssStorageAdapter(settings)
    documents = InMemoryDocumentRepository()
    tasks = InMemoryProcessingTaskRepository()
    jobs = InMemoryCommercialHardeningRepository()
    object_key = "materials/test/durable/document/version/original/resume.md"
    storage.uploaded_objects[object_key] = b"# Resume\n\n- Built a reliable document pipeline."
    now_ms = _now_ms()
    document = documents.save(
        DocumentRecord(
            document_id="document-durable",
            owner_user_id="durable-user",
            document_kind="resume",
            display_name="resume.md",
            file_kind="md",
            content_type="text/markdown",
            size_bytes=48,
            object_key=object_key,
            status="processing_requested",
            knowledge_collection_id=None,
            processing_requested_at_ms=now_ms,
            deleted_at_ms=None,
            created_at_ms=now_ms,
            updated_at_ms=now_ms,
            summary="waiting",
            document_version_id="version-durable",
            index_state="queued",
        )
    )
    api_service = _service(settings=settings, storage=storage, documents=documents, tasks=tasks, jobs=jobs)
    queued = api_service.submit_document(document)

    assert queued.current_stage == "QUEUED"
    assert api_service._worker_started is False
    assert jobs.jobs[f"processing-{queued.task_id}"].status == "queued"

    restarted_service = _service(settings=settings, storage=storage, documents=documents, tasks=tasks, jobs=jobs)
    worker = CommercialWorkerService(
        repository=jobs,
        storage=storage,
        logger=configure_logging(settings),
        processing_service=restarted_service,
        lease_seconds=900,
    )
    result = worker.run_once()

    completed = tasks.get_task(queued.task_id)
    assert result.processed == 1
    assert result.succeeded == 1
    assert completed is not None
    assert completed.current_stage == "COMPLETED"
    assert documents.get_by_id(document.document_id).status == "ready"  # type: ignore[union-attr]
    assert jobs.jobs[f"processing-{queued.task_id}"].status == "succeeded"


def test_stale_running_job_is_recovered_and_retryable() -> None:
    jobs = InMemoryCommercialHardeningRepository()
    now_ms = _now_ms()
    job = CommercialJobRecord(
        job_id="processing-stale",
        owner_user_id="stale-user",
        job_kind="processing",
        status="running",
        stage="PARSING",
        related_task_id="task-stale",
        retry_count=0,
        max_retries=2,
        created_at_ms=now_ms - 2_000_000,
        updated_at_ms=now_ms - 2_000_000,
        scheduled_after_ms=0,
    )
    jobs.enqueue_processing_job(job)

    recovered = jobs.recover_stale_jobs(
        job_kind="processing",
        now_ms=now_ms,
        stale_before_ms=now_ms - 900_000,
    )

    assert recovered == 1
    assert jobs.jobs[job.job_id] == replace(
        job,
        status="retrying",
        retry_count=1,
        safe_error_code="worker_lease_expired",
        scheduled_after_ms=now_ms,
        updated_at_ms=now_ms,
        completed_at_ms=None,
    )


def test_worker_reconstructs_legacy_task_from_durable_job() -> None:
    settings = Settings(_env_file=None, environment="test", document_processing_inline_worker_enabled=False)
    storage = AliyunOssStorageAdapter(settings)
    documents = InMemoryDocumentRepository()
    tasks = InMemoryProcessingTaskRepository()
    jobs = InMemoryCommercialHardeningRepository()
    object_key = "materials/test/recovered/document/version/original/jd.md"
    storage.uploaded_objects[object_key] = b"# Job description\n\nBuild reliable services."
    now_ms = _now_ms()
    document = documents.save(
        DocumentRecord(
            document_id="document-recovered",
            owner_user_id="recovered-user",
            document_kind="job_description",
            display_name="jd.md",
            file_kind="md",
            content_type="text/markdown",
            size_bytes=44,
            object_key=object_key,
            status="processing_requested",
            knowledge_collection_id=None,
            processing_requested_at_ms=now_ms,
            deleted_at_ms=None,
            created_at_ms=now_ms,
            updated_at_ms=now_ms,
            summary="waiting",
            document_version_id="version-recovered",
            index_state="queued",
        )
    )
    jobs.enqueue_processing_job(
        CommercialJobRecord(
            job_id="processing-legacy-shadow",
            owner_user_id=document.owner_user_id,
            job_kind="processing",
            status="queued",
            stage="QUEUED",
            document_id=document.document_id,
            document_version_id=document.document_version_id,
            related_task_id="task-legacy-shadow",
            retry_count=0,
            max_retries=2,
            payload={"parserProvider": "mineru", "embeddingProvider": "synthetic-embedding"},
            created_at_ms=now_ms,
            updated_at_ms=now_ms,
            scheduled_after_ms=now_ms,
        )
    )
    service = _service(settings=settings, storage=storage, documents=documents, tasks=tasks, jobs=jobs)
    worker = CommercialWorkerService(
        repository=jobs,
        storage=storage,
        logger=configure_logging(settings),
        processing_service=service,
    )

    result = worker.run_once()

    recovered = tasks.get_task("task-legacy-shadow")
    assert result.succeeded == 1
    assert recovered is not None
    assert recovered.current_stage == "COMPLETED"
    assert any(event.event_name == "task_recovered_from_durable_job" for event in tasks.list_events_for_task(recovered.task_id))
    assert jobs.jobs["processing-legacy-shadow"].status == "succeeded"


def test_mineru_timeout_is_reduced_to_safe_actionable_code(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(
        _env_file=None,
        environment="test",
        integration_mineru_base_url="https://mineru.invalid",
    )
    adapter = MineruDocumentParserAdapter(settings)
    monkeypatch.setenv("OFFERSTEADY_TEST_USE_REMOTE_MINERU", "1")
    monkeypatch.setattr(
        adapter,
        "_parse_with_mineru",
        lambda **_kwargs: (_ for _ in ()).throw(httpx.ReadTimeout("synthetic timeout")),
    )

    with pytest.raises(RuntimeError, match="provider_timeout"):
        adapter.parse(
            context=type(
                "Context",
                (),
                {
                    "file_kind": "pdf",
                    "object_key": "materials/test/document.pdf",
                    "display_name": "document.pdf",
                    "content_type": "application/pdf",
                    "document_kind": "resume",
                },
            )(),
            payload=b"%PDF-1.7",
        )


@pytest.mark.skipif(not DATABASE_URL, reason="OFFERSTEADY_TEST_DATABASE_URL is not configured")
def test_postgres_upload_and_processing_state_survive_repository_recreation() -> None:
    settings = Settings(_env_file=None, environment="test", database_url=DATABASE_URL)
    suffix = uuid4().hex
    now_ms = _now_ms()
    intent = UploadIntentReservation(
        intent_id=f"intent-{suffix}",
        user_id=f"user-{suffix}",
        material_kind="resume",
        filename="resume.pdf",
        file_kind="pdf",
        content_type="application/pdf",
        object_key=f"materials/test/{suffix}/resume.pdf",
        upload_url="https://oss.example.test",
        upload_fields={"key": f"materials/test/{suffix}/resume.pdf", "Signature": "synthetic"},
        issued_at_ms=now_ms,
        expires_at_ms=now_ms + 900_000,
        object_id=f"object-{suffix}",
        document_id=f"document-{suffix}",
        document_version_id=f"version-{suffix}",
    )
    PostgresUploadIntentRepository(settings).save(intent)
    assert PostgresUploadIntentRepository(settings).get(intent.intent_id) == intent

    task = ProcessingTaskRecord(
        task_id=f"task-{suffix}",
        document_id=intent.document_id or f"document-{suffix}",
        owner_user_id=intent.user_id,
        document_kind="resume",
        current_stage="QUEUED",
        retry_count=0,
        max_retries=2,
        parser_provider="mineru",
        embedding_provider="text-embedding-v3",
        created_at_ms=now_ms,
        updated_at_ms=now_ms,
        queued_at_ms=now_ms,
    )
    first_tasks = PostgresProcessingTaskRepository(settings)
    first_tasks.save_task(task)
    event = ProcessingTaskEvent(
        event_id=f"event-{suffix}",
        task_id=task.task_id,
        stage="QUEUED",
        retry_count=0,
        event_name="task_queued",
        duration_ms=None,
        error_code=None,
        created_at_ms=now_ms,
    )
    first_tasks.save_event(event)
    restarted_tasks = PostgresProcessingTaskRepository(settings)
    assert restarted_tasks.get_task(task.task_id) == task
    assert restarted_tasks.list_events_for_task(task.task_id) == [event]

    jobs = PostgresCommercialHardeningRepository(settings)
    job = CommercialJobRecord(
        job_id=f"processing-{task.task_id}",
        owner_user_id=task.owner_user_id,
        job_kind="processing",
        status="queued",
        stage="QUEUED",
        document_id=task.document_id,
        document_version_id=intent.document_version_id,
        related_task_id=task.task_id,
        retry_count=0,
        max_retries=2,
        created_at_ms=now_ms,
        updated_at_ms=now_ms,
        scheduled_after_ms=now_ms,
    )
    jobs.enqueue_processing_job(job)
    claimed = PostgresCommercialHardeningRepository(settings).claim_next_job(job_kind="processing", now_ms=now_ms + 1)
    assert claimed is not None
    assert claimed.job_id == job.job_id
    assert claimed.status == "running"
