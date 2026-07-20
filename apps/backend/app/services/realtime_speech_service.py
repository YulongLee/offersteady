from __future__ import annotations

import base64
import concurrent.futures
import logging
import queue
import re
import threading
from collections import Counter
from dataclasses import replace
from time import time
from typing import Any
from uuid import uuid4

from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.core.logging import log_event
from app.ports.realtime_speech import (
    AsrUsageReport,
    AudioFrame,
    DesktopDeviceRecord,
    QuestionCandidateRecord,
    RealtimeFrameReceiptRecord,
    RealtimeAsrGatewayPort,
    RealtimeEvent,
    RealtimePublisherRecord,
    RealtimeSourceKind,
    RealtimeSpeechRepository,
    SessionDesktopBindingRecord,
    TranscriptSegmentRecord,
    TranscriptResult,
    WebSessionHeartbeatRecord,
)
from app.schemas.realtime_speech import (
    DesktopDeviceBindingResponse,
    QuestionCandidateResponse,
    RealtimeFrameReceiptResponse,
    RealtimeEventListResponse,
    RealtimeEventResponse,
    RealtimePublisherResponse,
    RealtimeQuestionCandidateListResponse,
    RealtimeRuntimeCountersResponse,
    RealtimeRuntimePerformanceResponse,
    RealtimeSessionRuntimeResponse,
    RealtimeStageTimingResponse,
    RealtimeSourceHealthResponse,
    RealtimeTranscriptListResponse,
    TranscriptSegmentResponse,
)
from app.services.chat_service import ChatService
from app.services.session_service import SessionService


def _now_ms() -> int:
    return int(time() * 1000)


class RetryableAsrError(Exception):
    pass


class NonRetryableAsrError(Exception):
    pass


