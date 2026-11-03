from __future__ import annotations

import base64
import json
import logging
import time
from types import SimpleNamespace

import httpx
import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.ports.screenshot_answer import PreparedScreenshotImage, VisionSummary
from app.services.screenshot_answer_repository import InMemoryScreenshotAnswerRepository
from app.services.screenshot_answer_service import (
    InMemoryScreenshotUploadPort,
    NonRetryableVisionError,
    OpenAICompatibleVisionGateway,
    ScreenshotAnswerService,
    ScreenshotPreprocessor,
)


SYNTHETIC_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class RecordingStorage:
    def __init__(self) -> None:
        self.saved: dict[str, bytes] = {}

    def save_object_bytes(self, *, object_key: str, payload: bytes, content_type: str) -> None:
        _ = content_type
        self.saved[object_key] = payload

    def object_exists(self, *, object_key: str) -> bool:
        return object_key in self.saved

    def create_signed_download_url(self, *, object_key: str, expires_seconds: int) -> str:
        return f"https://synthetic.invalid/{object_key}?ttl={expires_seconds}"


class SessionStub:
    def __init__(self, interview_language: str = "zh-CN") -> None:
        self.session = SimpleNamespace(
            status="live",
            interview_language=interview_language,
            material_binding=SimpleNamespace(revision=3),
        )
        self.contexts: list[dict[str, object]] = []

    def get_session(self, *, user_id: str, session_id: str):
        _ = user_id, session_id
        return self.session

    def touch_activity(self, *, user_id: str, session_id: str, force: bool) -> None:
        _ = user_id, session_id, force

    def append_context(self, **kwargs) -> None:
        self.contexts.append(kwargs)

    def record_usage(self, **kwargs) -> None:
        _ = kwargs


class CapturingVisionGateway:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.images: list[PreparedScreenshotImage] = []

    def analyze(self, *, session_id: str, instruction: str, images: list[PreparedScreenshotImage], attempt: int) -> VisionSummary:
        _ = session_id, instruction, attempt
        self.images = images
        if self.fail:
            raise NonRetryableVisionError("synthetic_vision_failure")
        return VisionSummary(
            title="合成截图题",
            summary_text="合成截图内容",
            derived_question="请回答合成截图题",
            final_answer="简要回答\n合成答案。\n\n---\n\n详细回答\n合成详细答案。",
            image_count=len(images),
            provider_name="synthetic",
            model_name="synthetic-vision",
        )


class StreamingVisionGateway(CapturingVisionGateway):
    def stream_analyze(self, **kwargs):  # noqa: ANN003
        self.images = kwargs["images"]
        yield "简要回答\n先说明核心思路。"
        time.sleep(0.03)
        yield "\n\n---\n\n详细回答\n再给出完整实现。"

    def summary_from_stream(self, *, text: str, images: list[PreparedScreenshotImage]) -> VisionSummary:
        return VisionSummary(
            title="流式截图题", summary_text="流式截图内容", derived_question="请回答流式截图题",
            final_answer=text, image_count=len(images), provider_name="synthetic", model_name="streaming-vision",
        )


class UnsupportedStreamingVisionGateway(StreamingVisionGateway):
    def stream_analyze(self, **kwargs):  # noqa: ANN003
        _ = kwargs
        raise NonRetryableVisionError("provider_streaming_unsupported")
        yield ""  # pragma: no cover


def build_service(*, delivery_mode: str, fail_vision: bool = False, interview_language: str = "zh-CN"):
    settings = Settings(_env_file=None, screenshot_vision_delivery_mode=delivery_mode)
    storage = RecordingStorage()
    repository = InMemoryScreenshotAnswerRepository()
    upload_port = InMemoryScreenshotUploadPort(settings)
    vision = CapturingVisionGateway(fail=fail_vision)
    service = ScreenshotAnswerService(
        settings=settings,
        logger=logging.getLogger("test.screenshot-inline"),
        session_service=SessionStub(interview_language),  # type: ignore[arg-type]
        retrieval_service=SimpleNamespace(),  # type: ignore[arg-type]
        object_storage=storage,  # type: ignore[arg-type]
        repository=repository,
        upload_port=upload_port,
        preprocessor=ScreenshotPreprocessor(),
        vision_gateway=vision,
        prompt_template=SimpleNamespace(),  # type: ignore[arg-type]
        prompt_builder=SimpleNamespace(),  # type: ignore[arg-type]
        llm_gateway=SimpleNamespace(),  # type: ignore[arg-type]
    )
    return service, storage, repository, upload_port, vision


