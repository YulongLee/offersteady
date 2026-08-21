from __future__ import annotations

import json
import time
from dataclasses import asdict, replace

from redis import Redis

from app.core.config import Settings
from app.ports.chat import ChatAnswerChunk, ChatAnswerTaskRecord, ChatRepository
from app.ports.screenshot_answer import (
    ConfirmedScreenshotUpload,
    RemoteScreenshotCaptureRequest,
    ScreenshotAnswerRepository,
    ScreenshotAnswerTaskRecord,
    ScreenshotTimingTelemetry,
)


class _RedisRuntimeStore:
    def __init__(self, settings: Settings, *, redis_client=None) -> None:  # noqa: ANN001
        if not settings.redis_url and redis_client is None:
            raise ValueError("redis_url_required")
        self.redis = redis_client or Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_timeout=settings.redis_socket_timeout_seconds,
            socket_connect_timeout=settings.redis_socket_timeout_seconds,
            health_check_interval=15,
        )
        self.ttl = max(300, settings.live_task_runtime_ttl_seconds)
        self.stale_ms = max(30, settings.live_task_stale_seconds) * 1000
        self.redis.ping()

    def _save(self, *, key: str, payload: dict[str, object], index_key: str, score: int, member: str) -> None:
        pipe = self.redis.pipeline(transaction=True)
        pipe.set(key, json.dumps(payload, ensure_ascii=True, separators=(",", ":")), ex=self.ttl)
        pipe.zadd(index_key, {member: score})
        pipe.expire(index_key, self.ttl)
        pipe.execute()

    def _load(self, key: str) -> dict[str, object] | None:
        raw = self.redis.get(key)
        return json.loads(raw) if raw else None

    def _lock(self, key: str):  # noqa: ANN202
        return self.redis.lock(f"{key}:lock", timeout=5, blocking_timeout=2)


class RedisChatRepository(_RedisRuntimeStore, ChatRepository):
    _prefix = "offersteady:live:chat:v1"

    def save_task(self, task: ChatAnswerTaskRecord) -> ChatAnswerTaskRecord:
        key = f"{self._prefix}:task:{task.task_id}"
        with self._lock(key):
            payload = self._load(key)
            existing = self._decode(payload) if payload else None
            if existing is not None:
                if existing.status in {"completed", "failed", "cancelled"} and task.status not in {"completed", "failed", "cancelled"}:
                    return existing
                if task.updated_at_ms < existing.updated_at_ms:
                    return existing
            self._save(
                key=key, payload=asdict(task),
                index_key=f"{self._prefix}:session:{task.session_id}",
                score=task.created_at_ms, member=task.task_id,
            )
            return replace(task)

    def get_task(self, task_id: str) -> ChatAnswerTaskRecord | None:
        payload = self._load(f"{self._prefix}:task:{task_id}")
        task = self._decode(payload) if payload else None
        if task is not None and task.status in {"queued", "streaming"} and int(time.time() * 1000) - task.updated_at_ms > self.stale_ms:
            task = replace(
                task, status="failed", error_code="runtime_task_interrupted",
                error_message="回答任务因服务重启中断，请重新发起。",
                updated_at_ms=int(time.time() * 1000), completed_at_ms=int(time.time() * 1000),
            )
            self._save(
                key=f"{self._prefix}:task:{task.task_id}", payload=asdict(task),
                index_key=f"{self._prefix}:session:{task.session_id}",
                score=task.created_at_ms, member=task.task_id,
            )
            return task
        return task

    def list_tasks_for_session(self, *, session_id: str) -> list[ChatAnswerTaskRecord]:
        ids = self.redis.zrange(f"{self._prefix}:session:{session_id}", 0, -1)
        return [item for task_id in ids if (item := self.get_task(task_id)) is not None]

    @staticmethod
    def _decode(payload: dict[str, object]) -> ChatAnswerTaskRecord:
        data = dict(payload)
        data["chunks"] = [ChatAnswerChunk(**item) for item in data.get("chunks", [])]
        return ChatAnswerTaskRecord(**data)


