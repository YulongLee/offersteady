from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

from app.ports.chat import ChatAnswerChunk, PromptBuildResult


ScreenshotAnswerTaskStatus = Literal["queued", "processing-images", "vision-running", "streaming", "completed", "failed", "cancelled"]
ScreenshotUploadStatus = Literal["pending_upload", "uploaded", "deleted"]
RemoteCaptureRequestStatus = Literal["requested", "processing", "completed", "failed", "cancelled"]
RemoteCaptureRequestStage = Literal["requested", "claimed", "capture-failed", "upload-failed", "uploaded", "vision-running", "completed", "failed", "cancelled"]


@dataclass(frozen=True)
class ScreenshotTimingTelemetry:
    upload_accepted_ms: float | None = None
    image_optimize_ms: float | None = None
    oss_write_ms: float | None = None
    signed_url_ms: float | None = None
    vision_model_ms: float | None = None
    answer_persist_ms: float | None = None
    total_background_ms: float | None = None
    failed_phase: str | None = None
    error_code: str | None = None
    original_width: int | None = None
    original_height: int | None = None
    compressed_width: int | None = None
    compressed_height: int | None = None
    original_bytes: int | None = None
    compressed_bytes: int | None = None
    content_type: str | None = None


@dataclass(frozen=True)
class ScreenshotUploadIntent:
    intent_id: str
    session_id: str
    user_id: str
    filename: str
    content_type: str
    object_key: str
    upload_url: str
    upload_fields: dict[str, str]
    issued_at_ms: int
    expires_at_ms: int
    upload_method: Literal["POST"] = "POST"


@dataclass(frozen=True)
class ConfirmedScreenshotUpload:
    image_id: str
    session_id: str
    owner_user_id: str
    filename: str
    content_type: str
    object_key: str
    size_bytes: int
    status: ScreenshotUploadStatus
    uploaded_at_ms: int
    etag: str | None = None
    deleted_at_ms: int | None = None


@dataclass(frozen=True)
class PreparedScreenshotImage:
    image_id: str
    session_id: str
    owner_user_id: str
    filename: str
    content_type: str
    object_key: str
    size_bytes: int
    ordinal: int
    content_sha256: str
    byte_length: int
    payload_bytes: bytes
    public_url: str | None = None


@dataclass(frozen=True)
class VisionUsageReport:
    visual_tokens: int
    total_tokens: int
    provider_name: str
    model_name: str


@dataclass(frozen=True)
class VisionSummary:
    title: str
    summary_text: str
    derived_question: str
    image_count: int
    ordered_image_names: list[str] = field(default_factory=list)
    final_answer: str | None = None
    usage: VisionUsageReport | None = None
    provider_name: str | None = None
    model_name: str | None = None


@dataclass(frozen=True)
class ScreenshotAnswerTaskRecord:
    task_id: str
    session_id: str
    owner_user_id: str
    instruction: str
    answer_text: str
    status: ScreenshotAnswerTaskStatus
    stream_mode: bool
    image_ids: list[str] = field(default_factory=list)
    image_count: int = 0
    provider_name: str | None = None
    model_name: str | None = None
    vision_provider_name: str | None = None
    vision_model_name: str | None = None
    prompt_template_id: str | None = None
    prompt_version: str | None = None
    retrieval_excerpt_count: int = 0
    material_context_status: str = "not-assembled"
    fixed_source_count: int = 0
    retrieved_source_count: int = 0
    material_provenance: dict[str, object] = field(default_factory=dict)
    unavailable_material_sources: list[dict[str, object]] = field(default_factory=list)
    retry_count: int = 0
    error_code: str | None = None
    error_message: str | None = None
    created_at_ms: int = 0
    updated_at_ms: int = 0
    completed_at_ms: int | None = None
    chunks: list[ChatAnswerChunk] = field(default_factory=list)
    vision_summary_title: str | None = None
    telemetry: ScreenshotTimingTelemetry = field(default_factory=ScreenshotTimingTelemetry)


@dataclass(frozen=True)
class RemoteScreenshotCaptureRequest:
    request_id: str
    session_id: str
    owner_user_id: str
    device_id: str
    manual_code: str
    instruction: str
    status: RemoteCaptureRequestStatus
    created_at_ms: int
    updated_at_ms: int
    stage: RemoteCaptureRequestStage = "requested"
    answer_task_id: str | None = None
    error_message: str | None = None
    captured_filename: str | None = None
    claimed_at_ms: int | None = None
    completed_at_ms: int | None = None
    telemetry: ScreenshotTimingTelemetry = field(default_factory=ScreenshotTimingTelemetry)


class ScreenshotUploadPort(Protocol):
    def create_upload_intent(
        self,
        *,
        user_id: str,
        session_id: str,
        filename: str,
        content_type: str,
    ) -> ScreenshotUploadIntent: ...

    def confirm_uploaded_image(
        self,
        *,
        user_id: str,
        session_id: str,
        intent_id: str,
        object_key: str,
        content_type: str,
        size_bytes: int,
        etag: str | None = None,
    ) -> ConfirmedScreenshotUpload: ...

    def store_uploaded_image_bytes(
        self,
        *,
        intent_id: str,
        payload: bytes,
    ) -> None: ...

    def load_image_bytes(self, *, image: ConfirmedScreenshotUpload) -> bytes: ...


class VisionGatewayPort(Protocol):
    def analyze(
        self,
        *,
        session_id: str,
        instruction: str,
        images: list[PreparedScreenshotImage],
        attempt: int,
    ) -> VisionSummary: ...


class ScreenshotPromptTemplatePort(Protocol):
    def load_system_prompt(self) -> tuple[str, object]: ...


class ScreenshotPromptBuilderPort(Protocol):
    def build(
        self,
        *,
        instruction: str,
        session_title: str,
        system_prompt: str,
        conversation_history: list[str],
        session_material_context_text: str,
        retrieval_context_text: str,
        vision_summary: VisionSummary,
        prompt_config: object,
    ) -> PromptBuildResult: ...


class ScreenshotAnswerRepository(Protocol):
    def save_task(self, task: ScreenshotAnswerTaskRecord) -> ScreenshotAnswerTaskRecord: ...

    def get_task(self, task_id: str) -> ScreenshotAnswerTaskRecord | None: ...

    def list_tasks_for_session(self, *, session_id: str) -> list[ScreenshotAnswerTaskRecord]: ...

    def save_upload(self, upload: ConfirmedScreenshotUpload) -> ConfirmedScreenshotUpload: ...

    def get_upload(self, image_id: str) -> ConfirmedScreenshotUpload | None: ...

    def list_uploads_for_session(self, *, session_id: str) -> list[ConfirmedScreenshotUpload]: ...

    def save_remote_capture_request(self, request: RemoteScreenshotCaptureRequest) -> RemoteScreenshotCaptureRequest: ...

    def get_remote_capture_request(self, request_id: str) -> RemoteScreenshotCaptureRequest | None: ...

    def get_next_pending_remote_capture_request(self, *, device_id: str, manual_code: str) -> RemoteScreenshotCaptureRequest | None: ...
