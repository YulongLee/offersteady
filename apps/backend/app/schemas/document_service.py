from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.material_formats import MaterialFormatId, MaterialKind


DocumentLifecycleStatus = Literal[
    "pending_upload",
    "uploaded",
    "processing_requested",
    "processing",
    "ready",
    "failed",
    "deleting",
    "deleted",
]


class DocumentValidationPolicyResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    max_file_size_bytes: int = Field(alias="maxFileSizeBytes")
    accepted_extensions: list[str] = Field(alias="acceptedExtensions")
    accepted_mime_types: list[str] = Field(alias="acceptedMimeTypes")
    label: str


class CreateDocumentUploadIntentRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    user_id: str = Field(min_length=1, alias="userId")
    document_kind: MaterialKind = Field(alias="documentKind")
    filename: str = Field(min_length=1)
    content_type: str = Field(min_length=1, alias="contentType")
    size_bytes: int = Field(ge=1, alias="sizeBytes")
    knowledge_collection_id: str | None = Field(default=None, alias="knowledgeCollectionId")


class DocumentUploadIntentResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    intent_id: str = Field(alias="intentId")
    user_id: str = Field(alias="userId")
    document_kind: MaterialKind = Field(alias="documentKind")
    filename: str
    file_kind: MaterialFormatId = Field(alias="fileKind")
    content_type: str = Field(alias="contentType")
    object_key: str = Field(alias="objectKey")
    upload_method: Literal["POST"] = Field(alias="uploadMethod")
    upload_url: str = Field(alias="uploadUrl")
    upload_fields: dict[str, str] = Field(alias="uploadFields")
    issued_at_ms: int = Field(alias="issuedAtMs")
    expires_at_ms: int = Field(alias="expiresAtMs")


class CompleteDocumentUploadRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    user_id: str = Field(min_length=1, alias="userId")
    intent_id: str = Field(min_length=1, alias="intentId")
    object_key: str = Field(min_length=1, alias="objectKey")
    content_type: str = Field(min_length=1, alias="contentType")
    size_bytes: int = Field(ge=1, alias="sizeBytes")
    etag: str | None = None
    content_sha256: str | None = Field(default=None, alias="contentSha256")
    knowledge_collection_id: str | None = Field(default=None, alias="knowledgeCollectionId")


class DocumentRecordResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    document_id: str = Field(alias="documentId")
    owner_user_id: str = Field(alias="ownerUserId")
    document_kind: MaterialKind = Field(alias="documentKind")
    display_name: str = Field(alias="displayName")
    file_kind: MaterialFormatId = Field(alias="fileKind")
    content_type: str = Field(alias="contentType")
    size_bytes: int = Field(alias="sizeBytes")
    object_key: str = Field(alias="objectKey")
    status: DocumentLifecycleStatus
    knowledge_collection_id: str | None = Field(default=None, alias="knowledgeCollectionId")
    processing_requested_at_ms: int | None = Field(default=None, alias="processingRequestedAtMs")
    deleted_at_ms: int | None = Field(default=None, alias="deletedAtMs")
    created_at_ms: int = Field(alias="createdAtMs")
    updated_at_ms: int = Field(alias="updatedAtMs")
    summary: str | None = None
    object_id: str | None = Field(default=None, alias="objectId")
    document_version_id: str | None = Field(default=None, alias="documentVersionId")
    version: int | None = None
    content_fingerprint: str | None = Field(default=None, alias="contentFingerprint")
    original_filename: str | None = Field(default=None, alias="originalFilename")
    index_state: str | None = Field(default=None, alias="indexState")


class CompleteDocumentUploadResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    document: DocumentRecordResponse


class ListDocumentsRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    user_id: str = Field(min_length=1, alias="userId")
    document_kind: MaterialKind | None = Field(default=None, alias="documentKind")
    knowledge_collection_id: str | None = Field(default=None, alias="knowledgeCollectionId")
    include_deleted: bool = Field(default=False, alias="includeDeleted")


class DeleteDocumentRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    user_id: str = Field(min_length=1, alias="userId")


class DocumentProcessingHandoffResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    document_id: str = Field(alias="documentId")
    owner_user_id: str = Field(alias="ownerUserId")
    document_kind: MaterialKind = Field(alias="documentKind")
    object_key: str = Field(alias="objectKey")
    status: Literal["processing_requested", "processing", "ready", "failed"]
    requested_at_ms: int | None = Field(default=None, alias="requestedAtMs")
