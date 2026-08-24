from __future__ import annotations

import base64
import json
import queue
from dataclasses import replace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import create_app
from app.deps import realtime_speech_service
from app.ports.realtime_speech import AudioFrame
from app.services.realtime_speech_service import RealtimeSpeechService


client = TestClient(create_app())


def unwrap(response):
    assert response.status_code == 200, response.text
    return response.json()["data"]


def create_live_binding():
    suffix = uuid4().hex[:8]
    user_id = f"transport-user-{suffix}"
    device_id = f"transport-device-{suffix}"
    manual_code = str(100000 + int(suffix[:6], 16) % 900000)
    session = unwrap(client.post("/api/v1/sessions", json={"userId": user_id, "title": "Realtime v2"}))
    session_id = session["sessionId"]
    unwrap(client.post("/api/v1/realtime-speech/desktop-devices/register", json={
        "deviceId": device_id,
        "manualCode": manual_code,
        "displayName": "Synthetic desktop",
        "capabilities": {"protocolVersion": "2.0"},
    }))
    unwrap(client.post(f"/api/v1/realtime-speech/sessions/{session_id}/desktop-binding", json={"userId": user_id, "manualCode": manual_code}))
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": user_id}))
    publisher = unwrap(client.post("/api/v1/realtime-speech/publishers", json={
        "userId": user_id,
        "sessionId": session_id,
        "sourceKind": "mixed",
        "clientName": "Synthetic multiplexed transport",
        "deviceId": device_id,
        "manualCode": manual_code,
    }))
    return user_id, session_id, device_id, publisher


def frame(*, device_id: str, source_kind: str, sequence: int):
    payload = base64.b64encode(("synthetic-" + source_kind).encode()).decode()
    return {
        "type": "audio-frame",
        "deviceId": device_id,
        "sourceId": f"native-{source_kind}",
        "sequence": sequence,
        "sourceKind": source_kind,
        "segmentId": f"segment-{source_kind}-{sequence}",
        "revision": 1,
        "capturedAtMs": 1000 + sequence,
        "sentAtMs": 1010 + sequence,
        "traceId": f"trace-{source_kind}-{sequence}",
        "startedAtMs": 1000 + sequence,
        "endedAtMs": 1020 + sequence,
        "durationMs": 20,
        "codec": "pcm-s16le",
        "sampleRateHz": 16000,
        "channels": 1,
        "isFinal": False,
        "audioBase64": payload,
    }


def test_multiplexed_transport_acknowledges_independent_channels_and_gaps():
    _user_id, _session_id, device_id, publisher = create_live_binding()
    with client.websocket_connect(f"/api/v1/realtime-speech/ingest-ws?token={publisher['token']}&protocol=2.0") as websocket:
        handshake = websocket.receive_json()
        assert handshake["payload"]["channels"] == ["microphone", "system"]
        websocket.send_json(frame(device_id=device_id, source_kind="microphone", sequence=0))
        assert websocket.receive_json()["payload"]["sequence"] == 0
        websocket.send_json(frame(device_id=device_id, source_kind="system", sequence=0))
        assert websocket.receive_json()["payload"]["sequence"] == 0
        websocket.send_json(frame(device_id=device_id, source_kind="microphone", sequence=0))
        duplicate = websocket.receive_json()
        assert duplicate["payload"]["duplicate"] is True
        websocket.send_json(frame(device_id=device_id, source_kind="microphone", sequence=2))
        gap = websocket.receive_json()
        assert gap["kind"] == "sequence-gap"
        assert gap["payload"] == {"sourceKind": "microphone", "expected": 1, "received": 2}


def test_multiplexed_transport_accepts_negotiated_binary_audio_without_base64():
    _user_id, session_id, device_id, publisher = create_live_binding()
    payload = frame(device_id=device_id, source_kind="system", sequence=0)
    audio = base64.b64decode(payload.pop("audioBase64"))
    header = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    envelope = len(header).to_bytes(4, byteorder="big") + header + audio

    with client.websocket_connect(
        f"/api/v1/realtime-speech/ingest-ws?token={publisher['token']}&protocol=2.0&media=binary-v1"
    ) as websocket:
        handshake = websocket.receive_json()
        assert handshake["payload"]["mediaMode"] == "binary-v1"
        websocket.send_bytes(envelope)
        accepted = websocket.receive_json()
        assert accepted["kind"] == "frame-accepted"
        assert accepted["payload"]["sourceKind"] == "system"

    queued = realtime_speech_service()._frame_queues.get((session_id, "system"))
    if queued is not None:
        queued.join()
    transcript = realtime_speech_service().repository.get_transcript(session_id, "segment-system-0")
    assert transcript is not None


