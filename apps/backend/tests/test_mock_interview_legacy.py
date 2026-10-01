"""Shipped v2 wire format; no modified desktop implementation is used."""
import asyncio
import base64
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.core.errors import DomainRequestError
from app.modules.mock_interview_legacy import decode_frame, MAX_PCM
from app.ports.realtime_speech import RealtimePublisherRecord
from app.schemas.realtime_speech import RealtimeFrameRequest
from app.services.mock_interview_legacy import LegacyPublisher, MockLegacyBridge
from app.services.realtime_speech_service import RealtimeSpeechService


def wire(**changes):
    return dict(type="audio-frame", deviceId="device", sourceId="microphone",
        sequence=0, sourceKind="microphone", segmentId="segment", revision=1,
        capturedAtMs=2000, startedAtMs=1500, endedAtMs=2000, durationMs=500,
        codec="pcm-s16le", sampleRateHz=16000, channels=1, isFinal=False,
        sourceGeneration=1, audioBase64=base64.b64encode(b"00"*1600).decode(), **changes)


def frame(**changes):
    return RealtimeFrameRequest.model_validate({**wire(), **changes})


def bridge_fixture():
    runtime = SimpleNamespace(now_ms=lambda: 2000, audio=SimpleNamespace(max_frame_bytes=8192, ingest=Mock()))
    bridge = MockLegacyBridge(runtime)
    entry = LegacyPublisher(RealtimePublisherRecord("p", "rt-mock-token", "s", "u", "microphone", "old", 1, 9999), "device", 1)
    entry.connected = True
    entry.epoch = "epoch-one"
    entry.opened_at_ms = 1000
    return bridge, entry, runtime


@pytest.mark.parametrize("media", ["binary-v1", "json-base64"])
def test_shipped_wire_formats_and_empty_terminal(media):
    data = wire()
    if media == "binary-v1":
        pcm = base64.b64decode(data.pop("audioBase64"))
        header = json.dumps(data).encode()
        message = {"bytes": len(header).to_bytes(4, "big") + header + pcm}
    else:
        message = {"text": json.dumps(data)}
    decoded, pcm = decode_frame(message, media)
    assert decoded.source_kind == "microphone" and pcm == b"00"*1600
    data = {**wire(), "isFinal": True, "terminalId": "end", "audioBase64": ""}
    decoded, pcm = decode_frame({"text": json.dumps(data)}, "json-base64")
    assert decoded.terminal_id == "end" and pcm == b""


@pytest.mark.parametrize("message,media", [
    ({"bytes": b"00"}, "binary-v1"),
    ({"bytes": (2).to_bytes(4, "big") + b"{}" + b"0" * (MAX_PCM + 1)}, "binary-v1"),
    ({"text": "[1]"}, "json-base64"),
    ({"text": json.dumps({**wire(), "audioBase64": "!bad!"})}, "json-base64"),
])
def test_malformed_or_oversized_frames_rejected(message, media):
    with pytest.raises(ValueError): decode_frame(message, media)


def test_duplicate_terminal_and_system_frames_ack_without_extra_asr():
    async def run():
        bridge, entry, runtime = bridge_fixture()
        terminal = frame(isFinal=True, terminalId="terminal")
        first = await bridge.accept(entry, terminal, b"00")
        second = await bridge.accept(entry, terminal, b"00")
        await bridge.accept(entry, frame(sourceKind="system"), b"00")
        assert first["kind"] == second["kind"] == "terminal-accepted"
        assert second["payload"]["duplicate"] is True
        assert runtime.audio.ingest.call_count == 1
    asyncio.run(run())


@pytest.mark.parametrize("change", [{"startedAtMs": 999}, {"capturedAtMs": -4000, "startedAtMs": -5000}, {"sourceGeneration": 1}])
def test_old_segments_delayed_frames_and_generations_do_not_cross_rounds(change):
    async def run():
        bridge, entry, runtime = bridge_fixture()
        if "sourceGeneration" in change: entry.generations["microphone"] = 2
        await bridge.accept(entry, frame(**change), b"00")
        assert entry.expected["microphone"] == 1
        runtime.audio.ingest.assert_not_called()
    asyncio.run(run())


def test_playback_closed_gate_never_calls_provider_and_gap_is_bounded():
    async def run():
        bridge, entry, runtime = bridge_fixture()
        entry.epoch = None
        await bridge.accept(entry, frame(), b"00")
        runtime.audio.ingest.assert_not_called()
        for _ in range(4):
            assert (await bridge.accept(entry, frame(sequence=9), b"00"))["kind"] == "sequence-gap"
        with pytest.raises(DomainRequestError): await bridge.accept(entry, frame(sequence=9), b"00")
    asyncio.run(run())


def test_future_clock_and_wrong_device_fail_closed():
    async def run():
        bridge, entry, runtime = bridge_fixture()
        for changes in ({"capturedAtMs": 3000}, {"deviceId": "other"}):
            with pytest.raises(DomainRequestError): await bridge.accept(entry, frame(**changes), b"00")
        runtime.audio.ingest.assert_not_called()
    asyncio.run(run())


def test_inflight_round_revocation_does_not_relabel_remaining_pcm():
    async def run():
        bridge, entry, runtime = bridge_fixture()
        def changed(**kwargs): entry.epoch = "epoch-two"
        runtime.audio.ingest.side_effect = changed
        await bridge.accept(entry, frame(), b"00"*10000)
        runtime.audio.ingest.assert_called_once()
        assert runtime.audio.ingest.call_args.kwargs["epoch"] == "epoch-one"
    asyncio.run(run())


def test_mock_tokens_cannot_use_normal_ingest_http_or_ws():
    service = Mock()
    with pytest.raises(DomainRequestError) as caught:
        RealtimeSpeechService._require_publisher_token(service, "rt-mock-token")
    assert caught.value.error_code == "mock_transport_required"
    service.repository.get_publisher_by_token.assert_not_called()


def test_retired_connections_release_bounded_registries_and_publisher_credentials():
    async def run():
        bridge, entry, runtime = bridge_fixture()
        runtime.desktops = {}
        runtime.realtime = Mock()
        for _ in range(100):
            entry.revoked = False
            entry.desktop = ("device", AsyncMock())
            runtime.desktops["s"] = entry.desktop
            bridge.sessions["s"] = entry
            await bridge.retire("s")
            assert not bridge.sessions and not runtime.desktops and entry.epoch is None
        assert runtime.realtime.repository.prune_publishers_for_session.call_count == 100
        runtime.realtime.repository.prune_publishers_for_session.assert_called_with(session_id="s", keep_publisher_ids=set())
    asyncio.run(run())
