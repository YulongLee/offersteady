from __future__ import annotations

import json
from collections.abc import Iterator
from time import time

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from app.core.errors import DomainRequestError
from app.core.config import get_settings
from app.core.logging import utc_now_iso
from app.core.responses import success_response
from app.deps import chat_service, optional_authenticated_context, realtime_speech_service, resolve_owned_user_id
from app.ports.authentication import AuthenticatedRequestContext
from app.schemas.foundation import ApiEnvelope, ModuleDescriptor
from app.schemas.live_answer import CancelLiveAnswerRequest, CancelLiveAnswerResponse, LiveAnswerQuestionRequest, LiveAnswerResponse, LiveAnswerStreamEvent, LiveAnswerTaskResponse, LiveAnswerChunkResponse
from app.services.chat_service import ChatService
from app.services.live_answer_stream_executor import LiveAnswerStreamExecutor
from app.services.realtime_speech_service import RealtimeSpeechService


router = APIRouter(prefix="/live-answer", tags=["live-answer"])
descriptor = ModuleDescriptor(
    feature="live-answer",
    owningApp="apps/backend",
    routePrefix="/api/v1/live-answer",
    mode="active",
    notes="Chat-powered interview answer generation with retrieval grounding, streaming chunks, and session history.",
)


def _to_task_response(task) -> LiveAnswerTaskResponse:
    return LiveAnswerTaskResponse(
        taskId=task.task_id,
        sessionId=task.session_id,
        ownerUserId=task.owner_user_id,
        question=task.question,
        rawQuestion=task.raw_question,
        normalizedQuestion=task.normalized_question,
        questionNormalizationStatus=task.question_normalization_status,
        questionId=task.question_id,
        questionRevision=task.question_revision,
        clickedAtMs=task.clicked_at_ms,
        prefetchRevision=task.prefetch_revision,
        answerText=task.answer_text,
        status=task.status,
        streamMode=task.stream_mode,
        providerName=task.provider_name,
        modelName=task.model_name,
        promptTemplateId=task.prompt_template_id,
        promptVersion=task.prompt_version,
        retrievalExcerptCount=task.retrieval_excerpt_count,
        materialContextStatus=task.material_context_status,
        fixedSourceCount=task.fixed_source_count,
        retrievedSourceCount=task.retrieved_source_count,
        materialProvenance=task.material_provenance,
        unavailableMaterialSources=task.unavailable_material_sources,
        webSearchEnabled=task.web_search_enabled,
        quickAnswerCompleted=task.quick_answer_completed,
        webSearchStatus=task.web_search_status,
        webSources=task.web_sources,
        retryCount=task.retry_count,
        errorCode=task.error_code,
        errorMessage=task.error_message,
        createdAtMs=task.created_at_ms,
        updatedAtMs=task.updated_at_ms,
        completedAtMs=task.completed_at_ms,
        chunks=[
            LiveAnswerChunkResponse(sequence=chunk.sequence, text=chunk.text, isFinal=chunk.is_final)
            for chunk in task.chunks
        ],
    )


def _to_stream_event(payload: dict) -> LiveAnswerStreamEvent:
    task = payload.get("task")
    chunk = payload.get("chunk")
    return LiveAnswerStreamEvent(
        type=payload["type"],
        task=_to_task_response(task) if task is not None else None,
        chunk=LiveAnswerChunkResponse(sequence=chunk.sequence, text=chunk.text, isFinal=chunk.is_final) if chunk is not None else None,
        retrieval=payload.get("retrieval"),
        errorCode=payload.get("error_code"),
        errorMessage=payload.get("error_message"),
        partialText=payload.get("partial_text"),
        timing=payload.get("timing"),
    )


def _sse_frame(event: LiveAnswerStreamEvent) -> str:
    data = event.model_dump(by_alias=True, exclude_none=True)
    return f"event: {event.type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _publish_answer_task_event(
    realtime: RealtimeSpeechService,
    *,
    user_id: str,
    session_id: str,
    phase: str,
    task,
    trigger: str = "manual",
) -> None:
    if task is None:
        return
    realtime.publish_session_event(
        user_id=user_id,
        session_id=session_id,
        kind="answer-task-updated",
        payload={
            "phase": phase,
            "trigger": trigger,
            "task": _to_task_response(task).model_dump(by_alias=True),
        },
    )


