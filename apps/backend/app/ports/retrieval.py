from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

from app.material_formats import MaterialKind


RetrievalStrategy = Literal["filtered-first", "single-pass"]


@dataclass(frozen=True)
class RetrievalFilter:
    owner_user_id: str
    interview_session_id: str | None = None
    document_kinds: list[MaterialKind] = field(default_factory=list)
    document_ids: list[str] = field(default_factory=list)
    document_version_ids: list[str] = field(default_factory=list)
    knowledge_collection_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class QueryEmbeddingResult:
    query_text: str
    vector: list[float]
    provider_name: str
    model_name: str


@dataclass(frozen=True)
class RetrievedChunk:
    document_id: str
    document_kind: MaterialKind
    chunk_id: str
    chunk_index: int
    content: str
    score: float
    metadata: dict[str, str] = field(default_factory=dict)
    rerank_score: float | None = None


@dataclass(frozen=True)
class RetrievalContext:
    normalized_question: str
    context_text: str
    chunks: list[RetrievedChunk] = field(default_factory=list)
    candidate_count: int = 0
    final_count: int = 0
    strategy: RetrievalStrategy = "filtered-first"
    trace_id: str | None = None


class QueryEmbeddingPort(Protocol):
    def embed_query(self, *, question: str) -> QueryEmbeddingResult: ...


class RerankerPort(Protocol):
    def rerank(self, *, question: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]: ...


class ContextBuilderPort(Protocol):
    def build(self, *, question: str, chunks: list[RetrievedChunk], strategy: RetrievalStrategy) -> RetrievalContext: ...


class RetrievalPort(Protocol):
    def retrieve(
        self,
        *,
        question: str,
        filter: RetrievalFilter,
        candidate_top_k: int,
        final_top_k: int,
        strategy: RetrievalStrategy,
    ) -> RetrievalContext: ...


class NullRetrievalPort(RetrievalPort):
    def retrieve(
        self,
        *,
        question: str,
        filter: RetrievalFilter,
        candidate_top_k: int,
        final_top_k: int,
        strategy: RetrievalStrategy,
    ) -> RetrievalContext:
        return RetrievalContext(
            normalized_question=question.strip(),
            context_text="",
            chunks=[],
            candidate_count=0,
            final_count=0,
            strategy=strategy,
        )
