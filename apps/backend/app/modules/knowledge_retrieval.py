from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.core.config import Settings
from app.core.logging import utc_now_iso
from app.core.responses import success_response
from app.deps import retrieval_port, settings_dependency
from app.ports.retrieval import RetrievalFilter, RetrievalPort
from app.schemas.foundation import ApiEnvelope, ModuleDescriptor
from app.schemas.retrieval import RetrievalRequest, RetrievalResponse, RetrievedChunkResponse


router = APIRouter(prefix="/knowledge-retrieval", tags=["knowledge-retrieval"])
descriptor = ModuleDescriptor(
    feature="knowledge-retrieval",
    owningApp="apps/backend",
    routePrefix="/api/v1/knowledge-retrieval",
    mode="active",
    notes="Unified retrieval API for resume, JD, and knowledge-base vector context.",
)


@router.post("/context", response_model=ApiEnvelope[RetrievalResponse])
async def retrieve_context(
    request_context: Request,
    request: RetrievalRequest,
    service: RetrievalPort = Depends(retrieval_port),
    settings: Settings = Depends(settings_dependency),
) -> ApiEnvelope[RetrievalResponse]:
    result = service.retrieve(
        question=request.question,
        filter=RetrievalFilter(
            owner_user_id=request.filter.owner_user_id,
            interview_session_id=request.filter.interview_session_id,
            document_kinds=request.filter.document_kinds,
            document_ids=request.filter.document_ids,
            knowledge_collection_ids=request.filter.knowledge_collection_ids,
        ),
        candidate_top_k=request.candidate_top_k or settings.retrieval_candidate_top_k,
        final_top_k=request.final_top_k or settings.retrieval_final_top_k,
        strategy=request.strategy or settings.retrieval_strategy,
    )
    return success_response(
        request=request_context,
        data=RetrievalResponse(
            normalizedQuestion=result.normalized_question,
            contextText=result.context_text,
            chunks=[
                RetrievedChunkResponse(
                    documentId=chunk.document_id,
                    documentKind=chunk.document_kind,
                    chunkId=chunk.chunk_id,
                    chunkIndex=chunk.chunk_index,
                    content=chunk.content,
                    score=chunk.score,
                    rerankScore=chunk.rerank_score,
                    metadata=chunk.metadata,
                )
                for chunk in result.chunks
            ],
            candidateCount=result.candidate_count,
            finalCount=result.final_count,
            strategy=result.strategy,
        ),
        timestamp=utc_now_iso(),
    )
