from __future__ import annotations

import base64
import json
import queue
import threading
import time
from dataclasses import replace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import create_app
from app.deps import realtime_speech_service
from app.ports.realtime_speech import AudioFrame, TranscriptResult
from app.services.realtime_speech_service import (
    RealtimeSpeechService,
    RetryableAsrError,
    stabilize_visible_transcript_text,
)


client = TestClient(create_app())


def test_visible_transcript_stabilization_keeps_growth_fast_and_blocks_destructive_revisions():
    assert stabilize_visible_transcript_text(
        current_text="请介绍项目",
        incoming_text="请介绍项目的性能优化",
        is_final=False,
    ) == "请介绍项目的性能优化"
    assert stabilize_visible_transcript_text(
        current_text="请介绍项目的性能优化",
        incoming_text="请介绍项目",
        is_final=False,
    ) == "请介绍项目的性能优化"
    assert stabilize_visible_transcript_text(
        current_text="旧的临时识别文本",
        incoming_text="准确终稿",
        is_final=True,
    ) == "旧的临时识别文本"
    assert stabilize_visible_transcript_text(
        current_text="请介绍项目的性能优化",
        incoming_text="请介绍项目",
        is_final=True,
    ) == "请介绍项目的性能优化"


def test_visible_transcript_stabilization_allows_only_bounded_tail_corrections():
    current = "请介绍一下你在上一家公司负责的核心项目上线"
    tail_correction = "请介绍一下你在上一家公司负责的核心项目复盘结果"
    assert stabilize_visible_transcript_text(
        current_text=current,
        incoming_text=tail_correction,
        is_final=False,
    ) == tail_correction

    stable_prefix_rewrite = "能否请你介绍在上一家公司负责的核心项目上线与复盘结果"
    assert len(stable_prefix_rewrite) >= len(current)
    assert stabilize_visible_transcript_text(
        current_text=current,
        incoming_text=stable_prefix_rewrite,
        is_final=False,
    ) == current
    assert stabilize_visible_transcript_text(
        current_text=current,
        incoming_text=stable_prefix_rewrite,
        is_final=True,
    ) == current


def test_visible_transcript_stabilization_blocks_equal_length_prefix_rewrite():
    current = "这是已经展示给用户的完整面试问题内容"
    rewrite = f"那{current[1:]}"
    assert len(rewrite) == len(current)
    assert stabilize_visible_transcript_text(
        current_text=current,
        incoming_text=rewrite,
        is_final=False,
    ) == current


def test_strict_prefix_final_freezes_the_fuller_published_partial(monkeypatch):
    _user_id, session_id, device_id, publisher_payload = create_live_binding()
    service = realtime_speech_service()
    publisher = service.repository.get_publisher(publisher_payload["publisherId"])
    assert publisher is not None
    now_ms = int(time.time() * 1000)
    partial_frame = AudioFrame(
        publisher_id=publisher.publisher_id,
        session_id=session_id,
        device_id=device_id,
        source_id="system-prefix-final",
        source_kind="system",
        segment_id=f"prefix-final-{uuid4().hex}",
        revision=1,
        sequence=0,
        captured_at_ms=now_ms - 200,
        started_at_ms=now_ms - 200,
        ended_at_ms=now_ms - 100,
        duration_ms=100,
        codec="pcm-s16le",
        sample_rate_hz=16_000,
        channels=1,
        is_final=False,
        audio_bytes=b"partial",
    )
    service._publish_provider_partial(partial_frame, TranscriptResult(
        text="请介绍项目的性能优化",
        confidence=0.9,
        partial_received_at_ms=now_ms - 50,
        provider_revision=1,
    ))
    terminal = replace(
        partial_frame,
        revision=2,
        sequence=1,
        ended_at_ms=now_ms,
        duration_ms=200,
        is_final=True,
        audio_bytes=b"terminal",
    )
    monkeypatch.setattr(service.asr_gateway, "finalize", lambda **_kwargs: TranscriptResult(
        text="请介绍项目",
        confidence=0.96,
        completed_at_ms=now_ms,
    ))

    transcript, result = service._transcribe_frame(publisher=publisher, frame=terminal)

    assert transcript is not None
    assert transcript.text == "请介绍项目的性能优化"
    assert transcript.is_final is True
    assert result.text == "请介绍项目的性能优化"


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


