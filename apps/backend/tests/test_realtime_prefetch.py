from __future__ import annotations

from copy import deepcopy
import logging
import threading
from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.ports.retrieval import RetrievedChunk, RetrievalContext
from app.services.chat_service import ChatService


def _session():
    return SimpleNamespace(
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


def _context(question="合成问题", version="synthetic-v1"):
    return RetrievalContext(
        normalized_question=question, context_text=f"synthetic:{version}",
        chunks=[RetrievedChunk(
            document_id="synthetic-doc", document_kind="knowledge", chunk_id=f"chunk:{version}",
            chunk_index=0, content="合成资料依据", score=1.0, metadata={"documentVersionId": version},
        )],
    )


def _service(current=None):
    current = current or _session()
    reads = []

    def get_session(**_kwargs):
        reads.append(1)
        return deepcopy(current)

    service = ChatService(
        settings=Settings(_env_file=None), logger=logging.getLogger("test.realtime-prefetch"),
        session_service=SimpleNamespace(get_session=get_session), retrieval_service=SimpleNamespace(),
        object_storage=SimpleNamespace(), repository=SimpleNamespace(), prompt_template=SimpleNamespace(),
        prompt_builder=SimpleNamespace(), llm_gateway=SimpleNamespace(),
    )
    service._retrieve_context = lambda *, question, **_kwargs: _context(question)  # type: ignore[method-assign]
    return service, current, reads


def _prefetch(service, *, revision=1, question="合成问题", **kwargs):
    service.prefetch_question_context(
        user_id="synthetic-owner", session_id="synthetic-session", question_id="synthetic-question",
        revision=revision, question=question, **kwargs,
    )


def _lookup(service, current, *, revision=1, question="合成问题", **kwargs):
    return service._prepared_retrieval(
        user_id=kwargs.get("user_id", "synthetic-owner"), session_id=kwargs.get("session_id", "synthetic-session"),
        session=current, question_id="synthetic-question", revision=revision, question=question,
    )


def test_newer_question_revision_cancels_a_stale_prefetch_result() -> None:
    service, current, _ = _service()
    old_started = threading.Event()
    release_old = threading.Event()

    def retrieve_context(*, question: str, **_kwargs) -> RetrievalContext:
        if question == "旧问题":
            old_started.set()
            assert release_old.wait(timeout=2)
        return _context(question)

    service._retrieve_context = retrieve_context  # type: ignore[method-assign]
    old = threading.Thread(target=_prefetch, args=(service,), kwargs={"question": "旧问题"})
    old.start()
    assert old_started.wait(timeout=2)
    _prefetch(service, revision=2, question="新问题")
    release_old.set()
    old.join(timeout=2)

    assert not old.is_alive()
    assert _lookup(service, current, question="旧问题") is None
    assert _lookup(service, current, revision=2, question="新问题") == _context("新问题")


@pytest.mark.parametrize("field,value", [
    ("document_version_id", "synthetic-v2"), ("active", False), ("status", "deleted"),
    ("index_state", "processing"), ("knowledge_collection_id", "synthetic-other-collection"),
    ("document_id", "synthetic-other-document"), ("document_kind", "resume"),
])
def test_material_changes_invalidate_cache_even_without_selection_revision_change(field, value):
    service, current, reads = _service()
    _prefetch(service)
    setattr(current.material_binding.bound_documents[0], field, value)
    assert current.material_binding.revision == 1
    assert _lookup(service, current) is None
    assert len(reads) == 2, "click lookup must not add a session read"


@pytest.mark.parametrize("changes", [
    {"revision": 2}, {"knowledge_document_ids": ["synthetic-other-document"]},
    {"resume_document_id": "synthetic-resume"}, {"job_description_document_id": "synthetic-jd"},
    {"owner_user_id": "synthetic-other-owner"}, {"session_id": "synthetic-other-session"},
])
def test_material_selection_and_binding_identity_are_part_of_cache_key(changes):
    service, current, _ = _service()
    _prefetch(service)
    for name, value in changes.items():
        setattr(current.material_binding, name, value)
    assert _lookup(service, current) is None


def test_question_matching_requires_complete_text_but_normalizes_whitespace():
    service, current, _ = _service()
    _prefetch(service, question="How  do you\n design a cache?")
    assert _lookup(service, current, question=" How do you design a cache? ") is not None
    assert _lookup(service, current, question="How do you design a cache? Explain consistency.") is None
    assert _lookup(service, current, question="design a cache?") is None
    assert _lookup(service, current, revision=2, question="How do you design a cache?") is None


@pytest.mark.parametrize("field,value", [("owner_user_id", "synthetic-other-owner"), ("session_id", "synthetic-other-session")])
def test_cross_identity_cache_lookup_is_rejected(field, value):
    service, current, reads = _service()
    _prefetch(service)
    setattr(current, field, value)
    kwargs = {"user_id": current.owner_user_id, "session_id": current.session_id}
    assert _lookup(service, current, **kwargs) is None
    assert len(reads) == 2


def test_same_revision_old_materials_cannot_overwrite_a_new_result():
    service, current, _ = _service()
    old_started = threading.Event()
    release_old = threading.Event()

    def retrieve(*, question, session, **_kwargs):
        version = session.material_binding.bound_documents[0].document_version_id
        if version == "synthetic-v1":
            old_started.set()
            assert release_old.wait(timeout=2)
        return _context(question, version)

    service._retrieve_context = retrieve
    old = threading.Thread(target=_prefetch, args=(service,))
    old.start()
    assert old_started.wait(timeout=2)
    current.material_binding.bound_documents[0].document_version_id = "synthetic-v2"
    _prefetch(service)
    release_old.set()
    old.join(timeout=2)
    assert not old.is_alive()
    assert _lookup(service, current).chunks[0].metadata["documentVersionId"] == "synthetic-v2"


def test_changed_materials_at_commit_are_not_cached():
    service, current, reads = _service()

    def retrieve(**_kwargs):
        current.material_binding.bound_documents[0].document_version_id = "synthetic-v2"
        return _context()

    service._retrieve_context = retrieve
    _prefetch(service)
    assert _lookup(service, current) is None
    assert not service._prepared_context
    assert len(reads) == 2


def test_completed_and_inflight_equivalent_work_is_reused():
    service, current, _ = _service()
    started = threading.Event()
    release = threading.Event()
    retrievals = []

    def retrieve(**_kwargs):
        retrievals.append(1)
        started.set()
        assert release.wait(timeout=2)
        return _context()

    service._retrieve_context = retrieve
    first = threading.Thread(target=_prefetch, args=(service,))
    first.start()
    assert started.wait(timeout=2)
    _prefetch(service)
    assert retrievals == [1]
    release.set()
    first.join(timeout=2)
    assert not first.is_alive()
    _prefetch(service)
    assert retrievals == [1]
    assert _lookup(service, current) is not None


def test_cancelled_scheduling_token_skips_reads_and_discards_running_results():
    service, current, reads = _service()
    _prefetch(service, is_current=lambda: False)
    assert not reads
    allowed = [True]

    def retrieve(**_kwargs):
        allowed[0] = False
        return _context()

    service._retrieve_context = retrieve
    _prefetch(service, is_current=lambda: allowed[0])
    assert _lookup(service, current) is None
    assert len(reads) == 1, "superseded work must skip the completion session read"


def test_same_revision_valid_generation_does_not_reuse_revoked_inflight_work():
    service, current, _ = _service()
    started = threading.Event()
    release = threading.Event()
    old_allowed = [True]
    retrievals = []

    def retrieve(**_kwargs):
        retrievals.append(1)
        if len(retrievals) == 1:
            started.set()
            assert release.wait(timeout=2)
        return _context(version=f"synthetic-result-{len(retrievals)}")

    service._retrieve_context = retrieve
    first = threading.Thread(target=_prefetch, args=(service,), kwargs={"is_current": lambda: old_allowed[0]})
    first.start()
    assert started.wait(timeout=2)
    old_allowed[0] = False
    _prefetch(service, is_current=lambda: True)
    release.set()
    first.join(timeout=2)
    assert not first.is_alive()
    assert len(retrievals) == 2
    assert _lookup(service, current).context_text == "synthetic:synthetic-result-2"


def test_cache_and_running_generation_expiry_cannot_be_resurrected(monkeypatch):
    now = [100_000]
    monkeypatch.setattr("app.services.chat_service._now_ms", lambda: now[0])
    service, current, _ = _service()
    _prefetch(service)
    now[0] += 60_000
    assert _lookup(service, current) is None
    assert not service._prepared_context and not service._latest_prefetch_revision

    def retrieve(**_kwargs):
        now[0] += 60_000
        return _context()

    service._retrieve_context = retrieve
    _prefetch(service)
    assert not service._prepared_context and not service._latest_prefetch_revision


def test_cache_and_generation_tracking_stay_bounded():
    service, current, _ = _service()
    for index in range(200):
        service.prefetch_question_context(
            user_id=current.owner_user_id, session_id=current.session_id,
            question_id=f"synthetic-question-{index}", revision=1, question=f"合成问题{index}",
        )
    assert len(service._prepared_context) == 128
    assert len(service._latest_prefetch_revision) == 128
    assert not any(key[2] == "synthetic-question-0" for key in service._prepared_context)


def test_evicted_running_generation_cannot_publish_after_completion():
    service, current, _ = _service()
    started = threading.Event()
    release = threading.Event()

    def retrieve(*, question, **_kwargs):
        if question == "合成问题":
            started.set()
            assert release.wait(timeout=3)
        return _context(question)

    service._retrieve_context = retrieve
    old = threading.Thread(target=_prefetch, args=(service,))
    old.start()
    assert started.wait(timeout=2)
    for index in range(128):
        service.prefetch_question_context(
            user_id=current.owner_user_id, session_id=current.session_id,
            question_id=f"synthetic-other-question-{index}", revision=1, question=f"其它合成问题{index}",
        )
    release.set()
    old.join(timeout=2)
    assert not old.is_alive()
    assert _lookup(service, current) is None
    assert len(service._prepared_context) == 128


@pytest.mark.parametrize("status,mode", [("ended", "interview"), ("preparing", "interview"), ("live", "mock")])
def test_non_live_or_mock_sessions_do_not_prefetch(status, mode):
    service, current, _ = _service()
    current.status, current.session_mode = status, mode
    service._retrieve_context = lambda **_kwargs: pytest.fail("ineligible session must not retrieve")
    _prefetch(service)
    assert not service._prepared_context


def test_failed_optional_retrieval_is_not_cached_and_logs_no_content(caplog):
    service, current, _ = _service()

    def failed(**_kwargs):
        raise RuntimeError("synthetic-private-content-must-not-be-logged")

    service._retrieve_context = failed
    with caplog.at_level(logging.INFO):
        _prefetch(service, question="synthetic-question-content-must-not-be-logged")
    assert not service._prepared_context
    assert "synthetic-private-content-must-not-be-logged" not in caplog.text
    assert "synthetic-question-content-must-not-be-logged" not in caplog.text
    assert "chat.question_prefetch_skipped" in caplog.text
    assert _lookup(service, current) is None


def test_real_retrieval_failure_is_not_reclassified_as_successful_empty_prefetch(monkeypatch):
    service, current, _ = _service()
    service._retrieve_context = ChatService._retrieve_context.__get__(service, ChatService)
    service.retrieval_service = SimpleNamespace(retrieve=lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("synthetic")))
    monkeypatch.setattr(service, "_log", lambda *_args, **_kwargs: None)
    _prefetch(service)
    assert not service._prepared_context
    # Existing formal-answer degradation remains available with its default.
    assert service._retrieve_context(user_id=current.owner_user_id, session=current, question="合成问题").chunks == []


