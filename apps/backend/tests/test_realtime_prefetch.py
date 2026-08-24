from __future__ import annotations

import logging
import threading
from types import SimpleNamespace

from app.ports.retrieval import RetrievalContext
from app.services.chat_service import ChatService


def test_newer_question_revision_cancels_a_stale_prefetch_result() -> None:
    service = ChatService.__new__(ChatService)
    service.logger = logging.getLogger("test.realtime-prefetch")
    service.session_service = SimpleNamespace(get_session=lambda **_kwargs: SimpleNamespace())
    service._prepared_context_lock = threading.Lock()
    service._prepared_context = {}
    service._latest_prefetch_revision = {}
    old_started = threading.Event()
    release_old = threading.Event()

    def retrieve_context(*, question: str, **_kwargs) -> RetrievalContext:
        if question == "旧问题":
            old_started.set()
            assert release_old.wait(timeout=2)
        return RetrievalContext(normalized_question=question, context_text=f"context:{question}")

    service._retrieve_context = retrieve_context  # type: ignore[method-assign]
    old = threading.Thread(target=service.prefetch_question_context, kwargs={
        "user_id": "synthetic-user", "session_id": "session-1", "question_id": "question-1",
        "revision": 1, "question": "旧问题",
    })
    old.start()
    assert old_started.wait(timeout=2)
    service.prefetch_question_context(
        user_id="synthetic-user", session_id="session-1", question_id="question-1",
        revision=2, question="新问题",
    )
    release_old.set()
    old.join(timeout=2)

    assert ("session-1", "question-1", 1) not in service._prepared_context
    assert service._prepared_retrieval(
        session_id="session-1", question_id="question-1", revision=2, question="新问题"
    ) == RetrievalContext(normalized_question="新问题", context_text="context:新问题")
