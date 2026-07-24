from __future__ import annotations

import base64
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import create_app


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


def test_realtime_metrics_are_privacy_safe():
    metrics = unwrap(client.get("/api/v1/realtime-speech/metrics"))
    assert metrics["protocolVersion"] == "2.0"
    assert metrics["rawAudioPersisted"] is False
    assert "fileDescriptors" in metrics
    assert "maxResidentSetKb" in metrics
    serialized = str(metrics).lower()
    assert "audiobase64" not in serialized
    assert "transcripttext" not in serialized
