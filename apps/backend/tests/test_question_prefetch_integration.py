from __future__ import annotations

from copy import deepcopy
import logging
import threading
from time import monotonic, sleep
from types import SimpleNamespace

from app.core.config import Settings
from app.ports.retrieval import RetrievalContext
from app.services.chat_service import ChatService
from app.services.question_prefetch_scheduler import QuestionPrefetchScheduler


def synthetic_chat():
    session = SimpleNamespace(
        session_id="synthetic-session", owner_user_id="synthetic-owner", status="live", session_mode="interview",
        material_binding=SimpleNamespace(
            session_id="synthetic-session", owner_user_id="synthetic-owner", revision=1,
            resume_document_id=None, job_description_document_id=None, knowledge_document_ids=["synthetic-doc"],
            bound_documents=[SimpleNamespace(
                document_id="synthetic-doc", document_kind="knowledge", document_version_id="synthetic-v1",
                status="ready", index_state="indexed", active=True, knowledge_collection_id="synthetic-collection",
            )],
        ),
    )
    service = ChatService(
        settings=Settings(_env_file=None), logger=logging.getLogger("synthetic-integration-prefetch"),
        session_service=SimpleNamespace(get_session=lambda **_kwargs: deepcopy(session)),
        retrieval_service=SimpleNamespace(), object_storage=SimpleNamespace(), repository=SimpleNamespace(),
        prompt_template=SimpleNamespace(), prompt_builder=SimpleNamespace(), llm_gateway=SimpleNamespace(),
    )
    return service, session


def enqueue(scheduler, revision=1, *, question="合成初始问题", is_final=False):
    return scheduler.submit(user_id="synthetic-owner", session_id="synthetic-session",
                            question_id="synthetic-question", revision=revision,
                            question=question, is_final=is_final)


def lookup(service, session, revision=1, question="合成初始问题"):
    return service._prepared_retrieval(user_id="synthetic-owner", session_id="synthetic-session", session=session,
                                       question_id="synthetic-question", revision=revision, question=question)


def until(predicate):
    deadline = monotonic() + 2
    while not predicate():
        assert monotonic() < deadline
        sleep(0.002)


def test_real_chat_final_can_finish_before_blocked_partial_and_late_partial_is_not_cached():
    service, session = synthetic_chat()
    started, release, final_done = threading.Event(), threading.Event(), threading.Event()

    def retrieve(*, question, **_kwargs):
        if question == "合成初始问题":
            started.set()
            assert release.wait(2)
        else:
            final_done.set()
        return RetrievalContext(normalized_question=question, context_text=f"synthetic evidence:{question}")

    service._retrieve_context = retrieve
    scheduler = QuestionPrefetchScheduler(service.prefetch_question_context, logger=service.logger)
    try:
        enqueue(scheduler)
        assert started.wait(1)
        enqueue(scheduler, 2, question="合成最终完整问题", is_final=True)
        assert final_done.wait(1)
        until(lambda: lookup(service, session, revision=2, question="合成最终完整问题") is not None)
        assert not release.is_set()
        assert lookup(service, session) is None
        release.set()
        until(lambda: scheduler.diagnostics()["active"] == 0)
        assert lookup(service, session, revision=2, question="合成最终完整问题").context_text.endswith("合成最终完整问题")
        assert lookup(service, session) is None
    finally:
        release.set()
        scheduler.shutdown(wait=True)


def test_real_chat_same_revision_final_hint_reuses_current_inflight_preparation():
    service, session = synthetic_chat()
    started, release = threading.Event(), threading.Event()
    calls = []

    def retrieve(*, question, **_kwargs):
        calls.append(question)
        started.set()
        assert release.wait(2)
        return RetrievalContext(normalized_question=question, context_text="synthetic final evidence")

    service._retrieve_context = retrieve
    scheduler = QuestionPrefetchScheduler(service.prefetch_question_context, logger=service.logger)
    try:
        assert enqueue(scheduler)
        assert started.wait(1)
        assert not enqueue(scheduler)
        assert enqueue(scheduler, is_final=True)
        release.set()
        until(lambda: scheduler.diagnostics()["active"] == 0)
        assert calls == ["合成初始问题"]
        assert lookup(service, session).context_text == "synthetic final evidence"
    finally:
        release.set()
        scheduler.shutdown(wait=True)


def test_real_chat_session_clear_and_shutdown_revoke_late_preparation():
    for shutdown in (False, True):
        service, session = synthetic_chat()
        started, release = threading.Event(), threading.Event()

        def retrieve(*, question, **_kwargs):
            started.set()
            assert release.wait(2)
            return RetrievalContext(normalized_question=question, context_text="synthetic obsolete evidence")

        service._retrieve_context = retrieve
        scheduler = QuestionPrefetchScheduler(service.prefetch_question_context, logger=service.logger)
        try:
            enqueue(scheduler)
            assert started.wait(1)
            enqueue(scheduler, 2)
            if shutdown:
                scheduler.shutdown()
            else:
                scheduler.clear_session(session_id=session.session_id)
            release.set()
            until(lambda: scheduler.diagnostics()["active"] == 0)
            assert lookup(service, session) is None
            assert scheduler.diagnostics()["pending"] == 0
        finally:
            release.set()
            scheduler.shutdown(wait=True)
