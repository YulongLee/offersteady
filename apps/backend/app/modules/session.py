from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from app.core.logging import utc_now_iso
from app.core.responses import success_response
from app.deps import optional_authenticated_context, realtime_speech_service, resolve_owned_user_id, session_service
from app.ports.authentication import AuthenticatedRequestContext
from app.schemas.foundation import ApiEnvelope, ModuleDescriptor
from app.schemas.session import (
    ActiveSessionConflictResponse,
    ConfirmSessionMaterialsRequest,
    ContinueInterviewSessionResponse,
    ConversationContextEntryResponse,
    CreateInterviewSessionRequest,
    InterviewSessionResponse,
    InterviewReviewSnapshotResponse,
    RecordSessionUsageRequest,
    SessionCommandRequest,
    SessionContextAppendRequest,
    SessionContextWindowResponse,
    SessionUsageRecordResponse,
    SessionUsageResponse,
    SupersedeActiveSessionRequest,
    SupersedeActiveSessionResponse,
    UpdateInterviewLanguageRequest,
)
from app.services.realtime_speech_service import RealtimeSpeechService
from app.services.session_service import SessionService


router = APIRouter(prefix="/sessions", tags=["session"])
descriptor = ModuleDescriptor(
    feature="session",
    owningApp="apps/backend",
    routePrefix="/api/v1/sessions",
    mode="active",
    notes="Authoritative interview session lifecycle, materials, context recovery, and usage boundaries.",
)


def _to_session_response(session) -> InterviewSessionResponse:
    return InterviewSessionResponse(
        sessionId=session.session_id,
        ownerUserId=session.owner_user_id,
        title=session.title,
        interviewLanguage=session.interview_language,
        status=session.status,
        continueTarget=session.continue_target,
        materialBinding={
            "revision": session.material_binding.revision,
            "resumeDocumentId": session.material_binding.resume_document_id,
            "jobDescriptionDocumentId": session.material_binding.job_description_document_id,
            "knowledgeDocumentIds": session.material_binding.knowledge_document_ids,
            "boundDocuments": [
                {
                    "documentId": document.document_id,
                    "documentKind": document.document_kind,
                    "displayName": document.display_name,
                    "status": document.status,
                    "documentVersionId": document.document_version_id,
                    "indexState": document.index_state,
                    "knowledgeCollectionId": document.knowledge_collection_id,
                    "summary": document.summary,
                    "active": document.active,
                }
                for document in session.material_binding.bound_documents
            ],
            "confirmedAtMs": session.material_binding.confirmed_at_ms,
        },
        configSnapshot={
            "modelConfigRef": session.config_snapshot.model_config_ref,
            "promptConfigRef": session.config_snapshot.prompt_config_ref,
            "retrievalConfigRef": session.config_snapshot.retrieval_config_ref,
            "versionTag": session.config_snapshot.version_tag,
            "capturedAtMs": session.config_snapshot.captured_at_ms,
        },
        usageTotals={
            "promptTokens": session.usage_totals.prompt_tokens,
            "completionTokens": session.usage_totals.completion_tokens,
            "totalTokens": session.usage_totals.total_tokens,
            "embeddingTokens": session.usage_totals.embedding_tokens,
            "retrievalTokens": session.usage_totals.retrieval_tokens,
            "recordCount": session.usage_totals.record_count,
        },
        integrationReferences=[
            {
                "name": reference.name,
                "sessionId": reference.session_id,
                "details": reference.details,
            }
            for reference in session.integration_references
        ],
        restartOfSessionId=session.restart_of_session_id,
        startedAtMs=session.started_at_ms,
        endedAtMs=session.ended_at_ms,
        createdAtMs=session.created_at_ms,
        updatedAtMs=session.updated_at_ms,
        lastActivityAtMs=session.last_activity_at_ms,
    )


@router.get("/status", response_model=ApiEnvelope[dict[str, str]])
async def status(request: Request) -> ApiEnvelope[dict[str, str]]:
    return success_response(
        request=request,
        data={"status": "active", "feature": "session", "message": "Interview Session Service is available for lifecycle, context, and usage management."},
        timestamp=utc_now_iso(),
    )


@router.post("", response_model=ApiEnvelope[InterviewSessionResponse])
async def create_session(
    request_context: Request,
    request: CreateInterviewSessionRequest,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: SessionService = Depends(session_service),
) -> ApiEnvelope[InterviewSessionResponse]:
    session = service.create_session(
        user_id=resolve_owned_user_id(explicit_user_id=request.user_id, auth_context=auth_context),
        title=request.title,
        interview_language=request.interview_language,
    )
    return success_response(request=request_context, data=_to_session_response(session), timestamp=utc_now_iso())


