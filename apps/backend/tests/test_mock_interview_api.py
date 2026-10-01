"""Real local PostgreSQL + in-process HTTP/WebSockets; synthetic identities only."""
import logging
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.config import Settings
from app.core.errors import DomainRequestError, install_exception_handlers
from app.modules import mock_interview as api
from app.modules import realtime_speech as realtime_api
from app.services.realtime_speech_service import RealtimeSpeechService
from app.ports.realtime_speech import TranscriptResult
from test_mock_interview_postgres import repositories, mock_runtime_fixture, DATABASE_URL

pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="Isolated PostgreSQL required")


@pytest.fixture
def client_runtime(repositories, monkeypatch):
    runtime, user, sid, now, generator, billing = mock_runtime_fixture(repositories)
    app = FastAPI()
    app.include_router(api.router, prefix="/api/v1")
    install_exception_handlers(app, settings=Settings(_env_file=None), logger=logging.getLogger("synthetic-mock-tests"))
    app.dependency_overrides[api.require_mock_runtime] = lambda: runtime
    app.dependency_overrides[api.require_authenticated_context] = lambda: SimpleNamespace(user_id=user)
    monkeypatch.setattr(api, "require_mock_runtime", lambda: runtime)
    def authenticate(*, access_token):
        if access_token not in ("synthetic-owner", "synthetic-other"):
            raise DomainRequestError("auth", "token", "登录无效", 401, "invalid_token")
        return SimpleNamespace(user_id=user if access_token == "synthetic-owner" else "other")
    monkeypatch.setattr(api, "authentication_service", lambda: SimpleNamespace(authenticate_access_token=authenticate))
    monkeypatch.setattr(api, "billing_service", lambda: billing)
    runtime.realtime.get_desktop_capture_binding.return_value = SimpleNamespace(session_id=sid, owner_user_id=user)
    with TestClient(app) as client:
        yield client, runtime, user, sid


def receive_type(socket, kind):
    for _ in range(12):
        item = socket.receive_json()
        if item["type"] == kind:
            return item
    raise AssertionError("expected bounded response sequence")


def test_http_cannot_read_or_delete_another_owner_record(client_runtime):
    client, runtime, user, sid = client_runtime
    response = client.get(f"/api/v1/mock-interviews/{sid}")
    assert response.status_code == 200 and response.json()["data"]["sessionId"] == sid
    assert "control_token" not in response.text and "generation_claim" not in response.text
    client.app.dependency_overrides[api.require_authenticated_context] = lambda: SimpleNamespace(user_id="other")
    assert client.get(f"/api/v1/mock-interviews/{sid}").status_code == 404
    assert client.delete(f"/api/v1/mock-interviews/{sid}").status_code == 404
    assert runtime.repository.get(user_id=user, session_id=sid)


@pytest.mark.parametrize("token,code", [("wrong", "invalid_token"), ("synthetic-other", "mock_not_found")])
def test_control_rejects_bad_token_and_cross_owner_before_admission(client_runtime, token, code):
    client, runtime, _, sid = client_runtime
    with client.websocket_connect(f"/api/v1/mock-interviews/{sid}/control") as socket:
        socket.send_json({"accessToken": token})
        assert socket.receive_json()["code"] == code
        with pytest.raises(WebSocketDisconnect): socket.receive_json()
    assert runtime.controllers == {} and runtime.audio.snapshot()["captures"] == 0


def test_socket_commands_reject_forged_fields_and_duplicate_controller(client_runtime):
    client, runtime, _, sid = client_runtime
    with client.websocket_connect(f"/api/v1/mock-interviews/{sid}/control") as socket:
        socket.send_json({"accessToken": "synthetic-owner"})
        state = socket.receive_json()["session"]["state"]
        socket.send_json({"action": "start", "version": state["version"], "refunded": True})
        assert socket.receive_json()["code"] == "mock_invalid_command"
        with client.websocket_connect(f"/api/v1/mock-interviews/{sid}/control") as second:
            second.send_json({"accessToken": "synthetic-owner"})
            assert second.receive_json()["code"] == "mock_control_in_use"
        socket.send_json({"action": "heartbeat"})
        assert receive_type(socket, "state")["session"]["state"]["phase"] == "preparing"
    assert runtime.controllers == {}


def test_microphone_device_credentials_and_playback_gate_are_enforced(client_runtime):
    client, runtime, _, sid = client_runtime
    with client.websocket_connect(f"/api/v1/mock-interviews/{sid}/microphone") as socket:
        socket.send_json({"deviceId": "wrong", "manualCode": "000000"})
        assert socket.receive_json()["code"] == "mock_device_mismatch"
    with client.websocket_connect(f"/api/v1/mock-interviews/{sid}/microphone") as socket:
        socket.send_json({"deviceId": "device", "manualCode": "000000"})
        assert socket.receive_json() == {"type": "capture", "epoch": None}
        socket.send_bytes(b"a"*32+b"00")
        assert socket.receive_json()["code"] == "mock_capture_expired"
    assert runtime.desktops == {} and runtime.audio.snapshot()["captures"] == 0


