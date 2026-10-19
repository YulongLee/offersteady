from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.ports.screenshot_answer import RemoteScreenshotCaptureRequest, ScreenshotAnswerTaskRecord
from app.schemas.screenshot_answer import CreateRemoteScreenshotCaptureRequest
from app.services.redis_live_task_repositories import RedisScreenshotAnswerRepository
from app.services.screenshot_answer_repository import InMemoryScreenshotAnswerRepository
from test_redis_live_task_repositories import FakeRedis
from test_screenshot_inline_delivery import (
    SYNTHETIC_PNG, CapturingVisionGateway, StreamingVisionGateway, build_service,
)


class BillingProbe:
    def __init__(self, *, insufficient=False):
        self.insufficient = insufficient
        self.reserved = []
        self.settled = []
        self.released = []

    def reserve_usage(self, **kwargs):
        self.reserved.append(kwargs)
        return SimpleNamespace(status="insufficient_balance" if self.insufficient else "reserved")

    def settle_usage(self, **kwargs):
        self.settled.append(kwargs)

    def release_usage(self, **kwargs):
        self.released.append(kwargs)


class CountingVision(CapturingVisionGateway):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.calls = 0

    def analyze(self, **kwargs):
        self.calls += 1
        return super().analyze(**{key: kwargs[key] for key in ("session_id", "instruction", "images", "attempt")})


def service_fixture(*, insufficient=False, fail_vision=False):
    service, storage, repository, upload_port, _ = build_service(delivery_mode="inline")
    service.session_service.session.session_mode = "written"
    service.billing_service = BillingProbe(insufficient=insufficient)
    service.vision_gateway = CountingVision(fail=fail_vision)
    return service, storage, repository, upload_port


def capture(service, *, filename="synthetic.png", user_id="synthetic-user", session_id="synthetic-session"):
    request = service.create_remote_capture_request(
        user_id=user_id, session_id=session_id, device_id="synthetic-device",
        manual_code="654321", instruction="", capture_only=True,
    )
    request, task = service.complete_remote_capture_request(
        request_id=request.request_id, device_id=request.device_id, manual_code=request.manual_code,
        filename=filename, content_type="image/png", payload=SYNTHETIC_PNG,
    )
    assert task is None
    assert request.capture_only and request.status == "completed" and request.captured_image_id
    return request


def batch(service, requests, **kwargs):
    return service.create_batch_answer_request(
        user_id="synthetic-user", session_id="synthetic-session",
        capture_request_ids=[item.request_id for item in requests], instruction="", **kwargs,
    )


def test_capture_only_is_compatible_and_has_no_generation_history_or_usage():
    service, storage, repository, upload_port = service_fixture()
    assert CreateRemoteScreenshotCaptureRequest(userId="synthetic-user").capture_only is False
    assert service.validation_policy()["supportsCaptureOnly"] is True
    request = capture(service)
    assert upload_port.load_image_bytes(image=repository.get_upload(request.captured_image_id))
    assert not repository.tasks and not service.session_service.contexts
    assert service.vision_gateway.calls == 0
    assert not service.billing_service.reserved and not service.billing_service.settled
    assert not storage.saved


def test_four_capture_limit_includes_inflight_requests_and_clearing_releases_slot():
    service, _, repository, upload_port = service_fixture()
    ready = capture(service)
    for _ in range(3):
        service.create_remote_capture_request(
            user_id="synthetic-user", session_id="synthetic-session", device_id="synthetic-device",
            manual_code="654321", instruction="", capture_only=True,
        )
    with pytest.raises(DomainRequestError, match="最多暂存"):
        service.create_remote_capture_request(
            user_id="synthetic-user", session_id="synthetic-session", device_id="synthetic-device",
            manual_code="654321", instruction="", capture_only=True,
        )
    cleared = service.cancel_remote_capture_request(user_id="synthetic-user", request_id=ready.request_id)
    assert cleared.status == "cancelled"
    assert repository.get_upload(ready.captured_image_id).status == "deleted"
    assert not upload_port.uploaded_images
    replacement = service.create_remote_capture_request(
        user_id="synthetic-user", session_id="synthetic-session", device_id="synthetic-device",
        manual_code="654321", instruction="", capture_only=True,
    )
    assert replacement.status == "requested"


