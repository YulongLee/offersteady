from __future__ import annotations

import argparse
import base64
import hashlib
import json
import logging
import math
import subprocess
import time as time_module
import wave
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from tempfile import NamedTemporaryFile
from time import perf_counter, time
from typing import Any, Protocol
from urllib.parse import urljoin
from urllib.parse import urlencode
from uuid import uuid4

import httpx
import psycopg

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, log_event


VerificationStatus = str


def _now_ms() -> int:
    return int(time() * 1000)


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _mask_secret(value: str | None) -> str | None:
    if value is None:
        return None
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}***{value[-4:]}"


def _digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _safe_excerpt(value: str, limit: int = 80) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit]}…"


def _sanitize_payload(payload: Any) -> Any:
    secret_markers = ("token", "secret", "authorization", "api_key", "apikey", "password")
    if isinstance(payload, dict):
        sanitized: dict[str, Any] = {}
        for key, value in payload.items():
            if any(marker in key.lower() for marker in secret_markers):
                sanitized[key] = _mask_secret(str(value)) if value is not None else None
            else:
                sanitized[key] = _sanitize_payload(value)
        return sanitized
    if isinstance(payload, list):
        return [_sanitize_payload(item) for item in payload]
    if isinstance(payload, str):
        if len(payload) > 160:
            return {"excerpt": _safe_excerpt(payload), "sha256": _digest_text(payload), "length": len(payload)}
        return payload
    return payload


def _join_url(base_url: str, path: str) -> str:
    return urljoin(f"{base_url.rstrip('/')}/", path.lstrip("/"))


def _extract_path(payload: Any, dotted_path: str) -> Any:
    current = payload
    for segment in dotted_path.split("."):
        if isinstance(current, dict):
            current = current.get(segment)
        else:
            return None
    return current


def _extract_first_text(payload: Any) -> str | None:
    if isinstance(payload, str):
        stripped = payload.strip()
        return stripped or None
    if isinstance(payload, dict):
        for key in ("text", "content", "markdown", "answer", "transcript"):
            value = payload.get(key)
            text = _extract_first_text(value)
            if text:
                return text
        for value in payload.values():
            text = _extract_first_text(value)
            if text:
                return text
    if isinstance(payload, list):
        for item in payload:
            text = _extract_first_text(item)
            if text:
                return text
    return None


@dataclass
class VerificationStepResult:
    name: str
    status: VerificationStatus
    duration_ms: int
    summary: str
    metrics: dict[str, Any] = field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None


@dataclass
class VerificationItemResult:
    item_id: str
    title: str
    provider_name: str
    status: VerificationStatus
    started_at: str
    completed_at: str
    duration_ms: int
    attempts: int
    steps: list[VerificationStepResult] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "itemId": self.item_id,
            "title": self.title,
            "providerName": self.provider_name,
            "status": self.status,
            "startedAt": self.started_at,
            "completedAt": self.completed_at,
            "durationMs": self.duration_ms,
            "attempts": self.attempts,
            "summary": self.summary,
            "steps": [
                {
                    "name": step.name,
                    "status": step.status,
                    "durationMs": step.duration_ms,
                    "summary": step.summary,
                    "metrics": _sanitize_payload(step.metrics),
                    "errorCode": step.error_code,
                    "errorMessage": step.error_message,
                }
                for step in self.steps
            ],
        }


@dataclass
class IntegrationReport:
    report_id: str
    environment_label: str
    started_at: str
    completed_at: str
    duration_ms: int
    overall_status: VerificationStatus
    selected_items: list[str]
    results: list[VerificationItemResult]

    def to_dict(self) -> dict[str, Any]:
        passed = sum(1 for item in self.results if item.status == "passed")
        failed = sum(1 for item in self.results if item.status == "failed")
        skipped = sum(1 for item in self.results if item.status == "skipped")
        return {
            "reportId": self.report_id,
            "environmentLabel": self.environment_label,
            "startedAt": self.started_at,
            "completedAt": self.completed_at,
            "durationMs": self.duration_ms,
            "overallStatus": self.overall_status,
            "selectedItems": self.selected_items,
            "summary": {
                "total": len(self.results),
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
            },
            "results": [item.to_dict() for item in self.results],
        }


class VerificationError(Exception):
    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        self.code = code
        self.message = message
        self.retryable = retryable
        super().__init__(message)


