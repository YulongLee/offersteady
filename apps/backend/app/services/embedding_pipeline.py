from __future__ import annotations

import logging
import json
from dataclasses import dataclass, replace
from time import time
from uuid import uuid4

from app.core.config import Settings
from app.core.logging import log_event
from app.ports.commercial_hardening import AiUsageRecord, CommercialHardeningRepository, MaterialArtifactRecord
from app.ports.document_processing import (
    ChunkMetadataBuilderPort,
    ChunkSplitterPort,
    ChunkingProfile,
    CleanedMarkdown,
    EmbeddedChunk,
    EmbeddingFailure,
    EmbeddingPort,
    EmbeddingStatusPort,
    ParsedDocument,
    ProcessingTaskEvent,
    ProcessingTaskRecord,
    ProcessingTaskRepository,
    VectorStorePort,
)
from app.ports.document_repository import DocumentRecord
from app.ports.storage import FileStoragePort
from app.services.material_object_keys import MaterialObjectKeyFactory
from app.services.commercial_hardening import artifact_id, usage_id


def _now_ms() -> int:
    return int(time() * 1000)


class EmbeddingExecutionError(Exception):
    def __init__(self, *, task: ProcessingTaskRecord, failure: EmbeddingFailure):
        self.task = task
        self.failure = failure
        super().__init__(failure.message_safe_for_log)


@dataclass(frozen=True)
class EmbeddingPipelineResult:
    task: ProcessingTaskRecord
    chunk_count: int
    rebuild_version: int
    embedding_model: str


