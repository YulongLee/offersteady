import json

from fastapi.testclient import TestClient

from app import deps
from app.main import create_app
from app.ports.chat import ChatAnswerChunk, GatewayAnswerResult, UsageReport


client = TestClient(create_app())


class ProviderLanguageDriftGateway:
    def __init__(self, *, always_chinese: bool = False) -> None:
        self.always_chinese = always_chinese
        self.calls: list[tuple[str, bool]] = []

    @staticmethod
    def _usage() -> UsageReport:
        return UsageReport(prompt_tokens=10, completion_tokens=10, total_tokens=20, provider_name="synthetic", model_name="synthetic")

    def generate(self, *, question, prompt, stream, attempt):
        _ = question, stream, attempt
        repair = "ENGLISH-ONLY REPAIR" in prompt.system_prompt
        self.calls.append((prompt.prompt_config.template_id, repair))
        text = (
            "Quick Answer\nI would introduce my machine-learning focus and the verified systems I have delivered.\n\n---\n\nDetailed Answer\nI would connect that experience to the role and explain the relevant engineering trade-offs."
            if repair and not self.always_chinese
            else "简要回答\n我是算法工程师，主要负责推荐系统。\n\n---\n\n详细回答\n我会介绍项目经验和技术能力。"
        )
        return GatewayAnswerResult(provider_name="synthetic", model_name="synthetic", chunks=[ChatAnswerChunk(sequence=1, text=text, is_final=True)], final_text=text, usage=self._usage())

    def stream_generate(self, *, question, prompt, attempt):
        _ = question, attempt
        repair = "ENGLISH-ONLY REPAIR" in prompt.system_prompt
        self.calls.append((prompt.prompt_config.template_id, repair))
        if prompt.prompt_config.template_id.endswith("quick"):
            text = (
                "<normalized_question>Please introduce yourself.</normalized_question>\nI would briefly explain my machine-learning focus and the verified systems I have delivered."
                if repair and not self.always_chinese
                else "<normalized_question>介绍自己</normalized_question>\n我是算法工程师，主要负责推荐系统和自然语言处理。"
            )
        else:
            text = "I would then connect that experience to the role, explain my engineering decisions, and close with the measurable outcome."
        yield ChatAnswerChunk(sequence=1, text=text, is_final=True, provider_finish_reason="stop")


def unwrap(response):
    assert response.status_code == 200, response.text
    return response.json()["data"]


def parse_sse(payload: str) -> list[dict[str, object]]:
    return [
        json.loads(line.removeprefix("data: "))
        for line in payload.splitlines()
        if line.startswith("data: ")
    ]


def test_english_session_routes_nonstream_and_stream_answers_to_english_prompts() -> None:
    user_id = "synthetic-english-answer-user"
    created = unwrap(client.post("/api/v1/sessions", json={
        "userId": user_id,
        "title": "Synthetic English interview",
        "interviewLanguage": "en-US",
    }))
    session_id = created["sessionId"]
    assert created["interviewLanguage"] == "en-US"
    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": user_id}))

    ordinary = unwrap(client.post("/api/v1/live-answer/questions", json={
        "userId": user_id,
        "sessionId": session_id,
        "question": "How would you design a safe deployment pipeline?",
        "stream": False,
    }))["task"]
    assert ordinary["promptTemplateId"] == "interview-chat-en-system"
    assert "Quick Answer" in ordinary["answerText"]
    assert "详细回答" not in ordinary["answerText"]

    with client.stream("POST", "/api/v1/live-answer/questions/stream", json={
        "userId": user_id,
        "sessionId": session_id,
        "question": "Tell me about a production incident you handled.",
        "stream": True,
    }) as response:
        assert response.status_code == 200
        events = parse_sse(response.read().decode("utf-8"))

    completed = events[-1]["task"]
    assert isinstance(completed, dict)
    assert completed["promptTemplateId"] == "interview-chat-quick+detail"
    assert "Quick Answer" in completed["answerText"]
    assert "Detailed Answer" in completed["answerText"]
    assert "简单回答" not in completed["answerText"]