class RedisScreenshotAnswerRepository(_RedisRuntimeStore, ScreenshotAnswerRepository):
    _prefix = "offersteady:live:screenshot:v1"

    def save_task(self, task: ScreenshotAnswerTaskRecord) -> ScreenshotAnswerTaskRecord:
        key = f"{self._prefix}:task:{task.task_id}"
        with self._lock(key):
            payload = self._load(key)
            existing = self._decode_task(payload) if payload else None
            if existing is not None:
                if existing.status in {"completed", "failed", "cancelled"} and task.status not in {"completed", "failed", "cancelled"}:
                    return existing
                if task.updated_at_ms < existing.updated_at_ms:
                    return existing
            self._save(
                key=key, payload=asdict(task),
                index_key=f"{self._prefix}:session:{task.session_id}:tasks",
                score=task.created_at_ms, member=task.task_id,
            )
            return replace(task)

    def get_task(self, task_id: str) -> ScreenshotAnswerTaskRecord | None:
        payload = self._load(f"{self._prefix}:task:{task_id}")
        task = self._decode_task(payload) if payload else None
        if task is not None and task.status in {"queued", "processing-images", "vision-running", "streaming"} and int(time.time() * 1000) - task.updated_at_ms > self.stale_ms:
            now_ms = int(time.time() * 1000)
            task = replace(
                task, status="failed", error_code="runtime_task_interrupted",
                error_message="截图回答因服务重启中断，请重新发起。",
                updated_at_ms=now_ms, completed_at_ms=now_ms,
            )
            self._save(
                key=f"{self._prefix}:task:{task.task_id}", payload=asdict(task),
                index_key=f"{self._prefix}:session:{task.session_id}:tasks",
                score=task.created_at_ms, member=task.task_id,
            )
            return task
        return task

    def list_tasks_for_session(self, *, session_id: str) -> list[ScreenshotAnswerTaskRecord]:
        ids = self.redis.zrange(f"{self._prefix}:session:{session_id}:tasks", 0, -1)
        return [item for task_id in ids if (item := self.get_task(task_id)) is not None]

    def save_upload(self, upload: ConfirmedScreenshotUpload) -> ConfirmedScreenshotUpload:
        key = f"{self._prefix}:upload:{upload.image_id}"
        with self._lock(key):
            payload = self._load(key)
            existing = ConfirmedScreenshotUpload(**payload) if payload else None
            if existing is not None and existing.status == "deleted" and upload.status != "deleted":
                return existing
            self._save(
                key=key, payload=asdict(upload),
                index_key=f"{self._prefix}:session:{upload.session_id}:uploads",
                score=upload.uploaded_at_ms, member=upload.image_id,
            )
            return replace(upload)

    def get_upload(self, image_id: str) -> ConfirmedScreenshotUpload | None:
        payload = self._load(f"{self._prefix}:upload:{image_id}")
        return ConfirmedScreenshotUpload(**payload) if payload else None

    def list_uploads_for_session(self, *, session_id: str) -> list[ConfirmedScreenshotUpload]:
        ids = self.redis.zrange(f"{self._prefix}:session:{session_id}:uploads", 0, -1)
        return [item for image_id in ids if (item := self.get_upload(image_id)) is not None]

    def save_remote_capture_request(self, request: RemoteScreenshotCaptureRequest) -> RemoteScreenshotCaptureRequest:
        key = f"{self._prefix}:request:{request.request_id}"
        with self._lock(key):
            payload = self._load(key)
            existing = self._decode_request(payload) if payload else None
            if existing is not None:
                if existing.status in {"completed", "failed", "cancelled"} and request.status not in {"completed", "failed", "cancelled"}:
                    return existing
                if request.updated_at_ms < existing.updated_at_ms:
                    return existing
            device_index = f"{self._prefix}:device:{request.device_id}:{request.manual_code}:requests"
            self._save(
                key=key, payload=asdict(request),
                index_key=f"{self._prefix}:session:{request.session_id}:requests",
                score=request.created_at_ms, member=request.request_id,
            )
            self.redis.zadd(device_index, {request.request_id: request.created_at_ms})
            self.redis.expire(device_index, self.ttl)
            return replace(request)

    def get_remote_capture_request(self, request_id: str) -> RemoteScreenshotCaptureRequest | None:
        payload = self._load(f"{self._prefix}:request:{request_id}")
        return self._decode_request(payload) if payload else None

    def list_remote_capture_requests_for_session(self, *, session_id: str) -> list[RemoteScreenshotCaptureRequest]:
        ids = self.redis.zrange(f"{self._prefix}:session:{session_id}:requests", 0, -1)
        return [item for request_id in ids if (item := self.get_remote_capture_request(request_id)) is not None]

    def get_next_pending_remote_capture_request(self, *, device_id: str, manual_code: str) -> RemoteScreenshotCaptureRequest | None:
        index = f"{self._prefix}:device:{device_id}:{manual_code}:requests"
        for request_id in self.redis.zrange(index, 0, -1):
            request = self.get_remote_capture_request(request_id)
            if request is not None and request.status == "requested":
                return request
        return None

    @staticmethod
    def _decode_task(payload: dict[str, object]) -> ScreenshotAnswerTaskRecord:
        data = dict(payload)
        data["chunks"] = [ChatAnswerChunk(**item) for item in data.get("chunks", [])]
        data["telemetry"] = ScreenshotTimingTelemetry(**data.get("telemetry", {}))
        return ScreenshotAnswerTaskRecord(**data)

    @staticmethod
    def _decode_request(payload: dict[str, object]) -> RemoteScreenshotCaptureRequest:
        data = dict(payload)
        data["telemetry"] = ScreenshotTimingTelemetry(**data.get("telemetry", {}))
        return RemoteScreenshotCaptureRequest(**data)