def test_ordered_batch_is_one_task_one_charge_and_retries_return_original():
    service, _, repository, upload_port = service_fixture()
    first, second = capture(service, filename="page-1.png"), capture(service, filename="page-2.png")
    request, created = batch(service, [second, first])
    duplicate, created_again = batch(service, [second, first])
    assert created and not created_again and duplicate.request_id == request.request_id
    events = []
    service.complete_batch_answer_request_safely(request_id=request.request_id, on_transition=lambda req, task: events.append((req, task)))
    result = repository.get_remote_capture_request(request.request_id)
    assert result.status == "completed" and result.answer_task_id
    assert len(repository.tasks) == 1 and service.vision_gateway.calls == 1
    assert [image.filename for image in service.vision_gateway.images] == ["page-2.png", "page-1.png"]
    task = repository.get_task(result.answer_task_id)
    assert task.image_ids == [second.captured_image_id, first.captured_image_id]
    assert task.image_count == 2 and task.material_context_status == "not-used"
    assert task.material_provenance["noPersonalMaterialUsed"]
    assert len(service.billing_service.reserved) == len(service.billing_service.settled) == 1
    assert len(service.session_service.contexts) == 2 and not upload_port.uploaded_images
    assert events[0][0].answer_task_id == events[0][1].task_id
    completed_again, created_again = batch(service, [second, first])
    assert completed_again.request_id == result.request_id and not created_again
    service.complete_batch_answer_request_safely(request_id=request.request_id)
    assert service.vision_gateway.calls == 1


def test_concurrent_identical_and_overlapping_batches_cannot_double_consume():
    service, _, repository, _ = service_fixture()
    first, second = capture(service), capture(service)
    barrier = threading.Barrier(6)

    def submit(_):
        barrier.wait(timeout=5)
        return batch(service, [first, second])

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(submit, range(6)))
    assert sum(created for _, created in results) == 1
    assert len({request.request_id for request, _ in results}) == 1
    with pytest.raises(DomainRequestError, match="已提交"):
        batch(service, [first])
    assert len([item for item in repository.remote_capture_requests.values() if item.capture_request_ids]) == 1


@pytest.mark.parametrize("kind", ["duplicate", "empty", "too-many", "foreign-user", "foreign-session", "expired", "removed", "not-ready"])
def test_invalid_batch_does_no_model_or_billing_work(kind):
    service, _, repository, upload_port = service_fixture()
    source = capture(service)
    ids = [source.request_id]
    if kind == "duplicate": ids *= 2
    if kind == "empty": ids = []
    if kind == "too-many": ids *= 5
    if kind == "foreign-user": repository.save_remote_capture_request(replace(source, owner_user_id="someone-else"))
    if kind == "foreign-session": repository.save_remote_capture_request(replace(source, session_id="another-session"))
    if kind == "expired": upload_port._sweep_expired(now_ms=10**16)
    if kind == "removed": service.cancel_remote_capture_request(user_id="synthetic-user", request_id=source.request_id)
    if kind == "not-ready":
        source = service.create_remote_capture_request(user_id="synthetic-user", session_id="synthetic-session", device_id="synthetic-device", manual_code="654321", instruction="", capture_only=True)
        ids = [source.request_id]
    with pytest.raises(DomainRequestError):
        service.create_batch_answer_request(user_id="synthetic-user", session_id="synthetic-session", capture_request_ids=ids, instruction="")
    assert not repository.tasks and not service.billing_service.reserved
    assert service.vision_gateway.calls == 0


def test_cancel_racing_upload_releases_late_image_without_reviving_request(monkeypatch):
    service, _, repository, upload_port = service_fixture()
    request = service.create_remote_capture_request(user_id="synthetic-user", session_id="synthetic-session", device_id="synthetic-device", manual_code="654321", instruction="", capture_only=True)
    original = service.upload_bytes

    def upload_then_cancel(**kwargs):
        upload = original(**kwargs)
        service.cancel_remote_capture_request(user_id="synthetic-user", request_id=request.request_id)
        return upload

    monkeypatch.setattr(service, "upload_bytes", upload_then_cancel)
    result, task = service.complete_remote_capture_request(request_id=request.request_id, device_id=request.device_id, manual_code=request.manual_code, filename="synthetic.png", content_type="image/png", payload=SYNTHETIC_PNG)
    assert result.status == "cancelled" and result.captured_image_id is None and task is None
    assert not upload_port.uploaded_images and not repository.tasks
    assert not service.billing_service.reserved