@pytest.mark.parametrize("recovery_failure", [None, "lookup", "save", "callback"])
def test_remote_capture_failure_logging_preserves_original_error(monkeypatch, caplog, recovery_failure):
    service, _, repository, _, _ = build_service(delivery_mode="inline")
    request = service.create_remote_capture_request(
        user_id="synthetic-user", session_id="synthetic-session", device_id="synthetic-device",
        manual_code="654321", instruction="Synthetic capture",
    )

    def fail_original(**kwargs):
        raise DomainRequestError("screenshot-answer", "save-object", "private-synthetic-error-body", 503,
                                 error_code="synthetic_storage_failure")

    def fail_recovery(*args, **kwargs):
        raise LookupError("private-synthetic-recovery-body")

    monkeypatch.setattr(service, "complete_remote_capture_request", fail_original)
    if recovery_failure == "lookup":
        monkeypatch.setattr(repository, "get_remote_capture_request", fail_recovery)
    elif recovery_failure == "save":
        monkeypatch.setattr(repository, "save_remote_capture_request", fail_recovery)
    caplog.set_level(logging.WARNING, logger=service.logger.name)
    service.complete_remote_capture_request_safely(
        request_id=request.request_id, device_id=request.device_id, manual_code=request.manual_code,
        filename="synthetic.png", content_type="image/png", payload=SYNTHETIC_PNG,
        on_transition=fail_recovery if recovery_failure == "callback" else None,
    )
    events = [json.loads(item.getMessage()) for item in caplog.records if item.name == service.logger.name]
    assert events[0]["event"] == "screenshot_answer.remote_background_error"
    assert events[0]["error_code"] == "synthetic_storage_failure"
    assert events[0]["image_count"] == 1
    if recovery_failure is not None:
        assert events[-1]["event"] == "screenshot_answer.remote_background_failed"
        assert events[-1]["error_code"] == "LookupError"
    else:
        failed = repository.get_remote_capture_request(request.request_id)
        assert failed.status == "failed"
        assert failed.stage == "upload-failed"
        assert failed.telemetry.failed_phase == "oss-write"
        assert failed.telemetry.error_code == "synthetic_storage_failure"
    assert "private-synthetic" not in caplog.text
    assert request.manual_code not in caplog.text
    assert "synthetic.png" not in caplog.text


def test_cancelled_capture_does_not_raise_secondary_logging_error(caplog):
    service, _, repository, _, _ = build_service(delivery_mode="inline")
    request = service.create_remote_capture_request(
        user_id="synthetic-user", session_id="synthetic-session", device_id="synthetic-device",
        manual_code="654321", instruction="Synthetic capture",
    )
    service.cancel_remote_capture_request(user_id=request.owner_user_id, request_id=request.request_id)
    caplog.set_level(logging.WARNING, logger=service.logger.name)
    service.complete_remote_capture_request_safely(
        request_id=request.request_id, device_id=request.device_id, manual_code=request.manual_code,
        filename="synthetic.png", content_type="image/png", payload=SYNTHETIC_PNG,
    )
    assert repository.get_remote_capture_request(request.request_id).status == "cancelled"
    events = [json.loads(item.getMessage()) for item in caplog.records if item.name == service.logger.name]
    assert [item["event"] for item in events] == [
        "screenshot_answer.remote_background_error", "screenshot_answer.remote_background_failed",
    ]


class EnglishVisionGateway(CapturingVisionGateway):
    def analyze(
        self, *, session_id: str, instruction: str, images: list[PreparedScreenshotImage],
        attempt: int, interview_language: str = "zh-CN",
    ) -> VisionSummary:
        _ = session_id, attempt
        self.images = images
        assert interview_language == "en-US"
        assert instruction == "Answer the screenshot question."
        return VisionSummary(
            title="Synthetic screenshot question",
            summary_text="Synthetic screenshot evidence",
            derived_question="Explain the algorithm shown in the screenshot.",
            final_answer="Use the visible constraints and explain the trade-offs.",
            image_count=len(images),
            provider_name="synthetic",
            model_name="synthetic-vision",
        )


class DriftingEnglishVisionGateway(EnglishVisionGateway):
    def __init__(self, *, always_chinese: bool = False) -> None:
        super().__init__()
        self.always_chinese = always_chinese
        self.instructions: list[str] = []

    def analyze(
        self, *, session_id: str, instruction: str, images: list[PreparedScreenshotImage],
        attempt: int, interview_language: str = "zh-CN",
    ) -> VisionSummary:
        _ = session_id, attempt
        self.instructions.append(instruction)
        repair = "ENGLISH-ONLY REPAIR" in instruction
        if repair and not self.always_chinese:
            return super().analyze(
                session_id=session_id,
                instruction="Answer the screenshot question.",
                images=images,
                attempt=attempt,
                interview_language=interview_language,
            )
        return VisionSummary(
            title="截图算法题",
            summary_text="截图中要求解释算法思路。",
            derived_question="请解释截图中的算法。",
            final_answer="简要回答\n先说明核心思路。\n\n---\n\n详细回答\n再解释边界和复杂度。",
            image_count=len(images),
            provider_name="synthetic",
            model_name="synthetic-vision",
        )


