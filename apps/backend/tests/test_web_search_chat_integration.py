from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import Request
from app.deps import chat_service as chat_service_dep
from app.main import create_app
from app.modules import live_answer
from app.ports.chat import ChatAnswerChunk
from app.ports.web_search import WebSearchAnswer, WebSearchSource
from app.schemas.live_answer import LiveAnswerQuestionRequest
from app.services.billing_service import BillingService
from app.services.live_answer_stream_executor import LiveAnswerStreamExecutor
from fastapi.testclient import TestClient


def _unwrap(response):
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["success"] is True
    return payload["data"]


def test_stream_search_is_detailed_only_and_propagates_sources(monkeypatch) -> None:
    client = TestClient(create_app())
    user_id = "web-search-chat-integration-user"
    session = _unwrap(client.post("/api/v1/sessions", json={"userId": user_id, "title": "联网回答测试"}))
    session_id = session["sessionId"]
    _unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": user_id}))

    service = chat_service_dep()
    calls: list[str] = []

    class FakeWebSearch:
        def answer(self, **kwargs):
            calls.append(str(kwargs["question"]))
            return WebSearchAnswer(
                answer_text="联网补充：该方案应先确认官方接口契约，再验证缓存失效策略。",
                sources=[WebSearchSource(title="官方文档", url="https://example.com/docs", snippet="官方说明")],
                status="succeeded",
                provider="dashscope-web-search",
            )

    def quick_only_stream(*, question, prompt, attempt):
        assert prompt.prompt_config.template_id == "interview-chat-quick"
        yield ChatAnswerChunk(sequence=1, text=f"<normalized_question>{question}</normalized_question>先给结论。", is_final=False)
        yield ChatAnswerChunk(sequence=2, text="再说明执行步骤。", is_final=True)

    monkeypatch.setattr(service, "web_search_gateway", FakeWebSearch())
    monkeypatch.setattr(service.llm_gateway, "stream_generate", quick_only_stream)

    events = list(service.stream_answer_question(
        user_id=user_id,
        session_id=session_id,
        question="如何验证接口契约？",
        web_search_enabled=True,
    ))

    assert calls == ["如何验证接口契约？"]
    assert events[-1]["type"] == "completed"
    task = events[-1]["task"]
    assert task.status == "completed"
    assert task.web_search_status == "succeeded"
    assert task.web_sources[0]["url"] == "https://example.com/docs"
    assert "联网补充" in task.answer_text


def _start_synthetic_session(monkeypatch, suffix):
    client = TestClient(create_app())
    user_id = f"synthetic-web-switch-{suffix}"
    session = _unwrap(client.post("/api/v1/sessions", json={"userId": user_id, "title": "合成切换测试"}))
    session_id = session["sessionId"]
    _unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": user_id}))
    service = chat_service_dep()
    monkeypatch.setattr(service, "billing_service", BillingService())

    def local_stream(*, question, prompt, attempt):
        yield ChatAnswerChunk(sequence=1, text=f"<normalized_question>{question}</normalized_question>先给结论，再说明依据。", is_final=True)

    monkeypatch.setattr(service.llm_gateway, "stream_generate", local_stream)
    return service, user_id, session_id


@pytest.mark.parametrize("search_status", ["succeeded", "unavailable", "disabled"])
def test_quick_completion_precedes_detail_wait_and_does_not_settle_usage(monkeypatch, search_status):
    from app.services import chat_service as chat_service_module

    service, user_id, session_id = _start_synthetic_session(monkeypatch, f"quick-boundary-{search_status}")
    calls = []
    quick_seen = False

    def submit(fn, *args, **kwargs):
        def result():
            assert quick_seen, "Detailed retrieval must not hold up the quick completion event"
            calls.append("retrieval")
            return fn(*args, **kwargs)
        return SimpleNamespace(result=result)

    def search(**kwargs):
        assert quick_seen
        calls.append("web")
        return WebSearchAnswer(answer_text="合成联网详细回答。", status=search_status)

    monkeypatch.setattr(chat_service_module, "_DETAIL_RETRIEVAL_EXECUTOR", SimpleNamespace(submit=submit))
    monkeypatch.setattr(service, "web_search_gateway", SimpleNamespace(answer=search))
    usage_id = f"quick-boundary:{session_id}"
    events = []
    for event in service.stream_answer_question(
        user_id=user_id, session_id=session_id, question="如何设计缓存？",
        usage_id=usage_id, web_search_enabled=search_status != "disabled",
    ):
        events.append(event)
        if event["type"] == "quick-completed":
            quick_seen = True
            assert calls == []
            task = event["task"]
            assert task.quick_answer_completed is True
            assert task.status == "streaming"
            assert task.completed_at_ms is None
            assert "先给结论" in task.answer_text
            assert "详细回答" not in task.answer_text
            assert service.get_task(user_id=user_id, task_id=task.task_id).quick_answer_completed
            assert service.billing_service.usage_reservations_by_id[usage_id].status == "reserved"
            response = live_answer._to_stream_event(event)
            assert response.type == "quick-completed"
            assert response.task.model_dump(by_alias=True)["quickAnswerCompleted"] is True
    assert quick_seen
    assert sum(event["type"] == "quick-completed" for event in events) == 1
    assert events[-1]["type"] == "completed"
    assert events[-1]["task"].quick_answer_completed is True
    assert calls.count("web") == (0 if search_status == "disabled" else 1)