def test_batch_cancellation_before_worker_releases_all_images():
    service, _, repository, upload_port = service_fixture()
    request, _ = batch(service, [capture(service), capture(service)])
    service.cancel_remote_capture_request(user_id="synthetic-user", request_id=request.request_id)
    service.complete_batch_answer_request_safely(request_id=request.request_id)
    assert not upload_port.uploaded_images and not repository.tasks
    assert service.vision_gateway.calls == 0 and not service.billing_service.reserved


def test_cancel_during_generation_keeps_terminal_state_and_releases_reservation():
    service, _, repository, upload_port = service_fixture()
    request, _ = batch(service, [capture(service), capture(service)])
    original = service.vision_gateway.analyze

    def cancel_while_generating(**kwargs):
        current = repository.get_remote_capture_request(request.request_id)
        assert current.answer_task_id, "task identity must be bound before model work"
        service.cancel_remote_capture_request(user_id="synthetic-user", request_id=request.request_id)
        return original(**kwargs)

    service.vision_gateway.analyze = cancel_while_generating
    service.complete_batch_answer_request_safely(request_id=request.request_id)
    current = repository.get_remote_capture_request(request.request_id)
    assert current.status == "cancelled"
    assert repository.get_task(current.answer_task_id).status == "cancelled"
    assert not upload_port.uploaded_images and not service.session_service.contexts
    assert not service.billing_service.settled and service.billing_service.released


def test_streaming_batch_binds_task_and_emits_partials_before_final_result():
    service, _, repository, _ = service_fixture()
    service.vision_gateway = StreamingVisionGateway()
    request, _ = batch(service, [capture(service), capture(service)])
    events = []
    service.complete_batch_answer_request_safely(request_id=request.request_id, on_transition=lambda req, task: events.append((req, task)))
    assert any(task and task.status == "streaming" and task.answer_text for _, task in events)
    assert all(req.answer_task_id == task.task_id for req, task in events if task is not None)
    assert repository.get_remote_capture_request(request.request_id).status == "completed"


@pytest.mark.parametrize("failure", ["insufficient", "vision"])
def test_batch_failure_is_terminal_clear_and_requires_recapture(failure):
    service, _, repository, upload_port = service_fixture(insufficient=failure == "insufficient", fail_vision=failure == "vision")
    request, _ = batch(service, [capture(service)])
    service.complete_batch_answer_request_safely(request_id=request.request_id)
    result = repository.get_remote_capture_request(request.request_id)
    assert result.status == "failed" and "重新截屏" in result.error_message
    assert not upload_port.uploaded_images and not service.billing_service.settled
    if failure == "insufficient": assert service.vision_gateway.calls == 0
    original, created = batch(service, [repository.get_remote_capture_request(request.capture_request_ids[0])])
    assert original.request_id == request.request_id and not created


@pytest.mark.parametrize("mode,status", [("interview", "live"), ("mock", "live"), ("written", "ended")])
def test_multi_screen_rejects_other_modes_and_ended_sessions(mode, status):
    service, _, repository, _ = service_fixture()
    service.session_service.session.session_mode = mode
    service.session_service.session.status = status
    with pytest.raises(DomainRequestError):
        service.create_remote_capture_request(user_id="synthetic-user", session_id="synthetic-session", device_id="synthetic-device", manual_code="654321", instruction="", capture_only=True)
    with pytest.raises(DomainRequestError):
        service.create_batch_answer_request(user_id="synthetic-user", session_id="synthetic-session", capture_request_ids=["synthetic"], instruction="")
    assert not repository.remote_capture_requests and not service.billing_service.reserved


def test_redis_roundtrip_new_fields_and_old_records_have_compatible_defaults():
    redis = FakeRedis()
    settings = Settings(_env_file=None, redis_url="redis://unused")
    repository = RedisScreenshotAnswerRepository(settings, redis_client=redis)
    request = RemoteScreenshotCaptureRequest(request_id="synthetic-capture", session_id="synthetic-session", owner_user_id="synthetic-user", device_id="synthetic-device", manual_code="654321", instruction="", status="completed", created_at_ms=1, updated_at_ms=1, capture_only=True, captured_image_id="synthetic-image")
    repository.save_remote_capture_request(request)
    assert RedisScreenshotAnswerRepository(settings, redis_client=redis).get_remote_capture_request(request.request_id) == request
    old = asdict(request)
    for field in ("capture_only", "captured_image_id", "capture_request_ids", "consumed_by_request_id", "upload_in_progress"):
        del old[field]
    decoded = RedisScreenshotAnswerRepository._decode_request(old)
    assert not decoded.capture_only and not decoded.capture_request_ids and decoded.captured_image_id is None
    assert "payload_bytes" not in json.dumps(redis.values)


