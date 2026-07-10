from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.material_formats import MaterialFormatId, MaterialKind


MaterialProcessingState = Literal["pending_upload", "uploaded", "processing", "ready", "failed", "deleted"]


class UploadIntentRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    user_id: str = Field(min_length=1, alias="userId")
    filename: str = Field(min_length=1)
    content_type: str = Field(min_length=1, alias="contentType")
    size_bytes: int = Field(ge=1, alias="sizeBytes")


class UploadIntentResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    intent_id: str = Field(alias="intentId")
    user_id: str = Field(alias="userId")
    material_kind: MaterialKind = Field(alias="materialKind")
    upload_method: Literal["POST"] = Field(alias="uploadMethod")
    filename: str
    file_kind: MaterialFormatId = Field(alias="fileKind")
    content_type: str = Field(alias="contentType")
    object_key: str = Field(alias="objectKey")
    upload_url: str = Field(alias="uploadUrl")
    upload_fields: dict[str, str] = Field(alias="uploadFields")
    issued_at_ms: int = Field(alias="issuedAtMs")
    expires_at_ms: int = Field(alias="expiresAtMs")


class CompleteUploadRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    user_id: str = Field(min_length=1, alias="userId")
    intent_id: str = Field(min_length=1, alias="intentId")
    object_key: str = Field(min_length=1, alias="objectKey")
    content_type: str = Field(min_length=1, alias="contentType")
    size_bytes: int = Field(ge=1, alias="sizeBytes")
    etag: str | None = None
    content_sha256: str | None = Field(default=None, alias="contentSha256")


class MaterialSourceRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    source_id: str = Field(alias="sourceId")
    owner_user_id: str = Field(alias="ownerUserId")
    material_kind: MaterialKind = Field(alias="materialKind")
    display_name: str = Field(alias="displayName")
    version: str
    processing_state: MaterialProcessingState = Field(alias="processingState")
    updated_at_ms: int = Field(alias="updatedAtMs")
    summary: str | None = None


class MaterialUploadCompletionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    source: MaterialSourceRecord
    document_version_id: str | None = Field(default=None, alias="documentVersionId")
    collection_id: str | None = Field(default=None, alias="collectionId")


class CreateKnowledgeCollectionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    user_id: str = Field(min_length=1, alias="userId")
    name: str = Field(min_length=1, max_length=120)


class CreatedKnowledgeCollectionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    collection_id: str = Field(alias="collectionId")
    owner_user_id: str = Field(alias="ownerUserId")
    name: str
    created_at_ms: int = Field(alias="createdAtMs")
    updated_at_ms: int = Field(alias="updatedAtMs")


class CreatePastedJobDescriptionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    user_id: str = Field(min_length=1, alias="userId")
    text: str = Field(min_length=1)
    display_name: str | None = Field(default=None, alias="displayName")
