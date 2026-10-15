"""Synthetic evidence-selection evals; no provider or persistence is used."""
from __future__ import annotations

from copy import deepcopy
import json
import logging
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.ports.retrieval import RetrievedChunk, RetrievalContext
from app.services.chat_service import ChatService


CASES = [json.loads(line) for line in (
    Path(__file__).resolve().parents[3] / "ai/evals/question-prefetch-grounding.jsonl"
).read_text().splitlines() if line.strip()]


def synthetic_session():
    owner = "synthetic-owner"
    session_id = "synthetic-prefetch-session"
    document = SimpleNamespace(
        document_id="synthetic-knowledge", document_kind="knowledge",
        document_version_id="synthetic-v1", status="ready", index_state="indexed",
        active=True, knowledge_collection_id="synthetic-collection",
        display_name="合成缓存资料", summary="用于本地评测的合成摘要",
    )
    return SimpleNamespace(
        session_id=session_id, owner_user_id=owner, session_mode="interview", status="live",
        material_binding=SimpleNamespace(
            session_id=session_id, owner_user_id=owner, revision=1,
            resume_document_id=None, job_description_document_id=None,
            knowledge_document_ids=[document.document_id], bound_documents=[document],
        ),
    )


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_prefetch_evidence_selection_eval(case):
    current = synthetic_session()
    reads = []

    def get_session(**kwargs):
        assert kwargs == {"user_id": current.owner_user_id, "session_id": current.session_id}
        reads.append(1)
        return deepcopy(current)

    service = ChatService(
        settings=Settings(_env_file=None), logger=logging.getLogger("synthetic.prefetch.evals"),
        session_service=SimpleNamespace(get_session=get_session),
        retrieval_service=SimpleNamespace(), object_storage=SimpleNamespace(),
        repository=SimpleNamespace(), prompt_template=SimpleNamespace(),
        prompt_builder=SimpleNamespace(), llm_gateway=SimpleNamespace(),
    )

    def retrieve(*, question, session, **_kwargs):
        doc = session.material_binding.bound_documents[0]
        return RetrievalContext(
            normalized_question=question, context_text="合成资料依据",
            chunks=[RetrievedChunk(
                document_id=doc.document_id, document_kind="knowledge",
                chunk_id="synthetic-chunk", chunk_index=0, content="合成缓存策略",
                score=1.0, metadata={"documentVersionId": doc.document_version_id},
            )],
        )

    service._retrieve_context = retrieve
    source = case["input"]
    service.prefetch_question_context(
        user_id=current.owner_user_id, session_id=current.session_id,
        question_id="synthetic-question", revision=1,
        question=source["preparedQuestion"],
    )
    for name, value in source["changes"].items():
        setattr(current.material_binding.bound_documents[0], name, value)
    current.material_binding.revision = source.get("selectionRevision", 1)
    snapshot = deepcopy(current)
    click_owner = source.get("clickOwner", current.owner_user_id)
    click_session = source.get("clickSession", current.session_id)
    if click_owner != current.owner_user_id:
        snapshot.owner_user_id = snapshot.material_binding.owner_user_id = click_owner
    if click_session != current.session_id:
        snapshot.session_id = snapshot.material_binding.session_id = click_session
    read_count_before_click = len(reads)
    result = service._prepared_retrieval(
        user_id=click_owner, session=snapshot, session_id=click_session,
        question_id="synthetic-question", revision=1,
        question=source["clickedQuestion"],
    )
    assert len(reads) == read_count_before_click, "click cache lookup must reuse its authorized snapshot"
    assert (result is not None) == case["expected"]["cacheHit"]
    if result is not None:
        assert result.chunks[0].metadata["documentVersionId"] == case["expected"]["sourceVersion"]