def test_cancel_at_quick_completion_never_starts_web_search(monkeypatch):
    service, user_id, session_id = _start_synthetic_session(monkeypatch, "cancel-quick-boundary")
    calls = []
    monkeypatch.setattr(service, "web_search_gateway", SimpleNamespace(answer=lambda **kwargs: calls.append(kwargs)))
    events = []
    for event in service.stream_answer_question(
        user_id=user_id, session_id=session_id, question="如何设计缓存？", web_search_enabled=True,
    ):
        events.append(event)
        if event["type"] == "quick-completed":
            service.cancel_task(user_id=user_id, task_id=event["task"].task_id)
    assert events[-1]["type"] == "cancelled"
    assert events[-1]["task"].quick_answer_completed is True
    assert "先给结论" in events[-1]["task"].answer_text
    assert calls == []
    assert service.billing_service.state_for_user(user_id=user_id).balance == 200


@pytest.mark.parametrize("search_status", ["succeeded", "unavailable"])
def test_cancel_during_search_does_not_revive_task_or_charge(monkeypatch, search_status):
    service, user_id, session_id = _start_synthetic_session(monkeypatch, search_status)
    task_ids = []

    class LateSearch:
        def answer(self, **kwargs):
            outcome, _ = service.cancel_task(user_id=user_id, task_id=task_ids[0])
            assert outcome == "cancelled"
            return WebSearchAnswer(answer_text="迟到的联网结果", status=search_status)

    monkeypatch.setattr(service, "web_search_gateway", LateSearch())
    events = []
    for event in service.stream_answer_question(
        user_id=user_id, session_id=session_id, question="如何设计缓存？",
        usage_id=f"manual:{session_id}:web:attempt-1", web_search_enabled=True,
    ):
        task_ids.append(event["task"].task_id)
        events.append(event)
    assert events[-1]["type"] == "cancelled"
    task = service.get_task(user_id=user_id, task_id=task_ids[0])
    assert task.status == "cancelled"
    assert "迟到的联网结果" not in task.answer_text
    assert service.billing_service.state_for_user(user_id=user_id).balance == 200
    reservation = service.billing_service.usage_reservations_by_id[f"manual:{session_id}:web:attempt-1"]
    assert reservation.status == "released"

    # The same question can immediately use a fresh ordinary request.
    local = list(service.stream_answer_question(
        user_id=user_id, session_id=session_id, question="如何设计缓存？",
        usage_id=f"manual:{session_id}:local:attempt-2", web_search_enabled=False,
    ))[-1]
    assert local["type"] == "completed"
    assert local["task"].web_search_status == "disabled"
    assert service.billing_service.state_for_user(user_id=user_id).balance == 195


def test_cancelling_after_search_before_detail_delivery_releases_usage(monkeypatch):
    service, user_id, session_id = _start_synthetic_session(monkeypatch, "after-search")
    monkeypatch.setattr(service, "web_search_gateway", SimpleNamespace(
        answer=lambda **kwargs: WebSearchAnswer(answer_text="不应再显示的详细回答", status="succeeded"),
    ))
    events = []
    for event in service.stream_answer_question(
        user_id=user_id, session_id=session_id, question="如何设计缓存？", web_search_enabled=True,
    ):
        events.append(event)
        if event["type"] == "chunk" and "详细回答" in event["chunk"].text:
            service.cancel_task(user_id=user_id, task_id=event["task"].task_id)
    assert events[-1]["type"] == "cancelled"
    assert "不应再显示" not in events[-1]["task"].answer_text
    assert service.billing_service.state_for_user(user_id=user_id).balance == 200


def test_route_disconnect_before_task_acknowledgement_cleans_up_reservation(monkeypatch):
    service, user_id, session_id = _start_synthetic_session(monkeypatch, "disconnect")

    class CaptureProducer(LiveAnswerStreamExecutor):
        def stream(self, lease, producer_factory):
            self.producer = producer_factory()
            self.lease = lease

            async def empty():
                if False:
                    yield ""
            return empty()

    executor = CaptureProducer(max_workers=1, queue_max=0, event_queue_max=1)
    request = Request({"type": "http", "app": SimpleNamespace(state=SimpleNamespace(live_answer_stream_executor=executor))})
    publish = []
    monkeypatch.setattr(live_answer, "_publish_answer_task_event", lambda *args, **kwargs: publish.append(kwargs["phase"]))
    try:
        asyncio.run(live_answer.stream_live_answer(
            request_context=request,
            request=LiveAnswerQuestionRequest(userId=user_id, sessionId=session_id, question="如何设计缓存？", idempotencyKey="synthetic-web-disconnect", webSearchEnabled=True),
            auth_context=None, service=service, realtime=SimpleNamespace(),
        ))
        assert "task-started" in next(executor.producer)
        executor.producer.close()
        task = service.list_session_history(user_id=user_id, session_id=session_id)[-1]
        assert task.status == "cancelled"
        assert service.billing_service.usage_reservations_by_id["synthetic-web-disconnect"].status == "released"
        assert publish == ["task-started", "cancelled"]
    finally:
        executor.lease.release()
        executor.shutdown()
