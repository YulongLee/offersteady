"""Synthetic state IO regressions; no providers, production data or databases."""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import logging
import threading
from types import SimpleNamespace
from unittest.mock import Mock, call

from fastapi import FastAPI, HTTPException
import httpx
import pytest

from app import deps
from app.core.config import Settings
from app.core.errors import DomainRequestError, install_exception_handlers
from app.modules import realtime_speech, session, web
from app.ports.authentication import AuthenticatedRequestContext
from app.ports.document_repository import DocumentRecord
from app.ports.interview_session import SessionBoundDocument
from app.services.interview_session_repository import InMemoryInterviewSessionRepository
from app.services.realtime_speech_service import RealtimeSpeechService
from app.services.session_service import SessionService


NOW = 1_800_000_000_000
OWNER = "synthetic-state-owner"


def _document(document_id="synthetic-material", *, owner=OWNER, **changes):
    record = DocumentRecord(
        document_id=document_id, owner_user_id=owner, document_kind="knowledge",
        display_name="Synthetic material", file_kind="txt", content_type="text/plain",
        size_bytes=12, object_key=f"synthetic/{document_id}", status="ready",
        knowledge_collection_id="synthetic-collection", processing_requested_at_ms=None,
        deleted_at_ms=None, created_at_ms=NOW, updated_at_ms=NOW,
        summary="Synthetic summary", document_version_id="synthetic-version-1", index_state="indexed",
    )
    return replace(record, **changes)


def _services(monkeypatch):
    monkeypatch.setattr("app.services.session_service._now_ms", lambda: NOW)
    settings = Settings(_env_file=None, interview_idle_warning_seconds=60,
                        interview_idle_timeout_seconds=120)
    repository = InMemoryInterviewSessionRepository()
    documents = Mock()
    documents.get_by_id.return_value = _document()
    sessions = SessionService(settings=settings, repository=repository, document_repository=documents)
    return sessions, repository, documents


def _bound_session(sessions, repository, *, owner=OWNER, document_ids=("synthetic-material",), status="live"):
    created = sessions.create_session(user_id=owner, title="Synthetic state interview")
    bound = [SessionBoundDocument(document_id=document_id, document_kind="knowledge",
             display_name="Synthetic material", status="ready", active=True,
             document_version_id="synthetic-version-1", index_state="indexed")
             for document_id in document_ids]
    record = replace(created, status=status, started_at_ms=None if status == "preparing" else NOW,
                     material_binding=replace(created.material_binding, revision=1, bound_documents=bound))
    repository.save_session(record)
    return record


@pytest.mark.parametrize("status", ["preparing", "live", "ended"])
@pytest.mark.parametrize("offset", [0, 59_999, 60_000, 119_999, 120_000])
def test_idle_projection_preserves_all_fields_and_boundaries_without_material_reads(monkeypatch, status, offset):
    sessions, repository, documents = _services(monkeypatch)
    record = _bound_session(sessions, repository, document_ids=tuple(f"synthetic-{i}" for i in range(25)), status=status)
    projection = Mock(wraps=repository.get_heartbeat_state)
    monkeypatch.setattr(repository, "get_heartbeat_state", projection)
    monkeypatch.setattr(repository, "get_session", Mock(side_effect=AssertionError("full session read")))
    monkeypatch.setattr(repository, "save_session", Mock(side_effect=AssertionError("unexpected session write")))
    expected = sessions._idle_status_from_session(session=record, at_ms=NOW + offset)
    actual = sessions.idle_status(user_id=OWNER, session_id=record.session_id, at_ms=NOW + offset)
    assert actual == expected
    assert set(actual) == {"sessionId", "state", "lastActivityAtMs", "warningAtMs", "expiresAtMs", "remainingMs"}
    projection.assert_called_once_with(record.session_id)
    documents.get_by_id.assert_not_called()


@pytest.mark.parametrize("missing, owner, code", [(False, "synthetic-other-owner", 403), (True, OWNER, 404)])
def test_idle_projection_rejects_foreign_or_absent_before_material_reads(monkeypatch, missing, owner, code):
    sessions, repository, documents = _services(monkeypatch)
    record = _bound_session(sessions, repository)
    if missing:
        repository.sessions.clear()
    before = dict(repository.sessions)
    with pytest.raises(DomainRequestError) as caught:
        sessions.idle_status(user_id=owner, session_id=record.session_id)
    assert caught.value.status_code == code
    assert caught.value.feature == "session"
    assert repository.sessions == before
    documents.get_by_id.assert_not_called()


