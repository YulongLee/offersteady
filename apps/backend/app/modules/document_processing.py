from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from app.core.errors import DomainRequestError
from app.core.logging import utc_now_iso
from app.core.responses import success_response
from app.deps import document_processing_service, optional_authenticated_context, resolve_owned_user_id
from app.ports.authentication import AuthenticatedRequestContext
from app.schemas.document_processing import (
    DocumentProcessingStatusResponse,
    ProcessingTaskEventResponse,
    ProcessingTaskResponse,
    RetryProcessingTaskRequest,
)
from app.schemas.foundation import ApiEnvelope, ModuleDescriptor
from app.services.document_processing import DocumentProcessingService


router = APIRouter(prefix="/document-processing", tags=["document-processing"])
descriptor = ModuleDescriptor(
    feature="document-processing",
    owningApp="apps/backend",
    routePrefix="/api/v1/document-processing",
    mode="active",
    notes="Shared asynchronous processing pipeline for resume, JD, and knowledge documents.",
)


def _ready_for_ai(stage: str, document_status: str | None = None) -> bool:
    return stage == "COMPLETED" and document_status == "ready"


def _to_task_response(task, *, document_status: str | None = None) -> ProcessingTaskResponse:
    return ProcessingTaskResponse(
        taskId=task.task_id,
        documentId=task.document_id,
        ownerUserId=task.owner_user_id,
        documentKind=task.document_kind,
        currentStage=task.current_stage,
        retryCount=task.retry_count,
        maxRetries=task.max_retries,
        parserProvider=task.parser_provider,
        embeddingProvider=task.embedding_provider,
        chunkCount=task.chunk_count,
        errorCode=task.error_code,
        errorMessage=task.error_message,
        createdAtMs=task.created_at_ms,
        updatedAtMs=task.updated_at_ms,
        queuedAtMs=task.queued_at_ms,
        startedAtMs=task.started_at_ms,
        completedAtMs=task.completed_at_ms,
        lastRetryAtMs=task.last_retry_at_ms,
        readyForAi=_ready_for_ai(task.current_stage, document_status),
    )


@router.get("/tasks/{task_id}", response_model=ApiEnvelope[ProcessingTaskResponse])
async def get_processing_task(
    task_id: str,
    request: Request,
    user_id: str | None = Query(default=None, alias="userId"),
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: DocumentProcessingService = Depends(document_processing_service),
) -> ApiEnvelope[ProcessingTaskResponse]:
    task = service.get_task(task_id=task_id, user_id=resolve_owned_user_id(explicit_user_id=user_id, auth_context=auth_context))
    document = service.document_repository.get_by_id(task.document_id)
    return success_response(request=request, data=_to_task_response(task, document_status=document.status if document else None), timestamp=utc_now_iso())


@router.get("/documents/{document_id}", response_model=ApiEnvelope[DocumentProcessingStatusResponse])
async def get_document_processing_status(
    document_id: str,
    request: Request,
    user_id: str | None = Query(default=None, alias="userId"),
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: DocumentProcessingService = Depends(document_processing_service),
) -> ApiEnvelope[DocumentProcessingStatusResponse]:
    resolved_user_id = resolve_owned_user_id(explicit_user_id=user_id, auth_context=auth_context)
    latest_task = service.latest_task_for_document(document_id=document_id, user_id=resolved_user_id)
    if latest_task is None:
        document = service.document_repository.get_by_id(document_id)
        if document is None:
            raise DomainRequestError("document-processing", "get-document-status", "文档不存在。", 404)
        if document.owner_user_id != resolved_user_id:
            raise DomainRequestError("document-processing", "get-document-status", "不能查看其他用户的处理状态。", 403)
        raise DomainRequestError("document-processing", "get-document-status", "当前文档还没有处理任务。", 404)
    document = service.document_repository.get_by_id(latest_task.document_id)
    events = service.list_events(task_id=latest_task.task_id, user_id=resolved_user_id)
    return success_response(
        request=request,
        data=DocumentProcessingStatusResponse(
            documentId=latest_task.document_id,
            documentKind=latest_task.document_kind,
            latestTask=_to_task_response(latest_task, document_status=document.status if document else None),
            events=[
                ProcessingTaskEventResponse(
                    eventId=event.event_id,
                    taskId=event.task_id,
                    stage=event.stage,
                    retryCount=event.retry_count,
                    eventName=event.event_name,
                    durationMs=event.duration_ms,
                    errorCode=event.error_code,
                    createdAtMs=event.created_at_ms,
                )
                for event in events
            ],
            readyForAi=_ready_for_ai(latest_task.current_stage, document.status if document else None),
        ),
        timestamp=utc_now_iso(),
    )


@router.post("/tasks/{task_id}/retry", response_model=ApiEnvelope[ProcessingTaskResponse])
async def retry_processing_task(
    task_id: str,
    request_context: Request,
    request: RetryProcessingTaskRequest,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: DocumentProcessingService = Depends(document_processing_service),
) -> ApiEnvelope[ProcessingTaskResponse]:
    task = service.retry_task(task_id=task_id, user_id=resolve_owned_user_id(explicit_user_id=request.user_id, auth_context=auth_context))
    document = service.document_repository.get_by_id(task.document_id)
    return success_response(request=request_context, data=_to_task_response(task, document_status=document.status if document else None), timestamp=utc_now_iso())