class RecordedVerificationFailure(VerificationError):
    def __init__(self, recorder: "VerificationItemRecorder", code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(code, message, retryable=retryable)
        self.recorder = recorder


@dataclass
class VerificationContext:
    settings: Settings
    logger: logging.Logger
    temp_dir: Path


class IntegrationVerifier(Protocol):
    item_id: str
    title: str
    provider_name: str

    def verify(self, context: VerificationContext) -> VerificationItemResult: ...


class VerificationItemRecorder:
    def __init__(self, *, context: VerificationContext, item_id: str, title: str, provider_name: str) -> None:
        self.context = context
        self.item_id = item_id
        self.title = title
        self.provider_name = provider_name
        self.started_at_iso = _utc_now_iso()
        self.started_at_perf = perf_counter()
        self.steps: list[VerificationStepResult] = []

    def run_step(self, name: str, action, *, success_summary: str) -> Any:
        started = perf_counter()
        try:
            result = action()
            duration_ms = int((perf_counter() - started) * 1000)
            metrics = result if isinstance(result, dict) else {}
            self.steps.append(VerificationStepResult(name=name, status="passed", duration_ms=duration_ms, summary=success_summary, metrics=metrics))
            log_event(
                self.context.logger,
                logging.INFO,
                settings=self.context.settings,
                event="integration_verification.step_passed",
                feature="integration-verification",
                action=name,
                provider=self.provider_name,
                item_id=self.item_id,
                metrics=_sanitize_payload(metrics),
            )
            return result
        except VerificationError as exc:
            duration_ms = int((perf_counter() - started) * 1000)
            self.steps.append(
                VerificationStepResult(
                    name=name,
                    status="failed",
                    duration_ms=duration_ms,
                    summary="Step failed",
                    error_code=exc.code,
                    error_message=exc.message,
                )
            )
            log_event(
                self.context.logger,
                logging.WARNING,
                settings=self.context.settings,
                event="integration_verification.step_failed",
                feature="integration-verification",
                action=name,
                provider=self.provider_name,
                item_id=self.item_id,
                error_code=exc.code,
                error_message=exc.message,
            )
            raise RecordedVerificationFailure(self, exc.code, exc.message, retryable=exc.retryable) from exc
        except Exception as exc:  # pragma: no cover - defensive
            duration_ms = int((perf_counter() - started) * 1000)
            self.steps.append(
                VerificationStepResult(
                    name=name,
                    status="failed",
                    duration_ms=duration_ms,
                    summary="Step failed",
                    error_code=exc.__class__.__name__,
                    error_message=str(exc),
                )
            )
            log_event(
                self.context.logger,
                logging.WARNING,
                settings=self.context.settings,
                event="integration_verification.step_failed",
                feature="integration-verification",
                action=name,
                provider=self.provider_name,
                item_id=self.item_id,
                error_code=exc.__class__.__name__,
                error_message=str(exc),
            )
            raise RecordedVerificationFailure(self, exc.__class__.__name__, str(exc), retryable=False) from exc

    def finalize(self, *, status: VerificationStatus, attempts: int, summary: str) -> VerificationItemResult:
        return VerificationItemResult(
            item_id=self.item_id,
            title=self.title,
            provider_name=self.provider_name,
            status=status,
            started_at=self.started_at_iso,
            completed_at=_utc_now_iso(),
            duration_ms=int((perf_counter() - self.started_at_perf) * 1000),
            attempts=attempts,
            steps=list(self.steps),
            summary=summary,
        )


class BaseVerifier:
    item_id = ""
    title = ""
    provider_name = ""

    def _require(self, condition: Any, *, code: str, message: str) -> None:
        if not condition:
            raise VerificationError(code, message)


class OssVerifier(BaseVerifier):
    item_id = "oss"
    title = "OSS Upload / Download Test"
    provider_name = "aliyun-oss"

    def verify(self, context: VerificationContext) -> VerificationItemResult:
        recorder = VerificationItemRecorder(context=context, item_id=self.item_id, title=self.title, provider_name=self.provider_name)
        settings = context.settings
        self._require(settings.oss_access_key_id and settings.oss_access_key_secret, code="oss_credentials_missing", message="OSS credentials are not configured.")
        self._require(settings.oss_bucket and settings.oss_endpoint, code="oss_config_missing", message="OSS bucket or endpoint is not configured.")
        try:
            from oss2 import Auth, Bucket
        except ModuleNotFoundError as exc:  # pragma: no cover - depends on environment
            raise VerificationError("oss_sdk_missing", "Python package `oss2` is not installed.") from exc
        endpoint = (settings.oss_endpoint or "").replace("https://", "").replace("http://", "")
        auth = Auth(settings.oss_access_key_id, settings.oss_access_key_secret)
        bucket = Bucket(auth, endpoint, settings.oss_bucket)
        object_key = f"{settings.oss_key_prefix.strip('/')}/integration-verification/{uuid4().hex}.md"
        payload = b"# OfferSteady Integration Verification\n\nSynthetic OSS payload.\n"

        def upload() -> dict[str, Any]:
            result = bucket.put_object(object_key, payload)
            if result.status not in {200, 201}:
                raise VerificationError("oss_upload_failed", f"Unexpected OSS upload status: {result.status}")
            return {"objectKey": object_key, "sizeBytes": len(payload), "status": result.status}

        def head() -> dict[str, Any]:
            result = bucket.head_object(object_key)
            return {"contentLength": getattr(result, "content_length", len(payload)), "requestId": getattr(result, "request_id", "")}

        def download() -> dict[str, Any]:
            body = bucket.get_object(object_key).read()
            if body != payload:
                raise VerificationError("oss_download_mismatch", "Downloaded payload does not match uploaded payload.")
            return {"sha256": hashlib.sha256(body).hexdigest()[:16], "bytes": len(body)}

        try:
            recorder.run_step("upload", upload, success_summary="Uploaded synthetic object to OSS.")
            recorder.run_step("head", head, success_summary="Confirmed uploaded object metadata from OSS.")
            recorder.run_step("download", download, success_summary="Downloaded and verified the uploaded OSS object.")
            return recorder.finalize(status="passed", attempts=1, summary="OSS upload/head/download verification passed.")
        finally:
            try:
                bucket.delete_object(object_key)
            except Exception:
                pass


class MineruVerifier(BaseVerifier):
    item_id = "mineru"
    title = "MinerU Test"
    provider_name = "mineru"

    def verify(self, context: VerificationContext) -> VerificationItemResult:
        recorder = VerificationItemRecorder(context=context, item_id=self.item_id, title=self.title, provider_name=self.provider_name)
        settings = context.settings
        self._require(settings.integration_mineru_base_url, code="mineru_base_url_missing", message="MinerU base URL is not configured.")
        url = settings.integration_mineru_base_url
        if url.endswith("/"):
            url = url.rstrip("/")
        if url.endswith("/api/v4") or url.endswith("/api/v4/"):
            url = _join_url(url, "/extract/task")
        elif url.endswith("/extract/task"):
            pass
        else:
            url = _join_url(url, settings.integration_mineru_parse_path)

        uploaded_key: str | None = None
        bucket = None

        def upload_sample_to_oss() -> dict[str, Any]:
            nonlocal uploaded_key, bucket
            self._require(
                settings.oss_access_key_id and settings.oss_access_key_secret and settings.oss_bucket and settings.oss_endpoint,
                code="oss_config_missing",
                message="OSS configuration is required for MinerU signed URL verification.",
            )
            try:
                from oss2 import Auth, Bucket
            except ModuleNotFoundError as exc:  # pragma: no cover - depends on environment
                raise VerificationError("oss_sdk_missing", "Python package `oss2` is not installed.") from exc

            endpoint = (settings.oss_endpoint or "").replace("https://", "").replace("http://", "")
            auth = Auth(settings.oss_access_key_id, settings.oss_access_key_secret)
            bucket = Bucket(auth, endpoint, settings.oss_bucket)
            uploaded_key = f"{settings.oss_key_prefix.strip('/')}/integration-verification/mineru-{uuid4().hex}.pdf"
            payload = self._sample_pdf_bytes()
            result = bucket.put_object(uploaded_key, payload, headers={"Content-Type": "application/pdf"})
            if result.status not in {200, 201}:
                raise VerificationError("oss_upload_failed", f"Unexpected OSS upload status for MinerU seed file: {result.status}")
            signed_url = bucket.sign_url("GET", uploaded_key, 15 * 60)
            return {
                "objectKey": uploaded_key,
                "signedUrlPrefix": signed_url.split("?", 1)[0],
                "sizeBytes": len(payload),
                "sourceUrl": signed_url,
            }

        def parse_document() -> dict[str, Any]:
            headers = {}
            if settings.integration_mineru_api_key:
                headers["Authorization"] = f"Bearer {settings.integration_mineru_api_key}"
            oss_seed = upload_sample_to_oss()
            source_url = oss_seed["sourceUrl"]
            payload = {
                "url": source_url,
                "model_version": "vlm",
            }
            with httpx.Client(timeout=settings.integration_http_timeout_seconds) as client:
                response = client.post(url, headers={**headers, "Content-Type": "application/json"}, json=payload)
            if response.status_code >= 400:
                raise VerificationError("mineru_http_error", f"MinerU returned HTTP {response.status_code}")
            response_payload = response.json()
            if response_payload.get("code") not in {0, "0", None}:
                raise VerificationError("mineru_task_rejected", f"MinerU rejected task: {response_payload.get('msg') or response_payload.get('message') or 'unknown error'}")
            data = response_payload.get("data")
            if not data:
                raise VerificationError("mineru_data_missing", "MinerU response does not include task data.")
            task_reference = None
            if isinstance(data, dict):
                task_reference = data.get("task_id") or data.get("id") or data.get("extract_id")
            return {
                "responseKeys": list(response_payload.keys())[:6],
                "taskReference": task_reference or "accepted",
                "usedUrlHost": source_url.split("/", 3)[2] if "://" in source_url else "unknown",
            }

        try:
            recorder.run_step("parse", parse_document, success_summary="Submitted an OSS-hosted PDF URL to MinerU and received an accepted task response.")
            return recorder.finalize(status="passed", attempts=1, summary="MinerU task submission verification passed.")
        finally:
            if bucket is not None and uploaded_key is not None:
                try:
                    bucket.delete_object(uploaded_key)
                except Exception:
                    pass

    def _sample_pdf_bytes(self) -> bytes:
        return (
            b"%PDF-1.4\n"
            b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
            b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 144]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
            b"4 0 obj<</Length 49>>stream\n"
            b"BT /F1 18 Tf 36 96 Td (OfferSteady MinerU Test) Tj ET\n"
            b"endstream\n"
            b"endobj\n"
            b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
            b"xref\n0 6\n0000000000 65535 f \n0000000010 00000 n \n0000000053 00000 n \n0000000110 00000 n \n0000000236 00000 n \n0000000335 00000 n \n"
            b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n405\n%%EOF\n"
        )


