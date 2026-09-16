from __future__ import annotations

from collections import deque
import logging
import threading
from types import SimpleNamespace

from app.core.config import Settings
from app.services.realtime_speech_service import RealtimeSpeechService
from app.services.screenshot_answer_service import InMemoryScreenshotUploadPort


def test_abandoned_screenshot_uploads_are_swept_after_expiry() -> None:
    port = InMemoryScreenshotUploadPort(
        Settings(_env_file=None, oss_upload_intent_ttl_seconds=1, public_web_base_url="https://example.test")
    )
    intent = port.create_upload_intent(
        user_id="user-1",
        session_id="session-1",
        filename="question.png",
        content_type="image/png",
    )
    port.store_uploaded_image_bytes(intent_id=intent.intent_id, payload=b"x" * 32)

    removed = port._sweep_expired(now_ms=intent.expires_at_ms + 1)

    assert removed == 1
    assert port.operational_diagnostics()["bufferedBytes"] == 0
    assert port.issued_intents == {}
    assert port.pending_upload_payloads == {}


def test_screenshot_session_release_removes_confirmed_images_and_is_idempotent() -> None:
    port = InMemoryScreenshotUploadPort(Settings(_env_file=None, public_web_base_url="https://example.test"))
    intent = port.create_upload_intent(
        user_id="user-1",
        session_id="session-1",
        filename="question.png",
        content_type="image/png",
    )
    port.store_uploaded_image_bytes(intent_id=intent.intent_id, payload=b"image")
    upload = port.confirm_uploaded_image(
        user_id="user-1",
        session_id="session-1",
        intent_id=intent.intent_id,
        object_key=intent.object_key,
        content_type="image/png",
        size_bytes=5,
    )

    assert port.release_session(session_id="session-1") == 2
    assert port.release_session(session_id="session-1") == 0
    assert port.operational_diagnostics()["bufferedBytes"] == 0
    assert port.uploaded_images == {}
    assert upload.image_id not in port._uploaded_image_sessions


def test_realtime_session_cleanup_drops_short_lived_indexes_and_keeps_other_sessions() -> None:
    service = object.__new__(RealtimeSpeechService)
    service.logger = logging.getLogger("resource-cleanup-test")
    service.screenshot_upload_port = InMemoryScreenshotUploadPort(Settings(_env_file=None))
    service._terminal_lock = threading.Lock()
    service._accepted_terminal_ids = {
        ("session-ended", "microphone"): {"terminal-1": 1},
        ("session-live", "microphone"): {"terminal-2": 1},
    }
    service._latest_source_generations = {
        ("session-ended", "microphone"): 1,
        ("session-live", "microphone"): 2,
    }
    service._counters_by_session_source = {
        ("session-ended", "microphone"): {"chunksProduced": 4},
        ("session-live", "microphone"): {"chunksProduced": 7},
    }
    service._segment_audio_lock = threading.Lock()
    service._segment_audio_buffers = {
        ("session-ended", "microphone", "segment-1"): {"audio": bytearray(b"audio")},
        ("session-live", "microphone", "segment-2"): {"audio": bytearray(b"audio")},
    }
    service._capture_control_cache = {"session-ended": "capturing", "session-live": "capturing"}
    service._session_language_cache = {"session-ended": "en-US", "session-live": "zh-CN"}
    service._auto_answer_active_candidates = {"session-ended": "candidate-1", "session-live": "candidate-2"}
    service._session_activity_lock = threading.Lock()
    service._session_last_activity_ms = {"session-ended": 100, "session-live": 200}
    service._session_owners = {"session-ended": "user-1", "session-live": "user-2"}
    service._session_cleanup_locks = {
        "session-ended": threading.Lock(),
        "session-live": threading.Lock(),
    }
    service._publisher_status_cache = {
        "publisher-ended": "closed",
        "publisher-live": "connected",
    }
    service.repository = SimpleNamespace(
        list_publishers_for_session=lambda *, session_id: (
            [SimpleNamespace(publisher_id="publisher-ended")] if session_id == "session-ended" else []
        )
    )
    service._stable_question_state = {
        ("session-ended", "question-1"): {"text": "old"},
        ("session-live", "question-2"): {"text": "live"},
    }
    service._trace_lock = threading.Lock()
    service._trace_records = {
        "trace-ended": {"sessionId": "session-ended"},
        "trace-live": {"sessionId": "session-live"},
    }
    service._trace_order = deque(["trace-ended", "trace-live"], maxlen=16)
    service._retired_session_ids = {"session-ended", "session-live"}

    service._clear_session_state_indexes(session_id="session-ended")

    assert all(key[0] != "session-ended" for key in service._accepted_terminal_ids)
    assert all(key[0] != "session-ended" for key in service._latest_source_generations)
    assert all(key[0] != "session-ended" for key in service._counters_by_session_source)
    assert all(key[0] != "session-ended" for key in service._segment_audio_buffers)
    assert "session-ended" not in service._capture_control_cache
    assert "session-ended" not in service._session_language_cache
    assert "session-ended" not in service._auto_answer_active_candidates
    assert "session-ended" not in service._session_last_activity_ms
    assert "session-ended" not in service._session_owners
    assert "session-ended" not in service._session_cleanup_locks
    assert "session-live" in service._session_cleanup_locks
    assert "publisher-ended" not in service._publisher_status_cache
    assert "publisher-live" in service._publisher_status_cache
    assert all(key[0] != "session-ended" for key in service._stable_question_state)
    assert "trace-ended" not in service._trace_records
    assert list(service._trace_order) == ["trace-live"]
    assert ("session-live", "microphone") in service._counters_by_session_source