@router.get("", response_model=ApiEnvelope[list[InterviewSessionResponse]])
async def list_sessions(
    request: Request,
    user_id: str | None = Query(default=None, alias="userId"),
    status: str | None = None,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: SessionService = Depends(session_service),
) -> ApiEnvelope[list[InterviewSessionResponse]]:
    sessions = service.list_sessions(user_id=resolve_owned_user_id(explicit_user_id=user_id, auth_context=auth_context), status=status)
    return success_response(request=request, data=[_to_session_response(session) for session in sessions], timestamp=utc_now_iso())


@router.get("/{session_id}", response_model=ApiEnvelope[InterviewSessionResponse])
async def get_session(
    session_id: str,
    request: Request,
    user_id: str | None = Query(default=None, alias="userId"),
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: SessionService = Depends(session_service),
) -> ApiEnvelope[InterviewSessionResponse]:
    session = service.get_session(user_id=resolve_owned_user_id(explicit_user_id=user_id, auth_context=auth_context), session_id=session_id)
    return success_response(request=request, data=_to_session_response(session), timestamp=utc_now_iso())


@router.get("/{session_id}/review", response_model=ApiEnvelope[InterviewReviewSnapshotResponse])
async def get_interview_review(
    session_id: str,
    request: Request,
    user_id: str | None = Query(default=None, alias="userId"),
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: SessionService = Depends(session_service),
) -> ApiEnvelope[InterviewReviewSnapshotResponse]:
    resolved_user_id = resolve_owned_user_id(explicit_user_id=user_id, auth_context=auth_context)
    session, transcripts = service.get_review_transcripts(user_id=resolved_user_id, session_id=session_id)
    duration_ms = max(0, (session.ended_at_ms or session.updated_at_ms) - (session.started_at_ms or session.created_at_ms))
    return success_response(
        request=request,
        data=InterviewReviewSnapshotResponse(
            sessionId=session.session_id,
            title=session.title,
            status=session.status,
            startedAtMs=session.started_at_ms,
            endedAtMs=session.ended_at_ms,
            durationMs=duration_ms,
            transcripts=[
                {
                    "id": entry.entry_id,
                    "role": entry.role,
                    "speakerLabel": "面试官" if entry.role == "interviewer" else "我",
                    "text": entry.content,
                    "occurredAtMs": entry.created_at_ms,
                    "ordering": entry.ordering,
                }
                for entry in transcripts
            ],
        ),
        timestamp=utc_now_iso(),
    )


@router.delete("/{session_id}", response_model=ApiEnvelope[dict[str, str]])
async def delete_session(
    session_id: str,
    request: Request,
    user_id: str | None = Query(default=None, alias="userId"),
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: SessionService = Depends(session_service),
) -> ApiEnvelope[dict[str, str]]:
    service.delete_session(user_id=resolve_owned_user_id(explicit_user_id=user_id, auth_context=auth_context), session_id=session_id)
    return success_response(request=request, data={"sessionId": session_id, "status": "deleted"}, timestamp=utc_now_iso())


@router.get("/{session_id}/active-conflict", response_model=ApiEnvelope[ActiveSessionConflictResponse])
async def get_active_session_conflict(
    session_id: str,
    request: Request,
    user_id: str | None = Query(default=None, alias="userId"),
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: RealtimeSpeechService = Depends(realtime_speech_service),
) -> ApiEnvelope[ActiveSessionConflictResponse]:
    resolved_user_id = resolve_owned_user_id(explicit_user_id=user_id, auth_context=auth_context)
    active_session = service.get_active_interview_conflict(user_id=resolved_user_id, session_id=session_id)
    return success_response(
        request=request,
        data=ActiveSessionConflictResponse(
            currentSessionId=session_id,
            activeSession=_to_session_response(active_session) if active_session else None,
        ),
        timestamp=utc_now_iso(),
    )


@router.post("/{session_id}/supersede-active", response_model=ApiEnvelope[SupersedeActiveSessionResponse])
async def supersede_active_sessions(
    session_id: str,
    request_context: Request,
    request: SupersedeActiveSessionRequest,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: RealtimeSpeechService = Depends(realtime_speech_service),
) -> ApiEnvelope[SupersedeActiveSessionResponse]:
    user_id = resolve_owned_user_id(explicit_user_id=request.user_id, auth_context=auth_context)
    retired_session_ids = service.supersede_active_interviews(
        user_id=user_id,
        session_id=session_id,
        expected_previous_session_id=request.expected_previous_session_id,
    )
    return success_response(
        request=request_context,
        data=SupersedeActiveSessionResponse(currentSessionId=session_id, retiredSessionIds=retired_session_ids),
        timestamp=utc_now_iso(),
    )


