from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.material_formats import MaterialKind


RetrievalStrategy = Literal["filtered-first", "single-pass"]


class RetrievalFilterRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    owner_user_id: str = Field(min_length=1, alias="ownerUserId")
    interview_session_id: str | None = Field(default=None, alias="interviewSessionId")
    document_kinds: list[MaterialKind] = Field(default_factory=list, alias="documentKinds")
    document_ids: list[str] = Field(default_factory=list, alias="documentIds")
    document_version_ids: list[str] = Field(default_factory=list, alias="documentVersionIds")
    knowledge_collection_ids: list[str] = Field(default_factory=list, alias="knowledgeCollectionIds")


class RetrievalRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    question: str = Field(min_length=1)
    filter: RetrievalFilterRequest
    candidate_top_k: int | None = Field(default=None, alias="candidateTopK")
    final_top_k: int | None = Field(default=None, alias="finalTopK")
    strategy: RetrievalStrategy | None = None


class RetrievedChunkResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    document_id: str = Field(alias="documentId")
    document_kind: MaterialKind = Field(alias="documentKind")
    chunk_id: str = Field(alias="chunkId")
    chunk_index: int = Field(alias="chunkIndex")
    content: str
    score: float
    rerank_score: float | None = Field(default=None, alias="rerankScore")
    metadata: dict[str, str] = Field(default_factory=dict)


class RetrievalResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    normalized_question: str = Field(alias="normalizedQuestion")
    context_text: str = Field(alias="contextText")
    chunks: list[RetrievedChunkResponse] = Field(default_factory=list)
    candidate_count: int = Field(alias="candidateCount")
    final_count: int = Field(alias="finalCount")
    strategy: RetrievalStrategy