@pytest.mark.parametrize("repository", [InMemoryScreenshotAnswerRepository(), RedisScreenshotAnswerRepository(Settings(_env_file=None, redis_url="redis://unused"), redis_client=FakeRedis())])
def test_cancelled_screenshot_metadata_and_tasks_cannot_be_revived(repository):
    request = RemoteScreenshotCaptureRequest(request_id="synthetic-cancelled", session_id="synthetic-session", owner_user_id="synthetic-user", device_id="synthetic-device", manual_code="654321", instruction="", status="cancelled", stage="cancelled", created_at_ms=1, updated_at_ms=1)
    repository.save_remote_capture_request(request)
    task = ScreenshotAnswerTaskRecord(task_id="synthetic-task", session_id="synthetic-session", owner_user_id="synthetic-user", instruction="", answer_text="", status="cancelled", stream_mode=True)
    repository.save_task(task)
    for status in ("processing", "completed", "failed"):
        assert repository.save_remote_capture_request(replace(request, status=status, updated_at_ms=2)).status == "cancelled"
    for status in ("streaming", "completed", "failed"):
        assert repository.save_task(replace(task, status=status, updated_at_ms=2)).status == "cancelled"


def test_multi_screen_http_contract_keeps_legacy_desktop_upload_and_event_metadata(monkeypatch):
    from fastapi.testclient import TestClient
    from app.deps import optional_authenticated_context, realtime_speech_service, screenshot_answer_service
    from app.main import app

    service, _, _, _ = service_fixture()
    events = []
    realtime = SimpleNamespace(
        get_desktop_binding=lambda **kwargs: SimpleNamespace(device_id="synthetic-device", manual_code="654321"),
        get_desktop_capture_binding=lambda **kwargs: SimpleNamespace(),
        publish_session_event=lambda **kwargs: events.append(kwargs),
    )
    monkeypatch.setitem(app.dependency_overrides, screenshot_answer_service, lambda: service)
    monkeypatch.setitem(app.dependency_overrides, realtime_speech_service, lambda: realtime)
    monkeypatch.setitem(app.dependency_overrides, optional_authenticated_context, lambda: None)
    client = TestClient(app)
    policy = client.get("/api/v1/screenshot-answer/validation-policy").json()["data"]
    assert policy["supportsCaptureOnly"] and policy["maxImagesPerTask"] == 4
    capture_ids = []
    for page in (1, 2):
        created_response = client.post(
            "/api/v1/screenshot-answer/sessions/synthetic-session/remote-capture-requests",
            json={"userId": "synthetic-user", "captureOnly": True},
        )
        created_response.raise_for_status()
        created = created_response.json()["data"]
        assert created["captureOnly"] and created["capturedImageId"] is None
        capture_id = created["requestId"]
        upload_response = client.post(
            f"/api/v1/screenshot-answer/capture-requests/{capture_id}/desktop-upload",
            data={"deviceId": "synthetic-device", "manualCode": "654321"},
            files={"screenshot": (f"page-{page}.png", SYNTHETIC_PNG, "image/png")},
        )
        upload_response.raise_for_status()
        ready = client.get(f"/api/v1/screenshot-answer/capture-requests/{capture_id}", params={"userId": "synthetic-user"}).json()["data"]
        assert ready["captureOnly"] and ready["status"] == "completed" and ready["capturedImageId"]
        assert ready["answerTask"] is None
        capture_ids.append(capture_id)
    assert not service.billing_service.reserved and service.vision_gateway.calls == 0
    body = {"userId": "synthetic-user", "captureRequestIds": capture_ids}
    submitted = client.post("/api/v1/screenshot-answer/sessions/synthetic-session/batch-answer-requests", json=body)
    submitted.raise_for_status()
    parent_id = submitted.json()["data"]["requestId"]
    result = client.get(f"/api/v1/screenshot-answer/capture-requests/{parent_id}", params={"userId": "synthetic-user"}).json()["data"]
    assert result["status"] == "completed" and result["captureRequestIds"] == capture_ids
    assert result["answerTask"]["imageCount"] == 2
    duplicate = client.post("/api/v1/screenshot-answer/sessions/synthetic-session/batch-answer-requests", json=body)
    assert duplicate.json()["data"]["requestId"] == parent_id
    assert service.vision_gateway.calls == 1 and len(service.billing_service.settled) == 1
    captured_events = [event["payload"] for event in events if event["payload"].get("captureOnly") and event["payload"]["status"] == "completed"]
    assert [event["capturedFilename"] for event in captured_events] == ["page-1.png", "page-2.png"]
    assert all(event["capturedImageId"] for event in captured_events)


