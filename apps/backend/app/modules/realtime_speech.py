from __future__ import annotations

import asyncio
import json
from collections import deque
from time import time

from fastapi import APIRouter, Depends, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from app.core.errors import DomainRequestError
from app.core.logging import utc_now_iso
from app.core.responses import success_response
from app.deps import optional_authenticated_context, realtime_speech_service, resolve_owned_user_id
from app.ports.authentication import AuthenticatedRequestContext
from app.schemas.foundation import ApiEnvelope, ModuleDescriptor
from app.schemas.realtime_speech import (
    BindDesktopDeviceRequest,
    CreateRealtimePublisherRequest,
    DesktopDeviceHeartbeatRequest,
    DesktopDeviceBindingResponse,
    RealtimeCandidateCommandRequest,
    RealtimeDeviceStatusRequest,
    RealtimeEventListResponse,
    RealtimePublisherResponse,
    RealtimeQuestionCandidateListResponse,
    RealtimeSessionRuntimeResponse,
    RealtimeTranscriptListResponse,
    RealtimeFrameIngestRequest,
    RealtimeFrameRequest,
    RegisterDesktopDeviceRequest,
    WebSessionHeartbeatRequest,
)
from app.services.realtime_speech_service import RealtimeSpeechService


router = APIRouter(prefix="/realtime-speech", tags=["realtime-speech"])
_active_ingest_tokens: set[str] = set()
descriptor = ModuleDescriptor(
    feature="realtime-speech",
    owningApp="apps/backend",
    routePrefix="/api/v1/realtime-speech",
    mode="active",
    notes="Session-bound realtime speech orchestration for subtitles, question detection, and Chat Service handoff.",
)


def _sse_frame(event: str, payload: dict[str, object], *, cursor: int | None = None) -> str:
    cursor_line = f"id: {cursor}\n" if cursor is not None else ""
    return f"{cursor_line}event: {event}\ndata: {json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}\n\n"


def _fast_desktop_binding_response(*, session_id: str, user_id: str, device_id: str | None = None, manual_code: str | None = None) -> DesktopDeviceBindingResponse:
    now_ms = int(time() * 1000)
    return DesktopDeviceBindingResponse(
        bindingId="local-dev-unbound",
        sessionId=session_id,
        ownerUserId=user_id,
        deviceId=device_id or "local-dev-device",
        manualCode=manual_code or "000000",
        displayName="本地桌面伴随程序",
        capabilities={},
        status="unbound",
        boundAtMs=now_ms,
        lastSeenAtMs=now_ms,
        bindingGeneration=1,
    )


@router.get("/status", response_model=ApiEnvelope[dict[str, str]])
async def status(request: Request, service: RealtimeSpeechService = Depends(realtime_speech_service)) -> ApiEnvelope[dict[str, str]]:
    readiness = getattr(service.repository, "readiness", None)
    runtime_store = "redis" if callable(readiness) and readiness() else "local"
    return success_response(
        request=request,
        data={"status": "active", "feature": "realtime-speech", "runtimeStore": runtime_store, "protocolVersion": service.settings.realtime_protocol_version, "transport": service.settings.realtime_transport_mode},
        timestamp=utc_now_iso(),
    )


@router.get("/metrics", response_model=ApiEnvelope[dict[str, object]])
async def realtime_metrics(request: Request, service: RealtimeSpeechService = Depends(realtime_speech_service)) -> ApiEnvelope[dict[str, object]]:
    return success_response(
        request=request,
        data={
            **service.operational_metrics(),
            "activeDesktopTransports": len(_active_ingest_tokens),
            "protocolVersion": service.settings.realtime_protocol_version,
        },
        timestamp=utc_now_iso(),
    )


@router.post("/publishers", response_model=ApiEnvelope[RealtimePublisherResponse])
async def create_publisher(
    request_context: Request,
    request: CreateRealtimePublisherRequest,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: RealtimeSpeechService = Depends(realtime_speech_service),
) -> ApiEnvelope[RealtimePublisherResponse]:
    publisher = service.create_publisher(
        user_id=resolve_owned_user_id(explicit_user_id=request.user_id, auth_context=auth_context),
        session_id=request.session_id,
        source_kind=request.source_kind,
        client_name=request.client_name,
    )
    return success_response(request=request_context, data=service._publisher_response(publisher), timestamp=utc_now_iso())


