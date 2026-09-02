from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import StreamingResponse

from app.core.logging import utc_now_iso
from app.core.responses import success_response
from app.deps import optional_authenticated_context, realtime_speech_service, resolve_owned_user_id, screenshot_answer_service
from app.ports.authentication import AuthenticatedRequestContext
from app.services.realtime_speech_service import RealtimeSpeechService
from app.schemas.foundation import ApiEnvelope, ModuleDescriptor
from app.schemas.screenshot_answer import (
    CancelRemoteScreenshotCaptureRequest,
    CompleteScreenshotUploadRequest,
    CreateScreenshotUploadIntentRequest,
    ScreenshotAnswerChunkResponse,
    ScreenshotAnswerResponse,
    ScreenshotAnswerTaskResponse,
    ScreenshotTimingTelemetryResponse,
    RemoteScreenshotCaptureRequestResponse,
    ScreenshotUploadIntentResponse,
    ScreenshotUploadResponse,
    ScreenshotValidationPolicyResponse,
    StartScreenshotAnswerRequest,
    CreateRemoteScreenshotCaptureRequest,
    CreateDesktopShortcutCaptureRequest,
    FailRemoteScreenshotCaptureRequest,
)
from app.services.screenshot_answer_service import ScreenshotAnswerService
from app.services.realtime_event_wait import run_realtime_event_wait
from app.services.realtime_control_executor import run_realtime_control


router = APIRouter(prefix="/screenshot-answer", tags=["screenshot-answer"])
descriptor = ModuleDescriptor(
    feature="screenshot-answer",
    owningApp="apps/backend",
    routePrefix="/api/v1/screenshot-answer",
    mode="active",
    notes="Screenshot upload, vision grounding, retrieval enhancement, and streaming interview answer generation.",
)


def _sse_frame(event: str, payload: dict[str, object], *, cursor: int | None = None) -> str:
    identifier = f"id: {cursor}\n" if cursor is not None else ""
    return f"{identifier}event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _to_upload_response(upload) -> ScreenshotUploadResponse:
    return ScreenshotUploadResponse(
        imageId=upload.image_id,
        sessionId=upload.session_id,
        ownerUserId=upload.owner_user_id,
        filename=upload.filename,
        contentType=upload.content_type,
        objectKey=upload.object_key,
        sizeBytes=upload.size_bytes,
        status=upload.status,
        uploadedAtMs=upload.uploaded_at_ms,
        etag=upload.etag,
        deletedAtMs=upload.deleted_at_ms,
    )


def _to_telemetry_response(telemetry) -> ScreenshotTimingTelemetryResponse:
    return ScreenshotTimingTelemetryResponse(
        deliveryMode=telemetry.delivery_mode,
        uploadAcceptedMs=telemetry.upload_accepted_ms,
        imageOptimizeMs=telemetry.image_optimize_ms,
        ossWriteMs=telemetry.oss_write_ms,
        signedUrlMs=telemetry.signed_url_ms,
        firstTextMs=telemetry.first_text_ms,
        visionModelMs=telemetry.vision_model_ms,
        answerPersistMs=telemetry.answer_persist_ms,
        totalBackgroundMs=telemetry.total_background_ms,
        failedPhase=telemetry.failed_phase,
        errorCode=telemetry.error_code,
        originalWidth=telemetry.original_width,
        originalHeight=telemetry.original_height,
        compressedWidth=telemetry.compressed_width,
        compressedHeight=telemetry.compressed_height,
        originalBytes=telemetry.original_bytes,
        compressedBytes=telemetry.compressed_bytes,
        contentType=telemetry.content_type,
    )


def _to_task_response(task) -> ScreenshotAnswerTaskResponse:
    return ScreenshotAnswerTaskResponse(
        taskId=task.task_id,
        sessionId=task.session_id,
        ownerUserId=task.owner_user_id,
        instruction=task.instruction,
        answerText=task.answer_text,
        status=task.status,
        streamMode=task.stream_mode,
        imageIds=task.image_ids,
        imageCount=task.image_count,
        providerName=task.provider_name,
        modelName=task.model_name,
        visionProviderName=task.vision_provider_name,
        visionModelName=task.vision_model_name,
        promptTemplateId=task.prompt_template_id,
        promptVersion=task.prompt_version,
        retrievalExcerptCount=task.retrieval_excerpt_count,
        materialContextStatus=task.material_context_status,
        fixedSourceCount=task.fixed_source_count,
        retrievedSourceCount=task.retrieved_source_count,
        materialProvenance=task.material_provenance,
        unavailableMaterialSources=task.unavailable_material_sources,
        retryCount=task.retry_count,
        errorCode=task.error_code,
        errorMessage=task.error_message,
        createdAtMs=task.created_at_ms,
        updatedAtMs=task.updated_at_ms,
        completedAtMs=task.completed_at_ms,
        visionSummaryTitle=task.vision_summary_title,
        telemetry=_to_telemetry_response(task.telemetry),
        chunks=[
            ScreenshotAnswerChunkResponse(sequence=chunk.sequence, text=chunk.text, isFinal=chunk.is_final)
            for chunk in task.chunks
        ],
    )