def test_authenticated_audio_hot_path_does_not_reload_session_from_database():
    _user_id, _session_id, device_id, publisher_payload = create_live_binding()
    service = realtime_speech_service()
    publisher = service.connect_publisher(token=publisher_payload["token"])
    original_get_session = service.session_service.get_session
    service.session_service.get_session = lambda **_kwargs: (_ for _ in ()).throw(AssertionError("database access on frame hot path"))  # type: ignore[method-assign]
    try:
        prepared = service._prepare_audio_frame(
            token=publisher.token,
            device_id=device_id,
            source_id="native-system",
            sequence=0,
            source_kind="system",
            segment_id="hot-path-segment",
            revision=1,
            captured_at_ms=1_000,
            started_at_ms=1_000,
            ended_at_ms=1_020,
            duration_ms=20,
            codec="pcm-s16le",
            sample_rate_hz=16_000,
            channels=1,
            is_final=False,
            turn_state=None,
            finalization_reason=None,
            source_generation=None,
            terminal_id=None,
            trace_id="hot-path-trace",
            sent_at_ms=1_010,
            audio_bytes=b"synthetic-system",
            authenticated_publisher=publisher,
        )
        assert prepared["frame"].audio_bytes == b"synthetic-system"  # type: ignore[union-attr]
    finally:
        service.session_service.get_session = original_get_session  # type: ignore[method-assign]
        service.disconnect_publisher(token=publisher.token)


def test_terminal_is_acknowledged_idempotently_and_stale_generation_is_rejected():
    _user_id, _session_id, device_id, publisher = create_live_binding()
    terminal = {
        **frame(device_id=device_id, source_kind="system", sequence=0),
        "segmentId": "commercial-terminal-segment",
        "revision": 3,
        "isFinal": True,
        "turnState": "committing",
        "finalizationReason": "silence",
        "sourceGeneration": 2,
        "terminalId": "commercial-terminal-2-3",
    }
    with client.websocket_connect(f"/api/v1/realtime-speech/ingest-ws?token={publisher['token']}&protocol=2.0") as websocket:
        websocket.receive_json()
        websocket.send_json(terminal)
        accepted = websocket.receive_json()
        assert accepted["kind"] == "terminal-accepted"
        assert accepted["payload"]["terminalId"] == "commercial-terminal-2-3"

        websocket.send_json(terminal)
        duplicate = websocket.receive_json()
        assert duplicate["kind"] == "terminal-accepted"
        assert duplicate["payload"]["duplicate"] is True

        stale = {
            **frame(device_id=device_id, source_kind="system", sequence=1),
            "segmentId": "stale-generation-segment",
            "sourceGeneration": 1,
        }
        websocket.send_json(stale)
        rejected = websocket.receive_json()
        assert rejected["kind"] == "degraded"
        assert rejected["payload"]["reason"] == "stale-source-generation"


def test_watchdog_publishes_one_incomplete_terminal_without_question_side_effects():
    user_id, session_id, device_id, publisher = create_live_binding()
    service = realtime_speech_service()
    original_enabled = service.settings.realtime_source_watchdog_enabled
    service.settings.realtime_source_watchdog_enabled = True
    try:
        partial = {
            **frame(device_id=device_id, source_kind="system", sequence=0),
            "segmentId": "abandoned-commercial-turn",
            "sourceGeneration": 1,
        }
        with client.websocket_connect(f"/api/v1/realtime-speech/ingest-ws?token={publisher['token']}&protocol=2.0") as websocket:
            websocket.receive_json()
            websocket.send_json(partial)
            assert websocket.receive_json()["kind"] == "frame-accepted"
        queue_key = (session_id, "system")
        queued = service._frame_queues.get(queue_key)
        if queued is not None:
            queued.join()
        with service._watchdog_lock:
            active = service._active_source_turns.pop(queue_key)
        service._finalize_abandoned_source_turn(key=queue_key, active=active, now_ms=20_000)

        transcript = service.repository.get_transcript(session_id, "abandoned-commercial-turn")
        assert transcript is not None
        assert transcript.is_final is True
        assert transcript.terminal_state == "incomplete"
        assert transcript.finalization_reason == "backend-watchdog"
        assert service.repository.list_candidates_for_session(session_id=session_id) == []
        terminal_events = [
            event for event in service.repository.list_events_for_session(session_id=session_id)
            if event.kind == "transcript-updated"
            and event.payload.get("segmentId") == "abandoned-commercial-turn"
            and event.payload.get("terminalState") == "incomplete"
        ]
        assert len(terminal_events) == 1
    finally:
        service.settings.realtime_source_watchdog_enabled = original_enabled


