from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.ports.screenshot_answer import ScreenshotAnswerTaskStatus, ScreenshotUploadStatus
from app.schemas.retrieval import RetrievalResponse


class ScreenshotValidationPolicyResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    max_file_size_bytes: int = Field(alias="maxFileSizeBytes")
    accepted_extensions: list[str] = Field(alias="acceptedExtensions")
    accepted_mime_types: list[str] = Field(alias="acceptedMimeTypes")
    max_images_per_task: int = Field(alias="maxImagesPerTask")


class CreateScreenshotUploadIntentRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    user_id: str = Field(min_length=1, alias="userId")
    session_id: str = Field(min_length=1, alias="sessionId")
    filename: str = Field(min_length=1)
    content_type: str = Field(min_length=1, alias="contentType")
    size_bytes: int = Field(ge=1, alias="sizeBytes")


class ScreenshotUploadIntentResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    intent_id: str = Field(alias="intentId")
    session_id: str = Field(alias="sessionId")
    user_id: str = Field(alias="userId")
    filename: str
    content_type: str = Field(alias="contentType")
    object_key: str = Field(alias="objectKey")
    upload_method: Literal["POST"] = Field(alias="uploadMethod")
    upload_url: str = Field(alias="uploadUrl")
    upload_fields: dict[str, str] = Field(alias="uploadFields")
    issued_at_ms: int = Field(alias="issuedAtMs")
    expires_at_ms: int = Field(alias="expiresAtMs")


class CompleteScreenshotUploadRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    user_id: str = Field(min_length=1, alias="userId")
    session_id: str = Field(min_length=1, alias="sessionId")
    intent_id: str = Field(min_length=1, alias="intentId")
    object_key: str = Field(min_length=1, alias="objectKey")
    content_type: str = Field(min_length=1, alias="contentType")
    size_bytes: int = Field(ge=1, alias="sizeBytes")
    etag: str | None = None


class ScreenshotUploadResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    image_id: str = Field(alias="imageId")
    session_id: str = Field(alias="sessionId")
    owner_user_id: str = Field(alias="ownerUserId")
    filename: str
    content_type: str = Field(alias="contentType")
    object_key: str = Field(alias="objectKey")
    size_bytes: int = Field(alias="sizeBytes")
    status: ScreenshotUploadStatus
    uploaded_at_ms: int = Field(alias="uploadedAtMs")
    etag: str | None = None
    deleted_at_ms: int | None = Field(default=None, alias="deletedAtMs")


class StartScreenshotAnswerRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    user_id: str = Field(min_length=1, alias="userId")
    session_id: str = Field(min_length=1, alias="sessionId")
    image_ids: list[str] = Field(min_length=1, alias="imageIds")
    instruction: str = ""
    stream: bool = True


class ScreenshotAnswerChunkResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    sequence: int
    text: str
    is_final: bool = Field(alias="isFinal")


class ScreenshotTimingTelemetryResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    upload_accepted_ms: float | None = Field(default=None, alias="uploadAcceptedMs")
    image_optimize_ms: float | None = Field(default=None, alias="imageOptimizeMs")
    oss_write_ms: float | None = Field(default=None, alias="ossWriteMs")
    signed_url_ms: float | None = Field(default=None, alias="signedUrlMs")
    vision_model_ms: float | None = Field(default=None, alias="visionModelMs")
    answer_persist_ms: float | None = Field(default=None, alias="answerPersistMs")
    total_background_ms: float | None = Field(default=None, alias="totalBackgroundMs")
    failed_phase: str | None = Field(default=None, alias="failedPhase")
    error_code: str | None = Field(default=None, alias="errorCode")
    original_width: int | None = Field(default=None, alias="originalWidth")
    original_height: int | None = Field(default=None, alias="originalHeight")
    compressed_width: int | None = Field(default=None, alias="compressedWidth")
    compressed_height: int | None = Field(default=None, alias="compressedHeight")
    original_bytes: int | None = Field(default=None, alias="originalBytes")
    compressed_bytes: int | None = Field(default=None, alias="compressedBytes")
    content_type: str | None = Field(default=None, alias="contentType")


class ScreenshotAnswerTaskResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    task_id: str = Field(alias="taskId")
    session_id: str = Field(alias="sessionId")
    owner_user_id: str = Field(alias="ownerUserId")
    instruction: str
    answer_text: str = Field(alias="answerText")
    status: ScreenshotAnswerTaskStatus
    stream_mode: bool = Field(alias="streamMode")
    image_ids: list[str] = Field(alias="imageIds")
    image_count: int = Field(alias="imageCount")
    provider_name: str | None = Field(default=None, alias="providerName")
    model_name: str | None = Field(default=None, alias="modelName")
    vision_provider_name: str | None = Field(default=None, alias="visionProviderName")
    vision_model_name: str | None = Field(default=None, alias="visionModelName")
    prompt_template_id: str | None = Field(default=None, alias="promptTemplateId")
    prompt_version: str | None = Field(default=None, alias="promptVersion")
    retrieval_excerpt_count: int = Field(alias="retrievalExcerptCount")
    material_context_status: str = Field(default="not-assembled", alias="materialContextStatus")
    fixed_source_count: int = Field(default=0, alias="fixedSourceCount")
    retrieved_source_count: int = Field(default=0, alias="retrievedSourceCount")
    material_provenance: dict[str, object] = Field(default_factory=dict, alias="materialProvenance")
    unavailable_material_sources: list[dict[str, object]] = Field(default_factory=list, alias="unavailableMaterialSources")
    retry_count: int = Field(alias="retryCount")
    error_code: str | None = Field(default=None, alias="errorCode")
    error_message: str | None = Field(default=None, alias="errorMessage")
    created_at_ms: int = Field(alias="createdAtMs")
    updated_at_ms: int = Field(alias="updatedAtMs")
    completed_at_ms: int | None = Field(default=None, alias="completedAtMs")
    vision_summary_title: str | None = Field(default=None, alias="visionSummaryTitle")
    telemetry: ScreenshotTimingTelemetryResponse | None = None
    chunks: list[ScreenshotAnswerChunkResponse] = Field(default_factory=list)


class ScreenshotAnswerResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    task: ScreenshotAnswerTaskResponse
    retrieval: RetrievalResponse


class CreateRemoteScreenshotCaptureRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    user_id: str = Field(min_length=1, alias="userId")
    instruction: str = ""


class RemoteScreenshotCaptureRequestResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    request_id: str = Field(alias="requestId")
    session_id: str = Field(alias="sessionId")
    owner_user_id: str = Field(alias="ownerUserId")
    device_id: str = Field(alias="deviceId")
    manual_code: str = Field(alias="manualCode")
    instruction: str
    status: str
    stage: str = "requested"
    created_at_ms: int = Field(alias="createdAtMs")
    updated_at_ms: int = Field(alias="updatedAtMs")
    answer_task_id: str | None = Field(default=None, alias="answerTaskId")
    error_message: str | None = Field(default=None, alias="errorMessage")
    captured_filename: str | None = Field(default=None, alias="capturedFilename")
    claimed_at_ms: int | None = Field(default=None, alias="claimedAtMs")
    completed_at_ms: int | None = Field(default=None, alias="completedAtMs")
    telemetry: ScreenshotTimingTelemetryResponse | None = None
    answer_task: ScreenshotAnswerTaskResponse | None = Field(default=None, alias="answerTask")


class FailRemoteScreenshotCaptureRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    device_id: str = Field(min_length=1, alias="deviceId")
    manual_code: str = Field(min_length=6, max_length=6, alias="manualCode")
    message: str = Field(min_length=1)
    stage: str = "capture-failed"


class CancelRemoteScreenshotCaptureRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    user_id: str = Field(min_length=1, alias="userId")