def _to_remote_capture_request_response(request, task=None) -> RemoteScreenshotCaptureRequestResponse:
    return RemoteScreenshotCaptureRequestResponse(
        requestId=request.request_id,
        sessionId=request.session_id,
        ownerUserId=request.owner_user_id,
        deviceId=request.device_id,
        manualCode=request.manual_code,
        instruction=request.instruction,
        status=request.status,
        stage=request.stage,
        createdAtMs=request.created_at_ms,
        updatedAtMs=request.updated_at_ms,
        answerTaskId=request.answer_task_id,
        errorMessage=request.error_message,
        capturedFilename=request.captured_filename,
        claimedAtMs=request.claimed_at_ms,
        completedAtMs=request.completed_at_ms,
        telemetry=_to_telemetry_response(request.telemetry),
        answerTask=_to_task_response(task) if task is not None else None,
    )


def _publish_capture_event(realtime: RealtimeSpeechService, capture_request, task=None) -> None:
    payload: dict[str, object] = {
        "requestId": capture_request.request_id,
        "deviceId": capture_request.device_id,
        "status": capture_request.status,
        "stage": capture_request.stage,
        "updatedAtMs": capture_request.updated_at_ms,
    }
    if capture_request.claimed_at_ms is not None:
        payload["claimedAtMs"] = capture_request.claimed_at_ms
    if capture_request.completed_at_ms is not None:
        payload["completedAtMs"] = capture_request.completed_at_ms
    if capture_request.error_message:
        payload["errorMessage"] = capture_request.error_message[:240]
    if task is not None:
        payload["answerTask"] = _to_task_response(task).model_dump(by_alias=True)
    realtime.publish_session_event(
        user_id=capture_request.owner_user_id,
        session_id=capture_request.session_id,
        kind="screenshot-capture-updated",
        payload=payload,
    )


@router.get("/status", response_model=ApiEnvelope[dict[str, str]])
async def status(request: Request) -> ApiEnvelope[dict[str, str]]:
    return success_response(
        request=request,
        data={"status": "active", "feature": "screenshot-answer", "message": "Screenshot Answer Service is available for live interview screenshot workflows."},
        timestamp=utc_now_iso(),
    )


@router.get("/validation-policy", response_model=ApiEnvelope[ScreenshotValidationPolicyResponse])
async def validation_policy(
    request: Request,
    service: ScreenshotAnswerService = Depends(screenshot_answer_service),
) -> ApiEnvelope[ScreenshotValidationPolicyResponse]:
    return success_response(request=request, data=service.validation_policy(), timestamp=utc_now_iso())


@router.post("/upload-intents", response_model=ApiEnvelope[ScreenshotUploadIntentResponse])
async def create_upload_intent(
    request_context: Request,
    request: CreateScreenshotUploadIntentRequest,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: ScreenshotAnswerService = Depends(screenshot_answer_service),
) -> ApiEnvelope[ScreenshotUploadIntentResponse]:
    return success_response(
        request=request_context,
        data=service.create_upload_intent(
            user_id=resolve_owned_user_id(explicit_user_id=request.user_id, auth_context=auth_context),
            session_id=request.session_id,
            filename=request.filename,
            content_type=request.content_type,
            size_bytes=request.size_bytes,
        ),
        timestamp=utc_now_iso(),
    )


@router.post("/uploads/complete", response_model=ApiEnvelope[ScreenshotUploadResponse])
async def complete_upload(
    request_context: Request,
    request: CompleteScreenshotUploadRequest,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: ScreenshotAnswerService = Depends(screenshot_answer_service),
) -> ApiEnvelope[ScreenshotUploadResponse]:
    upload = service.complete_upload(
        user_id=resolve_owned_user_id(explicit_user_id=request.user_id, auth_context=auth_context),
        session_id=request.session_id,
        intent_id=request.intent_id,
        object_key=request.object_key,
        content_type=request.content_type,
        size_bytes=request.size_bytes,
        etag=request.etag,
    )
    return success_response(request=request_context, data=_to_upload_response(upload), timestamp=utc_now_iso())