def test_language_route_validates_values_and_locks_after_start() -> None:
    user_id = "synthetic-language-route-user"
    created = unwrap(client.post("/api/v1/sessions", json={"userId": user_id, "title": "Route contract"}))
    session_id = created["sessionId"]

    invalid = client.patch(
        f"/api/v1/sessions/{session_id}/language",
        json={"userId": user_id, "interviewLanguage": "fr-FR"},
    )
    assert invalid.status_code == 422

    updated = unwrap(client.patch(
        f"/api/v1/sessions/{session_id}/language",
        json={"userId": user_id, "interviewLanguage": "en-US"},
    ))
    assert updated["interviewLanguage"] == "en-US"

    unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": user_id}))
    locked = client.patch(
        f"/api/v1/sessions/{session_id}/language",
        json={"userId": user_id, "interviewLanguage": "zh-CN"},
    )
    assert locked.status_code == 409
    assert locked.json()["error"]["details"]["errorCode"] == "interview_language_locked"


def test_english_stream_repairs_provider_chinese_drift_before_publishing() -> None:
    service = deps.chat_service()
    original_gateway = service.llm_gateway
    gateway = ProviderLanguageDriftGateway()
    service.llm_gateway = gateway
    try:
        user_id = "synthetic-english-repair-user"
        created = unwrap(client.post("/api/v1/sessions", json={
            "userId": user_id,
            "title": "算法工程师",
            "interviewLanguage": "en-US",
        }))
        session_id = created["sessionId"]
        unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": user_id}))

        with client.stream("POST", "/api/v1/live-answer/questions/stream", json={
            "userId": user_id,
            "sessionId": session_id,
            "question": "介绍自己",
            "stream": True,
        }) as response:
            events = parse_sse(response.read().decode("utf-8"))

        completed = events[-1]["task"]
        assert completed["status"] == "completed"
        assert completed["question"] == "Please introduce yourself."
        assert "我是" not in completed["answerText"]
        assert "I would" in completed["answerText"]
        assert ("interview-chat-en-quick", False) in gateway.calls
        assert ("interview-chat-en-quick", True) in gateway.calls
    finally:
        service.llm_gateway = original_gateway


def test_english_nonstream_repairs_provider_chinese_drift() -> None:
    service = deps.chat_service()
    original_gateway = service.llm_gateway
    gateway = ProviderLanguageDriftGateway()
    service.llm_gateway = gateway
    try:
        user_id = "synthetic-english-nonstream-repair-user"
        created = unwrap(client.post("/api/v1/sessions", json={
            "userId": user_id,
            "title": "算法工程师",
            "interviewLanguage": "en-US",
        }))
        session_id = created["sessionId"]
        unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": user_id}))

        task = unwrap(client.post("/api/v1/live-answer/questions", json={
            "userId": user_id,
            "sessionId": session_id,
            "question": "介绍自己",
            "stream": False,
        }))["task"]

        assert task["status"] == "completed"
        assert "I would" in task["answerText"]
        assert "我是" not in task["answerText"]
        assert gateway.calls == [("interview-chat-en-system", False), ("interview-chat-en-system", True)]
    finally:
        service.llm_gateway = original_gateway


def test_english_stream_fails_closed_when_provider_repeatedly_returns_chinese() -> None:
    service = deps.chat_service()
    original_gateway = service.llm_gateway
    service.llm_gateway = ProviderLanguageDriftGateway(always_chinese=True)
    try:
        user_id = "synthetic-english-fail-closed-user"
        created = unwrap(client.post("/api/v1/sessions", json={
            "userId": user_id,
            "title": "算法工程师",
            "interviewLanguage": "en-US",
        }))
        session_id = created["sessionId"]
        unwrap(client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": user_id}))

        with client.stream("POST", "/api/v1/live-answer/questions/stream", json={
            "userId": user_id,
            "sessionId": session_id,
            "question": "介绍自己",
            "stream": True,
        }) as response:
            events = parse_sse(response.read().decode("utf-8"))

        assert events[-1]["type"] == "failed"
        assert events[-1]["task"]["errorCode"] == "chat_output_language_violation"
        assert events[-1]["task"]["answerText"] == ""
    finally:
        service.llm_gateway = original_gateway
