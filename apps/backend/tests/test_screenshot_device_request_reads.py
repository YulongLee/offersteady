"""Synthetic router-only device reads: no application runtime or external services."""
from __future__ import annotations

from dataclasses import replace
import logging
from types import SimpleNamespace
from unittest.mock import Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.core.config import Settings
from app.core.errors import DomainRequestError, install_exception_handlers
from app.deps import realtime_speech_service, screenshot_answer_service
from app.modules.screenshot_answer import router
from app.ports.screenshot_answer import RemoteScreenshotCaptureRequest


DEVICE = "synthetic-current-device"
CODE = "123456"
SESSION = "synthetic-current-session"
OWNER = "synthetic-current-owner"
PATH = f"/screenshot-answer/desktop-devices/{DEVICE}/capture-requests/next"


def capture(**changes) -> RemoteScreenshotCaptureRequest:
    return replace(RemoteScreenshotCaptureRequest(
        request_id="synthetic-request", session_id=SESSION, owner_user_id=OWNER,
        device_id=DEVICE, manual_code=CODE, instruction="Synthetic question",
        status="requested", created_at_ms=100, updated_at_ms=100,
    ), **changes)


@pytest.fixture
def harness():
    repository = Mock(spec=[
        "get_remote_capture_request", "list_remote_capture_requests_for_session",
        "save_remote_capture_request", "save_task", "session_operation_lock",
    ])
    repository.get_remote_capture_request.return_value = capture()
    repository.list_remote_capture_requests_for_session.return_value = []
    for operation in (repository.save_remote_capture_request, repository.save_task, repository.session_operation_lock):
        operation.side_effect = AssertionError("device inspection must never mutate state")
    service = SimpleNamespace(
        repository=repository,
        get_next_remote_capture_request=Mock(return_value=capture(request_id="synthetic-legacy-request")),
        get_task=Mock(side_effect=AssertionError("get_task can mutate stale state")),
    )
    realtime = SimpleNamespace(
        get_desktop_pairing_status=Mock(return_value={"bound": True, "sessionStatus": "live"}),
        get_desktop_capture_binding=Mock(return_value=SimpleNamespace(
            session_id=SESSION, owner_user_id=OWNER, device_id=DEVICE, manual_code=CODE,
        )),
    )
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[screenshot_answer_service] = lambda: service
    app.dependency_overrides[realtime_speech_service] = lambda: realtime
    install_exception_handlers(app, settings=Settings(_env_file=None), logger=logging.getLogger(__name__))
    with TestClient(app) as client:
        yield SimpleNamespace(client=client, repository=repository, service=service, realtime=realtime)
    service.get_task.assert_not_called()
    repository.save_remote_capture_request.assert_not_called()
    repository.save_task.assert_not_called()
    repository.session_operation_lock.assert_not_called()


def read(harness, **queries):
    response = harness.client.get(PATH, params={"manualCode": CODE, **queries})
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["error"] is None
    assert payload["meta"]["apiVersion"] == "v1"
    return payload["data"]


def test_no_optional_queries_preserve_legacy_next_request_path(harness):
    # Older clients retain the previous all-device ordering, even for an old session.
    harness.service.get_next_remote_capture_request.return_value = capture(session_id="synthetic-older-session")
    result = read(harness)
    assert result["sessionId"] == "synthetic-older-session"
    harness.service.get_next_remote_capture_request.assert_called_once_with(device_id=DEVICE, manual_code=CODE)
    harness.realtime.get_desktop_capture_binding.assert_not_called()
    harness.repository.get_remote_capture_request.assert_not_called()
    harness.repository.list_remote_capture_requests_for_session.assert_not_called()


@pytest.mark.parametrize("queries", [{}, {"sessionId": SESSION}, {"requestId": "synthetic-request"}])
@pytest.mark.parametrize("pairing", [{"bound": False}, {"bound": True, "sessionStatus": "preparing"}, {"bound": True, "sessionStatus": "ended"}])
def test_existing_unbound_and_nonlive_gate_precedes_every_request_read(harness, queries, pairing):
    harness.realtime.get_desktop_pairing_status.return_value = pairing
    assert read(harness, **queries) is None
    harness.service.get_next_remote_capture_request.assert_not_called()
    harness.realtime.get_desktop_capture_binding.assert_not_called()
    harness.repository.get_remote_capture_request.assert_not_called()
    harness.repository.list_remote_capture_requests_for_session.assert_not_called()


@pytest.mark.parametrize("queries", [{"sessionId": "synthetic-other-session"}, {"sessionId": "synthetic-other-session", "requestId": "synthetic-request"}])
def test_mismatched_session_is_rejected_before_repository_reads(harness, queries):
    assert read(harness, **queries) is None
    harness.realtime.get_desktop_capture_binding.assert_called_once_with(device_id=DEVICE, manual_code=CODE)
    harness.repository.get_remote_capture_request.assert_not_called()
    harness.repository.list_remote_capture_requests_for_session.assert_not_called()
    harness.service.get_next_remote_capture_request.assert_not_called()