@router.post("/desktop-devices/register", response_model=ApiEnvelope[dict[str, object]])
async def register_desktop_device(
    request_context: Request,
    request: RegisterDesktopDeviceRequest,
    service: RealtimeSpeechService = Depends(realtime_speech_service),
) -> ApiEnvelope[dict[str, object]]:
    device = service.register_desktop_device(
        device_id=request.device_id,
        manual_code=request.manual_code,
        display_name=request.display_name or "本地桌面伴随程序",
        capabilities=request.capabilities,
    )
    return success_response(
        request=request_context,
        data={
            "deviceId": device.device_id,
            "manualCode": device.manual_code,
            "displayName": device.display_name,
            "status": device.status,
            "lastSeenAtMs": device.last_seen_at_ms,
            "generation": device.generation,
        },
        timestamp=utc_now_iso(),
    )


@router.post("/desktop-devices/{device_id}/heartbeat", response_model=ApiEnvelope[dict[str, object]])
async def desktop_device_heartbeat(
    device_id: str,
    request_context: Request,
    request: DesktopDeviceHeartbeatRequest,
    service: RealtimeSpeechService = Depends(realtime_speech_service),
) -> ApiEnvelope[dict[str, object]]:
    device = service.record_desktop_device_heartbeat(
        device_id=device_id,
        manual_code=request.manual_code,
        display_name=request.display_name,
        capabilities=request.capabilities,
    )
    return success_response(
        request=request_context,
        data={
            "deviceId": device.device_id,
            "manualCode": device.manual_code,
            "displayName": device.display_name,
            "status": device.status,
            "lastSeenAtMs": device.last_seen_at_ms,
            "generation": device.generation,
        },
        timestamp=utc_now_iso(),
    )


@router.post("/sessions/{session_id}/desktop-binding", response_model=ApiEnvelope[DesktopDeviceBindingResponse])
async def bind_desktop_device(
    session_id: str,
    request_context: Request,
    request: BindDesktopDeviceRequest,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: RealtimeSpeechService = Depends(realtime_speech_service),
) -> ApiEnvelope[DesktopDeviceBindingResponse]:
    binding = service.bind_desktop_device(
        user_id=resolve_owned_user_id(explicit_user_id=request.user_id, auth_context=auth_context),
        session_id=session_id,
        manual_code=request.manual_code,
    )
    return success_response(request=request_context, data=service.desktop_binding_response(binding), timestamp=utc_now_iso())


@router.post("/sessions/{session_id}/web-heartbeat", response_model=ApiEnvelope[dict[str, object]])
async def web_session_heartbeat(
    session_id: str,
    request_context: Request,
    request: WebSessionHeartbeatRequest,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: RealtimeSpeechService = Depends(realtime_speech_service),
) -> ApiEnvelope[dict[str, object]]:
    user_id = resolve_owned_user_id(explicit_user_id=request.user_id, auth_context=auth_context)
    heartbeat = service.record_web_session_heartbeat(
        user_id=user_id,
        session_id=session_id,
        binding_id=request.binding_id,
        page=request.page,
    )
    return success_response(
        request=request_context,
        data={
            "sessionId": heartbeat.session_id,
            "ownerUserId": heartbeat.owner_user_id,
            "bindingId": heartbeat.binding_id,
            "page": heartbeat.page,
            "seenAtMs": heartbeat.seen_at_ms,
        },
        timestamp=utc_now_iso(),
    )


