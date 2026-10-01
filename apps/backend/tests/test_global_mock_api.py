"""Global HTTP/WS lifecycle with a real isolated DB and synthetic providers/device."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.modules import mock_interview as api
from app.schemas.mock_interview import MockQuestion, MockReport
from app.services.global_usage_billing_adapter import GlobalUsageBillingAdapter
from app.services.mock_interview_audio import MockInterviewAudio
from app.services.mock_interview_jobs import MockInterviewJobs
from app.services.mock_interview_runtime import MockInterviewRuntime
from app.services.realtime_speech_service import RealtimeSpeechService
from test_global_mock_postgres import repos, member, NOW, pytestmark
from test_mock_interview_api import receive_type


def test_global_http_control_round_uses_only_global_entitlements(repos, monkeypatch):
    repo, commerce, _ = repos
    user, _ = member(commerce)
    reader = Mock()
    reader.read.return_value = "SYNTHETIC: Built a bounded cache."
    generator = SimpleNamespace(
        question=AsyncMock(return_value=MockQuestion(question="How did you test eviction?", focus="Cache validation")),
        report=AsyncMock(return_value=MockReport(summary="No confirmed answers; no score.")))
    realtime = Mock()
    realtime.session_service.get_session.return_value = SimpleNamespace(status="live", session_mode="mock")
    realtime.get_desktop_binding.return_value = SimpleNamespace(device_id="synthetic-device", binding_generation=1, status="bound", manual_code="000000")
    realtime.repository.get_desktop_device_by_code.return_value = SimpleNamespace(device_id="synthetic-device", generation=1,
        capabilities={"protocolVersion": "2.0", "microphone": "unknown"})
    realtime._desktop_device_fresh.return_value = True
    realtime._permission_status.side_effect = RealtimeSpeechService._permission_status
    runtime = MockInterviewRuntime(repo, reader, MockInterviewJobs(repo, reader, generator, now_ms=lambda: NOW), Mock(),
        MockInterviewAudio(Mock(), now_ms=lambda: NOW, interview_language="en-US"), realtime, now_ms=lambda: NOW)
    settings = Settings(_env_file=None, product_edition="global", global_mock_interview_enabled=True)
    monkeypatch.setattr(api, "get_settings", lambda: settings)
    domestic = Mock(side_effect=AssertionError("Must not instantiate CN billing"))
    monkeypatch.setattr(api, "billing_service", domestic)
    monkeypatch.setattr(api, "usage_billing_service", lambda: GlobalUsageBillingAdapter(commerce))
    app = FastAPI()
    app.include_router(api.router, prefix="/api/v1")
    app.dependency_overrides[api.require_mock_runtime] = lambda: runtime
    app.dependency_overrides[api.require_authenticated_context] = lambda: SimpleNamespace(user_id=user)
    monkeypatch.setattr(api, "require_mock_runtime", lambda: runtime)
    monkeypatch.setattr(api, "authentication_service", lambda: SimpleNamespace(
        authenticate_access_token=lambda **kw: SimpleNamespace(user_id=user)))
    with TestClient(app) as client:
        response = client.post("/api/v1/mock-interviews", json={"title": "Synthetic English practice",
            "targetRole": "Backend engineer", "idempotencyKey": "synthetic-http", "expectedBillingClass": "daily_pass_free"})
        response.raise_for_status()
        sid = response.json()["data"]["sessionId"]
        client.post(f"/api/v1/mock-interviews/{sid}/resume", json={"documentId": "synthetic-resume",
            "documentVersionId": "v1", "version": 0}).raise_for_status()
        with client.websocket_connect(f"/api/v1/mock-interviews/{sid}/control") as socket:
            socket.send_json({"accessToken": "synthetic-owner"})
            initial = receive_type(socket, "state")["session"]
            socket.send_json({"action": "start", "version": initial["state"]["version"]})
            for _ in range(5):
                current = receive_type(socket, "state")["session"]
                if current["state"]["phase"] == "speaking":
                    break
            assert current["state"]["rounds"][0]["question"] == "How did you test eviction?"
            socket.send_json({"action": "end", "version": current["state"]["version"]})
            for _ in range(5):
                current = receive_type(socket, "state")["session"]
                if current["state"]["phase"] == "completed":
                    break
            assert current["state"]["phase"] == "completed"
            assert current["report"]["overall_score"] is None
            assert current["billableMs"] == 0 and current["billedMinutes"] == 0
        listing = client.get("/api/v1/mock-interviews").json()["data"]
        assert listing["quote"]["dailyFreeRemaining"] == 2
        assert listing["quote"]["entryPoints"] == listing["quote"]["minutePoints"] == 0
        assert len(listing["sessions"]) == 1
    domestic.assert_not_called()
    assert runtime.controllers == {} and runtime.audio.snapshot()["captures"] == 0
    asyncio.run(runtime.shutdown())
