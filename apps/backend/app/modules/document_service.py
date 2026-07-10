from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from app.core.logging import utc_now_iso
from app.core.responses import success_response
from app.deps import document_service, optional_authenticated_context, resolve_owned_user_id
from app.ports.authentication import AuthenticatedRequestContext
from app.schemas.document_service import (
    CompleteDocumentUploadRequest,
    CompleteDocumentUploadResponse,
    CreateDocumentUploadIntentRequest,
    DeleteDocumentRequest,
    DocumentProcessingHandoffResponse,
    DocumentRecordResponse,
    DocumentUploadIntentResponse,
    DocumentValidationPolicyResponse,
    ListDocumentsRequest,
)
from app.schemas.foundation import ApiEnvelope, ModuleDescriptor
from app.services.document_service import DocumentService


router = APIRouter(prefix="/documents", tags=["document-service"])
descriptor = ModuleDescriptor(
    feature="document-service",
    owningApp="apps/backend",
    routePrefix="/api/v1/documents",
    mode="active",
    notes="Unified document lifecycle service for resume, JD, and knowledge files.",
)


@router.get("/validation-policy", response_model=ApiEnvelope[DocumentValidationPolicyResponse])
async def validation_policy(request: Request, service: DocumentService = Depends(document_service)) -> ApiEnvelope[DocumentValidationPolicyResponse]:
    return success_response(request=request, data=service.validation_policy(), timestamp=utc_now_iso())


@router.post("/upload-intents", response_model=ApiEnvelope[DocumentUploadIntentResponse])
async def create_upload_intent(
    request_context: Request,
    request: CreateDocumentUploadIntentRequest,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: DocumentService = Depends(document_service),
) -> ApiEnvelope[DocumentUploadIntentResponse]:
    user_id = resolve_owned_user_id(explicit_user_id=request.user_id, auth_context=auth_context)
    return success_response(
        request=request_context,
        data=service.create_upload_intent(
            user_id=user_id,
            document_kind=request.document_kind,
            filename=request.filename,
            content_type=request.content_type,
            size_bytes=request.size_bytes,
            knowledge_collection_id=request.knowledge_collection_id,
        ),
        timestamp=utc_now_iso(),
    )


@router.post("/uploads/complete", response_model=ApiEnvelope[CompleteDocumentUploadResponse])
async def complete_upload(
    request_context: Request,
    request: CompleteDocumentUploadRequest,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: DocumentService = Depends(document_service),
) -> ApiEnvelope[CompleteDocumentUploadResponse]:
    user_id = resolve_owned_user_id(explicit_user_id=request.user_id, auth_context=auth_context)
    return success_response(
        request=request_context,
        data=service.complete_upload(
            user_id=user_id,
            intent_id=request.intent_id,
            object_key=request.object_key,
            content_type=request.content_type,
            size_bytes=request.size_bytes,
            etag=request.etag,
            content_sha256=request.content_sha256,
            knowledge_collection_id=request.knowledge_collection_id,
        ),
        timestamp=utc_now_iso(),
    )


@router.get("", response_model=ApiEnvelope[list[DocumentRecordResponse]])
async def list_documents(
    request: Request,
    user_id: str | None = Query(default=None, alias="userId"),
    document_kind: str | None = Query(default=None, alias="documentKind"),
    knowledge_collection_id: str | None = Query(default=None, alias="knowledgeCollectionId"),
    include_deleted: bool = Query(default=False, alias="includeDeleted"),
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: DocumentService = Depends(document_service),
) -> ApiEnvelope[list[DocumentRecordResponse]]:
    resolved_user_id = resolve_owned_user_id(explicit_user_id=user_id, auth_context=auth_context)
    _ = ListDocumentsRequest(
        userId=resolved_user_id,
        documentKind=document_kind,
        knowledgeCollectionId=knowledge_collection_id,
        includeDeleted=include_deleted,
    )
    return success_response(
        request=request,
        data=service.list_documents(
            user_id=resolved_user_id,
            document_kind=document_kind,  # type: ignore[arg-type]
            knowledge_collection_id=knowledge_collection_id,
            include_deleted=include_deleted,
        ),
        timestamp=utc_now_iso(),
    )


@router.get("/{document_id}", response_model=ApiEnvelope[DocumentRecordResponse])
async def get_document(
    document_id: str,
    request: Request,
    user_id: str | None = Query(default=None, alias="userId"),
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: DocumentService = Depends(document_service),
) -> ApiEnvelope[DocumentRecordResponse]:
    resolved_user_id = resolve_owned_user_id(explicit_user_id=user_id, auth_context=auth_context)
    return success_response(request=request, data=service.get_document(user_id=resolved_user_id, document_id=document_id), timestamp=utc_now_iso())


@router.delete("/{document_id}", response_model=ApiEnvelope[DocumentRecordResponse])
async def delete_document(
    document_id: str,
    request_context: Request,
    request: DeleteDocumentRequest = Depends(),
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: DocumentService = Depends(document_service),
) -> ApiEnvelope[DocumentRecordResponse]:
    user_id = resolve_owned_user_id(explicit_user_id=request.user_id, auth_context=auth_context)
    return success_response(
        request=request_context,
        data=service.delete_document(user_id=user_id, document_id=document_id),
        timestamp=utc_now_iso(),
    )


@router.get("/processing/handoffs", response_model=ApiEnvelope[list[DocumentProcessingHandoffResponse]])
async def list_processing_handoffs(
    request: Request,
    user_id: str | None = Query(default=None, alias="userId"),
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: DocumentService = Depends(document_service),
) -> ApiEnvelope[list[DocumentProcessingHandoffResponse]]:
    resolved_user_id = resolve_owned_user_id(explicit_user_id=user_id, auth_context=auth_context) if (user_id or auth_context) else None
    return success_response(request=request, data=service.list_processing_handoffs(user_id=resolved_user_id), timestamp=utc_now_iso())