def test_publisher_attachment_rewarms_an_already_live_session(monkeypatch):
    service = realtime_speech_service()
    suffix = uuid4().hex[:8]
    user_id = f"attachment-prewarm-{suffix}"
    session = unwrap(client.post("/api/v1/sessions", json={"userId": user_id, "title": "Attachment prewarm"}))
    unwrap(client.post(f"/api/v1/sessions/{session['sessionId']}/start", json={"userId": user_id}))
    warmed: list[str] = []
    complete = threading.Event()
    with service._prewarm_metrics_lock:
        service._prewarm_ready_by_session.pop(session["sessionId"], None)

    def warm_session(**kwargs):
        warmed.append(str(kwargs["source_kind"]))
        if {"microphone", "system"}.issubset(warmed):
            complete.set()

    monkeypatch.setattr(service.asr_gateway, "warm_session", warm_session)
    unwrap(client.post("/api/v1/realtime-speech/publishers", json={
        "userId": user_id,
        "sessionId": session["sessionId"],
        "sourceKind": "mixed",
        "clientName": "Restarted desktop",
    }))

    assert complete.wait(timeout=1)
    assert set(warmed) == {"microphone", "system"}


def test_retry_replays_the_complete_ephemeral_utterance(monkeypatch):
    _user_id, session_id, device_id, publisher_payload = create_live_binding()
    service = realtime_speech_service()
    publisher = service.repository.get_publisher(publisher_payload["publisherId"])
    assert publisher is not None
    first = AudioFrame(
        publisher_id=publisher.publisher_id,
        session_id=session_id,
        device_id=device_id,
        source_id="native-microphone",
        source_kind="microphone",
        segment_id="replay-complete-segment",
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
        audio_bytes=b"complete-prefix-",
    )
    terminal = replace(
        first,
        revision=2,
        sequence=1,
        ended_at_ms=1_040,
        duration_ms=40,
        is_final=True,
        audio_bytes=b"terminal-tail",
    )
    service._buffer_segment_audio(first)
    service._buffer_segment_audio(terminal)
    observed: list[bytes] = []

    def finalize(*, frame: AudioFrame, attempt: int):
        observed.append(frame.audio_bytes)
        if attempt == 0:
            raise RetryableAsrError("synthetic-provider-disconnect")
        now_ms = int(time.time() * 1000)
        return TranscriptResult(text="synthetic complete utterance", confidence=0.96, completed_at_ms=now_ms)

    monkeypatch.setattr(service.asr_gateway, "finalize", finalize)
    transcript, _result = service._transcribe_frame(publisher=publisher, frame=terminal)

    assert transcript is not None
    assert observed == [b"terminal-tail", b"complete-prefix-terminal-tail"]
    service._clear_segment_audio(terminal)
    assert service._replay_frame(terminal) is None


def test_replay_buffer_keeps_a_rolling_tail_after_capacity_is_exceeded():
    service = realtime_speech_service()
    original_tail_ms = service.settings.realtime_asr_replay_tail_ms
    original_max_bytes = service.settings.realtime_asr_replay_buffer_max_bytes
    service.settings.realtime_asr_replay_tail_ms = 100
    service.settings.realtime_asr_replay_buffer_max_bytes = 3_200
    frame_base = AudioFrame(
        publisher_id="rolling-publisher",
        session_id=f"rolling-session-{uuid4().hex[:8]}",
        device_id="rolling-device",
        source_id="rolling-microphone",
        source_kind="microphone",
        segment_id="rolling-segment",
        revision=1,
        sequence=1,
        captured_at_ms=1_000,
        started_at_ms=1_000,
        ended_at_ms=1_100,
        duration_ms=100,
        codec="pcm-s16le",
        sample_rate_hz=16_000,
        channels=1,
        is_final=False,
        audio_bytes=b"a" * 2_000,
    )
    second = replace(frame_base, revision=2, sequence=2, ended_at_ms=1_200, audio_bytes=b"b" * 2_000)
    try:
        service._buffer_segment_audio(frame_base)
        service._buffer_segment_audio(second)
        replay = service._replay_frame(second)
        assert replay is not None
        assert replay.audio_bytes == (b"a" * 1_200) + (b"b" * 2_000)
        assert replay.duration_ms == 100
    finally:
        service._clear_segment_audio(second)
        service.settings.realtime_asr_replay_tail_ms = original_tail_ms
        service.settings.realtime_asr_replay_buffer_max_bytes = original_max_bytes