@router.get("/status", response_model=ApiEnvelope[dict[str, object]])
async def status(request: Request) -> ApiEnvelope[dict[str, object]]:
    settings = get_settings()
    web_search_enabled = bool(getattr(settings, "web_search_enabled", False))
    web_search_configured = bool(
        web_search_enabled
        and str(getattr(settings, "web_search_responses_base_url", "") or "").strip()
        and str(getattr(settings, "web_search_api_key", "") or getattr(settings, "chat_qwen_api_key", "") or "").strip()
    )
    return success_response(
        request=request,
        data={
            "status": "active",
            "feature": "live-answer",
            "message": "Chat Service is available for session-grounded real-time interview answers.",
            "webSearchEnabled": web_search_enabled,
            "webSearchAvailable": web_search_configured,
            "webSearchPoints": int(getattr(settings, "web_search_points", 20) or 20),
        },
        timestamp=utc_now_iso(),
    )


@router.post("/questions", response_model=ApiEnvelope[LiveAnswerResponse])
async def start_live_answer(
    request_context: Request,
    request: LiveAnswerQuestionRequest,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: ChatService = Depends(chat_service),
    realtime: RealtimeSpeechService = Depends(realtime_speech_service),
) -> ApiEnvelope[LiveAnswerResponse]:
    user_id = resolve_owned_user_id(explicit_user_id=request.user_id, auth_context=auth_context)
    claim = None
    if request.trigger_mode == "auto":
        claim = realtime.claim_auto_answer_candidate(
            user_id=user_id, session_id=request.session_id, candidate_id=request.question_id or ""
        )
    claim_bound = False
    try:
        task, retrieval = service.answer_question(
            user_id=user_id,
            session_id=request.session_id,
            question=request.question,
            stream=request.stream,
            usage_id=request.idempotency_key,
            web_search_enabled=request.web_search_enabled,
        )
        if claim is not None:
            realtime.bind_auto_answer_candidate(
                user_id=user_id, candidate_id=claim.candidate_id,
                claim_id=claim.answer_task_id or "", task_id=task.task_id,
            )
            claim_bound = True
    finally:
        if claim is not None:
            if claim_bound:
                realtime.finish_auto_answer_candidate(user_id=user_id, candidate_id=claim.candidate_id)
            else:
                realtime.release_auto_answer_candidate(
                    user_id=user_id, candidate_id=claim.candidate_id, claim_id=claim.answer_task_id or ""
                )
    _publish_answer_task_event(
        realtime, user_id=user_id, session_id=request.session_id,
        phase=task.status, task=task, trigger=request.trigger_mode,
    )
    return success_response(
        request=request_context,
        data=LiveAnswerResponse(task=_to_task_response(task), retrieval=retrieval),
        timestamp=utc_now_iso(),
    )