@router.post("/uploads/direct", response_model=ApiEnvelope[ScreenshotUploadResponse])
async def direct_upload(
    request_context: Request,
    user_id: str = Form(alias="userId"),
    session_id: str = Form(alias="sessionId"),
    screenshot: UploadFile = File(...),
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: ScreenshotAnswerService = Depends(screenshot_answer_service),
) -> ApiEnvelope[ScreenshotUploadResponse]:
    payload = await screenshot.read()
    upload = service.upload_bytes(
        user_id=resolve_owned_user_id(explicit_user_id=user_id, auth_context=auth_context),
        session_id=session_id,
        filename=screenshot.filename or "current-screen.png",
        content_type=screenshot.content_type or "image/png",
        payload=payload,
    )
    return success_response(request=request_context, data=_to_upload_response(upload), timestamp=utc_now_iso())


@router.get("/sessions/{session_id}/uploads", response_model=ApiEnvelope[list[ScreenshotUploadResponse]])
async def list_uploads(
    session_id: str,
    request: Request,
    user_id: str | None = Query(default=None, alias="userId"),
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: ScreenshotAnswerService = Depends(screenshot_answer_service),
) -> ApiEnvelope[list[ScreenshotUploadResponse]]:
    uploads = service.list_uploads(user_id=resolve_owned_user_id(explicit_user_id=user_id, auth_context=auth_context), session_id=session_id)
    return success_response(request=request, data=[_to_upload_response(item) for item in uploads], timestamp=utc_now_iso())


@router.post("/tasks", response_model=ApiEnvelope[ScreenshotAnswerResponse])
async def create_screenshot_task(
    request_context: Request,
    request: StartScreenshotAnswerRequest,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: ScreenshotAnswerService = Depends(screenshot_answer_service),
) -> ApiEnvelope[ScreenshotAnswerResponse]:
    task, retrieval = service.answer_screenshots(
        user_id=resolve_owned_user_id(explicit_user_id=request.user_id, auth_context=auth_context),
        session_id=request.session_id,
        image_ids=request.image_ids,
        instruction=request.instruction,
        stream=request.stream,
    )
    return success_response(
        request=request_context,
        data=ScreenshotAnswerResponse(task=_to_task_response(task), retrieval=retrieval),
        timestamp=utc_now_iso(),
    )


@router.get("/tasks/{task_id}", response_model=ApiEnvelope[ScreenshotAnswerTaskResponse])
async def get_task(
    task_id: str,
    request: Request,
    user_id: str | None = Query(default=None, alias="userId"),
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: ScreenshotAnswerService = Depends(screenshot_answer_service),
) -> ApiEnvelope[ScreenshotAnswerTaskResponse]:
    task = service.get_task(user_id=resolve_owned_user_id(explicit_user_id=user_id, auth_context=auth_context), task_id=task_id)
    return success_response(request=request, data=_to_task_response(task), timestamp=utc_now_iso())


@router.delete("/tasks/{task_id}", response_model=ApiEnvelope[ScreenshotAnswerTaskResponse])
async def delete_task(
    task_id: str,
    request: Request,
    user_id: str | None = Query(default=None, alias="userId"),
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: ScreenshotAnswerService = Depends(screenshot_answer_service),
) -> ApiEnvelope[ScreenshotAnswerTaskResponse]:
    task = service.delete_task(user_id=resolve_owned_user_id(explicit_user_id=user_id, auth_context=auth_context), task_id=task_id)
    return success_response(request=request, data=_to_task_response(task), timestamp=utc_now_iso())


@router.get("/sessions/{session_id}/history", response_model=ApiEnvelope[list[ScreenshotAnswerTaskResponse]])
async def list_history(
    session_id: str,
    request: Request,
    user_id: str | None = Query(default=None, alias="userId"),
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: ScreenshotAnswerService = Depends(screenshot_answer_service),
) -> ApiEnvelope[list[ScreenshotAnswerTaskResponse]]:
    tasks = service.list_session_history(user_id=resolve_owned_user_id(explicit_user_id=user_id, auth_context=auth_context), session_id=session_id)
    return success_response(request=request, data=[_to_task_response(task) for task in tasks], timestamp=utc_now_iso())


