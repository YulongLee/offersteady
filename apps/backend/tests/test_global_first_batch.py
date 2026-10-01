from dataclasses import asdict
import json
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.deps import chat_service, realtime_speech_service
from app.main import create_app
from app.modules.live_answer import _to_stream_event
from app.ports.chat import ChatAnswerChunk, ChatAnswerTaskRecord
from app.services.billing_service import UsageReservationRecord
from app.services.chat_service import NonRetryableChatError
from app.services.global_commerce_repository import InMemoryGlobalCommerceRepository
from app.services.global_commerce_service import GlobalCommerceService
from app.services.global_usage_billing_adapter import GlobalUsageBillingAdapter
from app.services.postgres_billing_repository import PostgresBillingRepository


def test_reservation_output_excludes_policy_inputs(monkeypatch):
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    cursor.fetchone.side_effect = [None, None, {"balance": 0}, {"reserved": 0}]
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.cursor.return_value = cursor
    repository = object.__new__(PostgresBillingRepository)
    monkeypatch.setattr(repository, "_connect", lambda: connection)
    record = UsageReservationRecord(**repository.reserve_usage(usage={
        "reservation_id": "synthetic", "usage_id": "synthetic", "user_id": "synthetic",
        "usage_kind": "answer", "points_reserved": 5, "wallet_only": True,
        "policy_input_not_in_result": None,
    }, created_at_ms=1))
    assert record.status == "insufficient_balance"
    assert record.wallet_only
    connection.commit.assert_not_called()


@pytest.mark.parametrize("automatic", [False, True])
def test_startup_denial_precedes_headers_and_releases_claim(automatic):
    application = create_app()
    def denied(**kwargs):
        raise DomainRequestError("live-answer", "reserve", "Synthetic entitlement denial", 409)
        yield  # This is intentionally a lazy generator like the actual service.
    service = SimpleNamespace(stream_answer_question=denied)
    realtime = MagicMock()
    realtime.claim_auto_answer_candidate.return_value = SimpleNamespace(candidate_id="candidate", answer_task_id="claim")
    application.dependency_overrides[chat_service] = lambda: service
    application.dependency_overrides[realtime_speech_service] = lambda: realtime
    with TestClient(application) as client:
        response = client.post("/api/v1/live-answer/questions/stream", json={
            "userId": "synthetic", "sessionId": "synthetic", "question": "Synthetic question?",
            "triggerMode": "auto" if automatic else "manual", "questionId": "candidate",
        })
        assert response.status_code == 409
        assert response.json()["success"] is False
        assert "text/event-stream" not in response.headers["content-type"]
        assert client.app.state.live_answer_stream_executor.diagnostics()["active"] == 0
    assert realtime.release_auto_answer_candidate.call_count == int(automatic)


@pytest.mark.parametrize("outcome", ["success", "detail-failure", "cancel"])
def test_quick_completion_precedes_detail_and_preserves_global_billing(monkeypatch, outcome):
    user_id = "synthetic-global-" + uuid4().hex
    commerce = GlobalCommerceService(Settings(_env_file=None, product_edition="global"), InMemoryGlobalCommerceRepository())
    billing = GlobalUsageBillingAdapter(commerce)
    with TestClient(create_app()) as client:
        response = client.post("/api/v1/sessions", json={"userId": user_id, "title": "Synthetic Global", "interviewLanguage": "en-US"})
        response.raise_for_status()
        session_id = response.json()["data"]["sessionId"]
        client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": user_id}).raise_for_status()
        service = chat_service()
        monkeypatch.setattr(service, "billing_service", billing)
        monkeypatch.setattr(service, "settings", service.settings.model_copy(update={"product_edition": "global", "chat_detail_retrieval_prefetch_enabled": False}))
        quick_seen = False
        stages = []
        retrieve = service._retrieve_context
        def retrieval(**kwargs):
            assert quick_seen, "Detail retrieval blocked completion of the quick stage"
            return retrieve(**kwargs)
        monkeypatch.setattr(service, "_retrieve_context", retrieval)
        def model(*, question, prompt, attempt):
            stage = prompt.prompt_config.template_id
            stages.append(stage)
            if "detail" in stage:
                assert quick_seen
                if outcome == "detail-failure":
                    raise NonRetryableChatError("Synthetic detail failure")
                yield ChatAnswerChunk(sequence=1, text="Use a bounded cache and verify eviction under load.", is_final=True, provider_finish_reason="stop")
            else:
                yield ChatAnswerChunk(sequence=1, text=f"<normalized_question>{question}</normalized_question>Use bounded caching and measure latency before changing capacity.", is_final=True, provider_finish_reason="stop")
        monkeypatch.setattr(service.llm_gateway, "stream_generate", model)
        usage_id = "synthetic-usage-" + uuid4().hex
        events = []
        for event in service.stream_answer_question(user_id=user_id, session_id=session_id, question="How do you design a cache?", usage_id=usage_id):
            events.append(event)
            if event["type"] == "quick-completed":
                quick_seen = True
                task = event["task"]
                assert task.quick_answer_completed and task.status == "streaming"
                assert billing._records[usage_id].status == "reserved"
                assert _to_stream_event(event).model_dump(by_alias=True)["task"]["quickAnswerCompleted"]
                if outcome == "cancel":
                    service.cancel_task(user_id=user_id, task_id=task.task_id)
        assert quick_seen
        assert sum(item["type"] == "quick-completed" for item in events) == 1
        assert events[-1]["type"] == {"success": "completed", "detail-failure": "failed", "cancel": "cancelled"}[outcome]
        assert "Use bounded caching" in events[-1]["task"].answer_text
        assert billing._records[usage_id].status == ("settled" if outcome == "success" else "released")
        assert commerce.state(user_id)["copilot"]["remaining"] == 15
        assert sum("quick" in stage for stage in stages) == 1
        client.post(f"/api/v1/sessions/{session_id}/end", json={"userId": user_id}).raise_for_status()


def test_task_defaults_and_stream_first_event_exactly_once():
    task = ChatAnswerTaskRecord(task_id="synthetic", session_id="synthetic", owner_user_id="synthetic", question="Synthetic?", answer_text="Quick answer.", status="streaming", stream_mode=True)
    assert not task.quick_answer_completed
    values = asdict(task)
    values.pop("quick_answer_completed")
    assert not ChatAnswerTaskRecord(**values).quick_answer_completed
    application = create_app()
    def stream(**kwargs):
        yield {"type": "task-started", "task": task}
        yield {"type": "quick-completed", "task": task}
        yield {"type": "completed", "task": task}
    application.dependency_overrides[chat_service] = lambda: SimpleNamespace(stream_answer_question=stream)
    application.dependency_overrides[realtime_speech_service] = lambda: MagicMock()
    with TestClient(application) as client:
        response = client.post("/api/v1/live-answer/questions/stream", json={"userId": "synthetic", "sessionId": "synthetic", "question": "Synthetic?"})
    assert response.status_code == 200
    events = [json.loads(line[6:])["type"] for line in response.text.splitlines() if line.startswith("data: ")]
    assert events == ["task-started", "quick-completed", "completed"]