@router.post("/{session_id}/continue", response_model=ApiEnvelope[ContinueInterviewSessionResponse])
async def continue_session(
    session_id: str,
    request_context: Request,
    request: SessionCommandRequest,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: SessionService = Depends(session_service),
) -> ApiEnvelope[ContinueInterviewSessionResponse]:
    session = service.continue_session(user_id=resolve_owned_user_id(explicit_user_id=request.user_id, auth_context=auth_context), session_id=session_id)
    return success_response(
        request=request_context,
        data=ContinueInterviewSessionResponse(target=session.continue_target, session=_to_session_response(session)),
        timestamp=utc_now_iso(),
    )

@router.get("/{session_id}/idle-status", response_model=ApiEnvelope[dict[str, object]])
async def idle_status(
    session_id: str,
    request: Request,
    user_id: str | None = Query(default=None, alias="userId"),
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: RealtimeSpeechService = Depends(realtime_speech_service),
) -> ApiEnvelope[dict[str, object]]:
    resolved_user_id = resolve_owned_user_id(explicit_user_id=user_id, auth_context=auth_context)
    result = service.reconcile_idle_session(user_id=resolved_user_id, session_id=session_id)
    return success_response(request=request, data=result, timestamp=utc_now_iso())


@router.post("/{session_id}/materials/confirm", response_model=ApiEnvelope[InterviewSessionResponse])
async def confirm_materials(
    session_id: str,
    request_context: Request,
    request: ConfirmSessionMaterialsRequest,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: SessionService = Depends(session_service),
) -> ApiEnvelope[InterviewSessionResponse]:
    user_id = resolve_owned_user_id(explicit_user_id=request.user_id, auth_context=auth_context)
    session = service.confirm_materials(
        user_id=user_id,
        session_id=session_id,
        resume_document_id=request.resume_document_id,
        job_description_document_id=request.job_description_document_id,
        knowledge_document_ids=request.knowledge_document_ids,
    )
    return success_response(request=request_context, data=_to_session_response(session), timestamp=utc_now_iso())


@router.patch("/{session_id}/language", response_model=ApiEnvelope[InterviewSessionResponse])
async def update_interview_language(
    session_id: str,
    request_context: Request,
    request: UpdateInterviewLanguageRequest,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: SessionService = Depends(session_service),
) -> ApiEnvelope[InterviewSessionResponse]:
    session = service.update_interview_language(
        user_id=resolve_owned_user_id(explicit_user_id=request.user_id, auth_context=auth_context),
        session_id=session_id,
        interview_language=request.interview_language,
    )
    return success_response(request=request_context, data=_to_session_response(session), timestamp=utc_now_iso())


@router.post("/{session_id}/start", response_model=ApiEnvelope[InterviewSessionResponse])
async def start_session(
    session_id: str,
    request_context: Request,
    request: SessionCommandRequest,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: RealtimeSpeechService = Depends(realtime_speech_service),
) -> ApiEnvelope[InterviewSessionResponse]:
    session = service.start_live_session(
        user_id=resolve_owned_user_id(explicit_user_id=request.user_id, auth_context=auth_context),
        session_id=session_id,
    )
    return success_response(request=request_context, data=_to_session_response(session), timestamp=utc_now_iso())


@router.post("/{session_id}/end", response_model=ApiEnvelope[InterviewSessionResponse])
async def end_session(
    session_id: str,
    request_context: Request,
    request: SessionCommandRequest,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: RealtimeSpeechService = Depends(realtime_speech_service),
) -> ApiEnvelope[InterviewSessionResponse]:
    user_id = resolve_owned_user_id(explicit_user_id=request.user_id, auth_context=auth_context)
    service.terminate_session_for_admin(user_id=user_id, session_id=session_id)
    session = service.session_service.get_session(user_id=user_id, session_id=session_id)
    return success_response(request=request_context, data=_to_session_response(session), timestamp=utc_now_iso())


@router.post("/{session_id}/restart", response_model=ApiEnvelope[InterviewSessionResponse])
async def restart_session(
    session_id: str,
    request_context: Request,
    request: SessionCommandRequest,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: SessionService = Depends(session_service),
) -> ApiEnvelope[InterviewSessionResponse]:
    session = service.restart_session(user_id=resolve_owned_user_id(explicit_user_id=request.user_id, auth_context=auth_context), session_id=session_id)
    return success_response(request=request_context, data=_to_session_response(session), timestamp=utc_now_iso())


