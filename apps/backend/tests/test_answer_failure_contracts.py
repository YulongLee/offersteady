from __future__ import annotations

import json
from time import sleep
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.deps import chat_service, realtime_speech_service
from app.main import create_app
from app.services.billing_service import BillingService
from app.services.postgres_billing_repository import PostgresBillingRepository


@pytest.fixture
def api_client():
    # Production creates the stream executor in lifespan; run the same startup.
    with TestClient(create_app()) as client:
        yield client


def insufficient_postgres_billing(monkeypatch, *, balance=0, reserved=0):
    # Exercise the real repository return branch, without any real user data.
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    cursor.fetchone.side_effect = [None, None, {"balance": balance}, {"reserved": reserved}]
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.cursor.return_value = cursor
    repository = object.__new__(PostgresBillingRepository)
    monkeypatch.setattr(repository, "_connect", lambda: connection)
    service = BillingService(Settings(_env_file=None, environment="test"), billing_repository=repository)
    monkeypatch.setattr(service, "_ensure_welcome_grant", lambda **kwargs: None)
    monkeypatch.setattr(service, "_release_stale_usage_reservations", lambda **kwargs: 0)
    monkeypatch.setattr(service, "rates", lambda: {
        "answerPoints": 5, "webSearchAnswerPoints": 20, "screenshotAnswerPoints": 15,
        "realtimeMinutePoints": 5, "writtenExamPoints": 30,
    })
    return service, cursor, connection


@pytest.mark.parametrize("kind,minimum_days,cost", [
    ("answer", None, 5), ("web_answer", 7, 20), ("screenshot_answer", None, 15),
    ("realtime_minute", None, 5), ("written_exam_entry", None, 30),
])
@pytest.mark.parametrize("balance,reserved", [(0, 0), (100, 100)])
def test_postgres_insufficient_balance_excludes_policy_fields(monkeypatch, kind, minimum_days, cost, balance, reserved):
    service, cursor, connection = insufficient_postgres_billing(monkeypatch, balance=balance, reserved=reserved)
    reservation = service.reserve_usage(
        user_id="synthetic-user", usage_id="synthetic-usage", usage_kind=kind,
        minimum_pass_duration_days=minimum_days,
    )
    assert reservation.status == "insufficient_balance"
    assert reservation.points_reserved == cost
    assert reservation.billing_source == "points"
    assert "minimum_pass_duration_days" not in vars(reservation)
    assert not any("INSERT" in call.args[0] for call in cursor.execute.call_args_list)
    connection.commit.assert_not_called()
    if minimum_days is not None:
        assert any("product.duration_days >= %s" in call.args[0] and call.args[1][-1] == 7
                   for call in cursor.execute.call_args_list)


@pytest.mark.parametrize("web_enabled", [False, True])
@pytest.mark.parametrize("streaming", [False, True])
@pytest.mark.parametrize("trigger", ["manual", "auto"])
def test_answer_stream_returns_recoverable_billing_error_from_postgres(monkeypatch, api_client, web_enabled, streaming, trigger):
    client = api_client
    user_id = f"synthetic-billing-contract-{uuid4().hex}"
    created = client.post("/api/v1/sessions", json={"userId": user_id, "title": "Synthetic billing regression"})
    created.raise_for_status()
    session_id = created.json()["data"]["sessionId"]
    client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": user_id}).raise_for_status()
    service, _, _ = insufficient_postgres_billing(monkeypatch)
    chat = chat_service()
    monkeypatch.setattr(chat, "billing_service", service)
    model = MagicMock(side_effect=AssertionError("Insufficient balance must not call a model"))
    monkeypatch.setattr(chat.llm_gateway, "stream_generate", model)
    realtime = realtime_speech_service()
    release_claim = MagicMock()
    if trigger == "auto":
        monkeypatch.setattr(realtime, "claim_auto_answer_candidate", MagicMock(return_value=SimpleNamespace(
            candidate_id="synthetic-candidate", answer_task_id="synthetic-claim",
        )))
        monkeypatch.setattr(realtime, "release_auto_answer_candidate", release_claim)
    route = "/api/v1/live-answer/questions" + ("/stream" if streaming else "")
    response = client.post(route, json={
        "userId": user_id, "sessionId": session_id,
        "question": "Explain synthetic testing.", "webSearchEnabled": web_enabled,
        "triggerMode": trigger, "questionId": "synthetic-candidate",
    })
    assert response.status_code == 409, response.text
    assert response.json()["success"] is False
    assert "积分" in response.json()["error"]["message"]
    if web_enabled:
        assert response.json()["error"]["details"]["errorCode"] == "web_search_points_insufficient"
    model.assert_not_called()
    if trigger == "auto":
        release_claim.assert_called_once()
    if streaming:
        executor = client.app.state.live_answer_stream_executor
        for _ in range(100):
            if executor.diagnostics()["completed"] == executor.diagnostics()["submitted"]:
                break
            sleep(0.001)
        assert executor.diagnostics()["active"] == 0
        assert executor.diagnostics()["completed"] == executor.diagnostics()["submitted"]
    client.post(f"/api/v1/sessions/{session_id}/end", json={"userId": user_id}).raise_for_status()


def test_successful_stream_keeps_first_event_once_and_completes(api_client):
    user_id = f"synthetic-stream-success-{uuid4().hex}"
    session_id = api_client.post("/api/v1/sessions", json={
        "userId": user_id, "title": "Synthetic stream success",
    }).json()["data"]["sessionId"]
    api_client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": user_id}).raise_for_status()
    response = api_client.post("/api/v1/live-answer/questions/stream", json={
        "userId": user_id, "sessionId": session_id, "question": "如何编写合成回归测试？",
    })
    assert response.status_code == 200
    events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
    assert events[0]["type"] == "task-started"
    assert sum(item["type"] == "task-started" for item in events) == 1
    assert events[-1]["type"] == "completed"
    sequences = [item["chunk"]["sequence"] for item in events if item["type"] == "chunk"]
    assert sequences == list(range(1, len(sequences) + 1))
    assert events[-1]["task"]["answerText"]
    api_client.post(f"/api/v1/sessions/{session_id}/end", json={"userId": user_id}).raise_for_status()