@pytest.mark.parametrize(
    ("prefix", "recovered", "expected"),
    [
        ("这是已经显示的字幕", "显示的字幕继续恢复", "这是已经显示的字幕继续恢复"),
        ("hello world", "world again", "hello world again"),
        ("完整内容", "", "完整内容"),
    ],
)
def test_recovery_transcript_stitching_deduplicates_replayed_tail(prefix, recovered, expected):
    assert RealtimeSpeechService._merge_recovery_transcript(prefix, recovered) == expected


def test_missing_provider_completion_is_suppressed_without_degrading_publisher(monkeypatch):
    _user_id, session_id, device_id, publisher_payload = create_live_binding()
    service = realtime_speech_service()
    publisher = service.repository.get_publisher(publisher_payload["publisherId"])
    assert publisher is not None
    terminal = AudioFrame(
        publisher_id=publisher.publisher_id,
        session_id=session_id,
        device_id=device_id,
        source_id="native-system",
        source_kind="system",
        segment_id="missing-provider-completion",
        revision=2,
        sequence=1,
        captured_at_ms=1_000,
        started_at_ms=1_000,
        ended_at_ms=1_500,
        duration_ms=500,
        codec="pcm-s16le",
        sample_rate_hz=16_000,
        channels=1,
        is_final=True,
        audio_bytes=b"terminal",
    )
    attempts: list[int] = []

    def finalize(*, frame: AudioFrame, attempt: int):
        attempts.append(attempt)
        raise RetryableAsrError("realtime_asr_transcript_missing")

    monkeypatch.setattr(service.asr_gateway, "finalize", finalize)
    transcript, result = service._transcribe_frame(publisher=publisher, frame=terminal)

    assert transcript is None
    assert result.text == ""
    assert result.suppressed_reason == "blank"
    assert attempts == [0]
    assert service.repository.get_publisher(publisher.publisher_id).status != "degraded"


def test_terminal_turn_remains_supervised_while_committing():
    _user_id, session_id, device_id, publisher_payload = create_live_binding()
    service = realtime_speech_service()
    publisher = service.repository.get_publisher(publisher_payload["publisherId"])
    assert publisher is not None
    terminal = AudioFrame(
        publisher_id=publisher.publisher_id,
        session_id=session_id,
        device_id=device_id,
        source_id="native-system",
        source_kind="system",
        segment_id="committing-supervised-segment",
        revision=3,
        sequence=2,
        captured_at_ms=1_000,
        started_at_ms=1_000,
        ended_at_ms=1_500,
        duration_ms=500,
        codec="pcm-s16le",
        sample_rate_hz=16_000,
        channels=1,
        is_final=True,
        audio_bytes=b"terminal",
    )
    original_enabled = service.settings.realtime_source_watchdog_enabled
    service.settings.realtime_source_watchdog_enabled = True
    try:
        service._track_source_turn({"publisher": publisher, "frame": terminal})
        assert (session_id, "system") not in service._active_source_turns
        assert (session_id, "system", terminal.segment_id) in service._committing_source_turns
        following = replace(
            terminal,
            segment_id="following-supervised-segment",
            revision=1,
            sequence=3,
            is_final=False,
        )
        service._track_source_turn({"publisher": publisher, "frame": following})
        assert service._active_source_turns[(session_id, "system")]["frame"] == following
        service._complete_source_turn(terminal)
        assert (session_id, "system", terminal.segment_id) not in service._committing_source_turns
        assert service._active_source_turns[(session_id, "system")]["frame"] == following
    finally:
        service.settings.realtime_source_watchdog_enabled = original_enabled


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