def test_batch_uses_existing_real_billing_rule_once_for_multiple_images():
    from app.services.billing_service import BillingService

    service, _, _, _ = service_fixture()
    service.billing_service = BillingService(Settings(_env_file=None))
    before = service.billing_service.state_for_user(user_id="synthetic-user").balance
    sources = [capture(service), capture(service)]
    assert service.billing_service.state_for_user(user_id="synthetic-user").balance == before
    request, _ = batch(service, sources)
    service.complete_batch_answer_request_safely(request_id=request.request_id)
    replay, created = batch(service, sources)
    assert not created and replay.request_id == request.request_id
    after = service.billing_service.state_for_user(user_id="synthetic-user")
    assert before - after.balance == 15
    assert len([item for item in after.ledger if item.kind == "screenshot_answer_settlement"]) == 1


def test_repository_recreation_uses_shared_redis_session_lock_for_batch_admission():
    from copy import copy

    class LockingFakeRedis(FakeRedis):
        def __init__(self):
            super().__init__()
            self.locks = {}
            self.guard = threading.Lock()

        def lock(self, key, **kwargs):
            with self.guard:
                return self.locks.setdefault(key, threading.RLock())

    redis = LockingFakeRedis()
    settings = Settings(_env_file=None, redis_url="redis://unused")
    first, _, _, _ = service_fixture()
    first.repository = RedisScreenshotAnswerRepository(settings, redis_client=redis)
    second = copy(first)
    second.repository = RedisScreenshotAnswerRepository(settings, redis_client=redis)
    sources = [capture(first), capture(first)]
    barrier = threading.Barrier(2)

    def submit(service):
        barrier.wait(timeout=5)
        return batch(service, sources)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(submit, [first, second]))
    assert sum(created for _, created in results) == 1
    assert results[0][0].request_id == results[1][0].request_id
    assert any("operation-lock" in key for key in redis.locks)


def test_concurrent_capture_requests_cannot_exceed_four():
    service, _, repository, _ = service_fixture()
    barrier = threading.Barrier(8)

    def attempt(_):
        barrier.wait(timeout=5)
        try:
            return service.create_remote_capture_request(user_id="synthetic-user", session_id="synthetic-session", device_id="synthetic-device", manual_code="654321", instruction="", capture_only=True)
        except DomainRequestError as exc:
            assert exc.error_code == "screenshot_capture_limit_reached"
            return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(attempt, range(8)))
    assert len([result for result in results if result is not None]) == 4
    assert len(repository.remote_capture_requests) == 4


def test_abandoned_inflight_capture_requests_expire_and_free_capacity(monkeypatch):
    service, _, repository, _ = service_fixture()
    requests = [service.create_remote_capture_request(user_id="synthetic-user", session_id="synthetic-session", device_id="synthetic-device", manual_code="654321", instruction="", capture_only=True) for _ in range(4)]
    claimed = service.claim_remote_capture_request(request_id=requests[0].request_id, device_id="synthetic-device", manual_code="654321")
    expires_at = claimed.created_at_ms + service.settings.oss_upload_intent_ttl_seconds * 1000 + 1
    monkeypatch.setattr("app.services.screenshot_answer_service._now_ms", lambda: expires_at)
    new = service.create_remote_capture_request(user_id="synthetic-user", session_id="synthetic-session", device_id="synthetic-device", manual_code="654321", instruction="", capture_only=True)
    assert new.status == "requested"
    assert all(repository.get_remote_capture_request(item.request_id).status == "cancelled" for item in requests)
    assert all("过期" in repository.get_remote_capture_request(item.request_id).error_message for item in requests)


