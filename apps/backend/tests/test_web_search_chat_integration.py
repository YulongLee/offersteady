from __future__ import annotations

from app.deps import chat_service as chat_service_dep
from app.main import create_app
from app.ports.chat import ChatAnswerChunk
from app.ports.web_search import WebSearchAnswer, WebSearchSource
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
