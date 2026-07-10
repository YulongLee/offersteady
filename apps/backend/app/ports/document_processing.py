from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

from app.material_formats import MaterialFormatId, MaterialKind


ProcessingStage = Literal["UPLOADED", "QUEUED", "PARSING", "CHUNKING", "EMBEDDING", "VECTOR_WRITING", "COMPLETED", "FAILED"]


@dataclass
class ProcessingTaskRecord:
    task_id: str
    document_id: str
    owner_user_id: str
    document_kind: MaterialKind
    current_stage: ProcessingStage
    retry_count: int
    max_retries: int
    parser_provider: str
    embedding_provider: str
    chunk_count: int = 0
    error_code: str | None = None
    error_message: str | None = None
    created_at_ms: int = 0
    updated_at_ms: int = 0
    queued_at_ms: int | None = None
    started_at_ms: int | None = None
    completed_at_ms: int | None = None
    last_retry_at_ms: int | None = None


@dataclass
class ProcessingTaskEvent:
    event_id: str
    task_id: str
    stage: ProcessingStage
    retry_count: int
    event_name: str
    duration_ms: int | None
    error_code: str | None
    created_at_ms: int


@dataclass(frozen=True)
class ParserWarning:
    code: str
    message: str


@dataclass(frozen=True)
class ParserFailure:
    error_code: str
    error_type: Literal["recoverable", "permanent"]
    retryable: bool
    provider_name: str
    message_safe_for_log: str
    warnings: list[ParserWarning] = field(default_factory=list)


@dataclass(frozen=True)
class DocumentParserContext:
    task_id: str
    document_id: str
    document_kind: MaterialKind
    file_kind: MaterialFormatId
    content_type: str
    object_key: str
    display_name: str
    retry_count: int


@dataclass(frozen=True)
class ParsedDocument:
    markdown: str
    provider_name: str
    detected_title: str | None = None
    warnings: list[ParserWarning] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class NormalizedDocument:
    markdown: str


@dataclass(frozen=True)
class CleanedMarkdown:
    markdown: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ChunkingProfile:
    profile_name: str
    chunk_size: int
    overlap: int
    split_priority: Literal["fixed", "paragraph", "heading"]


@dataclass(frozen=True)
class ChunkRecord:
    chunk_id: str
    content: str
    index: int
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class EmbeddedChunk:
    chunk_id: str
    vector: list[float]
    content: str
    index: int
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class EmbeddingFailure:
    error_code: str
    error_type: Literal["recoverable", "permanent"]
    retryable: bool
    provider_name: str
    message_safe_for_log: str


@dataclass(frozen=True)
class StoredVectorRecord:
    document_id: str
    document_kind: MaterialKind
    chunk_id: str
    embedding_model: str
    rebuild_version: int
    chunk_index: int
    owner_user_id: str | None = None
    document_version_id: str | None = None
    knowledge_collection_id: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class VectorSearchMatch:
    document_id: str
    document_kind: MaterialKind
    chunk_id: str
    chunk_index: int
    content: str
    score: float
    embedding_model: str
    rebuild_version: int
    metadata: dict[str, str] = field(default_factory=dict)


class ProcessingTaskRepository(Protocol):
    def save_task(self, task: ProcessingTaskRecord) -> ProcessingTaskRecord: ...
    def get_task(self, task_id: str) -> ProcessingTaskRecord | None: ...
    def list_tasks_for_user(self, *, user_id: str | None = None, document_id: str | None = None) -> list[ProcessingTaskRecord]: ...
    def save_event(self, event: ProcessingTaskEvent) -> ProcessingTaskEvent: ...
    def list_events_for_task(self, task_id: str) -> list[ProcessingTaskEvent]: ...


class DocumentParserPort(Protocol):
    def parse(self, *, context: DocumentParserContext, payload: bytes) -> ParsedDocument: ...


class MarkdownNormalizerPort(Protocol):
    def normalize(self, *, markdown: str, document_kind: MaterialKind, file_kind: MaterialFormatId) -> NormalizedDocument: ...


class ParserStatusPort(Protocol):
    def mark_parsing_started(self, task: ProcessingTaskRecord) -> ProcessingTaskRecord: ...
    def mark_parsing_succeeded(self, task: ProcessingTaskRecord, parsed: ParsedDocument, *, duration_ms: int) -> ProcessingTaskRecord: ...
    def mark_parsing_failed(self, task: ProcessingTaskRecord, failure: ParserFailure, *, duration_ms: int) -> ProcessingTaskRecord: ...


class MarkdownCleanerPort(Protocol):
    def clean(self, *, markdown: str, document_kind: MaterialKind) -> CleanedMarkdown: ...


class ChunkSplitterPort(Protocol):
    def split(self, *, markdown: str, document_kind: MaterialKind, profile: ChunkingProfile) -> list[ChunkRecord]: ...


class ChunkMetadataBuilderPort(Protocol):
    def build(
        self,
        *,
        document_id: str,
        document_kind: MaterialKind,
        profile: ChunkingProfile,
        parser_metadata: dict[str, str],
        chunks: list[ChunkRecord],
        rebuild_version: int,
    ) -> list[ChunkRecord]: ...


class EmbeddingPort(Protocol):
    def embed(
        self,
        *,
        chunks: list[ChunkRecord],
        document_kind: MaterialKind,
        embedding_model: str,
        batch_size: int,
    ) -> list[EmbeddedChunk]: ...


class VectorStorePort(Protocol):
    def upsert_document_chunks(
        self,
        *,
        document_id: str,
        document_kind: MaterialKind,
        chunks: list[EmbeddedChunk],
        embedding_model: str,
        rebuild_version: int,
    ) -> int: ...

    def next_rebuild_version(self, *, document_id: str) -> int: ...

    def search_similar(
        self,
        *,
        query_vector: list[float],
        top_k: int,
        document_kinds: list[MaterialKind] | None = None,
        document_ids: list[str] | None = None,
        knowledge_collection_ids: list[str] | None = None,
    ) -> list[VectorSearchMatch]: ...


class EmbeddingStatusPort(Protocol):
    def mark_chunking_started(self, task: ProcessingTaskRecord, *, profile: ChunkingProfile) -> ProcessingTaskRecord: ...
    def mark_embedding_started(self, task: ProcessingTaskRecord, *, chunk_count: int, embedding_model: str) -> ProcessingTaskRecord: ...
    def mark_vector_writing_started(self, task: ProcessingTaskRecord, *, chunk_count: int, rebuild_version: int) -> ProcessingTaskRecord: ...
    def mark_embedding_failed(self, task: ProcessingTaskRecord, failure: EmbeddingFailure, *, duration_ms: int) -> ProcessingTaskRecord: ...
