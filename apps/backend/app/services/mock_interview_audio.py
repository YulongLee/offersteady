"""Microphone-only, round-scoped ASR, deliberately separate from live answers.

No audio/transcript repository, automatic question detection or normal billing.
The owning controller must renew its paid interaction deadline. Revocation is
immediate; closing waits for an in-flight append before releasing the provider,
so a late append cannot recreate a closed provider session.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from time import time
from typing import Callable

from app.ports.realtime_speech import AudioFrame, TranscriptResult
from app.services.mock_interview_repository import mock_error


@dataclass
class Capture:
    session_id: str
    owner_id: str
    device_id: str
    epoch: str
    deadline_ms: int
    opened_at_ms: int
    sink: Callable[[str, str], None]
    gateway: object
    lock: threading.Lock = field(default_factory=threading.Lock)
    revoked: bool = False
    bytes_received: int = 0
    sequence: int = 0
    text: str = ""
    provider_revision: int = -1
    limit_reached: bool = False

    @property
    def provider_id(self):
        return f"{self.session_id}/{self.epoch}"


class MockInterviewAudio:
    max_captures = 64
    max_frame_bytes = 8192

    def __init__(self, gateway=None, *, gateway_factory=None, now_ms=None, interview_language="zh-CN"):
        # Production uses a per-round adapter. Some legacy ASR adapters retain
        # per-source creation locks for their own lifetime; do not accumulate
        # those locks across every historical mock round in a shared singleton.
        if gateway is None and gateway_factory is None:
            raise ValueError("ASR adapter factory required")
        self._gateway_factory = gateway_factory or (lambda: gateway)
        self.interview_language = interview_language
        self.now_ms = now_ms or (lambda: int(time() * 1000))
        self._lock = threading.RLock()
        self._captures: dict[str, Capture] = {}

    def open(self, *, session_id: str, owner_id: str, device_id: str, epoch: str,
             deadline_ms: int, sink: Callable[[str, str], None]) -> Capture:
        with self._lock:
            if session_id in self._captures:
                raise mock_error("请先关闭上一轮收音。", "mock_capture_in_use")
            if len(self._captures) >= self.max_captures:
                raise mock_error("模拟面试收音繁忙，请稍后重试。", "mock_capture_busy", 503)
            if not epoch or deadline_ms <= self.now_ms():
                raise mock_error("收音授权已过期。", "mock_capture_expired")
            gateway = self._gateway_factory()
            gateway.set_partial_listener(self._partial)
            capture = Capture(session_id, owner_id, device_id, epoch, deadline_ms, self.now_ms(), sink, gateway)
            self._captures[session_id] = capture
            return capture

    def renew(self, session_id: str, epoch: str, deadline_ms: int) -> None:
        with self._lock:
            current = self._captures.get(session_id)
            if current and current.epoch == epoch and not current.revoked:
                current.deadline_ms = deadline_ms

    def revoke(self, session_id: str) -> Capture | None:
        """Nonblocking fence. Provider close is intentionally outside the lock."""
        with self._lock:
            capture = self._captures.pop(session_id, None)
            if capture:
                capture.revoked = True
                capture.text = ""
            return capture

    def close(self, capture: Capture | None) -> None:
        if capture:
            with capture.lock:
                try:
                    capture.gateway.close_session(session_id=capture.provider_id)
                finally:
                    capture.gateway.set_partial_listener(lambda *_: None)

    def _valid(self, capture: Capture) -> bool:
        return (not capture.revoked and self._captures.get(capture.session_id) is capture
                and capture.deadline_ms > self.now_ms())

    def ingest(self, *, session_id: str, device_id: str, epoch: str, pcm: bytes) -> None:
        if not pcm or len(pcm) > self.max_frame_bytes or len(pcm) % 2:
            raise mock_error("音频帧格式无效。", "mock_invalid_audio", 422)
        with self._lock:
            capture = self._captures.get(session_id)
            if capture and capture.epoch == epoch and capture.device_id == device_id and capture.limit_reached:
                raise mock_error("本题转写已达到 8000 字，请校正并提交回答。", "mock_answer_length_limit")
            if (not capture or capture.epoch != epoch or capture.device_id != device_id
                    or not self._valid(capture)):
                raise mock_error("当前题目不接收音频。", "mock_capture_expired")
        # One provider append per round at a time; queued old frames check the
        # fence after obtaining the lock as well as after the provider returns.
        with capture.lock:
            with self._lock:
                if not self._valid(capture):
                    return
                elapsed = max(0, self.now_ms() - capture.opened_at_ms)
                if capture.bytes_received + len(pcm) > (elapsed + 1000) * 64:
                    raise mock_error("音频发送过快。", "mock_audio_rate_limited", 429)
                capture.bytes_received += len(pcm)
                capture.sequence += 1
            now = self.now_ms()
            frame = AudioFrame(publisher_id=capture.epoch, session_id=capture.provider_id,
                device_id=device_id, source_id="mock-microphone", source_kind="microphone",
                segment_id=capture.epoch, revision=capture.sequence, sequence=capture.sequence,
                captured_at_ms=now, started_at_ms=capture.opened_at_ms, ended_at_ms=now,
                duration_ms=len(pcm) // 32, codec="pcm-s16le", sample_rate_hz=16000,
                channels=1, is_final=False, audio_bytes=pcm, interview_language=self.interview_language)
            result = capture.gateway.transcribe(frame=frame, attempt=1)
            self._partial(frame, result)

    def _partial(self, frame: AudioFrame, result: TranscriptResult) -> None:
        session_id, _, epoch = frame.session_id.partition("/")
        with self._lock:
            capture = self._captures.get(session_id)
            if not capture or capture.epoch != epoch or not self._valid(capture):
                return
            if result.provider_revision is not None:
                if result.provider_revision < capture.provider_revision:
                    return
                capture.provider_revision = result.provider_revision
            text = result.text.strip()[:8000]
            if not text or capture.text == text:
                return
            capture.text = text
            # Sink only enqueues an immutable copy; it must never block or I/O.
            capture.sink(epoch, text)
            if len(result.text.strip()) >= 8000:
                # Stop the next append and close this ASR adapter, bounding its
                # internal sentence history as well as our displayed text.
                capture.limit_reached = True
                capture.deadline_ms = self.now_ms()

    def expired(self) -> list[str]:
        with self._lock:
            return [sid for sid, capture in self._captures.items() if not self._valid(capture)]

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return {"captures": len(self._captures),
                    "draft_characters": sum(len(c.text) for c in self._captures.values())}