def test_slow_prefetch_does_not_block_cache_miss_or_add_a_click_session_read():
    service, current, reads = _service()
    started = threading.Event()
    release = threading.Event()
    lookup_finished = threading.Event()
    outcomes = []

    def retrieve(**_kwargs):
        started.set()
        assert release.wait(timeout=2)
        return _context()

    service._retrieve_context = retrieve
    pending = threading.Thread(target=_prefetch, args=(service,))
    pending.start()
    assert started.wait(timeout=2)

    def click_lookup():
        outcomes.append(_lookup(service, current))
        lookup_finished.set()

    click = threading.Thread(target=click_lookup)
    click.start()
    assert lookup_finished.wait(timeout=0.5), "optional retrieval must not block a cache miss"
    assert outcomes == [None]
    assert len(reads) == 1
    release.set()
    click.join(timeout=2)
    pending.join(timeout=2)
    assert not pending.is_alive() and not click.is_alive()


def test_revocation_at_commit_boundary_cannot_publish_valid_cached_evidence():
    service, current, reads = _service()
    calls = []
    allowed = [True]

    def is_current():
        # Every scheduling callback, including post-write checks, is outside the
        # Chat cache lock so it cannot hold explicit lookup behind optional work.
        acquired = service._prepared_context_lock.acquire(blocking=False)
        assert acquired
        service._prepared_context_lock.release()
        calls.append(1)
        if len(calls) == 5:
            # Model revocation immediately after the last pre-write observation.
            allowed[0] = False
            return True
        return allowed[0]

    _prefetch(service, is_current=is_current)
    assert len(calls) == 6
    assert not service._prepared_context
    assert _lookup(service, current) is None
    assert len(reads) == 2