def test_replacement_publisher_resumes_session_channel_offsets():
    user_id, session_id, device_id, first = create_live_binding()
    with client.websocket_connect(f"/api/v1/realtime-speech/ingest-ws?token={first['token']}&protocol=2.0") as websocket:
        assert websocket.receive_json()["payload"]["resumeOffsets"] == {"microphone": -1, "system": -1}
        websocket.send_json(frame(device_id=device_id, source_kind="microphone", sequence=0))
        assert websocket.receive_json()["payload"]["sequence"] == 0
        websocket.send_json(frame(device_id=device_id, source_kind="system", sequence=0))
        assert websocket.receive_json()["payload"]["sequence"] == 0

    replacement = unwrap(client.post("/api/v1/realtime-speech/publishers", json={
        "userId": user_id,
        "sessionId": session_id,
        "sourceKind": "mixed",
        "clientName": "Synthetic replacement transport",
        "deviceId": device_id,
    }))
    assert replacement["publisherId"] != first["publisherId"]
    with client.websocket_connect(f"/api/v1/realtime-speech/ingest-ws?token={replacement['token']}&protocol=2.0") as websocket:
        handshake = websocket.receive_json()
        assert handshake["payload"]["resumeOffsets"] == {"microphone": 0, "system": 0}
        websocket.send_json(frame(device_id=device_id, source_kind="microphone", sequence=1))
        accepted = websocket.receive_json()
        assert accepted["kind"] == "frame-accepted"
        assert accepted["payload"]["sequence"] == 1


def test_replacement_publisher_resumes_above_authoritative_source_generation():
    user_id, session_id, device_id, first = create_live_binding()
    first_frame = {
        **frame(device_id=device_id, source_kind="system", sequence=0),
        "sourceGeneration": 7,
    }
    with client.websocket_connect(f"/api/v1/realtime-speech/ingest-ws?token={first['token']}&protocol=2.0") as websocket:
        websocket.receive_json()
        websocket.send_json(first_frame)
        assert websocket.receive_json()["kind"] == "frame-accepted"

    replacement = unwrap(client.post("/api/v1/realtime-speech/publishers", json={
        "userId": user_id,
        "sessionId": session_id,
        "sourceKind": "mixed",
        "clientName": "Synthetic process restart",
        "deviceId": device_id,
    }))
    with client.websocket_connect(f"/api/v1/realtime-speech/ingest-ws?token={replacement['token']}&protocol=2.0") as websocket:
        handshake = websocket.receive_json()
        assert handshake["payload"]["resumeOffsets"]["system"] == 0
        assert handshake["payload"]["resumeSourceGenerations"] == {"microphone": 0, "system": 7}
        resumed = {
            **frame(device_id=device_id, source_kind="system", sequence=1),
            "sourceGeneration": 8,
        }
        websocket.send_json(resumed)
        accepted = websocket.receive_json()
        assert accepted["kind"] == "frame-accepted"
        assert accepted["payload"]["sequence"] == 1


def test_replayed_terminal_below_resume_offset_is_readmitted_until_explicitly_accepted():
    user_id, session_id, device_id, first = create_live_binding()
    partial = {
        **frame(device_id=device_id, source_kind="system", sequence=0),
        "segmentId": "resume-terminal-segment",
    }
    with client.websocket_connect(f"/api/v1/realtime-speech/ingest-ws?token={first['token']}&protocol=2.0") as websocket:
        websocket.receive_json()
        websocket.send_json(partial)
        assert websocket.receive_json()["kind"] == "frame-accepted"

    replacement = unwrap(client.post("/api/v1/realtime-speech/publishers", json={
        "userId": user_id,
        "sessionId": session_id,
        "sourceKind": "mixed",
        "clientName": "Synthetic terminal recovery",
        "deviceId": device_id,
    }))
    terminal = {
        **partial,
        "revision": 2,
        "isFinal": True,
        "turnState": "committing",
        "finalizationReason": "silence",
        "sourceGeneration": 1,
        "terminalId": "resume-terminal-segment:1:2",
    }
    service = realtime_speech_service()
    assert not service.terminal_is_accepted(
        session_id=session_id,
        source_kind="system",
        segment_id="resume-terminal-segment",
        terminal_id="resume-terminal-segment:1:2",
    )
    with client.websocket_connect(f"/api/v1/realtime-speech/ingest-ws?token={replacement['token']}&protocol=2.0") as websocket:
        assert websocket.receive_json()["payload"]["resumeOffsets"]["system"] == 0
        websocket.send_json(terminal)
        accepted = websocket.receive_json()
        assert accepted["kind"] == "terminal-accepted"
        assert accepted["payload"]["terminalId"] == "resume-terminal-segment:1:2"

    assert service.terminal_is_accepted(
        session_id=session_id,
        source_kind="system",
        segment_id="resume-terminal-segment",
        terminal_id="resume-terminal-segment:1:2",
    )


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


