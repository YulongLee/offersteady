"""Capture lifecycle serialization with synthetic state and no outside services."""
import asyncio
from collections import deque
import threading
from types import SimpleNamespace
from unittest.mock import Mock

from fastapi import FastAPI, Request
import pytest

from app.core.errors import DomainRequestError
from app.modules import realtime_speech as routes
from app.modules import session as session_routes
from app.schemas.realtime_speech import RealtimeCaptureControlRequest
from app.schemas.session import SessionCommandRequest, SupersedeActiveSessionRequest
from app.services.cn_realtime_io_executor import CnRealtimeIoExecutor
from app.services.realtime_speech_service import RealtimeSpeechService


def target(edition="global"):
    service = object.__new__(RealtimeSpeechService)
    service.settings = SimpleNamespace(product_edition=edition)
    session = SimpleNamespace(session_id="synthetic-session", session_mode="interview", status="live", interview_language="zh-CN", interview_audio_mode="computer")
    new_session = SimpleNamespace(**{**vars(session), "session_id": "synthetic-new", "status": "preparing"})
    seen = []
    def get_session(**kwargs):
        record = new_session if kwargs["session_id"] == "synthetic-new" else session
        seen.append(("read", record.status))
        return record
    def end_session(**kwargs):
        session.status = "ended"
        return session
    service.session_service = SimpleNamespace(get_session=get_session, touch_activity=Mock(), end_session=end_session,
        list_sessions=lambda **kwargs: [session] if session.status == "live" else [])
    service._frame_worker_lock = threading.Lock()
    service._session_cleanup_locks = {}
    service._session_cleanup_lock_users = {}
    service._retired_session_ids = set()
    service._retired_session_order = deque(maxlen=1024)
    service._capture_control_cache = {}
    service._prewarm_metrics_lock = threading.Lock()
    service._prewarm_ready_by_session = {}
    service._prewarm_ready_at_by_session = {}
    service._session_language_cache = {}
    service._session_audio_mode_cache = {}
    service._session_activity_lock = threading.Lock()
    service._session_last_activity_ms = {}
    service._session_owners = {}
    service.capture_control_state = lambda **kwargs: service._capture_control_cache.get("synthetic-session", "capturing")
    service._save_event = lambda **kwargs: seen.append(("event", kwargs["payload"].get("action", kwargs["payload"].get("status"))))
    service._settle_realtime_minute = Mock(return_value=True)
    service._stop_realtime_metering = Mock()
    service._ensure_realtime_metering = Mock()
    service._prewarm_asr_session = Mock()
    service.asr_gateway = SimpleNamespace(close_session=Mock(return_value=1))
    service.repository = SimpleNamespace(list_session_desktop_bindings_for_user=lambda **kwargs: [],
        list_publishers_for_session=lambda **kwargs: [], clear_session_runtime=lambda **kwargs: {})
    service._reset_realtime_session = lambda **kwargs: {}
    service._invalidate_control_query_cache = Mock()
    service._record_reclamation = Mock()
    service._log = Mock()
    return service, session, seen


async def started(event):
    assert await asyncio.wait_for(asyncio.to_thread(event.wait, 1), 2)


def test_pause_and_resume_are_serialized_while_main_loop_remains_responsive(monkeypatch):
    async def scenario():
        executor = CnRealtimeIoExecutor()
        app = FastAPI();app.state.cn_realtime_io_executor = executor
        request = Request({"type": "http", "app": app})
        service, session, seen = target()
        begin, release = threading.Event(), threading.Event()
        def slow_close(**kwargs):
            begin.set()
            assert release.wait(2)
        service.asr_gateway.close_session = slow_close
        monkeypatch.setattr(routes, "resolve_owned_user_id", lambda **kwargs: "synthetic-owner")
        def run(action):
            return routes.control_session_capture("synthetic-session", request,
                RealtimeCaptureControlRequest(userId="synthetic-owner", action=action), None, service)
        pause = asyncio.create_task(run("pause"))
        try:
            await started(begin)
            resume = asyncio.create_task(run("resume"))
            await asyncio.sleep(.01)
            assert not resume.done()
            assert seen == [("read", "live"), ("event", "pause")]
            assert await asyncio.wait_for(asyncio.to_thread(lambda: 7), .5) == 7
            release.set()
            assert (await pause).data["captureState"] == "paused"
            assert (await resume).data["captureState"] == "capturing"
            assert seen == [("read", "live"), ("event", "pause"), ("read", "live"), ("event", "resume")]
            service._settle_realtime_minute.assert_called_once()
            assert service._session_cleanup_locks == service._session_cleanup_lock_users == {}
        finally:
            release.set()
            executor.shutdown()
    asyncio.run(scenario())


