from types import SimpleNamespace
import logging
import threading
import time

from app.core.config import Settings
from app.ports.realtime_speech import AudioFrame
from app.services.dashscope_realtime_asr_gateway import DashScopeRealtimeAsrGateway, _SourceRealtimeSession
from app.services.realtime_speech_service import RealtimeSpeechService


class FakeConnection:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


def language_frame(interview_language: str) -> AudioFrame:
    return AudioFrame(
        publisher_id="publisher-language",
        session_id="session-language",
        device_id="device-language",
        source_id="system-language",
        source_kind="system",
        segment_id="segment-language",
        revision=1,
        sequence=1,
        captured_at_ms=int(time.time() * 1000),
        started_at_ms=1,
        ended_at_ms=2,
        duration_ms=1,
        codec="pcm-s16le",
        sample_rate_hz=16_000,
        channels=1,
        is_final=False,
        audio_bytes=b"synthetic",
        interview_language=interview_language,  # type: ignore[arg-type]
    )


def test_stale_provider_session_is_closed_and_reported(monkeypatch) -> None:
    gateway = object.__new__(DashScopeRealtimeAsrGateway)
    gateway.settings = SimpleNamespace(realtime_asr_session_idle_seconds=30)
    gateway._source_sessions = {}
    gateway._idle_session_closures = {}
    gateway._connection_state_by_source = {}
    connection = FakeConnection()
    session = _SourceRealtimeSession(
        connection=connection,
        sample_rate_hz=16_000,
        created_at_monotonic=1.0,
        updated_at_monotonic=1.0,
        source_session_key="session-a:microphone",
        source_kind="microphone",
    )
    gateway._source_sessions[session.source_session_key] = session
    monkeypatch.setattr("app.services.dashscope_realtime_asr_gateway.time.monotonic", lambda: 40.0)

    gateway._sweep_stale_sessions_locked()

    assert gateway._source_sessions == {}
    assert connection.closed is True
    assert gateway._idle_session_closures["microphone"] == 1
    assert gateway._connection_state_by_source["microphone"] == "idle"


def test_persistent_provider_session_is_not_closed_only_because_interview_is_quiet(monkeypatch) -> None:
    gateway = object.__new__(DashScopeRealtimeAsrGateway)
    gateway.settings = SimpleNamespace(
        realtime_asr_session_idle_seconds=30,
        realtime_asr_persistent_sessions_enabled=True,
    )
    gateway._source_sessions = {}
    connection = FakeConnection()
    session = _SourceRealtimeSession(
        connection=connection,
        sample_rate_hz=16_000,
        created_at_monotonic=1.0,
        updated_at_monotonic=1.0,
        source_session_key="session-persistent:microphone",
        source_kind="microphone",
    )
    gateway._source_sessions[session.source_session_key] = session
    monkeypatch.setattr("app.services.dashscope_realtime_asr_gateway.time.monotonic", lambda: 3_601.0)

    gateway._sweep_stale_sessions_locked()

    assert gateway._source_sessions == {session.source_session_key: session}
    assert connection.closed is False


def test_close_session_only_closes_provider_connections_for_target_session() -> None:
    gateway = object.__new__(DashScopeRealtimeAsrGateway)
    gateway._source_sessions = {}
    gateway._source_sessions_lock = __import__("threading").Lock()
    gateway._connection_state_by_source = {}
    target_microphone = FakeConnection()
    target_system = FakeConnection()
    other_microphone = FakeConnection()
    for key, source_kind, connection in (
        ("session-target:microphone", "microphone", target_microphone),
        ("session-target:system", "system", target_system),
        ("session-other:microphone", "microphone", other_microphone),
    ):
        gateway._source_sessions[key] = _SourceRealtimeSession(
            connection=connection,
            sample_rate_hz=16_000,
            created_at_monotonic=1.0,
            updated_at_monotonic=1.0,
            source_session_key=key,
            source_kind=source_kind,
        )

    closed_count = gateway.close_session(session_id="session-target")

    assert closed_count == 2
    assert target_microphone.closed is True
    assert target_system.closed is True
    assert other_microphone.closed is False
    assert list(gateway._source_sessions) == ["session-other:microphone"]


def test_close_source_does_not_interrupt_the_other_channel() -> None:
    gateway = object.__new__(DashScopeRealtimeAsrGateway)
    gateway._source_sessions = {}
    gateway._source_sessions_lock = __import__("threading").Lock()
    gateway._connection_state_by_source = {}
    microphone = FakeConnection()
    system = FakeConnection()
    for source_kind, connection in (("microphone", microphone), ("system", system)):
        key = f"session-target:{source_kind}"
        gateway._source_sessions[key] = _SourceRealtimeSession(
            connection=connection,
            sample_rate_hz=16_000,
            created_at_monotonic=1.0,
            updated_at_monotonic=1.0,
            source_session_key=key,
            source_kind=source_kind,
        )

    assert gateway.close_source(session_id="session-target", source_kind="system") == 1
    assert system.closed is True
    assert microphone.closed is False
    assert list(gateway._source_sessions) == ["session-target:microphone"]


def test_warm_session_opens_provider_without_sending_audio(monkeypatch) -> None:
    gateway = object.__new__(DashScopeRealtimeAsrGateway)
    captured = []
    monkeypatch.setattr(gateway, "_get_or_create_source_session", lambda frame: captured.append(frame))

    gateway.warm_session(session_id="session-warm", source_kind="system", interview_language="en-US")

    assert len(captured) == 1
    frame = captured[0]
    assert frame.session_id == "session-warm"
    assert frame.source_kind == "system"
    assert frame.audio_bytes == b""
    assert frame.revision == 0
    assert frame.interview_language == "en-US"


def test_provider_payload_maps_closed_domain_languages() -> None:
    gateway = DashScopeRealtimeAsrGateway(Settings(realtime_asr_api_key="synthetic"), logging.getLogger("language-payload"))

    chinese, _ = gateway._session_update_payload(language_frame("zh-CN"))
    english, _ = gateway._session_update_payload(language_frame("en-US"))

    assert chinese["input_audio_transcription"] == {"language": "zh"}
    assert english["input_audio_transcription"] == {"language": "en"}


def test_provider_connection_is_not_reused_across_languages(monkeypatch) -> None:
    gateway = DashScopeRealtimeAsrGateway(Settings(realtime_asr_api_key="synthetic"), logging.getLogger("language-isolation"))
    first_connection = FakeConnection()
    second_connection = FakeConnection()
    connections = iter([first_connection, second_connection])
    monkeypatch.setattr(gateway, "_open_connection", lambda _frame: (next(connections), "manual"))
    monkeypatch.setattr(gateway, "_receive_events", lambda _session: None)

    english = gateway._get_or_create_source_session(language_frame("en-US"))
    chinese = gateway._get_or_create_source_session(language_frame("zh-CN"))

    assert english is not chinese
    assert first_connection.closed is True
    assert chinese.interview_language == "zh-CN"


def test_question_detection_uses_english_interrogatives_without_triggering_greetings() -> None:
    assert RealtimeSpeechService._looks_like_question(
        "Tell me about a difficult production incident you handled.", interview_language="en-US"
    )
    assert RealtimeSpeechService._looks_like_question(
        "Walk me through your rollback strategy", interview_language="en-US"
    )
    assert not RealtimeSpeechService._looks_like_question("Good morning", interview_language="en-US")
    assert not RealtimeSpeechService._looks_like_question("I worked on the deployment pipeline", interview_language="en-US")