@router.post("/questions/stream")
async def stream_live_answer(
    request_context: Request,
    request: LiveAnswerQuestionRequest,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: ChatService = Depends(chat_service),
    realtime: RealtimeSpeechService = Depends(realtime_speech_service),
) -> StreamingResponse:
    route_received_at_ms = int(time() * 1_000)
    user_id = resolve_owned_user_id(explicit_user_id=request.user_id, auth_context=auth_context)
    executor = getattr(request_context.app.state, "live_answer_stream_executor", None)
    if not isinstance(executor, LiveAnswerStreamExecutor) or not executor.available():
        raise DomainRequestError(
            "live-answer",
            "stream-admission",
            "回答服务正在启动，请稍后重试。",
            503,
            error_code="live_answer_stream_unavailable",
            retry_after_ms=1_000,
        )
    lease = executor.try_acquire()
    if lease is None:
        raise DomainRequestError(
            "live-answer",
            "stream-admission",
            "回答请求较多，请稍后重试。",
            503,
            error_code="live_answer_stream_capacity",
            retry_after_ms=1_000,
        )
    claim = None
    try:
        if request.trigger_mode == "auto":
            claim = realtime.claim_auto_answer_candidate(
                user_id=user_id, session_id=request.session_id, candidate_id=request.question_id or ""
            )
    except Exception:
        lease.release()
        raise

    def events() -> Iterator[str]:
        answer_generator_started_at_ms = int(time() * 1_000)
        first_visible_sent = False
        claim_bound = False
        last_task = None
        terminal = False
        answer_iterator = None
        try:
            answer_iterator = service.stream_answer_question(
                user_id=user_id,
                session_id=request.session_id,
                question=request.question,
                usage_id=request.idempotency_key,
                question_id=request.question_id,
                question_revision=request.question_revision,
                clicked_at_ms=request.clicked_at_ms,
                prefetch_revision=request.prefetch_revision,
                web_search_enabled=request.web_search_enabled,
                route_received_at_ms=route_received_at_ms,
                executor_admitted_at_ms=lease.admitted_at_ms,
                answer_generator_started_at_ms=answer_generator_started_at_ms,
            )
            for payload in answer_iterator:
                phase = str(payload.get("type") or "update")
                task = payload.get("task")
                if task is not None:
                    last_task = task
                terminal = phase in {"complete", "completed", "error", "failed", "cancelled"}
                if claim is not None and not claim_bound and task is not None:
                    realtime.bind_auto_answer_candidate(
                        user_id=user_id, candidate_id=claim.candidate_id,
                        claim_id=claim.answer_task_id or "", task_id=task.task_id,
                    )
                    claim_bound = True
                if phase in {"task-started", "quick-completed", "retrieval", "complete", "completed", "error", "failed", "cancelled"}:
                    _publish_answer_task_event(
                        realtime,
                        user_id=user_id,
                        session_id=request.session_id,
                        phase=phase,
                        task=task,
                        trigger=request.trigger_mode,
                    )
                if not first_visible_sent and phase == "chunk" and payload.get("chunk") is not None:
                    first_visible_sent = True
                    timing = dict(payload.get("timing") or {})
                    timing["sseYieldAtMs"] = int(time() * 1000)
                    payload = {**payload, "timing": timing}
                yield _sse_frame(_to_stream_event(payload))
        finally:
            try:
                if answer_iterator is not None:
                    answer_iterator.close()
                # A browser can abort before receiving task-started. It cannot
                # call cancel by ID then, so the stream owns this cleanup.
                if not terminal and last_task is not None:
                    outcome, cancelled = service.cancel_task(user_id=user_id, task_id=last_task.task_id)
                    if outcome in {"cancelled", "already-cancelled"}:
                        _publish_answer_task_event(
                            realtime, user_id=user_id, session_id=request.session_id,
                            phase="cancelled", task=cancelled, trigger=request.trigger_mode,
                        )
            finally:
                if claim is not None:
                    if claim_bound:
                        realtime.finish_auto_answer_candidate(user_id=user_id, candidate_id=claim.candidate_id)
                    else:
                        realtime.release_auto_answer_candidate(
                            user_id=user_id, candidate_id=claim.candidate_id,
                            claim_id=claim.answer_task_id or "",
                        )

    return StreamingResponse(
        executor.stream(lease, events),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/tasks/{task_id}", response_model=ApiEnvelope[LiveAnswerTaskResponse])
async def get_live_answer_task(
    task_id: str,
    request: Request,
    user_id: str | None = Query(default=None, alias="userId"),
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: ChatService = Depends(chat_service),
) -> ApiEnvelope[LiveAnswerTaskResponse]:
    task = service.get_task(user_id=resolve_owned_user_id(explicit_user_id=user_id, auth_context=auth_context), task_id=task_id)
    return success_response(request=request, data=_to_task_response(task), timestamp=utc_now_iso())


@router.post("/tasks/{task_id}/cancel", response_model=ApiEnvelope[CancelLiveAnswerResponse])
async def cancel_live_answer_task(
    task_id: str,
    request_context: Request,
    request: CancelLiveAnswerRequest,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: ChatService = Depends(chat_service),
    realtime: RealtimeSpeechService = Depends(realtime_speech_service),
) -> ApiEnvelope[CancelLiveAnswerResponse]:
    user_id = resolve_owned_user_id(explicit_user_id=request.user_id, auth_context=auth_context)
    outcome, task = service.cancel_task(
        user_id=user_id,
        task_id=task_id,
        expected_revision=request.expected_revision,
    )
    _publish_answer_task_event(realtime, user_id=user_id, session_id=task.session_id, phase=task.status, task=task)
    return success_response(
        request=request_context,
        data=CancelLiveAnswerResponse(
            outcome=outcome,
            task=_to_task_response(task),
            billingReleased=outcome in {"cancelled", "already-cancelled"},
        ),
        timestamp=utc_now_iso(),
    )


@router.get("/sessions/{session_id}/history", response_model=ApiEnvelope[list[LiveAnswerTaskResponse]])
async def get_live_answer_history(
    session_id: str,
    request: Request,
    user_id: str | None = Query(default=None, alias="userId"),
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: ChatService = Depends(chat_service),
) -> ApiEnvelope[list[LiveAnswerTaskResponse]]:
    tasks = service.list_session_history(user_id=resolve_owned_user_id(explicit_user_id=user_id, auth_context=auth_context), session_id=session_id)
    return success_response(request=request, data=[_to_task_response(task) for task in tasks], timestamp=utc_now_iso())
