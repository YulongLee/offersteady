from __future__ import annotations

import hashlib
import logging
import re
from typing import Any
from dataclasses import replace
from time import time

import httpx

from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.core.logging import log_event
from app.ports.commercial_hardening import AiUsageRecord, CommercialHardeningRepository, RagRetrievalTraceRecord
from app.ports.document_processing import VectorStorePort
from app.ports.document_repository import DocumentRepository
from app.ports.retrieval import (
    ContextBuilderPort,
    QueryEmbeddingPort,
    QueryEmbeddingResult,
    RetrievedChunk,
    RetrievalContext,
    RetrievalFilter,
    RetrievalPort,
    RetrievalStrategy,
    RerankerPort,
)
from app.services.commercial_hardening import trace_id, usage_id


def _now_ms() -> int:
    return int(time() * 1000)


class SyntheticQueryEmbeddingAdapter(QueryEmbeddingPort):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def embed_query(self, *, question: str) -> QueryEmbeddingResult:
        normalized = _normalize_question(question)
        digest = hashlib.sha256(f"query:{normalized}".encode("utf-8")).digest()
        vector = [round(byte / 255, 6) for byte in digest[:8]]
        return QueryEmbeddingResult(
            query_text=normalized,
            vector=vector,
            provider_name=self.settings.retrieval_query_embedding_provider,
            model_name=self.settings.document_processing_embedding_provider,
        )


class DashScopeCompatibleQueryEmbeddingAdapter(QueryEmbeddingPort):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def embed_query(self, *, question: str) -> QueryEmbeddingResult:
        normalized = _normalize_question(question)
        base_url = (self.settings.embedding_base_url or "").rstrip("/")
        api_key = self.settings.embedding_api_key
        if not base_url or not api_key:
            raise RuntimeError("embedding_config_missing")
        model = self.settings.embedding_model
        with httpx.Client(timeout=self.settings.integration_http_timeout_seconds) as client:
            response = client.post(
                f"{base_url}/embeddings",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model, "input": normalized},
            )
        if response.status_code >= 400:
            response.raise_for_status()
        payload = response.json()
        data = payload.get("data")
        if not isinstance(data, list) or not data or not isinstance(data[0], dict) or not isinstance(data[0].get("embedding"), list):
            raise RuntimeError("embedding_provider_invalid_response")
        return QueryEmbeddingResult(
            query_text=normalized,
            vector=[float(value) for value in data[0]["embedding"]],
            provider_name="dashscope-compatible-embedding",
            model_name=model,
        )