class SyntheticRealtimeAsrGateway(RealtimeAsrGatewayPort):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def transcribe(self, *, frame: AudioFrame, attempt: int) -> TranscriptResult:
        try:
            text = frame.audio_bytes.decode("utf-8").strip()
        except UnicodeDecodeError as exc:
            raise NonRetryableAsrError("unreadable_audio_payload") from exc
        if "__asr_retry_once__" in text and attempt == 0:
            raise RetryableAsrError("forced_retryable_asr_failure")
        if "__asr_fail__" in text:
            raise NonRetryableAsrError("forced_permanent_asr_failure")
        low_conf = "__low_conf__" in text
        cleaned = text.replace("__asr_retry_once__", "").replace("__asr_fail__", "").replace("__low_conf__", "").strip() or "（语音内容较短）"
        confidence = 0.72 if low_conf else (0.96 if frame.is_final else 0.78)
        completed_at_ms = _now_ms()
        usage = AsrUsageReport(
            total_tokens=max(1, len(cleaned) // 2),
            provider_name=self.settings.realtime_asr_provider,
            model_name=self.settings.realtime_asr_model,
        )
        return TranscriptResult(
            text=cleaned,
            confidence=confidence,
            overlap=False,
            usage=usage,
            first_text_at_ms=completed_at_ms,
            completed_at_ms=completed_at_ms,
        )


class RealtimeSpeechService:
    def __init__(
        self,
        *,
        settings: Settings,
        logger: logging.Logger,
        repository: RealtimeSpeechRepository,
        session_service: SessionService,
        chat_service: ChatService,
        asr_gateway: RealtimeAsrGatewayPort,
    ) -> None:
        self.settings = settings
        self.logger = logger
        self.repository = repository
        self.session_service = session_service
        self.chat_service = chat_service
        self.asr_gateway = asr_gateway
        self._asr_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="realtime-asr")
        self._latest_timings_by_session_source: dict[tuple[str, RealtimeSourceKind], dict[str, int | None]] = {}
        self._counters_by_session_source: dict[tuple[str, RealtimeSourceKind], dict[str, int]] = {}
        self._active_requests_by_session_source: dict[tuple[str, RealtimeSourceKind], int] = {}
        self._frame_worker_lock = threading.Lock()
        self._frame_workers: dict[tuple[str, RealtimeSourceKind], threading.Thread] = {}
        self._frame_queues: dict[tuple[str, RealtimeSourceKind], "queue.Queue[dict[str, object]]"] = {}

    @staticmethod
    def _session_source_key(session_id: str, source_kind: RealtimeSourceKind) -> tuple[str, RealtimeSourceKind]:
        return (session_id, source_kind)

    def _counter_bucket(self, *, session_id: str, source_kind: RealtimeSourceKind) -> dict[str, int]:
        key = self._session_source_key(session_id, source_kind)
        return self._counters_by_session_source.setdefault(key, {
            "queueDepth": 0,
            "droppedPartialUpdates": 0,
            "connectionRecreations": 0,
            "emptyResultsSuppressed": 0,
            "phantomResultsSuppressed": 0,
            "repetitiveResultsSuppressed": 0,
            "duplicateResultsSuppressed": 0,
            "fillerResultsSuppressed": 0,
            "chunksProduced": 0,
            "chunksUploaded": 0,
            "serializedAudioBytes": 0,
        })

    def _set_latest_timing(self, *, session_id: str, source_kind: RealtimeSourceKind, timing: dict[str, int | None]) -> None:
        self._latest_timings_by_session_source[self._session_source_key(session_id, source_kind)] = timing

    def _latest_timing(self, *, session_id: str, source_kind: RealtimeSourceKind) -> dict[str, int | None] | None:
        return self._latest_timings_by_session_source.get(self._session_source_key(session_id, source_kind))

    def _active_request_enter(self, *, session_id: str, source_kind: RealtimeSourceKind) -> int:
        key = self._session_source_key(session_id, source_kind)
        next_depth = self._active_requests_by_session_source.get(key, 0) + 1
        self._active_requests_by_session_source[key] = next_depth
        self._counter_bucket(session_id=session_id, source_kind=source_kind)["queueDepth"] = max(0, next_depth - 1)
        return next_depth

    def _active_request_leave(self, *, session_id: str, source_kind: RealtimeSourceKind) -> None:
        key = self._session_source_key(session_id, source_kind)
        remaining = max(0, self._active_requests_by_session_source.get(key, 0) - 1)
        if remaining == 0:
            self._active_requests_by_session_source.pop(key, None)
        else:
            self._active_requests_by_session_source[key] = remaining
        self._counter_bucket(session_id=session_id, source_kind=source_kind)["queueDepth"] = max(0, remaining - 1)

    def _gateway_diagnostics(self, *, source_kind: RealtimeSourceKind) -> dict[str, int]:
        diagnostics = getattr(self.asr_gateway, "diagnostics", None)
        if callable(diagnostics):
            payload = diagnostics(source_kind)
            if isinstance(payload, dict):
                return {str(key): int(value) for key, value in payload.items() if isinstance(value, int)}
        return {}

    def _gateway_runtime_status(self, *, source_kind: RealtimeSourceKind) -> dict[str, object]:
        runtime_status = getattr(self.asr_gateway, "runtime_status", None)
        if callable(runtime_status):
            payload = runtime_status(source_kind)
            if isinstance(payload, dict):
                return dict(payload)
        return {}

    def operational_metrics(self) -> dict[str, object]:
        import os
        import resource

        descriptor_root = "/proc/self/fd" if os.path.isdir("/proc/self/fd") else "/dev/fd"
        try:
            file_descriptors = len(os.listdir(descriptor_root))
        except OSError:
            file_descriptors = -1
        usage = resource.getrusage(resource.RUSAGE_SELF)
        queues = {
            f"{session_id}:{source_kind}": work_queue.qsize()
            for (session_id, source_kind), work_queue in self._frame_queues.items()
        }
        return {
            "activeQueueWorkers": sum(1 for worker in self._frame_workers.values() if worker.is_alive()),
            "queueDepthByChannel": queues,
            "queuedFrames": sum(queues.values()),
            "fileDescriptors": file_descriptors,
            "maxResidentSetKb": int(usage.ru_maxrss),
            "asr": {
                source_kind: self._gateway_diagnostics(source_kind=source_kind)  # type: ignore[arg-type]
                for source_kind in ("microphone", "system")
            },
            "rawAudioPersisted": False,
        }

    def register_desktop_device(self, *, device_id: str, manual_code: str, display_name: str, capabilities: dict[str, object]) -> DesktopDeviceRecord:
        code = manual_code.strip()
        if not code.isdigit() or len(code) != 6:
            raise DomainRequestError("realtime-speech", "register-device", "机器码必须是 6 位数字。", 400)
        now_ms = _now_ms()
        existing = self.repository.get_desktop_device_by_code(code)
        generation = (existing.generation + 1) if existing is not None and existing.device_id != device_id.strip() else (existing.generation if existing is not None else 1)
        stored = self.repository.save_desktop_device(DesktopDeviceRecord(
            device_id=device_id.strip(),
            manual_code=code,
            display_name=display_name.strip(),
            capabilities=dict(capabilities),
            registered_at_ms=now_ms,
            last_seen_at_ms=now_ms,
            status="online",
            generation=generation,
        ))
        self._log(logging.INFO, "realtime_speech.desktop_device_registered", session_id="desktop-registration", publisher_id=stored.device_id, state=stored.status)
        return stored

    def bind_desktop_device(self, *, user_id: str, session_id: str, manual_code: str) -> SessionDesktopBindingRecord:
        self.session_service.get_session(user_id=user_id, session_id=session_id)
        code = manual_code.strip()
        device = self.repository.get_desktop_device_by_code(code)
        if device is None:
            raise DomainRequestError("realtime-speech", "bind-device", "未找到对应机器码。请确认电脑伴随程序已打开，并输入 6 位验证码。", 404)
        now_ms = _now_ms()
        binding = self.repository.save_session_desktop_binding(SessionDesktopBindingRecord(
            binding_id=f"desktop-binding-{uuid4().hex}",
            session_id=session_id,
            owner_user_id=user_id,
            device_id=device.device_id,
            manual_code=device.manual_code,
            display_name=device.display_name,
            capabilities=device.capabilities,
            bound_at_ms=now_ms,
            last_seen_at_ms=device.last_seen_at_ms,
            status="bound",
            binding_generation=device.generation,
        ))
        self._save_event(
            session_id=session_id,
            owner_user_id=user_id,
            kind="connection-state",
            payload={"deviceId": binding.device_id, "status": "bound", "displayName": binding.display_name},
        )
        self._log(logging.INFO, "realtime_speech.desktop_device_bound", session_id=session_id, publisher_id=binding.device_id, state=binding.status)
        return binding

    def record_web_session_heartbeat(self, *, user_id: str, session_id: str, binding_id: str | None, page: str) -> WebSessionHeartbeatRecord:
        self.session_service.get_session(user_id=user_id, session_id=session_id)
        safe_page = "live" if page == "live" else "preparation"
        heartbeat = self.repository.save_web_session_heartbeat(WebSessionHeartbeatRecord(
            session_id=session_id,
            owner_user_id=user_id,
            page=safe_page,  # type: ignore[arg-type]
            binding_id=binding_id,
            seen_at_ms=_now_ms(),
        ))
        return heartbeat

    def record_desktop_device_heartbeat(self, *, device_id: str, manual_code: str, display_name: str | None, capabilities: dict[str, object]) -> DesktopDeviceRecord:
        device = self.repository.get_desktop_device_by_code(manual_code.strip())
        if device is None or device.device_id != device_id.strip():
            return self.register_desktop_device(
                device_id=device_id,
                manual_code=manual_code,
                display_name=display_name or "面试稳伴随程序",
                capabilities=capabilities,
            )
        now_ms = _now_ms()
        return self.repository.save_desktop_device(replace(
            device,
            display_name=(display_name.strip() if display_name else device.display_name),
            capabilities={**device.capabilities, **dict(capabilities)},
            last_seen_at_ms=now_ms,
            status="online",
        ))

    def get_desktop_binding(self, *, user_id: str, session_id: str) -> SessionDesktopBindingRecord:
        self.session_service.get_session(user_id=user_id, session_id=session_id)
        binding = self.repository.get_session_desktop_binding(user_id=user_id, session_id=session_id)
        if binding is None:
            raise DomainRequestError("realtime-speech", "get-device-binding", "本场面试尚未绑定电脑伴随程序。", 404)
        return binding

    def get_desktop_active_binding(self, *, device_id: str, manual_code: str) -> SessionDesktopBindingRecord:
        code = manual_code.strip()
        requested_device_id = device_id.strip()
        device = self.repository.get_desktop_device_by_code(code)
        if device is None:
            raise DomainRequestError("realtime-speech", "desktop-active-binding", "这台电脑尚未登记或机器码不匹配。", 404)
        binding = self.repository.get_latest_session_desktop_binding_for_device(device_id=requested_device_id, manual_code=device.manual_code)
        if binding is None and device.device_id != requested_device_id:
            binding = self.repository.get_latest_session_desktop_binding_for_device(device_id=device.device_id, manual_code=device.manual_code)
        if binding is None:
            binding = self.repository.get_latest_session_desktop_binding_by_code(manual_code=device.manual_code)
        if binding is None:
            raise DomainRequestError("realtime-speech", "desktop-active-binding", "网页端尚未输入该机器码绑定面试。", 404)
        if not self._binding_is_active(binding=binding, device=device):
            raise DomainRequestError("realtime-speech", "desktop-active-binding", "网页端绑定已过期，请打开面试页面重新验证机器码。", 404)
        return binding

    def get_desktop_capture_binding(self, *, device_id: str, manual_code: str) -> SessionDesktopBindingRecord:
        code = manual_code.strip()
        requested_device_id = device_id.strip()
        device = self.repository.get_desktop_device_by_code(code)
        if device is None:
            raise DomainRequestError("realtime-speech", "desktop-capture-binding", "这台电脑尚未登记或机器码不匹配。", 404)
        binding = self.repository.get_latest_session_desktop_binding_for_device(device_id=requested_device_id, manual_code=device.manual_code)
        if binding is None and device.device_id != requested_device_id:
            binding = self.repository.get_latest_session_desktop_binding_for_device(device_id=device.device_id, manual_code=device.manual_code)
        if binding is None:
            binding = self.repository.get_latest_session_desktop_binding_by_code(manual_code=device.manual_code)
        if binding is None:
            raise DomainRequestError("realtime-speech", "desktop-capture-binding", "网页端尚未输入该机器码绑定面试。", 404)
        if binding.status != "bound":
            raise DomainRequestError("realtime-speech", "desktop-capture-binding", "网页端绑定已失效，请重新绑定机器码。", 404)
        if binding.binding_generation != device.generation:
            raise DomainRequestError("realtime-speech", "desktop-capture-binding", "伴随程序已重新登记，请在面试页重新绑定机器码。", 404)
        if not self._desktop_device_fresh(device):
            raise DomainRequestError("realtime-speech", "desktop-capture-binding", "电脑伴随程序心跳已过期，请保持伴随程序打开。", 404)
        try:
            session_status = self.session_service.get_session(user_id=binding.owner_user_id, session_id=binding.session_id).status
        except DomainRequestError:
            raise DomainRequestError("realtime-speech", "desktop-capture-binding", "当前面试不存在或已不可用。", 404)
        if session_status not in {"preparing", "live"}:
            raise DomainRequestError("realtime-speech", "desktop-capture-binding", "当前面试已结束，不能继续截图回答。", 409)
        return binding

    def get_desktop_active_binding_by_code(self, *, manual_code: str) -> SessionDesktopBindingRecord:
        code = manual_code.strip()
        device = self.repository.get_desktop_device_by_code(code)
        binding = self.repository.get_latest_session_desktop_binding_by_code(manual_code=code)
        if binding is None:
            if device is None:
                raise DomainRequestError("realtime-speech", "desktop-active-binding", "这台电脑尚未登记或机器码不匹配。", 404)
            raise DomainRequestError("realtime-speech", "desktop-active-binding", "网页端尚未输入该机器码绑定面试。", 404)
        if device is None or not self._binding_is_active(binding=binding, device=device):
            raise DomainRequestError("realtime-speech", "desktop-active-binding", "网页端绑定已过期，请打开面试页面重新验证机器码。", 404)
        return binding

    def get_desktop_pairing_status(self, *, manual_code: str, device_id: str | None = None) -> dict[str, object]:
        code = manual_code.strip()
        if not code.isdigit() or len(code) != 6:
            return {
                "state": "invalid-code",
                "manualCode": code,
                "requestedDeviceId": device_id,
                "registered": False,
                "bound": False,
                "message": "机器码必须是 6 位数字。",
            }
        device = self.repository.get_desktop_device_by_code(code)
        binding = self.repository.get_latest_session_desktop_binding_by_code(manual_code=code)
        if binding is not None:
            session_status = "unknown"
            try:
                session_status = self.session_service.get_session(user_id=binding.owner_user_id, session_id=binding.session_id).status
            except DomainRequestError:
                session_status = "missing"
            active = device is not None and self._binding_is_active(binding=binding, device=device)
            if not active:
                stale_reason = self._binding_stale_reason(binding=binding, device=device)
                return {
                    "state": "stale-bound",
                    "manualCode": code,
                    "requestedDeviceId": device_id,
                    "registered": device is not None and self._desktop_device_fresh(device),
                    "registeredDeviceId": device.device_id if device else binding.device_id,
                    "bound": False,
                    "sessionStatus": session_status,
                    "staleReason": stale_reason,
                    "message": self._stale_binding_message(stale_reason),
                    "binding": self.desktop_binding_response(replace(binding, status="stale")).model_dump(by_alias=True),
                }
            return {
                "state": "bound",
                "manualCode": code,
                "requestedDeviceId": device_id,
                "registered": device is not None,
                "registeredDeviceId": device.device_id if device else binding.device_id,
                "bound": True,
                "sessionStatus": session_status,
                "message": "网页端已绑定本机。",
                "binding": self.desktop_binding_response(binding).model_dump(by_alias=True),
            }
        if device is not None:
            return {
                "state": "registered",
                "manualCode": code,
                "requestedDeviceId": device_id,
                "registered": True,
                "registeredDeviceId": device.device_id,
                "bound": False,
                "message": "这台电脑已登记，网页端尚未绑定该机器码。",
            }
        return {
            "state": "not-registered",
            "manualCode": code,
            "requestedDeviceId": device_id,
            "registered": False,
            "bound": False,
            "message": "后端尚未登记这台电脑，请保持伴随程序打开。",
        }

    def _desktop_device_fresh(self, device: DesktopDeviceRecord) -> bool:
        return (_now_ms() - device.last_seen_at_ms) <= self.settings.realtime_desktop_heartbeat_ttl_seconds * 1000

    def _web_heartbeat_fresh(self, *, user_id: str, session_id: str) -> bool:
        heartbeat = self.repository.get_web_session_heartbeat(user_id=user_id, session_id=session_id)
        if heartbeat is None:
            return False
        return (_now_ms() - heartbeat.seen_at_ms) <= self.settings.realtime_web_heartbeat_ttl_seconds * 1000

    def _binding_is_active(self, *, binding: SessionDesktopBindingRecord, device: DesktopDeviceRecord | None) -> bool:
        if device is None:
            return False
        if binding.status != "bound":
            return False
        if binding.binding_generation != device.generation:
            return False
        if not self._desktop_device_fresh(device):
            return False
        try:
            session_status = self.session_service.get_session(user_id=binding.owner_user_id, session_id=binding.session_id).status
        except DomainRequestError:
            return False
        return session_status in {"preparing", "live"}

    def _binding_stale_reason(self, *, binding: SessionDesktopBindingRecord, device: DesktopDeviceRecord | None) -> str:
        if device is None:
            return "desktop-not-registered"
        if binding.binding_generation != device.generation:
            return "desktop-generation-changed"
        if not self._desktop_device_fresh(device):
            return "desktop-heartbeat-stale"
        try:
            session_status = self.session_service.get_session(user_id=binding.owner_user_id, session_id=binding.session_id).status
        except DomainRequestError:
            return "session-missing"
        if session_status not in {"preparing", "live"}:
            return "session-not-active"
        return "unknown"

    def _require_active_desktop_binding(
        self,
        *,
        publisher: RealtimePublisherRecord,
        device_id: str,
    ) -> SessionDesktopBindingRecord:
        binding = self.repository.get_session_desktop_binding(user_id=publisher.owner_user_id, session_id=publisher.session_id)
        if binding is None:
            raise DomainRequestError(
                "realtime-speech",
                "audio-frame",
                "未检测到本会话的桌面端绑定，请先在网页端输入机器码并完成桌面绑定。",
                409,
                "machine_code_not_bound",
            )
        if binding.device_id != device_id:
            raise DomainRequestError(
                "realtime-speech",
                "audio-frame",
                "桌面采集端设备与会话绑定设备不一致，请检查当前机器码并重新绑定。",
                409,
                "desktop_device_mismatch",
            )
        device = self.repository.get_desktop_device_by_code(binding.manual_code)
        stale_reason = self._binding_stale_reason(binding=binding, device=device)
        if stale_reason != "unknown":
            raise DomainRequestError(
                "realtime-speech",
                "audio-frame",
                self._stale_binding_message(stale_reason),
                409,
                stale_reason,
            )
        return binding

    @staticmethod
    def _stale_binding_message(reason: str) -> str:
        return {
            "desktop-not-registered": "后端没有这台电脑的在线登记，请保持伴随程序打开。",
            "desktop-generation-changed": "该机器码已被新的电脑登记，历史绑定已失效。",
            "desktop-heartbeat-stale": "电脑伴随程序心跳已过期，请重新打开伴随程序。",
            "web-heartbeat-missing": "网页端没有活跃心跳，请打开面试准备页或面试页重新绑定。",
            "session-missing": "历史绑定的面试不存在。",
            "session-not-active": "历史绑定的面试已结束或不可用。",
        }.get(reason, "历史绑定已失效，请重新验证机器码。")

    def create_publisher(self, *, user_id: str, session_id: str, source_kind: RealtimeSourceKind, client_name: str) -> RealtimePublisherRecord:
        session = self.session_service.get_session(user_id=user_id, session_id=session_id)
        if session.status != "live":
            raise DomainRequestError("realtime-speech", "create-publisher", "只有进行中的面试会话才能创建实时语音发布者。", 400)
        now_ms = _now_ms()
        publisher = RealtimePublisherRecord(
            publisher_id=f"publisher-{uuid4().hex}",
            token=f"rt-{uuid4().hex}",
            session_id=session_id,
            owner_user_id=user_id,
            source_kind=source_kind,
            client_name=client_name.strip(),
            issued_at_ms=now_ms,
            expires_at_ms=now_ms + self.settings.realtime_publisher_ttl_seconds * 1000,
            status="connected",
        )
        stored = self.repository.save_publisher(publisher)
        self._save_event(
            session_id=session_id,
            owner_user_id=user_id,
            kind="connection-state",
            payload={"publisherId": stored.publisher_id, "status": stored.status, "sourceKind": stored.source_kind},
        )
        return stored

    def connect_publisher(self, *, token: str) -> RealtimePublisherRecord:
        publisher = self._require_publisher_token(token)
        if _now_ms() > publisher.expires_at_ms:
            raise DomainRequestError("realtime-speech", "connect", "实时语音发布令牌已过期。", 410)
        connected = self.repository.save_publisher(replace(publisher, connected_at_ms=_now_ms(), status="connected"))
        self._save_event(
            session_id=connected.session_id,
            owner_user_id=connected.owner_user_id,
            kind="connection-state",
            payload={"publisherId": connected.publisher_id, "status": connected.status, "sourceKind": connected.source_kind},
        )
        self._log(logging.INFO, "realtime_speech.publisher_connected", session_id=connected.session_id, publisher_id=connected.publisher_id, state=connected.status)
        return connected

    def disconnect_publisher(self, *, token: str, final_state: str = "closed") -> RealtimePublisherRecord:
        publisher = self._require_publisher_token(token)
        updated = self.repository.save_publisher(replace(publisher, disconnected_at_ms=_now_ms(), status=final_state))  # type: ignore[arg-type]
        self._save_event(
            session_id=updated.session_id,
            owner_user_id=updated.owner_user_id,
            kind="connection-state",
            payload={"publisherId": updated.publisher_id, "status": updated.status, "sourceKind": updated.source_kind},
        )
        return updated

    def process_audio_frame(
        self,
        *,
        token: str,
        device_id: str,
        source_id: str,
        sequence: int,
        source_kind: RealtimeSourceKind,
        segment_id: str,
        revision: int,
        captured_at_ms: int,
        started_at_ms: int,
        ended_at_ms: int,
        duration_ms: int,
        codec: str,
        sample_rate_hz: int,
        channels: int,
        is_final: bool,
        trace_id: str | None,
        sent_at_ms: int | None,
        audio_base64: str,
    ) -> list[dict[str, object]]:
        prepared = self._prepare_audio_frame(
            token=token,
            device_id=device_id,
            source_id=source_id,
            sequence=sequence,
            source_kind=source_kind,
            segment_id=segment_id,
            revision=revision,
            captured_at_ms=captured_at_ms,
            started_at_ms=started_at_ms,
            ended_at_ms=ended_at_ms,
            duration_ms=duration_ms,
            codec=codec,
            sample_rate_hz=sample_rate_hz,
            channels=channels,
            is_final=is_final,
            trace_id=trace_id,
            sent_at_ms=sent_at_ms,
            audio_base64=audio_base64,
        )
        return self._process_prepared_audio_frame(prepared)

    def enqueue_audio_frame(
        self,
        *,
        token: str,
        device_id: str,
        source_id: str,
        sequence: int,
        source_kind: RealtimeSourceKind,
        segment_id: str,
        revision: int,
        captured_at_ms: int,
        started_at_ms: int,
        ended_at_ms: int,
        duration_ms: int,
        codec: str,
        sample_rate_hz: int,
        channels: int,
        is_final: bool,
        trace_id: str | None,
        sent_at_ms: int | None,
        audio_base64: str,
    ) -> list[dict[str, object]]:
        prepared = self._prepare_audio_frame(
            token=token,
            device_id=device_id,
            source_id=source_id,
            sequence=sequence,
            source_kind=source_kind,
            segment_id=segment_id,
            revision=revision,
            captured_at_ms=captured_at_ms,
            started_at_ms=started_at_ms,
            ended_at_ms=ended_at_ms,
            duration_ms=duration_ms,
            codec=codec,
            sample_rate_hz=sample_rate_hz,
            channels=channels,
            is_final=is_final,
            trace_id=trace_id,
            sent_at_ms=sent_at_ms,
            audio_base64=audio_base64,
        )
        key = self._session_source_key(prepared["publisher"].session_id, prepared["frame"].source_kind)  # type: ignore[index]
        with self._frame_worker_lock:
            work_queue = self._frame_queues.get(key)
            worker = self._frame_workers.get(key)
            if work_queue is None:
                work_queue = queue.Queue(maxsize=max(8, self.settings.realtime_ingress_queue_max_frames))
                self._frame_queues[key] = work_queue
            if worker is None or not worker.is_alive():
                worker = threading.Thread(target=self._frame_worker_loop, args=(key, work_queue), daemon=True)
                worker.start()
                self._frame_workers[key] = worker
            counter_bucket = prepared.get("counter_bucket")
            if isinstance(counter_bucket, dict):
                counter_bucket["queueDepth"] = max(counter_bucket.get("queueDepth", 0), work_queue.qsize() + 1)
        try:
            work_queue.put_nowait(prepared)
        except queue.Full:
            counter_bucket = prepared.get("counter_bucket")
            if isinstance(counter_bucket, dict):
                counter_bucket["droppedPartialUpdates"] = int(counter_bucket.get("droppedPartialUpdates", 0)) + 1
            frame = prepared.get("frame")
            if isinstance(frame, AudioFrame) and frame.is_final:
                work_queue.put(prepared, timeout=0.25)
        return []

    def _frame_worker_loop(self, key: tuple[str, RealtimeSourceKind], work_queue: "queue.Queue[dict[str, object]]") -> None:
        while True:
            try:
                job = work_queue.get(timeout=15)
            except queue.Empty:
                with self._frame_worker_lock:
                    if work_queue.empty():
                        self._frame_workers.pop(key, None)
                        self._frame_queues.pop(key, None)
                        return
                    continue
            try:
                self._process_prepared_audio_frame(job)
            except DomainRequestError:
                pass
            finally:
                work_queue.task_done()

    def _prepare_audio_frame(
        self,
        *,
        token: str,
        device_id: str,
        source_id: str,
        sequence: int,
        source_kind: RealtimeSourceKind,
        segment_id: str,
        revision: int,
        captured_at_ms: int,
        started_at_ms: int,
        ended_at_ms: int,
        duration_ms: int,
        codec: str,
        sample_rate_hz: int,
        channels: int,
        is_final: bool,
        trace_id: str | None,
        sent_at_ms: int | None,
        audio_base64: str,
    ) -> dict[str, object]:
        publisher = self._require_publisher_token(token)
        self.session_service.get_session(user_id=publisher.owner_user_id, session_id=publisher.session_id)
        ingest_received_at_ms = _now_ms()
        if source_kind == "mixed":
            degraded = self.repository.save_publisher(replace(publisher, status="degraded"))
            event = self._save_event(
                session_id=degraded.session_id,
                owner_user_id=degraded.owner_user_id,
                kind="degraded",
                payload={"publisherId": degraded.publisher_id, "reason": "mixed-input", "sourceKind": source_kind},
            )
            self._log(logging.WARNING, "realtime_speech.degraded", session_id=degraded.session_id, publisher_id=degraded.publisher_id, state="degraded", error_code="mixed_input")
            return {"early_events": [self._event_payload(event)]}
        audio_bytes = base64.b64decode(audio_base64.encode("utf-8"))
        frame = AudioFrame(
            publisher_id=publisher.publisher_id,
            session_id=publisher.session_id,
            device_id=device_id,
            source_id=source_id,
            source_kind=source_kind,
            segment_id=segment_id,
            revision=revision,
            sequence=sequence,
            captured_at_ms=captured_at_ms,
            started_at_ms=started_at_ms,
            ended_at_ms=ended_at_ms,
            duration_ms=duration_ms,
            codec=codec,  # type: ignore[arg-type]
            sample_rate_hz=sample_rate_hz,
            channels=channels,
            is_final=is_final,
            trace_id=trace_id,
            sent_at_ms=sent_at_ms,
            audio_bytes=audio_bytes,
        )
        if not frame.audio_bytes:
            self.repository.save_publisher(replace(publisher, status="receiving-audio"))
            degraded = self._save_event(
                session_id=publisher.session_id,
                owner_user_id=publisher.owner_user_id,
                kind="degraded",
                payload={
                    "publisherId": publisher.publisher_id,
                    "reason": "empty-audio-frame",
                    "sourceKind": source_kind,
                    "message": "该音频帧为空，已跳过本次转写。",
                },
            )
            return {"early_events": [self._event_payload(degraded)]}
        counter_bucket = self._counter_bucket(session_id=publisher.session_id, source_kind=source_kind)
        counter_bucket["chunksProduced"] += 1
        counter_bucket["chunksUploaded"] += 1
        counter_bucket["serializedAudioBytes"] += len(audio_bytes)
        previous_receipts = self.repository.list_frame_receipts_for_session(session_id=publisher.session_id)
        previous = next((item for item in previous_receipts if item.source_kind == source_kind and item.source_id == source_id), None)
        pending_receipt = self.repository.save_frame_receipt(RealtimeFrameReceiptRecord(
            session_id=publisher.session_id,
            owner_user_id=publisher.owner_user_id,
            publisher_id=publisher.publisher_id,
            device_id=device_id,
            source_id=source_id,
            source_kind=source_kind,
            sequence=sequence,
            frame_count=(previous.frame_count + 1 if previous is not None else 1),
            captured_at_ms=captured_at_ms,
            received_at_ms=_now_ms(),
            asr_status="pending",
        ))
        return {
            "publisher": publisher,
            "frame": frame,
            "pending_receipt": pending_receipt,
            "counter_bucket": counter_bucket,
            "ingest_received_at_ms": ingest_received_at_ms,
            "captured_at_ms": captured_at_ms,
            "sent_at_ms": sent_at_ms,
            "source_kind": source_kind,
        }

    def _process_prepared_audio_frame(self, prepared: dict[str, object]) -> list[dict[str, object]]:
        early_events = prepared.get("early_events")
        if isinstance(early_events, list):
            return early_events
        publisher = prepared["publisher"]
        frame = prepared["frame"]
        pending_receipt = prepared["pending_receipt"]
        counter_bucket = prepared["counter_bucket"]
        ingest_received_at_ms = int(prepared["ingest_received_at_ms"])
        captured_at_ms = int(prepared["captured_at_ms"])
        sent_at_ms = prepared.get("sent_at_ms")
        source_kind = prepared["source_kind"]
        assert isinstance(publisher, RealtimePublisherRecord)
        assert isinstance(frame, AudioFrame)
        assert isinstance(pending_receipt, RealtimeFrameReceiptRecord)
        assert isinstance(counter_bucket, dict)
        assert isinstance(source_kind, str)
        events: list[dict[str, object]] = []
        queue_depth = self._active_request_enter(session_id=publisher.session_id, source_kind=source_kind)
        worker_dequeued_at_ms = _now_ms()
        asr_started_at_ms = worker_dequeued_at_ms
        try:
            transcript, transcript_result = self._transcribe_frame(publisher=publisher, frame=frame)
            self.repository.save_frame_receipt(replace(pending_receipt, asr_status="accepted"))
        except DomainRequestError as exc:
            self.repository.save_frame_receipt(replace(pending_receipt, asr_status="failed", error_code=exc.error_code or "asr-failed"))
            events.append(self._event_payload(self._save_event(
                session_id=publisher.session_id,
                owner_user_id=publisher.owner_user_id,
                kind="degraded",
                payload={
                    "reason": "asr-frame-failed",
                    "sourceKind": source_kind,
                    "errorCode": exc.error_code or "asr-failed",
                    "message": str(exc),
                },
            )))
            return events
        finally:
            self._active_request_leave(session_id=publisher.session_id, source_kind=source_kind)
            self._counter_bucket(session_id=publisher.session_id, source_kind=source_kind)["queueDepth"] = max(0, queue_depth - 1)
        published_at_ms = _now_ms()
        timing = {
            "traceId": frame.trace_id,
            "captureToSendMs": (max(0, int(sent_at_ms) - captured_at_ms) if isinstance(sent_at_ms, int) else None),
            "sendToIngestMs": (max(0, ingest_received_at_ms - int(sent_at_ms)) if isinstance(sent_at_ms, int) else None),
            "captureToIngestMs": max(0, ingest_received_at_ms - captured_at_ms),
            "queueWaitMs": max(0, worker_dequeued_at_ms - ingest_received_at_ms),
            "asrTtftMs": (max(0, transcript_result.first_text_at_ms - asr_started_at_ms) if transcript_result.first_text_at_ms is not None else None),
            "finalTranscriptMs": (max(0, transcript_result.completed_at_ms - asr_started_at_ms) if transcript_result.completed_at_ms is not None else None),
            "backendPushMs": max(0, published_at_ms - (transcript_result.completed_at_ms or asr_started_at_ms)),
            "captureToPublishMs": max(0, published_at_ms - captured_at_ms),
            "frontendRenderMs": None,
        }
        self._set_latest_timing(session_id=publisher.session_id, source_kind=source_kind, timing=timing)
        if transcript is None:
            if transcript_result.suppressed_reason == "empty-transcript":
                counter_bucket["emptyResultsSuppressed"] += 1
                if not frame.is_final:
                    counter_bucket["phantomResultsSuppressed"] += 1
                return events
            if transcript_result.suppressed_reason == "filler-transcript":
                counter_bucket["fillerResultsSuppressed"] += 1
                events.append(self._event_payload(self._save_event(
                    session_id=publisher.session_id,
                    owner_user_id=publisher.owner_user_id,
                    kind="degraded",
                    payload={
                        "reason": "filler-transcript-suppressed",
                        "sourceKind": source_kind,
                        "message": "检测到口头语或极短碎片发言，系统已忽略本段结果。",
                    },
                )))
            if transcript_result.suppressed_reason == "repetitive-transcript":
                counter_bucket["repetitiveResultsSuppressed"] += 1
                events.append(self._event_payload(self._save_event(
                    session_id=publisher.session_id,
                    owner_user_id=publisher.owner_user_id,
                    kind="degraded",
                    payload={
                        "reason": "repetitive-transcript-suppressed",
                        "sourceKind": source_kind,
                        "message": "检测到异常重复转写，系统已忽略本段结果。",
                    },
                )))
            if transcript_result.suppressed_reason == "duplicate-nearby-transcript":
                counter_bucket["duplicateResultsSuppressed"] += 1
                events.append(self._event_payload(self._save_event(
                    session_id=publisher.session_id,
                    owner_user_id=publisher.owner_user_id,
                    kind="degraded",
                    payload={
                        "reason": "duplicate-nearby-transcript-suppressed",
                        "sourceKind": source_kind,
                        "message": "检测到短时间内高度重复的转写，系统已忽略本段结果。",
                    },
                )))
            return events
        transcript = self.repository.save_transcript(replace(transcript, published_at_ms=published_at_ms, performance=timing))
        if not self._is_meaningful_transcript(transcript.text):
            counter_bucket["emptyResultsSuppressed"] += 1
            if not frame.is_final:
                counter_bucket["phantomResultsSuppressed"] += 1
            return events
        events.append(self._event_payload(self._save_event(
            session_id=publisher.session_id,
            owner_user_id=publisher.owner_user_id,
            kind="transcript-updated",
            payload={
                "segmentId": transcript.segment_id,
                "revision": transcript.revision,
                "role": transcript.role,
                "text": transcript.text,
                "isFinal": transcript.is_final,
                "publishedAtMs": transcript.published_at_ms,
                "performance": transcript.performance,
            },
        )))
        if transcript.usage is not None:
            self.session_service.record_usage(
                user_id=publisher.owner_user_id,
                session_id=publisher.session_id,
                usage_kind="other",
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=transcript.usage.total_tokens,
                provider_name=transcript.usage.provider_name,
                model_name=transcript.usage.model_name,
                related_task_id=transcript.segment_id,
            )
        if transcript.is_final:
            self.session_service.append_context(
                user_id=publisher.owner_user_id,
                session_id=publisher.session_id,
                role=transcript.role,
                source_kind=f"realtime-{transcript.source_kind}",
                content=transcript.text,
                visibility="session",
                related_task_id=transcript.segment_id,
            )
            candidate = self._maybe_detect_question(transcript=transcript)
            if candidate is not None:
                events.append(self._event_payload(self._save_event(
                    session_id=publisher.session_id,
                    owner_user_id=publisher.owner_user_id,
                    kind="question-candidate" if candidate.state == "needs-confirmation" else "question-confirmed",
                    payload={"candidateId": candidate.candidate_id, "state": candidate.state, "text": candidate.text, "confidence": candidate.confidence},
                )))
                if candidate.state == "confirmed":
                    answer_task, _ = self.chat_service.answer_question(
                        user_id=publisher.owner_user_id,
                        session_id=publisher.session_id,
                        question=candidate.text,
                        stream=True,
                    )
                    candidate = self.repository.save_candidate(replace(candidate, answer_task_id=answer_task.task_id, updated_at_ms=_now_ms()))
                    events.append(self._event_payload(self._save_event(
                        session_id=publisher.session_id,
                        owner_user_id=publisher.owner_user_id,
                        kind="answer-completed",
                        payload={"candidateId": candidate.candidate_id, "taskId": answer_task.task_id, "status": answer_task.status, "answerText": answer_task.answer_text},
                    )))
        return events

    def confirm_candidate(self, *, user_id: str, candidate_id: str) -> QuestionCandidateRecord:
        candidate = self._require_candidate(user_id=user_id, candidate_id=candidate_id)
        if candidate.state != "needs-confirmation":
            return candidate
        answer_task, _ = self.chat_service.answer_question(
            user_id=user_id,
            session_id=candidate.session_id,
            question=candidate.text,
            stream=True,
        )
        confirmed = self.repository.save_candidate(
            replace(candidate, state="confirmed", reason="user-confirmed", answer_task_id=answer_task.task_id, updated_at_ms=_now_ms())
        )
        self._save_event(
            session_id=confirmed.session_id,
            owner_user_id=user_id,
            kind="question-confirmed",
            payload={"candidateId": confirmed.candidate_id, "taskId": answer_task.task_id, "text": confirmed.text},
        )
        return confirmed

    def dismiss_candidate(self, *, user_id: str, candidate_id: str) -> QuestionCandidateRecord:
        candidate = self._require_candidate(user_id=user_id, candidate_id=candidate_id)
        dismissed = self.repository.save_candidate(replace(candidate, state="dismissed", reason="user-dismissed", updated_at_ms=_now_ms()))
        self._save_event(
            session_id=dismissed.session_id,
            owner_user_id=user_id,
            kind="question-candidate",
            payload={"candidateId": dismissed.candidate_id, "state": dismissed.state, "text": dismissed.text},
        )
        return dismissed

    def get_runtime(self, *, user_id: str, session_id: str) -> RealtimeSessionRuntimeResponse:
        session = self.session_service.get_session(user_id=user_id, session_id=session_id)
        binding = self.repository.get_session_desktop_binding(user_id=user_id, session_id=session_id)
        device = self.repository.get_desktop_device_by_code(binding.manual_code) if binding is not None else None
        publishers = [item for item in self.repository.list_publishers_for_session(session_id=session_id) if item.owner_user_id == user_id]
        transcripts = [item for item in self.repository.list_transcripts_for_session(session_id=session_id) if item.owner_user_id == user_id]
        candidates = [item for item in self.repository.list_candidates_for_session(session_id=session_id) if item.owner_user_id == user_id]
        events = [item for item in self.repository.list_events_for_session(session_id=session_id) if item.owner_user_id == user_id]
        latest_device_status = next((item for item in reversed(events) if item.kind == "device-status"), None)
        web_heartbeat = self.repository.get_web_session_heartbeat(user_id=user_id, session_id=session_id)
        raw_health = latest_device_status.payload.get("sourceHealth", []) if latest_device_status is not None else []
        source_health = [self._runtime_source_health(item) for item in raw_health if isinstance(item, dict)]
        source_health_by_kind = {item.source_kind: item for item in source_health}
        receipts = [item for item in self.repository.list_frame_receipts_for_session(session_id=session_id) if item.owner_user_id == user_id]
        latest_state = publishers[-1].status if publishers else None
        last_degraded = next((item for item in reversed(events) if item.kind == "degraded"), None)
        last_failed_receipt = next((item for item in reversed(receipts) if item.asr_status == "failed"), None)
        last_error_code = (
            str(last_degraded.payload.get("errorCode") or last_degraded.payload.get("reason"))
            if last_degraded else
            str(last_failed_receipt.error_code)
            if last_failed_receipt and last_failed_receipt.error_code is not None
            else None
        )
        if binding is None:
            stage = "registered"
        elif session.status != "live":
            stage = "bound"
        elif any(item.status in {"transcribing"} for item in publishers):
            stage = "transcribing"
        elif transcripts:
            stage = "web-visible"
        elif receipts:
            stage = "publishing"
        elif latest_state in {"failed", "degraded"}:
            stage = latest_state
        else:
            stage = "live"
        counters_by_source: dict[str, RealtimeRuntimeCountersResponse] = {}
        latest_by_source: dict[str, RealtimeStageTimingResponse] = {}
        for source_kind in ("microphone", "system"):
            counter_bucket = self._counter_bucket(session_id=session_id, source_kind=source_kind)  # type: ignore[arg-type]
            diagnostics = self._gateway_diagnostics(source_kind=source_kind)  # type: ignore[arg-type]
            runtime_status = self._gateway_runtime_status(source_kind=source_kind)  # type: ignore[arg-type]
            counter_bucket["connectionRecreations"] = diagnostics.get("connection_recreations", counter_bucket.get("connectionRecreations", 0))
            counters_by_source[source_kind] = RealtimeRuntimeCountersResponse(**counter_bucket)
            latest_timing = self._latest_timing(session_id=session_id, source_kind=source_kind)  # type: ignore[arg-type]
            if latest_timing is not None:
                latest_by_source[source_kind] = RealtimeStageTimingResponse(**latest_timing)
            existing_health = source_health_by_kind.get(source_kind)
            if existing_health is not None:
                updated_health = existing_health.model_copy(update={
                    "provider_mode": runtime_status.get("mode"),
                    "provider_connection_state": runtime_status.get("connection_state"),
                    "provider_error_code": runtime_status.get("last_error_code"),
                })
                source_health[source_health.index(existing_health)] = updated_health
        evidence = self._runtime_evidence(
            session_status=session.status,
            binding_present=binding is not None,
            publishers=publishers,
            source_health=source_health,
            receipts=receipts,
            transcripts=transcripts,
            web_heartbeat=web_heartbeat,
        )
        anomaly_reasons, dominant_bottleneck = self._classify_runtime_anomalies(
            session_status=session.status,
            machine_code_bound=binding is not None,
            source_health=source_health,
            receipts=receipts,
            latest_by_source=latest_by_source,
            counters_by_source=counters_by_source,
            latest_state=latest_state,
            last_error_code=last_error_code,
            evidence=evidence,
        )
        return RealtimeSessionRuntimeResponse(
            sessionId=session_id,
            sessionStatus=session.status,
            stage=stage,
            backendReachable=True,
            deviceRegistered=device is not None,
            machineCodeBound=binding is not None,
            sessionLive=session.status == "live",
            manualCode=binding.manual_code if binding else None,
            deviceId=binding.device_id if binding else None,
            displayName=binding.display_name if binding else None,
            publishers=[self._publisher_response(item) for item in publishers],
            sourceHealth=source_health,
            frameReceipts=[RealtimeFrameReceiptResponse(
                sourceKind=item.source_kind,
                sourceId=item.source_id,
                frameCount=item.frame_count,
                lastFrameAtMs=item.received_at_ms,
                lastSequence=item.sequence,
                lastAsrStatus=item.asr_status,
                lastErrorCode=item.error_code,
            ) for item in receipts],
            transcriptCount=len(transcripts),
            questionCandidateCount=len(candidates),
            latestState=latest_state,
            lastErrorCode=last_error_code,
            anomalyReasons=anomaly_reasons,
            dominantBottleneck=dominant_bottleneck,
            performance=RealtimeRuntimePerformanceResponse(
                latestBySource=latest_by_source,
                countersBySource=counters_by_source,
            ),
            evidence=evidence,
            updatedAtMs=_now_ms(),
        )

    def _classify_runtime_anomalies(
        self,
        *,
        session_status: str,
        machine_code_bound: bool,
        source_health: list[RealtimeSourceHealthResponse],
        receipts: list[RealtimeFrameReceiptRecord],
        latest_by_source: dict[str, RealtimeStageTimingResponse],
        counters_by_source: dict[str, RealtimeRuntimeCountersResponse],
        latest_state: str | None,
        last_error_code: str | None,
        evidence: dict[str, object],
    ) -> tuple[list[str], str | None]:
        reasons: list[str] = []
        if not machine_code_bound:
            return ["machine_code_not_bound"], "machine_code_not_bound"
        if session_status != "live":
            return ["session_not_live"], "session_not_live"
        if evidence.get("sessionLive") and not evidence.get("localSignalObserved") and not evidence.get("realFrameReceiptReceived"):
            reasons.append("desktop_no_audio_frames")
        if evidence.get("localSignalObserved") and not evidence.get("realFrameReceiptReceived"):
            reasons.append("backend-no-receipt")
        if not evidence.get("localSignalObserved") and not evidence.get("realFrameReceiptReceived"):
            reasons.append("capture-no-frame")
        if not evidence.get("publisherCreated"):
            reasons.append("publisher-no-connect")
        if evidence.get("transcriptEmitted") and not evidence.get("webConsumerSeen"):
            reasons.append("web-no-consumer")
        for source_kind, timing in latest_by_source.items():
            if (timing.capture_to_send_ms or 0) > 180:
                reasons.append(f"{source_kind}:desktop_send_backlog")
            if (timing.queue_wait_ms or 0) > 120:
                reasons.append(f"{source_kind}:backend_ingest_queue_delayed")
            if (timing.asr_ttft_ms or 0) > 700:
                reasons.append(f"{source_kind}:provider_partial_timeout")
            if (timing.final_transcript_ms or 0) > 1600:
                reasons.append(f"{source_kind}:provider_final_timeout")
            if (timing.backend_push_ms or 0) > 250:
                reasons.append(f"{source_kind}:publish_lag")
        suppression_reasons: list[str] = []
        for source_kind, counters in counters_by_source.items():
            if counters.filler_results_suppressed > 0:
                suppression_reasons.append(f"{source_kind}:filler_transcript_suppressed")
            if counters.repetitive_results_suppressed > 0:
                suppression_reasons.append(f"{source_kind}:repetitive_transcript_suppressed")
            if counters.duplicate_results_suppressed > 0:
                suppression_reasons.append(f"{source_kind}:duplicate_transcript_suppressed")
        if suppression_reasons:
            reasons.extend(suppression_reasons)
        if evidence.get("asrAccepted") and not evidence.get("transcriptEmitted"):
            # Keep this as lower-priority than suppression counters; it is a provider-signal anomaly
            # and should not hide root-cause like repetitive suppression.
            reasons.append("asr-accepted-no-text")
        if latest_state == "failed" or (last_error_code is not None and "asr" in last_error_code):
            reasons.append("provider_failed")
        return reasons, (reasons[0] if reasons else None)


    def _runtime_evidence(
        self,
        *,
        session_status: str,
        binding_present: bool,
        publishers: list[RealtimePublisherRecord],
        source_health: list[RealtimeSourceHealthResponse],
        receipts: list[RealtimeFrameReceiptRecord],
        transcripts: list[TranscriptSegmentRecord],
        web_heartbeat: WebSessionHeartbeatRecord | None,
    ) -> dict[str, object]:
        real_receipts = [item for item in receipts if item.source_id != "diagnostic-pcm-probe" and item.frame_count > 0]
        diagnostic_receipts = [item for item in receipts if item.source_id == "diagnostic-pcm-probe" and item.frame_count > 0]
        local_signal_sources = [
            item.source_kind for item in source_health
            if (item.level or 0) > 0 or item.last_signal_at_ms is not None or (item.frame_count or 0) > 0
        ]
        real_frame_sources = sorted({item.source_kind for item in real_receipts})
        accepted_sources = sorted({item.source_kind for item in receipts if item.asr_status == "accepted"})
        return {
            "bindingReady": binding_present,
            "sessionLive": session_status == "live",
            "publisherCreated": len(publishers) > 0,
            "publisherCount": len(publishers),
            "localSignalObserved": len(local_signal_sources) > 0,
            "localSignalSources": sorted(set(local_signal_sources)),
            "realFrameReceiptReceived": len(real_receipts) > 0,
            "realFrameSources": real_frame_sources,
            "diagnosticProbeFrameReceived": len(diagnostic_receipts) > 0,
            "asrAccepted": any(item.asr_status == "accepted" for item in receipts),
            "asrAcceptedSources": accepted_sources,
            "transcriptEmitted": len(transcripts) > 0,
            "transcriptCount": len(transcripts),
            "webConsumerSeen": web_heartbeat is not None and web_heartbeat.page == "live",
            "webConsumerLastSeenAtMs": web_heartbeat.seen_at_ms if web_heartbeat else None,
        }

    def list_transcripts(self, *, user_id: str, session_id: str) -> RealtimeTranscriptListResponse:
        self.session_service.get_session(user_id=user_id, session_id=session_id)
        transcripts = [item for item in self.repository.list_transcripts_for_session(session_id=session_id) if item.owner_user_id == user_id]
        return RealtimeTranscriptListResponse(sessionId=session_id, transcripts=[self._transcript_response(item) for item in transcripts])

    def list_candidates(self, *, user_id: str, session_id: str):
        self.session_service.get_session(user_id=user_id, session_id=session_id)
        candidates = [item for item in self.repository.list_candidates_for_session(session_id=session_id) if item.owner_user_id == user_id]
        return RealtimeQuestionCandidateListResponse(sessionId=session_id, candidates=[self._candidate_response(item) for item in candidates])

    def list_events(self, *, user_id: str, session_id: str):
        self.session_service.get_session(user_id=user_id, session_id=session_id)
        events = [item for item in self.repository.list_events_for_session(session_id=session_id) if item.owner_user_id == user_id]
        return RealtimeEventListResponse(
            sessionId=session_id,
            events=[RealtimeEventResponse(eventId=item.event_id, kind=item.kind, payload=item.payload, createdAtMs=item.created_at_ms) for item in events],
        )

    def session_activity_version(self, *, user_id: str, session_id: str) -> int:
        self.session_service.get_session(user_id=user_id, session_id=session_id)
        return self.repository.get_session_activity_version(session_id=session_id)

    def publish_device_status(
        self,
        *,
        user_id: str,
        session_id: str,
        device_id: str,
        capture_state: str,
        source_health: list[dict[str, object]],
        capabilities: dict[str, object],
    ) -> RealtimeEventResponse:
        self.session_service.get_session(user_id=user_id, session_id=session_id)
        safe_source_health = [
            {
                "sourceId": str(item.get("sourceId", "")),
                "sourceKind": str(item.get("sourceKind", "")),
                "label": str(item.get("label", ""))[:120],
                "state": str(item.get("state", "")),
                "stage": item.get("stage"),
                "level": float(item.get("level", 0) or 0),
                "lastSignalAtMs": item.get("lastSignalAtMs"),
                "frameCount": item.get("frameCount"),
                "lastFrameAtMs": item.get("lastFrameAtMs"),
                "backendFrameCount": item.get("backendFrameCount"),
                "lastBackendFrameAtMs": item.get("lastBackendFrameAtMs"),
                "errorCode": item.get("errorCode"),
            }
            for item in source_health
        ]
        event = self._save_event(
            session_id=session_id,
            owner_user_id=user_id,
            kind="device-status",
            payload={
                "deviceId": device_id,
                "captureState": capture_state,
                "sourceHealth": safe_source_health,
                "capabilities": {
                    "platform": capabilities.get("platform"),
                    "architecture": capabilities.get("architecture"),
                    "protocolVersion": capabilities.get("protocolVersion"),
                    "appVersion": capabilities.get("appVersion"),
                    "microphone": capabilities.get("microphone"),
                    "systemAudio": capabilities.get("systemAudio"),
                },
            },
        )
        return RealtimeEventResponse(eventId=event.event_id, kind=event.kind, payload=event.payload, createdAtMs=event.created_at_ms)

    def _transcribe_frame(self, *, publisher: RealtimePublisherRecord, frame: AudioFrame) -> tuple[TranscriptSegmentRecord | None, TranscriptResult]:
        role = "candidate" if frame.source_kind == "microphone" else "interviewer"
        last_error: Exception | None = None
        asr_timeout_seconds = self._asr_timeout_seconds(frame)
        for attempt in range(self.settings.realtime_asr_retry_max_attempts + 1):
            try:
                self.repository.save_publisher(replace(publisher, status="transcribing"))
                future = self._asr_executor.submit(self.asr_gateway.transcribe, frame=frame, attempt=attempt)
                try:
                    result = future.result(timeout=asr_timeout_seconds)
                except concurrent.futures.TimeoutError as exc:
                    future.cancel()
                    self._log(logging.WARNING, "realtime_speech.transcribe_timeout", session_id=publisher.session_id, publisher_id=publisher.publisher_id, state="transcribe-timeout", error_code="realtime_asr_frame_timeout")
                    raise RetryableAsrError("realtime_asr_frame_timeout") from exc
                suppression_reason = self._suppression_reason(result.text, frame=frame)
                if suppression_reason is None:
                    suppression_reason = self._duplicate_nearby_suppression_reason(
                        text=result.text,
                        publisher=publisher,
                        frame=frame,
                    )
                if suppression_reason is not None:
                    self.repository.save_publisher(replace(publisher, status="receiving-audio"))
                    return None, replace(result, suppressed_reason=suppression_reason)
                current = self.repository.get_transcript(frame.session_id, frame.segment_id)
                created_at_ms = current.created_at_ms if current is not None else _now_ms()
                published_at_ms = _now_ms()
                performance = {
                    "traceId": frame.trace_id,
                    "captureToSendMs": (max(0, frame.sent_at_ms - frame.captured_at_ms) if frame.sent_at_ms is not None else None),
                    "sendToIngestMs": None,
                    "captureToIngestMs": None,
                    "queueWaitMs": None,
                    "asrTtftMs": None,
                    "finalTranscriptMs": None,
                    "backendPushMs": None,
                    "captureToPublishMs": max(0, published_at_ms - frame.captured_at_ms),
                    "frontendRenderMs": None,
                }
                stored = self.repository.save_transcript(
                    TranscriptSegmentRecord(
                        segment_id=frame.segment_id,
                        session_id=frame.session_id,
                        owner_user_id=publisher.owner_user_id,
                        source_id=frame.source_id,
                        source_kind=frame.source_kind,
                        role=role,  # type: ignore[arg-type]
                        revision=max(frame.revision, current.revision + 1 if current is not None else frame.revision),
                        text=result.text,
                        transcript_confidence=result.confidence,
                        started_at_ms=frame.started_at_ms,
                        ended_at_ms=frame.ended_at_ms,
                        is_final=frame.is_final,
                        overlap=result.overlap,
                        created_at_ms=created_at_ms,
                        published_at_ms=published_at_ms,
                        performance=performance,
                        usage=result.usage,
                    )
                )
                self.repository.save_publisher(replace(publisher, status="receiving-audio"))
                return stored, result
            except RetryableAsrError as exc:
                self._log(logging.WARNING, "realtime_speech.transcribe_retry", session_id=publisher.session_id, publisher_id=publisher.publisher_id, state="transcribe-retry", error_code=str(exc))
                last_error = exc
                continue
            except NonRetryableAsrError as exc:
                self._log(logging.WARNING, "realtime_speech.transcribe_non_retryable", session_id=publisher.session_id, publisher_id=publisher.publisher_id, state="transcribe-failed", error_code=str(exc))
                last_error = exc
                break
            except Exception as exc:
                self._log(logging.ERROR, "realtime_speech.transcribe_error", session_id=publisher.session_id, publisher_id=publisher.publisher_id, state="transcribe-error", error_code=str(exc))
                last_error = exc
                break
        failed = self.repository.save_publisher(replace(publisher, status="failed"))
        self._save_event(
            session_id=failed.session_id,
            owner_user_id=failed.owner_user_id,
            kind="degraded",
            payload={"publisherId": failed.publisher_id, "reason": "asr-failed", "errorCode": last_error.__class__.__name__ if last_error else "asr_failed"},
        )
        error_code = str(last_error) if last_error and str(last_error).strip() else "asr-failed"
        raise DomainRequestError("realtime-speech", "transcribe", "实时语音转写失败。", 502, error_code=error_code)

    def _asr_timeout_seconds(self, frame: AudioFrame) -> float:
        configured = max(1.0, float(self.settings.realtime_asr_frame_timeout_seconds))
        if frame.is_final:
            configured = max(
                configured,
                float(self.settings.realtime_asr_finalize_timeout_seconds) + 1.0,
            )
        return min(30.0, configured)

    @staticmethod
    def _suppression_reason(text: str, *, frame: AudioFrame) -> str | None:
        if not RealtimeSpeechService._is_meaningful_transcript(text):
            return "empty-transcript"
        if RealtimeSpeechService._looks_like_filler_transcript(text, source_kind=frame.source_kind):
            return "filler-transcript"
        if RealtimeSpeechService._looks_like_repetitive_hallucination(text, source_kind=frame.source_kind):
            return "repetitive-transcript"
        return None

    @staticmethod
    def _is_meaningful_transcript(text: str) -> bool:
        compact = re.sub(r"\s+|[，。！？、；：,.!?;:~～…·]+", "", text).strip()
        return bool(compact)

    @staticmethod
    def _looks_like_filler_transcript(text: str, *, source_kind: RealtimeSourceKind) -> bool:
        compact = re.sub(r"\s+", "", text)
        compact = re.sub(r"[，。！？、；：,.!?;:~～…·]+", "", compact)
        if not compact:
            return True
        filler_tokens = (
            "嗯", "啊", "呃", "额", "唉", "诶", "欸", "哦", "喔", "哎",
            "那个", "这个", "就是", "然后", "对", "是的", "好的", "行", "好", "哈", "嘿",
        )
        if len(compact) <= 4 and compact in filler_tokens:
            return True
        if compact.lower() in {"system", "assistant", "test"}:
            return True
        filler_pattern = "|".join(sorted((re.escape(item) for item in filler_tokens), key=len, reverse=True))
        stripped = re.sub(f"({filler_pattern})+", "", compact)
        if not stripped and len(compact) <= 12:
            return True
        if source_kind == "microphone" and len(compact) <= 8 and re.fullmatch(r"(.)\1{1,}", compact):
            return True
        return False

    @staticmethod
    def _looks_like_repetitive_hallucination(text: str, *, source_kind: RealtimeSourceKind) -> bool:
        normalized = re.sub(r"\s+", "", text)
        normalized = re.sub(r"[，。！？、；：,.!?;:]+", "|", normalized).strip("|")
        compact = normalized.replace("|", "")
        if len(compact) < 48:
            return False
        clauses = [item for item in normalized.split("|") if item]
        if len(clauses) >= 4:
            counts: dict[str, int] = {}
            for clause in clauses:
                counts[clause] = counts.get(clause, 0) + 1
            most_common = max(counts.values())
            if len(counts) <= max(2, len(clauses) // 4) and most_common / len(clauses) >= 0.6:
                return True
            adjacent_repeat_count = 0
            for index in range(1, len(clauses)):
                previous = clauses[index - 1]
                current = clauses[index]
                shorter, longer = sorted((previous, current), key=len)
                if shorter and (current == previous or longer.count(shorter) >= 2):
                    adjacent_repeat_count += 1
            if adjacent_repeat_count >= max(2, len(clauses) // 3):
                return True
        if len(compact) >= 64:
            windows = [compact[index:index + 10] for index in range(0, max(0, len(compact) - 9), 2)]
            windows = [item for item in windows if len(item) == 10]
            if windows:
                repeated_windows = sum(1 for count in Counter(windows).values() if count >= 3)
                if repeated_windows >= max(2, len(windows) // 10):
                    return True
        if source_kind == "system":
            windows = [compact[index:index + 12] for index in range(0, max(0, len(compact) - 11), 3)]
            windows = [item for item in windows if len(item) == 12]
            if windows:
                unique_windows = len(set(windows))
                if unique_windows / len(windows) <= 0.35:
                    return True
            if len(compact) >= 96:
                clause_lengths = [len(item) for item in clauses] if clauses else [len(compact)]
                if clause_lengths and sum(clause_lengths) / len(clause_lengths) >= 12:
                    repeated_prefixes = sum(1 for index in range(1, len(clauses)) if clauses[index][:10] == clauses[index - 1][:10])
                    if repeated_prefixes >= max(2, len(clauses) // 3):
                        return True
        return False

    def _duplicate_nearby_suppression_reason(
        self,
        *,
        text: str,
        publisher: RealtimePublisherRecord,
        frame: AudioFrame,
    ) -> str | None:
        compact = re.sub(r"\s+", "", text)
        compact = re.sub(r"[，。！？、；：,.!?;:]+", "", compact)
        if len(compact) < 2 or len(compact) > 24:
            return None
        transcripts = [
            item for item in self.repository.list_transcripts_for_session(session_id=frame.session_id)
            if item.owner_user_id == publisher.owner_user_id
            and item.source_kind == frame.source_kind
            and item.role == ("candidate" if frame.source_kind == "microphone" else "interviewer")
            and self._is_meaningful_transcript(item.text)
            and item.is_final
        ]
        if not transcripts:
            return None
        latest = transcripts[-1]
        previous_compact = re.sub(r"\s+", "", latest.text)
        previous_compact = re.sub(r"[，。！？、；：,.!?;:]+", "", previous_compact)
        if not previous_compact:
            return None
        if abs(frame.started_at_ms - latest.ended_at_ms) > 6_000:
            return None
        if compact == previous_compact:
            return "duplicate-nearby-transcript"
        if len(compact) <= 32 and len(previous_compact) <= 32:
            if compact in previous_compact or previous_compact in compact:
                return "duplicate-nearby-transcript"
        shorter, longer = sorted((compact, previous_compact), key=len)
        if len(shorter) >= 2 and longer.count(shorter) >= 2:
            return "duplicate-nearby-transcript"
        return None

    @staticmethod
    def _runtime_source_health(item: dict[str, object]) -> RealtimeSourceHealthResponse:
        return RealtimeSourceHealthResponse(
            sourceId=str(item.get("sourceId", "")),
            sourceKind=str(item.get("sourceKind", "")),
            label=str(item.get("label", ""))[:120],
            state=str(item.get("state", "unknown")),
            stage=str(item.get("stage")) if item.get("stage") is not None else None,
            level=float(item.get("level", 0) or 0),
            lastSignalAtMs=int(item["lastSignalAtMs"]) if item.get("lastSignalAtMs") is not None else None,
            frameCount=int(item["frameCount"]) if item.get("frameCount") is not None else None,
            lastFrameAtMs=int(item["lastFrameAtMs"]) if item.get("lastFrameAtMs") is not None else None,
            backendFrameCount=int(item["backendFrameCount"]) if item.get("backendFrameCount") is not None else None,
            lastBackendFrameAtMs=int(item["lastBackendFrameAtMs"]) if item.get("lastBackendFrameAtMs") is not None else None,
            errorCode=str(item.get("errorCode")) if item.get("errorCode") is not None else None,
            providerMode=str(item.get("providerMode")) if item.get("providerMode") is not None else None,
            providerConnectionState=str(item.get("providerConnectionState")) if item.get("providerConnectionState") is not None else None,
            providerErrorCode=str(item.get("providerErrorCode")) if item.get("providerErrorCode") is not None else None,
        )

    def _maybe_detect_question(self, *, transcript: TranscriptSegmentRecord) -> QuestionCandidateRecord | None:
        if transcript.source_kind != "system":
            return None
        text = transcript.text.strip()
        if not self._looks_like_question(text):
            return None
        confidence = transcript.transcript_confidence
        if confidence < self.settings.realtime_question_auto_confirm_threshold:
            return self.repository.save_candidate(
                QuestionCandidateRecord(
                    candidate_id=f"question:{transcript.session_id}:{transcript.segment_id}",
                    session_id=transcript.session_id,
                    owner_user_id=transcript.owner_user_id,
                    source_segment_ids=[transcript.segment_id],
                    text=text,
                    state="needs-confirmation",
                    reason="low-transcript-confidence",
                    confidence=confidence,
                    created_at_ms=_now_ms(),
                    updated_at_ms=_now_ms(),
                )
            )
        return self.repository.save_candidate(
            QuestionCandidateRecord(
                candidate_id=f"question:{transcript.session_id}:{transcript.segment_id}",
                session_id=transcript.session_id,
                owner_user_id=transcript.owner_user_id,
                source_segment_ids=[transcript.segment_id],
                text=text,
                state="confirmed",
                reason="auto-confirmed",
                confidence=confidence,
                created_at_ms=_now_ms(),
                updated_at_ms=_now_ms(),
            )
        )

    @staticmethod
    def _looks_like_question(text: str) -> bool:
        lowered = text.strip().lower()
        return lowered.endswith(("?", "？")) or any(
            key in lowered
            for key in ["请介绍", "讲讲", "怎么", "如何", "为什么", "请说明", "describe", "tell me", "what", "how", "why"]
        )

    def _require_publisher_token(self, token: str) -> RealtimePublisherRecord:
        publisher = self.repository.get_publisher_by_token(token)
        if publisher is None:
            raise DomainRequestError("realtime-speech", "publisher-token", "实时语音发布令牌无效。", 404)
        return publisher

    def _require_candidate(self, *, user_id: str, candidate_id: str) -> QuestionCandidateRecord:
        candidate = self.repository.get_candidate(candidate_id)
        if candidate is None:
            raise DomainRequestError("realtime-speech", "candidate", "问题候选不存在。", 404)
        if candidate.owner_user_id != user_id:
            raise DomainRequestError("realtime-speech", "candidate", "不能操作其他用户的问题候选。", 403)
        return candidate

    def _save_event(self, *, session_id: str, owner_user_id: str, kind, payload: dict[str, object]) -> RealtimeEvent:
        return self.repository.save_event(
            RealtimeEvent(
                event_id=f"rt-event-{uuid4().hex}",
                session_id=session_id,
                owner_user_id=owner_user_id,
                kind=kind,
                payload=payload,
                created_at_ms=_now_ms(),
            )
        )

    @staticmethod
    def _event_payload(event: RealtimeEvent) -> dict[str, object]:
        return {"kind": event.kind, "payload": event.payload, "eventId": event.event_id, "createdAtMs": event.created_at_ms}

    @staticmethod
    def desktop_binding_response(record: SessionDesktopBindingRecord) -> DesktopDeviceBindingResponse:
        return DesktopDeviceBindingResponse(
            bindingId=record.binding_id,
            sessionId=record.session_id,
            ownerUserId=record.owner_user_id,
            deviceId=record.device_id,
            manualCode=record.manual_code,
            displayName=record.display_name,
            capabilities=record.capabilities,
            status=record.status,
            boundAtMs=record.bound_at_ms,
            lastSeenAtMs=record.last_seen_at_ms,
            bindingGeneration=record.binding_generation,
        )

    @staticmethod
    def _publisher_response(record: RealtimePublisherRecord) -> RealtimePublisherResponse:
        return RealtimePublisherResponse(
            publisherId=record.publisher_id,
            token=record.token,
            sessionId=record.session_id,
            ownerUserId=record.owner_user_id,
            sourceKind=record.source_kind,
            clientName=record.client_name,
            issuedAtMs=record.issued_at_ms,
            expiresAtMs=record.expires_at_ms,
            connectedAtMs=record.connected_at_ms,
            disconnectedAtMs=record.disconnected_at_ms,
            status=record.status,
        )

    @staticmethod
    def _transcript_response(record: TranscriptSegmentRecord) -> TranscriptSegmentResponse:
        return TranscriptSegmentResponse(
            segmentId=record.segment_id,
            sourceId=record.source_id,
            sourceKind=record.source_kind,
            role=record.role,
            revision=record.revision,
            text=record.text,
            transcriptConfidence=record.transcript_confidence,
            startedAtMs=record.started_at_ms,
            endedAtMs=record.ended_at_ms,
            isFinal=record.is_final,
            overlap=record.overlap,
            createdAtMs=record.created_at_ms,
            publishedAtMs=record.published_at_ms,
            performance=(RealtimeStageTimingResponse(**record.performance) if record.performance is not None else None),
        )

    @staticmethod
    def _candidate_response(record: QuestionCandidateRecord) -> QuestionCandidateResponse:
        return QuestionCandidateResponse(
            candidateId=record.candidate_id,
            sourceSegmentIds=record.source_segment_ids,
            text=record.text,
            state=record.state,
            reason=record.reason,
            confidence=record.confidence,
            answerTaskId=record.answer_task_id,
            createdAtMs=record.created_at_ms,
            updatedAtMs=record.updated_at_ms,
        )

    def _log(self, level: int, event: str, *, session_id: str, publisher_id: str | None, state: str, error_code: str | None = None) -> None:
        log_event(
            self.logger,
            level,
            settings=self.settings,
            event=event,
            feature="realtime-speech",
            action="realtime-audio",
            session_id=session_id,
            publisher_id=publisher_id,
            state=state,
            error_code=error_code,
        )
