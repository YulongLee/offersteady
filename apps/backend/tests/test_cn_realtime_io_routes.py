"""CN scheduling tests with synthetic transports and in-memory service doubles."""
from __future__ import annotations

import asyncio
import base64
import json
import threading
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import Mock

from fastapi import FastAPI, Request
import pytest
from starlette.websockets import WebSocketDisconnect

from app.core.errors import DomainRequestError
from app.modules import realtime_speech as routes
from app.ports.realtime_speech import RealtimePublisherRecord
from app.schemas.realtime_speech import CreateRealtimePublisherRequest, RealtimeFrameIngestRequest
from app.services.cn_realtime_io_executor import CnRealtimeIoExecutor


PUB = RealtimePublisherRecord("synthetic-publisher", "synthetic-token", "synthetic-session", "synthetic-owner",
                             "mixed", "synthetic-desktop", 1, 999999)


def frame(sequence=0, **updates):
    return {"type": "audio-frame", "deviceId": "synthetic-device", "sourceId": "synthetic-source",
            "sourceKind": "microphone", "segmentId": "synthetic-segment", "sequence": sequence,
            "revision": sequence + 1, "capturedAtMs": 1000, "startedAtMs": 1000, "endedAtMs": 1020,
            "durationMs": 20, "codec": "pcm-s16le", "sampleRateHz": 16000, "channels": 1,
            "isFinal": False, "audioBase64": base64.b64encode(b"synthetic-pcm").decode(), **updates}


class Socket:
    def __init__(self, app, frames=(), *, binary=False, **query):
        self.app = app
        self.query_params = {"token": PUB.token, "protocol": "2.0", "media": "binary-v1" if binary else "json-base64", **query}
        self.frames = list(frames)
        self.binary = binary
        self.sent = []
        self.closed = []
    async def accept(self):
        pass
    async def receive_json(self):
        if not self.frames:
            raise WebSocketDisconnect()
        return self.frames.pop(0)
    async def receive(self):
        payload = await self.receive_json()
        if self.binary:
            pcm = base64.b64decode(payload.pop("audioBase64"))
            header = json.dumps(payload).encode()
            return {"type": "websocket.receive", "bytes": len(header).to_bytes(4, "big") + header + pcm}
        return {"type": "websocket.receive", "text": json.dumps(payload)}
    async def send_json(self, payload):
        self.sent.append(payload)
    async def close(self, **kwargs):
        self.closed.append(kwargs)


def target(edition="cn"):
    values = []
    def note(name, result=None):
        def operation(**kwargs):
            values.append((name, threading.get_ident(), kwargs))
            return result
        return operation
    service = SimpleNamespace(
        settings=SimpleNamespace(product_edition=edition, realtime_protocol_version="2.0",
            realtime_ingress_max_frames_per_second=100, realtime_ingress_sequence_gap_max_events=1,
            realtime_legacy_http_enabled=True),
        connect_publisher=note("connect", PUB), disconnect_publisher=note("disconnect", PUB),
        repository=SimpleNamespace(list_frame_receipts_for_session=note("bootstrap", [])),
        latest_source_generation=lambda **kwargs: 0, terminal_is_accepted=lambda **kwargs: True,
        process_audio_frame=note("legacy-frame", []), enqueue_audio_frame=note("frame", []),
        session_service=SimpleNamespace(get_session=note("session", SimpleNamespace(session_mode="standard"))),
        create_publisher=note("create", PUB),
        get_desktop_active_binding=note("binding", SimpleNamespace(session_id=PUB.session_id, owner_user_id=PUB.owner_user_id)),
        _publisher_response=routes.RealtimeSpeechService._publisher_response,
        operational_metrics=lambda: {},
    )
    return service, values


def application(configured=True):
    app = FastAPI()
    executor = CnRealtimeIoExecutor() if configured else None
    if executor:
        app.state.cn_realtime_io_executor = executor
    return app, executor


