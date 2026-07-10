from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile

from app.core.logging import utc_now_iso
from app.core.responses import success_response
from app.deps import document_service, optional_authenticated_context, resolve_owned_user_id
from app.ports.authentication import AuthenticatedRequestContext
from app.schemas.document_service import CompleteDocumentUploadRequest, CreateDocumentUploadIntentRequest
from app.schemas.foundation import ApiEnvelope, ModuleDescriptor
from app.schemas.material_upload import CompleteUploadRequest, MaterialUploadCompletionResponse, UploadIntentRequest, UploadIntentResponse
from app.services.document_service import DocumentService


router = APIRouter(prefix="/resume", tags=["resume"])
descriptor = ModuleDescriptor(
    feature="resume",
    owning_app="apps/backend",
    route_prefix="/api/v1/resume",
    mode="active",
    notes="Resume uploads issue OSS intents, confirm completion, and register non-ready material sources.",
)


@router.get("/status", response_model=ApiEnvelope[dict[str, str]])
async def status(request: Request) -> ApiEnvelope[dict[str, str]]:
    return success_response(
        request=request,
        data={"status": "active", "feature": "resume", "message": "Resume upload pipeline is available in MVP upload mode."},
        timestamp=utc_now_iso(),
    )


@router.post("/upload-intents", response_model=ApiEnvelope[UploadIntentResponse])
async def create_resume_upload_intent(
    request_context: Request,
    request: UploadIntentRequest,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: DocumentService = Depends(document_service),
) -> ApiEnvelope[UploadIntentResponse]:
    user_id = resolve_owned_user_id(explicit_user_id=request.user_id, auth_context=auth_context)
    intent = service.create_upload_intent(
        user_id=user_id,
        document_kind="resume",
        filename=request.filename,
        content_type=request.content_type,
        size_bytes=request.size_bytes,
    )
    return success_response(
        request=request_context,
        data=UploadIntentResponse(
            intentId=intent.intent_id,
            userId=intent.user_id,
            materialKind=intent.document_kind,
            uploadMethod=intent.upload_method,
            filename=intent.filename,
            fileKind=intent.file_kind,
            contentType=intent.content_type,
            objectKey=intent.object_key,
            uploadUrl=intent.upload_url,
            uploadFields=intent.upload_fields,
            issuedAtMs=intent.issued_at_ms,
            expiresAtMs=intent.expires_at_ms,
        ),
        timestamp=utc_now_iso(),
    )


@router.post("/uploads/complete", response_model=ApiEnvelope[MaterialUploadCompletionResponse])
async def complete_resume_upload(
    request_context: Request,
    request: CompleteUploadRequest,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: DocumentService = Depends(document_service),
) -> ApiEnvelope[MaterialUploadCompletionResponse]:
    user_id = resolve_owned_user_id(explicit_user_id=request.user_id, auth_context=auth_context)
    completed = service.complete_upload(
        user_id=user_id,
        intent_id=request.intent_id,
        object_key=request.object_key,
        content_type=request.content_type,
        size_bytes=request.size_bytes,
        etag=request.etag,
        content_sha256=request.content_sha256,
    )
    return success_response(
        request=request_context,
        data=MaterialUploadCompletionResponse(
            source={
                "sourceId": completed.document.document_id,
                "ownerUserId": completed.document.owner_user_id,
                "materialKind": completed.document.document_kind,
                "displayName": completed.document.display_name,
                "version": "v1",
                "processingState": "processing" if completed.document.status == "processing_requested" else completed.document.status,
                "updatedAtMs": completed.document.updated_at_ms,
                "summary": completed.document.summary,
            }
        ),
        timestamp=utc_now_iso(),
    )


@router.post("/uploads/proxy", response_model=ApiEnvelope[dict[str, int | str]])
async def proxy_resume_upload(
    request_context: Request,
    user_id: str = Form(alias="userId"),
    intent_id: str = Form(alias="intentId"),
    object_key: str = Form(alias="objectKey"),
    content_type: str = Form(alias="contentType"),
    file: UploadFile = File(),
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: DocumentService = Depends(document_service),
) -> ApiEnvelope[dict[str, int | str]]:
    owner_id = resolve_owned_user_id(explicit_user_id=user_id, auth_context=auth_context)
    return success_response(
        request=request_context,
        data=service.save_upload_bytes(
            user_id=owner_id,
            intent_id=intent_id,
            object_key=object_key,
            content_type=content_type,
            payload=await file.read(),
        ),
        timestamp=utc_now_iso(),
    )