@router.post("/sessions/{session_id}/remote-capture-requests", response_model=ApiEnvelope[RemoteScreenshotCaptureRequestResponse])
async def create_remote_capture_request(
    session_id: str,
    request_context: Request,
    request: CreateRemoteScreenshotCaptureRequest,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: ScreenshotAnswerService = Depends(screenshot_answer_service),
    realtime: RealtimeSpeechService = Depends(realtime_speech_service),
) -> ApiEnvelope[RemoteScreenshotCaptureRequestResponse]:
    resolved_user_id = resolve_owned_user_id(explicit_user_id=request.user_id, auth_context=auth_context)
    binding = realtime.get_desktop_binding(user_id=resolved_user_id, session_id=session_id)
    realtime.get_desktop_capture_binding(device_id=binding.device_id, manual_code=binding.manual_code)
    capture_request = service.create_remote_capture_request(
        user_id=resolved_user_id,
        session_id=session_id,
        device_id=binding.device_id,
        manual_code=binding.manual_code,
        instruction=request.instruction,
    )
    _publish_capture_event(realtime, capture_request)
    return success_response(request=request_context, data=_to_remote_capture_request_response(capture_request), timestamp=utc_now_iso())


@router.get("/sessions/{session_id}/remote-capture-requests", response_model=ApiEnvelope[list[RemoteScreenshotCaptureRequestResponse]])
async def list_session_remote_capture_requests(
    session_id: str,
    request: Request,
    user_id: str | None = Query(default=None, alias="userId"),
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: ScreenshotAnswerService = Depends(screenshot_answer_service),
) -> ApiEnvelope[list[RemoteScreenshotCaptureRequestResponse]]:
    resolved_user_id = resolve_owned_user_id(explicit_user_id=user_id, auth_context=auth_context)
    capture_requests = service.list_session_remote_capture_requests(user_id=resolved_user_id, session_id=session_id)
    responses = []
    for capture_request in capture_requests:
        task = service.get_task(user_id=resolved_user_id, task_id=capture_request.answer_task_id) if capture_request.answer_task_id else None
        responses.append(_to_remote_capture_request_response(capture_request, task))
    return success_response(request=request, data=responses, timestamp=utc_now_iso())


@router.post("/desktop-devices/{device_id}/shortcut-capture-requests", response_model=ApiEnvelope[RemoteScreenshotCaptureRequestResponse])
async def create_desktop_shortcut_capture_request(
    device_id: str,
    request_context: Request,
    request: CreateDesktopShortcutCaptureRequest,
    service: ScreenshotAnswerService = Depends(screenshot_answer_service),
    realtime: RealtimeSpeechService = Depends(realtime_speech_service),
) -> ApiEnvelope[RemoteScreenshotCaptureRequestResponse]:
    if request.device_id != device_id:
        from app.core.errors import DomainRequestError
        raise DomainRequestError("screenshot-answer", "desktop-shortcut", "设备标识不匹配。", 403)
    binding = realtime.get_desktop_capture_binding(device_id=device_id, manual_code=request.manual_code)
    session = realtime.session_service.get_session(user_id=binding.owner_user_id, session_id=binding.session_id)
    if session.status != "live":
        from app.core.errors import DomainRequestError
        raise DomainRequestError("screenshot-answer", "desktop-shortcut", "当前设备没有连接正在进行的面试。", 409)
    existing = service.get_next_remote_capture_request(device_id=device_id, manual_code=request.manual_code)
    if existing is not None:
        from app.core.errors import DomainRequestError
        raise DomainRequestError("screenshot-answer", "desktop-shortcut", "上一笔截屏回答仍在处理中，请稍候。", 409)
    capture_request = service.create_remote_capture_request(
        user_id=binding.owner_user_id,
        session_id=binding.session_id,
        device_id=device_id,
        manual_code=request.manual_code,
        instruction="请直接识别当前截图中的题目、代码或系统设计内容，并给出可直接使用的中文回答。[来源:助手快捷键]",
    )
    _publish_capture_event(realtime, capture_request)
    realtime.publish_screenshot_shortcut_accepted(
        user_id=binding.owner_user_id,
        session_id=binding.session_id,
        request_id=capture_request.request_id,
    )
    return success_response(request=request_context, data=_to_remote_capture_request_response(capture_request), timestamp=utc_now_iso())