class EmbeddingPipelineService:
    def __init__(
        self,
        *,
        settings: Settings,
        logger: logging.Logger,
        cleaner,
        splitter: ChunkSplitterPort,
        metadata_builder: ChunkMetadataBuilderPort,
        embedding: EmbeddingPort,
        vector_store: VectorStorePort,
        status_reporter: EmbeddingStatusPort,
        artifact_storage: FileStoragePort | None = None,
        commercial_repository: CommercialHardeningRepository | None = None,
    ) -> None:
        self.settings = settings
        self.logger = logger
        self.cleaner = cleaner
        self.splitter = splitter
        self.metadata_builder = metadata_builder
        self.embedding = embedding
        self.vector_store = vector_store
        self.status_reporter = status_reporter
        self.artifact_storage = artifact_storage
        self.commercial_repository = commercial_repository
        self.chunk_profiles = {
            "resume": ChunkingProfile(
                profile_name="resume-default",
                chunk_size=settings.embedding_pipeline_resume_chunk_size,
                overlap=settings.embedding_pipeline_resume_chunk_overlap,
                split_priority="paragraph",
            ),
            "job_description": ChunkingProfile(
                profile_name="jd-default",
                chunk_size=settings.embedding_pipeline_job_description_chunk_size,
                overlap=settings.embedding_pipeline_job_description_chunk_overlap,
                split_priority="paragraph",
            ),
            "knowledge": ChunkingProfile(
                profile_name="knowledge-default",
                chunk_size=settings.embedding_pipeline_knowledge_chunk_size,
                overlap=settings.embedding_pipeline_knowledge_chunk_overlap,
                split_priority="heading",
            ),
        }

    def process_markdown(self, *, task: ProcessingTaskRecord, document: DocumentRecord, parsed: ParsedDocument) -> EmbeddingPipelineResult:
        started_at = _now_ms()
        try:
            cleaned = self._clean_markdown(markdown=parsed.markdown, document_kind=document.document_kind)
            profile = self._profile_for(document.document_kind)
            current_task = self.status_reporter.mark_chunking_started(task, profile=profile)
            chunks = self.splitter.split(markdown=cleaned.markdown, document_kind=document.document_kind, profile=profile)
            if not chunks:
                raise EmbeddingExecutionError(
                    task=current_task,
                    failure=EmbeddingFailure(
                        error_code="no_text_chunks",
                        error_type="permanent",
                        retryable=False,
                        provider_name="chunk-splitter",
                        message_safe_for_log="文档未提取到可建立索引的文本片段。",
                    ),
                )
            rebuild_version = self.vector_store.next_rebuild_version(document_id=document.document_id)
            enriched_chunks = self.metadata_builder.build(
                document_id=document.document_id,
                document_kind=document.document_kind,
                profile=profile,
                parser_metadata={
                    **parsed.metadata,
                    **cleaned.metadata,
                    "ownerUserId": document.owner_user_id,
                    "documentVersionId": document.document_version_id or "",
                    "documentVersion": str(document.version or 1),
                    "contentFingerprint": document.content_fingerprint or "",
                    "knowledgeCollectionId": document.knowledge_collection_id or "",
                    "indexState": document.index_state or "queued",
                },
                chunks=chunks,
                rebuild_version=rebuild_version,
            )
            self._persist_chunk_manifest(document=document, chunks=enriched_chunks, rebuild_version=rebuild_version)
            runtime_embedding_model = (
                self.settings.embedding_model
                if self.settings.embedding_base_url and self.settings.embedding_api_key
                else self.settings.document_processing_embedding_provider
            )
            current_task = self.status_reporter.mark_embedding_started(
                current_task,
                chunk_count=len(enriched_chunks),
                embedding_model=runtime_embedding_model,
            )
            vectors = self.embedding.embed(
                chunks=enriched_chunks,
                document_kind=document.document_kind,
                embedding_model=runtime_embedding_model,
                batch_size=self.settings.embedding_pipeline_batch_size,
            )
            current_task = self.status_reporter.mark_vector_writing_started(
                current_task,
                chunk_count=len(vectors),
                rebuild_version=rebuild_version,
            )
            stored_count = self.vector_store.upsert_document_chunks(
                document_id=document.document_id,
                document_kind=document.document_kind,
                chunks=vectors,
                embedding_model=runtime_embedding_model,
                rebuild_version=rebuild_version,
            )
            self._record_embedding_usage(
                task=current_task,
                document=document,
                embedding_model=runtime_embedding_model,
                chunk_count=stored_count,
                status="succeeded",
                duration_ms=_now_ms() - started_at,
            )
            return EmbeddingPipelineResult(
                task=replace(
                    current_task,
                    chunk_count=stored_count,
                    embedding_provider=runtime_embedding_model,
                    updated_at_ms=_now_ms(),
                ),
                chunk_count=stored_count,
                rebuild_version=rebuild_version,
                embedding_model=runtime_embedding_model,
            )
        except EmbeddingExecutionError:
            raise
        except Exception as exc:
            failure = EmbeddingFailure(
                error_code=exc.__class__.__name__,
                error_type="recoverable",
                retryable=True,
                provider_name=self.settings.document_processing_embedding_provider,
                message_safe_for_log="向量化阶段发生未预期错误。",
            )
            failed_task = self.status_reporter.mark_embedding_failed(task, failure, duration_ms=_now_ms() - started_at)
            self._record_embedding_usage(
                task=failed_task,
                document=document,
                embedding_model=failure.provider_name,
                chunk_count=0,
                status="failed",
                duration_ms=_now_ms() - started_at,
                safe_error_code=failure.error_code,
            )
            raise EmbeddingExecutionError(task=failed_task, failure=failure) from exc

    def rebuild_document_vectors(self, *, task: ProcessingTaskRecord, document: DocumentRecord, parsed: ParsedDocument) -> EmbeddingPipelineResult:
        return self.process_markdown(task=task, document=document, parsed=parsed)

    def _clean_markdown(self, *, markdown: str, document_kind: str) -> CleanedMarkdown:
        return self.cleaner.clean(markdown=markdown, document_kind=document_kind)

    def _profile_for(self, document_kind: str) -> ChunkingProfile:
        return self.chunk_profiles[document_kind]

    def _persist_chunk_manifest(self, *, document: DocumentRecord, chunks, rebuild_version: int) -> None:
        if self.artifact_storage is None or not document.document_version_id:
            return
        manifest_key = MaterialObjectKeyFactory(self.settings).processed_artifact_key(
            owner_user_id=document.owner_user_id,
            document_kind=document.document_kind,
            document_id=document.document_id,
            document_version_id=document.document_version_id,
            artifact_kind="chunk_manifest",
        )
        lines = [
            json.dumps(
                {
                    "chunkId": chunk.chunk_id,
                    "chunkIndex": chunk.index,
                    "characterCount": len(chunk.content),
                    "metadata": chunk.metadata,
                    "rebuildVersion": rebuild_version,
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
            for chunk in chunks
        ]
        self.artifact_storage.save_object_bytes(
            object_key=manifest_key,
            payload=("\n".join(lines) + ("\n" if lines else "")).encode("utf-8"),
            content_type="application/x-ndjson; charset=utf-8",
        )
        self._record_chunk_manifest_artifact(document=document, object_key=manifest_key, size_bytes=len("\n".join(lines).encode("utf-8")))

    def _record_chunk_manifest_artifact(self, *, document: DocumentRecord, object_key: str, size_bytes: int) -> None:
        if self.commercial_repository is None or not document.document_version_id:
            return
        now = _now_ms()
        self.commercial_repository.save_artifact(
            MaterialArtifactRecord(
                artifact_id=artifact_id(),
                owner_user_id=document.owner_user_id,
                document_id=document.document_id,
                document_version_id=document.document_version_id,
                document_kind=document.document_kind,
                artifact_kind="chunk_manifest",
                object_key=object_key,
                sync_status="synced",
                required=document.document_kind == "knowledge",
                content_type="application/x-ndjson; charset=utf-8",
                size_bytes=size_bytes,
                verified_at_ms=now,
                created_at_ms=now,
                updated_at_ms=now,
            )
        )

    def _record_embedding_usage(
        self,
        *,
        task: ProcessingTaskRecord,
        document: DocumentRecord,
        embedding_model: str,
        chunk_count: int,
        status: str,
        duration_ms: int,
        safe_error_code: str | None = None,
    ) -> None:
        if self.commercial_repository is None:
            return
        self.commercial_repository.record_ai_usage(
            AiUsageRecord(
                usage_id=usage_id(),
                owner_user_id=document.owner_user_id,
                operation_kind="embedding",
                provider=self.settings.document_processing_embedding_provider,
                model=embedding_model,
                status=status,  # type: ignore[arg-type]
                related_task_id=task.task_id,
                document_id=document.document_id,
                document_version_id=document.document_version_id,
                input_units=chunk_count,
                total_units=chunk_count,
                duration_ms=duration_ms,
                safe_error_code=safe_error_code,
                created_at_ms=_now_ms(),
            )
        )


class ProcessingTaskEmbeddingStatusReporter(EmbeddingStatusPort):
    def __init__(self, *, settings: Settings, logger: logging.Logger, task_repository: ProcessingTaskRepository) -> None:
        self.settings = settings
        self.logger = logger
        self.task_repository = task_repository

    def mark_chunking_started(self, task: ProcessingTaskRecord, *, profile: ChunkingProfile) -> ProcessingTaskRecord:
        saved = self.task_repository.save_task(replace(task, current_stage="CHUNKING", updated_at_ms=_now_ms()))
        self._record(saved, action="embedding_chunking_started", profile_name=profile.profile_name)
        return saved

    def mark_embedding_started(self, task: ProcessingTaskRecord, *, chunk_count: int, embedding_model: str) -> ProcessingTaskRecord:
        saved = self.task_repository.save_task(
            replace(task, current_stage="EMBEDDING", updated_at_ms=_now_ms(), chunk_count=chunk_count, embedding_provider=embedding_model)
        )
        self._record(saved, action="embedding_started", chunk_count=chunk_count, embedding_model=embedding_model)
        return saved

    def mark_vector_writing_started(self, task: ProcessingTaskRecord, *, chunk_count: int, rebuild_version: int) -> ProcessingTaskRecord:
        saved = self.task_repository.save_task(
            replace(task, current_stage="VECTOR_WRITING", updated_at_ms=_now_ms(), chunk_count=chunk_count)
        )
        self._record(saved, action="vector_writing_started", chunk_count=chunk_count, rebuild_version=rebuild_version)
        return saved

    def mark_embedding_failed(self, task: ProcessingTaskRecord, failure: EmbeddingFailure, *, duration_ms: int) -> ProcessingTaskRecord:
        saved = self.task_repository.save_task(
            replace(
                task,
                updated_at_ms=_now_ms(),
                error_code=failure.error_code,
                error_message=failure.message_safe_for_log,
                embedding_provider=failure.provider_name,
            )
        )
        self._record(saved, action="embedding_failed", duration_ms=duration_ms, error_code=failure.error_code)
        return saved

    def _record(
        self,
        task: ProcessingTaskRecord,
        *,
        action: str,
        duration_ms: int | None = None,
        error_code: str | None = None,
        chunk_count: int | None = None,
        embedding_model: str | None = None,
        rebuild_version: int | None = None,
        profile_name: str | None = None,
    ) -> None:
        self.task_repository.save_event(
            ProcessingTaskEvent(
                event_id=f"event-{uuid4().hex}",
                task_id=task.task_id,
                stage=task.current_stage,
                retry_count=task.retry_count,
                event_name=action,
                duration_ms=duration_ms,
                error_code=error_code,
                created_at_ms=_now_ms(),
            )
        )
        log_event(
            self.logger,
            logging.INFO if error_code is None else logging.WARNING,
            settings=self.settings,
            event="embedding_pipeline.task_event",
            feature="embedding-pipeline",
            action=action,
            task_id=task.task_id,
            document_id=task.document_id,
            document_kind=task.document_kind,
            current_stage=task.current_stage,
            retry_count=task.retry_count,
            chunk_count=chunk_count,
            embedding_model=embedding_model,
            rebuild_version=rebuild_version,
            profile_name=profile_name,
            duration_ms=duration_ms,
            error_code=error_code,
        )
