from __future__ import annotations

from app.ports.realtime_speech import RealtimeFrameReceiptRecord, RealtimePublisherRecord, WebSessionHeartbeatRecord
from app.services.realtime_speech_service import RealtimeSpeechService


def test_runtime_evidence_separates_synthetic_asr_probe_from_real_desktop_frames() -> None:
    service = RealtimeSpeechService.__new__(RealtimeSpeechService)
    publisher = RealtimePublisherRecord(
        publisher_id="publisher-1",
        token="token-1",
        session_id="session-1",
        owner_user_id="admin",
        source_kind="microphone",
        client_name="diagnostic",
        issued_at_ms=1,
        expires_at_ms=999,
    )
    diagnostic_receipt = RealtimeFrameReceiptRecord(
        session_id="session-1",
        owner_user_id="admin",
        publisher_id="publisher-1",
        device_id="device-1",
        source_id="diagnostic-pcm-probe",
        source_kind="microphone",
        sequence=1,
        frame_count=1,
        captured_at_ms=10,
        received_at_ms=20,
        asr_status="accepted",
    )

    evidence = service._runtime_evidence(
        session_status="live",
        binding_present=True,
        publishers=[publisher],
        source_health=[],
        receipts=[diagnostic_receipt],
        transcripts=[],
        web_heartbeat=None,
    )

    assert evidence["diagnosticProbeFrameReceived"] is True
    assert evidence["asrAccepted"] is True
    assert evidence["realFrameReceiptReceived"] is False
    assert evidence["transcriptEmitted"] is False


def test_runtime_evidence_marks_web_consumer_and_real_frame_sources() -> None:
    service = RealtimeSpeechService.__new__(RealtimeSpeechService)
    publisher = RealtimePublisherRecord(
        publisher_id="publisher-2",
        token="token-2",
        session_id="session-2",
        owner_user_id="admin",
        source_kind="system",
        client_name="desktop-system",
        issued_at_ms=1,
        expires_at_ms=999,
    )
    real_receipt = RealtimeFrameReceiptRecord(
        session_id="session-2",
        owner_user_id="admin",
        publisher_id="publisher-2",
        device_id="device-1",
        source_id="system-loopback",
        source_kind="system",
        sequence=3,
        frame_count=2,
        captured_at_ms=10,
        received_at_ms=20,
        asr_status="accepted",
    )
    heartbeat = WebSessionHeartbeatRecord(
        session_id="session-2",
        owner_user_id="admin",
        page="live",
        seen_at_ms=30,
        binding_id="binding-1",
    )

    evidence = service._runtime_evidence(
        session_status="live",
        binding_present=True,
        publishers=[publisher],
        source_health=[],
        receipts=[real_receipt],
        transcripts=[],
        web_heartbeat=heartbeat,
    )

    assert evidence["realFrameReceiptReceived"] is True
    assert evidence["realFrameSources"] == ["system"]
    assert evidence["webConsumerSeen"] is True