@router.get("/sessions/{session_id}/desktop-binding", response_model=ApiEnvelope[DesktopDeviceBindingResponse])
async def get_desktop_binding(
    session_id: str,
    request: Request,
    user_id: str | None = Query(default=None, alias="userId"),
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: RealtimeSpeechService = Depends(realtime_speech_service),
) -> ApiEnvelope[DesktopDeviceBindingResponse]:
    resolved_user_id = resolve_owned_user_id(explicit_user_id=user_id, auth_context=auth_context)
    binding = service.get_desktop_binding(user_id=resolved_user_id, session_id=session_id)
    return success_response(request=request, data=service.desktop_binding_response(binding), timestamp=utc_now_iso())


@router.get("/desktop-devices/{device_id}/binding", response_model=ApiEnvelope[DesktopDeviceBindingResponse])
async def get_desktop_active_binding(
    device_id: str,
    request: Request,
    manual_code: str = Query(alias="manualCode"),
    service: RealtimeSpeechService = Depends(realtime_speech_service),
) -> ApiEnvelope[DesktopDeviceBindingResponse]:
    binding = service.get_desktop_active_binding(device_id=device_id, manual_code=manual_code)
    return success_response(request=request, data=service.desktop_binding_response(binding), timestamp=utc_now_iso())


@router.get("/desktop-devices/by-code/{manual_code}/binding", response_model=ApiEnvelope[DesktopDeviceBindingResponse])
async def get_desktop_active_binding_by_code(
    manual_code: str,
    request: Request,
    service: RealtimeSpeechService = Depends(realtime_speech_service),
) -> ApiEnvelope[DesktopDeviceBindingResponse]:
    binding = service.get_desktop_active_binding_by_code(manual_code=manual_code)
    return success_response(request=request, data=service.desktop_binding_response(binding), timestamp=utc_now_iso())


@router.get("/desktop-devices/pairing-status", response_model=ApiEnvelope[dict[str, object]])
async def get_desktop_pairing_status(
    request: Request,
    manual_code: str = Query(alias="manualCode"),
    device_id: str | None = Query(default=None, alias="deviceId"),
    service: RealtimeSpeechService = Depends(realtime_speech_service),
) -> ApiEnvelope[dict[str, object]]:
    status = service.get_desktop_pairing_status(manual_code=manual_code, device_id=device_id)
    return success_response(request=request, data=status, timestamp=utc_now_iso())


@router.get("/sessions/{session_id}/runtime", response_model=ApiEnvelope[RealtimeSessionRuntimeResponse])
async def get_runtime(
    session_id: str,
    request: Request,
    user_id: str | None = Query(default=None, alias="userId"),
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: RealtimeSpeechService = Depends(realtime_speech_service),
) -> ApiEnvelope[RealtimeSessionRuntimeResponse]:
    resolved_user_id = resolve_owned_user_id(explicit_user_id=user_id, auth_context=auth_context)
    runtime = service.get_runtime(user_id=resolved_user_id, session_id=session_id)
    return success_response(request=request, data=runtime, timestamp=utc_now_iso())


@router.get("/sessions/{session_id}/stream")
async def stream_session_runtime(
    session_id: str,
    request: Request,
    user_id: str | None = Query(default=None, alias="userId"),
    cursor: int = Query(default=0, ge=0),
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: RealtimeSpeechService = Depends(realtime_speech_service),
) -> StreamingResponse:
    resolved_user_id = resolve_owned_user_id(explicit_user_id=user_id, auth_context=auth_context)

    async def event_stream():
        last_cursor = cursor
        initial = True
        while True:
            if await request.is_disconnected():
                break
            stream_cursor = getattr(service.repository, "get_event_stream_version", None)
            current_cursor = stream_cursor(session_id=session_id) if callable(stream_cursor) else service.repository.get_session_activity_version(session_id=session_id)
            if not initial and current_cursor <= last_cursor:
                yield ": keepalive\n\n"
                await asyncio.sleep(1)
                continue
            runtime = service.get_runtime(user_id=resolved_user_id, session_id=session_id)
            transcripts = service.list_transcripts(user_id=resolved_user_id, session_id=session_id)
            candidates = service.list_candidates(user_id=resolved_user_id, session_id=session_id)
            events = service.list_events(user_id=resolved_user_id, session_id=session_id)
            payload = {
                "type": "snapshot",
                "transcripts": transcripts.model_dump(by_alias=True),
                "candidates": candidates.model_dump(by_alias=True),
                "events": [item.model_dump(by_alias=True) for item in events.events],
                "runtime": runtime.model_dump(by_alias=True),
                "ownerUserId": resolved_user_id,
                "cursor": current_cursor,
            }
            yield _sse_frame("snapshot", payload, cursor=current_cursor)
            last_cursor = current_cursor
            initial = False
            await asyncio.sleep(0.25)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/sessions/{session_id}/transcripts", response_model=ApiEnvelope[RealtimeTranscriptListResponse])
