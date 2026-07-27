from dataclasses import replace

from app.ports.screenshot_answer import RemoteScreenshotCaptureRequest
from app.services.screenshot_answer_repository import InMemoryScreenshotAnswerRepository


def test_processing_remote_capture_request_is_not_returned_for_capture_again() -> None:
    repository = InMemoryScreenshotAnswerRepository()
    requested = RemoteScreenshotCaptureRequest(
        request_id="shortcut-request-1",
        session_id="session-1",
        owner_user_id="user-1",
        device_id="device-1",
        manual_code="123456",
        instruction="快捷键截图回答",
        status="requested",
        created_at_ms=1,
        updated_at_ms=1,
    )
    repository.save_remote_capture_request(requested)

    assert repository.get_next_pending_remote_capture_request(
        device_id="device-1",
        manual_code="123456",
    ) == requested

    repository.save_remote_capture_request(
        replace(requested, status="processing", stage="claimed", updated_at_ms=2),
    )

    assert repository.get_next_pending_remote_capture_request(
        device_id="device-1",
        manual_code="123456",
    ) is None
