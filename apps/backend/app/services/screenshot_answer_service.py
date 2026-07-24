from __future__ import annotations

import hashlib
import base64
import io
import json
import logging
import re
from json import JSONDecodeError
from dataclasses import replace
from pathlib import Path
from time import perf_counter, time
from uuid import uuid4

import httpx

from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.core.logging import log_event
from app.ports.chat import (
    ChatAnswerChunk,
    ChatAnswerTaskRecord,
    LLMGatewayPort,
    MaterialContextAssembly,
    MaterialContextSource,
    PromptBuildResult,
    PromptBuilderPort,
    PromptConfig,
    UsageReport,
)
from app.ports.retrieval import RetrievalContext, RetrievalFilter, RetrievalPort
from app.ports.storage import FileStoragePort
from app.ports.screenshot_answer import (
    ConfirmedScreenshotUpload,
    PreparedScreenshotImage,
    RemoteScreenshotCaptureRequest,
    ScreenshotAnswerRepository,
    ScreenshotAnswerTaskRecord,
    ScreenshotTimingTelemetry,
    ScreenshotPromptBuilderPort,
    ScreenshotPromptTemplatePort,
    ScreenshotUploadIntent,
    ScreenshotUploadPort,
    VisionGatewayPort,
    VisionSummary,
    VisionUsageReport,
)
from app.schemas.retrieval import RetrievalResponse, RetrievedChunkResponse
from app.services.chat_service import NonRetryableChatError, RetryableChatError
from app.services.material_object_keys import MaterialObjectKeyFactory
from app.services.session_service import SessionService


def _now_ms() -> int:
    return int(time() * 1000)


def _elapsed_ms(start: float) -> float:
    return round((perf_counter() - start) * 1000, 2)


class RetryableVisionError(Exception):
    pass


class NonRetryableVisionError(Exception):
    pass


class FileScreenshotPromptTemplateAdapter(ScreenshotPromptTemplatePort):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def load_system_prompt(self) -> tuple[str, PromptConfig]:
        prompt_path = Path(self.settings.screenshot_prompt_template_path)
        if not prompt_path.is_absolute():
            prompt_path = Path(__file__).resolve().parents[4] / self.settings.screenshot_prompt_template_path
        text = prompt_path.read_text(encoding="utf-8").strip()
        return text, PromptConfig(
            template_id="screenshot-answer-system",
            version=self.settings.screenshot_prompt_version,
            max_history_entries=self.settings.screenshot_max_history_entries,
            include_retrieval_context=False,
        )


class ScreenshotPromptBuilder(ScreenshotPromptBuilderPort):
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
    ) -> PromptBuildResult:
        typed_prompt_config = prompt_config if isinstance(prompt_config, PromptConfig) else PromptConfig(
            template_id="screenshot-answer-system",
            version="v1",
            max_history_entries=4,
        )
        history_text = "\n".join(conversation_history[-typed_prompt_config.max_history_entries :])
        sections = [
            "<authoritative_screenshot_request>",
            f"会话标题：{session_title}\n截图摘要：{vision_summary.title}",
            "</authoritative_screenshot_request>",
            f"<untrusted_screenshot_evidence>\n{vision_summary.summary_text}\n</untrusted_screenshot_evidence>",
        ]
        if instruction.strip():
            sections.append(f"<user_instruction>{instruction.strip()}</user_instruction>")
        if history_text:
            sections.append(f"<untrusted_screenshot_conversation>\n{history_text}\n</untrusted_screenshot_conversation>")
        _ = session_material_context_text, retrieval_context_text
        user_prompt = "\n\n".join(sections)
        return PromptBuildResult(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            rendered_prompt=f"{system_prompt}\n\n{user_prompt}",
            prompt_config=typed_prompt_config,
            retrieval_excerpt_count=retrieval_context_text.count("["),
        )


