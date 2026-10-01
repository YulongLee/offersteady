"""Dedicated mock controller; normal interview prompts, ASR and billing stay untouched.

Single application worker only. Durable leases still fence reconnects and stale
provider results; process-local microphone channels fail closed on worker loss.
"""
from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass, field
from time import time
from typing import Awaitable, Callable

from app.core.errors import DomainRequestError
from app.services.mock_interview_audio import MockInterviewAudio
from app.services.mock_interview_legacy import MockLegacyBridge
from app.services.mock_interview_repository import MockInterviewRepository, mock_error, round_state


def public_mock(record: dict) -> dict:
    data = record["data"]
    return {"sessionId": record["session_id"], "billingClass": record["billing_class"],
        "refunded": record["refunded"], "createdAtMs": record["created_at_ms"],
        "title": data["title"], "targetRole": data["target_role"], "state": data["state"],
        "resumeId": data.get("resume_id"), "resumeVersion": data.get("resume_version"),
        "report": data.get("report"), "error": data.get("error"),
        "billableMs": data["billable_ms"], "billedMinutes": data["billed_minutes"],
        "interacting": data.get("clock_at_ms") is not None,
        "partial": len([r for r in data["state"]["rounds"] if r.get("answer")]) < 10}


@dataclass
class MockController:
    user_id: str
    session_id: str
    token: str
    record: dict
    send: Callable[[dict], Awaitable[None]]
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    generation: asyncio.Task | None = None
    speech: asyncio.Task | None = None
    speech_question: str | None = None
    has_audio: bool = False
    closed: bool = False
    draft: tuple[str, str] | None = None
    binding_released: bool = False