async def entered(event):
    assert await asyncio.wait_for(asyncio.to_thread(event.wait, 1), 2)


@pytest.mark.parametrize("configured", [False, True])
@pytest.mark.parametrize("binary", [False, True])
def test_v2_order_wire_and_all_io_off_main_loop(monkeypatch, configured, binary):
    async def scenario():
        app, executor = application(configured)
        service, calls = target()
        monkeypatch.setattr(routes, "realtime_speech_service", lambda: service)
        socket = Socket(app, [frame(0), frame(1), frame(1), frame(3)], binary=binary)
        try:
            await routes.realtime_ingest_ws(socket)
            assert [v[0] for v in calls] == ["connect", "bootstrap", "frame", "frame", "disconnect"]
            assert [v[2]["sequence"] for v in calls if v[0] == "frame"] == [0, 1]
            assert all(v[1] != threading.get_ident() for v in calls)
            assert socket.sent[0]["kind"] == "connection-state"
            assert socket.sent[0]["payload"]["resumeOffsets"] == {"microphone": -1, "system": -1}
            assert socket.sent[-2]["payload"]["duplicate"] is True
            assert socket.sent[-1]["payload"]["reason"] == "sequence-gap-budget-exhausted"
            assert socket.closed[-1]["code"] == 1013
            if binary:
                assert all(v[2]["audio_bytes"] == b"synthetic-pcm" for v in calls if v[0] == "frame")
            assert PUB.token not in routes._active_ingest_tokens
        finally:
            if executor:
                executor.shutdown()
    asyncio.run(scenario())


def test_global_v2_keeps_original_sync_calls(monkeypatch):
    async def scenario():
        app, executor = application()
        service, calls = target("global")
        monkeypatch.setattr(routes, "realtime_speech_service", lambda: service)
        try:
            await routes.realtime_ingest_ws(Socket(app, [frame()]))
            assert [v[0] for v in calls] == ["connect", "bootstrap", "frame", "disconnect"]
            assert all(v[1] == threading.get_ident() for v in calls)
            assert executor.diagnostics()["ingress"]["submitted"] == 0
            assert executor.diagnostics()["lifecycle"]["submitted"] == 0
        finally:
            executor.shutdown()
    asyncio.run(scenario())


@pytest.mark.parametrize("phase", ["connect", "frame"])
def test_cancel_connection_drains_inflight_before_exactly_one_disconnect(monkeypatch, phase):
    async def scenario():
        app, executor = application()
        service, calls = target()
        start, release = threading.Event(), threading.Event()
        trace = []
        def slow(**kwargs):
            trace.append("work-start")
            start.set()
            assert release.wait(2)
            trace.append("work-end")
            return PUB if phase == "connect" else []
        setattr(service, "connect_publisher" if phase == "connect" else "enqueue_audio_frame", slow)
        def disconnect(**kwargs):
            trace.append("disconnect")
            return PUB
        service.disconnect_publisher = disconnect
        monkeypatch.setattr(routes, "realtime_speech_service", lambda: service)
        task = asyncio.create_task(routes.realtime_ingest_ws(Socket(app, [frame()])))
        try:
            await entered(start)
            task.cancel()
            await asyncio.sleep(.01)
            task.cancel()
            assert trace == ["work-start"] and not task.done()
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert trace == ["work-start", "work-end", "disconnect"]
            assert PUB.token not in routes._active_ingest_tokens
        finally:
            release.set()
            executor.shutdown()
    asyncio.run(scenario())


def test_cancel_during_gap_cleanup_never_disconnects_twice(monkeypatch):
    async def scenario():
        app, executor = application()
        service, calls = target()
        start, release = threading.Event(), threading.Event()
        count = []
        def close(**kwargs):
            count.append(1)
            start.set()
            assert release.wait(2)
            return PUB
        service.disconnect_publisher = close
        monkeypatch.setattr(routes, "realtime_speech_service", lambda: service)
        task = asyncio.create_task(routes.realtime_ingest_ws(Socket(app, [frame(3)])))
        try:
            await entered(start)
            task.cancel()
            await asyncio.sleep(.01)
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert count == [1]
        finally:
            release.set()
            executor.shutdown()
    asyncio.run(scenario())