def test_binary_audio_diagnostics_cannot_collide_with_authoritative_trace_fields():
    _user_id, _session_id, device_id, publisher = create_live_binding()
    payload = frame(device_id=device_id, source_kind="system", sequence=0)
    payload["diagnostics"] = {
        "desktopWsSendAtMs": 9_999_999,
        "backendWsReceiveAtMs": 9_999_999,
        "desktopPublisherFlushAtMs": 1_005,
    }
    audio = base64.b64decode(payload.pop("audioBase64"))
    header = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    envelope = len(header).to_bytes(4, byteorder="big") + header + audio

    with client.websocket_connect(
        f"/api/v1/realtime-speech/ingest-ws?token={publisher['token']}&protocol=2.0&media=binary-v1"
    ) as websocket:
        websocket.receive_json()
        websocket.send_bytes(envelope)
        accepted = websocket.receive_json()
        assert accepted["kind"] == "frame-accepted"
        assert accepted["payload"]["sequence"] == 0

    trace = realtime_speech_service()._trace_snapshot("trace-system-0")
    assert trace["desktopWsSendAtMs"] == 1_010
    assert trace["backendWsReceiveAtMs"] != 9_999_999
    assert trace["desktopPublisherFlushAtMs"] == 1_005


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


def test_new_segment_terminalizes_superseded_visible_partial_without_closing_source():
    _user_id, session_id, device_id, publisher = create_live_binding()
    service = realtime_speech_service()
    original_enabled = service.settings.realtime_source_watchdog_enabled
    service.settings.realtime_source_watchdog_enabled = True
    try:
        with client.websocket_connect(f"/api/v1/realtime-speech/ingest-ws?token={publisher['token']}&protocol=2.0") as websocket:
            websocket.receive_json()
            first = {
                **frame(device_id=device_id, source_kind="microphone", sequence=0),
                "segmentId": "superseded-visible-partial",
            }
            websocket.send_json(first)
            assert websocket.receive_json()["kind"] == "frame-accepted"
            queued = service._frame_queues.get((session_id, "microphone"))
            if queued is not None:
                queued.join()
            current = service.repository.get_transcript(session_id, "superseded-visible-partial")
            assert current is not None and current.is_final is False

            second = {
                **frame(device_id=device_id, source_kind="microphone", sequence=1),
                "segmentId": "new-visible-partial",
            }
            websocket.send_json(second)
            assert websocket.receive_json()["kind"] == "frame-accepted"
            queued = service._frame_queues.get((session_id, "microphone"))
            if queued is not None:
                queued.join()

        superseded = service.repository.get_transcript(session_id, "superseded-visible-partial")
        assert superseded is not None
        assert superseded.is_final is True
        assert superseded.terminal_state == "incomplete"
        assert superseded.finalization_reason == "superseded-segment"
        terminal_events = [
            event for event in service.repository.list_events_for_session(session_id=session_id)
            if event.kind == "transcript-updated"
            and event.payload.get("segmentId") == "superseded-visible-partial"
            and event.payload.get("terminalState") == "incomplete"
        ]
        assert len(terminal_events) == 1
        assert service.repository.list_candidates_for_session(session_id=session_id) == []
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


def test_frame_worker_only_coalesces_after_a_real_backlog_develops():
    assert RealtimeSpeechService._backlog_coalesce_take_count(backlog_frames=0, max_frames=4) == 0
    assert RealtimeSpeechService._backlog_coalesce_take_count(backlog_frames=1, max_frames=4) == 0
    assert RealtimeSpeechService._backlog_coalesce_take_count(backlog_frames=2, max_frames=4) == 1
    assert RealtimeSpeechService._backlog_coalesce_take_count(backlog_frames=3, max_frames=4) == 1
    assert RealtimeSpeechService._backlog_coalesce_take_count(backlog_frames=4, max_frames=4) == 3


