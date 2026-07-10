from __future__ import annotations

from dataclasses import replace

from app.ports.screenshot_answer import ConfirmedScreenshotUpload, RemoteScreenshotCaptureRequest, ScreenshotAnswerRepository, ScreenshotAnswerTaskRecord


class InMemoryScreenshotAnswerRepository(ScreenshotAnswerRepository):
    def __init__(self) -> None:
        self.tasks: dict[str, ScreenshotAnswerTaskRecord] = {}
        self.uploads: dict[str, ConfirmedScreenshotUpload] = {}
        self.remote_capture_requests: dict[str, RemoteScreenshotCaptureRequest] = {}

    def save_task(self, task: ScreenshotAnswerTaskRecord) -> ScreenshotAnswerTaskRecord:
        stored = replace(task)
        self.tasks[stored.task_id] = stored
        return replace(stored)

    def get_task(self, task_id: str) -> ScreenshotAnswerTaskRecord | None:
        record = self.tasks.get(task_id)
        return replace(record) if record else None

    def list_tasks_for_session(self, *, session_id: str) -> list[ScreenshotAnswerTaskRecord]:
        items = [task for task in self.tasks.values() if task.session_id == session_id]
        return [replace(item) for item in sorted(items, key=lambda item: item.created_at_ms)]

    def save_upload(self, upload: ConfirmedScreenshotUpload) -> ConfirmedScreenshotUpload:
        stored = replace(upload)
        self.uploads[stored.image_id] = stored
        return replace(stored)

    def get_upload(self, image_id: str) -> ConfirmedScreenshotUpload | None:
        record = self.uploads.get(image_id)
        return replace(record) if record else None

    def list_uploads_for_session(self, *, session_id: str) -> list[ConfirmedScreenshotUpload]:
        items = [item for item in self.uploads.values() if item.session_id == session_id]
        return [replace(item) for item in sorted(items, key=lambda item: item.uploaded_at_ms)]

    def save_remote_capture_request(self, request: RemoteScreenshotCaptureRequest) -> RemoteScreenshotCaptureRequest:
        stored = replace(request)
        self.remote_capture_requests[stored.request_id] = stored
        return replace(stored)

    def get_remote_capture_request(self, request_id: str) -> RemoteScreenshotCaptureRequest | None:
        record = self.remote_capture_requests.get(request_id)
        return replace(record) if record else None

    def get_next_pending_remote_capture_request(self, *, device_id: str, manual_code: str) -> RemoteScreenshotCaptureRequest | None:
        matches = [
            request for request in self.remote_capture_requests.values()
            if request.device_id == device_id
            and request.manual_code == manual_code
            and request.status in {"requested", "processing"}
        ]
        if not matches:
            return None
        request = sorted(matches, key=lambda item: item.created_at_ms)[0]
        return replace(request)