async def list_transcripts(
    session_id: str,
    request: Request,
    user_id: str | None = Query(default=None, alias="userId"),
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: RealtimeSpeechService = Depends(realtime_speech_service),
) -> ApiEnvelope[RealtimeTranscriptListResponse]:
    return success_response(request=request, data=service.list_transcripts(user_id=resolve_owned_user_id(explicit_user_id=user_id, auth_context=auth_context), session_id=session_id), timestamp=utc_now_iso())


@router.get("/sessions/{session_id}/question-candidates", response_model=ApiEnvelope[RealtimeQuestionCandidateListResponse])
async def list_candidates(
    session_id: str,
    request: Request,
    user_id: str | None = Query(default=None, alias="userId"),
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: RealtimeSpeechService = Depends(realtime_speech_service),
) -> ApiEnvelope[RealtimeQuestionCandidateListResponse]:
    return success_response(request=request, data=service.list_candidates(user_id=resolve_owned_user_id(explicit_user_id=user_id, auth_context=auth_context), session_id=session_id), timestamp=utc_now_iso())


@router.post("/question-candidates/{candidate_id}/confirm", response_model=ApiEnvelope[dict[str, object]])
async def confirm_candidate(
    candidate_id: str,
    request_context: Request,
    request: RealtimeCandidateCommandRequest,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: RealtimeSpeechService = Depends(realtime_speech_service),
) -> ApiEnvelope[dict[str, object]]:
    candidate = service.confirm_candidate(user_id=resolve_owned_user_id(explicit_user_id=request.user_id, auth_context=auth_context), candidate_id=candidate_id)
    return success_response(
        request=request_context,
        data={"candidateId": candidate.candidate_id, "state": candidate.state, "answerTaskId": candidate.answer_task_id},
        timestamp=utc_now_iso(),
    )


@router.post("/question-candidates/{candidate_id}/dismiss", response_model=ApiEnvelope[dict[str, object]])
async def dismiss_candidate(
    candidate_id: str,
    request_context: Request,
    request: RealtimeCandidateCommandRequest,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: RealtimeSpeechService = Depends(realtime_speech_service),
) -> ApiEnvelope[dict[str, object]]:
    candidate = service.dismiss_candidate(user_id=resolve_owned_user_id(explicit_user_id=request.user_id, auth_context=auth_context), candidate_id=candidate_id)
    return success_response(
        request=request_context,
        data={"candidateId": candidate.candidate_id, "state": candidate.state},
        timestamp=utc_now_iso(),
    )


@router.get("/sessions/{session_id}/events", response_model=ApiEnvelope[RealtimeEventListResponse])
async def list_events(
    session_id: str,
    request: Request,
    user_id: str | None = Query(default=None, alias="userId"),
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: RealtimeSpeechService = Depends(realtime_speech_service),
) -> ApiEnvelope[RealtimeEventListResponse]:
    return success_response(request=request, data=service.list_events(user_id=resolve_owned_user_id(explicit_user_id=user_id, auth_context=auth_context), session_id=session_id), timestamp=utc_now_iso())


@router.post("/sessions/{session_id}/device-status", response_model=ApiEnvelope[dict[str, object]])
async def publish_device_status(
    session_id: str,
    request_context: Request,
    request: RealtimeDeviceStatusRequest,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: RealtimeSpeechService = Depends(realtime_speech_service),
) -> ApiEnvelope[dict[str, object]]:
    event = service.publish_device_status(
        user_id=resolve_owned_user_id(explicit_user_id=request.user_id, auth_context=auth_context),
        session_id=session_id,
        device_id=request.device_id,
        capture_state=str(request.capture_state),
        source_health=request.source_health,
        capabilities=request.capabilities,
    )
    return success_response(request=request_context, data=event.model_dump(by_alias=True), timestamp=utc_now_iso())


