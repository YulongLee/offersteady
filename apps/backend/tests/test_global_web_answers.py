"""Exercise Global membership and quick/detail ordering with synthetic providers."""
from time import time
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.deps import chat_service
from app.main import create_app
from app.ports.chat import ChatAnswerChunk
from app.ports.web_search import WebSearchAnswer, WebSearchSource
from app.services.global_commerce_repository import InMemoryGlobalCommerceRepository
from app.services.global_commerce_service import GlobalCommerceService
from app.services.global_usage_billing_adapter import GlobalUsageBillingAdapter


@pytest.mark.parametrize("outcome", ["succeeded", "unavailable", "cancel"])
def test_global_web_never_blocks_quick_or_changes_membership_meter(monkeypatch, outcome):
    user = "synthetic-web-" + uuid4().hex
    commerce = GlobalCommerceService(Settings(_env_file=None, product_edition="global"), InMemoryGlobalCommerceRepository())
    commerce.grant_purchase(user_id=user, offer_code="global-pro-weekly", source_kind="admin",
        source_id=user, starts_at_ms=int(time()*1000)-1)
    billing = GlobalUsageBillingAdapter(commerce)
    with TestClient(create_app()) as client:
        response = client.post("/api/v1/sessions", json={"userId": user, "title": "Synthetic Global", "interviewLanguage": "en-US"})
        response.raise_for_status()
        sid = response.json()["data"]["sessionId"]
        client.post(f"/api/v1/sessions/{sid}/start", json={"userId": user}).raise_for_status()
        service = chat_service()
        monkeypatch.setattr(service, "settings", service.settings.model_copy(update={
            "product_edition": "global", "global_web_answer_enabled": True, "web_search_enabled": True,
            "chat_detail_retrieval_prefetch_enabled": False}))
        monkeypatch.setattr(service, "billing_service", billing)
        quick_seen = False
        task_id = None
        search_calls = []
        def model(*, question, prompt, attempt):
            if "detail" in prompt.prompt_config.template_id:
                assert quick_seen
                text = "Measure cache hits and verify the bounded eviction policy."
            else:
                text = f"<normalized_question>{question}</normalized_question>Use a bounded cache and measure latency."
            yield ChatAnswerChunk(sequence=1, text=text, is_final=True, provider_finish_reason="stop")
        def search(**kwargs):
            assert quick_seen, "Search must not block quick completion"
            search_calls.append(kwargs)
            assert "private resume" in kwargs["user_prompt"]
            if outcome == "cancel":
                service.cancel_task(user_id=user, task_id=task_id)
            return WebSearchAnswer(answer_text="Verify the official cache contract before changing the eviction policy.",
                status="succeeded" if outcome == "cancel" else outcome,
                sources=[WebSearchSource(title="Synthetic source", url="https://example.invalid/docs")])
        monkeypatch.setattr(service.llm_gateway, "stream_generate", model)
        monkeypatch.setattr(service, "web_search_gateway", SimpleNamespace(answer=search))
        usage = "global-web-" + uuid4().hex
        events = []
        for event in service.stream_answer_question(user_id=user, session_id=sid, question="How do you design a cache?", usage_id=usage, web_search_enabled=True):
            events.append(event)
            task_id = event["task"].task_id
            if event["type"] == "quick-completed":
                quick_seen = True
                assert not search_calls
        assert len(search_calls) == 1 and quick_seen
        final = events[-1]["task"]
        assert "Use a bounded cache" in final.answer_text
        assert events[-1]["type"] == ("cancelled" if outcome == "cancel" else "completed")
        assert billing._records[usage].points_reserved == 0
        if outcome == "cancel":
            assert "official cache contract" not in final.answer_text
        local = list(service.stream_answer_question(user_id=user, session_id=sid,
            question="How do you design a cache?", usage_id=usage+"-standard", web_search_enabled=False))[-1]
        assert local["type"] == "completed" and local["task"].web_search_status == "disabled"
        assert len(search_calls) == 1
        client.post(f"/api/v1/sessions/{sid}/end", json={"userId": user}).raise_for_status()


def test_global_rollout_default_off():
    assert Settings(_env_file=None, product_edition="global").global_web_answer_enabled is False
    assert Settings(_env_file=None, product_edition="global").global_mock_interview_enabled is False