def test_stale_watchdog_snapshot_does_not_close_a_fresh_source_turn():
    _user_id, session_id, device_id, publisher_payload = create_live_binding()
    service = realtime_speech_service()
    publisher = service.repository.get_publisher(publisher_payload["publisherId"])
    assert publisher is not None
    source_key = (session_id, "system")
    expired_frame = AudioFrame(
        publisher_id=publisher.publisher_id,
        session_id=session_id,
        device_id=device_id,
        source_id="native-system",
        source_kind="system",
        segment_id="segment-expired",
        revision=1,
        sequence=0,
        captured_at_ms=1_000,
        started_at_ms=1_000,
        ended_at_ms=1_020,
        duration_ms=20,
        codec="pcm-s16le",
        sample_rate_hz=16_000,
        channels=1,
        is_final=False,
        audio_bytes=b"synthetic-system",
    )
    fresh_frame = replace(
        expired_frame,
        segment_id="segment-fresh",
        revision=1,
        sequence=expired_frame.sequence + 1,
    )
    expired = {"publisher": publisher, "frame": expired_frame, "lastFrameAtMs": 1_000}
    with service._watchdog_lock:
        service._active_source_turns[source_key] = {
            "publisher": publisher,
            "frame": fresh_frame,
            "lastFrameAtMs": 2_000,
        }

    closed_sources: list[tuple[str, str]] = []
    service._close_asr_source = lambda *, session_id, source_kind: closed_sources.append((session_id, source_kind))  # type: ignore[method-assign]
    service._finalize_abandoned_source_turn(key=source_key, active=expired, now_ms=10_000)

    assert closed_sources == []
    assert service.repository.get_transcript(session_id, expired_frame.segment_id) is None


def test_multiplexed_transport_rejects_stale_token_without_asgi_exception():
    with client.websocket_connect("/api/v1/realtime-speech/ingest-ws?token=rt-stale&protocol=2.0") as websocket:
        rejected = websocket.receive_json()
        assert rejected["kind"] == "connection-rejected"
        assert rejected["payload"]["reason"] == "publisher-credential-rejected"
        with pytest.raises(WebSocketDisconnect) as closed:
            websocket.receive_json()
        assert closed.value.code == 1008


def test_realtime_metrics_are_privacy_safe():
    metrics = unwrap(client.get("/api/v1/realtime-speech/metrics"))
    assert metrics["protocolVersion"] == "2.0"
    assert metrics["rawAudioPersisted"] is False
    assert "fileDescriptors" in metrics
    assert "maxResidentSetKb" in metrics
    serialized = str(metrics).lower()
    assert "audiobase64" not in serialized
    assert "transcripttext" not in serialized


def test_realtime_worker_coalesces_backlogged_incremental_pcm_and_preserves_final():
    first = AudioFrame(
        publisher_id="publisher-1",
        session_id="session-1",
        device_id="device-1",
        source_id="mic-1",
        source_kind="microphone",
        segment_id="segment-1",
        revision=1,
        sequence=0,
        captured_at_ms=100,
        started_at_ms=100,
        ended_at_ms=250,
        duration_ms=150,
        codec="pcm-s16le",
        sample_rate_hz=16000,
        channels=1,
        is_final=False,
        audio_bytes=b"first",
    )
    partial = replace(
        first,
        revision=2,
        sequence=1,
        captured_at_ms=250,
        ended_at_ms=400,
        audio_bytes=b"second",
    )
    final = replace(
        first,
        revision=3,
        sequence=2,
        captured_at_ms=400,
        ended_at_ms=520,
        is_final=True,
        audio_bytes=b"final",
    )

    coalesced = RealtimeSpeechService._coalesce_prepared_frame_jobs([
        {"frame": first},
        {"frame": partial},
        {"frame": final},
    ])

    assert len(coalesced) == 1
    merged = coalesced[0]["frame"]
    assert isinstance(merged, AudioFrame)
    assert merged.audio_bytes == b"firstsecondfinal"
    assert merged.sequence == 2
    assert merged.revision == 3
    assert merged.is_final is True
    assert merged.started_at_ms == 100
    assert merged.ended_at_ms == 520


def test_saturated_queue_replaces_only_a_partial_and_preserves_all_terminals():
    template = AudioFrame(
        publisher_id="publisher-queue",
        session_id="session-queue",
        device_id="device-queue",
        source_id="system-queue",
        source_kind="system",
        segment_id="segment-queue",
        revision=1,
        sequence=0,
        captured_at_ms=100,
        started_at_ms=100,
        ended_at_ms=200,
        duration_ms=100,
        codec="pcm-s16le",
        sample_rate_hz=16000,
        channels=1,
        is_final=False,
        audio_bytes=b"partial",
    )
    already_terminal = replace(template, segment_id="prior-terminal", is_final=True, terminal_id="prior")
    pending_partial = replace(template, segment_id="new-terminal", revision=2, audio_bytes=b"pending")
    new_terminal = replace(
        template,
        segment_id="new-terminal",
        revision=3,
        sequence=2,
        is_final=True,
        terminal_id="new",
        audio_bytes=b"tail",
    )
    work_queue: queue.Queue[dict[str, object]] = queue.Queue(maxsize=2)
    work_queue.put_nowait({"frame": already_terminal})
    work_queue.put_nowait({"frame": pending_partial})

    assert RealtimeSpeechService._replace_queued_partial_with_terminal(work_queue, {"frame": new_terminal}) is True
    jobs = [work_queue.get_nowait(), work_queue.get_nowait()]
    frames = [job["frame"] for job in jobs]
    assert isinstance(frames[0], AudioFrame) and frames[0].terminal_id == "prior"
    assert isinstance(frames[1], AudioFrame) and frames[1].terminal_id == "new"
    assert frames[1].audio_bytes == b"pendingtail"