@pytest.mark.parametrize("accepted", [False, True])
def test_duplicate_terminal_recovery_check_is_off_loop_without_changing_order(monkeypatch, accepted):
    async def scenario():
        app, executor = application()
        service, calls = target()
        checked = []
        def check(**kwargs):
            checked.append((threading.get_ident(), kwargs["terminal_id"]))
            return accepted
        service.terminal_is_accepted = check
        monkeypatch.setattr(routes, "realtime_speech_service", lambda: service)
        packet = frame(0, isFinal=True, terminalId="synthetic-terminal")
        socket = Socket(app, [packet, packet])
        try:
            await routes.realtime_ingest_ws(socket)
            assert len(checked) == 1 and checked[0][0] != threading.get_ident()
            assert len([v for v in calls if v[0] == "frame"]) == (1 if accepted else 2)
            if accepted:
                assert socket.sent[-1]["kind"] == "terminal-accepted"
                assert socket.sent[-1]["payload"]["duplicate"] is True
        finally:
            executor.shutdown()
    asyncio.run(scenario())


@pytest.mark.parametrize("entry", ["legacy-ws", "http-frames"])
def test_cn_legacy_sync_work_is_isolated(monkeypatch, entry):
    async def scenario():
        app, executor = application()
        service, calls = target()
        monkeypatch.setattr(routes, "realtime_speech_service", lambda: service)
        try:
            if entry == "legacy-ws":
                await routes.realtime_ws(Socket(app, [frame()]))
                assert [v[0] for v in calls] == ["connect", "legacy-frame", "disconnect"]
            else:
                response = await routes.ingest_frame(Request({"type": "http", "app": app}),
                    RealtimeFrameIngestRequest.model_validate({**frame(), "token": PUB.token}), service)
                assert response.success is True
                assert [v[0] for v in calls] == ["frame"]
            assert all(v[1] != threading.get_ident() for v in calls)
        finally:
            executor.shutdown()
    asyncio.run(scenario())


def test_cn_publisher_binding_mismatch_still_rejects_and_create_is_not_called(monkeypatch):
    async def scenario():
        app, executor = application()
        service, calls = target()
        body = CreateRealtimePublisherRequest(userId="synthetic-other", sessionId=PUB.session_id,
            sourceKind="mixed", clientName="synthetic", deviceId="synthetic-device", manualCode="123456")
        try:
            with pytest.raises(DomainRequestError) as error:
                await routes.create_publisher(Request({"type": "http", "app": app}), body, None, service)
            assert error.value.status_code == 403
            assert error.value.error_code == "desktop_binding_mismatch"
            assert [v[0] for v in calls] == ["binding"]
        finally:
            executor.shutdown()
    asyncio.run(scenario())


@pytest.mark.parametrize("edition", ["cn", "global"])
def test_publisher_success_retains_wire_and_edition_dispatch(monkeypatch, edition):
    async def scenario():
        app, executor = application()
        service, calls = target(edition)
        monkeypatch.setattr(routes, "resolve_owned_user_id", lambda **kwargs: PUB.owner_user_id)
        body = CreateRealtimePublisherRequest(userId=PUB.owner_user_id, sessionId=PUB.session_id,
            sourceKind="mixed", clientName="synthetic")
        try:
            response = await routes.create_publisher(Request({"type": "http", "app": app}), body, None, service)
            assert response.success and response.data.token == PUB.token
            assert response.data.session_id == PUB.session_id
            assert [v[0] for v in calls] == ["session", "create"]
            assert calls[0][1] != threading.get_ident()
            assert (calls[1][1] != threading.get_ident()) == (edition == "cn")
        finally:
            executor.shutdown()
    asyncio.run(scenario())