def test_background_reaper_reclaims_expired_sessions_idempotently() -> None:
    service = object.__new__(RealtimeSpeechService)
    service.logger = logging.getLogger("resource-reaper-test")
    service._reaper_lock = threading.Lock()
    service._reaper_runs = 0
    service._reaper_reclaimed_sessions = 0
    service._reaper_failures = 0
    service._reaper_last_run_at_ms = None
    service._reaper_last_error_code = None
    expired = [SimpleNamespace(owner_user_id="user-1", session_id="idle-session")]
    calls: list[str] = []

    class SessionService:
        def list_idle_live_sessions(self):
            return expired if not calls else []

    service.session_service = SessionService()
    service.terminate_session_for_admin = lambda **kwargs: calls.append(kwargs["session_id"])

    assert service.reap_idle_sessions() == {"reclaimedSessions": 1, "failures": 0}
    assert service.reap_idle_sessions() == {"reclaimedSessions": 0, "failures": 0}
    assert calls == ["idle-session"]
    assert service._reaper_runs == 2
    assert service._reaper_reclaimed_sessions == 1


def test_reaper_does_not_terminate_active_sessions() -> None:
    service = object.__new__(RealtimeSpeechService)
    service.logger = logging.getLogger("resource-reaper-active-test")
    service._reaper_lock = threading.Lock()
    service._reaper_runs = 0
    service._reaper_reclaimed_sessions = 0
    service._reaper_failures = 0
    service._reaper_last_run_at_ms = None
    service._reaper_last_error_code = None

    class SessionService:
        def list_idle_live_sessions(self):
            return []

    service.session_service = SessionService()
    service.terminate_session_for_admin = lambda **kwargs: (_ for _ in ()).throw(AssertionError("active session terminated"))

    assert service.reap_idle_sessions() == {"reclaimedSessions": 0, "failures": 0}


def test_realtime_service_shutdown_closes_gateway_and_worker_pools_once() -> None:
    service = object.__new__(RealtimeSpeechService)
    service.logger = logging.getLogger("resource-shutdown-test")
    service._shutdown_lock = threading.Lock()
    service._shutdown_complete = False

    class Gateway:
        def __init__(self) -> None:
            self.closed = 0

        def close_all_sessions(self) -> int:
            self.closed += 1
            return 2

    class Executor:
        def __init__(self) -> None:
            self.shutdowns = 0

        def shutdown(self, *, wait: bool, cancel_futures: bool) -> None:
            assert wait is False
            assert cancel_futures is True
            self.shutdowns += 1

    service.asr_gateway = Gateway()
    service._asr_executor = Executor()
    service._cold_executor = Executor()

    service.shutdown()
    service.shutdown()

    assert service.asr_gateway.closed == 1
    assert service._asr_executor.shutdowns == 1
    assert service._cold_executor.shutdowns == 1