class InMemoryScreenshotUploadPort(ScreenshotUploadPort):
    allowed_extensions = (".png", ".jpg", ".jpeg", ".webp")
    allowed_mime_types = ("image/png", "image/jpeg", "image/webp")

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.issued_intents: dict[str, ScreenshotUploadIntent] = {}
        self.uploaded_images: dict[str, bytes] = {}
        self.pending_upload_payloads: dict[str, bytes] = {}

    def create_upload_intent(
        self,
        *,
        user_id: str,
        session_id: str,
        filename: str,
        content_type: str,
    ) -> ScreenshotUploadIntent:
        issued_at_ms = _now_ms()
        expires_at_ms = issued_at_ms + self.settings.oss_upload_intent_ttl_seconds * 1000
        object_key = f"screenshots/{user_id}/{session_id}/{uuid4().hex}/{self._sanitize_filename(filename)}"
        reservation = ScreenshotUploadIntent(
            intent_id=f"shot-intent-{uuid4().hex}",
            session_id=session_id,
            user_id=user_id,
            filename=filename,
            content_type=content_type,
            object_key=object_key,
            upload_url=f"{self.settings.public_web_base_url.rstrip('/')}/mock-upload/screenshot",
            upload_fields={"key": object_key, "Content-Type": content_type},
            issued_at_ms=issued_at_ms,
            expires_at_ms=expires_at_ms,
        )
        self.issued_intents[reservation.intent_id] = reservation
        return reservation

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
    ) -> ConfirmedScreenshotUpload:
        reservation = self.issued_intents.get(intent_id)
        if reservation is None:
            raise DomainRequestError("screenshot-answer", "confirm-upload", "截图上传意图不存在或已失效。", 404)
        now_ms = _now_ms()
        if reservation.user_id != user_id or reservation.session_id != session_id or reservation.object_key != object_key:
            raise DomainRequestError("screenshot-answer", "confirm-upload", "截图上传对象与当前会话或用户不匹配。", 409)
        if now_ms > reservation.expires_at_ms:
            raise DomainRequestError("screenshot-answer", "confirm-upload", "截图上传意图已过期，请重新上传。", 410)
        if reservation.content_type != content_type:
            raise DomainRequestError("screenshot-answer", "confirm-upload", "截图内容类型与上传意图不一致。", 409)
        payload = self.pending_upload_payloads.get(intent_id)
        if payload is None:
            payload = self._placeholder_image_bytes(filename=reservation.filename, content_type=reservation.content_type)
        image_id = f"shot-{uuid4().hex}"
        self.uploaded_images[image_id] = payload
        self.pending_upload_payloads.pop(intent_id, None)
        return ConfirmedScreenshotUpload(
            image_id=image_id,
            session_id=session_id,
            owner_user_id=user_id,
            filename=reservation.filename,
            content_type=reservation.content_type,
            object_key=reservation.object_key,
            size_bytes=size_bytes,
            status="uploaded",
            uploaded_at_ms=now_ms,
            etag=etag,
        )

    def store_uploaded_image_bytes(
        self,
        *,
        intent_id: str,
        payload: bytes,
    ) -> None:
        reservation = self.issued_intents.get(intent_id)
        if reservation is None:
            raise DomainRequestError("screenshot-answer", "upload", "截图上传意图不存在或已失效。", 404)
        self.pending_upload_payloads[intent_id] = payload

    def _placeholder_image_bytes(self, *, filename: str, content_type: str) -> bytes:
        return f"OfferSteady screenshot placeholder\nfilename={filename}\ncontentType={content_type}\n".encode("utf-8")

    def load_image_bytes(self, *, image: ConfirmedScreenshotUpload) -> bytes:
        payload = self.uploaded_images.get(image.image_id)
        if payload is None:
            raise DomainRequestError("screenshot-answer", "load-image", "截图对象不存在或尚未可读。", 404)
        return payload

    @classmethod
    def _sanitize_filename(cls, filename: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", filename).strip("-.")
        if not cleaned or cleaned.startswith(".") or "/" in cleaned:
            return "screenshot.png"
        if "." not in cleaned:
            return f"{cleaned}.png"
        return cleaned


class ScreenshotPreprocessor:
    def preprocess(
        self,
        *,
        uploads: list[ConfirmedScreenshotUpload],
        upload_port: ScreenshotUploadPort,
        object_storage: FileStoragePort | None = None,
        signed_url_ttl_seconds: int = 600,
        use_signed_url: bool = True,
    ) -> list[PreparedScreenshotImage]:
        prepared: list[PreparedScreenshotImage] = []
        for index, upload in enumerate(uploads):
            payload = upload_port.load_image_bytes(image=upload)
            public_url = None
            if use_signed_url and object_storage is not None:
                try:
                    if object_storage.object_exists(object_key=upload.object_key):
                        public_url = object_storage.create_signed_download_url(
                            object_key=upload.object_key,
                            expires_seconds=signed_url_ttl_seconds,
                        )
                except DomainRequestError:
                    public_url = None
            prepared.append(
                PreparedScreenshotImage(
                    image_id=upload.image_id,
                    session_id=upload.session_id,
                    owner_user_id=upload.owner_user_id,
                    filename=upload.filename,
                    content_type=upload.content_type,
                    object_key=upload.object_key,
                    size_bytes=upload.size_bytes,
                    ordinal=index + 1,
                    content_sha256=hashlib.sha256(payload).hexdigest(),
                    byte_length=len(payload),
                    payload_bytes=payload,
                    public_url=public_url,
                )
            )
        return prepared


class SyntheticVisionGateway(VisionGatewayPort):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def analyze(
        self,
        *,
        session_id: str,
        instruction: str,
        images: list[PreparedScreenshotImage],
        attempt: int,
    ) -> VisionSummary:
        lowered = instruction.lower()
        if "__permanent_fail__" in lowered:
            raise NonRetryableVisionError("forced_permanent_vision_failure")
        if "__retry_once__" in lowered and attempt == 0:
            raise RetryableVisionError("forced_retryable_vision_failure")
        ordered_names = [image.filename for image in images]
        focus = instruction.strip() or "请基于截图给出更稳妥的回答思路"
        summary_text = (
            f"共识别到 {len(images)} 张截图，顺序为：{'、'.join(ordered_names)}。\n"
            f"用户当前想解决的是：{focus}。\n"
            "截图内容被归纳为一组需要直接作答的线上笔试题、代码题、系统设计题或算法题线索。"
        )
        final_answer = (
            "简要回答\n"
            "我会先根据截图题目明确输入输出、边界条件和核心解法，然后直接给出可提交的答案。\n\n"
            "---\n\n"
            "详细回答\n"
            "如果这是代码题，应该先说明思路，再给出完整代码实现；如果是系统设计题，应该先给架构方案、关键组件、数据流和权衡点。\n\n"
            "```python\n"
            "# 根据截图中的具体题目替换函数签名和实现\n"
            "def solve(*args):\n"
            "    pass\n"
            "```"
        )
        usage = VisionUsageReport(
            visual_tokens=max(1, sum(max(1, image.byte_length // 32) for image in images)),
            total_tokens=max(1, sum(max(1, image.byte_length // 32) for image in images)),
            provider_name=self.settings.screenshot_vision_provider,
            model_name=self.settings.screenshot_vision_model,
        )
        return VisionSummary(
            title="截图题目理解",
            summary_text=summary_text,
            derived_question=instruction.strip() or f"请根据截图内容给出回答思路：{'、'.join(ordered_names)}",
            image_count=len(images),
            ordered_image_names=ordered_names,
            final_answer=final_answer,
            usage=usage,
            provider_name=self.settings.screenshot_vision_provider,
            model_name=self.settings.screenshot_vision_model,
        )


class OpenAICompatibleVisionGateway(VisionGatewayPort):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _load_system_prompt(self) -> str:
        prompt_path = Path(self.settings.screenshot_prompt_template_path)
        if not prompt_path.is_absolute():
            prompt_path = Path(__file__).resolve().parents[4] / self.settings.screenshot_prompt_template_path
        return prompt_path.read_text(encoding="utf-8").strip()

    def analyze(
        self,
        *,
        session_id: str,
        instruction: str,
        images: list[PreparedScreenshotImage],
        attempt: int,
    ) -> VisionSummary:
        _ = session_id, attempt
        if not self.settings.screenshot_vision_base_url or not self.settings.screenshot_vision_api_key:
            raise NonRetryableVisionError("当前多模识别模型未配置完成，请检查服务端 .env 配置。")
        url = f"{self.settings.screenshot_vision_base_url.rstrip('/')}/chat/completions"
        content: list[dict[str, object]] = [
            {
                "type": "text",
                "text": (
                    "请直接识别并回答截图中的题目。只输出最终 Markdown 答案，不要输出 JSON、字段名、"
                    "识别过程、OCR 摘要或额外前言。答案必须严格执行系统策略；代码题必须给出完整可运行代码，"
                    "不要只描述解题框架。"
                    f"\n<user_instruction>{instruction.strip() or '无'}</user_instruction>"
                ),
            }
        ]
        for image in images:
            if image.public_url:
                content.append({"type": "image_url", "image_url": {"url": image.public_url}})
            else:
                media_type = image.content_type if image.content_type in {"image/png", "image/jpeg", "image/webp"} else "image/png"
                encoded = base64.b64encode(image.payload_bytes).decode("ascii")
                content.append({"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{encoded}"}})
        payload = {
            "model": self.settings.screenshot_vision_model,
            "stream": False,
            "temperature": 0.1,
            "messages": [
                {"role": "system", "content": self._load_system_prompt()},
                {"role": "user", "content": content},
            ],
        }
        try:
            with httpx.Client(timeout=max(self.settings.integration_http_timeout_seconds, 60.0)) as client:
                response = client.post(url, headers={"Authorization": f"Bearer {self.settings.screenshot_vision_api_key}"}, json=payload)
        except httpx.HTTPError as exc:
            raise RetryableVisionError("截图识别服务暂时不可用，请稍后重试。") from exc
        if response.status_code >= 500:
            raise RetryableVisionError(f"截图识别服务暂时不可用（HTTP {response.status_code}）。")
        if response.status_code >= 400:
            raise NonRetryableVisionError(f"截图识别服务返回异常（HTTP {response.status_code}）。")
        try:
            body = response.json()
        except JSONDecodeError as exc:
            raise NonRetryableVisionError("截图识别模型返回了无法解析的结果。") from exc
        text = self._extract_first_text(body)
        if not text:
            raise NonRetryableVisionError("截图识别模型没有返回可读取的内容。")
        title = "截图题目理解"
        summary_text = instruction.strip() or "已根据当前截图识别题目并生成回答。"
        derived_question = instruction.strip() or "请根据截图内容直接给出本题的回答。"
        final_answer = self._extract_final_answer(text)
        try:
            parsed = self._parse_json_object(text)
            title = str(parsed.get("title") or title).strip() or title
            derived_question = str(parsed.get("derived_question") or derived_question).strip() or derived_question
        except ValueError:
            pass
        usage_payload = body.get("usage", {}) if isinstance(body, dict) else {}
        usage = VisionUsageReport(
            visual_tokens=max(1, int(usage_payload.get("prompt_tokens", 0) or 1)),
            total_tokens=max(1, int(usage_payload.get("total_tokens", 0) or 1)),
            provider_name=self.settings.screenshot_vision_provider,
            model_name=self.settings.screenshot_vision_model,
        )
        return VisionSummary(
            title=title,
            summary_text=summary_text,
            derived_question=derived_question,
            image_count=len(images),
            ordered_image_names=[image.filename for image in images],
            final_answer=final_answer,
            usage=usage,
            provider_name=self.settings.screenshot_vision_provider,
            model_name=self.settings.screenshot_vision_model,
        )

    @staticmethod
    def _extract_first_text(body: dict) -> str | None:
        choices = body.get("choices")
        if not isinstance(choices, list):
            return None
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            message = choice.get("message")
            if not isinstance(message, dict):
                continue
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                return content.strip()
            if isinstance(content, list):
                parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
                        parts.append(item["text"])
                joined = "\n".join(part for part in parts if part.strip()).strip()
                if joined:
                    return joined
        return None

    @staticmethod
    def _parse_json_object(text: str) -> dict[str, object]:
        stripped = text.strip()
        if stripped.startswith("```"):
            stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
            stripped = re.sub(r"\s*```$", "", stripped)
        try:
            parsed = json.loads(stripped)
        except JSONDecodeError:
            start = stripped.find("{")
            end = stripped.rfind("}")
            if start < 0 or end <= start:
                raise ValueError("vision_json_missing")
            parsed = json.loads(stripped[start:end + 1])
        if not isinstance(parsed, dict):
            raise ValueError("vision_json_invalid")
        return parsed

    @classmethod
    def _extract_final_answer(cls, text: str) -> str:
        stripped = text.strip()
        try:
            parsed = cls._parse_json_object(stripped)
        except ValueError:
            return stripped
        final_answer = parsed.get("final_answer")
        if isinstance(final_answer, str) and final_answer.strip():
            return final_answer.strip()
        return stripped


class ScreenshotAnswerService:
    allowed_extensions = [".png", ".jpg", ".jpeg", ".webp"]
    allowed_mime_types = ["image/png", "image/jpeg", "image/webp"]

    def __init__(
        self,
        *,
        settings: Settings,
        logger: logging.Logger,
        session_service: SessionService,
        retrieval_service: RetrievalPort,
        object_storage: FileStoragePort,
        repository: ScreenshotAnswerRepository,
        upload_port: ScreenshotUploadPort,
        preprocessor: ScreenshotPreprocessor,
        vision_gateway: VisionGatewayPort,
        prompt_template: ScreenshotPromptTemplatePort,
        prompt_builder: ScreenshotPromptBuilderPort,
        llm_gateway: LLMGatewayPort,
    ) -> None:
        self.settings = settings
        self.logger = logger
        self.session_service = session_service
        self.retrieval_service = retrieval_service
        self.object_storage = object_storage
        self.repository = repository
        self.upload_port = upload_port
        self.preprocessor = preprocessor
        self.vision_gateway = vision_gateway
        self.prompt_template = prompt_template
        self.prompt_builder = prompt_builder
        self.llm_gateway = llm_gateway

    def validation_policy(self) -> dict[str, object]:
        return {
            "maxFileSizeBytes": self.settings.screenshot_max_file_size_bytes,
            "acceptedExtensions": self.allowed_extensions,
            "acceptedMimeTypes": self.allowed_mime_types,
            "maxImagesPerTask": self.settings.screenshot_max_images_per_task,
        }

    def create_upload_intent(self, *, user_id: str, session_id: str, filename: str, content_type: str, size_bytes: int) -> ScreenshotUploadIntent:
        self._assert_session_uploadable(user_id=user_id, session_id=session_id)
        self._validate_image(filename=filename, content_type=content_type, size_bytes=size_bytes)
        return self.upload_port.create_upload_intent(user_id=user_id, session_id=session_id, filename=filename, content_type=content_type)

    def complete_upload(
        self,
        *,
        user_id: str,
        session_id: str,
        intent_id: str,
        object_key: str,
        content_type: str,
        size_bytes: int,
        etag: str | None = None,
    ) -> ConfirmedScreenshotUpload:
        session = self._assert_session_uploadable(user_id=user_id, session_id=session_id)
        _ = session
        upload = self.upload_port.confirm_uploaded_image(
            user_id=user_id,
            session_id=session_id,
            intent_id=intent_id,
            object_key=object_key,
            content_type=content_type,
            size_bytes=size_bytes,
            etag=etag,
        )
        return self.repository.save_upload(upload)

    def upload_bytes(
        self,
        *,
        user_id: str,
        session_id: str,
        filename: str,
        content_type: str,
        payload: bytes,
        telemetry: dict[str, object] | None = None,
    ) -> ConfirmedScreenshotUpload:
        self._assert_session_uploadable(user_id=user_id, session_id=session_id)
        self._validate_image(filename=filename, content_type=content_type, size_bytes=len(payload))
        optimize_started = perf_counter()
        stored_filename, stored_content_type, stored_payload = self._optimize_screenshot_for_vision(
            filename=filename,
            content_type=content_type,
            payload=payload,
        )
        image_optimize_ms = _elapsed_ms(optimize_started)
        intent = self.upload_port.create_upload_intent(
            user_id=user_id,
            session_id=session_id,
            filename=stored_filename,
            content_type=stored_content_type,
        )
        self.upload_port.store_uploaded_image_bytes(intent_id=intent.intent_id, payload=stored_payload)
        upload = self.upload_port.confirm_uploaded_image(
            user_id=user_id,
            session_id=session_id,
            intent_id=intent.intent_id,
            object_key=intent.object_key,
            content_type=stored_content_type,
            size_bytes=len(stored_payload),
            etag=f"{stored_filename}:{len(stored_payload)}",
        )
        oss_started = perf_counter()
        self.object_storage.save_object_bytes(
            object_key=upload.object_key,
            payload=stored_payload,
            content_type=stored_content_type,
        )
        oss_write_ms = _elapsed_ms(oss_started)
        if telemetry is not None:
            dimensions = self._image_dimensions(payload)
            stored_dimensions = self._image_dimensions(stored_payload)
            telemetry.update({
                "image_optimize_ms": image_optimize_ms,
                "oss_write_ms": oss_write_ms,
                "original_width": dimensions[0],
                "original_height": dimensions[1],
                "compressed_width": stored_dimensions[0],
                "compressed_height": stored_dimensions[1],
                "original_bytes": len(payload),
                "compressed_bytes": len(stored_payload),
                "content_type": stored_content_type,
            })
        return self.repository.save_upload(upload)

    def _optimize_screenshot_for_vision(self, *, filename: str, content_type: str, payload: bytes) -> tuple[str, str, bytes]:
        if not self.settings.screenshot_optimize_before_vision:
            return filename, content_type, payload
        try:
            from PIL import Image
        except Exception:
            return filename, content_type, payload
        try:
            with Image.open(io.BytesIO(payload)) as image:
                image.load()
                width, height = image.size
                max_long_edge = max(320, int(self.settings.screenshot_vision_max_long_edge))
                longest = max(width, height)
                if longest > max_long_edge:
                    ratio = max_long_edge / float(longest)
                    next_size = (max(1, int(width * ratio)), max(1, int(height * ratio)))
                    image = image.resize(next_size, Image.Resampling.LANCZOS)
                if image.mode in {"RGBA", "LA"} or (image.mode == "P" and "transparency" in image.info):
                    background = Image.new("RGB", image.size, (255, 255, 255))
                    alpha = image.convert("RGBA").getchannel("A")
                    background.paste(image.convert("RGBA"), mask=alpha)
                    image = background
                elif image.mode != "RGB":
                    image = image.convert("RGB")
                output = io.BytesIO()
                quality = min(90, max(45, int(self.settings.screenshot_vision_jpeg_quality)))
                image.save(output, format="JPEG", quality=quality, optimize=True, progressive=True)
                optimized = output.getvalue()
        except Exception:
            return filename, content_type, payload
        if len(optimized) >= len(payload):
            return filename, content_type, payload
        stem = filename.rsplit(".", 1)[0] if "." in filename else filename
        safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("-.") or "screenshot"
        return f"{safe_stem}.jpg", "image/jpeg", optimized

    def _image_dimensions(self, payload: bytes) -> tuple[int | None, int | None]:
        try:
            from PIL import Image
            with Image.open(io.BytesIO(payload)) as image:
                return image.size
        except Exception:
            return None, None

    def _telemetry_from_metrics(self, metrics: dict[str, object] | None) -> ScreenshotTimingTelemetry:
        values = metrics or {}
        def number(name: str) -> float | None:
            value = values.get(name)
            return float(value) if isinstance(value, (int, float)) else None
        def integer(name: str) -> int | None:
            value = values.get(name)
            return int(value) if isinstance(value, int) else None
        def string(name: str) -> str | None:
            value = values.get(name)
            return str(value) if isinstance(value, str) and value else None
        return ScreenshotTimingTelemetry(
            upload_accepted_ms=number("upload_accepted_ms"),
            image_optimize_ms=number("image_optimize_ms"),
            oss_write_ms=number("oss_write_ms"),
            signed_url_ms=number("signed_url_ms"),
            vision_model_ms=number("vision_model_ms"),
            answer_persist_ms=number("answer_persist_ms"),
            total_background_ms=number("total_background_ms"),
            failed_phase=string("failed_phase"),
            error_code=string("error_code"),
            original_width=integer("original_width"),
            original_height=integer("original_height"),
            compressed_width=integer("compressed_width"),
            compressed_height=integer("compressed_height"),
            original_bytes=integer("original_bytes"),
            compressed_bytes=integer("compressed_bytes"),
            content_type=string("content_type"),
        )

    def list_uploads(self, *, user_id: str, session_id: str) -> list[ConfirmedScreenshotUpload]:
        self.session_service.get_session(user_id=user_id, session_id=session_id)
        return [item for item in self.repository.list_uploads_for_session(session_id=session_id) if item.owner_user_id == user_id and item.status != "deleted"]

    def answer_screenshots(
        self,
        *,
        user_id: str,
        session_id: str,
        image_ids: list[str],
        instruction: str,
        stream: bool,
        telemetry: dict[str, object] | None = None,
    ) -> tuple[ScreenshotAnswerTaskRecord, RetrievalResponse]:
        session = self.session_service.get_session(user_id=user_id, session_id=session_id)
        if session.status != "live":
            raise DomainRequestError("screenshot-answer", "create-task", "只有进行中的面试会话才能发起截图回答。", 400)
        if len(image_ids) > self.settings.screenshot_max_images_per_task:
            raise DomainRequestError(
                "screenshot-answer",
                "create-task",
                f"单次截图回答最多支持 {self.settings.screenshot_max_images_per_task} 张截图。",
                400,
            )
        uploads = [self._require_upload(user_id=user_id, session_id=session_id, image_id=image_id) for image_id in image_ids]
        now_ms = _now_ms()
        task = self.repository.save_task(
            ScreenshotAnswerTaskRecord(
                task_id=f"screenshot-answer-{uuid4().hex}",
                session_id=session_id,
                owner_user_id=user_id,
                instruction=instruction.strip(),
                answer_text="",
                status="queued",
                stream_mode=stream,
                image_ids=image_ids,
                image_count=len(image_ids),
                created_at_ms=now_ms,
                updated_at_ms=now_ms,
            )
        )
        self._log(logging.INFO, "screenshot_answer.started", task=task, session_id=session_id, image_count=len(image_ids), retry_count=0)
        prepare_started = perf_counter()
        prepared = self.preprocessor.preprocess(
            uploads=uploads,
            upload_port=self.upload_port,
            object_storage=self.object_storage,
            signed_url_ttl_seconds=self.settings.screenshot_signed_url_ttl_seconds,
            use_signed_url=self.settings.screenshot_use_signed_url_for_vision,
        )
        if telemetry is not None:
            telemetry["signed_url_ms"] = _elapsed_ms(prepare_started)
        current = self.repository.save_task(replace(task, status="processing-images", updated_at_ms=_now_ms()))
        last_error: Exception | None = None
        retrieval_context = RetrievalContext(
            normalized_question=instruction.strip(),
            context_text="",
            chunks=[],
            candidate_count=0,
            final_count=0,
            strategy="filtered-first",
        )
        for attempt in range(self.settings.screenshot_retry_max_attempts + 1):
            try:
                current = self.repository.save_task(replace(current, status="vision-running", updated_at_ms=_now_ms(), retry_count=attempt))
                vision_started = perf_counter()
                vision = self.vision_gateway.analyze(session_id=session_id, instruction=instruction, images=prepared, attempt=attempt)
                if telemetry is not None:
                    telemetry["vision_model_ms"] = _elapsed_ms(vision_started)
                current = self.repository.save_task(
                    replace(
                        current,
                        status="streaming",
                        prompt_template_id="screenshot-vision-direct",
                        prompt_version=self.settings.screenshot_prompt_version,
                        retrieval_excerpt_count=0,
                        material_context_status="not-used",
                        fixed_source_count=0,
                        retrieved_source_count=0,
                        material_provenance={"selectionRevision": session.material_binding.revision, "usedSources": [], "noPersonalMaterialUsed": True},
                        unavailable_material_sources=[],
                        vision_provider_name=vision.provider_name,
                        vision_model_name=vision.model_name,
                        vision_summary_title=vision.title,
                        updated_at_ms=_now_ms(),
                    )
                )
                persist_started = perf_counter()
                completed = self._complete_vision_direct_task(task=current, vision=vision, retry_count=attempt)
                self.session_service.append_context(
                    user_id=user_id,
                    session_id=session_id,
                    role="screenshot",
                    source_kind="screenshot-answer",
                    content=vision.summary_text,
                    visibility="session",
                    related_task_id=completed.task_id,
                )
                self.session_service.append_context(
                    user_id=user_id,
                    session_id=session_id,
                    role="assistant",
                    source_kind="screenshot-answer",
                    content=completed.answer_text,
                    visibility="ai",
                    related_task_id=completed.task_id,
                )
                if vision.usage is not None:
                    self.session_service.record_usage(
                        user_id=user_id,
                        session_id=session_id,
                        usage_kind="other",
                        prompt_tokens=0,
                        completion_tokens=0,
                        total_tokens=vision.usage.total_tokens,
                        provider_name=vision.usage.provider_name,
                        model_name=vision.usage.model_name,
                        related_task_id=completed.task_id,
                    )
                self._log(logging.INFO, "screenshot_answer.completed", task=completed, session_id=session_id, image_count=len(image_ids), retry_count=attempt)
                if telemetry is not None:
                    telemetry["answer_persist_ms"] = _elapsed_ms(persist_started)
                    completed = self.repository.save_task(replace(completed, telemetry=self._telemetry_from_metrics(telemetry)))
                return completed, self._to_retrieval_response(retrieval_context)
            except (RetryableVisionError, RetryableChatError) as exc:
                last_error = exc
                self._log(
                    logging.WARNING,
                    "screenshot_answer.retrying",
                    task=current,
                    session_id=session_id,
                    image_count=len(image_ids),
                    retry_count=attempt + 1,
                    error_code=str(exc),
                )
                continue
            except (NonRetryableVisionError, NonRetryableChatError) as exc:
                last_error = exc
                break
        failed = self.repository.save_task(
            replace(
                current,
                status="failed",
                retry_count=self.settings.screenshot_retry_max_attempts,
                error_code=last_error.__class__.__name__ if last_error else "screenshot_answer_failed",
                error_message=str(last_error) if last_error else "screenshot_answer_failed",
                telemetry=self._telemetry_from_metrics({
                    **(telemetry or {}),
                    "failed_phase": "vision",
                    "error_code": last_error.__class__.__name__ if last_error else "screenshot_answer_failed",
                }),
                updated_at_ms=_now_ms(),
                completed_at_ms=_now_ms(),
            )
        )
        self._log(logging.WARNING, "screenshot_answer.failed", task=failed, session_id=session_id, image_count=len(image_ids), retry_count=failed.retry_count, error_code=failed.error_code)
        return failed, self._to_retrieval_response(retrieval_context)

    def get_task(self, *, user_id: str, task_id: str) -> ScreenshotAnswerTaskRecord:
        task = self.repository.get_task(task_id)
        if task is None:
            raise DomainRequestError("screenshot-answer", "get-task", "截图回答任务不存在。", 404)
        if task.owner_user_id != user_id:
            raise DomainRequestError("screenshot-answer", "get-task", "不能查看其他用户的截图回答任务。", 403)
        return task

    def delete_task(self, *, user_id: str, task_id: str) -> ScreenshotAnswerTaskRecord:
        task = self.get_task(user_id=user_id, task_id=task_id)
        if task.status == "cancelled":
            return task
        return self.repository.save_task(replace(task, status="cancelled", updated_at_ms=_now_ms(), completed_at_ms=_now_ms()))

    def list_session_history(self, *, user_id: str, session_id: str) -> list[ScreenshotAnswerTaskRecord]:
        self.session_service.get_session(user_id=user_id, session_id=session_id)
        return [task for task in self.repository.list_tasks_for_session(session_id=session_id) if task.status != "cancelled"]

    def create_remote_capture_request(
        self,
        *,
        user_id: str,
        session_id: str,
        device_id: str,
        manual_code: str,
        instruction: str,
    ) -> RemoteScreenshotCaptureRequest:
        session = self.session_service.get_session(user_id=user_id, session_id=session_id)
        if session.status != "live":
            raise DomainRequestError("screenshot-answer", "remote-capture", "只有进行中的面试会话才能发起截屏回答。", 400)
        now_ms = _now_ms()
        request = RemoteScreenshotCaptureRequest(
            request_id=f"shot-capture-{uuid4().hex}",
            session_id=session_id,
            owner_user_id=user_id,
            device_id=device_id,
            manual_code=manual_code,
            instruction=instruction.strip(),
            status="requested",
            stage="requested",
            created_at_ms=now_ms,
            updated_at_ms=now_ms,
        )
        return self.repository.save_remote_capture_request(request)

    def get_remote_capture_request(self, *, user_id: str, request_id: str) -> RemoteScreenshotCaptureRequest:
        request = self.repository.get_remote_capture_request(request_id)
        if request is None:
            raise DomainRequestError("screenshot-answer", "remote-capture", "截图回答请求不存在。", 404)
        if request.owner_user_id != user_id:
            raise DomainRequestError("screenshot-answer", "remote-capture", "不能查看其他用户的截图回答请求。", 403)
        return request

    def cancel_remote_capture_request(self, *, user_id: str, request_id: str) -> RemoteScreenshotCaptureRequest:
        request = self.get_remote_capture_request(user_id=user_id, request_id=request_id)
        if request.status in {"completed", "failed", "cancelled"}:
            return request
        cancelled = replace(request, status="cancelled", stage="cancelled", updated_at_ms=_now_ms(), completed_at_ms=_now_ms(), error_message="截图回答已终止。")
        if request.answer_task_id:
            self.delete_task(user_id=user_id, task_id=request.answer_task_id)
        return self.repository.save_remote_capture_request(cancelled)

    def get_next_remote_capture_request(self, *, device_id: str, manual_code: str) -> RemoteScreenshotCaptureRequest | None:
        return self.repository.get_next_pending_remote_capture_request(device_id=device_id, manual_code=manual_code)

    def claim_remote_capture_request(self, *, request_id: str, device_id: str, manual_code: str) -> RemoteScreenshotCaptureRequest:
        request = self.repository.get_remote_capture_request(request_id)
        if request is None:
            raise DomainRequestError("screenshot-answer", "remote-capture", "截图回答请求不存在。", 404)
        if request.device_id != device_id or request.manual_code != manual_code:
            raise DomainRequestError("screenshot-answer", "remote-capture", "这台电脑不能处理当前截图请求。", 403)
        if request.status == "cancelled":
            raise DomainRequestError("screenshot-answer", "remote-capture", "截图回答请求已取消。", 409)
        if request.status == "completed":
            return request
        claimed = replace(request, status="processing", stage="claimed", updated_at_ms=_now_ms(), claimed_at_ms=request.claimed_at_ms or _now_ms())
        return self.repository.save_remote_capture_request(claimed)

    def fail_remote_capture_request(self, *, request_id: str, device_id: str, manual_code: str, message: str, stage: str = "capture-failed") -> RemoteScreenshotCaptureRequest:
        request = self.claim_remote_capture_request(request_id=request_id, device_id=device_id, manual_code=manual_code)
        failed = replace(request, status="failed", stage=stage, error_message=message, updated_at_ms=_now_ms(), completed_at_ms=_now_ms())
        return self.repository.save_remote_capture_request(failed)

    def complete_remote_capture_request(
        self,
        *,
        request_id: str,
        device_id: str,
        manual_code: str,
        filename: str,
        content_type: str,
        payload: bytes,
    ) -> tuple[RemoteScreenshotCaptureRequest, ScreenshotAnswerTaskRecord]:
        background_started = perf_counter()
        metrics: dict[str, object] = {"upload_accepted_ms": 0.0}
        request = self.claim_remote_capture_request(request_id=request_id, device_id=device_id, manual_code=manual_code)
        upload_started = perf_counter()
        upload = self.upload_bytes(
            user_id=request.owner_user_id,
            session_id=request.session_id,
            filename=filename,
            content_type=content_type,
            payload=payload,
            telemetry=metrics,
        )
        metrics["upload_accepted_ms"] = _elapsed_ms(upload_started)
        request = self.repository.save_remote_capture_request(replace(
            request,
            status="processing",
            stage="uploaded",
            updated_at_ms=_now_ms(),
            captured_filename=filename,
            telemetry=self._telemetry_from_metrics(metrics),
        ))
        request = self.repository.save_remote_capture_request(replace(
            request,
            stage="vision-running",
            updated_at_ms=_now_ms(),
            telemetry=self._telemetry_from_metrics(metrics),
        ))
        task, _ = self.answer_screenshots(
            user_id=request.owner_user_id,
            session_id=request.session_id,
            image_ids=[upload.image_id],
            instruction=request.instruction,
            stream=True,
            telemetry=metrics,
        )
        metrics["total_background_ms"] = _elapsed_ms(background_started)
        final_telemetry = self._telemetry_from_metrics(metrics)
        task = self.repository.save_task(replace(task, telemetry=final_telemetry))
        completed = replace(
            request,
            status="completed" if task.status == "completed" else "failed",
            updated_at_ms=_now_ms(),
            completed_at_ms=_now_ms(),
            answer_task_id=task.task_id,
            captured_filename=filename,
            error_message=task.error_message,
            telemetry=final_telemetry,
        )
        return self.repository.save_remote_capture_request(replace(completed, stage="completed" if task.status == "completed" else "failed")), task

    def complete_remote_capture_request_safely(
        self,
        *,
        request_id: str,
        device_id: str,
        manual_code: str,
        filename: str,
        content_type: str,
        payload: bytes,
    ) -> None:
        try:
            self.complete_remote_capture_request(
                request_id=request_id,
                device_id=device_id,
                manual_code=manual_code,
                filename=filename,
                content_type=content_type,
                payload=payload,
            )
        except Exception as exc:
            failed_phase = "background"
            stage = "failed"
            if isinstance(exc, DomainRequestError):
                if getattr(exc, "action", None) in {"upload", "save-object"}:
                    stage = "upload-failed"
                    failed_phase = "oss-write" if getattr(exc, "action", None) == "save-object" else "upload"
                elif getattr(exc, "action", None) == "sign-object":
                    failed_phase = "signed-url"
            try:
                request = self.repository.get_remote_capture_request(request_id)
                telemetry = self._telemetry_from_metrics({
                    **(request.telemetry.__dict__ if request is not None else {}),
                    "failed_phase": failed_phase,
                    "error_code": getattr(exc, "error_code", None) or exc.__class__.__name__,
                })
                failed = self.fail_remote_capture_request(
                    request_id=request_id,
                    device_id=device_id,
                    manual_code=manual_code,
                    message=str(exc) or "截图上传到 OSS 失败，请稍后重试。",
                    stage=stage,
                )
                self.repository.save_remote_capture_request(replace(failed, telemetry=telemetry))
            except Exception:
                self._log(
                    logging.WARNING,
                    "screenshot_answer.remote_background_failed",
                    session_id="unknown",
                    error_code=exc.__class__.__name__,
                )

    def _assert_session_uploadable(self, *, user_id: str, session_id: str):
        session = self.session_service.get_session(user_id=user_id, session_id=session_id)
        if session.status == "ended":
            raise DomainRequestError("screenshot-answer", "upload", "已结束的面试会话不能继续上传截图。", 400)
        return session

    def _validate_image(self, *, filename: str, content_type: str, size_bytes: int) -> None:
        lowered = filename.lower()
        if not any(lowered.endswith(item) for item in self.allowed_extensions):
            raise DomainRequestError("screenshot-answer", "upload", "截图仅支持 PNG、JPG、JPEG、WEBP。", 400)
        if content_type.lower() not in self.allowed_mime_types:
            raise DomainRequestError("screenshot-answer", "upload", "截图 MIME 类型不受支持。", 400)
        if size_bytes > self.settings.screenshot_max_file_size_bytes:
            raise DomainRequestError(
                "screenshot-answer",
                "upload",
                f"截图大小不能超过 {self.settings.screenshot_max_file_size_bytes // (1024 * 1024)} MB。",
                400,
            )

    def _require_upload(self, *, user_id: str, session_id: str, image_id: str) -> ConfirmedScreenshotUpload:
        upload = self.repository.get_upload(image_id)
        if upload is None:
            raise DomainRequestError("screenshot-answer", "create-task", "截图不存在，请重新上传。", 404)
        if upload.owner_user_id != user_id or upload.session_id != session_id:
            raise DomainRequestError("screenshot-answer", "create-task", "不能使用其他会话或其他用户的截图。", 403)
        if upload.status != "uploaded":
            raise DomainRequestError("screenshot-answer", "create-task", "当前截图不可用于回答。", 400)
        return upload

    def _complete_task(
        self,
        *,
        task: ScreenshotAnswerTaskRecord,
        prompt: PromptBuildResult,
        answer,
        vision: VisionSummary,
        retry_count: int,
    ) -> ScreenshotAnswerTaskRecord:
        completed = replace(
            task,
            answer_text=answer.final_text,
            status="completed",
            provider_name=answer.provider_name,
            model_name=answer.model_name,
            vision_provider_name=vision.provider_name,
            vision_model_name=vision.model_name,
            prompt_template_id=prompt.prompt_config.template_id,
            prompt_version=prompt.prompt_config.version,
            retrieval_excerpt_count=prompt.retrieval_excerpt_count,
            retry_count=retry_count,
            chunks=answer.chunks,
            vision_summary_title=vision.title,
            updated_at_ms=_now_ms(),
            completed_at_ms=_now_ms(),
        )
        return self.repository.save_task(completed)

    def _complete_vision_direct_task(
        self,
        *,
        task: ScreenshotAnswerTaskRecord,
        vision: VisionSummary,
        retry_count: int,
    ) -> ScreenshotAnswerTaskRecord:
        answer_text = (vision.final_answer or vision.summary_text or vision.derived_question).strip()
        if "简要回答" not in answer_text or "---" not in answer_text or "详细回答" not in answer_text:
            answer_text = f"简要回答\n{vision.derived_question.strip() or vision.title}\n\n---\n\n详细回答\n{answer_text}"
        completed = replace(
            task,
            answer_text=answer_text,
            status="completed",
            provider_name=vision.provider_name,
            model_name=vision.model_name,
            vision_provider_name=vision.provider_name,
            vision_model_name=vision.model_name,
            prompt_template_id="screenshot-vision-direct",
            prompt_version=self.settings.screenshot_prompt_version,
            retrieval_excerpt_count=0,
            material_context_status="not-used",
            fixed_source_count=0,
            retrieved_source_count=0,
            material_provenance={"usedSources": [], "noPersonalMaterialUsed": True},
            retry_count=retry_count,
            chunks=[ChatAnswerChunk(sequence=0, text=answer_text, is_final=True)],
            vision_summary_title=vision.title,
            updated_at_ms=_now_ms(),
            completed_at_ms=_now_ms(),
        )
        return self.repository.save_task(completed)

    def _retrieve_context(self, *, user_id: str, session, question: str) -> RetrievalContext:
        try:
            knowledge_documents = [document for document in session.material_binding.bound_documents if document.active and document.document_kind == "knowledge"]
            return self.retrieval_service.retrieve(
                question=question,
                filter=RetrievalFilter(
                    owner_user_id=user_id,
                    interview_session_id=session.session_id,
                    document_kinds=["knowledge"] if knowledge_documents else [],
                    document_ids=[document.document_id for document in knowledge_documents],
                    document_version_ids=[
                        document.document_version_id
                        for document in knowledge_documents
                        if document.document_version_id
                    ],
                    knowledge_collection_ids=[
                        document.knowledge_collection_id
                        for document in knowledge_documents
                        if document.knowledge_collection_id
                    ],
                ),
                candidate_top_k=self.settings.retrieval_candidate_top_k,
                final_top_k=self.settings.retrieval_final_top_k,
                strategy=self.settings.retrieval_strategy,  # type: ignore[arg-type]
            )
        except Exception as exc:
            self._log(
                logging.WARNING,
                "screenshot_answer.retrieval_degraded",
                task=None,
                session_id=session.session_id,
                image_count=0,
                retry_count=0,
                error_code=exc.__class__.__name__,
            )
            return RetrievalContext(
                normalized_question=question.strip(),
                context_text="",
                chunks=[],
                candidate_count=0,
                final_count=0,
                strategy="filtered-first",
            )

    def _session_material_prompt_context(self, session) -> str:
        return self._assemble_material_context(session=session, retrieval=RetrievalContext(normalized_question="", context_text="", chunks=[], candidate_count=0, final_count=0, strategy="filtered-first"))[0]

    def _assemble_material_context(self, *, session, retrieval: RetrievalContext) -> tuple[str, MaterialContextAssembly, dict[str, object]]:
        lines: list[str] = []
        used_sources: list[MaterialContextSource] = []
        unavailable_sources: list[MaterialContextSource] = []
        for label, kind in (("简历", "resume"), ("职位 JD", "job_description")):
            document = next((item for item in session.material_binding.bound_documents if item.active and item.document_kind == kind), None)
            if document is None:
                continue
            summary, truncated = self._load_material_markdown_for_prompt(document, owner_user_id=session.material_binding.owner_user_id)
            source = MaterialContextSource(
                source_id=document.document_id,
                source_version=document.document_version_id or document.document_id,
                display_name=document.display_name,
                kind="jd" if document.document_kind == "job_description" else document.document_kind,
                document_id=document.document_id,
                document_version_id=document.document_version_id,
                context_role="fixed",
                evidence_summary=(summary[:80].replace("\n", " ") if summary else None),
                truncated=truncated,
                unavailable=not bool(summary),
                unavailable_reason=None if summary else "processed_markdown_unavailable",
            )
            if summary:
                used_sources.append(source)
                lines.append(f"[{label}] {document.display_name} ({document.document_version_id or document.document_id})\n{summary}")
            else:
                unavailable_sources.append(source)
                lines.append(f"[{label}] {document.display_name}：资料已选择，但处理产物当前不可读，本次回答不得声称已使用该资料。")
        retrieved_by_document: dict[str, list] = {}
        for chunk in retrieval.chunks:
            retrieved_by_document.setdefault(chunk.document_id, []).append(chunk)
        for document in [item for item in session.material_binding.bound_documents if item.active and item.document_kind == "knowledge"]:
            chunks = retrieved_by_document.get(document.document_id, [])
            if not chunks:
                continue
            first = chunks[0]
            used_sources.append(
                MaterialContextSource(
                    source_id=document.document_id,
                    source_version=document.document_version_id or document.document_id,
                    display_name=document.display_name,
                    kind="knowledge",
                    document_id=document.document_id,
                    document_version_id=document.document_version_id,
                    context_role="retrieved",
                    evidence_summary=first.content[:80].replace("\n", " "),
                    retrieval_count=len(chunks),
                )
            )
        status = "ready" if used_sources and not unavailable_sources else "degraded" if used_sources or unavailable_sources else "no-context"
        assembly = MaterialContextAssembly(
            status=status,
            fixed_source_count=len([item for item in used_sources if item.context_role == "fixed"]),
            retrieved_source_count=len([item for item in used_sources if item.context_role == "retrieved"]),
            used_sources=used_sources,
            unavailable_sources=unavailable_sources,
        )
        provenance = {
            "selectionRevision": session.material_binding.revision,
            "usedSources": [self._material_source_payload(item) for item in used_sources],
            "unavailableSources": [self._material_source_payload(item) for item in unavailable_sources],
            "fixedSourceCount": assembly.fixed_source_count,
            "retrievedSourceCount": assembly.retrieved_source_count,
            "noPersonalMaterialUsed": not used_sources,
            "retrievalTraceId": retrieval.trace_id,
        }
        return "\n\n".join(lines), assembly, provenance

    def _load_material_markdown_for_prompt(self, document, *, owner_user_id: str) -> tuple[str, bool]:
        if not document.document_version_id:
            return "", False
        try:
            key = MaterialObjectKeyFactory(self.settings).processed_artifact_key(
                owner_user_id=owner_user_id,
                document_kind=document.document_kind,
                document_id=document.document_id,
                document_version_id=document.document_version_id,
                artifact_kind="normalized_markdown",
            )
            markdown = self.object_storage.load_object_bytes(object_key=key).decode("utf-8", errors="replace").strip()
        except Exception:
            return "", False
        limit = max(1200, min(self.settings.rag_context_max_characters, 6000))
        truncated = len(markdown) > limit
        return markdown[:limit] + ("\n\n[固定资料已截断]" if truncated else ""), truncated

    def _material_source_payload(self, source: MaterialContextSource) -> dict[str, object]:
        return {
            "sourceId": source.source_id,
            "sourceVersion": source.source_version,
            "displayName": source.display_name,
            "kind": source.kind,
            "documentId": source.document_id,
            "documentVersionId": source.document_version_id,
            "contextRole": source.context_role,
            "evidenceSummary": source.evidence_summary,
            "retrievalCount": source.retrieval_count,
            "truncated": source.truncated,
            "unavailable": source.unavailable,
            "unavailableReason": source.unavailable_reason,
        }

    def _to_retrieval_response(self, retrieval: RetrievalContext) -> RetrievalResponse:
        return RetrievalResponse(
            normalizedQuestion=retrieval.normalized_question,
            contextText=retrieval.context_text,
            chunks=[
                RetrievedChunkResponse(
                    documentId=chunk.document_id,
                    documentKind=chunk.document_kind,
                    chunkId=chunk.chunk_id,
                    chunkIndex=chunk.chunk_index,
                    content=chunk.content,
                    score=chunk.score,
                    rerankScore=chunk.rerank_score,
                    metadata=chunk.metadata,
                )
                for chunk in retrieval.chunks
            ],
            candidateCount=retrieval.candidate_count,
            finalCount=retrieval.final_count,
            strategy=retrieval.strategy,
        )

    def _log(
        self,
        level: int,
        event: str,
        *,
        task: ScreenshotAnswerTaskRecord | None,
        session_id: str,
        image_count: int,
        retry_count: int,
        error_code: str | None = None,
    ) -> None:
        log_event(
            self.logger,
            level,
            settings=self.settings,
            event=event,
            feature="screenshot-answer",
            action="screenshot-chat",
            session_id=session_id,
            task_id=task.task_id if task else None,
            provider_name=task.provider_name if task else None,
            model_name=task.model_name if task else None,
            vision_provider_name=task.vision_provider_name if task else None,
            vision_model_name=task.vision_model_name if task else None,
            prompt_version=task.prompt_version if task else None,
            image_count=image_count,
            retry_count=retry_count,
            status=task.status if task else None,
            error_code=error_code,
        )