@router.post("/frames", response_model=ApiEnvelope[list[dict[str, object]]])
async def ingest_frame(
    request_context: Request,
    request: RealtimeFrameIngestRequest,
    service: RealtimeSpeechService = Depends(realtime_speech_service),
) -> ApiEnvelope[list[dict[str, object]]]:
    if not service.settings.realtime_legacy_http_enabled:
        raise DomainRequestError("realtime-speech", "legacy-frame-ingest", "HTTP 逐帧发布已停用，请升级桌面助手使用 WebSocket v2。", 410, "legacy_realtime_transport_disabled")
    events = service.enqueue_audio_frame(
        token=request.token,
        device_id=request.device_id,
        source_id=request.source_id,
        sequence=request.sequence,
        source_kind=request.source_kind,
        segment_id=request.segment_id,
        revision=request.revision,
        captured_at_ms=request.captured_at_ms,
        started_at_ms=request.started_at_ms,
        ended_at_ms=request.ended_at_ms,
        duration_ms=request.duration_ms,
        codec=request.codec,
        sample_rate_hz=request.sample_rate_hz,
        channels=request.channels,
        is_final=request.is_final,
        trace_id=request.trace_id,
        sent_at_ms=request.sent_at_ms,
        audio_base64=request.audio_base64,
    )
    return success_response(request=request_context, data=events, timestamp=utc_now_iso())