def upload_synthetic_image(service: ScreenshotAnswerService, telemetry: dict[str, object]):
    return service.upload_bytes(
        user_id="user-inline",
        session_id="session-inline",
        filename="synthetic.png",
        content_type="image/png",
        payload=SYNTHETIC_PNG,
        telemetry=telemetry,
    )


def test_inline_mode_skips_oss_and_releases_transient_bytes_after_success() -> None:
    service, storage, repository, upload_port, vision = build_service(delivery_mode="inline")
    telemetry: dict[str, object] = {}
    upload = upload_synthetic_image(service, telemetry)

    assert storage.saved == {}
    assert telemetry["delivery_mode"] == "inline"
    assert telemetry["oss_write_ms"] == 0.0
    assert upload_port.load_image_bytes(image=upload)

    task, _ = service.answer_screenshots(
        user_id="user-inline",
        session_id="session-inline",
        image_ids=[upload.image_id],
        instruction="只回答截图",
        stream=True,
        telemetry=telemetry,
    )

    assert task.status == "completed"
    assert vision.images[0].public_url is None
    assert repository.get_upload(upload.image_id).status == "deleted"  # type: ignore[union-attr]
    with pytest.raises(DomainRequestError):
        upload_port.load_image_bytes(image=upload)
    assert "base64" not in str(task.telemetry)


def test_english_screenshot_answer_stays_in_english_and_records_language_route() -> None:
    service, _storage, _repository, _upload_port, _vision = build_service(
        delivery_mode="inline", interview_language="en-US"
    )
    service.vision_gateway = EnglishVisionGateway()
    upload = upload_synthetic_image(service, {})

    task, _ = service.answer_screenshots(
        user_id="user-inline",
        session_id="session-inline",
        image_ids=[upload.image_id],
        instruction="Answer the screenshot question.",
        stream=False,
    )

    assert task.prompt_template_id == "screenshot-vision-direct-en"
    assert task.answer_text.startswith("Quick Answer")
    assert "Detailed Answer" in task.answer_text
    assert task.material_provenance["interviewLanguage"] == "en-US"
    assert "简要回答" not in task.answer_text


def test_english_screenshot_repairs_chinese_provider_output() -> None:
    service, _storage, _repository, _upload_port, _vision = build_service(
        delivery_mode="inline", interview_language="en-US"
    )
    gateway = DriftingEnglishVisionGateway()
    service.vision_gateway = gateway
    upload = upload_synthetic_image(service, {})

    task, _ = service.answer_screenshots(
        user_id="user-inline",
        session_id="session-inline",
        image_ids=[upload.image_id],
        instruction="Answer the screenshot question.",
        stream=False,
    )

    assert task.status == "completed"
    assert "Quick Answer" in task.answer_text
    assert "简要回答" not in task.answer_text
    assert any("ENGLISH-ONLY REPAIR" in item for item in gateway.instructions)


def test_english_screenshot_repeated_chinese_output_fails_closed() -> None:
    service, _storage, _repository, _upload_port, _vision = build_service(
        delivery_mode="inline", interview_language="en-US"
    )
    service.vision_gateway = DriftingEnglishVisionGateway(always_chinese=True)
    upload = upload_synthetic_image(service, {})

    task, _ = service.answer_screenshots(
        user_id="user-inline",
        session_id="session-inline",
        image_ids=[upload.image_id],
        instruction="Answer the screenshot question.",
        stream=False,
    )

    assert task.status == "failed"
    assert task.error_code == "screenshot_output_language_violation"
    assert task.answer_text == ""


def test_inline_mode_releases_transient_bytes_when_vision_fails() -> None:
    service, storage, repository, upload_port, _vision = build_service(delivery_mode="inline", fail_vision=True)
    upload = upload_synthetic_image(service, {})

    task, _ = service.answer_screenshots(
        user_id="user-inline",
        session_id="session-inline",
        image_ids=[upload.image_id],
        instruction="只回答截图",
        stream=True,
    )

    assert task.status == "failed"
    assert storage.saved == {}
    assert repository.get_upload(upload.image_id).status == "deleted"  # type: ignore[union-attr]
    with pytest.raises(DomainRequestError):
        upload_port.load_image_bytes(image=upload)


