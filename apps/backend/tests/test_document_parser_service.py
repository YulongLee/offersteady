from __future__ import annotations

from time import time

import httpx

from app.core.config import Settings
from app.adapters.oss_storage import AliyunOssStorageAdapter
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.ports.document_processing import DocumentParserContext, ProcessingTaskRecord
from app.ports.document_repository import DocumentRecord
from app.services.embedding_pipeline import EmbeddingPipelineService, ProcessingTaskEmbeddingStatusReporter
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
from app.services.document_processing_repository import InMemoryProcessingTaskRepository
from app.services.document_repository import InMemoryDocumentRepository


def _now_ms() -> int:
    return int(time() * 1000)


def test_empty_text_document_becomes_permanent_parser_failure() -> None:
    settings = get_settings()
    logger = configure_logging(settings)
    storage = AliyunOssStorageAdapter(settings)
    storage.uploaded_objects["materials/test-user/resume/empty.txt"] = b"   "
    documents = InMemoryDocumentRepository()
    tasks = InMemoryProcessingTaskRepository()
    vector_store = InMemoryPgvectorStore()
    parser_reporter = ProcessingTaskParserStatusReporter(settings=settings, logger=logger, task_repository=tasks)
    embedding_reporter = ProcessingTaskEmbeddingStatusReporter(settings=settings, logger=logger, task_repository=tasks)
    parser_service = DocumentParserService(
        settings=settings,
        logger=logger,
        object_storage=storage,
        binary_parser=MineruDocumentParserAdapter(settings),
        markdown_normalizer=MarkdownNormalizerAdapter(),
        status_reporter=parser_reporter,
    )
    embedding_pipeline = EmbeddingPipelineService(
        settings=settings,
        logger=logger,
        cleaner=MarkdownCleanerAdapter(),
        splitter=MarkdownChunkSplitterAdapter(),
        metadata_builder=ChunkMetadataBuilderAdapter(),
        embedding=SyntheticEmbeddingAdapter(settings),
        vector_store=vector_store,
        status_reporter=embedding_reporter,
    )
    service = DocumentProcessingService(
        settings=settings,
        logger=logger,
        document_repository=documents,
        task_repository=tasks,
        parser_service=parser_service,
        embedding_pipeline=embedding_pipeline,
    )
    document = documents.save(
        DocumentRecord(
            document_id="document-empty-text",
            owner_user_id="test-user",
            document_kind="resume",
            display_name="empty.txt",
            file_kind="txt",
            content_type="text/plain",
            size_bytes=3,
            object_key="materials/test-user/resume/empty.txt",
            status="processing_requested",
            knowledge_collection_id=None,
            processing_requested_at_ms=_now_ms(),
            deleted_at_ms=None,
            created_at_ms=_now_ms(),
            updated_at_ms=_now_ms(),
            summary="等待处理",
        )
    )
    task = tasks.save_task(
        ProcessingTaskRecord(
            task_id="task-empty-text",
            document_id=document.document_id,
            owner_user_id=document.owner_user_id,
            document_kind=document.document_kind,
            current_stage="QUEUED",
            retry_count=0,
            max_retries=1,
            parser_provider=settings.document_processing_parser_provider,
            embedding_provider=settings.document_processing_embedding_provider,
            created_at_ms=_now_ms(),
            updated_at_ms=_now_ms(),
            queued_at_ms=_now_ms(),
        )
    )

    service.process_task(task.task_id)

    failed_task = tasks.get_task(task.task_id)
    assert failed_task is not None
    assert failed_task.current_stage == "FAILED"
    assert failed_task.error_code == "empty_document"
    assert failed_task.error_message == "文本内容为空，无法建立解析结果。"
    failed_document = documents.get_by_id(document.document_id)
    assert failed_document is not None
    assert failed_document.status == "failed"
    events = tasks.list_events_for_task(task.task_id)
    assert any(event.event_name == "parser_started" for event in events)
    assert any(event.event_name == "parser_failed" for event in events)
    assert any(event.event_name == "task_failed" for event in events)


def test_mineru_parser_polls_async_task_until_markdown(monkeypatch) -> None:
    monkeypatch.setenv("OFFERSTEADY_TEST_USE_REMOTE_MINERU", "1")
    settings = Settings(
        integration_mineru_base_url="https://mineru.example.test/api/v4",
        integration_mineru_parse_path="/extract/task",
        integration_mineru_result_path="/extract/task/{task_id}",
        integration_mineru_poll_attempts=2,
        integration_mineru_poll_interval_ms=0,
    )
    calls: list[str] = []
    real_client = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(f"{request.method} {request.url.path}")
        if request.method == "POST":
            return httpx.Response(200, json={"code": 0, "data": {"task_id": "task-async-1", "status": "pending"}})
        return httpx.Response(200, json={"code": 0, "data": {"status": "completed", "markdown": "# 已解析简历\n\n统一 Markdown 内容。"}})

    class MockClient:
        def __init__(self, *args, **kwargs):
            self.client = real_client(transport=httpx.MockTransport(handler))

        def __enter__(self):
            return self.client

        def __exit__(self, exc_type, exc, tb):
            self.client.close()

    monkeypatch.setattr(httpx, "Client", MockClient)
    parser = MineruDocumentParserAdapter(settings)
    parsed = parser.parse(
        context=DocumentParserContext(
            task_id="task-local",
            document_id="document-local",
            document_kind="resume",
            file_kind="pdf",
            content_type="application/pdf",
            object_key="materials/test/resume.pdf",
            display_name="resume.pdf",
            retry_count=0,
        ),
        payload=b"%PDF",
    )

    assert parsed.markdown.startswith("# 已解析简历")
    assert parsed.provider_name == "mineru"
    assert calls == ["POST /api/v4/extract/task", "GET /api/v4/extract/task/task-async-1"]
