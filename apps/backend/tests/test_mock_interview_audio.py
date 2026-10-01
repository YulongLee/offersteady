from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import Mock

import pytest

from app.core.errors import DomainRequestError
from app.ports.realtime_speech import TranscriptResult
from app.services.mock_interview_audio import MockInterviewAudio


def fixture():
    clock = [1000]
    gateway = Mock()
    gateway.transcribe.return_value = TranscriptResult("合成回答", 0.9)
    audio = MockInterviewAudio(gateway, now_ms=lambda: clock[0])
    messages = []
    capture = audio.open(session_id="mock-synthetic", owner_id="synthetic", device_id="device",
        epoch="a" * 32, deadline_ms=16000, sink=lambda *args: messages.append(args))
    return clock, gateway, audio, capture, messages


def test_audio_is_microphone_only_ephemeral_and_fenced_by_epoch():
    clock, gateway, audio, capture, messages = fixture()
    audio.ingest(session_id=capture.session_id, device_id="device", epoch=capture.epoch, pcm=b"\0\0" * 1600)
    frame = gateway.transcribe.call_args.kwargs["frame"]
    assert frame.source_kind == "microphone" and frame.channels == 1 and frame.sample_rate_hz == 16000
    assert frame.session_id.endswith("/" + capture.epoch)
    assert messages == [(capture.epoch, "合成回答")]
    audio.close(audio.revoke(capture.session_id))
    assert capture.text == "" and audio.snapshot() == {"captures": 0, "draft_characters": 0}
    audio._partial(frame, TranscriptResult("迟到内容", 0.9))
    assert len(messages) == 1
    with pytest.raises(DomainRequestError):
        audio.ingest(session_id=capture.session_id, device_id="device", epoch=capture.epoch, pcm=b"\0\0")
    gateway.close_session.assert_called_once_with(session_id=capture.provider_id)


def test_expired_wrong_device_wrong_round_and_oversized_frames_never_reach_provider():
    clock, gateway, audio, capture, _ = fixture()
    for device, epoch, pcm in [("other", capture.epoch, b"00"), ("device", "b"*32, b"00"),
                               ("device", capture.epoch, b"0"*8194), ("device", capture.epoch, b"0")]:
        with pytest.raises(DomainRequestError):
            audio.ingest(session_id=capture.session_id, device_id=device, epoch=epoch, pcm=pcm)
    clock[0] = 16000
    with pytest.raises(DomainRequestError):
        audio.ingest(session_id=capture.session_id, device_id="device", epoch=capture.epoch, pcm=b"00")
    assert audio.expired() == [capture.session_id]
    gateway.transcribe.assert_not_called()


def test_revoke_during_provider_call_drops_late_result_and_closes_after_append():
    _, gateway, audio, capture, messages = fixture()
    entered, release, closed = Event(), Event(), Event()
    def transcribe(**kwargs):
        entered.set()
        assert release.wait(3)
        assert not closed.is_set()
        return TranscriptResult("不应出现的旧轮回答", 0.9)
    gateway.transcribe.side_effect = transcribe
    gateway.close_session.side_effect = lambda **kwargs: closed.set()
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending = pool.submit(audio.ingest, session_id=capture.session_id, device_id="device",
                              epoch=capture.epoch, pcm=b"00")
        assert entered.wait(3)
        revoked = audio.revoke(capture.session_id)
        closing = pool.submit(audio.close, revoked)
        assert not closed.is_set()
        release.set()
        pending.result(3)
        closing.result(3)
    assert closed.is_set() and messages == []


def test_repeated_rounds_keep_no_live_capture_or_transcript():
    _, gateway, audio, capture, _ = fixture()
    audio.close(audio.revoke(capture.session_id))
    for n in range(100):
        current = audio.open(session_id="mock-synthetic", owner_id="synthetic", device_id="device",
            epoch=str(n).zfill(32), deadline_ms=16000, sink=lambda *args: None)
        audio.ingest(session_id=current.session_id, device_id="device", epoch=current.epoch, pcm=b"00")
        audio.close(audio.revoke(current.session_id))
    assert audio.snapshot() == {"captures": 0, "draft_characters": 0}
    assert gateway.close_session.call_count == 101


def test_late_provider_snapshot_cannot_replace_newer_partial():
    _, gateway, audio, capture, messages = fixture()
    def transcribe(**kwargs):
        audio._partial(kwargs["frame"], TranscriptResult("新的完整内容", .9, provider_revision=3))
        return TranscriptResult("旧快照", .9, provider_revision=2)
    gateway.transcribe.side_effect = transcribe
    audio.ingest(session_id=capture.session_id, device_id="device", epoch=capture.epoch, pcm=b"00")
    assert messages == [(capture.epoch, "新的完整内容")]
    audio.close(audio.revoke(capture.session_id))


def test_production_factory_gives_each_round_an_independent_adapter():
    created = []
    def factory():
        gateway = Mock()
        created.append(gateway)
        return gateway
    audio = MockInterviewAudio(gateway_factory=factory, now_ms=lambda: 1000)
    for index in range(100):
        capture = audio.open(session_id="mock-synthetic", owner_id="synthetic", device_id="device",
            epoch=f"{index:032x}", deadline_ms=2000, sink=lambda *_: None)
        audio.close(audio.revoke(capture.session_id))
    assert len({id(gateway) for gateway in created}) == 100
    assert audio.snapshot() == {"captures": 0, "draft_characters": 0}
    assert all(gateway.close_session.call_count == 1 for gateway in created)


def test_answer_limit_stops_new_audio_and_bounds_provider_history():
    _, gateway, audio, capture, messages = fixture()
    gateway.transcribe.return_value = TranscriptResult("合"*8100, .9)
    audio.ingest(session_id=capture.session_id, device_id="device", epoch=capture.epoch, pcm=b"00")
    assert len(messages[-1][1]) == 8000 and capture.limit_reached
    with pytest.raises(DomainRequestError) as exc:
        audio.ingest(session_id=capture.session_id, device_id="device", epoch=capture.epoch, pcm=b"00")
    assert exc.value.error_code == "mock_answer_length_limit"
    assert gateway.transcribe.call_count == 1
    audio.close(audio.revoke(capture.session_id))