class OpenAICompatibleChatVerifier(BaseVerifier):
    item_id = "qwen_chat"
    title = "Qwen Chat Test"
    provider_name = "qwen-compatible"

    def verify(self, context: VerificationContext) -> VerificationItemResult:
        recorder = VerificationItemRecorder(context=context, item_id=self.item_id, title=self.title, provider_name=self.provider_name)
        settings = context.settings
        self._require(settings.chat_qwen_base_url and settings.chat_qwen_api_key, code="chat_config_missing", message="Qwen chat base URL or API key is not configured.")
        url = _join_url(settings.chat_qwen_base_url, "/chat/completions")

        def request_chat() -> dict[str, Any]:
            payload = {
                "model": settings.chat_qwen_model,
                "stream": False,
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": "You are a deterministic integration test assistant."},
                    {"role": "user", "content": "请用一句话回复：面试稳集成测试通过。"},
                ],
            }
            with httpx.Client(timeout=settings.integration_http_timeout_seconds) as client:
                response = client.post(url, headers={"Authorization": f"Bearer {settings.chat_qwen_api_key}"}, json=payload)
            if response.status_code >= 400:
                raise VerificationError("chat_http_error", f"Qwen chat returned HTTP {response.status_code}")
            body = response.json()
            text = _extract_path(body, "choices.0.message.content") if isinstance(body.get("choices"), list) else None
            text = text or _extract_first_text(body)
            if not text:
                raise VerificationError("chat_content_missing", "Qwen chat response does not contain assistant content.")
            usage = body.get("usage", {})
            return {"model": settings.chat_qwen_model, "responseExcerpt": _safe_excerpt(str(text)), "usage": _sanitize_payload(usage)}

        recorder.run_step("chat_completion", request_chat, success_summary="Sent a real chat completion request to the configured Qwen-compatible endpoint.")
        return recorder.finalize(status="passed", attempts=1, summary="Qwen chat verification passed.")