def test_browser_and_desktop_round_submit_end_release_and_single_debit(client_runtime):
    client, runtime, user, sid = client_runtime
    with client.websocket_connect(f"/api/v1/mock-interviews/{sid}/control") as browser:
        browser.send_json({"accessToken": "synthetic-owner"})
        state = browser.receive_json()["session"]["state"]
        with client.websocket_connect(f"/api/v1/mock-interviews/{sid}/microphone") as desktop:
            desktop.send_json({"deviceId": "device", "manualCode": "000000"})
            assert desktop.receive_json()["epoch"] is None
            receive_type(browser, "state")
            browser.send_json({"action": "start", "version": state["version"]})
            state = receive_type(browser, "state")["session"]["state"]
            if state["phase"] == "generating_question":
                state = receive_type(browser, "state")["session"]["state"]
            assert state["phase"] == "speaking"
            browser.send_json({"action": "listen", "version": state["version"], "questionId": state["rounds"][-1]["question_id"]})
            capture = desktop.receive_json()
            if capture["epoch"] is None: capture = desktop.receive_json()
            assert len(capture["epoch"]) == 32
            state = receive_type(browser, "state")["session"]["state"]
            runtime.audio._captures[sid].gateway.transcribe.return_value = TranscriptResult("合成麦克风回答", .9)
            desktop.send_bytes(capture["epoch"].encode()+b"00"*1600)
            assert receive_type(browser, "transcript")["text"] == "合成麦克风回答"
            browser.send_json({"action": "end", "version": state["version"]})
            state = receive_type(browser, "state")["session"]["state"]
            if state["phase"] == "generating_report":
                state = receive_type(browser, "state")["session"]["state"]
            assert state["phase"] == "completed"
            assert runtime.audio.snapshot()["captures"] == 0
    assert runtime.controllers == {} and runtime.desktops == {}
    row = runtime.repository.get(user_id=user, session_id=sid)
    assert row["data"]["billed_minutes"] == 1


@pytest.mark.parametrize("media", ["binary-v1", "json-base64"])
def test_shipped_companion_prepare_publish_capture_reconnect_and_cleanup(client_runtime, monkeypatch, media):
    from test_mock_interview_legacy import wire
    client, runtime, user, sid = client_runtime
    client.app.include_router(realtime_api.router, prefix="/api/v1")
    client.app.dependency_overrides[realtime_api.realtime_speech_service] = lambda: runtime.realtime
    client.app.dependency_overrides[realtime_api.optional_authenticated_context] = lambda: None
    monkeypatch.setattr(realtime_api, "realtime_speech_service", lambda: runtime.realtime)
    runtime.realtime._publisher_response = RealtimeSpeechService._publisher_response
    runtime.realtime.get_desktop_active_binding.return_value = SimpleNamespace(session_id=sid, owner_user_id=user)
    runtime.realtime.repository.get_desktop_device_by_code.return_value.capabilities = {
        "protocolVersion": "2.0", "appVersion": "1.3.2", "microphone": "unknown", "systemAudio": "unknown"}
    with client.websocket_connect(f"/api/v1/mock-interviews/{sid}/control") as browser:
        browser.send_json({"accessToken": "synthetic-owner"})
        initial = browser.receive_json()
        assert initial["desktopConnected"] and not initial["microphoneConnected"]
        assert initial["preparation"]["code"] == "mock_permission_deferred"
        assert initial["session"]["billedMinutes"] == 0
        browser.send_json({"action": "start", "version": initial["session"]["state"]["version"]})
        state = receive_type(browser, "state")["session"]["state"]
        if state["phase"] == "generating_question": state = receive_type(browser, "state")["session"]["state"]
        assert state["phase"] == "speaking"
        assert runtime.repository.get(user_id=user, session_id=sid)["data"]["clock_at_ms"] is None
        body = {"userId": user, "sessionId": sid, "sourceKind": "microphone", "clientName": "synthetic-shipped-companion", "deviceId": "device", "manualCode": "000000"}
        response = client.post("/api/v1/realtime-speech/publishers", json=body)
        assert response.status_code == 200, response.text
        token = response.json()["data"]["token"]
        assert client.post("/api/v1/realtime-speech/publishers", json=body).json()["data"]["token"] == token
        url = f"/api/v1/realtime-speech/ingest-ws?token={token}&protocol=2.0&media={media}"
        with client.websocket_connect(url) as desktop:
            hello = desktop.receive_json()
            assert hello["payload"]["resumeOffsets"]["microphone"] == -1
            assert receive_type(browser, "state")["microphoneConnected"]
            def upload(seq, started, *, final=False):
                data = {**wire(), "sequence": seq, "startedAtMs": started, "capturedAtMs": runtime.now_ms(),
                        "endedAtMs": runtime.now_ms(), "isFinal": final, "terminalId": "terminal" if final else None}
                if media == "binary-v1":
                    data.pop("audioBase64")
                    header = json.dumps(data).encode()
                    desktop.send_bytes(len(header).to_bytes(4, "big") + header + b"00"*1600)
                else: desktop.send_json(data)
                return desktop.receive_json()
            assert upload(0, runtime.now_ms())["kind"] == "frame-accepted"
            assert runtime.audio.snapshot()["captures"] == 0  # Playback is not ASR.
            browser.send_json({"action": "listen", "version": state["version"], "questionId": state["rounds"][-1]["question_id"]})
            state = receive_type(browser, "state")["session"]["state"]
            capture = runtime.audio._captures[sid]
            capture.gateway.transcribe.return_value = TranscriptResult("旧版助手的合成回答", .9)
            assert upload(1, runtime.now_ms() - 1000)["kind"] == "frame-accepted"  # Late crossing segment.
            capture.gateway.transcribe.assert_not_called()
            assert upload(2, runtime.now_ms(), final=True)["kind"] == "terminal-accepted"
            assert upload(2, runtime.now_ms(), final=True)["payload"]["duplicate"]
            assert receive_type(browser, "transcript")["text"] == "旧版助手的合成回答"
            capture.gateway.transcribe.assert_called_once()
        paused = receive_type(browser, "state")
        assert paused["session"]["state"]["phase"] == "paused"
        assert not paused["session"]["interacting"] and not paused["microphoneConnected"]
        assert runtime.audio.snapshot()["captures"] == 0
        with client.websocket_connect(url) as desktop:
            assert desktop.receive_json()["payload"]["resumeOffsets"]["microphone"] == 2
            state = receive_type(browser, "state")["session"]["state"]
            assert state["phase"] == "paused"  # Reconnect never silently starts billing/audio.
            browser.send_json({"action": "end", "version": state["version"]})
            state = receive_type(browser, "state")["session"]["state"]
            if state["phase"] == "generating_report": state = receive_type(browser, "state")["session"]["state"]
            assert state["phase"] == "completed"
    assert not runtime.legacy.sessions and not runtime.desktops and not runtime.controllers
    assert runtime.repository.get(user_id=user, session_id=sid)["data"]["billed_minutes"] == 1
    runtime.realtime.create_publisher.assert_not_called()
    runtime.realtime.connect_publisher.assert_not_called()
    runtime.realtime.enqueue_audio_frame.assert_not_called()


