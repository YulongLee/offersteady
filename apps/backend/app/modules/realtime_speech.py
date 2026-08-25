from __future__ import annotations

import asyncio
import json
import logging
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
    RealtimeCaptureControlRequest,
    RealtimeDeviceStatusRequest,
    RealtimeEventListResponse,
    RealtimePublisherResponse,
    RealtimeQuestionCandidateListResponse,
    RealtimeSessionRuntimeResponse,
    RealtimeSessionSnapshotResponse,
    RealtimeTranscriptListResponse,
    RuntimePerformanceAcknowledgementRequest,
    RealtimeDeliveryMetricRequest,
    RealtimeFrameIngestRequest,
    RealtimeFrameRequest,
    RegisterDesktopDeviceRequest,
    WebSessionHeartbeatRequest,
)
from app.services.realtime_speech_service import RealtimeSpeechService
from app.services.realtime_event_wait import run_realtime_event_wait


router = APIRouter(prefix="/realtime-speech", tags=["realtime-speech"])
logger = logging.getLogger("offersteady.backend.realtime_speech")
REALTIME_SESSION_VALIDATION_INTERVAL_SECONDS = 15.0
REALTIME_BINARY_HEADER_MAX_BYTES = 64 * 1024
REALTIME_BINARY_AUDIO_MAX_BYTES = 2 * 1024 * 1024
_active_ingest_tokens: set[str] = set()
descriptor = ModuleDescriptor(
    feature="realtime-speech",
    owningApp="apps/backend",
    routePrefix="/api/v1/realtime-speech",
    mode="active",
    notes="Session-bound realtime speech orchestration for subtitles, question detection, and Chat Service handoff.",
)


def should_validate_realtime_session(*, last_validated_at: float, now: float) -> bool:
    return now - last_validated_at >= REALTIME_SESSION_VALIDATION_INTERVAL_SECONDS


def session_stream_refresh_plan(*, payload_type: str, event_kinds: set[str]) -> dict[str, bool]:
    snapshot = payload_type == "snapshot"
    return {
        "runtime": snapshot or bool(event_kinds & {
            "connection-state", "transcript-updated", "degraded", "device-status", "capture-control",
        }),
        "transcripts": snapshot or "transcript-updated" in event_kinds,
        "candidates": snapshot or bool(event_kinds & {"question-candidate", "question-confirmed"}),
        "events": snapshot,
    }


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


@router.post("/sessions/{session_id}/performance-ack", response_model=ApiEnvelope[dict[str, object]])
async def acknowledge_runtime_performance(
    session_id: str,
    request_context: Request,
    request: RuntimePerformanceAcknowledgementRequest,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: RealtimeSpeechService = Depends(realtime_speech_service),
) -> ApiEnvelope[dict[str, object]]:
    resolved_user_id = resolve_owned_user_id(explicit_user_id=request.user_id, auth_context=auth_context)
    event = service.acknowledge_runtime_timing(
        user_id=resolved_user_id,
        session_id=session_id,
        trace_id=request.trace_id,
        stage=request.stage,
        duration_ms=request.duration_ms,
        task_id=request.task_id,
        event_id=request.event_id,
        browser_event_receive_at_ms=request.browser_event_receive_at_ms,
        browser_state_update_at_ms=request.browser_state_update_at_ms,
        browser_render_at_ms=request.browser_render_at_ms,
        visibility_state=request.visibility_state,
        browser_stream_chunk_received_at_ms=request.browser_stream_chunk_received_at_ms,
        browser_event_parsed_at_ms=request.browser_event_parsed_at_ms,
        transcript_store_update_start_at_ms=request.transcript_store_update_start_at_ms,
        transcript_store_update_complete_at_ms=request.transcript_store_update_complete_at_ms,
        react_render_start_at_ms=request.react_render_start_at_ms,
        react_commit_at_ms=request.react_commit_at_ms,
        browser_paint_at_ms=request.browser_paint_at_ms,
        rendered_revision=request.rendered_revision,
        rendered_text_length=request.rendered_text_length,
    )
    return success_response(
        request=request_context,
        data={"accepted": True, "eventId": event.event_id},
        timestamp=utc_now_iso(),
    )


