"""Edition-gated mock interview API. Never exposes credentials or raw records."""
from __future__ import annotations

import asyncio
import json
from functools import lru_cache

import anyio
from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.core.config import get_settings
from app.core.errors import DomainRequestError
from app.core.logging import utc_now_iso
from app.core.responses import success_response
from app.deps import (authentication_service, billing_service, usage_billing_service, document_repository,
    interview_session_repository, logger, realtime_speech_service, require_authenticated_context,
    storage_port, _configured_realtime_asr_gateway)
from app.schemas.mock_interview import CreateMockInterviewRequest, SelectMockResumeRequest, MockWireCommand
from app.services.mock_interview_audio import MockInterviewAudio
from app.services.mock_interview_generation import MockInterviewGenerator, MockResumeReader
from app.services.mock_interview_jobs import MockInterviewJobs
from app.services.mock_interview_repository import MockInterviewRepository, mock_error
from app.services.mock_interview_runtime import MockInterviewRuntime, public_mock
from app.services.mock_interview_tts import MockInterviewTts


router = APIRouter(prefix="/mock-interviews", tags=["mock-interview"])


def enabled() -> bool:
    settings = get_settings()
    return settings.global_mock_interview_enabled if settings.product_edition == "global" else settings.mock_interview_enabled


def mock_billing_service():
    return usage_billing_service() if get_settings().product_edition == "global" else billing_service()


@lru_cache(maxsize=1)
def mock_runtime() -> MockInterviewRuntime:
    if not enabled():
        raise mock_error("模拟面试尚未开放。", "mock_not_enabled", 404)
    settings = get_settings()
    if not settings.chat_qwen_api_key or not settings.realtime_asr_api_key:
        raise mock_error("模拟面试服务尚未配置。", "mock_not_configured", 503)
    # Ensure additive migrations run after the existing session/billing schema.
    interview_session_repository()
    mock_billing_service()
    if settings.product_edition == "global":
        from app.services.global_mock_interview_repository import GlobalMockInterviewRepository
        repository = GlobalMockInterviewRepository(settings)
    else:
        repository = MockInterviewRepository(settings)
    reader = MockResumeReader(settings, document_repository(), storage_port())
    return MockInterviewRuntime(repository, reader,
        MockInterviewJobs(repository, reader, MockInterviewGenerator(settings)), MockInterviewTts(settings),
        MockInterviewAudio(gateway_factory=lambda: _configured_realtime_asr_gateway(settings, logger()),
            interview_language="en-US" if settings.product_edition == "global" else "zh-CN"), realtime_speech_service())


def require_mock_runtime():
    # A previously cached instance must not bypass a disabled rollout flag.
    if not enabled():
        raise mock_error("模拟面试尚未开放。", "mock_not_enabled", 404)
    return mock_runtime()


def envelope(request, data):
    return success_response(request=request, data=data, timestamp=utc_now_iso())


@router.get("/capabilities")
def capabilities(request: Request):
    return envelope(request, {"enabled": enabled(), "requiredDesktopProtocol": "2.0", "companionUpgradeRequired": False})


@router.get("")
def list_mock(request: Request, auth=Depends(require_authenticated_context), runtime=Depends(require_mock_runtime)):
    return envelope(request, {"sessions": [public_mock(row) for row in runtime.repository.list(user_id=auth.user_id)],
        "quote": runtime.repository.quote(auth.user_id, runtime.now_ms())})


@router.post("")
def create_mock(payload: CreateMockInterviewRequest, request: Request,
                auth=Depends(require_authenticated_context), runtime=Depends(require_mock_runtime)):
    mock_billing_service().state_for_user(user_id=auth.user_id)
    row = runtime.repository.create(user_id=auth.user_id, now_ms=runtime.now_ms(),
        idempotency_key=payload.idempotency_key, title=payload.title, target_role=payload.target_role,
        expected_billing_class=payload.expected_billing_class)
    return envelope(request, public_mock(row))


@router.get("/{session_id}")
def get_mock(session_id: str, request: Request, auth=Depends(require_authenticated_context), runtime=Depends(require_mock_runtime)):
    return envelope(request, public_mock(runtime.repository.get(user_id=auth.user_id, session_id=session_id)))


@router.delete("/{session_id}")
def delete_mock(session_id: str, request: Request, auth=Depends(require_authenticated_context), runtime=Depends(require_mock_runtime)):
    runtime.repository.delete(user_id=auth.user_id, session_id=session_id, now_ms=runtime.now_ms())
    return envelope(request, {"deleted": True})


@router.post("/{session_id}/resume")
async def select_resume(session_id: str, payload: SelectMockResumeRequest, request: Request,
                        auth=Depends(require_authenticated_context), runtime=Depends(require_mock_runtime)):
    # Read/validate before the short versioned transaction. No resume body stored.
    await asyncio.to_thread(runtime.reader.read, user_id=auth.user_id,
        document_id=payload.document_id, version_id=payload.document_version_id)
    controller = runtime.controllers.get(session_id)
    lock = controller.lock if controller and controller.user_id == auth.user_id else asyncio.Lock()
    async with lock:
        row = await runtime.db(runtime.repository.select_resume, user_id=auth.user_id, session_id=session_id,
            expected_version=payload.version, document_id=payload.document_id,
            version_id=payload.document_version_id, now_ms=runtime.now_ms())
        if controller and controller.user_id == auth.user_id:
            controller.record = row
            await runtime.publish(controller)
    return envelope(request, public_mock(row))


async def receive_bounded(socket, limit=16384):
    raw = await socket.receive_text()
    if len(raw) > limit:
        raise ValueError("message too large")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("object required")
    return value


