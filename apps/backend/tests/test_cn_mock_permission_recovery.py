"""Actual CN control/microphone routes with synthetic records and inert providers.

No database, OS permission request, actual audio, model or payment service is used.
"""
import asyncio
from copy import deepcopy
from dataclasses import asdict
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.modules import mock_interview as api
from app.services.mock_interview_repository import round_state
from app.services.mock_interview_rounds import MockRoundState
from app.services.mock_interview_runtime import MockInterviewRuntime
from app.services.realtime_speech_service import RealtimeSpeechService


@pytest.fixture
def synthetic_client(monkeypatch):
    owner, sid = "synthetic-permission-owner", "synthetic-permission-session"
    row = {"session_id": sid, "owner_user_id": owner, "billing_class": "points",
        "refunded": False, "created_at_ms": 1000,
        "data": {"title": "合成权限恢复练习", "target_role": "测试工程师",
            "state": asdict(MockRoundState()), "resume_id": "synthetic-resume",
            "resume_version": "synthetic-v1", "billable_ms": 0, "billed_minutes": 0,
            "clock_at_ms": None, "control_token": "synthetic-control", "lease_until_ms": 16_000,
            "started_at_ms": None, "deadline_at_ms": None, "duration_limit_ms": 3_600_000}}
    repo = Mock()
    repo.settings = SimpleNamespace(product_edition="cn")
    repo.duration_deadline.return_value = None
    repo.acquire_control.side_effect = lambda **_: deepcopy(row)
    repo.control_tick.side_effect = lambda **_: deepcopy(row)
    repo.get.side_effect = lambda **_: deepcopy(row)
    def transition(*, move, **_):
        row["data"]["state"] = asdict(move(round_state(row)))
        return deepcopy(row)
    repo.transition.side_effect = transition
    realtime = Mock()
    realtime.session_service.get_session.return_value = SimpleNamespace(session_mode="mock", status="preparing")
    device = SimpleNamespace(device_id="synthetic-device", generation=1,
        capabilities={"mockInterviewProtocol": 1, "protocolVersion": "2.0", "microphone": "unknown"})
    binding = SimpleNamespace(device_id=device.device_id, binding_generation=1, status="bound",
        manual_code="000000", session_id=sid, owner_user_id=owner)
    realtime.get_desktop_binding.return_value = binding
    realtime.get_desktop_capture_binding.return_value = binding
    realtime.repository.get_desktop_device_by_code.return_value = device
    realtime._desktop_device_fresh.return_value = True
    realtime._permission_status.side_effect = RealtimeSpeechService._permission_status
    audio = Mock()
    audio.revoke.return_value = None
    runtime = MockInterviewRuntime(repo, Mock(), Mock(), Mock(), audio, realtime, now_ms=lambda: 1000)
    # Starting can be observed without launching a task or invoking a provider.
    runtime._generate = Mock()
    monkeypatch.setattr(api, "require_mock_runtime", lambda: runtime)
    monkeypatch.setattr(api, "authentication_service", lambda: SimpleNamespace(
        authenticate_access_token=lambda **_: SimpleNamespace(user_id=owner)))
    app = FastAPI()
    app.include_router(api.router, prefix="/api/v1")
    try:
        with TestClient(app) as client:
            yield client, runtime, row, device, binding
    finally:
        asyncio.run(runtime.shutdown())