def test_cancel_late_http_publisher_creation_compensates_once(monkeypatch):
    async def scenario():
        app, executor = application()
        service, calls = target()
        start, release = threading.Event(), threading.Event()
        trace = []
        def create(**kwargs):
            trace.append("create")
            start.set()
            assert release.wait(2)
            return PUB
        service.create_publisher = create
        service.disconnect_publisher = lambda **kwargs: trace.append("disconnect")
        monkeypatch.setattr(routes, "resolve_owned_user_id", lambda **kwargs: PUB.owner_user_id)
        body = CreateRealtimePublisherRequest(userId=PUB.owner_user_id, sessionId=PUB.session_id,
            sourceKind="mixed", clientName="synthetic")
        task = asyncio.create_task(routes.create_publisher(Request({"type": "http", "app": app}), body, None, service))
        try:
            await entered(start)
            task.cancel()
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert trace == ["create", "disconnect"]
        finally:
            release.set()
            executor.shutdown()
    asyncio.run(scenario())


def test_mock_independent_transport_is_delegated_without_cn_io(monkeypatch):
    async def scenario():
        app, executor = application()
        service, calls = target()
        delegated = []
        async def legacy(*args):
            delegated.append(args[1:])
        from app.modules import mock_interview_legacy
        monkeypatch.setattr(mock_interview_legacy, "serve_legacy_microphone", legacy)
        monkeypatch.setattr(routes, "realtime_speech_service", lambda: service)
        try:
            await routes.realtime_ingest_ws(Socket(app, token="rt-mock-synthetic"))
            assert delegated == [("rt-mock-synthetic", "2.0", "json-base64")]
            assert calls == [] and executor.diagnostics()["ingress"]["submitted"] == 0
        finally:
            executor.shutdown()
    asyncio.run(scenario())


@pytest.mark.parametrize("edition", ["cn", "global"])
def test_observations_are_cn_only_and_fail_safely(edition):
    app, executor = application()
    app.state.cn_main_loop_monitor = SimpleNamespace(summary=lambda: {"count": 3, "p95Ms": 0.5})
    service, _ = target(edition)
    request = Request({"type": "http", "app": app})
    try:
        values = routes._cn_voice_observations(request, service)
        assert (set(values) == {"cnRealtimeIo", "cnMainLoopDelay"}) if edition == "cn" else values == {}
        app.state.cn_main_loop_monitor.summary = Mock(side_effect=ValueError("synthetic private error"))
        assert "cnMainLoopDelay" not in routes._cn_voice_observations(request, service)
    finally:
        executor.shutdown()


def test_normal_transport_then_service_then_executor_shutdown_order(monkeypatch):
    async def scenario():
        from app.platform.cn_realtime_lifespan import with_cn_realtime_lifespan
        app = FastAPI()
        service, calls = target()
        events = []
        monkeypatch.setattr(routes, "realtime_speech_service", lambda: service)
        @asynccontextmanager
        async def base(application):
            yield
            assert [value[0] for value in calls] == ["connect", "bootstrap", "disconnect"]
            assert PUB.token not in routes._active_ingest_tokens
            assert application.state.cn_realtime_io_executor.diagnostics()["closing"] == 0
            events.append("base-service-shutdown")
        async with with_cn_realtime_lifespan(base, service.settings)(app):
            await routes.realtime_ingest_ws(Socket(app))
            events.append("transport-closed")
        events.append("executor-shutdown")
        assert events == ["transport-closed", "base-service-shutdown", "executor-shutdown"]
        assert app.state.cn_realtime_io_executor.diagnostics()["poolsClosed"] == 1
        assert app.state.cn_realtime_io_executor.diagnostics()["outstanding"] == 0
    asyncio.run(scenario())