def serial_sender(socket):
    lock = asyncio.Lock()
    async def send(payload):
        async with asyncio.timeout(5):
            async with lock:
                await socket.send_json(payload)
    return send


@router.websocket("/{session_id}/control")
async def mock_control(socket: WebSocket, session_id: str):
    await socket.accept()
    controller = None
    pump = None
    runtime = None
    send = serial_sender(socket)
    try:
        # Authenticate in the first frame, never a token-bearing URL/access log.
        async with asyncio.timeout(5):
            initial = await receive_bounded(socket, 4096)
        runtime = await asyncio.to_thread(require_mock_runtime)
        token = initial.get("accessToken")
        if not isinstance(token, str) or not token:
            raise mock_error("请先登录。", "mock_auth_required", 401)
        auth = await asyncio.to_thread(authentication_service().authenticate_access_token, access_token=token)
        controller = await runtime.attach(user_id=auth.user_id, session_id=session_id, send=send)
        async def flush():
            while not controller.closed:
                await runtime.flush_draft(controller)
                await asyncio.sleep(0.15)
        pump = asyncio.create_task(flush())
        while not controller.closed:
            async with asyncio.timeout(15):
                payload = await receive_bounded(socket)
            try:
                if payload == {"action": "heartbeat"}:
                    await runtime.heartbeat(controller)
                else:
                    command = MockWireCommand.model_validate(payload)
                    await runtime.command(controller, **command.model_dump(by_alias=False))
            except DomainRequestError as exc:
                await send({"type": "error", "code": exc.error_code, "message": exc.message})
                await runtime.publish(controller)
            except ValidationError:
                await send({"type": "error", "code": "mock_invalid_command", "message": "操作参数无效。"})
    except DomainRequestError as exc:
        await send({"type": "error", "code": exc.error_code, "message": exc.message})
    except (WebSocketDisconnect, TimeoutError, ValueError):
        pass
    finally:
        # ASGI disconnect cancellation must not interrupt lease/audio cleanup.
        with anyio.CancelScope(shield=True):
            if pump:
                pump.cancel()
                await asyncio.gather(pump, return_exceptions=True)
            if controller and runtime:
                await runtime.detach(controller)
            try:
                await socket.close()
            except RuntimeError:
                pass


@router.websocket("/{session_id}/microphone")
async def mock_microphone(socket: WebSocket, session_id: str):
    await socket.accept()
    runtime = None
    registration = None
    send = serial_sender(socket)
    try:
        async with asyncio.timeout(5):
            initial = await receive_bounded(socket, 1024)
        runtime = await asyncio.to_thread(require_mock_runtime)
        device_id, manual_code = initial.get("deviceId"), initial.get("manualCode")
        if not isinstance(device_id, str) or not isinstance(manual_code, str):
            raise ValueError("credentials required")
        device = await asyncio.to_thread(runtime.realtime.repository.get_desktop_device_by_code, manual_code)
        if device is None or device.device_id != device_id:
            raise mock_error("机器码或设备不匹配。", "mock_device_mismatch", 403)
        binding = await asyncio.to_thread(runtime.realtime.get_desktop_capture_binding,
                                          device_id=device_id, manual_code=manual_code)
        if binding.session_id != session_id:
            raise mock_error("此设备未绑定本场面试。", "mock_device_mismatch", 403)
        await runtime.db(runtime.repository.get, user_id=binding.owner_user_id, session_id=session_id)
        await asyncio.to_thread(runtime.validate_device, binding.owner_user_id, session_id)
        if session_id in runtime.desktops or len(runtime.desktops) >= runtime.max_controllers:
            raise mock_error("设备通道已连接或当前繁忙。", "mock_device_in_use")
        registration = (device_id, send)
        runtime.desktops[session_id] = registration
        await send({"type": "capture", "epoch": None})
        controller = runtime.controllers.get(session_id)
        if controller:
            await runtime.publish(controller)
        while True:
            async with asyncio.timeout(15):
                message = await socket.receive()
            if message["type"] == "websocket.disconnect":
                break
            if message.get("text") == '{"action":"heartbeat"}':
                await asyncio.to_thread(runtime.validate_device, binding.owner_user_id, session_id)
                await send({"type": "heartbeat"})
                continue
            body = message.get("bytes")
            if not body or len(body) > 32 + runtime.audio.max_frame_bytes:
                raise ValueError("bounded binary PCM required")
            epoch = body[:32].decode("ascii")
            controller = runtime.controllers.get(session_id)
            if (controller and controller.record["data"].get("clock_at_ms") is not None
                    and runtime.repository.interaction_deadline(controller.record) <= runtime.now_ms()):
                await runtime.reap()
            await asyncio.to_thread(runtime.audio.ingest, session_id=session_id,
                device_id=device_id, epoch=epoch, pcm=body[32:])
    except DomainRequestError as exc:
        await send({"type": "error", "code": exc.error_code, "message": exc.message})
    except (WebSocketDisconnect, TimeoutError, ValueError):
        pass
    finally:
        with anyio.CancelScope(shield=True):
            if runtime and registration and runtime.desktops.get(session_id) is registration:
                runtime.desktops.pop(session_id, None)
                controller = runtime.controllers.get(session_id)
                if controller and not controller.closed:
                    async with controller.lock:
                        # Stop billing before waiting for upstream socket close.
                        await runtime._meter(controller, False)
                        await runtime._close_capture(controller)
                        from app.services.mock_interview_repository import round_state
                        state = round_state(controller.record)
                        if state.phase in ("speaking", "listening"):
                            await runtime._cancel(controller.speech)
                            controller.record = await runtime._transition(controller, state.pause)
                        await runtime.publish(controller)
            try:
                await socket.close()
            except RuntimeError:
                pass