@router.get("/capture-requests/{request_id}", response_model=ApiEnvelope[RemoteScreenshotCaptureRequestResponse])
async def get_remote_capture_request(
    request_id: str,
    request: Request,
    user_id: str | None = Query(default=None, alias="userId"),
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: ScreenshotAnswerService = Depends(screenshot_answer_service),
) -> ApiEnvelope[RemoteScreenshotCaptureRequestResponse]:
    resolved_user_id = resolve_owned_user_id(explicit_user_id=user_id, auth_context=auth_context)
    capture_request = service.get_remote_capture_request(user_id=resolved_user_id, request_id=request_id)
    task = service.get_task(user_id=resolved_user_id, task_id=capture_request.answer_task_id) if capture_request.answer_task_id else None
    return success_response(request=request, data=_to_remote_capture_request_response(capture_request, task), timestamp=utc_now_iso())


@router.post("/capture-requests/{request_id}/cancel", response_model=ApiEnvelope[RemoteScreenshotCaptureRequestResponse])
async def cancel_remote_capture_request(
    request_id: str,
    request_context: Request,
    request: CancelRemoteScreenshotCaptureRequest,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: ScreenshotAnswerService = Depends(screenshot_answer_service),
    realtime: RealtimeSpeechService = Depends(realtime_speech_service),
) -> ApiEnvelope[RemoteScreenshotCaptureRequestResponse]:
    resolved_user_id = resolve_owned_user_id(explicit_user_id=request.user_id, auth_context=auth_context)
    capture_request = service.cancel_remote_capture_request(user_id=resolved_user_id, request_id=request_id)
    task = service.get_task(user_id=resolved_user_id, task_id=capture_request.answer_task_id) if capture_request.answer_task_id else None
    _publish_capture_event(realtime, capture_request, task)
    return success_response(request=request_context, data=_to_remote_capture_request_response(capture_request, task), timestamp=utc_now_iso())


@router.get("/desktop-devices/{device_id}/capture-requests/next", response_model=ApiEnvelope[RemoteScreenshotCaptureRequestResponse | None])
async def get_next_remote_capture_request(
    device_id: str,
    request: Request,
    manual_code: str = Query(alias="manualCode"),
    service: ScreenshotAnswerService = Depends(screenshot_answer_service),
    realtime: RealtimeSpeechService = Depends(realtime_speech_service),
) -> ApiEnvelope[RemoteScreenshotCaptureRequestResponse | None]:
    pairing_status = await run_realtime_control(
        request,
        realtime.get_desktop_pairing_status,
        manual_code=manual_code,
        device_id=device_id,
    )
    if pairing_status.get("bound") is not True or pairing_status.get("sessionStatus") != "live":
        return success_response(request=request, data=None, timestamp=utc_now_iso())
    capture_request = service.get_next_remote_capture_request(device_id=device_id, manual_code=manual_code)
    return success_response(request=request, data=_to_remote_capture_request_response(capture_request) if capture_request is not None else None, timestamp=utc_now_iso())