def test_legacy_random_token_cannot_allocate_controller_or_asr(client_runtime, monkeypatch):
    client, runtime, user, sid = client_runtime
    client.app.include_router(realtime_api.router, prefix="/api/v1")
    monkeypatch.setattr(realtime_api, "realtime_speech_service", lambda: runtime.realtime)
    with client.websocket_connect("/api/v1/realtime-speech/ingest-ws?token=rt-mock-forged") as desktop:
        assert desktop.receive_json()["kind"] == "connection-rejected"
    assert not runtime.controllers and not runtime.legacy.sessions and runtime.audio.snapshot()["captures"] == 0


@pytest.mark.parametrize("reason,code", [("denied", "mock_microphone_required"), ("offline", "mock_desktop_unavailable")])
def test_readiness_explains_failure_and_recovers_same_paid_session(client_runtime, reason, code):
    client, runtime, user, sid = client_runtime
    device = runtime.realtime.repository.get_desktop_device_by_code.return_value
    device.capabilities = {"protocolVersion": "2.0", "appVersion": "1.3.2", "microphone": "unknown"}
    if reason == "denied": device.capabilities["microphone"] = "denied"
    if reason == "offline": runtime.realtime._desktop_device_fresh.return_value = False
    with client.websocket_connect(f"/api/v1/mock-interviews/{sid}/control") as browser:
        browser.send_json({"accessToken": "synthetic-owner"})
        initial = browser.receive_json()
        assert initial["preparation"]["code"] == code
        assert not initial["preparation"]["ready"] and not initial["desktopConnected"]
        assert initial["preparation"]["message"]
        browser.send_json({"action": "start", "version": initial["session"]["state"]["version"]})
        assert receive_type(browser, "error")["code"] == code
        rejected = receive_type(browser, "state")
        assert rejected["session"]["state"]["phase"] == "preparing"
        assert rejected["session"]["billedMinutes"] == 0
        device.capabilities["microphone"] = "unknown"
        runtime.realtime._desktop_device_fresh.return_value = True
        browser.send_json({"action": "heartbeat"})
        ready = receive_type(browser, "state")
        assert ready["desktopConnected"] and ready["preparation"]["ready"]
        assert not ready["microphoneConnected"]
        assert ready["session"]["sessionId"] == sid
        assert ready["session"]["state"]["version"] == initial["session"]["state"]["version"]
        assert ready["session"]["billedMinutes"] == 0 and not ready["session"]["interacting"]
    assert runtime.repository.quote(user, runtime.now_ms())["savedCount"] == 1