class HeuristicRerankerAdapter(RerankerPort):
    def rerank(self, *, question: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        question_tokens = set(_tokenize(question))
        reranked: list[RetrievedChunk] = []
        for chunk in chunks:
            overlap = len(question_tokens.intersection(_tokenize(chunk.content)))
            rerank_score = round(chunk.score + overlap * 0.05, 6)
            reranked.append(replace(chunk, rerank_score=rerank_score))
        reranked.sort(key=lambda item: item.rerank_score if item.rerank_score is not None else item.score, reverse=True)
        return reranked


class DashScopeRerankerAdapter(RerankerPort):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def rerank(self, *, question: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        if not chunks:
            return []
        base_url = (self.settings.rerank_base_url or "").rstrip("/")
        api_key = self.settings.rerank_api_key
        if not base_url or not api_key:
            return HeuristicRerankerAdapter().rerank(question=question, chunks=chunks)
        url = f"{base_url}{self.settings.rerank_api_path if self.settings.rerank_api_path.startswith('/') else f'/{self.settings.rerank_api_path}'}"
        documents = [chunk.content for chunk in chunks]
        try:
            with httpx.Client(timeout=self.settings.integration_http_timeout_seconds) as client:
                response = client.post(
                    url,
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={
                        "model": self.settings.rerank_model,
                        "input": {"query": question, "documents": documents[:6]},
                        "parameters": {"top_n": min(len(documents), 3), "return_documents": False},
                    },
                )
            if response.status_code >= 400:
                response.raise_for_status()
            results = self._extract_results(response.json())
        except Exception:
            return HeuristicRerankerAdapter().rerank(question=question, chunks=chunks)
        if not results:
            return HeuristicRerankerAdapter().rerank(question=question, chunks=chunks)
        reranked: list[RetrievedChunk] = []
        for index, score in results:
            if 0 <= index < len(chunks):
                reranked.append(replace(chunks[index], rerank_score=round(float(score), 6)))
        seen = {chunk.chunk_id for chunk in reranked}
        reranked.extend(chunk for chunk in chunks if chunk.chunk_id not in seen)
        reranked.sort(key=lambda item: item.rerank_score if item.rerank_score is not None else item.score, reverse=True)
        return reranked

    def _extract_results(self, payload: dict[str, Any]) -> list[tuple[int, float]]:
        raw_results = payload.get("results")
        if not isinstance(raw_results, list):
            output = payload.get("output")
            raw_results = output.get("results") if isinstance(output, dict) else None
        if not isinstance(raw_results, list):
            return []
        results: list[tuple[int, float]] = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            index = item.get("index")
            score = item.get("relevance_score", item.get("score"))
            if isinstance(index, int) and isinstance(score, (int, float)):
                results.append((index, float(score)))
        return results


class RetrievalContextBuilder(ContextBuilderPort):
    def build(self, *, question: str, chunks: list[RetrievedChunk], strategy: RetrievalStrategy) -> RetrievalContext:
        normalized_question = _normalize_question(question)
        lines = []
        for index, chunk in enumerate(chunks, start=1):
            source = chunk.metadata.get("displayName") or chunk.document_kind
            lines.append(f"[{index}] ({source}) {chunk.content.strip()}")
        return RetrievalContext(
            normalized_question=normalized_question,
            context_text="\n\n".join(lines),
            chunks=chunks,
            candidate_count=len(chunks),
            final_count=len(chunks),
            strategy=strategy,
        )


class KnowledgeRetrievalService(RetrievalPort):
    def __init__(
        self,
        *,
        settings: Settings,
        logger: logging.Logger,
        query_embedding: QueryEmbeddingPort,
        vector_store: VectorStorePort,
        document_repository: DocumentRepository,
        reranker: RerankerPort,
        context_builder: ContextBuilderPort,
        commercial_repository: CommercialHardeningRepository | None = None,
    ) -> None:
        self.settings = settings
        self.logger = logger
        self.query_embedding = query_embedding
        self.vector_store = vector_store
        self.document_repository = document_repository
        self.reranker = reranker
        self.context_builder = context_builder
        self.commercial_repository = commercial_repository

    def retrieve(
        self,
        *,
        question: str,
        filter: RetrievalFilter,
        candidate_top_k: int,
        final_top_k: int,
        strategy: RetrievalStrategy,
    ) -> RetrievalContext:
        started_at = _now_ms()
        normalized_question = _normalize_question(question)
        if not normalized_question:
            raise DomainRequestError("knowledge-retrieval", "retrieve", "用户问题不能为空。")
        if filter.interview_session_id and not filter.document_ids and not filter.document_version_ids:
            self._record_rag_trace(
                question=normalized_question,
                filter=filter,
                strategy=strategy,
                candidate_count=0,
                reranked_count=0,
                returned_chunks=[],
            )
            return RetrievalContext(
                normalized_question=normalized_question,
                context_text="",
                chunks=[],
                candidate_count=0,
                final_count=0,
                strategy=strategy,
            )
        self._log_retrieval_started(question=normalized_question, filter=filter)
        try:
            embedding = self.query_embedding.embed_query(question=normalized_question)
            self._record_usage(
                owner_user_id=filter.owner_user_id,
                operation_kind="embedding",
                provider=embedding.provider_name,
                model=embedding.model_name,
                status="succeeded",
                input_units=1,
                total_units=1,
            )
            candidate_matches = self.vector_store.search_similar(
                query_vector=embedding.vector,
                top_k=max(1, candidate_top_k),
                document_kinds=filter.document_kinds or None,
                document_ids=filter.document_ids or None,
                knowledge_collection_ids=filter.knowledge_collection_ids or None,
            )
            filtered_chunks = self._apply_metadata_filter(candidate_matches, filter=filter)
            filtered_chunks = [chunk for chunk in filtered_chunks if chunk.score >= self.settings.retrieval_min_score_threshold]
            top_candidates = filtered_chunks[: max(1, candidate_top_k)]
            final_chunks = self.reranker.rerank(question=normalized_question, chunks=top_candidates) if self.settings.retrieval_reranker_enabled else top_candidates
            if self.settings.retrieval_reranker_enabled:
                self._record_usage(
                    owner_user_id=filter.owner_user_id,
                    operation_kind="rerank",
                    provider=self.settings.rerank_base_url or "heuristic-reranker",
                    model=self.settings.rerank_model if self.settings.rerank_base_url else "heuristic-reranker",
                    status="succeeded",
                    input_units=len(top_candidates),
                    total_units=len(top_candidates),
                )
            final_chunks = final_chunks[: max(1, final_top_k)]
            context = self.context_builder.build(question=normalized_question, chunks=final_chunks, strategy=strategy)
            context = replace(context, candidate_count=len(top_candidates), final_count=len(final_chunks))
            rag_trace = self._record_rag_trace(
                question=normalized_question,
                filter=filter,
                strategy=strategy,
                candidate_count=len(top_candidates),
                reranked_count=len(final_chunks) if self.settings.retrieval_reranker_enabled else 0,
                returned_chunks=final_chunks,
            )
            if rag_trace is not None:
                context = replace(context, trace_id=rag_trace.trace_id)
            self._log_retrieval_succeeded(
                question=normalized_question,
                filter=filter,
                candidate_count=len(top_candidates),
                final_count=len(final_chunks),
                provider_name=embedding.provider_name,
                duration_ms=_now_ms() - started_at,
                strategy=strategy,
            )
            return context
        except Exception as exc:
            self._record_rag_trace(
                question=normalized_question,
                filter=filter,
                strategy=strategy,
                candidate_count=0,
                reranked_count=0,
                returned_chunks=[],
                safe_error_code=exc.__class__.__name__,
            )
            self._log_retrieval_failed(
                question=normalized_question,
                filter=filter,
                duration_ms=_now_ms() - started_at,
                error_code=exc.__class__.__name__,
            )
            raise

    def _record_usage(
        self,
        *,
        owner_user_id: str,
        operation_kind: str,
        provider: str,
        model: str,
        status: str,
        input_units: int,
        total_units: int,
    ) -> None:
        if self.commercial_repository is None:
            return
        self.commercial_repository.record_ai_usage(
            AiUsageRecord(
                usage_id=usage_id(),
                owner_user_id=owner_user_id,
                operation_kind=operation_kind,  # type: ignore[arg-type]
                provider=provider,
                model=model,
                status=status,  # type: ignore[arg-type]
                input_units=input_units,
                total_units=total_units,
                created_at_ms=_now_ms(),
            )
        )

    def _record_rag_trace(
        self,
        *,
        question: str,
        filter: RetrievalFilter,
        strategy: RetrievalStrategy,
        candidate_count: int,
        reranked_count: int,
        returned_chunks: list[RetrievedChunk],
        safe_error_code: str | None = None,
    ) -> RagRetrievalTraceRecord | None:
        if self.commercial_repository is None:
            return None
        trace = RagRetrievalTraceRecord(
            trace_id=trace_id(),
            owner_user_id=filter.owner_user_id,
            session_id=filter.interview_session_id,
            query_hash=hashlib.sha256(question.encode("utf-8")).hexdigest(),
            strategy=strategy,
            filter_document_ids=tuple(filter.document_ids),
            filter_document_version_ids=tuple(filter.document_version_ids),
            candidate_count=candidate_count,
            reranked_count=reranked_count,
            returned_count=len(returned_chunks),
            returned_source_ids=tuple(f"{chunk.document_id}:{chunk.chunk_id}" for chunk in returned_chunks),
            safe_error_code=safe_error_code,
            created_at_ms=_now_ms(),
        )
        return self.commercial_repository.record_rag_trace(trace)

    def _apply_metadata_filter(self, matches, *, filter: RetrievalFilter) -> list[RetrievedChunk]:
        filtered: list[RetrievedChunk] = []
        for match in matches:
            record = self.document_repository.get_by_id(match.document_id)
            if record is None:
                continue
            if record.owner_user_id != filter.owner_user_id:
                continue
            if record.status != "ready" or record.index_state not in {None, "indexed"}:
                continue
            if filter.document_kinds and record.document_kind not in filter.document_kinds:
                continue
            if filter.document_ids and record.document_id not in filter.document_ids:
                continue
            if filter.document_version_ids and record.document_version_id not in filter.document_version_ids:
                continue
            if filter.knowledge_collection_ids and record.knowledge_collection_id not in filter.knowledge_collection_ids:
                continue
            metadata = {
                **match.metadata,
                "displayName": record.display_name,
                "ownerUserId": record.owner_user_id,
                "documentVersionId": record.document_version_id or "",
                "indexState": record.index_state or "",
                "knowledgeCollectionId": record.knowledge_collection_id or "",
            }
            filtered.append(
                RetrievedChunk(
                    document_id=match.document_id,
                    document_kind=match.document_kind,
                    chunk_id=match.chunk_id,
                    chunk_index=match.chunk_index,
                    content=match.content,
                    score=round(match.score, 6),
                    metadata=metadata,
                )
            )
        filtered.sort(key=lambda item: item.score, reverse=True)
        return filtered

    def _log_retrieval_started(self, *, question: str, filter: RetrievalFilter) -> None:
        log_event(
            self.logger,
            logging.INFO,
            settings=self.settings,
            event="knowledge_retrieval.started",
            feature="knowledge-retrieval",
            action="retrieve",
            question_hash=hashlib.sha256(question.encode("utf-8")).hexdigest()[:12],
            question_length=len(question),
            retrieval_strategy=self.settings.retrieval_strategy,
            document_kinds=",".join(filter.document_kinds),
            document_ids_count=len(filter.document_ids),
            document_version_ids_count=len(filter.document_version_ids),
            knowledge_collection_ids_count=len(filter.knowledge_collection_ids),
        )

    def _log_retrieval_succeeded(
        self,
        *,
        question: str,
        filter: RetrievalFilter,
        candidate_count: int,
        final_count: int,
        provider_name: str,
        duration_ms: int,
        strategy: RetrievalStrategy,
    ) -> None:
        log_event(
            self.logger,
            logging.INFO,
            settings=self.settings,
            event="knowledge_retrieval.succeeded",
            feature="knowledge-retrieval",
            action="retrieve",
            question_hash=hashlib.sha256(question.encode("utf-8")).hexdigest()[:12],
            question_length=len(question),
            candidate_count=candidate_count,
            final_count=final_count,
            provider_name=provider_name,
            retrieval_strategy=strategy,
            document_kinds=",".join(filter.document_kinds),
            document_ids_count=len(filter.document_ids),
            document_version_ids_count=len(filter.document_version_ids),
            knowledge_collection_ids_count=len(filter.knowledge_collection_ids),
            duration_ms=duration_ms,
        )

    def _log_retrieval_failed(
        self,
        *,
        question: str,
        filter: RetrievalFilter,
        duration_ms: int,
        error_code: str,
    ) -> None:
        log_event(
            self.logger,
            logging.WARNING,
            settings=self.settings,
            event="knowledge_retrieval.failed",
            feature="knowledge-retrieval",
            action="retrieve",
            question_hash=hashlib.sha256(question.encode("utf-8")).hexdigest()[:12],
            question_length=len(question),
            retrieval_strategy=self.settings.retrieval_strategy,
            document_kinds=",".join(filter.document_kinds),
            document_ids_count=len(filter.document_ids),
            document_version_ids_count=len(filter.document_version_ids),
            knowledge_collection_ids_count=len(filter.knowledge_collection_ids),
            error_code=error_code,
            duration_ms=duration_ms,
        )


def _normalize_question(question: str) -> str:
    return re.sub(r"\s+", " ", question).strip()


def _tokenize(text: str) -> list[str]:
    return [token for token in re.split(r"[^a-zA-Z0-9\u4e00-\u9fff]+", text.lower()) if token]