@router.get("/desktop-devices/{device_id}/capture-requests/stream")
async def stream_desktop_capture_requests(
    device_id: str,
    request: Request,
    manual_code: str = Query(alias="manualCode"),
    cursor: int = Query(default=0, ge=0),
    service: ScreenshotAnswerService = Depends(screenshot_answer_service),
    realtime: RealtimeSpeechService = Depends(realtime_speech_service),
) -> StreamingResponse:
    binding = await run_realtime_control(
        request,
        realtime.get_desktop_capture_binding,
        device_id=device_id,
        manual_code=manual_code,
    )
    session = realtime.session_service.get_session(user_id=binding.owner_user_id, session_id=binding.session_id)
    if session.status != "live":
        from app.core.errors import DomainRequestError
        raise DomainRequestError("screenshot-answer", "desktop-stream", "当前设备没有连接正在进行的面试。", 409)

    async def event_stream():
        last_cursor = cursor
        pending = await asyncio.to_thread(
            service.get_next_remote_capture_request,
            device_id=device_id,
            manual_code=manual_code,
        )
        current_cursor, _events, _resumable = await asyncio.to_thread(
            realtime.list_session_events_after,
            user_id=binding.owner_user_id,
            session_id=binding.session_id,
            cursor=last_cursor,
        )
        if pending is not None:
            yield _sse_frame("capture-request", {
                "requestId": pending.request_id,
                "status": pending.status,
                "stage": pending.stage,
            }, cursor=current_cursor)
        last_cursor = current_cursor
        idle_ticks = 0
        binding_check_ticks = 0
        while True:
            if await request.is_disconnected():
                break
            binding_check_ticks += 1
            if binding_check_ticks >= 50:
                pairing_status = await run_realtime_control(
                    request,
                    realtime.get_desktop_pairing_status,
                    manual_code=manual_code,
                    device_id=device_id,
                )
                if pairing_status.get("bound") is not True or pairing_status.get("sessionStatus") != "live":
                    break
                binding_check_ticks = 0
            current_cursor, events, resumable = await run_realtime_event_wait(
                request,
                realtime.wait_for_session_events_after,
                user_id=binding.owner_user_id,
                session_id=binding.session_id,
                cursor=last_cursor,
                timeout_ms=max(100, realtime.settings.realtime_event_block_ms),
            )
            if not resumable:
                pending = await asyncio.to_thread(
                    service.get_next_remote_capture_request,
                    device_id=device_id,
                    manual_code=manual_code,
                )
                if pending is not None:
                    yield _sse_frame("capture-request", {
                        "requestId": pending.request_id,
                        "status": pending.status,
                        "stage": pending.stage,
                    }, cursor=current_cursor)
            for event in events:
                if event.kind != "screenshot-capture-updated":
                    continue
                if event.payload.get("deviceId") != device_id or event.payload.get("status") != "requested":
                    continue
                yield _sse_frame("capture-request", {
                    "requestId": str(event.payload.get("requestId") or ""),
                    "status": "requested",
                    "stage": str(event.payload.get("stage") or "waiting-desktop"),
                    "eventId": event.event_id,
                }, cursor=current_cursor)
            if current_cursor > last_cursor:
                last_cursor = current_cursor
                idle_ticks = 0
            else:
                idle_ticks += 1
                keepalive_ticks = max(1, 15_000 // max(100, realtime.settings.realtime_event_block_ms))
                if idle_ticks >= keepalive_ticks:
                    yield ": keepalive\n\n"
                    idle_ticks = 0

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.post("/capture-requests/{request_id}/desktop-upload", response_model=ApiEnvelope[RemoteScreenshotCaptureRequestResponse])
async def complete_remote_capture_request(
    request_id: str,
    request_context: Request,
    background_tasks: BackgroundTasks,
    device_id: str = Form(alias="deviceId"),
    manual_code: str = Form(alias="manualCode"),
    screenshot: UploadFile = File(...),
    service: ScreenshotAnswerService = Depends(screenshot_answer_service),
    realtime: RealtimeSpeechService = Depends(realtime_speech_service),
) -> ApiEnvelope[RemoteScreenshotCaptureRequestResponse]:
    realtime.get_desktop_capture_binding(device_id=device_id, manual_code=manual_code)
    payload = await screenshot.read()
    capture_request = service.claim_remote_capture_request(
        request_id=request_id,
        device_id=device_id,
        manual_code=manual_code,
    )
    _publish_capture_event(realtime, capture_request)
    background_tasks.add_task(
        service.complete_remote_capture_request_safely,
        request_id=request_id,
        device_id=device_id,
        manual_code=manual_code,
        filename=screenshot.filename or "current-screen.png",
        content_type=screenshot.content_type or "image/png",
        payload=payload,
        on_transition=lambda updated, task: _publish_capture_event(realtime, updated, task),
    )
    return success_response(request=request_context, data=_to_remote_capture_request_response(capture_request), timestamp=utc_now_iso())


@router.post("/capture-requests/{request_id}/desktop-fail", response_model=ApiEnvelope[RemoteScreenshotCaptureRequestResponse])
async def fail_remote_capture_request(
    request_id: str,
    request_context: Request,
    request: FailRemoteScreenshotCaptureRequest,
    service: ScreenshotAnswerService = Depends(screenshot_answer_service),
    realtime: RealtimeSpeechService = Depends(realtime_speech_service),
) -> ApiEnvelope[RemoteScreenshotCaptureRequestResponse]:
    realtime.get_desktop_capture_binding(device_id=request.device_id, manual_code=request.manual_code)
    capture_request = service.fail_remote_capture_request(
        request_id=request_id,
        device_id=request.device_id,
        manual_code=request.manual_code,
        message=request.message,
        stage=request.stage,
    )
    _publish_capture_event(realtime, capture_request)
    return success_response(request=request_context, data=_to_remote_capture_request_response(capture_request), timestamp=utc_now_iso())