@pytest.mark.parametrize("changes", [{"device_id": "synthetic-replaced-device"}, {"manual_code": "654321"}])
def test_binding_recovery_for_another_device_or_code_cannot_authorize_scoped_reads(harness, changes):
    binding = harness.realtime.get_desktop_capture_binding.return_value
    for key, value in changes.items():
        setattr(binding, key, value)
    assert read(harness, sessionId=SESSION, requestId="synthetic-request") is None
    harness.repository.get_remote_capture_request.assert_not_called()
    harness.repository.list_remote_capture_requests_for_session.assert_not_called()


@pytest.mark.parametrize("changes", [
    {"session_id": "synthetic-other-session"}, {"owner_user_id": "synthetic-other-owner"},
    {"device_id": "synthetic-other-device"}, {"manual_code": "654321"},
])
@pytest.mark.parametrize("include_session", [False, True])
def test_specified_foreign_record_never_leaks(harness, changes, include_session):
    harness.repository.get_remote_capture_request.return_value = capture(**changes)
    queries = {"requestId": "synthetic-request"}
    if include_session:
        queries["sessionId"] = SESSION
    assert read(harness, **queries) is None
    harness.repository.get_remote_capture_request.assert_called_once_with(request_id="synthetic-request")
    harness.repository.list_remote_capture_requests_for_session.assert_not_called()
    harness.service.get_next_remote_capture_request.assert_not_called()


def test_missing_specified_request_is_safe_empty_response(harness):
    harness.repository.get_remote_capture_request.return_value = None
    assert read(harness, sessionId=SESSION, requestId="synthetic-missing-request") is None


@pytest.mark.parametrize("status, stage", [
    ("requested", "requested"), ("processing", "claimed"), ("processing", "vision-running"),
    ("cancelled", "cancelled"), ("completed", "completed"), ("failed", "upload-failed"),
])
def test_specified_current_request_returns_its_actual_status_without_claim_or_task_reads(harness, status, stage):
    record = capture(status=status, stage=stage, answer_task_id="synthetic-task-not-read")
    harness.repository.get_remote_capture_request.return_value = record
    result = read(harness, sessionId=SESSION, requestId=record.request_id)
    assert (result["status"], result["stage"]) == (status, stage)
    assert result["answerTaskId"] == "synthetic-task-not-read"
    assert result["answerTask"] is None
    assert (result["ownerUserId"], result["sessionId"], result["deviceId"], result["manualCode"]) == (OWNER, SESSION, DEVICE, CODE)
    assert harness.repository.get_remote_capture_request.return_value is record
    harness.repository.list_remote_capture_requests_for_session.assert_not_called()
    harness.service.get_next_remote_capture_request.assert_not_called()


def test_session_only_selects_earliest_requested_current_record_with_all_ownership_checks(harness):
    records = [
        capture(request_id="synthetic-later", created_at_ms=300),
        capture(request_id="synthetic-earliest", created_at_ms=200),
        capture(request_id="synthetic-processing", status="processing", created_at_ms=1),
        capture(request_id="synthetic-cancelled", status="cancelled", created_at_ms=1),
        capture(request_id="synthetic-completed", status="completed", created_at_ms=1),
        capture(request_id="synthetic-failed", status="failed", created_at_ms=1),
        capture(request_id="synthetic-old-session", session_id="synthetic-old-session", created_at_ms=1),
        capture(request_id="synthetic-other-owner", owner_user_id="synthetic-other-owner", created_at_ms=1),
        capture(request_id="synthetic-other-device", device_id="synthetic-other-device", created_at_ms=1),
        capture(request_id="synthetic-other-code", manual_code="654321", created_at_ms=1),
    ]
    harness.repository.list_remote_capture_requests_for_session.return_value = records
    result = read(harness, sessionId=SESSION)
    assert result["requestId"] == "synthetic-earliest"
    assert harness.repository.list_remote_capture_requests_for_session.return_value == records
    harness.repository.list_remote_capture_requests_for_session.assert_called_once_with(session_id=SESSION)
    harness.repository.get_remote_capture_request.assert_not_called()
    harness.service.get_next_remote_capture_request.assert_not_called()


def test_session_only_with_no_pending_request_is_safe_empty_response(harness):
    assert read(harness, sessionId=SESSION) is None


@pytest.mark.parametrize("status", [404, 409])
def test_scoped_lookup_does_not_bypass_current_binding_validation(harness, status):
    harness.realtime.get_desktop_capture_binding.side_effect = DomainRequestError(
        "realtime-speech", "desktop-capture-binding", "Synthetic unavailable binding", status,
    )
    response = harness.client.get(PATH, params={"manualCode": CODE, "sessionId": SESSION, "requestId": "synthetic-request"})
    assert response.status_code == status
    assert response.json()["data"] is None
    harness.repository.get_remote_capture_request.assert_not_called()
    harness.repository.list_remote_capture_requests_for_session.assert_not_called()


def test_device_credentials_remain_required(harness):
    response = harness.client.get(PATH, params={"sessionId": SESSION, "requestId": "synthetic-request"})
    assert response.status_code == 422
    harness.realtime.get_desktop_pairing_status.assert_not_called()
    harness.realtime.get_desktop_capture_binding.assert_not_called()
