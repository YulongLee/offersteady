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