@router.get("/sessions/{session_id}/performance-summary", response_model=ApiEnvelope[dict[str, object]])
async def realtime_performance_summary(
    session_id: str,
    request: Request,
    user_id: str | None = Query(default=None, alias="userId"),
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: RealtimeSpeechService = Depends(realtime_speech_service),
) -> ApiEnvelope[dict[str, object]]:
    resolved_user_id = resolve_owned_user_id(explicit_user_id=user_id, auth_context=auth_context)
    service.session_service.get_session(user_id=resolved_user_id, session_id=session_id)
    return success_response(
        request=request,
        data=service.performance_summary(session_id=session_id),
        timestamp=utc_now_iso(),
    )


@router.get("/sessions/{session_id}/performance-traces", response_model=ApiEnvelope[list[dict[str, object]]])
async def realtime_performance_traces(
    session_id: str,
    request: Request,
    user_id: str | None = Query(default=None, alias="userId"),
    limit: int = Query(default=100, ge=1, le=4096),
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: RealtimeSpeechService = Depends(realtime_speech_service),
) -> ApiEnvelope[list[dict[str, object]]]:
    resolved_user_id = resolve_owned_user_id(explicit_user_id=user_id, auth_context=auth_context)
    service.session_service.get_session(user_id=resolved_user_id, session_id=session_id)
    return success_response(
        request=request,
        data=service.performance_traces(session_id=session_id, limit=limit),
        timestamp=utc_now_iso(),
    )


@router.post("/sessions/{session_id}/delivery-metrics", response_model=ApiEnvelope[dict[str, bool]])
async def record_delivery_metric(
    session_id: str,
    request_context: Request,
    request: RealtimeDeliveryMetricRequest,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: RealtimeSpeechService = Depends(realtime_speech_service),
) -> ApiEnvelope[dict[str, bool]]:
    resolved_user_id = resolve_owned_user_id(explicit_user_id=request.user_id, auth_context=auth_context)
    await asyncio.to_thread(
        service.record_delivery_metric,
        user_id=resolved_user_id,
        session_id=session_id,
        kind=request.kind,
        duration_ms=request.duration_ms,
        attempt=request.attempt,
        reason=request.reason,
    )
    return success_response(request=request_context, data={"accepted": True}, timestamp=utc_now_iso())


@router.post("/publishers", response_model=ApiEnvelope[RealtimePublisherResponse])
async def create_publisher(
    request_context: Request,
    request: CreateRealtimePublisherRequest,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: RealtimeSpeechService = Depends(realtime_speech_service),
) -> ApiEnvelope[RealtimePublisherResponse]:
    if request.device_id is not None and request.manual_code is not None:
        binding = service.get_desktop_active_binding(
            device_id=request.device_id,
            manual_code=request.manual_code,
        )
        if binding.session_id != request.session_id or binding.owner_user_id != request.user_id:
            raise DomainRequestError(
                "realtime-speech",
                "create-publisher",
                "桌面设备与当前面试绑定不一致，请重新输入机器码。",
                403,
                "desktop_binding_mismatch",
            )
        resolved_user_id = binding.owner_user_id
    else:
        resolved_user_id = resolve_owned_user_id(explicit_user_id=request.user_id, auth_context=auth_context)
    publisher = service.create_publisher(
        user_id=resolved_user_id,
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
        reuse_last_device=request.reuse_last_device,
    )
    return success_response(request=request_context, data=service.desktop_binding_response(binding), timestamp=utc_now_iso())


@router.get("/desktop-devices/last-used", response_model=ApiEnvelope[dict[str, object] | None])
async def get_last_used_desktop_device(
    request: Request,
    user_id: str | None = Query(default=None, alias="userId"),
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: RealtimeSpeechService = Depends(realtime_speech_service),
) -> ApiEnvelope[dict[str, object] | None]:
    resolved_user_id = resolve_owned_user_id(explicit_user_id=user_id, auth_context=auth_context)
    device = service.get_last_desktop_device_for_user(user_id=resolved_user_id)
    return success_response(request=request, data=device, timestamp=utc_now_iso())