@router.websocket("/ws")
async def realtime_ws(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token", "")
    service = realtime_speech_service()
    await websocket.accept()
    try:
        service.connect_publisher(token=token)
        while True:
            payload = RealtimeFrameRequest.model_validate(await websocket.receive_json())
            try:
                events = service.process_audio_frame(
                    token=token,
                    device_id=payload.device_id,
                    source_id=payload.source_id,
                    sequence=payload.sequence,
                    source_kind=payload.source_kind,
                    segment_id=payload.segment_id,
                    revision=payload.revision,
                    captured_at_ms=payload.captured_at_ms,
                    started_at_ms=payload.started_at_ms,
                    ended_at_ms=payload.ended_at_ms,
                    duration_ms=payload.duration_ms,
                    codec=payload.codec,
                    sample_rate_hz=payload.sample_rate_hz,
                    channels=payload.channels,
                    is_final=payload.is_final,
                    trace_id=payload.trace_id,
                    sent_at_ms=payload.sent_at_ms,
                    audio_base64=payload.audio_base64,
                )
            except DomainRequestError as exc:
                events = [{
                    "kind": "degraded",
                    "payload": {
                        "reason": "asr-frame-failed",
                        "sourceKind": payload.source_kind,
                        "message": exc.message,
                        "errorCode": exc.error_code or "asr-failed",
                    },
                }]
            for event in events:
                await websocket.send_json(event)
    except WebSocketDisconnect:
        service.disconnect_publisher(token=token)
    except Exception:
        try:
            service.disconnect_publisher(token=token, final_state="failed")
        finally:
            await websocket.close(code=1011)


@router.websocket("/ingest-ws")
async def realtime_ingest_ws(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token", "")
    requested_protocol = websocket.query_params.get("protocol", "2.0")
    service = realtime_speech_service()
    await websocket.accept()
    if token in _active_ingest_tokens:
        await websocket.send_json({"kind": "connection-rejected", "payload": {"reason": "publisher-already-connected"}})
        await websocket.close(code=1008)
        return
    _active_ingest_tokens.add(token)
    try:
        publisher = service.connect_publisher(token=token)
        if requested_protocol != service.settings.realtime_protocol_version:
            await websocket.send_json({"kind": "protocol-rejected", "payload": {"supported": service.settings.realtime_protocol_version}})
            await websocket.close(code=1002)
            return
        previous_receipts = service.repository.list_frame_receipts_for_session(session_id=publisher.session_id)
        expected_sequence: dict[str, int] = {"microphone": 0, "system": 0}
        for receipt in previous_receipts:
            if receipt.publisher_id == publisher.publisher_id and receipt.source_kind in expected_sequence:
                expected_sequence[receipt.source_kind] = max(expected_sequence[receipt.source_kind], receipt.sequence + 1)
        frame_arrivals: deque[float] = deque()
        await websocket.send_json({
            "kind": "connection-state",
            "payload": {
                "publisherId": publisher.publisher_id,
                "status": publisher.status,
                "sourceKind": publisher.source_kind,
                "transport": "websocket-v2-multiplexed",
                "protocolVersion": service.settings.realtime_protocol_version,
                "channels": ["microphone", "system"],
                "resumeOffsets": {channel: sequence - 1 for channel, sequence in expected_sequence.items()},
            },
        })
        while True:
            payload = RealtimeFrameRequest.model_validate(await websocket.receive_json())
            try:
                now = time()
                while frame_arrivals and now - frame_arrivals[0] >= 1:
                    frame_arrivals.popleft()
                if len(frame_arrivals) >= service.settings.realtime_ingress_max_frames_per_second:
                    await websocket.send_json({"kind": "degraded", "payload": {"reason": "ingress-rate-limited", "retryAfterMs": 100}})
                    continue
                frame_arrivals.append(now)
                if payload.source_kind not in {"microphone", "system"}:
                    await websocket.send_json({"kind": "channel-rejected", "payload": {"sourceKind": payload.source_kind}})
                    continue
                expected = expected_sequence[payload.source_kind]
                if payload.sequence < expected:
                    await websocket.send_json({"kind": "frame-accepted", "payload": {"sourceKind": payload.source_kind, "sourceId": payload.source_id, "sequence": expected - 1, "duplicate": True}})
                    continue
                if payload.sequence > expected:
                    await websocket.send_json({"kind": "sequence-gap", "payload": {"sourceKind": payload.source_kind, "expected": expected, "received": payload.sequence}})
                    continue
                service.enqueue_audio_frame(
                    token=token,
                    device_id=payload.device_id,
                    source_id=payload.source_id,
                    sequence=payload.sequence,
                    source_kind=payload.source_kind,
                    segment_id=payload.segment_id,
                    revision=payload.revision,
                    captured_at_ms=payload.captured_at_ms,
                    started_at_ms=payload.started_at_ms,
                    ended_at_ms=payload.ended_at_ms,
                    duration_ms=payload.duration_ms,
                    codec=payload.codec,
                    sample_rate_hz=payload.sample_rate_hz,
                    channels=payload.channels,
                    is_final=payload.is_final,
                    trace_id=payload.trace_id,
                    sent_at_ms=payload.sent_at_ms,
                    audio_base64=payload.audio_base64,
                )
                expected_sequence[payload.source_kind] = expected + 1
                await websocket.send_json({
                    "kind": "frame-accepted",
                    "payload": {
                        "sourceKind": payload.source_kind,
                        "sourceId": payload.source_id,
                        "sequence": payload.sequence,
                        "segmentId": payload.segment_id,
                        "revision": payload.revision,
                        "traceId": payload.trace_id,
                        "acceptedAtMs": int(time() * 1000),
                        "protocolVersion": service.settings.realtime_protocol_version,
                    },
                })
            except DomainRequestError as exc:
                await websocket.send_json({
                    "kind": "degraded",
                    "payload": {
                        "reason": "asr-frame-failed",
                        "sourceKind": payload.source_kind,
                        "message": exc.message,
                        "errorCode": exc.error_code or "asr-failed",
                    },
                })
    except WebSocketDisconnect:
        service.disconnect_publisher(token=token)
    except Exception:
        try:
            service.disconnect_publisher(token=token, final_state="failed")
        finally:
            await websocket.close(code=1011)
    finally:
        _active_ingest_tokens.discard(token)
