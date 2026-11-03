"""Synthetic route/executor tests; no application lifespan or external service."""
from __future__ import annotations

import asyncio
import logging
import threading
from types import SimpleNamespace
from unittest.mock import Mock

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
import pytest

from app import deps
from app.core.config import Settings
from app.core.errors import DomainRequestError, install_exception_handlers
from app.modules import realtime_speech as routes
from app.ports.authentication import AuthenticatedRequestContext
from app.schemas.realtime_speech import RealtimeDeviceStatusRequest, RealtimeEventResponse
from app.services.realtime_control_executor import RealtimeControlExecutor


OWNER = "synthetic-device-status-owner"
SESSION = "synthetic-device-status-session"
EVENT = RealtimeEventResponse(eventId="synthetic-event", kind="device-status", payload={"captureState": "ready"}, createdAtMs=1)


def body(**updates):
    return {"deviceId": "synthetic-device", "captureState": "ready", **updates}


def service(edition="cn"):
    return SimpleNamespace(
        settings=Settings(_env_file=None, product_edition=edition),
        publish_cn_device_status=Mock(return_value=EVENT),
        publish_device_status=Mock(return_value=EVENT),
        get_desktop_active_binding=Mock(return_value=SimpleNamespace(session_id=SESSION, owner_user_id=OWNER)),
    )


def application(monkeypatch, target, *, production=False):
    app = FastAPI()
    app.include_router(routes.router, prefix="/api/v1")
    app.dependency_overrides[deps.realtime_speech_service] = lambda: target
    settings = Settings(_env_file=None, environment="production" if production else "test")
    monkeypatch.setattr(deps, "get_settings", lambda: settings)
    install_exception_handlers(app, settings=settings, logger=logging.getLogger("synthetic-route-test"))
    return app


def test_cn_manual_code_dispatches_one_complete_job(monkeypatch):
    target = service()
    app = application(monkeypatch, target, production=True)
    with TestClient(app) as client:
        response = client.post(f"/api/v1/realtime-speech/sessions/{SESSION}/device-status", json=body(manualCode="123456", userId="ignored-legacy-id"))
    assert response.status_code == 200
    assert response.json()["data"] == EVENT.model_dump(by_alias=True)
    target.publish_cn_device_status.assert_called_once_with(user_id=None, session_id=SESSION,
        device_id="synthetic-device", manual_code="123456", capture_state="ready", source_health=[], capabilities={})
    target.get_desktop_active_binding.assert_not_called()
    target.publish_device_status.assert_not_called()


@pytest.mark.parametrize("authorization", ["Basic synthetic", "Bearer ", "Bearer synthetic-invalid"])
def test_invalid_auth_still_rejected_before_manual_code_dispatch(monkeypatch, authorization):
    target = service()
    app = application(monkeypatch, target, production=True)
    auth = Mock()
    auth.authenticate_access_token.side_effect = DomainRequestError("authentication", "token", "synthetic invalid token", 401)
    monkeypatch.setattr(deps, "authentication_service", lambda: auth)
    with TestClient(app) as client:
        response = client.post(f"/api/v1/realtime-speech/sessions/{SESSION}/device-status", json=body(manualCode="123456"), headers={"Authorization": authorization})
    assert response.status_code == 401
    target.publish_cn_device_status.assert_not_called()


@pytest.mark.parametrize("explicit,status", [(None, 200), (OWNER, 200), ("synthetic-foreign", 403)])
def test_no_code_retains_bearer_owner_resolution(monkeypatch, explicit, status):
    target = service()
    app = application(monkeypatch, target, production=True)
    app.dependency_overrides[deps.optional_authenticated_context] = lambda: AuthenticatedRequestContext(OWNER, "synthetic", "synthetic-auth")
    with TestClient(app) as client:
        response = client.post(f"/api/v1/realtime-speech/sessions/{SESSION}/device-status", json=body(**({"userId": explicit} if explicit else {})))
    assert response.status_code == status
    if status == 200:
        assert target.publish_cn_device_status.call_args.kwargs["user_id"] == OWNER
        assert target.publish_cn_device_status.call_args.kwargs["manual_code"] is None
    else:
        target.publish_cn_device_status.assert_not_called()


def test_production_no_bearer_cannot_dispatch_legacy_status(monkeypatch):
    target = service()
    app = application(monkeypatch, target, production=True)
    with TestClient(app) as client:
        response = client.post(f"/api/v1/realtime-speech/sessions/{SESSION}/device-status", json=body(userId=OWNER))
    assert response.status_code == 401
    target.publish_cn_device_status.assert_not_called()


@pytest.mark.parametrize("manual", [False, True])
def test_global_retains_original_service_calls(monkeypatch, manual):
    target = service("global")
    app = application(monkeypatch, target)
    with TestClient(app) as client:
        response = client.post(f"/api/v1/realtime-speech/sessions/{SESSION}/device-status", json=body(**({"manualCode": "123456"} if manual else {"userId": OWNER})))
    assert response.status_code == 200
    target.publish_cn_device_status.assert_not_called()
    target.publish_device_status.assert_called_once()
    assert target.publish_device_status.call_args.kwargs["user_id"] == OWNER
    assert target.get_desktop_active_binding.call_count == int(manual)


def test_domain_error_wire_contract_survives_worker(monkeypatch):
    target = service()
    app = application(monkeypatch, target)
    target.publish_cn_device_status.side_effect = DomainRequestError("realtime-speech", "device-status", "该设备已连接到另一场面试，请刷新当前连接。", 410, "desktop_binding_replaced")
    with TestClient(app) as client:
        response = client.post(f"/api/v1/realtime-speech/sessions/{SESSION}/device-status", json=body(manualCode="123456"))
    assert response.status_code == 410
    assert response.json()["error"]["details"]["errorCode"] == "desktop_binding_replaced"
    assert response.json()["error"]["message"] == "该设备已连接到另一场面试，请刷新当前连接。"
    assert target.publish_cn_device_status.call_count == 1


@pytest.mark.parametrize("configured", [False, True])
def test_slow_device_status_worker_leaves_loop_responsive(configured):
    async def scenario():
        executor = RealtimeControlExecutor(max_workers=1, queue_max=1) if configured else None
        app = FastAPI()
        if executor:
            app.state.realtime_control_executor = executor
        request = Request({"type": "http", "app": app})
        target = service()
        started, release = threading.Event(), threading.Event()
        worker_threads = []
        calls = []

        def slow(**kwargs):
            worker_threads.append(threading.get_ident())
            calls.append(kwargs)
            started.set()
            assert release.wait(2), "event loop failed to release blocked worker"
            return EVENT

        target.publish_cn_device_status = slow
        task = asyncio.create_task(routes.publish_device_status(SESSION, request,
            RealtimeDeviceStatusRequest(**body(manualCode="123456")), None, target))
        try:
            for _ in range(100):
                if started.is_set():
                    break
                await asyncio.sleep(0.005)
            assert started.is_set()
            assert not task.done()
            assert worker_threads == [worker_threads[0]]
            assert worker_threads[0] != threading.get_ident()
            # This line must run while synchronous repository work is blocked.
            release.set()
            result = await asyncio.wait_for(task, 2)
            assert result.data == EVENT.model_dump(by_alias=True)
            assert len(calls) == 1
            if executor:
                assert executor.diagnostics()["submitted"] == 1
        finally:
            release.set()
            if not task.done():
                await asyncio.wait_for(task, 2)
            if executor:
                executor.shutdown()

    asyncio.run(scenario())
