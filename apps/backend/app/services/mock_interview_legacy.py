"""Bounded adapter for the shipped companion's v2 microphone protocol.

Only transport framing/ACKs are shared with ordinary interviews. No frame
receipts, transcripts, quick answers or ordinary usage meters are invoked.
Legacy devices lack a server epoch: reject whole segments starting before the
answer window, and fail closed on future timestamps instead of adjusting clocks.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field, replace
from uuid import uuid4

from app.ports.realtime_speech import RealtimePublisherRecord
from app.services.mock_interview_repository import mock_error, round_state

MOCK_PUBLISHER_PREFIX = "rt-mock-"


@dataclass
class LegacyPublisher:
    publisher: RealtimePublisherRecord
    device_id: str
    binding_generation: int
    expected: dict = field(default_factory=lambda: {"microphone": 0, "system": 0})
    generations: dict = field(default_factory=lambda: {"microphone": 0, "system": 0})
    connected: bool = False
    revoked: bool = False
    epoch: str | None = None
    opened_at_ms: int = 0
    desktop: tuple | None = None
    gaps: int = 0


class MockLegacyBridge:
    def __init__(self, runtime):
        self.runtime = runtime
        # At most one publisher per controller (the runtime caps controllers).
        self.sessions: dict[str, LegacyPublisher] = {}

    async def create(self, *, user_id, session_id, device_id, source_kind, client_name):
        runtime = self.runtime
        controller = runtime.controllers.get(session_id)
        if not controller or controller.closed or controller.user_id != user_id:
            raise mock_error("请先打开本场模拟面试页面。", "mock_control_required")
        async with controller.lock:
            binding = await asyncio.to_thread(runtime.validate_device, user_id, session_id)
            if controller.closed:
                raise mock_error("页面连接已关闭，请重新连接。", "mock_control_expired")
            if device_id != binding.device_id or source_kind != "microphone":
                raise mock_error("模拟面试仅允许已绑定助手的麦克风。", "mock_microphone_required", 403)
            if round_state(controller.record).phase in ("preparing", "generating_report", "completed"):
                raise mock_error("本场尚未开始或已经结束。", "mock_not_live")
            old = self.sessions.get(session_id)
            if old and not old.revoked:
                if old.device_id != device_id or old.binding_generation != binding.binding_generation:
                    raise mock_error("请重新连接本场模拟面试。", "mock_binding_changed")
                if old.publisher.expires_at_ms <= runtime.now_ms():
                    # Only a freshly machine-code-authorized discovery can
                    # renew a token; an expired WS token cannot renew itself.
                    old.publisher = replace(old.publisher, expires_at_ms=runtime.now_ms() + 3_600_000)
                    await asyncio.to_thread(runtime.realtime.repository.save_publisher, old.publisher)
                # Repeated discovery/reconnect must not grow publisher history.
                return old.publisher
            now = runtime.now_ms()
            publisher = RealtimePublisherRecord(
                publisher_id=f"mock-publisher-{uuid4().hex}", token=f"{MOCK_PUBLISHER_PREFIX}{uuid4().hex}",
                session_id=session_id, owner_user_id=user_id, source_kind="microphone",
                client_name=client_name[:128], issued_at_ms=now, expires_at_ms=now + 3_600_000)
            await asyncio.to_thread(runtime.realtime.repository.save_publisher, publisher)
            await asyncio.to_thread(runtime.realtime.repository.prune_publishers_for_session,
                                    session_id=session_id, keep_publisher_ids={publisher.publisher_id})
            self.sessions[session_id] = LegacyPublisher(publisher, device_id, binding.binding_generation)
            return publisher

    async def connect(self, token):
        runtime = self.runtime
        entry = next((e for e in self.sessions.values() if e.publisher.token == token), None)
        if entry is None or entry.revoked or entry.connected or entry.publisher.expires_at_ms <= runtime.now_ms():
            raise mock_error("模拟面试收音连接无效或已被占用。", "mock_publisher_unavailable", 403)
        await self.validate(entry)
        sid = entry.publisher.session_id
        # Recheck after the validation await: competing sockets must not win.
        if entry.revoked or entry.connected or sid in runtime.desktops:
            raise mock_error("已有收音通道。", "mock_capture_in_use")
        async def capture(message):
            entry.epoch = message.get("epoch")
            entry.opened_at_ms = runtime.now_ms()
        entry.desktop = (entry.device_id, capture)
        entry.connected = True
        runtime.desktops[sid] = entry.desktop
        return entry

    async def validate(self, entry):
        runtime = self.runtime
        sid = entry.publisher.session_id
        controller = runtime.controllers.get(sid)
        if (entry.revoked or self.sessions.get(sid) is not entry or not controller or controller.closed
                or entry.publisher.expires_at_ms <= runtime.now_ms()
                or round_state(controller.record).phase in ("completed", "generating_report")):
            raise mock_error("模拟面试收音连接已结束。", "mock_session_ended")
        binding = await asyncio.to_thread(runtime.validate_device, controller.user_id, sid)
        if binding.device_id != entry.device_id or binding.binding_generation != entry.binding_generation:
            raise mock_error("桌面绑定已变化，请重新连接。", "mock_binding_changed")

    async def accept(self, entry, frame, pcm):
        runtime = self.runtime
        if (entry.revoked or not entry.connected or frame.type != "audio-frame"
                or frame.device_id != entry.device_id or frame.source_kind not in entry.expected
                or frame.sequence < 0 or frame.codec != "pcm-s16le"
                or frame.sample_rate_hz != 16000 or frame.channels != 1 or len(pcm) % 2):
            raise mock_error("模拟面试音频格式或设备无效。", "mock_invalid_audio", 422)
        channel = frame.source_kind
        expected = entry.expected[channel]
        if frame.sequence > expected:
            entry.gaps += 1
            if entry.gaps >= 5:
                raise mock_error("音频顺序中断，请重新连接。", "mock_audio_sequence_gap")
            return {"kind": "sequence-gap", "payload": {"sourceKind": channel, "expected": expected, "received": frame.sequence}}
        duplicate = frame.sequence < expected
        epoch, opened = entry.epoch, entry.opened_at_ms
        generation = frame.source_generation or 1
        now = runtime.now_ms()
        if frame.captured_at_ms > now + 250 or frame.started_at_ms > frame.captured_at_ms:
            raise mock_error("电脑时间与服务器不一致，请开启系统自动校时后重新连接。", "mock_audio_clock_invalid")
        # Reject the *whole* crossing segment, including later revisions. Never
        # re-label delayed PCM with the current question. Keep the epoch snapshot
        # across awaits so a round change during provider work also fails closed.
        admit = (not duplicate and epoch and channel == "microphone"
                 and generation >= entry.generations[channel]
                 and opened <= frame.started_at_ms <= frame.captured_at_ms
                 and now - frame.captured_at_ms <= 5000)
        if admit and pcm:
            for offset in range(0, len(pcm), runtime.audio.max_frame_bytes):
                if entry.revoked or entry.epoch != epoch:
                    break
                try:
                    await asyncio.to_thread(runtime.audio.ingest, session_id=entry.publisher.session_id,
                        device_id=entry.device_id, epoch=epoch, pcm=pcm[offset:offset + runtime.audio.max_frame_bytes])
                except Exception:
                    if entry.revoked or entry.epoch != epoch:
                        break  # An intentionally closed old round isn't a new-round fault.
                    raise
        entry.expected[channel] = max(expected, frame.sequence + 1)
        entry.generations[channel] = max(entry.generations[channel], generation)
        entry.gaps = 0
        # ACK discarded/non-answer frames too, otherwise old clients keep retrying
        # them forever. ACK is transport acceptance, not answer/transcript storage.
        return {"kind": "terminal-accepted" if frame.is_final and frame.terminal_id else "frame-accepted",
                "payload": {"sourceKind": channel, "sourceId": frame.source_id,
                    "sequence": frame.sequence, "segmentId": frame.segment_id, "revision": frame.revision,
                    "duplicate": duplicate, "acceptedAtMs": now,
                    **({"terminalId": frame.terminal_id} if frame.terminal_id else {})}}

    async def disconnect(self, entry, message=None):
        runtime = self.runtime
        sid = entry.publisher.session_id
        entry.connected = False
        entry.epoch = None
        if runtime.desktops.get(sid) is entry.desktop:
            runtime.desktops.pop(sid, None)
        controller = runtime.controllers.get(sid)
        if controller and not controller.closed and not entry.revoked:
            async with controller.lock:
                state = round_state(controller.record)
                if state.phase in ("speaking", "listening"):
                    await runtime._meter(controller, False)
                    await runtime._cancel(controller.speech)
                    await runtime._close_capture(controller)
                    controller.record = await runtime._transition(controller, state.pause)
                await runtime.publish(controller)
                if message:
                    await controller.send({"type": "error", "message": message})

    async def retire(self, session_id):
        entry = self.sessions.pop(session_id, None)
        if entry:
            entry.revoked = True
            entry.epoch = None
            if self.runtime.desktops.get(session_id) is entry.desktop:
                self.runtime.desktops.pop(session_id, None)
            await asyncio.to_thread(self.runtime.realtime.repository.prune_publishers_for_session,
                                    session_id=session_id, keep_publisher_ids=set())