def test_end_transaction_wins_before_late_resume_and_cannot_be_revived():
    async def scenario():
        service, session, seen = target()
        begin, release = threading.Event(), threading.Event()
        def end(**kwargs):
            begin.set()
            assert release.wait(2)
            session.status = "ended"
            return session
        service.session_service.end_session = end
        ending = asyncio.create_task(asyncio.to_thread(service.terminate_session_for_admin,
            user_id="synthetic-owner", session_id="synthetic-session"))
        try:
            await started(begin)
            resume = asyncio.create_task(asyncio.to_thread(service.control_capture,
                user_id="synthetic-owner", session_id="synthetic-session", action="resume"))
            await asyncio.sleep(.01)
            assert not resume.done()
            release.set()
            await ending
            with pytest.raises(DomainRequestError) as failure:
                await resume
            assert failure.value.status_code == 409 and failure.value.error_code == "session_not_live"
            assert session.status == "ended"
            service._settle_realtime_minute.assert_not_called()
            service._ensure_realtime_metering.assert_not_called()
            service._prewarm_asr_session.assert_not_called()
            assert service._session_cleanup_locks == service._session_cleanup_lock_users == {}
        finally:
            release.set()
    asyncio.run(scenario())


def test_resume_billing_error_retains_original_status_code_and_capture_state():
    service, session, seen = target()
    service._capture_control_cache["synthetic-session"] = "paused"
    service._settle_realtime_minute.return_value = False
    with pytest.raises(DomainRequestError) as failure:
        service.control_capture(user_id="synthetic-owner", session_id="synthetic-session", action="resume")
    assert failure.value.status_code == 402
    assert failure.value.error_code == "realtime_minute_insufficient_balance"
    assert service._capture_control_cache["synthetic-session"] == "paused"
    service.session_service.touch_activity.assert_not_called()
    service._ensure_realtime_metering.assert_not_called()
    assert service._session_cleanup_locks == service._session_cleanup_lock_users == {}


def test_global_capture_keeps_original_body_without_new_cleanup_lock():
    service, session, seen = target("cn")
    service._acquire_session_cleanup_lock = Mock(side_effect=AssertionError("Global must not use CN lock"))
    assert service.control_capture(user_id="synthetic-owner", session_id="synthetic-session", action="pause") == {
        "sessionId": "synthetic-session", "captureState": "paused"}
    service._acquire_session_cleanup_lock.assert_not_called()
    service.asr_gateway.close_session.assert_called_once()


@pytest.mark.parametrize("edition", ["global", "cn"])
@pytest.mark.parametrize("action", ["pause", "resume"])
def test_actual_capture_instance_rejects_mock_before_any_side_effect(edition, action):
    service, session, seen = target(edition)
    session.session_mode = "mock"
    with pytest.raises(DomainRequestError) as failure:
        service.control_capture(user_id="synthetic-owner", session_id="synthetic-session", action=action)
    assert failure.value.status_code == 409
    assert failure.value.error_code == "mock_dedicated_command_required"
    assert seen == [("read", "live")]
    service._settle_realtime_minute.assert_not_called()
    service._ensure_realtime_metering.assert_not_called()
    service._stop_realtime_metering.assert_not_called()
    service.asr_gateway.close_session.assert_not_called()
    service.session_service.touch_activity.assert_not_called()
    assert service._session_cleanup_locks == service._session_cleanup_lock_users == {}