def test_idle_projection_observes_end_and_deletion_on_next_read(monkeypatch):
    sessions, repository, documents = _services(monkeypatch)
    record = _bound_session(sessions, repository)
    assert sessions.idle_status(user_id=OWNER, session_id=record.session_id)["state"] == "active"
    repository.save_session(replace(record, status="ended"))
    assert sessions.idle_status(user_id=OWNER, session_id=record.session_id)["state"] == "ended"
    del repository.sessions[record.session_id]
    with pytest.raises(DomainRequestError) as caught:
        sessions.idle_status(user_id=OWNER, session_id=record.session_id)
    assert caught.value.status_code == 404
    documents.get_by_id.assert_not_called()


@pytest.mark.parametrize("cleanup_fails", [False, True])
def test_idle_expiry_still_uses_original_termination_and_propagates_failure(monkeypatch, cleanup_fails):
    sessions, repository, documents = _services(monkeypatch)
    record = _bound_session(sessions, repository)
    repository.save_session(replace(record, last_activity_at_ms=NOW - 120_000))
    realtime = object.__new__(RealtimeSpeechService)
    realtime.session_service = sessions
    realtime.terminate_session_for_admin = Mock(return_value={"settled": True, "releasedBindings": 1})
    if cleanup_fails:
        realtime.terminate_session_for_admin.side_effect = RuntimeError("synthetic cleanup failure")
        with pytest.raises(RuntimeError, match="synthetic cleanup failure"):
            realtime.reconcile_idle_session(user_id=OWNER, session_id=record.session_id)
    else:
        result = realtime.reconcile_idle_session(user_id=OWNER, session_id=record.session_id)
        assert result["state"] == "ended" and result["autoEnded"] is True
        assert result["release"] == {"settled": True, "releasedBindings": 1}
    realtime.terminate_session_for_admin.assert_called_once_with(
        user_id=OWNER, session_id=record.session_id, reason="idle-timeout")
    documents.get_by_id.assert_not_called()


def test_list_reads_each_shared_and_missing_material_once_per_call(monkeypatch):
    sessions, repository, documents = _services(monkeypatch)
    records = [
        _bound_session(sessions, repository, document_ids=("synthetic-material", "synthetic-missing"))
        for _ in range(4)
    ]
    documents.get_by_id.side_effect = lambda key: _document() if key == "synthetic-material" else None
    result = sessions.list_sessions(user_id=OWNER)
    assert {item.session_id for item in result} == {item.session_id for item in records}
    assert documents.get_by_id.call_args_list == [call("synthetic-material"), call("synthetic-missing")]
    for record in result:
        assert [item.document_id for item in record.material_binding.bound_documents] == ["synthetic-material", "synthetic-missing"]
        assert [item.active for item in record.material_binding.bound_documents] == [True, False]
        assert record.material_binding.bound_documents[1].status == "deleted"
    sessions.list_sessions(user_id=OWNER)
    assert documents.get_by_id.call_count == 4


@pytest.mark.parametrize("change", [
    {"status": "deleting"}, {"status": "deleted", "deleted_at_ms": NOW + 1},
    {"status": "processing"}, {"index_state": "disabled"},
    {"document_version_id": "synthetic-version-2", "display_name": "Updated synthetic material", "summary": "Updated summary"},
    None,
])
def test_new_list_call_reflects_changed_material_state(monkeypatch, change):
    sessions, repository, documents = _services(monkeypatch)
    for _ in range(3):
        _bound_session(sessions, repository)
    first = sessions.list_sessions(user_id=OWNER)
    assert all(item.material_binding.bound_documents[0].active for item in first)
    updated = _document(**change) if change is not None else None
    documents.get_by_id.return_value = updated
    second = sessions.list_sessions(user_id=OWNER)
    assert documents.get_by_id.call_count == 2
    for record in second:
        bound = record.material_binding.bound_documents[0]
        assert bound.document_id == "synthetic-material"
        assert bound.status == (updated.status if updated else "deleted")
        assert bound.active is bool(updated and updated.status == "ready" and updated.index_state in {None, "indexed"})
        if updated:
            assert (bound.document_version_id, bound.display_name, bound.summary, bound.index_state) == (
                updated.document_version_id, updated.display_name, updated.summary, updated.index_state)