class MockInterviewRuntime:
    max_controllers = 64

    def __init__(self, repository, reader, jobs, tts, audio: MockInterviewAudio, realtime, *, now_ms=None):
        self.repository = repository
        self.reader = reader
        self.jobs = jobs
        self.tts = tts
        self.audio = audio
        self.realtime = realtime
        self.now_ms = now_ms or (lambda: int(time() * 1000))
        self.controllers: dict[str, MockController] = {}
        self.desktops: dict[str, tuple[str, Callable]] = {}
        self.legacy = MockLegacyBridge(self)
        self._admission = asyncio.Lock()
        self._next_offline_scan_ms = self.now_ms() + 30_000
        self._offline_jobs: dict[str, asyncio.Task] = {}

    async def db(self, method, **kwargs):
        return await asyncio.to_thread(method, **kwargs)

    def validate_device(self, user_id: str, session_id: str):
        binding, _ = self._device_readiness(user_id, session_id)
        return binding

    def _device_readiness(self, user_id: str, session_id: str):
        session = self.realtime.session_service.get_session(user_id=user_id, session_id=session_id)
        if session.session_mode != "mock" or session.status not in ("preparing", "live"):
            raise mock_error("本场模拟面试已结束或不可用。", "mock_session_ended")
        binding = self.realtime.get_desktop_binding(user_id=user_id, session_id=session_id)
        device = self.realtime.repository.get_desktop_device_by_code(binding.manual_code)
        if (device is None or binding.status != "bound" or binding.binding_generation != device.generation
                or binding.device_id != device.device_id or not self.realtime._desktop_device_fresh(device)):
            raise mock_error("请先连接在线的桌面助手。", "mock_desktop_unavailable")
        if (device.capabilities.get("mockInterviewProtocol") != 1
                and device.capabilities.get("protocolVersion") != "2.0"):
            raise mock_error("无法确认助手的麦克风上传协议，请重新连接当前正式版助手。", "mock_desktop_incompatible")
        permission = self.realtime._permission_status(device).get("microphone")
        # Shipped v2 companions report "unknown" in main-process heartbeats,
        # even after the OS grants microphone access. It is not a denial. Keep
        # device authorization intact; the existing OS-controlled capture and
        # authenticated audio channel are still required to answer.
        deferred_permission = (device.capabilities.get("mockInterviewProtocol") != 1
                               and device.capabilities.get("protocolVersion") == "2.0"
                               and permission in (None, "unknown"))
        if permission != "granted" and not deferred_permission:
            raise mock_error("请在助手中开启麦克风权限。", "mock_microphone_required")
        return binding, deferred_permission

    async def attach(self, *, user_id: str, session_id: str, send) -> MockController:
        async with self._admission:
            if session_id in self.controllers:
                raise mock_error("面试已经在另一页面打开。", "mock_control_in_use")
            if len(self.controllers) >= self.max_controllers:
                raise mock_error("模拟面试繁忙，请稍后再试。", "mock_control_busy", 503)
            record = await self.db(self.repository.acquire_control, user_id=user_id,
                session_id=session_id, now_ms=self.now_ms())
            controller = MockController(user_id, session_id, record["data"]["control_token"], record, send)
            self.controllers[session_id] = controller
        # Reconnecting never silently resumes the microphone or replays audio.
        try:
            state = round_state(record)
            if state.phase in ("speaking", "listening"):
                controller.record = await self._transition(controller, state.pause)
            await self.publish(controller)
        except BaseException:
            await self.detach(controller)
            raise
        return controller

    async def publish(self, controller):
        if not controller.closed:
            if round_state(controller.record).phase in ("generating_report", "completed"):
                await self._release_binding(controller)
            ready = controller.session_id in self.desktops
            preparation = None
            if round_state(controller.record).phase == "preparing":
                try:
                    _, deferred = await asyncio.to_thread(self._device_readiness, controller.user_id, controller.session_id)
                    ready = True
                    preparation = {"ready": True, "code": "mock_permission_deferred" if deferred else "mock_ready",
                        "message": ("助手已连接，可开始面试。现有助手不回报实时权限状态；请确认助手已获麦克风授权，开始后再连接收音通道。"
                                    if deferred else "助手已就绪，可以开始模拟面试。")}
                except DomainRequestError as exc:
                    ready = False
                    preparation = {"ready": False, "code": exc.error_code, "message": exc.message}
            await controller.send({"type": "state", "session": public_mock(controller.record),
                                   "desktopConnected": ready,
                                   "preparation": preparation,
                                   "microphoneConnected": controller.session_id in self.desktops})

    async def _release_binding(self, controller):
        if not controller.binding_released:
            await self.legacy.retire(controller.session_id)
            # The base session is already durably ended. Reuse only the existing
            # owner-scoped cleanup operation, not ordinary start/audio/billing.
            await asyncio.to_thread(self.realtime.terminate_session_for_admin,
                user_id=controller.user_id, session_id=controller.session_id, reason="mock-ended")
            controller.binding_released = True

    async def _transition(self, controller, move):
        return await self.db(self.repository.transition, user_id=controller.user_id,
            session_id=controller.session_id, expected_version=round_state(controller.record).version,
            now_ms=self.now_ms(), move=lambda _: move())

    async def _meter(self, controller, active=None, *, renew_lease=True):
        controller.record = await self.db(self.repository.control_tick, user_id=controller.user_id,
            session_id=controller.session_id, control_token=controller.token,
            now_ms=self.now_ms(), active=active, renew_lease=renew_lease)
        return controller.record["data"].get("clock_at_ms") is not None

    async def _cancel(self, task):
        if task and not task.done() and task is not asyncio.current_task():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def _close_capture(self, controller):
        capture = self.audio.revoke(controller.session_id)
        controller.draft = None
        desktop = self.desktops.get(controller.session_id)
        if desktop:
            try:
                await desktop[1]({"type": "capture", "epoch": None})
            except Exception:
                pass
        await asyncio.to_thread(self.audio.close, capture)

    async def _open_capture(self, controller):
        binding = await asyncio.to_thread(self.validate_device, controller.user_id, controller.session_id)
        desktop = self.desktops.get(controller.session_id)
        if not desktop or desktop[0] != binding.device_id:
            raise mock_error("请等待桌面助手连接模拟面试通道。", "mock_desktop_unavailable")
        state = round_state(controller.record)
        if not await self._meter(controller, True):
            controller.record = await self._transition(controller, state.pause)
            return
        loop = asyncio.get_running_loop()
        def sink(epoch, text):
            # Coalesce updates in a single slot, never queue one task per token.
            loop.call_soon_threadsafe(self._draft, controller, epoch, text)
        self.audio.open(session_id=controller.session_id, owner_id=controller.user_id,
            device_id=binding.device_id, epoch=state.capture_epoch,
            deadline_ms=self.repository.interaction_deadline(controller.record), sink=sink)
        await desktop[1]({"type": "capture", "epoch": state.capture_epoch})

    def _draft(self, controller, epoch, text):
        if not controller.closed and round_state(controller.record).capture_epoch == epoch:
            controller.draft = (epoch, text)

    async def flush_draft(self, controller):
        if controller.draft and not controller.closed:
            epoch, text = controller.draft
            controller.draft = None
            await controller.send({"type": "transcript", "epoch": epoch, "text": text})

    async def heartbeat(self, controller):
        async with controller.lock:
            was_active = controller.record["data"].get("clock_at_ms") is not None
            await self._meter(controller)
            state = round_state(controller.record)
            if state.phase in ("speaking", "listening") and not controller.record["data"].get("clock_at_ms"):
                if state.phase == "listening" or was_active:
                    await self._cancel(controller.speech)
                    await self._close_capture(controller)
                    controller.record = await self._transition(controller, state.pause)
            if state.capture_epoch:
                self.audio.renew(controller.session_id, state.capture_epoch,
                                 self.repository.interaction_deadline(controller.record))
            if state.phase not in ("completed", "generating_report"):
                # Existing idle reaper must see an actually connected mock page.
                # This does not start ordinary ASR, metering or answer tasks.
                try:
                    await asyncio.to_thread(self.realtime.record_web_session_heartbeat,
                        user_id=controller.user_id, session_id=controller.session_id,
                        binding_id=None, page="preparation" if state.phase == "preparing" else "live")
                except DomainRequestError:
                    await self._cancel(controller.speech)
                    await self._cancel(controller.generation)
                    await self._close_capture(controller)
                    controller.record = await self._transition(controller, state.end)
                    self._generate(controller)
            await self.publish(controller)

    async def command(self, controller, *, action: str, version: int, question_id=None,
                      answer=None, submission_id=None):
        async with controller.lock:
            if controller.closed:
                raise mock_error("连接已关闭。", "mock_control_expired")
            # Renew/check the durable fence before any external action.
            await self._meter(controller)
            state = round_state(controller.record)
            if state.version != version:
                # A duplicate answer must match the original payload exactly.
                if action == "submit" and any(r.submission_id == submission_id for r in state.rounds):
                    state.submit(question_id=question_id, answer=answer, submission_id=submission_id)
                    await self.publish(controller)
                    return
                raise mock_error("面试状态已更新，请重试当前操作。", "mock_version_conflict")
            if action == "start":
                data = controller.record["data"]
                await asyncio.to_thread(self.validate_device, controller.user_id, controller.session_id)
                if not data.get("resume_id") or not data.get("resume_version"):
                    raise mock_error("请先选择已解析的简历。", "mock_resume_required")
                await asyncio.to_thread(self.reader.read, user_id=controller.user_id,
                    document_id=data["resume_id"], version_id=data["resume_version"])
                controller.record = await self._transition(controller, state.start)
                self._generate(controller)
            elif action == "retry":
                if controller.generation and not controller.generation.done():
                    raise mock_error("正在生成，请稍候。", "mock_generation_in_progress")
                controller.record = await self._transition(controller, state.retry_generation)
                self._generate(controller)
            elif action == "speak":
                if state.phase != "speaking" or state.rounds[-1].question_id != question_id:
                    raise mock_error("不是当前待朗读的题目。", "mock_stale_round")
                if controller.speech and not controller.speech.done():
                    raise mock_error("正在朗读，请稍候。", "mock_speech_in_progress")
                controller.has_audio = False
                controller.speech_question = question_id
                controller.speech = asyncio.create_task(self._speak(controller, state))
            elif action in ("playback_started", "playback_waiting"):
                if not controller.has_audio or controller.speech_question != question_id or state.phase != "speaking":
                    raise mock_error("本题尚未开始播放。", "mock_playback_not_ready")
                active = await self._meter(controller, action == "playback_started")
                if action == "playback_started" and not active:
                    await self._cancel(controller.speech)
                    controller.record = await self._transition(controller, state.pause)
            elif action in ("listen", "replay", "pause", "resume", "submit", "end"):
                move = {"listen": lambda: state.listen(question_id, self.now_ms()),
                        "replay": lambda: state.replay(question_id), "pause": state.pause,
                        "resume": lambda: state.resume(self.now_ms()),
                        "submit": lambda: state.submit(question_id=question_id, answer=answer, submission_id=submission_id),
                        "end": state.end}[action]
                # Validate first so a stale/invalid command cannot close live audio.
                following = move()
                if following != state:
                    # Stop the interaction clock and fence old output before
                    # waiting for provider shutdown/cancellation.
                    controller.record = await self._transition(controller, move)
                    await self._cancel(controller.speech)
                    await self._close_capture(controller)
                    if action == "end":
                        await self._cancel(controller.generation)
                    if following.phase == "listening":
                        try:
                            await self._open_capture(controller)
                        except Exception:
                            current = round_state(controller.record)
                            await self._meter(controller, False)
                            controller.record = await self._transition(controller, current.pause)
                            raise
                    if following.phase in ("generating_question", "generating_report"):
                        self._generate(controller)
            else:
                raise mock_error("未知操作。", "mock_invalid_command", 422)
            await self.publish(controller)

    def _generate(self, controller):
        async def run():
            try:
                await self.jobs.run_pending(user_id=controller.user_id, session_id=controller.session_id)
                async with controller.lock:
                    if controller.closed:
                        return
                    controller.record = await self.db(self.repository.get,
                        user_id=controller.user_id, session_id=controller.session_id)
                    await self.publish(controller)
            except asyncio.CancelledError:
                raise
            except Exception:
                if not controller.closed:
                    await controller.send({"type": "error", "code": "mock_generation_unavailable",
                                           "message": "生成暂时不可用，可在本场重试。"})
        controller.generation = asyncio.create_task(run())

    async def _speak(self, controller, state):
        question = state.rounds[-1]
        try:
            await controller.send({"type": "audio_start", "questionId": question.question_id,
                                   "sampleRate": 24000})
            async for pcm in self.tts.stream(question.question):
                if controller.closed or round_state(controller.record).version != state.version:
                    return
                controller.has_audio = True
                await controller.send({"type": "audio", "questionId": question.question_id,
                                       "pcm": base64.b64encode(pcm).decode("ascii")})
            await controller.send({"type": "audio_end", "questionId": question.question_id})
        except asyncio.CancelledError:
            raise
        except Exception:
            async with controller.lock:
                await self._meter(controller, False)
                await controller.send({"type": "speech_unavailable", "questionId": question.question_id,
                                       "message": "朗读暂时不可用，可重试或阅读题目后开始回答。"})

    async def detach(self, controller):
        if controller.closed:
            return
        controller.closed = True
        await self._cancel(controller.generation)
        await self._cancel(controller.speech)
        async with controller.lock:
            try:
                await self.db(self.repository.release_control, user_id=controller.user_id,
                    session_id=controller.session_id, control_token=controller.token, now_ms=self.now_ms())
            finally:
                try:
                    await self._close_capture(controller)
                finally:
                    try:
                        await self.legacy.retire(controller.session_id)
                    finally:
                        if self.controllers.get(controller.session_id) is controller:
                            self.controllers.pop(controller.session_id, None)

    async def reap(self):
        for controller in list(self.controllers.values()):
            if controller.record["data"].get("lease_until_ms", 0) <= self.now_ms():
                await self.detach(controller)
                continue
            if (controller.record["data"].get("clock_at_ms") is not None
                    and self.repository.interaction_deadline(controller.record) <= self.now_ms()):
                # Paid minute boundary, not a new browser heartbeat. Never extend
                # a disconnected page's control lease from the server timer.
                async with controller.lock:
                    if controller.closed:
                        continue
                    active = await self._meter(controller, renew_lease=False)
                    state = round_state(controller.record)
                    if not active:
                        await self._cancel(controller.speech)
                        await self._close_capture(controller)
                        if state.phase in ("speaking", "listening"):
                            controller.record = await self._transition(controller, state.pause)
                        await self.publish(controller)
                    elif state.capture_epoch:
                        self.audio.renew(controller.session_id, state.capture_epoch,
                                         self.repository.interaction_deadline(controller.record))
        if self.now_ms() >= self._next_offline_scan_ms:
            self._next_offline_scan_ms = self.now_ms() + 30_000
            candidates = await self.db(self.repository.recovery_candidates, now_ms=self.now_ms())
            for record in candidates:
                sid = record["session_id"]
                if sid in self.controllers or sid in self._offline_jobs or len(self._offline_jobs) >= 2:
                    continue
                self._offline_jobs[sid] = asyncio.create_task(self._recover_offline(record))

    async def _recover_offline(self, record):
        sid, user = record["session_id"], record["owner_user_id"]
        try:
            expired = await self.db(self.repository.expire_offline,
                user_id=user, session_id=sid, now_ms=self.now_ms())
            if round_state(expired).phase == "generating_report":
                await asyncio.to_thread(self.realtime.terminate_session_for_admin,
                    user_id=user, session_id=sid, reason="mock-offline")
                await self.jobs.run_pending(user_id=user, session_id=sid)
        except asyncio.CancelledError:
            raise
        except Exception:
            # Safe durable error/retry state is maintained by the jobs adapter.
            pass
        finally:
            self._offline_jobs.pop(sid, None)

    async def shutdown(self):
        await asyncio.gather(*(self.detach(c) for c in list(self.controllers.values())), return_exceptions=True)
        await asyncio.gather(*(self._cancel(task) for task in list(self._offline_jobs.values())), return_exceptions=True)