class OpenAICompatibleVisionVerifier(BaseVerifier):
    item_id = "qwen_vision"
    title = "Qwen Vision Test"
    provider_name = "qwen-vision-compatible"

    def verify(self, context: VerificationContext) -> VerificationItemResult:
        recorder = VerificationItemRecorder(context=context, item_id=self.item_id, title=self.title, provider_name=self.provider_name)
        settings = context.settings
        self._require(
            settings.screenshot_vision_base_url and settings.screenshot_vision_api_key,
            code="vision_config_missing",
            message="Qwen vision base URL or API key is not configured.",
        )
        url = _join_url(settings.screenshot_vision_base_url, "/chat/completions")

        def request_vision() -> dict[str, Any]:
            image_path = self._select_test_image()
            png_base64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
            payload = {
                "model": settings.screenshot_vision_model,
                "stream": False,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "请简述这张测试图片的内容。"},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{png_base64}"}},
                        ],
                    }
                ],
            }
            with httpx.Client(timeout=settings.integration_http_timeout_seconds) as client:
                response = client.post(url, headers={"Authorization": f"Bearer {settings.screenshot_vision_api_key}"}, json=payload)
            if response.status_code >= 400:
                raise VerificationError("vision_http_error", f"Qwen vision returned HTTP {response.status_code}")
            body = response.json()
            text = _extract_first_text(body)
            if not text:
                raise VerificationError("vision_content_missing", "Qwen vision response does not contain a readable content summary.")
            return {
                "model": settings.screenshot_vision_model,
                "responseExcerpt": _safe_excerpt(text),
                "imagePath": str(image_path),
                "imageBytes": image_path.stat().st_size,
            }

        recorder.run_step("vision_completion", request_vision, success_summary="Sent a multimodal image understanding request to the configured Qwen vision endpoint.")
        return recorder.finalize(status="passed", attempts=1, summary="Qwen vision verification passed.")

    def _select_test_image(self) -> Path:
        candidates = [
            Path("/Users/liyulong/Desktop/test.png"),
            Path("/Users/liyulong/Desktop/image.png"),
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        raise VerificationError("vision_test_image_missing", "No local vision test image was found for verification.")


class EmbeddingVerifier(BaseVerifier):
    item_id = "embedding"
    title = "Embedding Test"
    provider_name = "embedding-provider"

    def verify(self, context: VerificationContext) -> VerificationItemResult:
        recorder = VerificationItemRecorder(context=context, item_id=self.item_id, title=self.title, provider_name=self.provider_name)
        settings = context.settings
        self._require(settings.embedding_base_url and settings.embedding_api_key, code="embedding_config_missing", message="Embedding base URL or API key is not configured.")
        url = _join_url(settings.embedding_base_url, "/embeddings")

        def request_embedding() -> dict[str, Any]:
            payload = {"model": settings.embedding_model, "input": ["面试稳 Embedding 集成验证样本文本。"]}
            with httpx.Client(timeout=settings.integration_http_timeout_seconds) as client:
                response = client.post(url, headers={"Authorization": f"Bearer {settings.embedding_api_key}"}, json=payload)
            if response.status_code >= 400:
                raise VerificationError("embedding_http_error", f"Embedding endpoint returned HTTP {response.status_code}")
            body = response.json()
            embedding = None
            if isinstance(body.get("data"), list) and body["data"]:
                embedding = body["data"][0].get("embedding")
            if not isinstance(embedding, list) or not embedding:
                raise VerificationError("embedding_vector_missing", "Embedding response does not include a vector.")
            return {"model": settings.embedding_model, "dimensions": len(embedding)}

        recorder.run_step("embedding_request", request_embedding, success_summary="Requested a real embedding vector from the configured provider.")
        return recorder.finalize(status="passed", attempts=1, summary="Embedding verification passed.")


class RerankVerifier(BaseVerifier):
    item_id = "rerank"
    title = "Rerank Test"
    provider_name = "rerank-provider"

    def verify(self, context: VerificationContext) -> VerificationItemResult:
        recorder = VerificationItemRecorder(context=context, item_id=self.item_id, title=self.title, provider_name=self.provider_name)
        settings = context.settings
        self._require(settings.rerank_base_url and settings.rerank_api_key, code="rerank_config_missing", message="Rerank base URL or API key is not configured.")
        url = _join_url(settings.rerank_base_url, settings.rerank_api_path)

        def request_rerank() -> dict[str, Any]:
            payload = {
                "model": settings.rerank_model,
                "input": {
                    "query": "如何自我介绍？",
                    "documents": ["突出真实项目经历与结果。", "可以先讲天气。", "围绕岗位关键词组织答案。"],
                },
                "top_n": 2,
            }
            with httpx.Client(timeout=settings.integration_http_timeout_seconds) as client:
                response = client.post(url, headers={"Authorization": f"Bearer {settings.rerank_api_key}"}, json=payload)
            if response.status_code >= 400:
                raise VerificationError("rerank_http_error", f"Rerank endpoint returned HTTP {response.status_code}")
            body = response.json()
            results = body.get("results") or _extract_path(body, "output.results") or body.get("data") or []
            if not isinstance(results, list) or not results:
                raise VerificationError("rerank_results_missing", "Rerank response does not include scored results.")
            return {
                "model": settings.rerank_model,
                "resultCount": len(results),
                "topIndex": results[0].get("index") if isinstance(results[0], dict) else None,
            }

        recorder.run_step("rerank_request", request_rerank, success_summary="Requested a real rerank response from the configured provider.")
        return recorder.finalize(status="passed", attempts=1, summary="Rerank verification passed.")


class RealtimeAsrVerifier(BaseVerifier):
    item_id = "realtime_asr"
    title = "Realtime ASR Test"
    provider_name = "qwen-realtime-asr-compatible"

    def verify(self, context: VerificationContext) -> VerificationItemResult:
        recorder = VerificationItemRecorder(context=context, item_id=self.item_id, title=self.title, provider_name=self.provider_name)
        settings = context.settings
        ws_url = settings.realtime_asr_ws_url or settings.realtime_asr_base_url or "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"
        self._require(ws_url and settings.realtime_asr_api_key, code="realtime_asr_config_missing", message="Realtime ASR websocket URL or API key is not configured.")
        try:
            import websocket
        except ModuleNotFoundError as exc:  # pragma: no cover - depends on environment
            raise VerificationError("websocket_client_missing", "Python package `websocket-client` is not installed.") from exc

        def websocket_roundtrip() -> dict[str, Any]:
            model_name = settings.realtime_asr_model
            connect_url = ws_url
            if "model=" not in connect_url:
                separator = "&" if "?" in connect_url else "?"
                connect_url = f"{connect_url}{separator}{urlencode({'model': model_name})}"
            headers = [
                f"Authorization: Bearer {settings.realtime_asr_api_key}",
                "OpenAI-Beta: realtime=v1",
            ]
            websocket_client = websocket.create_connection(connect_url, header=headers, timeout=settings.integration_http_timeout_seconds)
            transcript_text = ""
            transcript_events = 0
            session_updated = False
            audio_source = "synthetic-tone"
            try:
                first_event = json.loads(websocket_client.recv())
                if first_event.get("type") == "error":
                    raise VerificationError("realtime_asr_session_error", _extract_first_text(first_event) or json.dumps(first_event, ensure_ascii=False))
                websocket_client.send(json.dumps({
                    "event_id": f"event_{uuid4().hex}",
                    "type": "session.update",
                    "session": {
                        "modalities": ["text"],
                        "input_audio_format": "pcm",
                        "sample_rate": 16000,
                        "input_audio_transcription": {
                            "language": "zh",
                        },
                        "turn_detection": None,
                    },
                }))
                audio_chunks, audio_source = self._audio_chunks_for_verification()
                for chunk in audio_chunks:
                    websocket_client.send(json.dumps({
                        "event_id": f"event_{uuid4().hex}",
                        "type": "input_audio_buffer.append",
                        "audio": base64.b64encode(chunk).decode("ascii"),
                    }))
                    time_module.sleep(0.1)
                websocket_client.send(json.dumps({"event_id": f"event_{uuid4().hex}", "type": "input_audio_buffer.commit"}))

                websocket_client.settimeout(max(10, context.settings.integration_http_timeout_seconds))
                for _ in range(60):
                    try:
                        message = json.loads(websocket_client.recv())
                    except websocket.WebSocketTimeoutException:
                        if transcript_text:
                            break
                        raise
                    event_type = message.get("type")
                    if event_type == "error":
                        raise VerificationError(
                            "realtime_asr_error_event",
                            _extract_path(message, "error.message") or _extract_first_text(message) or json.dumps(message, ensure_ascii=False),
                        )
                    if event_type == "session.updated":
                        session_updated = True
                    if event_type in {"conversation.item.input_audio_transcription.text", "conversation.item.input_audio_transcription.completed"}:
                        transcript_events += 1
                        transcript_text = (
                            message.get("transcript")
                            or message.get("text")
                            or message.get("stash")
                            or transcript_text
                        )
                    if event_type == "conversation.item.input_audio_transcription.completed":
                        break
            finally:
                try:
                    websocket_client.close()
                except Exception:
                    pass

            if not session_updated:
                raise VerificationError("realtime_asr_session_not_updated", "Realtime ASR session.update was not acknowledged by the server.")
            if transcript_text == "":
                raise VerificationError("realtime_asr_transcript_missing", "Realtime ASR websocket roundtrip did not return a completed transcript.")
            return {
                "model": model_name,
                "transcriptExcerpt": _safe_excerpt(transcript_text),
                "sessionUpdated": session_updated,
                "transcriptEvents": transcript_events,
                "audioSource": audio_source,
            }

        recorder.run_step("websocket_roundtrip", websocket_roundtrip, success_summary="Connected to the realtime ASR websocket and received a transcript event.")
        return recorder.finalize(status="passed", attempts=1, summary="Realtime ASR verification passed.")

    def _sample_pcm16_audio(self, *, duration_samples: int = 1600) -> bytes:
        sample_rate = 16000
        frames = bytearray()
        for index in range(duration_samples):
            amplitude = int(12000 * math.sin(2 * math.pi * 440 * index / sample_rate))
            frames.extend(int(amplitude).to_bytes(2, byteorder="little", signed=True))
        return bytes(frames)

    def _audio_chunks_for_verification(self) -> tuple[list[bytes], str]:
        spoken = self._synthesized_speech_pcm_chunks()
        if spoken is not None:
            return spoken, "synthesized-speech"
        fallback = self._sample_pcm16_audio(duration_samples=16000)
        return [fallback[index:index + 3200] for index in range(0, len(fallback), 3200)], "synthetic-tone"

    def _synthesized_speech_pcm_chunks(self) -> list[bytes] | None:
        say_path = Path("/usr/bin/say")
        afconvert_path = Path("/usr/bin/afconvert")
        if not say_path.exists() or not afconvert_path.exists():
            return None

        phrase = "你好，这是面试稳实时语音识别测试。"
        with NamedTemporaryFile(suffix=".aiff", delete=False) as aiff_file:
            aiff_path = Path(aiff_file.name)
        with NamedTemporaryFile(suffix=".wav", delete=False) as wav_file:
            wav_path = Path(wav_file.name)
        try:
            subprocess.run([str(say_path), "-o", str(aiff_path), phrase], check=True, capture_output=True)
            subprocess.run(
                [str(afconvert_path), "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", str(aiff_path), str(wav_path)],
                check=True,
                capture_output=True,
            )
            with wave.open(str(wav_path), "rb") as handle:
                if handle.getnchannels() != 1 or handle.getsampwidth() != 2 or handle.getframerate() != 16000:
                    return None
                chunks: list[bytes] = []
                while True:
                    frames = handle.readframes(1600)
                    if not frames:
                        break
                    chunks.append(frames)
                return chunks or None
        except Exception:
            return None
        finally:
            for temp_path in (aiff_path, wav_path):
                try:
                    temp_path.unlink(missing_ok=True)
                except Exception:
                    pass


class DatabaseVerifier(BaseVerifier):
    item_id = "postgresql"
    title = "PostgreSQL Test"
    provider_name = "postgresql"

    def verify(self, context: VerificationContext) -> VerificationItemResult:
        recorder = VerificationItemRecorder(context=context, item_id=self.item_id, title=self.title, provider_name=self.provider_name)
        settings = context.settings
        self._require(settings.database_url, code="database_url_missing", message="Database URL is not configured.")

        def select_one() -> dict[str, Any]:
            with psycopg.connect(
                settings.database_url,
                connect_timeout=settings.database_connect_timeout_seconds,
                application_name=f"{settings.database_application_name}-integration-verify",
            ) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("select current_database(), current_user, version()")
                    database_name, current_user, version = cursor.fetchone()
            return {"database": database_name, "user": current_user, "versionExcerpt": _safe_excerpt(str(version), 60)}

        recorder.run_step("connect", select_one, success_summary="Connected to PostgreSQL and executed a basic read query.")
        return recorder.finalize(status="passed", attempts=1, summary="PostgreSQL verification passed.")


class PgvectorVerifier(BaseVerifier):
    item_id = "pgvector"
    title = "pgvector Test"
    provider_name = "pgvector"

    def verify(self, context: VerificationContext) -> VerificationItemResult:
        recorder = VerificationItemRecorder(context=context, item_id=self.item_id, title=self.title, provider_name=self.provider_name)
        settings = context.settings
        self._require(settings.database_url, code="database_url_missing", message="Database URL is not configured.")

        def extension_check() -> dict[str, Any]:
            with psycopg.connect(
                settings.database_url,
                connect_timeout=settings.database_connect_timeout_seconds,
                application_name=f"{settings.database_application_name}-pgvector-verify",
            ) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("select extname from pg_extension where extname = %s", (settings.pgvector_extension_name,))
                    row = cursor.fetchone()
                    if row is None:
                        raise VerificationError("pgvector_extension_missing", "pgvector extension is not installed.")
                    cursor.execute("create temporary table if not exists offersteady_verify_vectors (id text, embedding vector(3))")
                    cursor.execute("delete from offersteady_verify_vectors")
                    cursor.execute("insert into offersteady_verify_vectors (id, embedding) values (%s, %s::vector), (%s, %s::vector)", ("a", "[0.1,0.2,0.3]", "b", "[0.2,0.1,0.0]"))
                    cursor.execute(
                        "select id, embedding <-> %s::vector as distance from offersteady_verify_vectors order by embedding <-> %s::vector limit 1",
                        ("[0.1,0.2,0.29]", "[0.1,0.2,0.29]"),
                    )
                    best_id, best_distance = cursor.fetchone()
            return {"extension": settings.pgvector_extension_name, "nearestId": best_id, "distance": float(best_distance)}

        recorder.run_step("vector_query", extension_check, success_summary="Validated pgvector extension presence and executed a similarity query.")
        return recorder.finalize(status="passed", attempts=1, summary="pgvector verification passed.")


class SmsAuthenticationVerifier(BaseVerifier):
    item_id = "sms_auth"
    title = "SMS Authentication Provider Readiness"
    provider_name = "aliyun-dypnsapi-or-fake"

    def verify(self, context: VerificationContext) -> VerificationItemResult:
        recorder = VerificationItemRecorder(context=context, item_id=self.item_id, title=self.title, provider_name=self.provider_name)
        settings = context.settings

        def config_check() -> dict[str, Any]:
            if settings.auth_sms_provider_mode == "aliyun":
                self._require(settings.auth_sms_aliyun_access_key_id and settings.auth_sms_aliyun_access_key_secret, code="sms_credentials_missing", message="Aliyun SMS credentials are not configured.")
                self._require(settings.auth_sms_aliyun_sign_name and settings.auth_sms_aliyun_template_code, code="sms_template_missing", message="Aliyun SMS sign name or template code is not configured.")
            return {
                "mode": settings.auth_sms_provider_mode,
                "endpoint": settings.auth_sms_aliyun_endpoint if settings.auth_sms_provider_mode == "aliyun" else "fake",
                "testPhoneConfigured": bool(settings.auth_sms_test_phone_number),
            }

        recorder.run_step("sms_config", config_check, success_summary="SMS auth configuration is readable.")

        def probe_policy() -> dict[str, Any]:
            if settings.auth_sms_provider_mode != "aliyun":
                return {"provider": "fake", "fakeCodeConfigured": bool(settings.auth_sms_fake_code)}
            if not settings.auth_sms_test_phone_number:
                return {"provider": "aliyun", "realSendSkipped": True, "reason": "OFFERSTEADY_AUTH_SMS_TEST_PHONE_NUMBER is not configured"}
            return {"provider": "aliyun", "realSendSkipped": True, "reason": "Real SMS sending must be triggered by a dedicated manual test, not the default verifier"}

        recorder.run_step("sms_probe_policy", probe_policy, success_summary="SMS auth probe policy is safe.")
        return recorder.finalize(status="passed", attempts=1, summary="SMS authentication provider configuration is ready.")


class IntegrationVerificationRunner:
    def __init__(self, *, settings: Settings, logger: logging.Logger, verifiers: dict[str, IntegrationVerifier]) -> None:
        self.settings = settings
        self.logger = logger
        self.verifiers = verifiers

    def run(self, *, selected_items: list[str] | None = None) -> IntegrationReport:
        chosen = selected_items or list(self.verifiers.keys())
        unknown = [item for item in chosen if item not in self.verifiers]
        if unknown:
            raise VerificationError("unknown_items", f"Unknown verification items: {', '.join(unknown)}")
        report_id = f"ivr-{uuid4().hex}"
        started_iso = _utc_now_iso()
        started_perf = perf_counter()
        results: list[VerificationItemResult] = []
        with TemporaryDirectory(prefix="offersteady-integration-") as tmp_dir:
            context = VerificationContext(settings=self.settings, logger=self.logger, temp_dir=Path(tmp_dir))
            for item_id in chosen:
                verifier = self.verifiers[item_id]
                attempts = 0
                while True:
                    attempts += 1
                    try:
                        result = verifier.verify(context)
                        result.attempts = attempts
                        results.append(result)
                        break
                    except RecordedVerificationFailure as exc:
                        if exc.retryable and attempts <= self.settings.integration_retry_attempts:
                            log_event(
                                self.logger,
                                logging.WARNING,
                                settings=self.settings,
                                event="integration_verification.retrying",
                                feature="integration-verification",
                                action="retry",
                                provider=verifier.provider_name,
                                item_id=item_id,
                                attempt=attempts,
                                error_code=exc.code,
                                error_message=exc.message,
                            )
                            continue
                        results.append(exc.recorder.finalize(status="failed", attempts=attempts, summary=f"Verification failed: {exc.message}"))
                        break
                    except VerificationError as exc:
                        if exc.retryable and attempts <= self.settings.integration_retry_attempts:
                            log_event(
                                self.logger,
                                logging.WARNING,
                                settings=self.settings,
                                event="integration_verification.retrying",
                                feature="integration-verification",
                                action="retry",
                                provider=verifier.provider_name,
                                item_id=item_id,
                                attempt=attempts,
                                error_code=exc.code,
                                error_message=exc.message,
                            )
                            continue
                        results.append(
                            VerificationItemResult(
                                item_id=item_id,
                                title=verifier.title,
                                provider_name=verifier.provider_name,
                                status="failed",
                                started_at=_utc_now_iso(),
                                completed_at=_utc_now_iso(),
                                duration_ms=0,
                                attempts=attempts,
                                steps=[],
                                summary=f"Verification failed before starting steps: {exc.message}",
                            )
                        )
                        break
        duration_ms = int((perf_counter() - started_perf) * 1000)
        overall_status = "failed" if any(item.status == "failed" for item in results) else "passed"
        return IntegrationReport(
            report_id=report_id,
            environment_label=self.settings.integration_environment_label,
            started_at=started_iso,
            completed_at=_utc_now_iso(),
            duration_ms=duration_ms,
            overall_status=overall_status,
            selected_items=chosen,
            results=results,
        )


class IntegrationReportWriter:
    def __init__(self, *, output_dir: Path) -> None:
        self.output_dir = output_dir

    def write(self, report: IntegrationReport) -> dict[str, Path]:
        report_dir = self.output_dir / report.report_id
        report_dir.mkdir(parents=True, exist_ok=True)
        json_path = report_dir / "report.json"
        markdown_path = report_dir / "report.md"
        json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        markdown_path.write_text(self._to_markdown(report), encoding="utf-8")
        return {"json": json_path, "markdown": markdown_path}

    def _to_markdown(self, report: IntegrationReport) -> str:
        lines = [
            "# Integration Report",
            "",
            f"- Report ID: `{report.report_id}`",
            f"- Environment: `{report.environment_label}`",
            f"- Overall Status: **{report.overall_status}**",
            f"- Started At: `{report.started_at}`",
            f"- Completed At: `{report.completed_at}`",
            f"- Duration: `{report.duration_ms} ms`",
            f"- Selected Items: {', '.join(report.selected_items)}",
            "",
            "## Results",
            "",
        ]
        for item in report.results:
            lines.extend([
                f"### {item.title}",
                "",
                f"- Item ID: `{item.item_id}`",
                f"- Provider: `{item.provider_name}`",
                f"- Status: **{item.status}**",
                f"- Attempts: `{item.attempts}`",
                f"- Duration: `{item.duration_ms} ms`",
                f"- Summary: {item.summary}",
                "",
            ])
            if item.steps:
                lines.append("| Step | Status | Duration (ms) | Summary |")
                lines.append("| --- | --- | ---: | --- |")
                for step in item.steps:
                    lines.append(f"| {step.name} | {step.status} | {step.duration_ms} | {step.summary} |")
                lines.append("")
        return "\n".join(lines)


def build_default_verifiers() -> dict[str, IntegrationVerifier]:
    verifiers: list[IntegrationVerifier] = [
        OssVerifier(),
        SmsAuthenticationVerifier(),
        MineruVerifier(),
        OpenAICompatibleChatVerifier(),
        OpenAICompatibleVisionVerifier(),
        EmbeddingVerifier(),
        RerankVerifier(),
        RealtimeAsrVerifier(),
        DatabaseVerifier(),
        PgvectorVerifier(),
    ]
    return {verifier.item_id: verifier for verifier in verifiers}


def run_integration_verification(*, settings: Settings | None = None, selected_items: list[str] | None = None) -> tuple[IntegrationReport, dict[str, Path]]:
    runtime_settings = settings or get_settings()
    runtime_logger = configure_logging(runtime_settings)
    runner = IntegrationVerificationRunner(settings=runtime_settings, logger=runtime_logger, verifiers=build_default_verifiers())
    report = runner.run(selected_items=selected_items)
    writer = IntegrationReportWriter(output_dir=Path(runtime_settings.integration_report_output_dir))
    paths = writer.write(report)
    return report, paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run OfferSteady third-party integration verification.")
    parser.add_argument("--item", action="append", default=None, help="Run only the selected verification item. Repeatable.")
    parser.add_argument("--list", action="store_true", help="List available verification items and exit.")
    args = parser.parse_args(argv)

    verifiers = build_default_verifiers()
    if args.list:
        for key, verifier in verifiers.items():
            print(f"{key}: {verifier.title} ({verifier.provider_name})")
        return 0

    report, paths = run_integration_verification(selected_items=args.item)
    print(json.dumps({
        "reportId": report.report_id,
        "overallStatus": report.overall_status,
        "selectedItems": report.selected_items,
        "jsonReport": str(paths["json"]),
        "markdownReport": str(paths["markdown"]),
    }, ensure_ascii=False, indent=2))
    return 0 if report.overall_status == "passed" else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