def test_oss_mode_preserves_signed_url_compatibility_and_releases_memory_copy() -> None:
    service, storage, repository, upload_port, vision = build_service(delivery_mode="oss")
    telemetry: dict[str, object] = {}
    upload = upload_synthetic_image(service, telemetry)

    assert storage.saved[upload.object_key]
    assert telemetry["delivery_mode"] == "oss"

    task, _ = service.answer_screenshots(
        user_id="user-inline",
        session_id="session-inline",
        image_ids=[upload.image_id],
        instruction="只回答截图",
        stream=True,
        telemetry=telemetry,
    )

    assert task.status == "completed"
    assert vision.images[0].public_url.startswith("https://synthetic.invalid/")  # type: ignore[union-attr]
    assert repository.get_upload(upload.image_id).status == "deleted"  # type: ignore[union-attr]
    with pytest.raises(DomainRequestError):
        upload_port.load_image_bytes(image=upload)


def test_vision_gateway_embeds_payload_as_data_url_without_logging_content(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_post(_client, url: str, *, headers: dict[str, str], json: dict[str, object]):
        _ = url, headers
        captured.update(json)
        return httpx.Response(200, json={"choices": [{"message": {"content": "简要回答\n答案。\n\n---\n\n详细回答\n详细答案。"}}]})

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    gateway = OpenAICompatibleVisionGateway(Settings(
        _env_file=None,
        screenshot_vision_base_url="https://vision.synthetic.invalid/v1",
        screenshot_vision_api_key="synthetic-secret",
    ))
    image = PreparedScreenshotImage(
        image_id="image-inline",
        session_id="session-inline",
        owner_user_id="user-inline",
        filename="synthetic.png",
        content_type="image/png",
        object_key="screenshots/synthetic.png",
        size_bytes=len(SYNTHETIC_PNG),
        ordinal=1,
        content_sha256="synthetic-sha",
        byte_length=len(SYNTHETIC_PNG),
        payload_bytes=SYNTHETIC_PNG,
        public_url=None,
    )

    result = gateway.analyze(session_id="session-inline", instruction="只回答截图", images=[image], attempt=0)

    content = captured["messages"][1]["content"]  # type: ignore[index]
    image_url = content[1]["image_url"]["url"]  # type: ignore[index]
    assert captured["enable_thinking"] is False
    assert image_url.startswith("data:image/png;base64,")
    assert base64.b64decode(image_url.split(",", 1)[1]) == SYNTHETIC_PNG
    assert result.final_answer.startswith("简要回答")  # type: ignore[union-attr]


def test_vision_gateway_thinking_mode_is_explicit_and_screenshot_scoped() -> None:
    disabled = OpenAICompatibleVisionGateway(Settings(_env_file=None))
    enabled = OpenAICompatibleVisionGateway(Settings(
        _env_file=None,
        screenshot_vision_enable_thinking=True,
    ))

    disabled_payload = disabled._request_payload(instruction="合成题", images=[], stream=True)
    enabled_payload = enabled._request_payload(instruction="合成题", images=[], stream=True)

    assert disabled_payload["enable_thinking"] is False
    assert enabled_payload["enable_thinking"] is True


def test_invalid_screenshot_delivery_mode_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, screenshot_vision_delivery_mode="unsupported")


def test_streaming_screenshot_publishes_partial_before_terminal_completion() -> None:
    service, _storage, _repository, _upload_port, _vision = build_service(delivery_mode="inline")
    service.settings.screenshot_progress_emit_interval_ms = 20
    service.vision_gateway = StreamingVisionGateway()
    recorded_usage = []
    service.commercial_repository = SimpleNamespace(
        record_ai_usage=lambda usage: recorded_usage.append(usage) or usage,
    )
    upload = upload_synthetic_image(service, {})
    updates = []
    telemetry: dict[str, object] = {}

    task, _ = service.answer_screenshots(
        user_id="user-inline", session_id="session-inline", image_ids=[upload.image_id],
        instruction="只回答截图", stream=True, on_task_update=updates.append, telemetry=telemetry,
    )

    partials = [item for item in updates if item.status == "streaming" and item.answer_text]
    assert partials
    assert partials[0].answer_text.startswith("简要回答")
    assert task.status == "completed"
    assert task.answer_text.endswith("再给出完整实现。")
    assert task.telemetry.first_text_ms is not None
    assert len(recorded_usage) == 1
    assert recorded_usage[0].first_token_ms == max(0, round(task.telemetry.first_text_ms))


def test_streaming_screenshot_falls_back_to_complete_response_before_any_chunk() -> None:
    service, _storage, _repository, _upload_port, _vision = build_service(delivery_mode="inline")
    service.vision_gateway = UnsupportedStreamingVisionGateway()
    upload = upload_synthetic_image(service, {})

    task, _ = service.answer_screenshots(
        user_id="user-inline", session_id="session-inline", image_ids=[upload.image_id],
        instruction="只回答截图", stream=True,
    )

    assert task.status == "completed"
    assert "合成详细答案" in task.answer_text