def test_public_task_delete_during_batch_generation_prevents_context_and_settlement():
    from fastapi.testclient import TestClient
    from app.deps import optional_authenticated_context, screenshot_answer_service
    from app.main import app

    service, _, repository, _ = service_fixture()
    request, _ = batch(service, [capture(service)])
    app.dependency_overrides[screenshot_answer_service] = lambda: service
    app.dependency_overrides[optional_authenticated_context] = lambda: None
    original = service.vision_gateway.analyze

    def delete_via_api(**kwargs):
        current = repository.get_remote_capture_request(request.request_id)
        result = TestClient(app).delete(f"/api/v1/screenshot-answer/tasks/{current.answer_task_id}", params={"userId": "synthetic-user"})
        result.raise_for_status()
        assert result.json()["data"]["status"] == "cancelled"
        return original(**kwargs)

    service.vision_gateway.analyze = delete_via_api
    try:
        service.complete_batch_answer_request_safely(request_id=request.request_id)
    finally:
        app.dependency_overrides.pop(screenshot_answer_service, None)
        app.dependency_overrides.pop(optional_authenticated_context, None)
    current = repository.get_remote_capture_request(request.request_id)
    assert current.status == "cancelled"
    assert repository.get_task(current.answer_task_id).status == "cancelled"
    assert not service.billing_service.settled and not service.session_service.contexts


def test_synthetic_multiscreen_evals_keep_all_pages_in_one_ordered_vision_message():
    import base64
    from pathlib import Path
    from app.ports.screenshot_answer import PreparedScreenshotImage
    from app.services.screenshot_answer_service import OpenAICompatibleVisionGateway

    eval_path = Path(__file__).resolve().parents[3] / "ai/evals/written-multi-screen-answer-v1.jsonl"
    cases = [json.loads(line) for line in eval_path.read_text().splitlines()]
    gateway = OpenAICompatibleVisionGateway(Settings(_env_file=None))
    for case in cases:
        assert case["synthetic"]
        if not case["expected"].get("single_vision_message"):
            continue
        images = [PreparedScreenshotImage(
            image_id=f"synthetic-image-{index}", session_id="synthetic-session", owner_user_id="synthetic-user",
            filename=page["name"], content_type="image/png", object_key=f"synthetic/{index}",
            size_bytes=len(page["text"].encode()), ordinal=index + 1, content_sha256="synthetic",
            byte_length=len(page["text"].encode()), payload_bytes=page["text"].encode(),
        ) for index, page in enumerate(case["images"])]
        payload = gateway._request_payload(instruction="", images=images, stream=True)
        user_messages = [message for message in payload["messages"] if message["role"] == "user"]
        assert len(user_messages) == 1
        content = user_messages[0]["content"]
        encoded_pages = [item["image_url"]["url"] for item in content if item["type"] == "image_url"]
        assert [base64.b64decode(url.split(",", 1)[1]).decode() for url in encoded_pages] == [page["text"] for page in case["images"]]
        assert [image.filename for image in images] == case["expected"]["ordered_image_names"]


def test_public_delete_and_final_context_settlement_share_one_completion_lock(monkeypatch):
    from fastapi.testclient import TestClient
    from app.deps import optional_authenticated_context, screenshot_answer_service
    from app.main import app

    service, _, repository, _ = service_fixture()
    request, _ = batch(service, [capture(service)])
    monkeypatch.setitem(app.dependency_overrides, screenshot_answer_service, lambda: service)
    monkeypatch.setitem(app.dependency_overrides, optional_authenticated_context, lambda: None)
    attempted, finished = threading.Event(), threading.Event()
    order = []
    original_delete = service.delete_task
    original_append = service.session_service.append_context
    original_settle = service.billing_service.settle_usage
    futures = []

    def report_delete(**kwargs):
        attempted.set()
        result = original_delete(**kwargs)
        order.append("deleted")
        finished.set()
        return result

    def settle(**kwargs):
        assert not finished.is_set()
        order.append("settled")
        return original_settle(**kwargs)

    with ThreadPoolExecutor(max_workers=1) as pool:
        def append_context(**kwargs):
            if kwargs["role"] == "screenshot":
                task_id = repository.get_remote_capture_request(request.request_id).answer_task_id
                futures.append(pool.submit(lambda: TestClient(app).delete(f"/api/v1/screenshot-answer/tasks/{task_id}", params={"userId": "synthetic-user"})))
                assert attempted.wait(timeout=3)
                assert not finished.is_set(), "DELETE must wait for the active final context/settlement section"
            original_append(**kwargs)

        monkeypatch.setattr(service, "delete_task", report_delete)
        monkeypatch.setattr(service.session_service, "append_context", append_context)
        monkeypatch.setattr(service.billing_service, "settle_usage", settle)
        service.complete_batch_answer_request_safely(request_id=request.request_id)
        assert futures[0].result(timeout=3).status_code == 200
    assert order == ["settled", "deleted"]
    assert len(service.session_service.contexts) == 2