@pytest.mark.parametrize("entry", ["end", "supersede"])
def test_real_session_close_route_waits_for_pause_off_loop(monkeypatch, entry):
    async def scenario():
        executor = CnRealtimeIoExecutor()
        app = FastAPI();app.state.cn_realtime_io_executor = executor
        request = Request({"type": "http", "app": app})
        service, session, seen = target()
        begin, release = threading.Event(), threading.Event()
        def close(**kwargs):
            begin.set()
            assert release.wait(2)
        service.asr_gateway.close_session = close
        monkeypatch.setattr(routes, "resolve_owned_user_id", lambda **kwargs: "synthetic-owner")
        monkeypatch.setattr(session_routes, "resolve_owned_user_id", lambda **kwargs: "synthetic-owner")
        monkeypatch.setattr(session_routes, "_to_session_response", lambda record: {"status": record.status})
        pause = asyncio.create_task(routes.control_session_capture("synthetic-session", request,
            RealtimeCaptureControlRequest(userId="synthetic-owner", action="pause"), None, service))
        try:
            await started(begin)
            if entry == "end":
                closing = asyncio.create_task(session_routes.end_session("synthetic-session", request,
                    SessionCommandRequest(userId="synthetic-owner"), None, service))
            else:
                closing = asyncio.create_task(session_routes.supersede_active_sessions("synthetic-new", request,
                    SupersedeActiveSessionRequest(userId="synthetic-owner", expectedPreviousSessionId="synthetic-session"), None, service))
            await asyncio.sleep(.01)
            assert not closing.done() and session.status == "live"
            assert await asyncio.wait_for(asyncio.to_thread(lambda: 29), .5) == 29
            release.set()
            await pause
            response = await closing
            assert response.success and session.status == "ended"
            if entry == "supersede":
                assert response.data.retired_session_ids == ["synthetic-session"]
            assert service._session_cleanup_locks == service._session_cleanup_lock_users == {}
        finally:
            release.set()
            executor.shutdown()
    asyncio.run(scenario())


@pytest.mark.parametrize("edition", ["global", "cn"])
def test_supersede_changed_expected_session_retains_original_error(monkeypatch, edition):
    async def scenario():
        executor = CnRealtimeIoExecutor()
        app = FastAPI();app.state.cn_realtime_io_executor = executor
        service, session, seen = target(edition)
        monkeypatch.setattr(session_routes, "resolve_owned_user_id", lambda **kwargs: "synthetic-owner")
        try:
            with pytest.raises(DomainRequestError) as failure:
                await session_routes.supersede_active_sessions("synthetic-new", Request({"type": "http", "app": app}),
                    SupersedeActiveSessionRequest(userId="synthetic-owner", expectedPreviousSessionId="changed-session"), None, service)
            assert failure.value.status_code == 409 and failure.value.error_code == "active_interview_changed"
            assert session.status == "live"
            assert executor.diagnostics()["lifecycle"]["submitted"] == int(edition == "global")
        finally:
            executor.shutdown()
    asyncio.run(scenario())


@pytest.mark.parametrize("edition", ["global", "cn"])
def test_end_still_denies_mock_before_termination(monkeypatch, edition):
    async def scenario():
        executor = CnRealtimeIoExecutor()
        app = FastAPI();app.state.cn_realtime_io_executor = executor
        service, session, seen = target(edition)
        session.session_mode = "mock"
        service.terminate_session_for_admin = Mock(side_effect=AssertionError("mock must be denied"))
        monkeypatch.setattr(session_routes, "resolve_owned_user_id", lambda **kwargs: "synthetic-owner")
        try:
            with pytest.raises(DomainRequestError) as failure:
                await session_routes.end_session("synthetic-session", Request({"type": "http", "app": app}),
                    SessionCommandRequest(userId="synthetic-owner"), None, service)
            assert failure.value.status_code == 409
            service.terminate_session_for_admin.assert_not_called()
        finally:
            executor.shutdown()
    asyncio.run(scenario())