def test_provider_partial_hot_path_does_not_scan_session_history_or_run_question_observer(monkeypatch):
    _user_id, session_id, device_id, publisher_payload = create_live_binding()
    service = realtime_speech_service()
    publisher = service.repository.get_publisher(publisher_payload["publisherId"])
    assert publisher is not None
    now_ms = int(time.time() * 1000)
    frame = AudioFrame(
        publisher_id=publisher.publisher_id,
        session_id=session_id,
        device_id=device_id,
        source_id="system-fast-partial",
        source_kind="system",
        segment_id=f"fast-partial-{uuid4().hex}",
        revision=1,
        sequence=0,
        captured_at_ms=now_ms - 100,
        started_at_ms=now_ms - 100,
        ended_at_ms=now_ms,
        duration_ms=100,
        codec="pcm-s16le",
        sample_rate_hz=16_000,
        channels=1,
        is_final=False,
        audio_bytes=b"partial-pcm",
    )
    cold_calls: list[str] = []

    def fail_history_scan(*_args, **_kwargs):
        raise AssertionError("partial publication scanned session history")

    def fail_inline_observer(*_args, **_kwargs):
        raise AssertionError("stable question observer ran inline")

    def capture_cold(operation, *_args, **_kwargs):
        cold_calls.append(getattr(operation, "__name__", "unknown"))

    monkeypatch.setattr(service.repository, "list_transcripts_for_session", fail_history_scan)
    monkeypatch.setattr(service, "_observe_stable_interviewer_partial", fail_inline_observer)
    monkeypatch.setattr(service, "_submit_cold", capture_cold)

    service._publish_provider_partial(frame, TranscriptResult(
        text="请介绍你的项目",
        confidence=0.92,
        partial_received_at_ms=now_ms,
        provider_revision=1,
    ))

    transcript = service.repository.get_transcript(session_id, frame.segment_id)
    assert transcript is not None
    assert transcript.text == "请介绍你的项目"
    assert cold_calls == ["fail_inline_observer"]

    service._publish_provider_partial(replace(frame, revision=2), TranscriptResult(
        text="能否请你详细介绍一下你负责的项目经验",
        confidence=0.94,
        partial_received_at_ms=now_ms + 1,
        provider_revision=2,
    ))

    destructive = service.repository.get_transcript(session_id, frame.segment_id)
    assert destructive is not None
    assert destructive.text == "请介绍你的项目"
    assert destructive.revision == transcript.revision

    service._publish_provider_partial(replace(frame, revision=2), TranscriptResult(
        text="请介绍",
        confidence=0.93,
        partial_received_at_ms=now_ms + 2,
        provider_revision=3,
    ))

    stabilized = service.repository.get_transcript(session_id, frame.segment_id)
    assert stabilized is not None
    assert stabilized.text == "请介绍你的项目"
    assert stabilized.revision == transcript.revision
    assert cold_calls == ["fail_inline_observer"]


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


def test_terminal_promotion_folds_contiguous_same_segment_pcm_without_overtaking_prior_terminal():
    template = AudioFrame(
        publisher_id="publisher-priority",
        session_id="session-priority",
        device_id="device-priority",
        source_id="mic-priority",
        source_kind="microphone",
        segment_id="segment-priority",
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
        audio_bytes=b"one",
    )
    prior_terminal = replace(template, segment_id="prior", is_final=True, terminal_id="prior")
    second = replace(template, revision=2, sequence=1, ended_at_ms=300, audio_bytes=b"two")
    terminal = replace(
        template,
        revision=3,
        sequence=2,
        ended_at_ms=400,
        is_final=True,
        terminal_id="current",
        audio_bytes=b"tail",
    )
    work_queue: queue.Queue[dict[str, object]] = queue.Queue(maxsize=8)
    work_queue.put_nowait({"frame": prior_terminal})
    work_queue.put_nowait({"frame": template})
    work_queue.put_nowait({"frame": second})
    work_queue.put_nowait({"frame": terminal})

    assert RealtimeSpeechService._promote_queued_terminal(work_queue, "current") is True
    jobs = [work_queue.get_nowait(), work_queue.get_nowait()]
    frames = [job["frame"] for job in jobs]
    assert isinstance(frames[0], AudioFrame) and frames[0].terminal_id == "prior"
    assert isinstance(frames[1], AudioFrame) and frames[1].terminal_id == "current"
    assert frames[1].audio_bytes == b"onetwotail"
    assert jobs[1]["coalesced_frame_count"] == 3
    work_queue.task_done()
    work_queue.task_done()
    assert work_queue.unfinished_tasks == 0