def test_complete_get_reads_fresh_material_and_checks_owner_first(monkeypatch):
    sessions, repository, documents = _services(monkeypatch)
    record = _bound_session(sessions, repository)
    first = sessions.get_session(user_id=OWNER, session_id=record.session_id)
    documents.get_by_id.return_value = None
    second = sessions.get_session(user_id=OWNER, session_id=record.session_id)
    assert first.material_binding.bound_documents[0].active is True
    assert second.material_binding.bound_documents[0].active is False
    assert documents.get_by_id.call_count == 2
    with pytest.raises(DomainRequestError) as caught:
        sessions.get_session(user_id="synthetic-other-owner", session_id=record.session_id)
    assert caught.value.status_code == 403
    assert documents.get_by_id.call_count == 2


def test_concurrent_lists_keep_owner_and_material_reuse_local(monkeypatch):
    sessions, repository, documents = _services(monkeypatch)
    owners = ["synthetic-owner-a", "synthetic-owner-b"]
    for owner in owners:
        for _ in range(3):
            _bound_session(sessions, repository, owner=owner, document_ids=(f"{owner}-material",))
    documents.get_by_id.side_effect = lambda key: _document(key, owner=key.removesuffix("-material"))
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda owner: sessions.list_sessions(user_id=owner), owners))
    assert documents.get_by_id.call_count == 2
    for owner, records in zip(owners, results, strict=True):
        assert len(records) == 3
        assert all(record.owner_user_id == owner for record in records)
        assert all(record.material_binding.bound_documents[0].document_id == f"{owner}-material" for record in records)


def test_mock_list_preserves_version_owned_by_mock_state(monkeypatch):
    sessions, repository, documents = _services(monkeypatch)
    record = _bound_session(sessions, repository)
    repository.save_session(replace(record, session_mode="mock"))
    documents.get_by_id.return_value = None
    result = sessions.list_sessions(user_id=OWNER)
    assert result[0].material_binding == record.material_binding
    documents.get_by_id.assert_not_called()


def test_state_read_http_contracts_and_owner_errors_remain_unchanged(monkeypatch):
    sessions, repository, _ = _services(monkeypatch)
    record = _bound_session(sessions, repository)
    mock = _bound_session(sessions, repository)
    repository.save_session(replace(mock, session_mode="mock"))
    realtime = object.__new__(RealtimeSpeechService)
    realtime.session_service = sessions
    realtime.terminate_session_for_admin = Mock(side_effect=AssertionError("active session terminated"))
    app = FastAPI()
    app.include_router(session.router)
    settings = Settings(_env_file=None, environment="development")
    install_exception_handlers(app, settings=settings, logger=logging.getLogger("synthetic-state-contract"))
    app.dependency_overrides[deps.optional_authenticated_context] = lambda: None
    app.dependency_overrides[deps.session_service] = lambda: sessions
    app.dependency_overrides[deps.realtime_speech_service] = lambda: realtime
    monkeypatch.setattr(deps, "get_settings", lambda: settings)

    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://synthetic.local") as client:
            query = {"userId": OWNER}
            response = await client.get(f"/sessions/{record.session_id}", params=query)
            assert response.status_code == 200
            envelope = response.json()
            assert set(envelope) == {"success", "data", "error", "requestId", "meta"}
            assert envelope["success"] is True and envelope["error"] is None
            expected = session._to_session_response(sessions.get_session(user_id=OWNER, session_id=record.session_id))
            assert envelope["data"] == expected.model_dump(by_alias=True)
            listed = await client.get("/sessions", params=query)
            assert listed.status_code == 200
            assert listed.json()["data"] == [envelope["data"]]
            review = await client.get(f"/sessions/{record.session_id}/review", params=query)
            assert review.status_code == 409
            repository.save_session(replace(record, status="ended", ended_at_ms=NOW))
            review = await client.get(f"/sessions/{record.session_id}/review", params=query)
            assert review.status_code == 200 and review.json()["data"]["transcripts"] == []
            idle = await client.get(f"/sessions/{record.session_id}/idle-status", params=query)
            assert idle.status_code == 200
            assert idle.json()["data"] == sessions.idle_status(user_id=OWNER, session_id=record.session_id)
            for suffix in ("", "/review", "/idle-status"):
                denied = await client.get(f"/sessions/{record.session_id}{suffix}", params={"userId": "synthetic-other-owner"})
                assert denied.status_code == 403
                assert denied.json()["error"] == {
                    "code": "domain_request_error", "message": "不能查看其他用户的面试会话。",
                    "details": {"feature": "session", "action": "get", "errorCode": None},
                }
                absent = await client.get(f"/sessions/synthetic-absent{suffix}", params=query)
                assert absent.status_code == 404
                assert absent.json()["error"]["code"] == "domain_request_error"
                assert absent.json()["error"]["details"] == {"feature": "session", "action": "get", "errorCode": None}
            realtime.terminate_session_for_admin.assert_not_called()

    asyncio.run(exercise())


