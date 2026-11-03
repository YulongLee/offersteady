import json

from app.services.dashscope_realtime_asr_gateway import DashScopeRealtimeAsrGateway


class _Socket:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def send(self, message: str) -> None:
        self.messages.append(message)


def test_audio_chunks_use_unique_frame_prefix_and_200ms_payloads() -> None:
    socket = _Socket()

    DashScopeRealtimeAsrGateway._send_audio_chunks(
        socket,
        b"\x00" * 12_800,
        event_id_prefix="segment-7",
    )

    payloads = [json.loads(message) for message in socket.messages]
    assert [payload["event_id"] for payload in payloads] == [
        "rt-audio-segment-7-0",
        "rt-audio-segment-7-1",
    ]
    assert all(payload["type"] == "input_audio_buffer.append" for payload in payloads)
