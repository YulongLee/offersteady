"""Real app lifespan + PG authority + deterministic, network-free answer stages."""
from dataclasses import replace
import json
import logging
from types import SimpleNamespace

from fastapi import Request
from fastapi.testclient import TestClient
import pytest

from app import main
from app.deps import chat_service, optional_authenticated_context, realtime_speech_service
from app.platform import cn_hot_database as provider
from app.ports.chat import ChatAnswerChunk
from app.ports.retrieval import RetrievalContext
from app.services.chat_repository import InMemoryChatRepository
from app.services.chat_service import ChatService, FilePromptTemplateAdapter, InterviewPromptBuilder
from app.services.document_repository import InMemoryDocumentRepository
from app.services.session_service import SessionService
from test_cn_hot_database import local_pg, persistent_repositories


class SyntheticStageGateway:
    def __init__(self):
        self.stages = []

    def stream_generate(self, *, question, prompt, attempt):
        assert attempt == 0
        stage = prompt.prompt_config.template_id
        self.stages.append(stage)
        if stage == "interview-chat-quick":
            text = f"<normalized_question>{question}</normalized_question>先明确超时边界，再核对请求是否重复。"
        else:
            assert stage == "interview-chat-detail"
            text = "先测量建连和查询耗时，再用相同合成场景验证优化效果，并保留失败回滚路径。"
        yield ChatAnswerChunk(sequence=1, text=text, is_final=True, provider_finish_reason="stop")


@local_pg
@pytest.mark.parametrize("enabled", [False, True])
def test_started_app_streams_complete_answer_and_rejects_ended_session(persistent_repositories, monkeypatch, enabled):
    original, auth, repository, authentication, user, _, token, session = persistent_repositories
    settings = original.model_copy(update={"cn_hot_database_pool_enabled": enabled,
        "cn_hot_database_pool_timeout_seconds": 2.0,
        "admin_enabled": False, "realtime_resource_reaper_enabled": False,
        "mock_interview_enabled": False, "cn_resume_optimizer_enabled": False,
        "chat_qwen_api_key": None, "chat_qwen_base_url": None})
    auth.settings = repository.settings = settings
    sessions = SessionService(settings=settings, repository=repository, document_repository=InMemoryDocumentRepository())
    repository.save_session(replace(session, status="live"))
    gateway = SyntheticStageGateway()
    tasks = InMemoryChatRepository()
    retrieval = SimpleNamespace(retrieve=lambda **kwargs: RetrievalContext(
        normalized_question=kwargs["question"], context_text="", chunks=[],
        candidate_count=0, final_count=0, strategy="filtered-first"))
    answers = ChatService(settings=settings, logger=logging.getLogger("test.synthetic-lifespan-answer"),
        session_service=sessions, retrieval_service=retrieval, object_storage=SimpleNamespace(),
        repository=tasks, prompt_template=FilePromptTemplateAdapter(settings),
        prompt_builder=InterviewPromptBuilder(), llm_gateway=gateway)
    published = []

    def authorize(request: Request):
        assert request.headers["authorization"] == f"Bearer {token}"
        return authentication.authenticate_access_token(access_token=token)

    monkeypatch.setattr(main, "get_settings", lambda: settings)
    app = main.create_app()
    app.dependency_overrides[optional_authenticated_context] = authorize
    app.dependency_overrides[chat_service] = lambda: answers
    app.dependency_overrides[realtime_speech_service] = lambda: SimpleNamespace(
        publish_session_event=lambda **event: published.append(event))
    body = {"userId": user.user_id, "sessionId": session.session_id,
        "question": "如何验证性能优化？", "stream": True, "idempotencyKey": "synthetic-first-answer"}
    try:
        # Enter the actual create_app lifespan so its dedicated stream executor
        # and the new outer database lifecycle are both installed and released.
        with TestClient(app) as client:
            assert provider.cn_hot_database_diagnostics(settings)["active"] is enabled
            with client.stream("POST", "/api/v1/live-answer/questions/stream", json=body,
                               headers={"Authorization": f"Bearer {token}"}) as response:
                assert response.status_code == 200
                assert response.headers["content-type"].startswith("text/event-stream")
                events = [json.loads(line[5:].strip()) for line in response.iter_lines() if line.startswith("data:")]
            assert events[0]["type"] == "task-started"
            assert events[-1]["type"] == "completed"
            event_types = [event["type"] for event in events]
            assert event_types.index("task-started") < event_types.index("quick-completed") < event_types.index("completed")
            completed = events[-1]["task"]
            assert completed["status"] == "completed" and completed["quickAnswerCompleted"] is True
            assert completed["questionNormalizationStatus"] == "completed"
            assert "明确超时边界" in completed["answerText"] and "失败回滚路径" in completed["answerText"]
            assert gateway.stages == ["interview-chat-quick", "interview-chat-detail"]
            assert tasks.get_task(completed["taskId"]).status == "completed"
            assert any(event["payload"]["phase"] == "completed" for event in published)

            # Commit via the real session service, then exercise normal HTTP
            # answer admission again; no test stub decides whether it is ended.
            assert sessions.end_session(user_id=user.user_id, session_id=session.session_id).status == "ended"
            rejected = client.post("/api/v1/live-answer/questions/stream",
                json={**body, "idempotencyKey": "synthetic-after-end"},
                headers={"Authorization": f"Bearer {token}"})
            assert rejected.status_code == 400
            assert rejected.json()["success"] is False
            assert "进行中" in rejected.json()["error"]["message"]
            assert len(tasks.tasks) == 1 and len(gateway.stages) == 2
    finally:
        app.dependency_overrides.clear()
    assert provider._entry is None and provider._retiring is None