_STATE_READS = [
    ("/sessions?userId=" + OWNER, "list_sessions"),
    ("/sessions/synthetic-session?userId=" + OWNER, "get_session"),
    ("/sessions/synthetic-session/review?userId=" + OWNER, "get_review_transcripts"),
    ("/sessions/synthetic-session/idle-status?userId=" + OWNER, "reconcile_idle_session"),
    ("/web/state", "state_for_user"),
    ("/realtime-speech/sessions/synthetic-session/runtime?userId=" + OWNER, "get_runtime"),
    ("/realtime-speech/desktop-devices/last-used?userId=" + OWNER, "get_last_desktop_device_for_user"),
    ("/realtime-speech/desktop-devices", "list_desktop_devices_for_user"),
]


def _blocking_app(monkeypatch, method):
    started, release, finished = threading.Event(), threading.Event(), threading.Event()
    lock = threading.Lock()
    count = 0

    def read(**_kwargs):
        nonlocal count
        with lock:
            count += 1
            first = count == 1
        if first:
            started.set()
            try:
                if not release.wait(2):
                    raise AssertionError("synthetic blocking IO was not released")
            finally:
                finished.set()
        raise HTTPException(status_code=418, detail="synthetic state read error")

    fake = SimpleNamespace(**{method: read})
    app = FastAPI()
    for router in (session.router, web.router, realtime_speech.router):
        app.include_router(router)
    context = AuthenticatedRequestContext(user_id=OWNER, login_id="synthetic-login", auth_session_id="synthetic-auth")
    app.dependency_overrides[deps.optional_authenticated_context] = lambda: context
    app.dependency_overrides[deps.session_service] = lambda: fake
    app.dependency_overrides[deps.realtime_speech_service] = lambda: fake
    app.dependency_overrides[deps.billing_service] = lambda: fake
    if hasattr(deps, "usage_billing_service"):
        app.dependency_overrides[deps.usage_billing_service] = lambda: fake
    app.dependency_overrides[deps.document_read_service] = lambda: SimpleNamespace()
    monkeypatch.setattr(web, "authentication_service", lambda: SimpleNamespace(get_current_user=lambda **kwargs: None))

    @app.get("/synthetic-loop-sentinel")
    async def sentinel():
        return {"progressed": True}

    return app, started, release, finished


@pytest.mark.parametrize("path, method", _STATE_READS)
def test_slow_state_io_keeps_event_loop_responsive_and_recovers_after_error(monkeypatch, path, method):
    app, started, release, finished = _blocking_app(monkeypatch, method)

    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://synthetic.local") as client:
            slow = asyncio.create_task(client.get(path))
            try:
                assert await asyncio.wait_for(asyncio.to_thread(started.wait, 1), timeout=1.5)
                assert not finished.is_set(), "sync state IO blocked the request event loop"
                probe = await asyncio.wait_for(client.get("/synthetic-loop-sentinel"), timeout=0.5)
                assert probe.json() == {"progressed": True}
                assert not finished.is_set()
            finally:
                release.set()
            response = await asyncio.wait_for(slow, timeout=2)
            assert response.status_code == 418
            assert response.json() == {"detail": "synthetic state read error"}
            assert finished.is_set()
            later = await client.get(path)
            assert later.status_code == 418 and later.json() == response.json()

    asyncio.run(exercise())


def test_cancelled_state_request_releases_controlled_worker_and_next_request_recovers(monkeypatch):
    app, started, release, finished = _blocking_app(monkeypatch, "get_session")
    sessions, repository, _ = _services(monkeypatch)
    record = _bound_session(sessions, repository)

    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://synthetic.local") as client:
            slow = asyncio.create_task(client.get("/sessions/synthetic-session?userId=" + OWNER))
            try:
                assert await asyncio.wait_for(asyncio.to_thread(started.wait, 1), timeout=1.5)
                slow.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await slow
            finally:
                release.set()
            assert await asyncio.wait_for(asyncio.to_thread(finished.wait, 1), timeout=1.5)
            assert (await client.get("/synthetic-loop-sentinel")).status_code == 200
            app.dependency_overrides[deps.session_service] = lambda: sessions
            later = await client.get(f"/sessions/{record.session_id}", params={"userId": OWNER})
            assert later.status_code == 200 and later.json()["data"]["sessionId"] == record.session_id

    asyncio.run(exercise())
