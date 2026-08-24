from types import SimpleNamespace

from app.services.dashscope_realtime_asr_gateway import DashScopeRealtimeAsrGateway, _SourceRealtimeSession


class FakeConnection:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


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

    gateway.warm_session(session_id="session-warm", source_kind="system")

    assert len(captured) == 1
    frame = captured[0]
    assert frame.session_id == "session-warm"
    assert frame.source_kind == "system"
    assert frame.audio_bytes == b""
    assert frame.revision == 0