@router.get("/desktop-devices", response_model=ApiEnvelope[list[dict[str, object]]])
async def list_account_desktop_devices(
    request: Request,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: RealtimeSpeechService = Depends(realtime_speech_service),
) -> ApiEnvelope[list[dict[str, object]]]:
    user_id = resolve_owned_user_id(explicit_user_id=None, auth_context=auth_context)
    devices = service.list_desktop_devices_for_user(user_id=user_id)
    return success_response(request=request, data=devices, timestamp=utc_now_iso())


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
        page_instance_id=request.page_instance_id,
    )
    return success_response(
        request=request_context,
        data={
            "sessionId": heartbeat.session_id,
            "ownerUserId": heartbeat.owner_user_id,
            "bindingId": heartbeat.binding_id,
            "page": heartbeat.page,
            "seenAtMs": heartbeat.seen_at_ms,
            "pageInstanceId": heartbeat.page_instance_id,
            "leaseGeneration": heartbeat.lease_generation,
            "leaseExpiresAtMs": heartbeat.lease_expires_at_ms,
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


@router.get("/desktop-devices/{device_id}/active-connection", response_model=ApiEnvelope[dict[str, object]])
async def get_desktop_active_connection(
    device_id: str,
    request: Request,
    manual_code: str = Query(alias="manualCode"),
    service: RealtimeSpeechService = Depends(realtime_speech_service),
) -> ApiEnvelope[dict[str, object]]:
    connection = service.get_desktop_active_connection(device_id=device_id, manual_code=manual_code)
    return success_response(request=request, data=connection, timestamp=utc_now_iso())


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


@router.get("/sessions/{session_id}/snapshot", response_model=ApiEnvelope[RealtimeSessionSnapshotResponse])
async def get_session_snapshot(
    session_id: str,
    request: Request,
    user_id: str | None = Query(default=None, alias="userId"),
    page_instance_id: str | None = Query(default=None, alias="pageInstanceId"),
    lease_generation: int | None = Query(default=None, ge=1, alias="leaseGeneration"),
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: RealtimeSpeechService = Depends(realtime_speech_service),
) -> ApiEnvelope[RealtimeSessionSnapshotResponse]:
    resolved_user_id = resolve_owned_user_id(explicit_user_id=user_id, auth_context=auth_context)
    if page_instance_id is not None or lease_generation is not None:
        if page_instance_id is None or lease_generation is None:
            raise DomainRequestError(
                "realtime-speech",
                "snapshot-lease",
                "页面会话参数不完整，请刷新后重试。",
                422,
                "incomplete_page_lease",
            )
        await asyncio.to_thread(
            service.require_active_realtime_session,
            user_id=resolved_user_id,
            session_id=session_id,
            page_instance_id=page_instance_id,
            lease_generation=lease_generation,
        )
    snapshot = await asyncio.to_thread(
        service.get_session_snapshot,
        user_id=resolved_user_id,
        session_id=session_id,
    )
    return success_response(request=request, data=snapshot, timestamp=utc_now_iso())


@router.post("/sessions/{session_id}/capture-control", response_model=ApiEnvelope[dict[str, object]])
async def control_session_capture(
    session_id: str,
    request_context: Request,
    request: RealtimeCaptureControlRequest,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: RealtimeSpeechService = Depends(realtime_speech_service),
) -> ApiEnvelope[dict[str, object]]:
    user_id = resolve_owned_user_id(explicit_user_id=request.user_id, auth_context=auth_context)
    result = service.control_capture(user_id=user_id, session_id=session_id, action=request.action)
    return success_response(request=request_context, data=result, timestamp=utc_now_iso())


@router.get("/sessions/{session_id}/stream")
async def stream_session_runtime(
    session_id: str,
    request: Request,
    user_id: str | None = Query(default=None, alias="userId"),
    cursor: int = Query(default=0, ge=0),
    page_instance_id: str | None = Query(default=None, alias="pageInstanceId"),
    lease_generation: int | None = Query(default=None, ge=1, alias="leaseGeneration"),
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: RealtimeSpeechService = Depends(realtime_speech_service),
) -> StreamingResponse:
    resolved_user_id = resolve_owned_user_id(explicit_user_id=user_id, auth_context=auth_context)
    await asyncio.to_thread(
        service.require_active_realtime_session,
        user_id=resolved_user_id,
        session_id=session_id,
        page_instance_id=page_instance_id,
        lease_generation=lease_generation,
    )

    async def event_stream():
        last_cursor = cursor
        initial = True
        idle_polls = 0
        cached_runtime = None
        cached_transcripts = None
        cached_candidates = None
        runtime_refreshed_at = 0.0
        session_validated_at = asyncio.get_running_loop().time()
        while True:
            if await request.is_disconnected():
                break
            loop_now = asyncio.get_running_loop().time()
            if should_validate_realtime_session(last_validated_at=session_validated_at, now=loop_now):
                try:
                    await asyncio.to_thread(
                        service.require_active_realtime_session,
                        user_id=resolved_user_id,
                        session_id=session_id,
                        page_instance_id=page_instance_id,
                        lease_generation=lease_generation,
                    )
                    session_validated_at = loop_now
                except DomainRequestError:
                    yield _sse_frame("revoked", {
                        "type": "revoked",
                        "sessionId": session_id,
                        "reason": "session-replaced",
                    })
                    break
            event_reader = service.list_session_events_after if initial else service.wait_for_session_events_after
            reader_kwargs = {
                "user_id": resolved_user_id,
                "session_id": session_id,
                "cursor": last_cursor,
            }
            if not initial:
                reader_kwargs["timeout_ms"] = max(100, service.settings.realtime_event_block_ms)
            current_cursor, incremental_events, resumable = await run_realtime_event_wait(
                request,
                event_reader,
                **reader_kwargs,
            )
            if not initial and current_cursor <= last_cursor:
                idle_polls += 1
                keepalive_polls = max(1, 15_000 // max(100, service.settings.realtime_event_block_ms))
                if idle_polls >= keepalive_polls:
                    yield ": keepalive\n\n"
                    idle_polls = 0
                continue
            idle_polls = 0
            payload_type = "snapshot" if initial or not resumable else "update"
            if payload_type == "snapshot":
                runtime, transcripts, candidates, snapshot_events = await asyncio.gather(
                    asyncio.to_thread(service.get_runtime, user_id=resolved_user_id, session_id=session_id),
                    asyncio.to_thread(service.list_transcripts, user_id=resolved_user_id, session_id=session_id),
                    asyncio.to_thread(service.list_candidates, user_id=resolved_user_id, session_id=session_id),
                    asyncio.to_thread(service.list_events, user_id=resolved_user_id, session_id=session_id),
                )
                cached_runtime = runtime
                cached_transcripts = transcripts
                cached_candidates = candidates
                runtime_refreshed_at = asyncio.get_running_loop().time()
                payload = {
                    "type": payload_type,
                    "transcripts": transcripts.model_dump(by_alias=True),
                    "candidates": candidates.model_dump(by_alias=True),
                    "events": snapshot_events.model_dump(by_alias=True),
                    "runtime": runtime.model_dump(by_alias=True),
                    "ownerUserId": resolved_user_id,
                    "cursor": current_cursor,
                }
            else:
                # Normal updates are event deltas. Full state is reserved for
                # initial entry and expired-cursor recovery.
                sse_sent_at_ms = int(time() * 1000)
                incremental_events = service.observe_sse_delivery(incremental_events, sent_at_ms=sse_sent_at_ms)
                payload = {
                    "type": payload_type,
                    "events": {
                        "sessionId": session_id,
                        "events": [service.event_response(event).model_dump(by_alias=True) for event in incremental_events],
                    },
                    "ownerUserId": resolved_user_id,
                    "cursor": current_cursor,
                }
            yield _sse_frame(payload_type, payload, cursor=current_cursor)
            last_cursor = current_cursor
            initial = False

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
    if request.manual_code is not None:
        binding = service.get_desktop_active_binding(device_id=request.device_id, manual_code=request.manual_code)
        if binding.session_id != session_id:
            raise DomainRequestError(
                "realtime-speech",
                "device-status",
                "该设备已连接到另一场面试，请刷新当前连接。",
                410,
                "desktop_binding_replaced",
            )
        resolved_user_id = binding.owner_user_id
    else:
        resolved_user_id = resolve_owned_user_id(explicit_user_id=request.user_id, auth_context=auth_context)
    event = service.publish_device_status(
        user_id=resolved_user_id,
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
        vad_triggered_at_ms=request.vad_triggered_at_ms,
        speech_confirmed_at_ms=request.speech_confirmed_at_ms,
        ended_at_ms=request.ended_at_ms,
        duration_ms=request.duration_ms,
        codec=request.codec,
        sample_rate_hz=request.sample_rate_hz,
        channels=request.channels,
        is_final=request.is_final,
        turn_state=request.turn_state,
        finalization_reason=request.finalization_reason,
        source_generation=request.source_generation,
        terminal_id=request.terminal_id,
        trace_id=request.trace_id,
        sent_at_ms=request.sent_at_ms,
        diagnostics=request.diagnostics,
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
                    vad_triggered_at_ms=payload.vad_triggered_at_ms,
                    speech_confirmed_at_ms=payload.speech_confirmed_at_ms,
                    ended_at_ms=payload.ended_at_ms,
                    duration_ms=payload.duration_ms,
                    codec=payload.codec,
                    sample_rate_hz=payload.sample_rate_hz,
                    channels=payload.channels,
                    is_final=payload.is_final,
                    turn_state=payload.turn_state,
                    finalization_reason=payload.finalization_reason,
                    source_generation=payload.source_generation,
                    terminal_id=payload.terminal_id,
                    trace_id=payload.trace_id,
                    sent_at_ms=payload.sent_at_ms,
                    diagnostics=payload.diagnostics,
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
        logger.exception("Legacy realtime websocket failed")
        try:
            service.disconnect_publisher(token=token, final_state="failed")
        finally:
            await websocket.close(code=1011)


@router.websocket("/ingest-ws")
async def realtime_ingest_ws(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token", "")
    requested_protocol = websocket.query_params.get("protocol", "2.0")
    requested_media = websocket.query_params.get("media", "json-base64")
    service = realtime_speech_service()
    await websocket.accept()
    if token in _active_ingest_tokens:
        await websocket.send_json({"kind": "connection-rejected", "payload": {"reason": "publisher-already-connected"}})
        await websocket.close(code=1008)
        return
    _active_ingest_tokens.add(token)
    publisher_connected = False
    try:
        try:
            publisher = service.connect_publisher(token=token)
            publisher_connected = True
        except DomainRequestError as exc:
            await websocket.send_json({
                "kind": "connection-rejected",
                "payload": {
                    "reason": "publisher-credential-rejected",
                    "message": exc.message,
                },
            })
            await websocket.close(code=1008)
            return
        if requested_protocol != service.settings.realtime_protocol_version:
            await websocket.send_json({"kind": "protocol-rejected", "payload": {"supported": service.settings.realtime_protocol_version}})
            try:
                service.disconnect_publisher(token=token)
            except DomainRequestError:
                pass
            publisher_connected = False
            await websocket.close(code=1002)
            return
        if requested_media not in {"json-base64", "binary-v1"}:
            await websocket.send_json({"kind": "protocol-rejected", "payload": {"supportedMedia": ["json-base64", "binary-v1"]}})
            service.disconnect_publisher(token=token)
            publisher_connected = False
            await websocket.close(code=1002)
            return
        previous_receipts = service.repository.list_frame_receipts_for_session(session_id=publisher.session_id)
        expected_sequence: dict[str, int] = {"microphone": 0, "system": 0}
        for receipt in previous_receipts:
            if receipt.publisher_id == publisher.publisher_id and receipt.source_kind in expected_sequence:
                expected_sequence[receipt.source_kind] = max(expected_sequence[receipt.source_kind], receipt.sequence + 1)
        frame_arrivals: deque[float] = deque()
        sequence_gap_events: dict[str, int] = {"microphone": 0, "system": 0}
        await websocket.send_json({
            "kind": "connection-state",
            "payload": {
                "publisherId": publisher.publisher_id,
                "status": publisher.status,
                "sourceKind": publisher.source_kind,
                "transport": "websocket-v2-multiplexed",
                "protocolVersion": service.settings.realtime_protocol_version,
                "channels": ["microphone", "system"],
                "mediaMode": requested_media,
                "resumeOffsets": {channel: sequence - 1 for channel, sequence in expected_sequence.items()},
            },
        })
        while True:
            audio_bytes: bytes | None = None
            if requested_media == "binary-v1":
                message = await websocket.receive()
                websocket_frame_received_at_ms = int(time() * 1000)
                raw = message.get("bytes")
                if not isinstance(raw, bytes) or len(raw) < 4:
                    await websocket.close(code=1002, reason="binary-frame-required")
                    return
                header_size = int.from_bytes(raw[:4], byteorder="big", signed=False)
                if header_size < 2 or header_size > REALTIME_BINARY_HEADER_MAX_BYTES or 4 + header_size > len(raw):
                    await websocket.close(code=1002, reason="invalid-binary-header")
                    return
                audio_bytes = raw[4 + header_size:]
                if not audio_bytes or len(audio_bytes) > REALTIME_BINARY_AUDIO_MAX_BYTES:
                    await websocket.close(code=1009, reason="invalid-audio-size")
                    return
                try:
                    header = json.loads(raw[4:4 + header_size].decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    await websocket.close(code=1002, reason="invalid-binary-header-json")
                    return
                if not isinstance(header, dict) or "audioBase64" in header:
                    await websocket.close(code=1002, reason="invalid-binary-envelope")
                    return
                payload = RealtimeFrameRequest.model_validate({**header, "audioBase64": ""})
            else:
                message = await websocket.receive()
                websocket_frame_received_at_ms = int(time() * 1000)
                raw_text = message.get("text")
                if not isinstance(raw_text, str):
                    await websocket.close(code=1002, reason="json-frame-required")
                    return
                payload = RealtimeFrameRequest.model_validate(json.loads(raw_text))
            frame_validation_done_at_ms = int(time() * 1000)
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
                    sequence_gap_events[payload.source_kind] = 0
                    await websocket.send_json({
                        "kind": "terminal-accepted" if payload.is_final and payload.terminal_id else "frame-accepted",
                        "payload": {
                            "sourceKind": payload.source_kind,
                            "sourceId": payload.source_id,
                            "sequence": expected - 1,
                            "segmentId": payload.segment_id,
                            "revision": payload.revision,
                            **({"terminalId": payload.terminal_id} if payload.terminal_id else {}),
                            "duplicate": True,
                            "acceptedAtMs": int(time() * 1000),
                        },
                    })
                    continue
                if payload.sequence > expected:
                    sequence_gap_events[payload.source_kind] += 1
                    if sequence_gap_events[payload.source_kind] >= service.settings.realtime_ingress_sequence_gap_max_events:
                        await websocket.send_json({
                            "kind": "degraded",
                            "payload": {
                                "reason": "sequence-gap-budget-exhausted",
                                "sourceKind": payload.source_kind,
                                "expected": expected,
                                "received": payload.sequence,
                                "gapEvents": sequence_gap_events[payload.source_kind],
                                "retryable": True,
                            },
                        })
                        service.disconnect_publisher(token=token)
                        publisher_connected = False
                        await websocket.close(code=1013, reason="sequence-gap-budget-exhausted")
                        return
                    await websocket.send_json({"kind": "sequence-gap", "payload": {"sourceKind": payload.source_kind, "expected": expected, "received": payload.sequence}})
                    continue
                sequence_gap_events[payload.source_kind] = 0
                channel_routing_done_at_ms = int(time() * 1000)
                diagnostics = {
                    **payload.diagnostics,
                    "backendWebsocketFrameReceivedAtMs": websocket_frame_received_at_ms,
                    "backendFrameValidationDoneAtMs": frame_validation_done_at_ms,
                    "backendChannelRoutingDoneAtMs": channel_routing_done_at_ms,
                }
                admission_events = service.enqueue_audio_frame(
                    token=token,
                    device_id=payload.device_id,
                    source_id=payload.source_id,
                    sequence=payload.sequence,
                    source_kind=payload.source_kind,
                    segment_id=payload.segment_id,
                    revision=payload.revision,
                    captured_at_ms=payload.captured_at_ms,
                    started_at_ms=payload.started_at_ms,
                    vad_triggered_at_ms=payload.vad_triggered_at_ms,
                    speech_confirmed_at_ms=payload.speech_confirmed_at_ms,
                    ended_at_ms=payload.ended_at_ms,
                    duration_ms=payload.duration_ms,
                    codec=payload.codec,
                    sample_rate_hz=payload.sample_rate_hz,
                    channels=payload.channels,
                    is_final=payload.is_final,
                    turn_state=payload.turn_state,
                    finalization_reason=payload.finalization_reason,
                    source_generation=payload.source_generation,
                    terminal_id=payload.terminal_id,
                    trace_id=payload.trace_id,
                    sent_at_ms=payload.sent_at_ms,
                    diagnostics=diagnostics,
                    audio_base64=payload.audio_base64,
                    audio_bytes=audio_bytes,
                    authenticated_publisher=publisher,
                )
                terminal_event = next((event for event in admission_events if event.get("kind") in {"terminal-accepted", "degraded"}), None)
                if terminal_event is not None and (payload.is_final or terminal_event.get("kind") == "degraded"):
                    if terminal_event.get("kind") == "terminal-accepted":
                        expected_sequence[payload.source_kind] = expected + 1
                    await websocket.send_json(terminal_event)
                    continue
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
        if publisher_connected:
            try:
                service.disconnect_publisher(token=token)
            except DomainRequestError:
                pass
    except Exception:
        logger.exception("Realtime ingest websocket failed")
        try:
            if publisher_connected:
                try:
                    service.disconnect_publisher(token=token, final_state="failed")
                except DomainRequestError:
                    pass
        finally:
            try:
                await websocket.close(code=1011)
            except RuntimeError:
                pass
    finally:
        _active_ingest_tokens.discard(token)