@pytest.mark.parametrize("permission,code", [
    ("unknown", "mock_microphone_checking"),
    (None, "mock_microphone_checking"),
    ("invalid", "mock_microphone_checking"),
    ("denied", "mock_microphone_required"),
    ("restricted", "mock_microphone_required"),
])
def test_control_publish_start_reject_then_same_session_recovers(synthetic_client, permission, code):
    client, runtime, row, device, binding = synthetic_client
    if permission is None:
        device.capabilities.pop("microphone")
    else:
        device.capabilities["microphone"] = permission
    original = deepcopy(row)
    with client.websocket_connect(f"/api/v1/mock-interviews/{row['session_id']}/control") as socket:
        socket.send_json({"accessToken": "synthetic-token"})
        initial = socket.receive_json()
        assert initial["preparation"]["code"] == code
        assert not initial["preparation"]["ready"] and not initial["desktopConnected"]
        socket.send_json({"action": "start", "version": 0})
        assert socket.receive_json()["code"] == code
        blocked = socket.receive_json()
        assert blocked["preparation"] == initial["preparation"]
        assert row == original
        runtime.repository.transition.assert_not_called()
        runtime._generate.assert_not_called()
        runtime.reader.read.assert_not_called()
        runtime.audio.open.assert_not_called()
        assert not runtime.desktops
        # Only a subsequently observed authoritative registration makes ready.
        device.capabilities["microphone"] = "granted"
        socket.send_json({"action": "heartbeat"})
        ready = socket.receive_json()
        assert ready["preparation"]["code"] == "mock_ready"
        assert ready["preparation"]["ready"] and ready["desktopConnected"]
        assert not ready["microphoneConnected"]
        assert ready["session"] == initial["session"]
        assert row == original
        runtime.repository.create.assert_not_called()
        runtime.repository.select_resume.assert_not_called()
        realtime = runtime.realtime
        realtime.repository.save_desktop_device.assert_not_called()
        assert realtime.get_desktop_binding.return_value is binding
        runtime._generate.assert_not_called()
        # Recovery does not start automatically. An explicit later command does.
        socket.send_json({"action": "start", "version": 0})
        started = socket.receive_json()
        assert started["session"]["state"]["phase"] == "generating_question"
        runtime._generate.assert_called_once()
        runtime.reader.read.assert_called_once_with(user_id=row["owner_user_id"],
            document_id="synthetic-resume", version_id="synthetic-v1")
        runtime.audio.open.assert_not_called()


@pytest.mark.parametrize("permission,code", [
    ("unknown", "mock_microphone_checking"),
    (None, "mock_microphone_checking"),
    ([], "mock_microphone_checking"),
    ("denied", "mock_microphone_required"),
    ("restricted", "mock_microphone_required"),
])
def test_audio_attach_blocks_unconfirmed_before_registering_channel(synthetic_client, permission, code):
    client, runtime, row, device, _ = synthetic_client
    device.capabilities["microphone"] = permission
    original = deepcopy(row)
    url = f"/api/v1/mock-interviews/{row['session_id']}/microphone"
    body = {"deviceId": device.device_id, "manualCode": "000000"}
    with client.websocket_connect(url) as socket:
        socket.send_json(body)
        assert socket.receive_json()["code"] == code
        with pytest.raises(WebSocketDisconnect):
            socket.receive_json()
    assert not runtime.desktops
    assert row == original
    runtime.audio.open.assert_not_called()
    runtime._generate.assert_not_called()
    runtime.repository.transition.assert_not_called()
    runtime.repository.create.assert_not_called()
    # The same credential/binding can attach after a real status update.
    device.capabilities["microphone"] = "granted"
    with client.websocket_connect(url) as socket:
        socket.send_json(body)
        assert socket.receive_json() == {"type": "capture", "epoch": None}
        assert row["session_id"] in runtime.desktops
        runtime.audio.open.assert_not_called()
    assert not runtime.desktops
    assert row == original


@pytest.mark.parametrize("boundary", ["start", "microphone"])
def test_ready_snapshot_does_not_bypass_later_permission_change(synthetic_client, boundary):
    client, runtime, row, device, _ = synthetic_client
    device.capabilities["microphone"] = "granted"
    with client.websocket_connect(f"/api/v1/mock-interviews/{row['session_id']}/control") as control:
        control.send_json({"accessToken": "synthetic-token"})
        assert control.receive_json()["preparation"]["ready"]
        device.capabilities["microphone"] = "unknown"
        if boundary == "start":
            control.send_json({"action": "start", "version": 0})
            assert control.receive_json()["code"] == "mock_microphone_checking"
            assert not control.receive_json()["preparation"]["ready"]
        else:
            with client.websocket_connect(f"/api/v1/mock-interviews/{row['session_id']}/microphone") as socket:
                socket.send_json({"deviceId": device.device_id, "manualCode": "000000"})
                assert socket.receive_json()["code"] == "mock_microphone_checking"
        runtime.audio.open.assert_not_called()
        runtime._generate.assert_not_called()
        runtime.repository.transition.assert_not_called()
        assert row["data"]["started_at_ms"] is None and row["data"]["deadline_at_ms"] is None
