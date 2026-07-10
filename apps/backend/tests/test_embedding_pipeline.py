from __future__ import annotations

from time import time

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.ports.document_processing import ParsedDocument, ProcessingTaskRecord
from app.ports.document_repository import DocumentRecord
from app.services.embedding_pipeline import EmbeddingPipelineService, ProcessingTaskEmbeddingStatusReporter
from app.services.document_processing_adapters import (
    ChunkMetadataBuilderAdapter,
    InMemoryPgvectorStore,
    MarkdownCleanerAdapter,
    MarkdownChunkSplitterAdapter,
    SyntheticEmbeddingAdapter,
)
from app.services.document_processing_repository import InMemoryProcessingTaskRepository


def _now_ms() -> int:
    return int(time() * 1000)


def test_embedding_pipeline_supports_rebuild_versions_and_chunk_profiles() -> None:
    settings = get_settings()
    logger = configure_logging(settings)
    task_repository = InMemoryProcessingTaskRepository()
    vector_store = InMemoryPgvectorStore()
    reporter = ProcessingTaskEmbeddingStatusReporter(settings=settings, logger=logger, task_repository=task_repository)
    service = EmbeddingPipelineService(
        settings=settings,
        logger=logger,
        cleaner=MarkdownCleanerAdapter(),
        splitter=MarkdownChunkSplitterAdapter(),
        metadata_builder=ChunkMetadataBuilderAdapter(),
        embedding=SyntheticEmbeddingAdapter(settings),
        vector_store=vector_store,
        status_reporter=reporter,
    )
    document = DocumentRecord(
        document_id="document-knowledge-1",
        owner_user_id="owner-1",
        document_kind="knowledge",
        display_name="notes.md",
        file_kind="md",
        content_type="text/markdown",
        size_bytes=1024,
        object_key="materials/owner-1/knowledge/notes.md",
        status="processing",
        knowledge_collection_id="collection-1",
        processing_requested_at_ms=_now_ms(),
        deleted_at_ms=None,
        created_at_ms=_now_ms(),
        updated_at_ms=_now_ms(),
        summary="处理中",
    )
    task = ProcessingTaskRecord(
        task_id="task-embedding-1",
        document_id=document.document_id,
        owner_user_id=document.owner_user_id,
        document_kind=document.document_kind,
        current_stage="PARSING",
        retry_count=0,
        max_retries=2,
        parser_provider="text-parser",
        embedding_provider=settings.document_processing_embedding_provider,
        created_at_ms=_now_ms(),
        updated_at_ms=_now_ms(),
        started_at_ms=_now_ms(),
    )
    parsed = ParsedDocument(
        markdown="# Notes\n\n" + ("知识点内容 " * 500),
        provider_name="text-parser",
        metadata={"parserProfile": "plain-text"},
    )

    first = service.process_markdown(task=task, document=document, parsed=parsed)
    second = service.rebuild_document_vectors(task=first.task, document=document, parsed=parsed)

    assert first.chunk_count >= 1
    assert second.rebuild_version == first.rebuild_version + 1
    assert vector_store.rows[document.document_id][0].metadata["chunkProfile"] == "knowledge-default"
    assert vector_store.rows[document.document_id][0].metadata["rebuildVersion"] == str(second.rebuild_version)
    events = task_repository.list_events_for_task(task.task_id)
    assert any(event.event_name == "embedding_chunking_started" for event in events)
    assert any(event.event_name == "embedding_started" for event in events)
    assert any(event.event_name == "vector_writing_started" for event in events)