@router.post("/{session_id}/context", response_model=ApiEnvelope[ConversationContextEntryResponse])
async def append_context(
    session_id: str,
    request_context: Request,
    request: SessionContextAppendRequest,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: SessionService = Depends(session_service),
) -> ApiEnvelope[ConversationContextEntryResponse]:
    user_id = resolve_owned_user_id(explicit_user_id=request.user_id, auth_context=auth_context)
    entry = service.append_context(
        user_id=user_id,
        session_id=session_id,
        role=request.role,
        source_kind=request.source_kind,
        content=request.content,
        visibility=request.visibility,
        related_task_id=request.related_task_id,
    )
    return success_response(
        request=request_context,
        data=ConversationContextEntryResponse(
            entryId=entry.entry_id,
            role=entry.role,
            sourceKind=entry.source_kind,
            content=entry.content,
            visibility=entry.visibility,
            ordering=entry.ordering,
            relatedTaskId=entry.related_task_id,
            createdAtMs=entry.created_at_ms,
        ),
        timestamp=utc_now_iso(),
    )


@router.get("/{session_id}/context", response_model=ApiEnvelope[SessionContextWindowResponse])
async def get_context_window(
    session_id: str,
    request: Request,
    user_id: str | None = Query(default=None, alias="userId"),
    limit: int | None = Query(default=None),
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: SessionService = Depends(session_service),
) -> ApiEnvelope[SessionContextWindowResponse]:
    entries = service.get_context_window(user_id=resolve_owned_user_id(explicit_user_id=user_id, auth_context=auth_context), session_id=session_id, limit=limit)
    return success_response(
        request=request,
        data=SessionContextWindowResponse(
            sessionId=session_id,
            entries=[
                ConversationContextEntryResponse(
                    entryId=entry.entry_id,
                    role=entry.role,
                    sourceKind=entry.source_kind,
                    content=entry.content,
                    visibility=entry.visibility,
                    ordering=entry.ordering,
                    relatedTaskId=entry.related_task_id,
                    createdAtMs=entry.created_at_ms,
                )
                for entry in entries
            ],
            totalCount=len(entries),
        ),
        timestamp=utc_now_iso(),
    )


@router.post("/{session_id}/usage", response_model=ApiEnvelope[InterviewSessionResponse])
async def record_usage(
    session_id: str,
    request_context: Request,
    request: RecordSessionUsageRequest,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: SessionService = Depends(session_service),
) -> ApiEnvelope[InterviewSessionResponse]:
    session = service.record_usage(
        user_id=resolve_owned_user_id(explicit_user_id=request.user_id, auth_context=auth_context),
        session_id=session_id,
        usage_kind=request.usage_kind,
        prompt_tokens=request.prompt_tokens,
        completion_tokens=request.completion_tokens,
        total_tokens=request.total_tokens,
        provider_name=request.provider_name,
        model_name=request.model_name,
        related_task_id=request.related_task_id,
    )
    return success_response(request=request_context, data=_to_session_response(session), timestamp=utc_now_iso())


@router.get("/{session_id}/usage", response_model=ApiEnvelope[SessionUsageResponse])
async def get_usage(
    session_id: str,
    request: Request,
    user_id: str | None = Query(default=None, alias="userId"),
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: SessionService = Depends(session_service),
) -> ApiEnvelope[SessionUsageResponse]:
    totals, records = service.get_usage(user_id=resolve_owned_user_id(explicit_user_id=user_id, auth_context=auth_context), session_id=session_id)
    return success_response(
        request=request,
        data=SessionUsageResponse(
            sessionId=session_id,
            totals={
                "promptTokens": totals.prompt_tokens,
                "completionTokens": totals.completion_tokens,
                "totalTokens": totals.total_tokens,
                "embeddingTokens": totals.embedding_tokens,
                "retrievalTokens": totals.retrieval_tokens,
                "recordCount": totals.record_count,
            },
            records=[
                SessionUsageRecordResponse(
                    usageId=record.usage_id,
                    usageKind=record.usage_kind,
                    promptTokens=record.prompt_tokens,
                    completionTokens=record.completion_tokens,
                    totalTokens=record.total_tokens,
                    providerName=record.provider_name,
                    modelName=record.model_name,
                    relatedTaskId=record.related_task_id,
                    createdAtMs=record.created_at_ms,
                )
                for record in records
            ],
        ),
        timestamp=utc_now_iso(),
    )
