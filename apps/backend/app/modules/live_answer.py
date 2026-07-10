from __future__ import annotations

import json
from collections.abc import Iterator

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from app.core.logging import utc_now_iso
from app.core.responses import success_response
from app.deps import chat_service, optional_authenticated_context, resolve_owned_user_id
from app.ports.authentication import AuthenticatedRequestContext
from app.schemas.foundation import ApiEnvelope, ModuleDescriptor
from app.schemas.live_answer import CancelLiveAnswerRequest, CancelLiveAnswerResponse, LiveAnswerQuestionRequest, LiveAnswerResponse, LiveAnswerStreamEvent, LiveAnswerTaskResponse, LiveAnswerChunkResponse
from app.services.chat_service import ChatService


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
    )


def _sse_frame(event: LiveAnswerStreamEvent) -> str:
    data = event.model_dump(by_alias=True, exclude_none=True)
    return f"event: {event.type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.get("/status", response_model=ApiEnvelope[dict[str, str]])
async def status(request: Request) -> ApiEnvelope[dict[str, str]]:
    return success_response(
        request=request,
        data={"status": "active", "feature": "live-answer", "message": "Chat Service is available for session-grounded real-time interview answers."},
        timestamp=utc_now_iso(),
    )


@router.post("/questions", response_model=ApiEnvelope[LiveAnswerResponse])
async def start_live_answer(
    request_context: Request,
    request: LiveAnswerQuestionRequest,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: ChatService = Depends(chat_service),
) -> ApiEnvelope[LiveAnswerResponse]:
    task, retrieval = service.answer_question(
        user_id=resolve_owned_user_id(explicit_user_id=request.user_id, auth_context=auth_context),
        session_id=request.session_id,
        question=request.question,
        stream=request.stream,
    )
    return success_response(
        request=request_context,
        data=LiveAnswerResponse(task=_to_task_response(task), retrieval=retrieval),
        timestamp=utc_now_iso(),
    )


@router.post("/questions/stream")
async def stream_live_answer(
    request: LiveAnswerQuestionRequest,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: ChatService = Depends(chat_service),
) -> StreamingResponse:
    user_id = resolve_owned_user_id(explicit_user_id=request.user_id, auth_context=auth_context)

    def events() -> Iterator[str]:
        for payload in service.stream_answer_question(user_id=user_id, session_id=request.session_id, question=request.question):
            yield _sse_frame(_to_stream_event(payload))

    return StreamingResponse(
        events(),
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
) -> ApiEnvelope[CancelLiveAnswerResponse]:
    outcome, task = service.cancel_task(
        user_id=resolve_owned_user_id(explicit_user_id=request.user_id, auth_context=auth_context),
        task_id=task_id,
        expected_revision=request.expected_revision,
    )
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