def test_post_write_revocation_cleanup_does_not_remove_a_replacement_generation():
    service, current, _ = _service()
    calls = []
    allowed = [True]

    def is_current():
        calls.append(1)
        if len(calls) == 6:
            allowed[0] = False
            current.material_binding.bound_documents[0].document_version_id = "synthetic-v2"
            service._retrieve_context = lambda *, question, **_kwargs: _context(question, "synthetic-v2")
            _prefetch(service, is_current=lambda: True)
        return allowed[0]

    _prefetch(service, is_current=is_current)
    assert _lookup(service, current).chunks[0].metadata["documentVersionId"] == "synthetic-v2"


def test_lookup_rejects_revoked_preparation_without_a_session_read_or_cache_lock_callback():
    service, current, reads = _service()
    allowed = [True]

    def is_current():
        acquired = service._prepared_context_lock.acquire(blocking=False)
        assert acquired
        service._prepared_context_lock.release()
        return allowed[0]

    _prefetch(service, is_current=is_current)
    assert _lookup(service, current) is not None
    allowed[0] = False
    assert _lookup(service, current) is None
    assert not service._prepared_context
    assert len(reads) == 2


def test_optional_scheduling_guard_failure_does_not_break_explicit_cache_lookup():
    service, current, _ = _service()
    fail = [False]

    def is_current():
        if fail[0]:
            raise RuntimeError("synthetic scheduling state unavailable")
        return True

    _prefetch(service, is_current=is_current)
    fail[0] = True
    assert _lookup(service, current) is None


def test_new_valid_token_reprepares_same_revision_after_old_cached_guard_is_revoked():
    service, current, _ = _service()
    allowed = [True]
    _prefetch(service, is_current=lambda: allowed[0])
    allowed[0] = False
    retrievals = []

    def retrieve(**_kwargs):
        retrievals.append(1)
        return _context(version="synthetic-fresh-result")

    service._retrieve_context = retrieve
    _prefetch(service, is_current=lambda: True)
    assert retrievals == [1]
    assert _lookup(service, current).context_text == "synthetic:synthetic-fresh-result"
